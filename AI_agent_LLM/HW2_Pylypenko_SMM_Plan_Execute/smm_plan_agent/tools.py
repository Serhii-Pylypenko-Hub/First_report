"""Чотири tools: пошук, Agentic RAG, оцінювання та ризикова дія."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .data_source import FixtureYouTubeSource
from .knowledge import BrandSafetyKnowledgeBase
from .models import (
    EvaluateTrendsInput,
    ScheduleCampaignInput,
    SearchKnowledgeInput,
    SearchRecentVideosInput,
    VideoCandidate,
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _parse_policies(policy_documents: list[str]) -> list[dict]:
    policies: list[dict] = []
    for raw in policy_documents:
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            policies.append(value)
    return policies


def build_tools(
    *,
    source: FixtureYouTubeSource,
    knowledge_base: BrandSafetyKnowledgeBase,
    action_log_path: str | Path,
) -> list[BaseTool]:
    """Створити tools, прив'язані до джерела, ChromaDB й audit log."""

    action_log = Path(action_log_path)

    @tool("search_recent_videos", args_schema=SearchRecentVideosInput)
    def search_recent_videos(
        topic: str = "",
        days: int = 7,
        region_code: str = "UA",
        max_candidates: int = 20,
    ) -> str:
        """Знайти свіжі YouTube-відео для маркетингового аналізу.

        Використовуйте для отримання кандидатів. Цей read-only tool не знає
        правил brand safety: після нього агент повинен окремо вирішити, чи
        потрібен search_knowledge.
        """

        videos = source.search_recent(
            topic=topic,
            days=days,
            region_code=region_code,
            max_candidates=max_candidates,
        )
        validated = [VideoCandidate.model_validate(row).model_dump(mode="json") for row in videos]
        return _json(
            {
                "result_type": "video_search",
                "topic": topic,
                "days": days,
                "region_code": region_code,
                "source_mode": source.source_mode,
                "candidates": validated,
            }
        )

    @tool("search_knowledge", args_schema=SearchKnowledgeInput)
    def search_knowledge(query: str, top_k: int = 6) -> str:
        """Знайти правила у ChromaDB базі знань.

        Використовуйте, коли крок потребує довідкових правил brand safety,
        заборонених тем, human review або marketing policy. Не використовуйте
        замість пошуку відео чи виконання зовнішньої дії.
        """

        hits = knowledge_base.search(query, top_k=top_k)
        return _json({"result_type": "knowledge", "query": query, "hits": hits})

    @tool("evaluate_trends", args_schema=EvaluateTrendsInput)
    def evaluate_trends(
        videos: list[VideoCandidate],
        policy_documents: list[str],
        top_n: int = 10,
    ) -> str:
        """Розподілити відео на дозволені, сумнівні та заблоковані.

        Використовуйте лише після search_recent_videos і search_knowledge.
        Класифікація спирається на retrieved policy documents. Сумнівні
        позиції не додаються до топу без рішення людини.
        """

        candidates = [VideoCandidate.model_validate(item) for item in videos]
        policies = _parse_policies(policy_documents)
        allowed: list[dict] = []
        review: list[dict] = []
        blocked: list[dict] = []
        for video in candidates:
            searchable = f"{video.title} {video.description}".lower()
            matches: list[tuple[dict, list[str]]] = []
            for policy in policies:
                keywords = [str(word).lower() for word in policy.get("keywords", [])]
                matched = [word for word in keywords if word and word in searchable]
                if matched:
                    matches.append((policy, matched))

            block_matches = [item for item in matches if item[0].get("decision") == "block"]
            review_matches = [item for item in matches if item[0].get("decision") == "review"]
            if block_matches:
                decision = "block"
                selected = block_matches
                target = blocked
            elif review_matches:
                decision = "review"
                selected = review_matches
                target = review
            else:
                decision = "allow"
                selected = []
                target = allowed

            categories = sorted({str(policy.get("category", "unknown")) for policy, _ in selected})
            policy_ids = sorted({str(policy.get("id", "")) for policy, _ in selected})
            words = sorted({word for _, matched in selected for word in matched})
            reason = (
                "Не знайдено збігів із retrieved заборонами."
                if decision == "allow"
                else f"Збіг із політикою: {', '.join(words)}."
            )
            target.append(
                {
                    "video": video.model_dump(mode="json"),
                    "decision": decision,
                    "categories": categories,
                    "reason": reason,
                    "matched_policy_ids": policy_ids,
                }
            )

        allowed.sort(key=lambda item: item["video"]["trend_score"], reverse=True)
        review.sort(key=lambda item: item["video"]["trend_score"], reverse=True)
        blocked.sort(key=lambda item: item["video"]["trend_score"], reverse=True)
        return _json(
            {
                "result_type": "evaluation",
                "approved": allowed[:top_n],
                "needs_review": review,
                "blocked": blocked,
                "top_n": top_n,
            }
        )

    @tool("schedule_campaign", args_schema=ScheduleCampaignInput)
    def schedule_campaign(
        campaign_name: str,
        video_ids: list[str],
        planned_date: str,
        note: str = "",
    ) -> str:
        """Запланувати SMM-кампанію — РИЗИКОВА зовнішня write-дія.

        Tool дозволено виконувати лише після interrupt() та явного рішення
        людини approve або edit. Сам executor не має права викликати його
        напряму без approval gate.
        """

        action = {
            "status": "scheduled",
            "campaign_name": campaign_name,
            "video_ids": video_ids,
            "planned_date": planned_date,
            "note": note,
            "executed_at": datetime.now(UTC).isoformat(),
        }
        action_log.parent.mkdir(parents=True, exist_ok=True)
        with action_log.open("a", encoding="utf-8") as stream:
            stream.write(_json(action) + "\n")
        return _json({"result_type": "campaign", **action})

    return [search_recent_videos, search_knowledge, evaluate_trends, schedule_campaign]

