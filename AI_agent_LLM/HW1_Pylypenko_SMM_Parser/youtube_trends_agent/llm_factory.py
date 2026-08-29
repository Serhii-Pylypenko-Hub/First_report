"""Безпечне створення Gemini або локального Ollama без ключів у коді."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def create_chat_model(provider: str | None = None) -> "BaseChatModel":
    """Створити LLM за LLM_PROVIDER=gemini|ollama."""

    selected = (provider or os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
    if selected == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError(
                "Для Gemini задайте GOOGLE_API_KEY у .env. "
                "Ключ ніколи не потрібно записувати в notebook."
            )
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0,
        )
    if selected == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            temperature=0,
            num_predict=700,
        )
    raise ValueError("LLM_PROVIDER повинен бути gemini або ollama")
