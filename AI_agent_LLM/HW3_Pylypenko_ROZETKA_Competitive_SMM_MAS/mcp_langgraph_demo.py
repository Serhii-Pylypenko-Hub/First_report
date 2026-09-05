"""Два реальні MCP tool calls із LangGraph node через MultiServerMCPClient."""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from hw3_smm.mcp_integration import load_mcp_tools


class DemoState(TypedDict, total=False):
    query_type: str
    result: dict[str, Any]
    tool_name: str


async def run_query(query_type: str) -> dict[str, Any]:
    agent_name = "collector" if query_type == "collect" else "researcher"
    tools = await load_mcp_tools(agent_name)
    if len(tools) != 1:
        raise RuntimeError(f"Неочікуваний allowlist {agent_name}: {[tool.name for tool in tools]}")
    tool = tools[0]

    async def agent_node(state: DemoState) -> dict[str, Any]:
        if state["query_type"] == "collect":
            result = await tool.ainvoke({"brand": "rozetka", "platforms": ["instagram"], "period_days": 30, "source_mode": "fixture"})
        else:
            result = await tool.ainvoke({"query": "нормалізація метрик і funnel", "top_k": 2})
        if isinstance(result, list) and result and isinstance(result[0], dict) and "text" in result[0]:
            result = json.loads(result[0]["text"])
        return {"result": result, "tool_name": tool.name}

    graph = StateGraph(DemoState)
    graph.add_node("mcp_agent", agent_node)
    graph.add_edge(START, "mcp_agent")
    graph.add_edge("mcp_agent", END)
    return await graph.compile().ainvoke({"query_type": query_type})


async def main() -> None:
    rows = [await run_query("collect"), await run_query("knowledge")]
    summary = [
        {
            "query": row["query_type"],
            "tool": row["tool_name"],
            "status": row["result"].get("status"),
            "result_keys": sorted(row["result"].get("data", {})),
        }
        for row in rows
    ]
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
