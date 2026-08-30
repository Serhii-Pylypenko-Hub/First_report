"""LangGraph: planner → executor → replanner + два HITL approval gates."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from .data_source import FixtureYouTubeSource
from .knowledge import BrandSafetyKnowledgeBase
from .models import (
    CampaignApprovalDecision,
    HumanModerationDecision,
    Plan,
    ReplanDecision,
    ScheduleCampaignInput,
)
from .scripted import extract_topic
from .tools import build_tools


class PlanExecuteState(TypedDict, total=False):
    """Checkpointed state одного thread."""

    messages: Annotated[list[AnyMessage], add_messages]
    request: str
    topic: str
    goal: str
    plan: list[str]
    current_step: int
    results: list[str]
    candidates: list[dict]
    knowledge_hits: list[dict]
    approved: list[dict]
    needs_review: list[dict]
    blocked: list[dict]
    rejected_by_human: list[dict]
    final_top: list[dict]
    moderation_reviewed: bool
    pending_action: dict | None
    campaign_status: str
    completed: bool
    last_tool: str
    tool_history: list[str]
    last_result: str
    next_node: str
    replan_count: int


class SMMPlanExecuteAgent:
    """Збирає навчальний Plan-and-Execute workflow із file-backed persistence."""

    def __init__(
        self,
        *,
        llm,
        fixture_path: str | Path,
        knowledge_documents_path: str | Path,
        chroma_path: str | Path,
        db_path: str | Path,
        action_log_path: str | Path,
    ) -> None:
        self.llm = llm
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.checkpointer = SqliteSaver(self.connection)
        self.source = FixtureYouTubeSource(fixture_path)
        self.knowledge_base = BrandSafetyKnowledgeBase(
            persist_path=chroma_path,
            documents_path=knowledge_documents_path,
        )
        self.tools = build_tools(
            source=self.source,
            knowledge_base=self.knowledge_base,
            action_log_path=action_log_path,
        )
        self.tools_by_name = {item.name: item for item in self.tools}
        self.planner_llm = self.llm.with_structured_output(Plan)
        self.replanner_llm = self.llm.with_structured_output(ReplanDecision)
        self.executor_llm = self.llm.bind_tools(self.tools)
        self.app = self._build_graph()

    @staticmethod
    def config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

    def close(self) -> None:
        self.connection.close()

    def _build_graph(self):
        def planner_node(state: PlanExecuteState) -> dict:
            context = {"request": state["request"]}
            plan = self.planner_llm.invoke(
                "Створи повний план із 3–5 кроків для SMM-задачі. "
                "Використай доступні tools і завершуй ризиковою дією лише після перевірок.\n"
                f"CONTEXT_JSON:{json.dumps(context, ensure_ascii=False)}"
            )
            return {
                "goal": plan.goal,
                "plan": plan.steps,
                "current_step": 0,
                "results": [],
                "candidates": [],
                "knowledge_hits": [],
                "approved": [],
                "needs_review": [],
                "blocked": [],
                "rejected_by_human": [],
                "final_top": [],
                "moderation_reviewed": False,
                "pending_action": None,
                "campaign_status": "not_requested",
                "completed": False,
                "last_tool": "planner",
                "tool_history": [],
                "last_result": f"Створено план із {len(plan.steps)} кроків.",
                "next_node": "executor",
                "replan_count": 0,
                "messages": [AIMessage(content=f"План: {plan.steps}")],
            }

        def executor_node(state: PlanExecuteState) -> dict:
            index = state.get("current_step", 0)
            plan = state.get("plan", [])
            if index >= len(plan):
                return {"completed": True, "next_node": END}

            context = {
                "step": plan[index],
                "topic": state.get("topic", ""),
                "candidates": state.get("candidates", []),
                "knowledge_hits": state.get("knowledge_hits", []),
                "final_top": state.get("final_top", []),
                "previous_results": state.get("results", []),
            }
            response = self.executor_llm.invoke(
                "Виконай рівно поточний крок. Вибери один доречний tool. "
                "search_knowledge використовуй лише для правил/знань.\n"
                f"CONTEXT_JSON:{json.dumps(context, ensure_ascii=False, default=str)}"
            )
            calls = getattr(response, "tool_calls", None) or []
            if not calls:
                text = str(response.content or "Крок не виконав tool.")
                return {
                    "current_step": index + 1,
                    "results": [*state.get("results", []), text],
                    "last_tool": "none",
                    "tool_history": [*state.get("tool_history", []), "none"],
                    "last_result": text,
                    "messages": [AIMessage(content=text)],
                }

            call = calls[0]
            name = str(call["name"])
            args = dict(call.get("args") or {})
            if name not in self.tools_by_name:
                raise ValueError(f"LLM обрала невідомий tool: {name}")

            # Ризиковий tool лише готується. Фактичний invoke відбудеться після interrupt.
            if name == "schedule_campaign":
                validated = ScheduleCampaignInput.model_validate(args).model_dump()
                return {
                    "pending_action": {"tool": name, "args": validated},
                    "last_tool": name,
                    "tool_history": [*state.get("tool_history", []), name],
                    "last_result": "Очікується approval перед ризиковою дією.",
                    "campaign_status": "awaiting_approval",
                }

            raw = self.tools_by_name[name].invoke(args)
            payload = json.loads(raw)
            update: dict = {
                "current_step": index + 1,
                "results": [*state.get("results", []), f"{name}: {raw}"],
                "last_tool": name,
                "tool_history": [*state.get("tool_history", []), name],
                "last_result": raw,
                "messages": [AIMessage(content=f"Виконано {name}.")],
            }
            if payload.get("result_type") == "video_search":
                update["candidates"] = payload["candidates"]
            elif payload.get("result_type") == "knowledge":
                update["knowledge_hits"] = payload["hits"]
            elif payload.get("result_type") == "evaluation":
                update.update(
                    {
                        "approved": payload["approved"],
                        "needs_review": payload["needs_review"],
                        "blocked": payload["blocked"],
                        "final_top": payload["approved"],
                        "moderation_reviewed": not bool(payload["needs_review"]),
                    }
                )
            return update

        def replanner_node(state: PlanExecuteState) -> dict:
            if state.get("pending_action"):
                return {"next_node": "campaign_approval"}
            if state.get("needs_review") and not state.get("moderation_reviewed"):
                return {"next_node": "moderation_review"}

            context = {
                "plan": state.get("plan", []),
                "current_step": state.get("current_step", 0),
                "results": state.get("results", []),
                "last_tool": state.get("last_tool", ""),
                "candidates": state.get("candidates", []),
                "campaign_status": state.get("campaign_status", ""),
            }
            decision = self.replanner_llm.invoke(
                "Оціни прогрес. Поверни continue, replan або finish. "
                "Не завершуй, доки ризикова дія не approved/rejected людиною.\n"
                f"CONTEXT_JSON:{json.dumps(context, ensure_ascii=False, default=str)}"
            )
            if decision.action == "finish":
                return {
                    "completed": True,
                    "next_node": END,
                    "messages": [AIMessage(content=f"Завершено: {decision.reasoning}")],
                }
            if decision.action == "replan" and decision.updated_steps:
                executed = state.get("plan", [])[: state.get("current_step", 0)]
                return {
                    "plan": [*executed, *decision.updated_steps],
                    "replan_count": state.get("replan_count", 0) + 1,
                    "next_node": "executor",
                    "messages": [AIMessage(content=f"План оновлено: {decision.reasoning}")],
                }
            return {"next_node": "executor"}

        def moderation_review_node(state: PlanExecuteState) -> dict:
            review_items = state.get("needs_review", [])
            payload = {
                "gate": "content_moderation",
                "message": "Позначте прийнятні позиції зі списку needs_review.",
                "already_approved": state.get("approved", []),
                "needs_review": review_items,
                "allowed_decisions": ["approve_selected", "approve_all", "reject_all"],
            }
            raw_decision = interrupt(payload)
            decision = HumanModerationDecision.model_validate(raw_decision)
            valid_ids = {item["video"]["video_id"] for item in review_items}
            if decision.decision == "approve_all":
                accepted_ids = valid_ids
            elif decision.decision == "reject_all":
                accepted_ids = set()
            else:
                accepted_ids = set(decision.acceptable_video_ids) & valid_ids

            accepted = [item for item in review_items if item["video"]["video_id"] in accepted_ids]
            rejected = [item for item in review_items if item["video"]["video_id"] not in accepted_ids]
            merged_by_id = {
                item["video"]["video_id"]: item
                for item in [*state.get("approved", []), *accepted]
            }
            final_top = sorted(
                merged_by_id.values(),
                key=lambda item: item["video"]["trend_score"],
                reverse=True,
            )[:10]
            summary = (
                f"Human review: прийнято {len(accepted)}, відхилено {len(rejected)} "
                f"із {len(review_items)} сумнівних позицій."
            )
            return {
                "approved": list(merged_by_id.values()),
                "rejected_by_human": rejected,
                "final_top": final_top,
                "moderation_reviewed": True,
                "results": [*state.get("results", []), summary],
                "last_result": summary,
                "messages": [AIMessage(content=summary)],
            }

        def campaign_approval_node(state: PlanExecuteState) -> dict:
            pending = state.get("pending_action") or {}
            payload = {
                "gate": "campaign_approval",
                "message": "Перевірте raw parameters ризикової дії schedule_campaign.",
                "action": pending,
                "allowed_decisions": ["approve", "edit", "reject"],
            }
            raw_decision = interrupt(payload)
            decision = CampaignApprovalDecision.model_validate(raw_decision)
            index = state.get("current_step", 0)
            if decision.decision == "reject":
                summary = f"schedule_campaign відхилено: {decision.reason or 'без пояснення'}"
                return {
                    "pending_action": None,
                    "campaign_status": "rejected",
                    "current_step": index + 1,
                    "results": [*state.get("results", []), summary],
                    "last_result": summary,
                    "messages": [AIMessage(content=summary)],
                }

            args = dict(pending.get("args") or {})
            if decision.decision == "edit":
                allowed_fields = {"campaign_name", "video_ids", "planned_date", "note"}
                unknown = set(decision.edits) - allowed_fields
                if unknown:
                    raise ValueError(f"Недозволені edit-поля: {sorted(unknown)}")
                args.update(decision.edits)
            validated = ScheduleCampaignInput.model_validate(args)
            approved_ids = {item["video"]["video_id"] for item in state.get("final_top", [])}
            if not set(validated.video_ids).issubset(approved_ids):
                raise ValueError("Campaign може містити лише позиції з фінального схваленого топу")
            raw = self.tools_by_name["schedule_campaign"].invoke(validated.model_dump())
            return {
                "pending_action": None,
                "campaign_status": "scheduled",
                "current_step": index + 1,
                "results": [*state.get("results", []), f"schedule_campaign: {raw}"],
                "last_result": raw,
                "messages": [AIMessage(content="Кампанію заплановано після підтвердження людини.")],
                "tool_history": [*state.get("tool_history", []), "schedule_campaign:executed"],
            }

        def route_after_replanner(state: PlanExecuteState) -> Literal[
            "executor", "moderation_review", "campaign_approval", "__end__"
        ]:
            next_node = state.get("next_node", "executor")
            if next_node == END or state.get("completed"):
                return END
            if next_node in {"moderation_review", "campaign_approval"}:
                return next_node  # type: ignore[return-value]
            return "executor"

        graph = StateGraph(PlanExecuteState)
        graph.add_node("planner", planner_node)
        graph.add_node("executor", executor_node)
        graph.add_node("replanner", replanner_node)
        graph.add_node("moderation_review", moderation_review_node)
        graph.add_node("campaign_approval", campaign_approval_node)
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "executor")
        graph.add_edge("executor", "replanner")
        graph.add_conditional_edges("replanner", route_after_replanner)
        graph.add_edge("moderation_review", "replanner")
        graph.add_edge("campaign_approval", "replanner")
        return graph.compile(checkpointer=self.checkpointer)

    def start(self, request: str, *, thread_id: str) -> dict:
        initial: PlanExecuteState = {
            "messages": [HumanMessage(content=request)],
            "request": request,
            "topic": extract_topic(request),
        }
        return self.app.invoke(initial, config=self.config(thread_id))

    def resume(self, decision: dict, *, thread_id: str) -> dict:
        return self.app.invoke(Command(resume=decision), config=self.config(thread_id))

    def state(self, *, thread_id: str):
        return self.app.get_state(self.config(thread_id))
