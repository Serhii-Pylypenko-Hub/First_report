"""Вкладений ReAct executor із max_steps, timeout і repeat detection."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class ReActState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    task: dict[str, Any]
    step_count: int
    started_monotonic: float
    timeout_seconds: int
    max_steps: int
    signatures: list[str]
    observations: list[dict]
    trajectory: list[dict]
    completed: bool
    stop_reason: str
    final_answer: str


def _event(event: str, **details: Any) -> dict:
    return {"timestamp": datetime.now(UTC).isoformat(), "event": event, **details}


class GuardedReActExecutor:
    """Один ReAct-агент, який адаптується до observation інструментів."""

    def __init__(self, *, llm, tools: list, max_steps: int = 10, timeout_seconds: int = 120) -> None:
        self.tools = {item.name: item for item in tools}
        self.llm = llm.bind_tools(tools)
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.app = self._build_graph()

    def _build_graph(self):
        def agent_node(state: ReActState) -> dict:
            elapsed = time.monotonic() - state["started_monotonic"]
            if elapsed >= state["timeout_seconds"]:
                return {
                    "completed": True,
                    "stop_reason": "timeout",
                    "final_answer": "ReAct зупинено за timeout.",
                    "trajectory": [*state.get("trajectory", []), _event("guardrail", reason="timeout")],
                }
            if state.get("step_count", 0) >= state["max_steps"]:
                return {
                    "completed": True,
                    "stop_reason": "max_steps",
                    "final_answer": "ReAct досяг max_steps.",
                    "trajectory": [*state.get("trajectory", []), _event("guardrail", reason="max_steps")],
                }
            response = self.llm.invoke(
                [
                    SystemMessage(
                        content=(
                            "Ти ReAct executor SMM-аналітика. Обирай один tool за ітерацію. "
                            "Після error не повторюй той самий виклик: обери fixture fallback."
                        )
                    ),
                    *state["messages"],
                ]
            )
            calls = getattr(response, "tool_calls", None) or []
            text = str(response.content or "")
            return {
                "messages": [response],
                "step_count": state.get("step_count", 0) + 1,
                "completed": not bool(calls),
                "stop_reason": "completed" if not calls else "",
                "final_answer": text if not calls else state.get("final_answer", ""),
                "trajectory": [
                    *state.get("trajectory", []),
                    _event(
                        "agent_decision",
                        step=state.get("step_count", 0) + 1,
                        tool_calls=[{"name": call["name"], "args": call.get("args", {})} for call in calls],
                        final=not bool(calls),
                    ),
                ],
            }

        def tools_node(state: ReActState) -> dict:
            last = state["messages"][-1]
            call = (getattr(last, "tool_calls", None) or [])[0]
            name = str(call["name"])
            args = dict(call.get("args") or {})
            signature = json.dumps({"name": name, "args": args}, sort_keys=True, ensure_ascii=False, default=str)
            if signature in state.get("signatures", []):
                return {
                    "completed": True,
                    "stop_reason": "repeated_tool_call",
                    "final_answer": f"Зупинено повторний виклик {name}.",
                    "trajectory": [
                        *state.get("trajectory", []),
                        _event("guardrail", reason="repeated_tool_call", tool=name),
                    ],
                }
            if name not in self.tools:
                payload = {"status": "error", "error": {"code": "UNKNOWN_TOOL", "message": name}}
            else:
                raw = self.tools[name].invoke(args)
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = {"status": "error", "error": {"code": "INVALID_JSON", "message": raw}}
            observation = {"tool": name, "args": args, "payload": payload}
            return {
                "messages": [ToolMessage(content=json.dumps(payload, ensure_ascii=False), tool_call_id=call["id"], name=name)],
                "signatures": [*state.get("signatures", []), signature],
                "observations": [*state.get("observations", []), observation],
                "trajectory": [
                    *state.get("trajectory", []),
                    _event(
                        "tool_observation",
                        tool=name,
                        status=payload.get("status"),
                        error_code=payload.get("error", {}).get("code"),
                    ),
                ],
            }

        def after_agent(state: ReActState) -> Literal["tools", "__end__"]:
            if state.get("completed") or state.get("stop_reason") in {
                "timeout",
                "max_steps",
                "repeated_tool_call",
            }:
                return END
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        def after_tools(state: ReActState) -> Literal["agent", "__end__"]:
            return END if state.get("completed") else "agent"

        graph = StateGraph(ReActState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", after_agent)
        graph.add_conditional_edges("tools", after_tools)
        return graph.compile()

    def run(self, task: dict[str, Any]) -> dict:
        initial: ReActState = {
            "messages": [HumanMessage(content=f"TASK_JSON:{json.dumps(task, ensure_ascii=False, default=str)}")],
            "task": task,
            "step_count": 0,
            "started_monotonic": time.monotonic(),
            "timeout_seconds": self.timeout_seconds,
            "max_steps": self.max_steps,
            "signatures": [],
            "observations": [],
            "trajectory": [_event("react_started", operation=task.get("operation"))],
            "completed": False,
            "stop_reason": "",
            "final_answer": "",
        }
        return self.app.invoke(initial, config={"recursion_limit": self.max_steps * 3 + 5})
