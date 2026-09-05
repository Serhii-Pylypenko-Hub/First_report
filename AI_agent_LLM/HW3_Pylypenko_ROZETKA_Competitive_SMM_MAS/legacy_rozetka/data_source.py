"""Platform adapters і fixture fallback для light-версії без API."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import Platform, SocialPost


OFFICIAL_PROFILES: dict[str, str] = {
    "instagram": "https://www.instagram.com/rozetkaua/",
    "facebook": "https://www.facebook.com/rozetka.ua",
    "threads": "https://www.threads.net/@rozetkaua",
    "telegram": "https://t.me/s/rrozetka",
}

# Fixture є незмінним навчальним snapshot. Фіксована дата гарантує, що Notebook,
# CLI та test runner повертають тотожні дати публікацій у повторних запусках.
FIXTURE_SNAPSHOT_AT = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

# Статус профілю не змішується з результатом конкретного збору постів.
# Підтверджені канали наведені в офіційному social hub ROZETKA; Threads там
# не зазначений, тому коректний статус — not_verified, а не does_not_exist.
PROFILE_REGISTRY: dict[str, dict[str, str]] = {
    "instagram": {
        "profile_status": "verified_official",
        "verification_source": "ROZETKA official social hub",
    },
    "facebook": {
        "profile_status": "verified_official",
        "verification_source": "ROZETKA official social hub",
    },
    "telegram": {
        "profile_status": "verified_official",
        "verification_source": "ROZETKA official Telegram channel",
    },
    "threads": {
        "profile_status": "not_verified",
        "verification_source": "Threads profile is not listed in ROZETKA official social hub",
    },
}


class PlatformAdapter(ABC):
    """Спільний контракт різних методів light-парсингу."""

    platform: Platform

    @abstractmethod
    def parse(self, profile_url: str, period_days: int) -> list[dict]:
        """Повернути публічні пости або підняти контрольовану помилку."""

    @staticmethod
    def fetch_html(url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (educational SMM analyzer)"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.read().decode("utf-8", errors="replace")


class MetaAdapter(PlatformAdapter):
    """Instagram/Facebook: OpenGraph metadata; пости часто закриті login-wall."""

    def __init__(self, platform: Literal["instagram", "facebook"]) -> None:
        self.platform = platform

    def parse(self, profile_url: str, period_days: int) -> list[dict]:
        html = self.fetch_html(profile_url)
        if "login" in html.casefold() or "temporarily blocked" in html.casefold():
            raise RuntimeError("PLATFORM_LOGIN_REQUIRED")
        descriptions = re.findall(
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
            html,
            flags=re.I,
        )
        if not descriptions:
            raise RuntimeError("PUBLIC_POSTS_NOT_EXPOSED")
        raise RuntimeError("PROFILE_METADATA_ONLY")


class ThreadsAdapter(PlatformAdapter):
    """Threads: embedded metadata, якщо профіль доступний без авторизації."""

    platform: Platform = "threads"

    def parse(self, profile_url: str, period_days: int) -> list[dict]:
        html = self.fetch_html(profile_url)
        if len(html) < 500 or "login" in html.casefold():
            raise RuntimeError("THREADS_PROFILE_UNAVAILABLE")
        raise RuntimeError("THREADS_POSTS_NOT_EXPOSED")


class TelegramAdapter(PlatformAdapter):
    """Telegram: публічний HTML t.me/s має серверний список повідомлень."""

    platform: Platform = "telegram"

    def parse(self, profile_url: str, period_days: int) -> list[dict]:
        html = self.fetch_html(profile_url)
        if "tgme_widget_message" not in html:
            raise RuntimeError("TELEGRAM_MESSAGES_NOT_FOUND")
        # Light-парсер навмисно не вигадує метрики, яких немає в HTML.
        # Для повної відтворюваної аналітики executor переходить до snapshot.
        raise RuntimeError("PUBLIC_HTML_INCOMPLETE_FOR_ANALYTICS")


class FixturePostSource:
    """Нормалізує навчальний snapshot відносно зафіксованої дати зрізу."""

    def __init__(self, fixture_path: str | Path) -> None:
        self.fixture_path = Path(fixture_path)
        self.rows = json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def load(self, platform: Platform, period_days: int) -> list[dict]:
        now = FIXTURE_SNAPSHOT_AT
        posts: list[dict] = []
        for row in self.rows:
            if row["platform"] != platform or row["days_ago"] >= period_days:
                continue
            value = dict(row)
            value.pop("days_ago")
            value["published_at"] = (now - timedelta(days=row["days_ago"])).isoformat()
            value["source_mode"] = "fixture"
            value["confidence"] = 0.72
            if value.get("views") is not None:
                value["views_status"] = "available"
            elif platform == "instagram":
                value["views_status"] = "not_public"
            elif platform == "facebook" and value.get("content_type") in {"photo", "carousel", "text"}:
                value["views_status"] = "not_applicable"
            else:
                value["views_status"] = "missing_in_source"
            posts.append(SocialPost.model_validate(value).model_dump(mode="json"))
        posts.sort(key=lambda item: item["published_at"], reverse=True)
        return posts


class SocialDataSource:
    """Маршрутизує платформу до адаптера та не приховує причину fallback."""

    def __init__(self, fixture_path: str | Path, *, live_enabled: bool = False) -> None:
        self.live_enabled = live_enabled
        self.fixture = FixturePostSource(fixture_path)
        self.adapters: dict[str, PlatformAdapter] = {
            "instagram": MetaAdapter("instagram"),
            "facebook": MetaAdapter("facebook"),
            "threads": ThreadsAdapter(),
            "telegram": TelegramAdapter(),
        }

    def collect_public(self, platform: Platform, profile_url: str, period_days: int) -> list[dict]:
        if not self.live_enabled:
            raise RuntimeError("LIVE_MODE_DISABLED")
        try:
            return self.adapters[platform].parse(profile_url, period_days)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("NETWORK_OR_PLATFORM_UNAVAILABLE") from exc

    def load_fixture(self, platform: Platform, period_days: int) -> list[dict]:
        return self.fixture.load(platform, period_days)
