"""Адаптер повторного використання мовної MAS для рекламних чернеток."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from language_mas.analyzers import (
    grammar_findings,
    structure_findings,
    style_findings,
    terminology_findings,
    verify_findings,
)
from language_mas.knowledge import SecureKnowledgeBase
from language_mas.models import DocumentNode, DocumentPayload

from guardrails import scan_forbidden_topics


def review_drafts(drafts: list[dict[str, Any]], root: str | Path) -> dict[str, Any]:
    kb = SecureKnowledgeBase(Path(root) / "knowledge" / "language_rules.json")
    nodes = [
        DocumentNode(node_id=draft["draft_id"], section_ref=draft["topic"], text=draft["text"])
        for draft in drafts
    ]
    document = DocumentPayload(document_id="generated-smm-drafts", register="general", nodes=nodes)
    outputs = {
        "grammar": grammar_findings(document, kb),
        "style": style_findings(document, kb),
        "terminology": terminology_findings(document, kb),
        "structure": structure_findings(document, kb),
    }
    all_findings = [finding for findings in outputs.values() for finding in findings]
    verified = verify_findings(document, all_findings)
    forbidden = [
        {"draft_id": draft["draft_id"], "alerts": scan_forbidden_topics(draft["text"])}
        for draft in drafts
        if scan_forbidden_topics(draft["text"])
    ]
    return {
        "agent_results": {
            name: {"status": "completed", "findings": [item.model_dump(mode="json") for item in findings]}
            for name, findings in outputs.items()
        },
        "verifier": {"status": "completed", "findings": [item.model_dump(mode="json") for item in verified]},
        "forbidden_topic_warnings": forbidden,
    }


def apply_language_fixes(drafts: list[dict[str, Any]], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {draft["draft_id"]: dict(draft) for draft in drafts}
    for finding in findings:
        fix = finding.get("suggested_fix")
        if not fix:
            continue
        draft = by_id.get(finding["node_id"])
        if not draft:
            continue
        def replacement(match: re.Match[str]) -> str:
            value = fix
            return value[:1].upper() + value[1:] if match.group(0)[:1].isupper() else value

        draft["text"] = re.sub(
            re.escape(finding["original_text"]),
            replacement,
            draft["text"],
            count=1,
            flags=re.IGNORECASE,
        )
    return list(by_id.values())
