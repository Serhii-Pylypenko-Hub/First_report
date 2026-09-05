"""Pydantic v2 контракти конкурентного аналізу, плану та HITL."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Brand(str, Enum):
    ROZETKA = "rozetka"
    COMFY = "comfy"
    ALLO = "allo"
    FOXTROT = "foxtrot"
    EPICENTR = "epicentr"


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    THREADS = "threads"
    TELEGRAM = "telegram"


class SourceType(str, Enum):
    ORGANIC = "organic_post"
    PROMOTIONAL = "promotional_post"
    PAID_AD = "paid_ad"


class FunnelStage(str, Enum):
    AWARENESS = "awareness"
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"
    RETENTION = "retention"


class CompetitivePost(StrictModel):
    """Канонічний пост; відсутні метрики є None, а не NaN або нулем."""

    brand: Brand
    platform: Platform
    post_id: str = Field(min_length=3, max_length=80)
    published_at: datetime
    content_type: Literal["reel", "video", "photo", "carousel", "text"]
    text: str = Field(min_length=1, max_length=5000)
    topic: str = Field(min_length=2, max_length=80)
    source_type: SourceType
    ad_status: Literal["confirmed", "unverified", "not_ad"]
    ad_evidence: str = Field(default="", max_length=300)
    views: int | None = Field(default=None, ge=0)
    views_status: Literal["available", "not_public", "not_applicable", "missing_in_source"]
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    url: str
    source_mode: Literal["fixture", "public_html", "api", "user_upload"] = "fixture"
    confidence: float = Field(ge=0, le=1)
    platform_metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        if not value.startswith(("https://", "fixture://")):
            raise ValueError("URL повинен використовувати HTTPS або fixture://")
        return value

    @model_validator(mode="after")
    def validate_ad_and_views(self) -> "CompetitivePost":
        if self.source_type == SourceType.PAID_AD and self.ad_status != "confirmed":
            raise ValueError("paid_ad потребує ad_status=confirmed")
        if self.ad_status == "confirmed" and not self.ad_evidence:
            raise ValueError("Підтверджена реклама потребує ad_evidence")
        if self.views_status == "available" and self.views is None:
            raise ValueError("views_status=available потребує числового views")
        if self.views_status != "available" and self.views is not None:
            raise ValueError("Недоступні views повинні бути null")
        return self


class AnalysisRequest(StrictModel):
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{3,80}$")
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{3,80}$")
    target_brand: Brand = Brand.ROZETKA
    competitors: list[Brand] = Field(
        default_factory=lambda: [Brand.COMFY, Brand.ALLO, Brand.FOXTROT, Brand.EPICENTR],
        min_length=2,
        max_length=4,
    )
    platforms: list[Platform] = Field(default_factory=lambda: list(Platform), min_length=1)
    period_days: int = Field(default=30, ge=1, le=31)
    top_k: int = Field(default=5, ge=3, le=10)
    draft_count: int = Field(default=5, ge=4, le=5)
    user_query: str = Field(default="Порівняй конкурентів і запропонуй рекламні пости.", max_length=2000)

    @model_validator(mode="after")
    def unique_scope(self) -> "AnalysisRequest":
        if self.target_brand in self.competitors:
            raise ValueError("Цільовий бренд не може бути власним конкурентом")
        if len(set(self.competitors)) != len(self.competitors):
            raise ValueError("Список конкурентів містить дублікати")
        return self


class PlanOperation(str, Enum):
    COLLECT_BRAND_CONTENT = "collect_brand_content"
    NORMALIZE_METRICS = "normalize_metrics"
    SEARCH_KNOWLEDGE = "search_knowledge"
    COMPARE_COMPETITORS = "compare_competitors"
    GENERATE_DRAFTS = "generate_drafts"
    LANGUAGE_REVIEW = "language_review"
    VERIFY_RESULTS = "verify_results"
    PREPARE_EXPORT = "prepare_export"


class PlanStep(StrictModel):
    step_id: int = Field(ge=1)
    operation: PlanOperation
    agent_name: str = Field(min_length=2, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)


class ExecutionPlan(StrictModel):
    goal: str = Field(min_length=5, max_length=500)
    steps: list[PlanStep] = Field(min_length=3, max_length=12)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps: list[PlanStep]) -> list[PlanStep]:
        ids = [step.step_id for step in steps]
        if len(ids) != len(set(ids)):
            raise ValueError("step_id повинні бути унікальними")
        known = set(ids)
        for step in steps:
            if any(dep not in known or dep >= step.step_id for dep in step.depends_on):
                raise ValueError("depends_on має посилатися лише на попередні кроки")
        return steps


class RouteDecision(StrictModel):
    action: Literal["collect", "research", "analyze", "create", "language", "report"]
    reasoning: str = Field(min_length=3, max_length=300)


class ReviewDecision(StrictModel):
    item_id: str = Field(min_length=3, max_length=100)
    decision: Literal["approve", "reject", "edit"]
    edited_text: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def edit_requires_text(self) -> "ReviewDecision":
        if self.decision == "edit" and not self.edited_text:
            raise ValueError("Для edit необхідно передати edited_text")
        return self


class ContentSelection(StrictModel):
    decision: Literal["approve", "reject", "edit"] = "approve"
    selected_top_ids: list[str] = Field(default_factory=list, max_length=10)
    selected_draft_ids: list[str] = Field(default_factory=list, max_length=5)
    edited_drafts: dict[str, str] = Field(default_factory=dict)

    @field_validator("selected_top_ids", "selected_draft_ids")
    @classmethod
    def unique_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Вибрані ID не повинні дублюватися")
        return values

    @field_validator("edited_drafts")
    @classmethod
    def safe_edits(cls, values: dict[str, str]) -> dict[str, str]:
        if any(len(text) > 5000 or not text.strip() for text in values.values()):
            raise ValueError("Відредагований текст порожній або перевищує 5000 символів")
        return values


class ExportRequest(StrictModel):
    path: str = "outputs/hw3_competitive_smm_report.json"
    report: dict[str, Any]
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,100}$")

    @field_validator("path")
    @classmethod
    def safe_output_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or not normalized.startswith("outputs/"):
            raise ValueError("Експорт дозволено лише всередину outputs/")
        if not re.fullmatch(r"outputs/[A-Za-z0-9_.-]+\.json", normalized):
            raise ValueError("Некоректне ім'я JSON-звіту")
        return normalized
