"""Детермінована LLM-підміна для тестів та notebook без API-ключа."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .data_source import OFFICIAL_PROFILES
from .models import Plan, ReplanDecision


def _marker_json(text: str, marker: str) -> dict:
    if marker not in text:
        return {}
    try:
        return json.loads(text.split(marker, 1)[1].strip())
    except json.JSONDecodeError:
        return {}


class _StructuredScripted:
    def __init__(self, schema: type) -> None:
        self.schema = schema

    def invoke(self, prompt: Any):
        context = _marker_json(str(prompt), "CONTEXT_JSON:")
        if self.schema is Plan:
            return Plan(
                goal=context.get("request", "Проаналізувати SMM ROZETKA за 30 днів"),
                steps=[
                    "COLLECT_PLATFORMS: зібрати Instagram, Facebook, Threads і Telegram через ReAct з fallback.",
                    "SEARCH_KNOWLEDGE: отримати правила метрик, funnel і нормалізації через Agentic RAG.",
                    "ANALYZE_PATTERNS: побудувати platform-звіти, топи, inferred-аудиторію і 5 патернів.",
                    "EXPORT_REPORT: підготувати ризиковий файловий експорт після HITL.",
                ],
            )
        if self.schema is ReplanDecision:
            if context.get("report_status") in {"exported", "rejected"}:
                return ReplanDecision(action="finish", reasoning="Експорт завершено рішенням оператора.")
            if context.get("current_step", 0) >= len(context.get("plan", [])):
                return ReplanDecision(action="finish", reasoning="Усі кроки виконано.")
            if context.get("last_stop_reason") in {"timeout", "max_steps", "repeated_tool_call"}:
                return ReplanDecision(
                    action="replan",
                    updated_steps=context.get("plan", [])[context.get("current_step", 0) :],
                    reasoning="ReAct guardrail зупинив крок; залишок плану збережено.",
                )
            return ReplanDecision(action="continue", reasoning="Результат достатній для наступного кроку.")
        raise TypeError(f"Непідтримувана structured schema: {self.schema}")


class ScriptedSMMModel:
    """Вибирає ті самі tools, які мав би обирати production LLM."""

    def with_structured_output(self, schema: type) -> _StructuredScripted:
        return _StructuredScripted(schema)

    def bind_tools(self, tools: list) -> "ScriptedSMMModel":
        self.tools = {item.name: item for item in tools}
        return self

    def invoke(self, messages: Any) -> AIMessage:
        if not isinstance(messages, list):
            return AIMessage(content="Scripted model очікує список повідомлень.")
        task: dict = {}
        observations: list[dict] = []
        for message in messages:
            if isinstance(message, HumanMessage):
                task.update(_marker_json(str(message.content), "TASK_JSON:"))
            elif isinstance(message, ToolMessage):
                try:
                    payload = json.loads(str(message.content))
                except json.JSONDecodeError:
                    payload = {"status": "error", "error": {"code": "INVALID_TOOL_JSON"}}
                observations.append(
                    {
                        "tool": message.name or "unknown",
                        "payload": payload,
                    }
                )

        operation = task.get("operation")
        if operation == "collect":
            return self._collect_decision(task, observations)
        if operation == "knowledge":
            if not any(item["tool"] == "knowledge_search" for item in observations):
                return self._call(
                    "knowledge_search",
                    {
                        "query": "SMM funnel Instagram Facebook Threads Telegram metrics normalization audience inference",
                        "top_k": 8,
                    },
                )
            return AIMessage(content="RAG-правила отримано; пошук не потрібно повторювати.")
        if operation == "analyze":
            if not any(item["tool"] == "analyze_marketing_patterns" for item in observations):
                return self._call(
                    "analyze_marketing_patterns",
                    {"posts": task.get("posts", []), "period_days": 30, "top_k": 5},
                )
            return AIMessage(content="Маркетингові патерни та platform-топи сформовано.")
        return AIMessage(content="Немає доречного інструмента для поточного кроку.")

    def _collect_decision(self, task: dict, observations: list[dict]) -> AIMessage:
        platforms = task.get("platforms", ["instagram", "facebook", "threads", "telegram"])
        for platform in platforms:
            platform_observations = [
                item
                for item in observations
                if (
                    item["payload"].get("data", {}).get("platform") == platform
                    or item["payload"].get("error", {}).get("details", {}).get("platform") == platform
                )
            ]
            successful = any(item["payload"].get("status") == "ok" for item in platform_observations)
            if successful:
                continue
            attempted_public = any(item["tool"] == "collect_public_posts" for item in platform_observations)
            if not attempted_public:
                return self._call(
                    "collect_public_posts",
                    {
                        "brand": "ROZETKA",
                        "platform": platform,
                        "profile_url": OFFICIAL_PROFILES[platform],
                        "period_days": 30,
                    },
                )
            return self._call(
                "load_fixture_posts",
                {"brand": "ROZETKA", "platform": platform, "period_days": 30},
            )
        return AIMessage(content="Збір завершено для всіх платформ із зафіксованим provenance.")

    @staticmethod
    def _call(name: str, args: dict) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[{"name": name, "args": args, "id": f"call-{name}-{args.get('platform', 'general')}"}],
        )
