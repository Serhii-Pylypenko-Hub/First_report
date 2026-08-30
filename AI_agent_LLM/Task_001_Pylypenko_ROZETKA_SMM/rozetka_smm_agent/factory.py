"""Фабрика провайдерів і стандартних шляхів проєкту."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .data_source import SocialDataSource
from .knowledge import SMMKnowledgeBase
from .plan_execute import RozetkaSMMPlanAgent
from .scripted import ScriptedSMMModel
from .tools import build_tools


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_llm(provider: str = "scripted"):
    load_dotenv(PROJECT_ROOT / ".env")
    if provider == "scripted":
        return ScriptedSMMModel()
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("Додайте GOOGLE_API_KEY до .env")
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0.1,
            timeout=30,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen3:4b"), temperature=0)
    raise ValueError("provider повинен бути scripted, gemini або ollama")


def create_agent(
    *,
    provider: str = "scripted",
    live_enabled: bool = False,
    db_path: str | Path | None = None,
    chroma_path: str | Path | None = None,
    trajectory_path: str | Path | None = None,
) -> RozetkaSMMPlanAgent:
    source = SocialDataSource(
        PROJECT_ROOT / "fixtures" / "social_posts.json",
        live_enabled=live_enabled,
    )
    knowledge = SMMKnowledgeBase(
        persist_path=chroma_path or PROJECT_ROOT / "chroma_db",
        documents_path=PROJECT_ROOT / "knowledge_documents.json",
    )
    tools = build_tools(source=source, knowledge_base=knowledge, project_root=PROJECT_ROOT)
    return RozetkaSMMPlanAgent(
        llm=create_llm(provider),
        tools=tools,
        db_path=db_path or PROJECT_ROOT / "agent_state.db",
        trajectory_path=trajectory_path or PROJECT_ROOT / "trajectory.json",
    )
