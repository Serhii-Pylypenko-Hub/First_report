"""Owner-scoped довготривала пам'ять підтверджених користувацьких виправлень."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import ActorContext, Category, DocumentPayload, Finding, ReviewDecision, Severity, finding_id
from .security import INJECTION_PATTERNS, SecurityError


class UserCorrectionMemory:
    """Мінімальний SQLite Store: namespace завжди починається з tenant_id/user_id."""

    def __init__(self, path: str | Path | None = None, *, ttl_days: int = 365) -> None:
        self.path = str(Path(path).resolve()) if path else ":memory:"
        self.ttl_days = ttl_days
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_corrections (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                category TEXT NOT NULL,
                original_text TEXT NOT NULL,
                preferred_text TEXT NOT NULL,
                source_finding_id TEXT NOT NULL,
                confirmed_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                confirmed INTEGER NOT NULL CHECK (confirmed = 1),
                PRIMARY KEY (tenant_id, user_id, agent, original_text)
            )
            """
        )
        self.connection.commit()

    @staticmethod
    def _safe_phrase(value: str) -> str:
        phrase = " ".join(value.split()).strip()
        if not phrase or len(phrase) > 500:
            raise SecurityError("Персональне виправлення має містити 1–500 символів")
        if any(pattern.search(phrase) for pattern in INJECTION_PATTERNS):
            raise SecurityError("Персональне виправлення містить ознаки prompt injection")
        return phrase

    def remember_confirmed_edits(
        self,
        actor: ActorContext,
        findings: list[Finding],
        decisions: list[ReviewDecision],
    ) -> list[dict]:
        """Write-gate: записує лише явні edit-рішення людини для відомих findings."""

        known = {item.finding_id: item for item in findings}
        now = datetime.now(UTC)
        expires = now + timedelta(days=self.ttl_days)
        updates: list[dict] = []
        for decision in decisions:
            if decision.decision != "edit":
                continue
            finding = known.get(decision.finding_id)
            if finding is None or finding.content_flag or finding.category == Category.SECURITY:
                raise SecurityError("Недозволена спроба запису персонального правила")
            original = self._safe_phrase(finding.original_text).casefold()
            preferred = self._safe_phrase(decision.edited_fix or "")
            self.connection.execute(
                """
                INSERT INTO user_corrections (
                    tenant_id, user_id, agent, category, original_text, preferred_text,
                    source_finding_id, confirmed_at, expires_at, confirmed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(tenant_id, user_id, agent, original_text) DO UPDATE SET
                    category=excluded.category,
                    preferred_text=excluded.preferred_text,
                    source_finding_id=excluded.source_finding_id,
                    confirmed_at=excluded.confirmed_at,
                    expires_at=excluded.expires_at,
                    confirmed=1
                """,
                (
                    actor.tenant_id, actor.user_id, finding.agent, finding.category.value,
                    original, preferred, finding.finding_id, now.isoformat(), expires.isoformat(),
                ),
            )
            updates.append({
                "namespace": [actor.tenant_id, actor.user_id, "corrections"],
                "original_text": original,
                "preferred_text": preferred,
                "agent": finding.agent,
                "source": "human_confirmed_edit",
                "confirmed": True,
                "expires_at": expires.isoformat(),
            })
        self.connection.commit()
        return updates

    def retrieve(self, actor: ActorContext, document: DocumentPayload, *, agent: str) -> list[Finding]:
        """Повертає лише активні записи поточного owner namespace, які є в документі."""

        now = datetime.now(UTC).isoformat()
        rows = self.connection.execute(
            """
            SELECT * FROM user_corrections
            WHERE tenant_id=? AND user_id=? AND agent=? AND confirmed=1 AND expires_at>?
            ORDER BY confirmed_at DESC
            """,
            (actor.tenant_id, actor.user_id, agent, now),
        ).fetchall()
        found: list[Finding] = []
        for row in rows:
            for node in document.nodes:
                if row["original_text"] not in node.text.casefold():
                    continue
                rule_id = f"MEMORY.USER.{row['source_finding_id']}"
                found.append(Finding(
                    finding_id=finding_id(agent, node.node_id, rule_id, row["original_text"]),
                    rule_id=rule_id,
                    agent=agent,
                    node_id=node.node_id,
                    section_ref=node.section_ref,
                    category=Category(row["category"]),
                    severity=Severity.LOW,
                    original_text=row["original_text"],
                    suggested_fix=row["preferred_text"],
                    reason="Персональний варіант, раніше підтверджений цим користувачем через HITL.",
                    confidence=0.99,
                    review_required=True,
                    evidence=[],
                ))
        return found

    def count(self, actor: ActorContext) -> int:
        return int(self.connection.execute(
            "SELECT COUNT(*) FROM user_corrections WHERE tenant_id=? AND user_id=? AND confirmed=1",
            (actor.tenant_id, actor.user_id),
        ).fetchone()[0])
