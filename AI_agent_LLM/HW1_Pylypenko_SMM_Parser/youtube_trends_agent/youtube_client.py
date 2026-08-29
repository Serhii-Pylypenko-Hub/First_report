"""Клієнти YouTube: публічний HTML та відтворюваний fixture-режим."""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator, Protocol
from urllib.parse import quote_plus

import requests


class YouTubeClientError(RuntimeError):
    """Зрозуміла доменна помилка клієнта YouTube."""


class YouTubeClient(Protocol):
    """Контракт джерела даних для tools."""

    source_mode: str

    def search_recent(
        self,
        *,
        topic: str,
        days: int,
        region_code: str,
        max_candidates: int,
    ) -> list[dict]: ...

    def fetch_statistics(self, video_ids: list[str]) -> list[dict]: ...


def parse_iso8601_duration(value: str) -> int | None:
    """Перетворити просту YouTube ISO-8601 duration у секунди."""

    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        value or "",
    )
    if not match:
        return None
    parts = {key: int(number or 0) for key, number in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def _extract_balanced_json(text: str, marker: str) -> dict:
    """Витягнути JSON-об'єкт після маркера без крихкого regex по всьому HTML."""

    marker_index = text.find(marker)
    if marker_index < 0:
        raise ValueError(f"Маркер {marker!r} не знайдено")
    start = text.find("{", marker_index + len(marker))
    if start < 0:
        raise ValueError("Початок ytInitialData не знайдено")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise ValueError("Незавершений JSON ytInitialData")


def extract_initial_data(html: str) -> dict:
    """Знайти ytInitialData у кількох відомих формах публічної сторінки."""

    errors = []
    for marker in ("var ytInitialData =", "window[\"ytInitialData\"] =", "ytInitialData ="):
        try:
            return _extract_balanced_json(html, marker)
        except (ValueError, json.JSONDecodeError) as error:
            errors.append(str(error))
    raise YouTubeClientError("YouTube не повернув доступну структуру ytInitialData: " + "; ".join(errors))


def walk_video_renderers(value: object) -> Iterator[dict]:
    """Рекурсивно знайти відеокартки незалежно від контейнера сторінки."""

    if isinstance(value, dict):
        for key in ("videoRenderer", "gridVideoRenderer", "compactVideoRenderer"):
            renderer = value.get(key)
            if isinstance(renderer, dict):
                yield renderer
        for child in value.values():
            yield from walk_video_renderers(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_video_renderers(child)


def text_value(value: object) -> str:
    """Зібрати текст YouTube runs/simpleText у звичайний рядок."""

    if not isinstance(value, dict):
        return ""
    if value.get("simpleText"):
        return str(value["simpleText"])
    return "".join(str(run.get("text", "")) for run in value.get("runs", []) if isinstance(run, dict))


def parse_compact_number(value: str) -> int:
    """Розпізнати 1.2M, 850K, 1,2 млн, 12 тис. та звичайні числа."""

    normalized = value.lower().replace("\u00a0", " ").replace("views", "").replace("переглядів", "")
    normalized = normalized.replace("просмотров", "").replace("view", "").strip()
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|m|b|тис\.?|тыс\.?|млн|млрд)?", normalized)
    if not match:
        return 0
    number = float(match.group(1).replace(",", "."))
    suffix = match.group(2) or ""
    multiplier = {
        "k": 1_000,
        "тис": 1_000,
        "тис.": 1_000,
        "тыс": 1_000,
        "тыс.": 1_000,
        "m": 1_000_000,
        "млн": 1_000_000,
        "b": 1_000_000_000,
        "млрд": 1_000_000_000,
    }.get(suffix, 1)
    return int(number * multiplier)


def parse_age_days(value: str) -> float | None:
    """Перетворити відносну дату YouTube на вік публікації у днях."""

    normalized = value.lower().replace("streamed", "").replace("premiered", "").strip()
    if any(word in normalized for word in ("just now", "щойно", "только что")):
        return 0.0
    match = re.search(r"(\d+)\s*([a-zа-яіїєґ.]+)", normalized)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit.startswith(("minute", "min", "хв", "мин")):
        return amount / 1440
    if unit.startswith(("hour", "hr", "год", "час")):
        return amount / 24
    if unit.startswith(("day", "дн", "день")):
        return float(amount)
    if unit.startswith(("week", "тиж", "нед")):
        return float(amount * 7)
    if unit.startswith(("month", "міс", "мес")):
        return float(amount * 30)
    return None


def parse_duration_text(value: str) -> int | None:
    parts = value.strip().split(":")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


class YouTubeHTMLClient:
    """Read-only parser публічного YouTube HTML без API-ключа."""

    source_mode = "html"

    def __init__(self, timeout_seconds: float = 15.0, max_html_bytes: int = 8_000_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_html_bytes = max_html_bytes
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self._cache: dict[str, dict] = {}

    def _download(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.Timeout as error:
            raise YouTubeClientError("Публічна сторінка YouTube не відповіла в межах timeout") from error
        except requests.RequestException as error:
            raise YouTubeClientError(f"Не вдалося завантажити YouTube HTML: {error}") from error
        content = response.content[: self.max_html_bytes]
        return content.decode(response.encoding or "utf-8", errors="replace")

    def search_recent(
        self,
        *,
        topic: str,
        days: int,
        region_code: str,
        max_candidates: int,
    ) -> list[dict]:
        if topic:
            urls = [f"https://www.youtube.com/results?search_query={quote_plus(topic)}&hl=en&gl={region_code}"]
        else:
            urls = [
                f"https://www.youtube.com/feed/trending?hl=en&gl={region_code}",
                f"https://www.youtube.com/?hl=en&gl={region_code}",
                f"https://www.youtube.com/results?search_query=music&hl=en&gl={region_code}",
                f"https://www.youtube.com/results?search_query=news&hl=en&gl={region_code}",
                f"https://www.youtube.com/results?search_query=sports&hl=en&gl={region_code}",
                f"https://www.youtube.com/results?search_query=technology&hl=en&gl={region_code}",
            ]
        now = datetime.now(UTC)
        videos: list[dict] = []
        seen: set[str] = set()
        for url in urls:
            initial_data = extract_initial_data(self._download(url))
            for renderer in walk_video_renderers(initial_data):
                video_id = str(renderer.get("videoId") or "")
                if not video_id or video_id in seen:
                    continue
                age_text = text_value(renderer.get("publishedTimeText"))
                age_days = parse_age_days(age_text)
                if age_days is None or age_days > days:
                    continue
                title = text_value(renderer.get("title")) or "Untitled video"
                channel = text_value(renderer.get("ownerText")) or text_value(renderer.get("longBylineText"))
                views_text = text_value(renderer.get("viewCountText")) or text_value(renderer.get("shortViewCountText"))
                description = text_value(renderer.get("descriptionSnippet"))
                duration = text_value(renderer.get("lengthText"))
                row = {
                    "video_id": video_id,
                    "title": title[:300],
                    "channel_title": (channel or "Unknown channel")[:200],
                    "published_at": (now - timedelta(days=age_days)).isoformat(),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "description": description[:1000],
                    "views": parse_compact_number(views_text),
                    "duration_seconds": parse_duration_text(duration),
                    "trend_score": 0.0,
                }
                videos.append(row)
                self._cache[video_id] = row
                seen.add(video_id)
                if len(videos) >= max_candidates:
                    break
            if topic or len(videos) >= max_candidates:
                break
        return videos

    def fetch_statistics(self, video_ids: list[str]) -> list[dict]:
        # Пошукова/трендова сторінка вже містить доступні без API публічні метрики.
        return [dict(self._cache[video_id]) for video_id in video_ids if video_id in self._cache]


class FixtureYouTubeClient:
    """Локальне джерело, яке імітує отримання даних без мережі та квоти."""

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
        query_terms = {
            token.lower()
            for token in re.findall(r"[\wА-Яа-яІіЇїЄєҐґ-]{2,}", topic, flags=re.UNICODE)
        }
        result = []
        for raw in self._rows:
            age = float(raw.get("published_days_ago", 0))
            if age > days:
                continue
            searchable = " ".join(
                [
                    str(raw.get("title", "")),
                    str(raw.get("description", "")),
                    " ".join(raw.get("tags", [])),
                ]
            ).lower()
            searchable_terms = {
                token.lower()
                for token in re.findall(
                    r"[\wА-Яа-яІіЇїЄєҐґ-]{2,}", searchable, flags=re.UNICODE
                )
            }
            if query_terms and not query_terms.intersection(searchable_terms):
                continue
            published_at = self.now - timedelta(days=age)
            result.append(
                {
                    "video_id": raw["video_id"],
                    "title": raw["title"],
                    "channel_title": raw["channel_title"],
                    "published_at": published_at.isoformat(),
                    "url": f"https://www.youtube.com/watch?v={raw['video_id']}",
                    "description": str(raw.get("description", ""))[:1000],
                    "views": int(raw.get("views", 0)),
                    "duration_seconds": int(raw.get("duration_seconds", 0)),
                    "trend_score": 0.0,
                }
            )
        result.sort(key=lambda row: row["views"], reverse=True)
        return result[:max_candidates]

    def fetch_statistics(self, video_ids: list[str]) -> list[dict]:
        wanted = set(video_ids)
        all_recent = self.search_recent(
            topic="",
            days=30,
            region_code="UA",
            max_candidates=50,
        )
        return [row for row in all_recent if row["video_id"] in wanted]


def compute_trend_scores(videos: list[dict], *, days: int, now: datetime | None = None) -> list[dict]:
    """Додати порівнюваний score: перегляди 85% і свіжість 15%."""

    if not videos:
        return []
    current = now or datetime.now(UTC)
    max_log_views = max(math.log1p(int(row.get("views", 0))) for row in videos) or 1.0
    enriched = []
    for source in videos:
        row = dict(source)
        published_at = datetime.fromisoformat(str(row["published_at"]).replace("Z", "+00:00"))
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        age_days = max(0.0, (current - published_at).total_seconds() / 86400)
        freshness = max(0.0, 1.0 - age_days / max(days, 1))
        view_score = math.log1p(int(row.get("views", 0))) / max_log_views
        score = 0.85 * view_score + 0.15 * freshness
        row["trend_score"] = round(score, 4)
        enriched.append(row)
    return enriched
