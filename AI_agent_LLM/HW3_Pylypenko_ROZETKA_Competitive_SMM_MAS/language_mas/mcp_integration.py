"""Нативне підключення FastMCP tools через langchain-mcp-adapters."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from .security import TOOL_PERMISSIONS


async def load_language_mcp_tools() -> list:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    server = Path(__file__).resolve().parents[1] / "mcp_server.py"
    client = MultiServerMCPClient({
        "language": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(server)],
        }
    })
    return await client.get_tools()


async def load_language_mcp_tools_for_agent(agent: str) -> list:
    """Server-side deny-by-default проєкція: агент бачить лише власний allowlist."""

    allowed = TOOL_PERMISSIONS.get(agent, set())
    tools = await load_language_mcp_tools()
    return [tool for tool in tools if tool.name in allowed]


async def list_language_mcp_tool_names() -> list[str]:
    async with asyncio.timeout(30):
        return sorted(tool.name for tool in await load_language_mcp_tools())
