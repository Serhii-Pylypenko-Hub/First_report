"""Перевикористані та розширені доменні tools із попереднього ROZETKA-проєкту."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardrails import authorize_tool, input_guardrail
from hw3_smm.analytics import analyze_competitors
from hw3_smm.contracts import error, ok
from hw3_smm.fixtures import build_fixture_posts
from hw3_smm.models import AnalysisRequest, Brand, CompetitivePost, ExportRequest, Platform
from legacy_rozetka.knowledge import SMMKnowledgeBase


ROOT = Path(__file__).resolve().parent
_EXPORTED_KEYS: dict[str, str] = {}


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CollectBrandPostsInput(ToolInput):
    brand: Brand
    platforms: list[Platform] = Field(min_length=1, max_length=4)
    period_days: int = Field(default=30, ge=1, le=31)
    source_mode: str = Field(default="fixture", pattern=r"^(fixture|live)$")


class SearchKnowledgeInput(ToolInput):
    query: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=8)

    @field_validator("query")
    @classmethod
    def reject_injection(cls, value: str) -> str:
        safe, alerts = input_guardrail(value, max_chars=500, max_tokens=200)
        if not safe:
            raise ValueError(f"Небезпечний RAG-запит: {alerts}")
        return value


class CalculateMetricsInput(ToolInput):
    posts: list[CompetitivePost] = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=3, le=10)

    @field_validator("posts")
    @classmethod
    def unique_posts(cls, posts: list[CompetitivePost]) -> list[CompetitivePost]:
        keys = {(post.brand, post.platform, post.post_id) for post in posts}
        if len(keys) != len(posts):
            raise ValueError("Публікації містять дублікати brand+platform+post_id")
        return posts


class GenerateBriefInput(ToolInput):
    target_brand: Brand
    theme_comparison: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    draft_count: int = Field(default=5, ge=4, le=5)


def _kb() -> SMMKnowledgeBase:
    return SMMKnowledgeBase(
        persist_path=ROOT / "chroma_db",
        documents_path=ROOT / "knowledge" / "smm_knowledge.json",
    )


def collect_brand_posts_payload(
    brand: str,
    platforms: list[str],
    period_days: int = 30,
    source_mode: str = "fixture",
) -> dict[str, Any]:
    try:
        data = CollectBrandPostsInput.model_validate({
            "brand": brand, "platforms": platforms, "period_days": period_days, "source_mode": source_mode,
        })
        if data.source_mode == "live":
            return error(
                "LIVE_CONNECTOR_NOT_CONFIGURED",
                "Live-режим потребує окремих дозволених API-конекторів; доступний fixture fallback.",
                {"brand": data.brand.value},
            )
        selected = [
            post.model_dump(mode="json") for post in build_fixture_posts()
            if post.brand == data.brand and post.platform in data.platforms
        ]
        return ok({
            "brand": data.brand.value,
            "source_mode": "fixture",
            "notice": "Синтетичний навчальний snapshot; не поточна статистика.",
            "posts": selected,
        })
    except Exception as exc:
        return error("COLLECT_VALIDATION_ERROR", str(exc))


def search_smm_knowledge_payload(query: str, top_k: int = 5) -> dict[str, Any]:
    try:
        data = SearchKnowledgeInput.model_validate({"query": query, "top_k": top_k})
        return ok({"query": data.query, "documents": _kb().search(data.query, data.top_k)})
    except Exception as exc:
        return error("KNOWLEDGE_SEARCH_BLOCKED", str(exc))


def calculate_competitive_metrics_payload(posts: list[dict[str, Any]], top_k: int = 5) -> dict[str, Any]:
    try:
        data = CalculateMetricsInput.model_validate({"posts": posts, "top_k": top_k})
        return ok(analyze_competitors(data.posts, data.top_k))
    except Exception as exc:
        return error("ANALYSIS_VALIDATION_ERROR", str(exc))


def generate_content_brief_payload(
    target_brand: str,
    theme_comparison: list[dict[str, Any]],
    draft_count: int = 5,
) -> dict[str, Any]:
    try:
        data = GenerateBriefInput.model_validate({
            "target_brand": target_brand,
            "theme_comparison": theme_comparison,
            "draft_count": draft_count,
        })
        selected = data.theme_comparison[: data.draft_count]
        return ok({
            "target_brand": data.target_brand.value,
            "briefs": [
                {
                    "topic": row["topic"],
                    "platform": "instagram" if index % 2 else "facebook",
                    "format": row["dominant_format"],
                    "funnel_stage": row["funnel_stage"],
                    "audience": row["audience"],
                    "evidence": {"leader": row["leader"], "score": row["leader_score"]},
                    "constraint": "Запозичити патерн, але не копіювати текст або креатив конкурента.",
                }
                for index, row in enumerate(selected, start=1)
            ],
        })
    except Exception as exc:
        return error("BRIEF_VALIDATION_ERROR", str(exc))


def export_smm_report_payload(
    path: str,
    report: dict[str, Any],
    idempotency_key: str,
    *,
    project_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Ризикова операція: викликати лише після server-side HITL."""
    try:
        authorize_tool("approval_executor", "export_smm_report", {"path": path})
        data = ExportRequest.model_validate({"path": path, "report": report, "idempotency_key": idempotency_key})
        root = Path(project_root).resolve()
        target = (root / data.path).resolve()
        output_root = (root / "outputs").resolve()
        if target != output_root and output_root not in target.parents:
            return error("PATH_OUTSIDE_OUTPUTS", "Ціль експорту поза outputs/")
        digest = sha256(json.dumps(data.report, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        previous = _EXPORTED_KEYS.get(data.idempotency_key)
        if previous is not None:
            if previous != digest:
                return error("IDEMPOTENCY_CONFLICT", "Ключ повторно використано для іншого payload")
            return ok({"path": str(target), "idempotent_replay": True, "checksum": digest})
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data.report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        _EXPORTED_KEYS[data.idempotency_key] = digest
        return ok({"path": str(target), "idempotent_replay": False, "checksum": digest})
    except Exception as exc:
        return error("EXPORT_BLOCKED", str(exc))


def default_request(request_id: str = "demo-001", session_id: str = "session-001") -> AnalysisRequest:
    return AnalysisRequest(request_id=request_id, session_id=session_id)
