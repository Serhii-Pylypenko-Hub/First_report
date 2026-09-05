"""Pydantic-контракти JSON-входу, висновків і людських рішень."""

from __future__ import annotations

from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)


class Register(str, Enum):
    GENERAL = "general"
    OFFICIAL = "official"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(str, Enum):
    GRAMMAR = "grammar"
    ORTHOGRAPHY = "orthography"
    PUNCTUATION = "punctuation"
    CALQUE = "calque"
    OFFICIAL_STYLE = "official_style"
    CLARITY = "clarity"
    TERMINOLOGY = "terminology"
    STRUCTURE = "structure"
    CONTENT_FLAG = "content_flag"
    SECURITY = "security"


class DocumentNode(StrictModel):
    node_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    node_type: Literal["paragraph", "section", "table_cell"] = "paragraph"
    section_ref: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=20_000)


class DocumentPayload(StrictModel):
    document_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    language: Literal["uk"] = "uk"
    document_register: Register = Field(default=Register.OFFICIAL, alias="register")
    nodes: list[DocumentNode] = Field(min_length=1, max_length=250)

    @field_validator("nodes")
    @classmethod
    def unique_node_ids(cls, value: list[DocumentNode]) -> list[DocumentNode]:
        ids = [node.node_id for node in value]
        if len(ids) != len(set(ids)):
            raise ValueError("node_id мають бути унікальними")
        return value

    def content_hash(self) -> str:
        raw = self.model_dump_json(exclude_none=False)
        return sha256(raw.encode("utf-8")).hexdigest()


class AnalysisRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    document: DocumentPayload
    options: dict[str, bool] = Field(default_factory=dict)

    @field_validator("options")
    @classmethod
    def allowed_options(cls, value: dict[str, bool]) -> dict[str, bool]:
        allowed = {"include_structure", "include_editor_note"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Невідомі options: {sorted(unknown)}")
        return value


class ActorContext(StrictModel):
    """Надходить від сервера авторизації, а не з користувацького JSON."""

    tenant_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")
    user_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:@-]+$")
    role: Literal["user", "admin"] = "user"


class Evidence(StrictModel):
    rule_id: str
    title: str
    source_url: str
    authority: str
    version: str
    excerpt: str
    checksum: str


class Finding(StrictModel):
    finding_id: str
    rule_id: str
    agent: str
    node_id: str
    section_ref: str | None = None
    category: Category
    severity: Severity
    original_text: str
    suggested_fix: str | None = None
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    review_required: bool = True
    content_flag: bool = False
    occurrences_count: int = Field(default=1, ge=1)
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def content_flags_are_never_autofixed(self) -> "Finding":
        if self.content_flag and self.suggested_fix is not None:
            raise ValueError("Для content_flag suggested_fix має бути порожнім")
        return self


class ReviewDecision(StrictModel):
    finding_id: str
    decision: Literal["approve", "edit", "reject"]
    edited_fix: str | None = Field(default=None, max_length=5_000)
    reason: str = Field(default="", max_length=1_000)

    @model_validator(mode="after")
    def edit_requires_text(self) -> "ReviewDecision":
        if self.decision == "edit" and not self.edited_fix:
            raise ValueError("Для рішення edit потрібне edited_fix")
        if self.decision != "edit" and self.edited_fix is not None:
            raise ValueError("edited_fix дозволене лише для рішення edit")
        return self


class ReviewPayload(StrictModel):
    request_id: str
    decisions: list[ReviewDecision]


class ToolResult(StrictModel):
    status: Literal["ok", "error", "blocked"]
    data: Any | None = None
    error: dict[str, str] | None = None


def finding_id(agent: str, node_id: str, rule_id: str, original: str) -> str:
    digest = sha256(f"{agent}|{node_id}|{rule_id}|{original}".encode("utf-8")).hexdigest()[:12]
    return f"f-{digest}"
