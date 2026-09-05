"""Завантаження відтворюваних JSON-прикладів."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_fixture(name: str = "demo_request.json") -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def approve_all_payload(result: dict) -> dict:
    findings = [*result.get("certain_findings", []), *result.get("needs_review", [])]
    return {
        "request_id": result["request_id"],
        "decisions": [
            {"finding_id": item["finding_id"], "decision": "approve", "reason": "Навчальна перевірка"}
            for item in findings
        ],
    }


def demo_review_payload(result: dict) -> dict:
    """Єдиний HITL-сценарій для notebook і run_demo.py.

    Коректні пропозиції агентів приймаються, а рівно для одного терміна
    користувач подає власний варіант через edit.
    """

    review = approve_all_payload(result)
    findings = {
        item["finding_id"]: item
        for item in [*result.get("certain_findings", []), *result.get("needs_review", [])]
    }
    for decision in review["decisions"]:
        finding = findings[decision["finding_id"]]
        if finding["original_text"] == "дедлайн":
            decision.update({
                "decision": "edit",
                "edited_fix": "кінцевий термін",
                "reason": "Власна термінологічна форма користувача",
            })
    return review
