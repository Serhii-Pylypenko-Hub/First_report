"""Guarded ReAct-збирач із timeout, max_steps і signature loop detection."""

from __future__ import annotations

import json
import time
from hashlib import sha256
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from guardrails import authorize_tool
from tools_legacy import collect_brand_posts_payload


class ReActState(TypedDict, total=False):
    brands: list[str]
    platforms: list[str]
    period_days: int
    index: int
    step_count: int
    started: float
    tool_call: dict[str, Any]
    signatures: list[str]
    posts: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    trajectory: list[dict[str, Any]]
    completed: bool


class GuardedCollectorReAct:
    def __init__(self, max_steps: int = 8, timeout_seconds: float = 30.0) -> None:
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds

    def run(self, brands: list[str], platforms: list[str], period_days: int) -> dict[str, Any]:
        def agent_decision(state: ReActState) -> dict[str, Any]:
            if state["index"] >= len(state["brands"]):
                return {"completed": True}
            if state["step_count"] >= self.max_steps:
                return {"completed": True, "errors": [*state["errors"], {"code": "MAX_STEPS_EXCEEDED"}]}
            if time.monotonic() - state["started"] > self.timeout_seconds:
                return {"completed": True, "errors": [*state["errors"], {"code": "TIMEOUT"}]}
            brand = state["brands"][state["index"]]
            return {"tool_call": {
                "name": "collect_brand_posts",
                "args": {"brand": brand, "platforms": state["platforms"], "period_days": state["period_days"], "source_mode": "fixture"},
            }}

        def tool_observation(state: ReActState) -> dict[str, Any]:
            call = state["tool_call"]
            signature = sha256(json.dumps(call, sort_keys=True).encode("utf-8")).hexdigest()
            if signature in state["signatures"]:
                return {"completed": True, "errors": [*state["errors"], {"code": "REPEATED_TOOL_CALL"}]}
            authorize_tool("collector", call["name"], call["args"])
            result = collect_brand_posts_payload(**call["args"])
            new_posts = list(state["posts"])
            new_errors = list(state["errors"])
            if result["status"] == "ok":
                new_posts.extend(result["data"]["posts"])
            else:
                new_errors.append(result["error"])
            event = {
                "step": state["step_count"] + 1,
                "thought": f'Зібрати контрольовані дані {call["args"]["brand"]}',
                "tool": call["name"], "status": result["status"],
            }
            return {
                "index": state["index"] + 1,
                "step_count": state["step_count"] + 1,
                "signatures": [*state["signatures"], signature],
                "posts": new_posts,
                "errors": new_errors,
                "trajectory": [*state["trajectory"], event],
            }

        def after_decision(state: ReActState) -> Literal["tool_observation", "__end__"]:
            return "__end__" if state.get("completed") else "tool_observation"

        graph = StateGraph(ReActState)
        graph.add_node("agent_decision", agent_decision)
        graph.add_node("tool_observation", tool_observation)
        graph.add_edge(START, "agent_decision")
        graph.add_conditional_edges("agent_decision", after_decision)
        graph.add_edge("tool_observation", "agent_decision")
        app = graph.compile()
        started = time.monotonic()
        result = app.invoke({
            "brands": brands, "platforms": platforms, "period_days": period_days,
            "index": 0, "step_count": 0, "started": started, "signatures": [],
            "posts": [], "errors": [], "trajectory": [], "completed": False,
        })
        return {
            "status": "ok" if result["posts"] else "error",
            "posts": result["posts"], "errors": result["errors"],
            "trajectory": result["trajectory"],
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        }
