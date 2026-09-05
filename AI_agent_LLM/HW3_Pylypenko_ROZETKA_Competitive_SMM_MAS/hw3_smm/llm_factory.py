"""Опційний LLM-router; fixture-режим не потребує ключа і не приховує fallback."""

from __future__ import annotations

import os


def create_router_model():
    from langchain_openai import ChatOpenAI

    if os.getenv("OPENROUTER_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            timeout=30,
            max_retries=2,
        )
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            temperature=0,
            timeout=30,
            max_retries=2,
        )
    return None
