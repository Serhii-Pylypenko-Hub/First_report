"""Детермінована LLM-підміна для тестів і fixture-демонстрації без API."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

from langchain_core.messages import AIMessage

from .models import Plan, ReplanDecision


def _context(text: str) -> dict:
    marker = "CONTEXT_JSON:"
    if marker not in text:
        return {}
    raw = text.split(marker, 1)[1].strip()
    return json.loads(raw)


class _StructuredScripted:
    def __init__(self, schema: type) -> None:
        self.schema = schema

    def invoke(self, prompt: str):
        data = _context(str(prompt))
        if self.schema is Plan:
            return Plan(
                goal=data.get("request", "Підготувати безпечну SMM-кампанію"),
                steps=[
                    "Знайти свіжі YouTube-відео за темою через search_recent_videos.",
                    "Отримати brand-safety правила через search_knowledge.",
                    "Оцінити тренди та сформувати approved і needs_review через evaluate_trends.",
                    "Запланувати кампанію з фінального топу через schedule_campaign.",
                ],
            )
        if self.schema is ReplanDecision:
            if data.get("campaign_status") in {"scheduled", "rejected"}:
                return ReplanDecision(
                    action="finish",
                    reasoning="Ризикова дія завершена або відхилена людиною.",
                )
            if data.get("current_step", 0) >= len(data.get("plan", [])):
                return ReplanDecision(action="finish", reasoning="Усі кроки плану виконано.")
            if data.get("last_tool") == "search_recent_videos" and not data.get("candidates"):
                return ReplanDecision(
                    action="replan",
                    updated_steps=[
                        "Повторити загальний пошук через search_recent_videos без вузької теми.",
                        "Отримати brand-safety правила через search_knowledge.",
                        "Оцінити тренди через evaluate_trends.",
                        "Запланувати кампанію через schedule_campaign.",
                    ],
                    reasoning="Тематичний пошук не повернув кандидатів.",
                )
            return ReplanDecision(action="continue", reasoning="План залишається актуальним.")
        raise TypeError(f"Непідтримувана structured schema: {self.schema}")


class ScriptedPlanExecuteLLM:
    """Відтворює коректний вибір tools, але не замінює production LLM."""

    def with_structured_output(self, schema: type) -> _StructuredScripted:
        return _StructuredScripted(schema)

    def bind_tools(self, tools: list) -> "ScriptedPlanExecuteLLM":
        self.tools = {item.name: item for item in tools}
        return self

    def invoke(self, prompt: str) -> AIMessage:
        data = _context(str(prompt))
        step = str(data.get("step", "")).lower()
        if "search_recent_videos" in step:
            topic = data.get("topic", "AI agents")
            if "без вузької теми" in step:
                topic = ""
            return self._call(
                "search_recent_videos",
                {"topic": topic, "days": 7, "region_code": "UA", "max_candidates": 20},
            )
        if "search_knowledge" in step:
            return self._call(
                "search_knowledge",
                {
                    "query": (
                        "brand safety порнографічний sexual explicit content графічне насильство "
                        "violence sensitive news war human review marketing policy"
                    ),
                    "top_k": 8,
                },
            )
        if "evaluate_trends" in step:
            documents = [hit["document"] for hit in data.get("knowledge_hits", [])]
            return self._call(
                "evaluate_trends",
                {"videos": data.get("candidates", []), "policy_documents": documents, "top_n": 10},
            )
        if "schedule_campaign" in step:
            ids = [item["video"]["video_id"] for item in data.get("final_top", [])[:5]]
            date = (datetime.now(UTC) + timedelta(days=2)).date().isoformat()
            return self._call(
                "schedule_campaign",
                {
                    "campaign_name": f"YouTube Trends — {data.get('topic') or 'General'}",
                    "video_ids": ids,
                    "planned_date": date,
                    "note": "Підготовлено Plan-and-Execute агентом після brand-safety review.",
                },
            )
        return AIMessage(content="Крок не потребує інструмента.")

    @staticmethod
    def _call(name: str, args: dict) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}],
        )


def extract_topic(request: str) -> str:
    """Витягнути тему з навчального українського запиту."""

    match = re.search(
        r"(?:\bпро\b|\bтема[:\s]+)\s*(.+?)(?:\s+за\s+останні|[,;.]|$)",
        request,
        re.I,
    )
    return match.group(1).strip() if match else "AI agents"
