"""Чотири структуровані tools для ReAct-агента."""

from __future__ import annotations

import json
import re
from collections import Counter

from langchain_core.tools import BaseTool, tool

from .models import (
    AnalyzeTopicSignalsInput,
    EnrichVideoStatisticsInput,
    RankTrendingVideosInput,
    SearchRecentVideosInput,
    VideoRecord,
)
from .store import TrendDataStore
from .youtube_client import YouTubeClient, compute_trend_scores


STOPWORDS = {
    "about", "after", "agents", "with", "from", "into", "your", "this", "that", "video",
    "youtube", "новий", "нова", "нове", "відео", "огляд", "топ", "для", "про", "через", "який",
    "яка", "які", "та", "або", "the", "and", "how", "why", "what",
}


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _ranked_row(row: dict, rank: int) -> dict:
    return {
        "rank": rank,
        "video_id": row["video_id"],
        "title": row["title"],
        "channel_title": row["channel_title"],
        "published_at": row["published_at"],
        "url": row["url"],
        "views": row["views"],
        "trend_score": row["trend_score"],
    }


def build_tools(client: YouTubeClient, store: TrendDataStore) -> list[BaseTool]:
    """Створити tools, прив'язані до клієнта та сховища одного запуску."""

    @tool("search_recent_videos", args_schema=SearchRecentVideosInput)
    def search_recent_videos(
        topic: str = "",
        days: int = 7,
        region_code: str = "UA",
        max_candidates: int = 50,
    ) -> str:
        """Знайти свіжі YouTube-відео для аналізу трендів.

        Використовуйте ПЕРШИМ. Порожня topic означає загальні тренди регіону.
        Для тематичних трендів передайте тему користувача. Інструмент повертає
        dataset_id; його треба використати в наступних tools. Не вигадуйте ID.
        """

        videos = client.search_recent(
            topic=topic,
            days=days,
            region_code=region_code,
            max_candidates=max_candidates,
        )
        validated = [VideoRecord.model_validate(row).model_dump(mode="json") for row in videos]
        query = {
            "topic": topic,
            "days": days,
            "region_code": region_code,
            "max_candidates": max_candidates,
        }
        dataset_id = store.create(query=query, videos=validated, source_mode=client.source_mode)
        return _json(
            {
                "result_type": "search",
                "dataset_id": dataset_id,
                "mode": "thematic" if topic else "general",
                "topic": topic,
                "candidates_found": len(validated),
                "sample": [
                    {"video_id": row["video_id"], "title": row["title"]}
                    for row in validated[:5]
                ],
                "next_action": "Call enrich_video_statistics with this dataset_id.",
            }
        )

    @tool("enrich_video_statistics", args_schema=EnrichVideoStatisticsInput)
    def enrich_video_statistics(dataset_id: str) -> str:
        """Додати перегляди, лайки, тривалість і trend score.

        Використовуйте ПІСЛЯ search_recent_videos і ДО ранжування. Передавайте
        точний dataset_id із попереднього результату. Інструмент читає лише
        публічні метрики й нічого не змінює на YouTube.
        """

        dataset = store.get(dataset_id)
        video_ids = [row["video_id"] for row in dataset["videos"]]
        detail_rows = client.fetch_statistics(video_ids)
        details = {row["video_id"]: row for row in detail_rows}
        merged = []
        for source in dataset["videos"]:
            row = {**source, **details.get(source["video_id"], {})}
            merged.append(VideoRecord.model_validate(row).model_dump(mode="json"))
        scored = compute_trend_scores(merged, days=int(dataset["query"]["days"]))
        validated = [VideoRecord.model_validate(row).model_dump(mode="json") for row in scored]
        store.update(dataset_id, videos=validated, statistics_enriched=True)
        return _json(
            {
                "result_type": "statistics",
                "dataset_id": dataset_id,
                "videos_enriched": len(validated),
                "metrics": ["views", "duration_seconds", "trend_score"],
                "next_action": "Call rank_trending_videos for trend_score and views.",
            }
        )

    @tool("rank_trending_videos", args_schema=RankTrendingVideosInput)
    def rank_trending_videos(
        dataset_id: str,
        metrics: list[str] | None = None,
        top_n: int = 20,
    ) -> str:
        """Побудувати топ відео з прямими посиланнями.

        Використовуйте лише після enrich_video_statistics. Для повного звіту
        запитайте два рейтинги: trend_score і views. top_n не більше 20.
        """

        dataset = store.get(dataset_id)
        if not dataset["statistics_enriched"]:
            raise ValueError("Спочатку викличте enrich_video_statistics")
        selected_metrics = metrics or ["trend_score", "views"]
        rankings: dict[str, list[dict]] = {}
        for metric in selected_metrics:
            sorted_rows = sorted(dataset["videos"], key=lambda row: row[metric], reverse=True)[:top_n]
            rankings[metric] = [_ranked_row(row, rank) for rank, row in enumerate(sorted_rows, 1)]
        store.update(dataset_id, rankings=rankings)
        return _json(
            {
                "result_type": "rankings",
                "dataset_id": dataset_id,
                "top_n": top_n,
                "rankings": rankings,
                "next_action": "Call analyze_topic_signals, then provide the final answer.",
            }
        )

    @tool("analyze_topic_signals", args_schema=AnalyzeTopicSignalsInput)
    def analyze_topic_signals(dataset_id: str, top_n: int = 10) -> str:
        """Знайти повторювані теми та провідні канали у відео.

        Використовуйте після отримання статистики. Інструмент аналізує назви
        та описи без завантаження коментарів і повертає сигнали для підсумку.
        """

        dataset = store.get(dataset_id)
        words: list[str] = []
        channels: Counter[str] = Counter()
        for row in dataset["videos"]:
            channels[row["channel_title"]] += 1
            tokens = re.findall(
                r"[A-Za-zА-Яа-яІіЇїЄєҐґ][\wА-Яа-яІіЇїЄєҐґ-]{2,}",
                f"{row['title']} {row.get('description', '')}",
                flags=re.UNICODE,
            )
            words.extend(token.lower() for token in tokens if token.lower() not in STOPWORDS)
        signals = {
            "trend_terms": [term for term, _ in Counter(words).most_common(top_n)],
            "leading_channels": [name for name, _ in channels.most_common(top_n)],
        }
        store.update(dataset_id, signals=signals)
        return _json({"result_type": "signals", "dataset_id": dataset_id, **signals})

    return [
        search_recent_videos,
        enrich_video_statistics,
        rank_trending_videos,
        analyze_topic_signals,
    ]
