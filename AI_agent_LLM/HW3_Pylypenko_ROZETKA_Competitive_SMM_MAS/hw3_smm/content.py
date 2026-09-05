"""Детермінована генерація оригінальних рекламних концепцій із доказами."""

from __future__ import annotations

from typing import Any


TEMPLATES = {
    "product_guide": "На мою думку обирати техніку простіше, коли знаєш три головні характеристики. Гортайте добірку та знайдіть свою модель у ROZETKA.",
    "seasonal_discount": "Самий вигідний час оновити техніку настав. До кінця тижня діють спеціальні пропозиції — перегляньте умови на ROZETKA.",
    "gaming": "Збери свій ігровий сетап без зайвих витрат. Порівняй ключові компоненти та обери вірне рішення на ROZETKA.",
    "home_solutions": "П'ять рішень, що допомагають економити час удома. Дивіться добірку і приймайте участь в обговоренні.",
    "gift_guide": "Добірка подарунків для тих, хто любить технології технології. Збережіть, щоб повернутися до ідей пізніше.",
}


def generate_drafts(analysis: dict[str, Any], count: int = 5) -> list[dict[str, Any]]:
    themes = analysis["theme_comparison"]
    ordered = [item["topic"] for item in themes if item["topic"] in TEMPLATES]
    ordered.extend(topic for topic in TEMPLATES if topic not in ordered)
    drafts: list[dict[str, Any]] = []
    for index, topic in enumerate(ordered[:count], start=1):
        evidence = next(item for item in themes if item["topic"] == topic)
        drafts.append({
            "draft_id": f"draft-{index:03d}",
            "target_brand": "rozetka",
            "topic": topic,
            "platform": "instagram" if index % 2 else "facebook",
            "content_type": evidence["dominant_format"],
            "funnel_stage": evidence["funnel_stage"],
            "audience_segment": evidence["audience"],
            "text": TEMPLATES[topic],
            "cta": "Переглянути пропозицію",
            "pattern_evidence": {
                "leader": evidence["leader"],
                "leader_score": evidence["leader_score"],
                "basis": "Тема і формат; текст конкурента не копіюється.",
            },
            "originality_notice": "Оригінальна навчальна чернетка на основі агрегованого патерну.",
            "expected_metric": "normalized engagement proxy",
            "confidence": 0.74,
        })
    return drafts
