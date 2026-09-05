"""Детермінований навчальний snapshot п'яти брендів; це не поточна статистика."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import Brand, CompetitivePost, Platform, SourceType


SNAPSHOT_AT = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
BRAND_SCALE = {
    Brand.ROZETKA: 1.00,
    Brand.COMFY: 0.83,
    Brand.ALLO: 0.76,
    Brand.FOXTROT: 0.64,
    Brand.EPICENTR: 0.71,
}
TOPICS = (
    ("seasonal_discount", "reel", "Знижки до 30% на техніку для навчання. Обирайте вигідно!", "conversion"),
    ("product_guide", "video", "Три ознаки, за якими легко вибрати робот-пилосос.", "consideration"),
    ("contest", "photo", "Розігруємо подарунок: поділіться улюбленим гаджетом у коментарях.", "engagement"),
    ("new_product", "carousel", "Огляд новинок тижня: функції, характеристики та сценарії використання.", "interest"),
    ("humor", "reel", "Коли заряд смартфона 1%, а зарядний пристрій залишився вдома.", "awareness"),
    ("home_solutions", "video", "П'ять рішень для зручної та енергоощадної оселі.", "consideration"),
    ("loyalty", "photo", "Бонуси для постійних клієнтів і персональні пропозиції в застосунку.", "retention"),
    ("gift_guide", "carousel", "Добірка подарунків для тих, хто любить технології.", "conversion"),
    ("gaming", "reel", "Ігровий сетап без зайвих витрат: добірка ключових компонентів.", "interest"),
    ("community_question", "text", "Яка функція смартфона для вас найважливіша?", "engagement"),
)


def build_fixture_posts() -> list[CompetitivePost]:
    posts: list[CompetitivePost] = []
    platforms = [Platform.INSTAGRAM, Platform.FACEBOOK, Platform.TELEGRAM, Platform.THREADS]
    for brand_index, brand in enumerate(Brand):
        scale = BRAND_SCALE[brand]
        for index, (topic, content_type, text, _) in enumerate(TOPICS):
            platform = platforms[index % len(platforms)]
            is_ad = index in {0, 1, 3, 7, 8}
            # Різні сильні сторони брендів створюють змістовне порівняння тем.
            affinity = 1.0
            if brand == Brand.COMFY and topic in {"humor", "home_solutions"}:
                affinity = 1.42
            elif brand == Brand.ALLO and topic in {"new_product", "gaming"}:
                affinity = 1.38
            elif brand == Brand.FOXTROT and topic in {"seasonal_discount", "loyalty"}:
                affinity = 1.34
            elif brand == Brand.EPICENTR and topic in {"home_solutions", "gift_guide"}:
                affinity = 1.45
            elif brand == Brand.ROZETKA and topic in {"contest", "product_guide"}:
                affinity = 1.31
            base = int((44_000 + index * 17_300 + brand_index * 3_100) * scale * affinity)
            static_format = content_type in {"photo", "text"}
            views = None if static_format else base * 4
            views_status = "not_applicable" if static_format else "available"
            likes = int(base * (0.17 + (index % 3) * 0.025))
            comments = int(base * (0.018 + (index % 4) * 0.006))
            shares = int(base * (0.026 + (index % 2) * 0.012))
            post_id = f"{brand.value[:3]}-{platform.value[:2]}-{index + 1:03d}"
            posts.append(CompetitivePost(
                brand=brand,
                platform=platform,
                post_id=post_id,
                published_at=SNAPSHOT_AT - timedelta(days=2 + index * 2),
                content_type=content_type,
                text=text,
                topic=topic,
                source_type=SourceType.PAID_AD if is_ad else SourceType.ORGANIC,
                ad_status="confirmed" if is_ad else "not_ad",
                ad_evidence="Навчальна fixture-позначка paid_ad" if is_ad else "",
                views=views,
                views_status=views_status,
                likes=likes,
                comments=comments,
                shares=shares,
                url=f"fixture://{brand.value}/{platform.value}/{post_id}",
                source_mode="fixture",
                confidence=0.95 if is_ad else 0.9,
                platform_metrics={"synthetic_snapshot": True},
            ))
    return posts


def fixture_payload() -> dict:
    return {
        "notice": "Синтетичний навчальний snapshot; не поточні дані брендів.",
        "snapshot_at": SNAPSHOT_AT.isoformat(),
        "posts": [post.model_dump(mode="json") for post in build_fixture_posts()],
    }


def save_fixture(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(fixture_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
