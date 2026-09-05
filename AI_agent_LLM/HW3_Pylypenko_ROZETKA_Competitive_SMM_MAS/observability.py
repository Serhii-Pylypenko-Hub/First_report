"""Налаштування LangSmith без збереження ключів у коді."""

from __future__ import annotations

import os
from typing import Any


def tracing_config(thread_id: str) -> dict[str, Any]:
    enabled = bool(os.getenv("LANGSMITH_API_KEY")) and os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    return {
        "configurable": {"thread_id": thread_id},
        "metadata": {"project": os.getenv("LANGSMITH_PROJECT", "hw3-rozetka-competitive-mas")},
        "tags": ["hw3", "competitive-smm", "langgraph"],
        "tracing_enabled": enabled,
    }
