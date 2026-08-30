"""Відтворюване fixture-джерело, перевикористане з підходу ДЗ №1."""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path


class FixtureYouTubeSource:
    """Читає локальні публічноподібні дані без мережі та API-ключів."""

    source_mode = "fixture"

    def __init__(self, fixture_path: str | Path, now: datetime | None = None) -> None:
        self.fixture_path = Path(fixture_path)
        self.now = now or datetime.now(UTC)
        self._rows = json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def search_recent(
        self,
        *,
        topic: str,
        days: int,
        region_code: str,
        max_candidates: int,
    ) -> list[dict]:
        """Повернути тематичні або загальні кандидати за заданий період."""

        del region_code  # fixture однаковий для всіх регіонів
        query_terms = set(re.findall(r"[\wА-Яа-яІіЇїЄєҐґ-]{2,}", topic.lower()))
        candidates: list[dict] = []
        for raw in self._rows:
            age = float(raw.get("published_days_ago", 0))
            if age > days:
                continue
            searchable = " ".join(
                [raw.get("title", ""), raw.get("description", ""), " ".join(raw.get("tags", []))]
            ).lower()
            searchable_terms = set(re.findall(r"[\wА-Яа-яІіЇїЄєҐґ-]{2,}", searchable))
            if query_terms and not query_terms.intersection(searchable_terms):
                continue
            candidates.append(
                {
                    "video_id": raw["video_id"],
                    "title": raw["title"],
                    "channel_title": raw["channel_title"],
                    "description": raw.get("description", ""),
                    "published_at": (self.now - timedelta(days=age)).isoformat(),
                    "url": f"https://www.youtube.com/watch?v={raw['video_id']}",
                    "views": int(raw.get("views", 0)),
                    "trend_score": 0.0,
                }
            )
        return self._score(candidates, days=days)[:max_candidates]

    def _score(self, videos: list[dict], *, days: int) -> list[dict]:
        if not videos:
            return []
        max_log_views = max(math.log1p(row["views"]) for row in videos) or 1.0
        result: list[dict] = []
        for source in videos:
            row = dict(source)
            published = datetime.fromisoformat(row["published_at"])
            age_days = max(0.0, (self.now - published).total_seconds() / 86400)
            freshness = max(0.0, 1.0 - age_days / max(days, 1))
            view_score = math.log1p(row["views"]) / max_log_views
            row["trend_score"] = round(0.85 * view_score + 0.15 * freshness, 4)
            result.append(row)
        return sorted(result, key=lambda item: item["trend_score"], reverse=True)

