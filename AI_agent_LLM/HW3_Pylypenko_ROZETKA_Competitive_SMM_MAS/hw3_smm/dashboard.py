"""Таблиці та matplotlib-дашборди з українськими підписами."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


BRAND_LABELS = {
    "rozetka": "ROZETKA", "comfy": "COMFY", "allo": "ALLO",
    "foxtrot": "Фокстрот", "epicentr": "Епіцентр",
}
FUNNEL_LABELS = {
    "awareness": "Обізнаність", "interest": "Інтерес", "consideration": "Розгляд",
    "conversion": "Конверсія", "retention": "Утримання",
}


def brand_table(analysis: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for brand, item in analysis["brand_summary"].items():
        rows.append({
            "Бренд": BRAND_LABELS.get(brand, brand),
            "Публікацій": item["post_count"],
            "Підтвердженої реклами": item["confirmed_ads"],
            "Медіана переглядів": item["median_views"],
            "Медіана вподобань": item["median_likes"],
            "Медіана поширень": item["median_shares"],
            "Середній нормалізований бал": item["average_normalized_score"],
        })
    return pd.DataFrame(rows)


def ad_ranking_table(analysis: dict[str, Any], ranking: str = "top_by_normalized_score") -> pd.DataFrame:
    labels = {
        "brand": "Бренд", "platform": "Платформа", "post_id": "ID публікації",
        "topic": "Тема", "content_type": "Формат", "source_type": "Тип джерела",
        "normalized_score": "Нормалізований бал", "views": "Перегляди",
        "likes": "Вподобання", "comments": "Коментарі", "shares": "Поширення", "url": "Посилання",
    }
    frame = pd.DataFrame(analysis["ad_rankings"][ranking])
    if frame.empty:
        return frame
    frame["brand"] = frame["brand"].map(lambda value: BRAND_LABELS.get(value, value))
    return frame.rename(columns=labels)


def create_dashboards(analysis: dict[str, Any]):
    brand = brand_table(analysis)
    fig1, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for axis, column, title in zip(
        axes,
        ("Медіана переглядів", "Медіана вподобань", "Медіана поширень"),
        ("Перегляди", "Вподобання", "Поширення"),
    ):
        axis.bar(brand["Бренд"], brand[column], color="#38a169")
        axis.set_title(f"Медіанні {title.lower()}")
        axis.tick_params(axis="x", rotation=35)
        axis.grid(axis="y", alpha=.25)
    fig1.suptitle("Дашборд 1. Порівняння доступних метрик брендів")
    fig1.tight_layout()

    funnel_rows = []
    for brand_name, item in analysis["brand_summary"].items():
        for stage, count in item["funnel_distribution"].items():
            funnel_rows.append({"Бренд": BRAND_LABELS.get(brand_name, brand_name), "Етап": FUNNEL_LABELS.get(stage, stage), "Кількість": count})
    funnel = pd.DataFrame(funnel_rows).pivot(index="Бренд", columns="Етап", values="Кількість").fillna(0)
    fig2, axis2 = plt.subplots(figsize=(11, 5))
    funnel.plot(kind="bar", stacked=True, ax=axis2, colormap="viridis")
    axis2.set_title("Дашборд 2. Контент брендів за етапами воронки")
    axis2.set_ylabel("Кількість публікацій")
    axis2.tick_params(axis="x", rotation=25)
    fig2.tight_layout()

    themes = pd.DataFrame([
        {"Тема": row["topic"], "Лідер": BRAND_LABELS.get(row["leader"], row["leader"]), "Бал лідера": row["leader_score"], "Етап": FUNNEL_LABELS.get(row["funnel_stage"], row["funnel_stage"])}
        for row in analysis["theme_comparison"]
    ])
    fig3, axis3 = plt.subplots(figsize=(12, 5))
    axis3.barh(themes["Тема"], themes["Бал лідера"], color="#3182ce")
    axis3.invert_yaxis()
    axis3.set_xlim(0, 1)
    axis3.set_title("Дашборд 3. Найсильніші конкурентні теми")
    axis3.set_xlabel("Нормалізований бал тематичного лідера")
    fig3.tight_layout()
    return fig1, fig2, fig3
