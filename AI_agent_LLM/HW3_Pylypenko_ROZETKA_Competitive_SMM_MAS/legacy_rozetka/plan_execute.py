"""Один Plan-and-Execute агент із вкладеним Guarded ReAct executor."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .data_source import OFFICIAL_PROFILES, PROFILE_REGISTRY
from .models import ExportDecision, ExportReportInput, Plan, ReplanDecision
from .react import GuardedReActExecutor
from .reporting import build_agent_result


class PlanExecuteState(TypedDict, total=False):
    request: str
    goal: str
    plan: list[str]
    current_step: int
    results: list[str]
    posts: list[dict]
    source_status: dict[str, dict]
    knowledge_hits: list[dict]
    analysis: dict
    pending_export: dict | None
    approval_decision: str
    approval_reason: str
    edited_export_path: str | None
    report_status: str
    report_path: str | None
    completed: bool
    next_node: str
    last_stop_reason: str
    replan_count: int
    trajectory: list[dict]


def _event(event: str, **details: Any) -> dict:
    return {"timestamp": datetime.now(UTC).isoformat(), "event": event, **details}


class RozetkaSMMPlanAgent:
    """File-backed одноагентна система для кросплатформної SMM-аналітики."""

    def __init__(
        self,
        *,
        llm,
        tools: list,
        db_path: str | Path,
        trajectory_path: str | Path,
    ) -> None:
        self.llm = llm
        self.tools = {item.name: item for item in tools}
        safe_tools = [item for item in tools if item.name != "export_smm_report"]
        self.react = GuardedReActExecutor(
            llm=llm,
            tools=safe_tools,
            max_steps=10,
            timeout_seconds=120,
        )
        self.planner_llm = llm.with_structured_output(Plan)
        self.replanner_llm = llm.with_structured_output(ReplanDecision)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.checkpointer = SqliteSaver(self.connection)
        self.trajectory_path = Path(trajectory_path)
        self.app = self._build_graph()

    @staticmethod
    def config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}

    def close(self) -> None:
        self.connection.close()

    def _build_graph(self):
        def planner_node(state: PlanExecuteState) -> dict:
            plan = self.planner_llm.invoke(
                "Створи повний план кросплатформної SMM-аналітики одного бренду. "
                "Збір виконує ReAct із fallback, RAG викликається лише за потреби, "
                "а write-експорт потребує HITL.\n"
                f"CONTEXT_JSON:{json.dumps({'request': state['request']}, ensure_ascii=False)}"
            )
            return {
                "goal": plan.goal,
                "plan": plan.steps,
                "current_step": 0,
                "results": [],
                "posts": [],
                "source_status": {},
                "knowledge_hits": [],
                "analysis": {},
                "pending_export": None,
                "approval_decision": "pending",
                "approval_reason": "",
                "edited_export_path": None,
                "report_status": "not_requested",
                "report_path": None,
                "completed": False,
                "next_node": "executor",
                "last_stop_reason": "",
                "replan_count": 0,
                "trajectory": [_event("plan_created", goal=plan.goal, steps=plan.steps)],
            }

        def executor_node(state: PlanExecuteState) -> dict:
            index = state.get("current_step", 0)
            plan = state.get("plan", [])
            if index >= len(plan):
                return {"completed": True, "next_node": END}
            step = plan[index]
            if "COLLECT_PLATFORMS" in step:
                task = {
                    "operation": "collect",
                    "brand": "ROZETKA",
                    "platforms": ["instagram", "facebook", "threads", "telegram"],
                    "period_days": 30,
                }
                react_result = self.react.run(task)
                posts: list[dict] = []
                statuses: dict[str, dict] = {
                    platform: {
                        **PROFILE_REGISTRY[platform],
                        "profile_url": OFFICIAL_PROFILES[platform],
                        "attempts": [],
                    }
                    for platform in task["platforms"]
                }
                for observation in react_result.get("observations", []):
                    payload = observation["payload"]
                    platform = (
                        payload.get("data", {}).get("platform")
                        or payload.get("error", {}).get("details", {}).get("platform")
                    )
                    if not platform:
                        continue
                    platform_status = statuses[platform]
                    platform_status["attempts"].append(
                        {
                            "tool": observation["tool"],
                            "status": payload.get("status"),
                            "error_code": payload.get("error", {}).get("code"),
                        }
                    )
                    if payload.get("status") == "ok":
                        collected = payload.get("data", {}).get("posts", [])
                        posts.extend(collected)
                        platform_status.update(
                            {
                                "final_source_mode": payload.get("data", {}).get("source_mode"),
                                "post_count": len(collected),
                                "zero_posts_reason": (
                                    "official_profile_not_verified"
                                    if not collected and platform_status["profile_status"] == "not_verified"
                                    else "no_posts_in_snapshot"
                                    if not collected
                                    else None
                                ),
                            }
                        )
                summary = f"Зібрано {len(posts)} постів; ReAct steps={react_result.get('step_count', 0)}."
                return {
                    "current_step": index + 1,
                    "posts": posts,
                    "source_status": statuses,
                    "results": [*state.get("results", []), summary],
                    "last_stop_reason": react_result.get("stop_reason", ""),
                    "trajectory": [
                        *state.get("trajectory", []),
                        *react_result.get("trajectory", []),
                        _event("plan_step_completed", step=step, summary=summary),
                    ],
                }
            if "SEARCH_KNOWLEDGE" in step:
                react_result = self.react.run({"operation": "knowledge"})
                hits: list[dict] = []
                for observation in react_result.get("observations", []):
                    if observation["tool"] == "knowledge_search" and observation["payload"].get("status") == "ok":
                        hits = observation["payload"]["data"]["hits"]
                summary = f"Agentic RAG повернув {len(hits)} документів."
                return {
                    "current_step": index + 1,
                    "knowledge_hits": hits,
                    "results": [*state.get("results", []), summary],
                    "last_stop_reason": react_result.get("stop_reason", ""),
                    "trajectory": [
                        *state.get("trajectory", []),
                        *react_result.get("trajectory", []),
                        _event("plan_step_completed", step=step, summary=summary),
                    ],
                }
            if "ANALYZE_PATTERNS" in step:
                react_result = self.react.run(
                    {"operation": "analyze", "posts": state.get("posts", [])}
                )
                analysis: dict = {}
                for observation in react_result.get("observations", []):
                    if observation["tool"] == "analyze_marketing_patterns" and observation["payload"].get("status") == "ok":
                        analysis = observation["payload"]["data"]
                summary = f"Знайдено {len(analysis.get('top_5_patterns', []))} основних патернів."
                return {
                    "current_step": index + 1,
                    "analysis": analysis,
                    "results": [*state.get("results", []), summary],
                    "last_stop_reason": react_result.get("stop_reason", ""),
                    "trajectory": [
                        *state.get("trajectory", []),
                        *react_result.get("trajectory", []),
                        _event("plan_step_completed", step=step, summary=summary),
                    ],
                }
            if "EXPORT_REPORT" in step:
                pending = ExportReportInput(
                    path="outputs/rozetka_smm_report.json",
                    report=state.get("analysis", {}),
                ).model_dump(mode="json")
                return {
                    "pending_export": pending,
                    "report_status": "awaiting_approval",
                    "next_node": "risky_export",
                    "trajectory": [
                        *state.get("trajectory", []),
                        _event("risky_action_prepared", tool="export_smm_report", path=pending["path"]),
                    ],
                }
            return {
                "current_step": index + 1,
                "results": [*state.get("results", []), f"Невідомий крок пропущено: {step}"],
            }

        def replanner_node(state: PlanExecuteState) -> dict:
            if state.get("pending_export"):
                return {"next_node": "risky_export"}
            context = {
                "plan": state.get("plan", []),
                "current_step": state.get("current_step", 0),
                "last_stop_reason": state.get("last_stop_reason", ""),
                "report_status": state.get("report_status", ""),
            }
            decision = self.replanner_llm.invoke(
                "Оціни прогрес після одного кроку: continue, replan або finish.\n"
                f"CONTEXT_JSON:{json.dumps(context, ensure_ascii=False)}"
            )
            trajectory = [
                *state.get("trajectory", []),
                _event("replan_decision", action=decision.action, reasoning=decision.reasoning),
            ]
            if decision.action == "finish":
                return {"completed": True, "next_node": END, "trajectory": trajectory}
            if decision.action == "replan" and decision.updated_steps:
                completed_steps = state.get("plan", [])[: state.get("current_step", 0)]
                return {
                    "plan": [*completed_steps, *decision.updated_steps],
                    "replan_count": state.get("replan_count", 0) + 1,
                    "next_node": "executor",
                    "trajectory": trajectory,
                }
            return {"next_node": "executor", "trajectory": trajectory}

        def risky_export_node(state: PlanExecuteState) -> dict:
            """Цей вузол завжди зупиняється через compile(interrupt_before=...)."""

            decision = state.get("approval_decision", "pending")
            index = state.get("current_step", 0)
            if decision == "reject":
                summary = f"Експорт відхилено: {state.get('approval_reason') or 'без пояснення'}"
                return {
                    "pending_export": None,
                    "report_status": "rejected",
                    "current_step": index + 1,
                    "results": [*state.get("results", []), summary],
                    "trajectory": [*state.get("trajectory", []), _event("export_rejected")],
                }
            if decision not in {"approve", "edit"}:
                raise ValueError("risky_export не може виконуватися без approve/edit")
            args = dict(state.get("pending_export") or {})
            if state.get("edited_export_path"):
                args["path"] = state["edited_export_path"]
            validated = ExportReportInput.model_validate(args)
            payload = json.loads(self.tools["export_smm_report"].invoke(validated.model_dump()))
            if payload.get("status") != "ok":
                raise RuntimeError(payload.get("error", {}).get("message", "Помилка експорту"))
            summary = f"Звіт експортовано: {payload['data']['path']}"
            return {
                "pending_export": None,
                "report_status": "exported",
                "report_path": payload["data"]["path"],
                "current_step": index + 1,
                "results": [*state.get("results", []), summary],
                "trajectory": [
                    *state.get("trajectory", []),
                    _event("export_executed", path=payload["data"]["path"]),
                ],
            }

        def route_replanner(state: PlanExecuteState) -> Literal["executor", "risky_export", "__end__"]:
            if state.get("completed") or state.get("next_node") == END:
                return END
            return "risky_export" if state.get("next_node") == "risky_export" else "executor"

        graph = StateGraph(PlanExecuteState)
        graph.add_node("planner", planner_node)
        graph.add_node("executor", executor_node)
        graph.add_node("replanner", replanner_node)
        graph.add_node("risky_export", risky_export_node)
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "executor")
        graph.add_edge("executor", "replanner")
        graph.add_conditional_edges("replanner", route_replanner)
        graph.add_edge("risky_export", "replanner")
        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["risky_export"],
        )

    def _save_trajectory(self, thread_id: str) -> None:
        state = self.state(thread_id=thread_id)
        payload = {
            "thread_id": thread_id,
            "saved_at": datetime.now(UTC).isoformat(),
            "events": state.values.get("trajectory", []),
        }
        self.trajectory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def start(self, request: str, *, thread_id: str) -> dict:
        result = self.app.invoke({"request": request}, config=self.config(thread_id))
        self._save_trajectory(thread_id)
        return result

    def pending_gate(self, *, thread_id: str) -> dict | None:
        snapshot = self.state(thread_id=thread_id)
        if "risky_export" not in snapshot.next:
            return None
        pending = snapshot.values.get("pending_export") or {}
        return {
            "gate": "report_export",
            "interrupt_mode": "interrupt_before",
            "action": {"tool": "export_smm_report", "path": pending.get("path")},
            "allowed_decisions": ["approve", "edit", "reject"],
        }

    def resume(self, decision: dict, *, thread_id: str) -> dict:
        snapshot = self.state(thread_id=thread_id)
        if not snapshot.values:
            raise ValueError(
                f"Thread '{thread_id}' не знайдено. Спочатку виконайте команду start."
            )
        if "risky_export" not in snapshot.next:
            raise ValueError(
                f"Thread '{thread_id}' не очікує рішення HITL; "
                "перевірте його через команду state."
            )
        parsed = ExportDecision.model_validate(decision)
        update = {
            "approval_decision": parsed.decision,
            "approval_reason": parsed.reason,
            "edited_export_path": parsed.path if parsed.decision == "edit" else None,
        }
        self.app.update_state(self.config(thread_id), update)
        result = self.app.invoke(None, config=self.config(thread_id))
        self._save_trajectory(thread_id)
        return result

    def state(self, *, thread_id: str):
        return self.app.get_state(self.config(thread_id))

    def result(self, *, thread_id: str) -> dict:
        """Канонічний результат, спільний для Notebook, CLI та test runner."""

        return build_agent_result(dict(self.state(thread_id=thread_id).values))
