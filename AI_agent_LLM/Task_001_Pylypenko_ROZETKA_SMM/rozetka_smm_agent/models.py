"""Pydantic-контракти інструментів, постів, планування та HITL."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Platform = Literal["instagram", "facebook", "threads", "telegram"]


class Plan(BaseModel):
    """Повний план, сформований до початку виконання."""

    goal: str = Field(min_length=5, description="Ціль маркетингового аналізу.")
    steps: list[str] = Field(min_length=3, max_length=6, description="Послідовні кроки.")


class ReplanDecision(BaseModel):
    """Рішення після виконання одного кроку плану."""

    action: Literal["continue", "replan", "finish"]
    updated_steps: list[str] | None = None
    reasoning: str = Field(min_length=3)


class CollectPublicPostsInput(BaseModel):
    """Вхід публічного light-парсингу однієї платформи."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    brand: str = Field(min_length=2, max_length=80)
    platform: Platform
    profile_url: str = Field(min_length=10, max_length=500)
    period_days: int = Field(default=30, ge=1, le=31)

    @field_validator("profile_url")
    @classmethod
    def validate_profile_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("profile_url повинен використовувати HTTPS")
        return value


class LoadFixturePostsInput(BaseModel):
    """Вхід відтворюваного fallback-джерела."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    brand: str = Field(min_length=2, max_length=80)
    platform: Platform
    period_days: int = Field(default=30, ge=1, le=31)

    @field_validator("brand")
    @classmethod
    def normalize_brand(cls, value: str) -> str:
        if value.casefold() not in {"rozetka", "розетка"}:
            raise ValueError("Навчальна версія підтримує лише бренд ROZETKA")
        return "ROZETKA"


class KnowledgeSearchInput(BaseModel):
    """Вхід Agentic RAG пошуку."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=8)

    @field_validator("query")
    @classmethod
    def reject_instruction_injection(cls, value: str) -> str:
        if "ignore previous instructions" in value.casefold():
            raise ValueError("Виявлено небезпечну інструкцію у RAG-запиті")
        return value


class SocialPost(BaseModel):
    """Канонічна модель поста незалежно від платформи."""

    model_config = ConfigDict(extra="forbid")

    platform: Platform
    post_id: str = Field(min_length=2)
    published_at: datetime
    content_type: Literal["reel", "video", "photo", "carousel", "text"]
    text: str = Field(default="", max_length=3000)
    topic: str = Field(min_length=2, max_length=80)
    views: int | None = Field(default=None, ge=0)
    views_status: Literal["available", "not_public", "not_applicable", "missing_in_source"]
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    url: str
    source_mode: Literal["public_html", "metadata", "fixture"]
    confidence: float = Field(ge=0, le=1)
    platform_metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith(("https://", "fixture://")):
            raise ValueError("URL має бути HTTPS або fixture://")
        return value


class AnalyzePatternsInput(BaseModel):
    """Вхід узагальнювальної маркетингової аналітики."""

    model_config = ConfigDict(extra="forbid")

    posts: list[SocialPost] = Field(min_length=1, max_length=200)
    period_days: int = Field(default=30, ge=1, le=31)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("posts")
    @classmethod
    def unique_posts(cls, value: list[SocialPost]) -> list[SocialPost]:
        keys = {(item.platform, item.post_id) for item in value}
        if len(keys) != len(value):
            raise ValueError("posts містить дублікати platform + post_id")
        return value


class ExportReportInput(BaseModel):
    """Параметри ризикового файлового експорту."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    path: str = Field(default="outputs/rozetka_smm_report.json", min_length=5, max_length=200)
    report: dict[str, Any]

    @field_validator("path")
    @classmethod
    def safe_relative_json_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("Дозволено лише відносний шлях усередині проєкту")
        if not re.fullmatch(r"[A-Za-z0-9_./-]+\.json", normalized):
            raise ValueError("Звіт повинен мати безпечне ім'я та розширення .json")
        return normalized


class ExportDecision(BaseModel):
    """Рішення оператора перед risky_export."""

    decision: Literal["approve", "reject", "edit"]
    path: str | None = None
    reason: str = Field(default="", max_length=300)

    @field_validator("path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        if value is not None:
            ExportReportInput.safe_relative_json_path(value)
        return value
