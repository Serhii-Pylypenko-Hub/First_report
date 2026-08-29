"""Pydantic-контракти інструментів і фінального звіту."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SearchRecentVideosInput(BaseModel):
    """Параметри пошуку свіжих відео на YouTube."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic: str = Field(
        default="",
        description=(
            "Тема пошуку. Порожній рядок означає загальні YouTube-тренди; "
            "непорожній — тематичний пошук, наприклад 'AI agents'."
        ),
        max_length=120,
    )
    days: int = Field(default=7, description="Період аналізу в днях, від 1 до 30.")
    region_code: str = Field(
        default="UA",
        description="Дволітерний ISO-код регіону YouTube, наприклад UA або US.",
    )
    max_candidates: int = Field(
        default=50,
        description="Максимальна кількість кандидатів для подальшого ранжування, 5–50.",
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        if any(char in value for char in "\r\n\t"):
            raise ValueError("Тема повинна бути одним текстовим рядком")
        return value

    @field_validator("days")
    @classmethod
    def validate_days(cls, value: int) -> int:
        if not 1 <= value <= 30:
            raise ValueError("Період аналізу має бути від 1 до 30 днів")
        return value

    @field_validator("region_code")
    @classmethod
    def validate_region_code(cls, value: str) -> str:
        normalized = value.upper()
        if not re.fullmatch(r"[A-Z]{2}", normalized):
            raise ValueError("Код регіону має складатися з двох латинських літер")
        return normalized

    @field_validator("max_candidates")
    @classmethod
    def validate_max_candidates(cls, value: int) -> int:
        if not 5 <= value <= 50:
            raise ValueError("Кількість кандидатів має бути від 5 до 50")
        return value


class EnrichVideoStatisticsInput(BaseModel):
    """Параметри отримання метрик для знайденого набору відео."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dataset_id: str = Field(
        description="Ідентифікатор набору, повернений інструментом search_recent_videos."
    )

    @field_validator("dataset_id")
    @classmethod
    def validate_dataset_id(cls, value: str) -> str:
        if not re.fullmatch(r"dataset-[a-f0-9]{10}", value):
            raise ValueError("Некоректний dataset_id; використайте значення з попереднього tool result")
        return value


class RankTrendingVideosInput(BaseModel):
    """Параметри побудови рейтингів YouTube-відео."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dataset_id: str = Field(
        description="Ідентифікатор збагаченого набору відео."
    )
    metrics: list[Literal["trend_score", "views"]] = Field(
        default_factory=lambda: ["trend_score", "views"],
        description="Рейтинги, які потрібно побудувати: загальний trend score та/або перегляди.",
    )
    top_n: int = Field(default=20, description="Кількість відео у кожному рейтингу, 1–20.")

    @field_validator("dataset_id")
    @classmethod
    def validate_dataset_id(cls, value: str) -> str:
        if not re.fullmatch(r"dataset-[a-f0-9]{10}", value):
            raise ValueError("Некоректний dataset_id")
        return value

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, value: list[str]) -> list[str]:
        unique = list(dict.fromkeys(value))
        if not unique:
            raise ValueError("Потрібно вказати хоча б одну метрику")
        return unique

    @field_validator("top_n")
    @classmethod
    def validate_top_n(cls, value: int) -> int:
        if not 1 <= value <= 20:
            raise ValueError("Розмір рейтингу має бути від 1 до 20")
        return value


class AnalyzeTopicSignalsInput(BaseModel):
    """Параметри аналізу тем і каналів у наборі відео."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dataset_id: str = Field(description="Ідентифікатор збагаченого набору відео.")
    top_n: int = Field(default=10, description="Кількість найчастіших тем і каналів, 3–20.")

    @field_validator("dataset_id")
    @classmethod
    def validate_dataset_id(cls, value: str) -> str:
        if not re.fullmatch(r"dataset-[a-f0-9]{10}", value):
            raise ValueError("Некоректний dataset_id")
        return value

    @field_validator("top_n")
    @classmethod
    def validate_top_n(cls, value: int) -> int:
        if not 3 <= value <= 20:
            raise ValueError("Кількість сигналів має бути від 3 до 20")
        return value


class VideoRecord(BaseModel):
    """Нормалізований запис одного YouTube-відео."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    video_id: str = Field(description="YouTube video ID.", min_length=3, max_length=32)
    title: str = Field(description="Назва відео.", min_length=1, max_length=300)
    channel_title: str = Field(description="Назва каналу.", min_length=1, max_length=200)
    published_at: datetime = Field(description="UTC-дата публікації.")
    url: str = Field(description="Пряме посилання на відео.")
    description: str = Field(default="", description="Короткий опис відео.", max_length=1000)
    views: int = Field(default=0, ge=0, description="Кількість переглядів.")
    duration_seconds: int | None = Field(default=None, ge=0, description="Тривалість відео в секундах.")
    trend_score: float = Field(default=0.0, ge=0, le=1, description="Інтегральний показник трендовості.")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not re.fullmatch(r"https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]+", value):
            raise ValueError("Очікується канонічне посилання YouTube watch URL")
        return value


class RankedVideo(BaseModel):
    """Відео у сформованому рейтингу."""

    rank: int = Field(ge=1)
    video_id: str
    title: str
    channel_title: str
    published_at: datetime
    url: str
    views: int = Field(ge=0)
    trend_score: float = Field(ge=0, le=1)


class TrendReport(BaseModel):
    """Строгий формат фінальної відповіді агента."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "partial", "error"]
    mode: Literal["general", "thematic"]
    topic: str
    period_days: int = Field(ge=1, le=30)
    region_code: str
    source_mode: Literal["html", "fixture"]
    generated_at: datetime
    candidates_found: int = Field(ge=0)
    videos_analyzed: int = Field(ge=0)
    top_overall: list[RankedVideo]
    top_by_views: list[RankedVideo]
    trend_terms: list[str]
    leading_channels: list[str]
    summary: str
    confidence: float = Field(ge=0, le=1)
    limitations: list[str]
    stop_reason: str = "completed"

    @model_validator(mode="after")
    def validate_mode_topic(self) -> "TrendReport":
        if self.mode == "thematic" and not self.topic:
            raise ValueError("Тематичний звіт повинен містити тему")
        return self
