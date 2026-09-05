"""Порівняльна аналітика реклами, аудиторних сегментів і funnel."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median
from typing import Any

from .models import CompetitivePost, FunnelStage, SourceType


def percentile(values: list[int], value: int | None) -> float | None:
    if value is None or not values:
        return None
    return round(sum(candidate <= value for candidate in values) / len(values), 4)


def infer_funnel(post: CompetitivePost) -> FunnelStage:
    if post.topic in {"seasonal_discount", "gift_guide"}:
        return FunnelStage.CONVERSION
    if post.topic in {"product_guide", "home_solutions"}:
        return FunnelStage.CONSIDERATION
    if post.topic in {"new_product", "gaming"}:
        return FunnelStage.INTEREST
    if post.topic in {"loyalty"}:
        return FunnelStage.RETENTION
    return FunnelStage.AWARENESS


def infer_audience(post: CompetitivePost) -> dict[str, Any]:
    mapping = {
        "seasonal_discount": ("price_sensitive_buyers", "покупці, орієнтовані на знижки"),
        "product_guide": ("comparison_shoppers", "користувачі, які порівнюють перед придбанням"),
        "contest": ("active_community", "активна спільнота бренду"),
        "new_product": ("early_adopters", "поціновувачі технологічних новинок"),
        "humor": ("entertainment_audience", "аудиторія розважального контенту"),
        "home_solutions": ("home_and_family", "сім'ї та покупці товарів для дому"),
        "loyalty": ("returning_customers", "постійні клієнти"),
        "gift_guide": ("gift_shoppers", "покупці подарунків"),
        "gaming": ("gamers", "геймери й технологічні ентузіасти"),
        "community_question": ("active_community", "активна спільнота бренду"),
    }
    segment, label = mapping.get(post.topic, ("broad_online_audience", "широка онлайн-аудиторія"))
    return {
        "segment": segment,
        "label_uk": label,
        "confidence": 0.68,
        "basis": "Inference за темою, форматом і CTA; не first-party demographics.",
    }


def enrich_posts(posts: list[CompetitivePost]) -> list[dict[str, Any]]:
    metric_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for post in posts:
        for metric in ("views", "likes", "comments", "shares"):
            value = getattr(post, metric)
            if value is not None:
                metric_groups[(post.platform.value, post.content_type, metric)].append(value)
    rows: list[dict[str, Any]] = []
    for post in posts:
        scores = {
            metric: percentile(
                metric_groups[(post.platform.value, post.content_type, metric)],
                getattr(post, metric),
            )
            for metric in ("views", "likes", "comments", "shares")
        }
        usable = [score for score in scores.values() if score is not None]
        funnel = infer_funnel(post)
        rows.append({
            **post.model_dump(mode="json"),
            "metric_percentiles": scores,
            "normalized_score": round(mean(usable), 4) if usable else 0.0,
            "funnel_stage": funnel.value,
            "audience_inference": infer_audience(post),
            "conversion_signal_score": round(mean(
                value for value in (scores["comments"], scores["shares"], scores["likes"]) if value is not None
            ), 4),
        })
    return rows


def _top(rows: list[dict[str, Any]], metric: str, limit: int, *, ads_only: bool = False) -> list[dict[str, Any]]:
    candidates = [
        row for row in rows
        if row.get(metric) is not None
        and (not ads_only or (row["source_type"] == SourceType.PAID_AD.value and row["ad_status"] == "confirmed"))
    ]
    fields = (
        "brand", "platform", "post_id", "topic", "content_type", "source_type",
        "ad_status", "ad_evidence", "confidence", metric, "url",
    )
    return [
        {key: row[key] for key in fields}
        for row in sorted(candidates, key=lambda item: item[metric], reverse=True)[:limit]
    ]


def analyze_competitors(posts: list[CompetitivePost], top_k: int = 5) -> dict[str, Any]:
    rows = enrich_posts(posts)
    brands = sorted({row["brand"] for row in rows})
    brand_summary: dict[str, Any] = {}
    for brand in brands:
        subset = [row for row in rows if row["brand"] == brand]
        ads = [row for row in subset if row["source_type"] == "paid_ad" and row["ad_status"] == "confirmed"]
        brand_summary[brand] = {
            "post_count": len(subset),
            "confirmed_ads": len(ads),
            "median_likes": median([row["likes"] for row in subset if row["likes"] is not None]),
            "median_views": median([row["views"] for row in subset if row["views"] is not None]),
            "median_shares": median([row["shares"] for row in subset if row["shares"] is not None]),
            "average_normalized_score": round(mean(row["normalized_score"] for row in subset), 4),
            "funnel_distribution": dict(Counter(row["funnel_stage"] for row in subset)),
            "top_topics": [item[0] for item in Counter(row["topic"] for row in subset).most_common(5)],
        }
    themes: list[dict[str, Any]] = []
    for topic in sorted({row["topic"] for row in rows}):
        topic_rows = [row for row in rows if row["topic"] == topic]
        by_brand = {
            brand: round(mean(row["normalized_score"] for row in topic_rows if row["brand"] == brand), 4)
            for brand in brands
            if any(row["brand"] == brand for row in topic_rows)
        }
        winner = max(by_brand, key=by_brand.get)
        themes.append({
            "topic": topic,
            "brands": len(by_brand),
            "leader": winner,
            "leader_score": by_brand[winner],
            "brand_scores": by_brand,
            "dominant_format": Counter(row["content_type"] for row in topic_rows).most_common(1)[0][0],
            "audience": topic_rows[0]["audience_inference"],
            "funnel_stage": topic_rows[0]["funnel_stage"],
        })
    themes.sort(key=lambda item: (item["leader_score"], item["brands"]), reverse=True)
    ad_rankings = {
        "top_by_views": _top(rows, "views", top_k, ads_only=True),
        "top_by_likes": _top(rows, "likes", top_k, ads_only=True),
        "top_by_comments": _top(rows, "comments", top_k, ads_only=True),
        "top_by_shares": _top(rows, "shares", top_k, ads_only=True),
        "top_by_normalized_score": _top(rows, "normalized_score", top_k, ads_only=True),
    }
    recommendations = []
    for item in themes[:5]:
        rozetka_score = item["brand_scores"].get("rozetka", 0.0)
        gap = round(item["leader_score"] - rozetka_score, 4)
        recommendations.append({
            "topic": item["topic"],
            "action": "experiment" if gap > 0.1 else "scale",
            "recommended_format": item["dominant_format"],
            "funnel_stage": item["funnel_stage"],
            "audience": item["audience"],
            "leader": item["leader"],
            "rozetka_score": rozetka_score,
            "opportunity_gap": gap,
            "reason": (
                "Конкурентний лідер має помітно вищий нормалізований результат; потрібен контрольований A/B-тест."
                if gap > 0.1 else
                "ROZETKA вже близька до лідера; патерн можна масштабувати після перевірки якості взаємодій."
            ),
            "confidence": round(min(0.9, 0.55 + item["brands"] * 0.06), 2),
        })
    return {
        "methodology": {
            "normalization": "Percentile всередині однакової платформи та формату.",
            "advertising": "У рекламні TOP входять лише записи paid_ad із confirmed evidence.",
            "audience": "Сегменти є inference, а не фактичною демографією.",
            "conversion": "Без first-party clicks/purchases використовується conversion_signal_score.",
        },
        "brand_summary": brand_summary,
        "ad_rankings": ad_rankings,
        "theme_comparison": themes,
        "recommendations": recommendations,
        "posts": rows,
        "limitations": [
            "Fixture є синтетичним навчальним snapshot, а не поточною статистикою брендів.",
            "Без рекламних кабінетів недоступні spend, CTR, CPA, ROAS і фактичні конверсії.",
            "Висновки про аудиторію є тематичними inference з указаним confidence.",
        ],
    }
