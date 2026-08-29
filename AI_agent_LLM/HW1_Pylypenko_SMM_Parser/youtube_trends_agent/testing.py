"""Детермінована модель лише для unit/integration tests без витрат API."""

from __future__ import annotations

import json
import re
import time

from langchain_core.messages import AIMessage, ToolMessage


class ScriptedReActLLM:
    """Відтворює коректний tool-selection ланцюжок для тестів графа.

    Production і notebook використовують Gemini. Цей клас не підміняє live demo,
    а робить автоматичні тести стабільними та незалежними від квоти.
    """

    def bind_tools(self, tools: list) -> "ScriptedReActLLM":
        self.tool_names = [item.name for item in tools]
        return self

    def invoke(self, messages: list) -> AIMessage:
        last = messages[-1]
        if not isinstance(last, ToolMessage):
            query = str(last.content)
            topic_match = re.search(
                r"(?:про|тема[:\s]+)\s*(.+?)(?:\s+за\s+останні|[,;.]|$)",
                query,
                flags=re.IGNORECASE,
            )
            topic = topic_match.group(1).strip() if topic_match else ""
            if "загаль" in query.lower():
                topic = ""
            return self._call(
                "search_recent_videos",
                {"topic": topic, "days": 7, "region_code": "UA", "max_candidates": 50},
                "call-search",
            )

        payload = json.loads(str(last.content))
        dataset_id = payload.get("dataset_id")
        result_type = payload.get("result_type")
        if result_type == "search":
            return self._call(
                "enrich_video_statistics",
                {"dataset_id": dataset_id},
                "call-statistics",
            )
        if result_type == "statistics":
            return self._call(
                "rank_trending_videos",
                {"dataset_id": dataset_id, "metrics": ["trend_score", "views"], "top_n": 20},
                "call-ranking",
            )
        if result_type == "rankings":
            return self._call(
                "analyze_topic_signals",
                {"dataset_id": dataset_id, "top_n": 10},
                "call-signals",
            )
        return AIMessage(content="Аналіз трендів завершено на основі результатів інструментів.")

    @staticmethod
    def _call(name: str, args: dict, call_id: str) -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


class LoopingToolLLM:
    """Навмисно повторює один tool call для демонстрації LoopDetector."""

    def bind_tools(self, tools: list) -> "LoopingToolLLM":
        return self

    def invoke(self, messages: list) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_recent_videos",
                    "args": {"topic": "AI", "days": 7, "region_code": "UA", "max_candidates": 20},
                    "id": f"loop-call-{len(messages)}",
                }
            ],
        )


class SlowScriptedLLM(ScriptedReActLLM):
    """Додає малу контрольовану затримку для демонстрації global timeout."""

    def invoke(self, messages: list) -> AIMessage:
        time.sleep(0.01)
        return super().invoke(messages)
