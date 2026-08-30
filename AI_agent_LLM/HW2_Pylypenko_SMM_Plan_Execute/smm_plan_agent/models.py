"""Pydantic-контракти плану, інструментів, HITL і фінального звіту."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Plan(BaseModel):
    """Повний план, який planner створює до початку виконання."""

    goal: str = Field(description="Головна ціль запиту користувача.")
    steps: list[str] = Field(
        description="Послідовність із 3–5 конкретних виконуваних кроків.",
        min_length=3,
        max_length=5,
    )


class ReplanDecision(BaseModel):
    """Рішення replanner після одного виконаного кроку."""

    action: Literal["continue", "replan", "finish"] = Field(
        description="Продовжити план, замінити залишок або завершити роботу."
    )
    updated_steps: list[str] | None = Field(
        default=None,
        description="Новий залишок плану лише для action=replan.",
    )
    reasoning: str = Field(description="Коротке пояснення рішення.")


class SearchRecentVideosInput(BaseModel):
    """Вхід пошуку свіжих YouTube-відео."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic: str = Field(default="", max_length=120, description="Тема аналізу.")
    days: int = Field(default=7, ge=1, le=30, description="Період у днях.")
    region_code: str = Field(default="UA", description="Дволітерний код регіону.")
    max_candidates: int = Field(default=20, ge=5, le=30, description="Ліміт кандидатів.")

    @field_validator("region_code")
    @classmethod
    def normalize_region(cls, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("region_code повинен містити дві латинські літери")
        return value


class SearchKnowledgeInput(BaseModel):
    """Вхід пошуку в ChromaDB."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(min_length=3, max_length=500, description="Запит до бази знань.")
    top_k: int = Field(default=6, ge=1, le=8, description="Кількість правил у відповіді.")


class VideoCandidate(BaseModel):
    """Нормалізований кандидат для SMM-рейтингу."""

    model_config = ConfigDict(extra="forbid")

    video_id: str
    title: str
    channel_title: str
    description: str = ""
    published_at: datetime
    url: str
    views: int = Field(ge=0)
    trend_score: float = Field(ge=0, le=1)


class EvaluateTrendsInput(BaseModel):
    """Вхід оцінювання трендів за retrieved-політиками."""

    model_config = ConfigDict(extra="forbid")

    videos: list[VideoCandidate] = Field(description="Кандидати з пошукового tool.")
    policy_documents: list[str] = Field(
        description="JSON-документи, повернені search_knowledge."
    )
    top_n: int = Field(default=10, ge=1, le=20, description="Розмір маркетингового топу.")


class ScheduleCampaignInput(BaseModel):
    """Параметри ризикової дії планування SMM-кампанії."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    campaign_name: str = Field(min_length=3, max_length=120, description="Назва кампанії.")
    video_ids: list[str] = Field(min_length=1, max_length=10, description="Відео для кампанії.")
    planned_date: str = Field(description="Запланована дата у форматі YYYY-MM-DD.")
    note: str = Field(default="", max_length=500, description="Примітка для SMM-команди.")

    @field_validator("planned_date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("planned_date має відповідати YYYY-MM-DD")
        return value


class SafetyItem(BaseModel):
    """Результат brand-safety перевірки одного відео."""

    video: VideoCandidate
    decision: Literal["allow", "review", "block"]
    categories: list[str] = Field(default_factory=list)
    reason: str
    matched_policy_ids: list[str] = Field(default_factory=list)


class HumanModerationDecision(BaseModel):
    """Структурована відповідь людини для сумнівних позицій."""

    decision: Literal["approve_selected", "approve_all", "reject_all"]
    acceptable_video_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class CampaignApprovalDecision(BaseModel):
    """Approve/edit/reject для ризикового schedule_campaign."""

    decision: Literal["approve", "edit", "reject"]
    edits: dict = Field(default_factory=dict)
    reason: str = ""

