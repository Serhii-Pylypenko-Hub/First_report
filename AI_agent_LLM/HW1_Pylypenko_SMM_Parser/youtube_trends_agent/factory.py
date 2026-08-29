"""Фабрика HTML/fixture клієнта без YouTube API."""

from __future__ import annotations

from pathlib import Path

from .youtube_client import FixtureYouTubeClient, YouTubeClient, YouTubeHTMLClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = PROJECT_ROOT / "fixtures" / "youtube_videos.json"


def create_youtube_client(mode: str | None = None) -> YouTubeClient:
    """Створити клієнт за YOUTUBE_DATA_MODE=fixture|html."""

    import os

    selected = (mode or os.getenv("YOUTUBE_DATA_MODE") or "fixture").strip().lower()
    if selected == "html":
        return YouTubeHTMLClient(timeout_seconds=float(os.getenv("YOUTUBE_HTTP_TIMEOUT", "15")))
    if selected != "fixture":
        raise ValueError("YOUTUBE_DATA_MODE повинен бути fixture або html")
    return FixtureYouTubeClient(DEFAULT_FIXTURE)
