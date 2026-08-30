"""П'ять доменних tools зі стандартним JSON-контрактом."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

from langchain_core.tools import BaseTool, tool

from .data_source import FIXTURE_SNAPSHOT_AT, SocialDataSource
from .knowledge import SMMKnowledgeBase
from .models import (
    AnalyzePatternsInput,
    CollectPublicPostsInput,
    ExportReportInput,
    KnowledgeSearchInput,
    LoadFixturePostsInput,
    SocialPost,
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _ok(data: object) -> str:
    return _json({"status": "ok", "data": data})


def _error(code: str, message: str, *, details: dict | None = None) -> str:
    return _json(
        {
            "status": "error",
            "error": {"code": code, "message": message, "details": details or {}},
        }
    )


def _percentile(values: list[int], value: int | None) -> float | None:
    if value is None or not values:
        return None
    return sum(item <= value for item in values) / len(values)


def _funnel(post: SocialPost) -> str:
    text = post.text.casefold()
    if post.topic in {"discount", "gift_guide"} or any(word in text for word in ["зниж", "промокод"]):
        return "conversion_oriented"
    if post.topic in {"contest", "community_question", "humor"}:
        return "engagement"
    if post.topic in {"product_guide", "education_tech"}:
        return "consideration"
    if post.topic == "brand_news":
        return "awareness"
    return "awareness"


def _audience(post: SocialPost) -> dict:
    text = f"{post.topic} {post.text}".casefold()
    if any(word in text for word in ["навчан", "ноутбук", "школ"]):
        return {"segment": "студенти, батьки та молоді спеціалісти", "age_inferred": "18–44"}
    if any(word in text for word in ["кух", "дім", "батьк"]):
        return {"segment": "домогосподарства та сімейна аудиторія", "age_inferred": "25–54"}
    if any(word in text for word in ["playstation", "гаджет", "смартфон", "gaming"]):
        return {"segment": "технологічно активна аудиторія", "age_inferred": "16–39"}
    if post.topic == "fashion":
        return {"segment": "міська fashion-аудиторія", "age_inferred": "18–39"}
    return {"segment": "широка українська онлайн-аудиторія", "age_inferred": "18–54"}


def analyze_posts(posts: list[SocialPost], period_days: int, top_k: int) -> dict:
    """Побудувати окремі platform-звіти й обережне cross-platform порівняння."""

    grouped: dict[str, list[SocialPost]] = defaultdict(list)
    for post in posts:
        grouped[post.platform].append(post)

    enriched: list[dict] = []
    platform_summaries: dict[str, dict] = {}
    for platform in ["instagram", "facebook", "threads", "telegram"]:
        platform_posts = grouped.get(platform, [])
        metric_values = {
            name: [int(getattr(item, name)) for item in platform_posts if getattr(item, name) is not None]
            for name in ["views", "likes", "comments", "shares"]
        }
        platform_rows: list[dict] = []
        for post in platform_posts:
            percentiles = {
                name: _percentile(metric_values[name], getattr(post, name))
                for name in metric_values
            }
            usable = [value for value in percentiles.values() if value is not None]
            normalized_score = round(mean(usable), 4) if usable else 0.0
            audience = _audience(post)
            row = {
                **post.model_dump(mode="json"),
                "funnel_stage": _funnel(post),
                "audience_inference": {
                    **audience,
                    "region_inferred": "Україна",
                    "confidence": 0.62,
                    "basis": "тема, формат і текст публікації; не first-party demographics",
                },
                "metric_percentiles": percentiles,
                "normalized_score": normalized_score,
            }
            platform_rows.append(row)
            enriched.append(row)

        def top(metric: str) -> list[dict]:
            available = [row for row in platform_rows if row.get(metric) is not None]
            return [
                {
                    "post_id": row["post_id"],
                    "value": row[metric],
                    "content_type": row["content_type"],
                    "topic": row["topic"],
                    "url": row["url"],
                }
                for row in sorted(available, key=lambda item: item[metric], reverse=True)[:top_k]
            ]

        dates = sorted(datetime.fromisoformat(row["published_at"]) for row in platform_rows)
        intervals = [(dates[index] - dates[index - 1]).days for index in range(1, len(dates))]
        platform_summaries[platform] = {
            "post_count": len(platform_rows),
            "posts_per_week": round(len(platform_rows) / period_days * 7, 2),
            "average_interval_days": round(mean(intervals), 2) if intervals else None,
            "views_availability": {
                status: sum(row["views_status"] == status for row in platform_rows)
                for status in ["available", "not_public", "not_applicable", "missing_in_source"]
            },
            "views_note": (
                "Video/Reels можуть мати public views; для статичних постів лічильник "
                "переглядів часто не публікується. None не означає 0 переглядів."
            ),
            "formats": {
                name: sum(row["content_type"] == name for row in platform_rows)
                for name in sorted({row["content_type"] for row in platform_rows})
            },
            "top_by_views": top("views"),
            "top_by_likes": top("likes"),
            "top_by_comments": top("comments"),
            "top_by_shares": top("shares"),
        }

    pattern_groups: dict[str, list[dict]] = defaultdict(list)
    for row in enriched:
        pattern_groups[row["topic"]].append(row)
    patterns = []
    for topic, rows in pattern_groups.items():
        average_score = round(mean(row["normalized_score"] for row in rows), 4)
        evidence_factor = 0.65 + 0.35 * min(len(rows), 3) / 3
        patterns.append(
            {
                "pattern": topic,
                "posts": len(rows),
                "average_normalized_score": average_score,
                "pattern_score": round(average_score * evidence_factor, 4),
                "evidence_level": "strong" if len(rows) >= 3 else "medium" if len(rows) == 2 else "weak_single_post",
                "platforms": sorted({row["platform"] for row in rows}),
                "formats": sorted({row["content_type"] for row in rows}),
                "dominant_funnel": max(
                    {row["funnel_stage"] for row in rows},
                    key=lambda value: sum(row["funnel_stage"] == value for row in rows),
                ),
                "example_urls": [row["url"] for row in sorted(rows, key=lambda item: item["normalized_score"], reverse=True)[:2]],
            }
        )
    patterns.sort(key=lambda item: (item["pattern_score"], item["posts"]), reverse=True)
    cross_platform_top = [
        {
            "platform": row["platform"],
            "post_id": row["post_id"],
            "topic": row["topic"],
            "content_type": row["content_type"],
            "normalized_score": row["normalized_score"],
            "url": row["url"],
        }
        for row in sorted(enriched, key=lambda item: item["normalized_score"], reverse=True)[:top_k]
    ]
    top_patterns = patterns[:5]
    strongest = top_patterns[0] if top_patterns else None
    executive_summary = [
        f"За 30 днів проаналізовано {len(enriched)} публікації на {sum(bool(grouped.get(name)) for name in grouped)} платформах.",
        (
            f"Найсильніший повторюваний патерн — {strongest['pattern']} "
            f"(score={strongest['pattern_score']}, posts={strongest['posts']})."
            if strongest
            else "Повторюваних патернів не знайдено."
        ),
        "Instagram, Facebook і Telegram мають дані snapshot; офіційний Threads-профіль потребує окремого підтвердження.",
        "Аудиторні сегменти є inference за темою та форматом, а не фактичною демографією платформи.",
    ]
    recommendations = [
        "Масштабувати contest-механіки, але оцінювати якість коментарів окремо перед production-рішенням.",
        "Підтримувати product guides у Reels/video/carousel: патерн повторюється на кількох платформах.",
        "Для discount-контенту тестувати різні формати й CTA, не порівнюючи сирі views між платформами.",
        "Humor розглядати як перспективний експеримент, а не доведений патерн, доки є лише один сильний пост.",
        "Перед стратегією для Threads вручну підтвердити офіційний профіль ROZETKA та доступність публічних метрик.",
    ]
    generated_at = (
        FIXTURE_SNAPSHOT_AT.isoformat()
        if enriched and all(row.get("source_mode") == "fixture" for row in enriched)
        else datetime.now(UTC).isoformat()
    )
    return {
        "brand": "ROZETKA",
        "period_days": period_days,
        "generated_at": generated_at,
        "methodology": (
            "Сирі метрики порівнюються лише всередині платформи; cross-platform top "
            "використовує середнє percentile доступних метрик. Аудиторія є inference."
        ),
        "platform_summaries": platform_summaries,
        "posts": enriched,
        "top_5_patterns": top_patterns,
        "cross_platform_top": cross_platform_top,
        "executive_summary": executive_summary,
        "recommendations": recommendations,
        "coverage_gaps": [
            platform for platform, summary in platform_summaries.items() if summary["post_count"] == 0
        ],
        "limitations": [
            "Fixture metrics є навчальним snapshot, а не поточною статистикою ROZETKA.",
            "Reach, saves та реальні demographics недоступні без first-party API.",
            "Тексти коментарів не збираються; використовується лише їх кількість.",
        ],
    }


def build_tools(
    *,
    source: SocialDataSource,
    knowledge_base: SMMKnowledgeBase,
    project_root: str | Path,
) -> list[BaseTool]:
    """Створити tools, прив'язані до джерел, RAG та безпечного каталогу."""

    root = Path(project_root).resolve()

    @tool("collect_public_posts", args_schema=CollectPublicPostsInput)
    def collect_public_posts(
        brand: str,
        platform: str,
        profile_url: str,
        period_days: int = 30,
    ) -> str:
        """Спробувати light HTML/metadata збір публікацій платформи без API."""

        try:
            posts = source.collect_public(platform, profile_url, period_days)  # type: ignore[arg-type]
            return _ok({"platform": platform, "source_mode": "public_html", "posts": posts})
        except Exception as exc:
            return _error(
                str(exc),
                "Публічний збір недоступний; агент може обрати fixture fallback.",
                details={"platform": platform, "profile_url": profile_url},
            )

    @tool("load_fixture_posts", args_schema=LoadFixturePostsInput)
    def load_fixture_posts(brand: str, platform: str, period_days: int = 30) -> str:
        """Завантажити відтворюваний snapshot після контрольованої помилки live-збору."""

        posts = source.load_fixture(platform, period_days)  # type: ignore[arg-type]
        return _ok(
            {
                "platform": platform,
                "source_mode": "fixture",
                "posts": posts,
                "notice": "Навчальний snapshot; не поточні production-дані.",
            }
        )

    @tool("knowledge_search", args_schema=KnowledgeSearchInput)
    def knowledge_search(query: str, top_k: int = 5) -> str:
        """Знайти правила SMM-воронки, метрик, аудиторії та нормалізації у ChromaDB."""

        return _ok({"query": query, "hits": knowledge_base.search(query, top_k)})

    @tool("analyze_marketing_patterns", args_schema=AnalyzePatternsInput)
    def analyze_marketing_patterns(
        posts: list[SocialPost],
        period_days: int = 30,
        top_k: int = 5,
    ) -> str:
        """Знайти топи, частоту, funnel, inferred-аудиторію та 5 контентних патернів."""

        validated = [SocialPost.model_validate(item) for item in posts]
        return _ok(analyze_posts(validated, period_days, top_k))

    @tool("export_smm_report", args_schema=ExportReportInput)
    def export_smm_report(path: str, report: dict) -> str:
        """Записати фінальний SMM-звіт — РИЗИКОВА write-операція лише після HITL."""

        target = (root / path).resolve()
        if root not in target.parents:
            return _error("PATH_OUTSIDE_PROJECT", "Шлях виходить за межі каталогу проєкту.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_json(report), encoding="utf-8")
        return _ok(
            {
                "path": str(target),
                "bytes": target.stat().st_size,
                "exported_at": datetime.now(UTC).isoformat(),
            }
        )

    return [
        collect_public_posts,
        load_fixture_posts,
        knowledge_search,
        analyze_marketing_patterns,
        export_smm_report,
    ]
