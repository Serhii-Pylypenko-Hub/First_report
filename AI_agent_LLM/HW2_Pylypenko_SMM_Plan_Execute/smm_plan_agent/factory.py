"""Фабрика LLM-провайдерів і стандартних шляхів проєкту."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .graph import SMMPlanExecuteAgent
from .scripted import ScriptedPlanExecuteLLM


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_llm(provider: str = "scripted"):
    """Створити scripted, Gemini або Ollama модель."""

    load_dotenv(PROJECT_ROOT / ".env")
    selected = provider.lower()
    if selected == "scripted":
        return ScriptedPlanExecuteLLM()
    if selected == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("Для Gemini задайте GOOGLE_API_KEY у .env")
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0.1,
        )
    if selected == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen3:4b"), temperature=0)
    raise ValueError("provider повинен бути scripted, gemini або ollama")


def create_agent(
    *,
    provider: str = "scripted",
    db_path: str | Path | None = None,
    chroma_path: str | Path | None = None,
    action_log_path: str | Path | None = None,
) -> SMMPlanExecuteAgent:
    """Створити готовий агент зі стандартними артефактами проєкту."""

    return SMMPlanExecuteAgent(
        llm=create_llm(provider),
        fixture_path=PROJECT_ROOT / "fixtures" / "youtube_videos.json",
        knowledge_documents_path=PROJECT_ROOT / "knowledge_documents.json",
        chroma_path=chroma_path or PROJECT_ROOT / "chroma_db",
        db_path=db_path or PROJECT_ROOT / "agent_state.db",
        action_log_path=action_log_path or PROJECT_ROOT / "campaign_actions.jsonl",
    )

