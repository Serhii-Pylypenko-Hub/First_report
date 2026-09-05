"""CLI/API helpers для approve, reject, edit та Command(resume=...)."""

from __future__ import annotations

from typing import Any

from mas_langgraph import CompetitiveSMMMAS


def approve_all_payload(state: dict[str, Any]) -> dict[str, Any]:
    values = state["values"]
    return {
        "decision": "approve",
        "selected_top_ids": [row["post_id"] for row in values["analysis"]["ad_rankings"]["top_by_normalized_score"]],
        "selected_draft_ids": [row["draft_id"] for row in values["drafts"]],
        "edited_drafts": {},
    }


def reject_all_payload() -> dict[str, Any]:
    return {"decision": "reject", "selected_top_ids": [], "selected_draft_ids": [], "edited_drafts": {}}


def resume_content_review(mas: CompetitiveSMMMAS, thread_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return mas.resume_selection(thread_id, payload)
