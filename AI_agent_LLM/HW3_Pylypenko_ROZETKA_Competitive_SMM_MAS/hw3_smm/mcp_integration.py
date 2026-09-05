"""Реальне stdio-підключення FastMCP tools до LangGraph-compatible tools."""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from guardrails import TOOL_PERMISSIONS


ROOT = Path(__file__).resolve().parents[1]


async def load_mcp_tools(agent_name: str):
    client = MultiServerMCPClient({
        "competitive_smm": {
            "command": sys.executable,
            "args": [str(ROOT / "mcp_server.py")],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()
    allowed = TOOL_PERMISSIONS.get(agent_name, set())
    return [tool for tool in tools if tool.name in allowed]


async def integration_summary() -> dict:
    # Один stdio-сеанс достатній для discovery; повторний запуск сервера для
    # кожної ролі зайво витрачав пам'ять на Windows/Jupyter.
    client = MultiServerMCPClient({
        "competitive_smm": {
            "command": sys.executable,
            "args": [str(ROOT / "mcp_server.py")],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()
    names = {tool.name for tool in tools}
    return {
        agent: sorted(names & TOOL_PERMISSIONS.get(agent, set()))
        for agent in ("supervisor", "collector", "researcher", "analyst", "strategist", "approval_executor")
    }
