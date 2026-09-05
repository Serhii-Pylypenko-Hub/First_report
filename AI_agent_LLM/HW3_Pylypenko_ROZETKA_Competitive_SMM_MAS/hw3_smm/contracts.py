"""Єдиний контракт успіху/помилки для Python та MCP tools."""

from __future__ import annotations

from typing import Any


def ok(data: Any) -> dict[str, Any]:
    return {"status": "ok", "data": data}


def error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {"code": code, "message": message, "details": details or {}},
    }
