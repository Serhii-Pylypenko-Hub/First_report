"""Supervisor MAS у LangGraph: вузькі ролі, HITL, persistence і JSON-контракти."""

from __future__ import annotations

import operator
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import traceable

from mcp_server import apply_approved_corrections_payload

from .analyzers import (
    grammar_findings,
    structure_findings,
    style_findings,
    terminology_findings,
    verify_findings,
)
from .audit import JsonlTracer
from .correction_memory import UserCorrectionMemory
from .knowledge import SecureKnowledgeBase
from .models import ActorContext, AnalysisRequest, Finding, ReviewDecision, ReviewPayload
from .security import MAX_INPUT_TOKENS, ToolGuardrail, assert_scope, estimate_tokens, input_guardrail, redact_pii


class WorkflowState(TypedDict, total=False):
    request: dict
    actor: dict
    original_hash: str
    alerts: list[dict]
    raw_findings: Annotated[list[dict], operator.add]
    completed_agents: Annotated[list[str], operator.add]
    verified_findings: list[dict]
    certain_findings: list[dict]
    review_findings: list[dict]
    decisions: list[dict]
    corrected_document: dict
    applied: list[dict]
    rejected: list[str]
    memory_updates: list[dict]
    status: str
    stop_reason: str
    final_result: dict
    step_count: int


SPECIALISTS = ("grammar", "style", "terminology", "structure")
MAX_GRAPH_STEPS = 16
MAX_FINDINGS = 200
MAX_SPECIALIST_SECONDS = 5.0
MAX_OUTPUT_TOKENS_PER_LLM_CALL = 1200
EXECUTION_PLAN = [
    {"step_id": "grammar", "executor": "grammar", "llm_planning": False},
    {"step_id": "style", "executor": "style", "llm_planning": False},
    {"step_id": "terminology", "executor": "terminology", "llm_planning": False},
    {"step_id": "structure", "executor": "structure", "llm_planning": False},
    {"step_id": "verify", "executor": "verifier", "llm_planning": False},
    {"step_id": "approval", "executor": "human_review", "llm_planning": False},
]


class LanguageSupervisorMAS:
    def __init__(
        self,
        *,
        checkpointer=None,
        trace_path: Path | None = None,
        correction_memory: UserCorrectionMemory | None = None,
    ) -> None:
        self.kb = SecureKnowledgeBase()
        self.tool_guardrail = ToolGuardrail(max_calls=30)
        self.tracer = JsonlTracer(trace_path)
        self.checkpointer = checkpointer or InMemorySaver()
        self.correction_memory = correction_memory or UserCorrectionMemory()
        self.app = self._build_graph().compile(checkpointer=self.checkpointer)

    def _request(self, state: WorkflowState) -> AnalysisRequest:
        return AnalysisRequest.model_validate(state["request"])

    def _trace(self, state: WorkflowState, node: str, **extra) -> None:
        request = self._request(state)
        self.tracer.emit(
            "node_completed", node_name=node, request_id=request.request_id,
            document_id=request.document.document_id, step_count=state.get("step_count", 0), **extra,
        )

    @staticmethod
    def _agent_results(state: WorkflowState) -> dict:
        """Формує прозорий результат кожної ролі без додавання нового доступу до даних."""

        raw = state.get("raw_findings", [])
        grouped = {name: [item for item in raw if item.get("agent") == name] for name in SPECIALISTS}
        completed = state.get("completed_agents", [])
        verified = state.get("verified_findings", [])
        results = {
            "supervisor": {
                "status": "completed" if len(completed) == len(SPECIALISTS) else "running",
                "routing_order": [*completed, *( ["verifier"] if "verified_findings" in state else [])],
                "completed_specialists": completed,
                "step_count": state.get("step_count", 0),
                "budget_limit": MAX_GRAPH_STEPS,
                "execution_plan": EXECUTION_PLAN,
                "input_token_budget": MAX_INPUT_TOKENS,
                "output_tokens_per_llm_call": MAX_OUTPUT_TOKENS_PER_LLM_CALL,
            }
        }
        for name in SPECIALISTS:
            results[name] = {
                "status": "completed" if name in completed else "not_run",
                "finding_count": len(grouped[name]),
                "findings": grouped[name],
            }
        results["verifier"] = {
            "status": "completed" if "verified_findings" in state else "not_run",
            "received_count": len(raw),
            "verified_count": len(verified),
            "filtered_count": max(0, len(raw) - len(verified)),
            "certain_count": len(state.get("certain_findings", [])),
            "needs_review_count": len(state.get("review_findings", [])),
            "findings": verified,
        }
        return results

    def input_gate(self, state: WorkflowState) -> Command[Literal["supervisor", "finalize"]]:
        request = self._request(state)
        alerts = input_guardrail(request)
        self._trace(state, "input_gate", alert_count=len(alerts))
        if alerts:
            return Command(
                update={"alerts": alerts, "status": "blocked", "stop_reason": "prompt_injection", "step_count": 1},
                goto="finalize",
            )
        return Command(
            update={"original_hash": request.document.content_hash(), "alerts": [], "status": "running", "step_count": 1},
            goto="supervisor",
        )

    def supervisor(self, state: WorkflowState) -> Command:
        step = state.get("step_count", 0) + 1
        if step > MAX_GRAPH_STEPS:
            return Command(update={"status": "partial", "stop_reason": "step_budget", "step_count": step}, goto="finalize")
        completed = set(state.get("completed_agents", []))
        for specialist in SPECIALISTS:
            if specialist not in completed:
                self._trace(state, "supervisor", next_agent=specialist)
                return Command(update={"step_count": step}, goto=specialist)
        self._trace(state, "supervisor", next_agent="verifier")
        return Command(update={"step_count": step}, goto="verifier")

    def _specialist(self, name: str, analyzer, state: WorkflowState) -> Command[Literal["supervisor"]]:
        request = self._request(state)
        actor = ActorContext.model_validate(state["actor"])
        before = request.document.content_hash()
        started = perf_counter()
        results: list[Finding] = analyzer(request.document, self.kb)
        remembered = self.correction_memory.retrieve(actor, request.document, agent=name)
        if remembered:
            remembered_originals = {item.original_text.casefold() for item in remembered}
            results = [item for item in results if item.original_text.casefold() not in remembered_originals]
            results.extend(remembered)
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        if elapsed_ms > MAX_SPECIALIST_SECONDS * 1000:
            raise TimeoutError(f"{name} перевищив ліміт {MAX_SPECIALIST_SECONDS} с")
        if len(results) > MAX_FINDINGS:
            results = results[:MAX_FINDINGS]
        after = request.document.content_hash()
        if before != after or before != state["original_hash"]:
            raise RuntimeError("Спеціаліст спробував змінити вхідний документ")
        self._trace(state, name, finding_count=len(results), elapsed_ms=elapsed_ms, finding_budget=MAX_FINDINGS)
        return Command(
            update={
                "raw_findings": [item.model_dump(mode="json") for item in results],
                "completed_agents": [name],
                "step_count": state.get("step_count", 0) + 1,
            },
            goto="supervisor",
        )

    def grammar(self, state: WorkflowState) -> Command:
        return self._specialist("grammar", grammar_findings, state)

    def style(self, state: WorkflowState) -> Command:
        return self._specialist("style", style_findings, state)

    def terminology(self, state: WorkflowState) -> Command:
        return self._specialist("terminology", terminology_findings, state)

    def structure(self, state: WorkflowState) -> Command:
        return self._specialist("structure", structure_findings, state)

    def verifier(self, state: WorkflowState) -> Command[Literal["human_review", "finalize"]]:
        request = self._request(state)
        raw = [Finding.model_validate(item) for item in state.get("raw_findings", [])]
        verified = verify_findings(request.document, raw)
        certain = [item for item in verified if item.confidence >= 0.85]
        review = [item for item in verified if item.confidence < 0.85]
        payload = [item.model_dump(mode="json") for item in verified]
        self._trace(state, "verifier", verified_count=len(payload))
        if not payload:
            return Command(
                update={"verified_findings": [], "certain_findings": [], "review_findings": [], "status": "completed", "stop_reason": "no_findings"},
                goto="finalize",
            )
        return Command(
            update={
                "verified_findings": payload,
                "certain_findings": [item.model_dump(mode="json") for item in certain],
                "review_findings": [item.model_dump(mode="json") for item in review],
                "status": "awaiting_review",
            },
            goto="human_review",
        )

    def human_review(self, state: WorkflowState) -> Command[Literal["apply_changes", "finalize"]]:
        request = self._request(state)
        decision_raw = interrupt({
            "gate": "linguistic_corrections",
            "request_id": request.request_id,
            "allowed_decisions": ["approve", "edit", "reject"],
            "certain": state.get("certain_findings", []),
            "needs_review": state.get("review_findings", []),
        })
        decisions = ReviewPayload.model_validate(decision_raw)
        if decisions.request_id != request.request_id:
            raise ValueError("request_id рішення не відповідає активному workflow")
        known = {item["finding_id"] for item in state.get("verified_findings", [])}
        submitted = {item.finding_id for item in decisions.decisions}
        if submitted != known:
            missing = sorted(known - submitted)
            extra = sorted(submitted - known)
            raise ValueError(f"Рішення повинні охоплювати всі findings; missing={missing}, extra={extra}")
        decision_counts = {
            value: sum(item.decision == value for item in decisions.decisions)
            for value in ("approve", "edit", "reject")
        }
        self._trace(state, "human_review", decision_count=len(decisions.decisions), decisions=decision_counts)
        return Command(
            update={"decisions": [item.model_dump(mode="json") for item in decisions.decisions], "status": "approved_for_apply"},
            goto="apply_changes",
        )

    def apply_changes(self, state: WorkflowState) -> Command[Literal["finalize"]]:
        self.tool_guardrail.authorize("approval_executor", "apply_approved_corrections", {"decision_count": len(state["decisions"])})
        request = self._request(state)
        result = apply_approved_corrections_payload(
            request.document.model_dump(mode="json", by_alias=True), state["verified_findings"], state["decisions"],
        )
        if result["status"] != "ok":
            return Command(update={"status": "failed", "stop_reason": result["error"]["code"]}, goto="finalize")
        data = result["data"]
        actor = ActorContext.model_validate(state["actor"])
        memory_updates = self.correction_memory.remember_confirmed_edits(
            actor,
            [Finding.model_validate(item) for item in state["verified_findings"]],
            [ReviewDecision.model_validate(item) for item in state["decisions"]],
        )
        self._trace(state, "apply_changes", applied_count=len(data["applied"]), memory_updates=len(memory_updates))
        return Command(
            update={
                "corrected_document": data["document"], "applied": data["applied"], "rejected": data["rejected"],
                "memory_updates": memory_updates,
                "status": "completed", "stop_reason": "completed",
            },
            goto="finalize",
        )

    def finalize(self, state: WorkflowState) -> dict:
        request = self._request(state)
        result = {
            "request_id": request.request_id,
            "document_id": request.document.document_id,
            "status": state.get("status", "failed"),
            "stop_reason": state.get("stop_reason", "awaiting_human_review"),
            "security_alerts": state.get("alerts", []),
            "agent_results": self._agent_results(state),
            "certain_findings": state.get("certain_findings", []),
            "needs_review": state.get("review_findings", []),
            "decisions": state.get("decisions", []),
            "applied": state.get("applied", []),
            "rejected": state.get("rejected", []),
            "memory_updates": state.get("memory_updates", []),
            "corrected_document": state.get("corrected_document"),
            "limitations": [
                "Scripted mode демонструє архітектуру та контрольовані правила, а не повний промисловий словник.",
                "Файловий ingestion реалізовано окремим ізольованим адаптером; мовне ядро приймає лише валідований JSON.",
            ],
        }
        safe_result = redact_pii(result)
        self._trace(state, "finalize", status=result["status"], stop_reason=result["stop_reason"])
        return {"final_result": safe_result}

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(WorkflowState)
        for name in ("input_gate", "supervisor", *SPECIALISTS, "verifier", "human_review", "apply_changes", "finalize"):
            builder.add_node(name, getattr(self, name))
        builder.add_edge(START, "input_gate")
        builder.add_edge("finalize", END)
        return builder

    @staticmethod
    def config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": MAX_GRAPH_STEPS}

    @traceable(name="language-mas-langgraph-start", run_type="chain")
    def start(self, request: dict, actor: ActorContext, *, thread_id: str) -> dict:
        validated = AnalysisRequest.model_validate(request)
        token_estimate = estimate_tokens("\n".join(node.text for node in validated.document.nodes))
        self.tracer.emit(
            "workflow_started", request_id=validated.request_id,
            document_id=validated.document.document_id, user_id=actor.user_id,
            tenant_id=actor.tenant_id, input_token_estimate=token_estimate,
            input_token_budget=MAX_INPUT_TOKENS, graph_step_budget=MAX_GRAPH_STEPS,
        )
        return self.app.invoke(
            {"request": validated.model_dump(mode="json", by_alias=True), "actor": actor.model_dump(mode="json"), "raw_findings": [], "completed_agents": [], "step_count": 0},
            config=self.config(thread_id),
        )

    @traceable(name="language-mas-langgraph-resume", run_type="chain")
    def resume(self, review: dict, actor: ActorContext, *, thread_id: str) -> dict:
        self._authorized_snapshot(thread_id, actor)
        return self.app.invoke(Command(resume=review), config=self.config(thread_id))

    def _authorized_snapshot(self, thread_id: str, actor: ActorContext):
        snapshot = self.app.get_state(self.config(thread_id))
        saved_actor = ActorContext.model_validate(snapshot.values["actor"])
        assert_scope(actor, saved_actor.tenant_id, saved_actor.user_id)
        return snapshot

    def state(self, actor: ActorContext, *, thread_id: str):
        return self._authorized_snapshot(thread_id, actor)

    def result(self, actor: ActorContext, *, thread_id: str) -> dict:
        snapshot = self._authorized_snapshot(thread_id, actor)
        if snapshot.values.get("final_result"):
            return snapshot.values["final_result"]
        return {
            "request_id": snapshot.values.get("request", {}).get("request_id"),
            "status": snapshot.values.get("status", "unknown"),
            "agent_results": redact_pii(self._agent_results(snapshot.values)),
            "certain_findings": snapshot.values.get("certain_findings", []),
            "needs_review": snapshot.values.get("review_findings", []),
            "next": list(snapshot.next),
            "interrupts": [item.value for task in snapshot.tasks for item in task.interrupts],
        }


def create_langgraph_mas(
    *, trace_path: str | Path | None = None, checkpointer=None,
    correction_memory: UserCorrectionMemory | None = None,
) -> LanguageSupervisorMAS:
    return LanguageSupervisorMAS(
        trace_path=Path(trace_path) if trace_path else None,
        checkpointer=checkpointer,
        correction_memory=correction_memory,
    )
