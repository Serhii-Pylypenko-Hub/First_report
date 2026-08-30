"""Створює відтворювані результати всіх критеріїв ДЗ №2."""

from __future__ import annotations

import json
from pathlib import Path

from smm_plan_agent.factory import PROJECT_ROOT, create_agent


REQUEST = (
    "Проаналізуй YouTube тренди про AI agents за останні 7 днів, "
    "перевір brand safety та заплануй SMM-кампанію"
)


def snapshot(agent, thread_id: str) -> dict:
    value = agent.state(thread_id=thread_id).values
    return {
        "current_step": value.get("current_step"),
        "plan": value.get("plan"),
        "approved": [item["video"]["video_id"] for item in value.get("approved", [])],
        "needs_review": [item["video"]["video_id"] for item in value.get("needs_review", [])],
        "blocked": [item["video"]["video_id"] for item in value.get("blocked", [])],
        "final_top": [item["video"]["video_id"] for item in value.get("final_top", [])],
        "campaign_status": value.get("campaign_status"),
        "completed": value.get("completed"),
        "replan_count": value.get("replan_count"),
        "tool_history": value.get("tool_history", []),
    }


def main() -> None:
    thread_id = "submission-demo"
    agent = create_agent()
    first = agent.start(REQUEST, thread_id=thread_id)
    first_snapshot = snapshot(agent, thread_id)
    first_gate = first["__interrupt__"][0].value["gate"]
    agent.close()

    # Новий Python-об'єкт і нове SQLite-з'єднання імітують restart процесу.
    agent = create_agent()
    restored_snapshot = snapshot(agent, thread_id)
    second = agent.resume(
        {
            "decision": "approve_selected",
            "acceptable_video_ids": ["boxingai01"],
            "reason": "Спортивний не-графічний контекст прийнятний.",
        },
        thread_id=thread_id,
    )
    second_snapshot = snapshot(agent, thread_id)
    second_gate = second["__interrupt__"][0].value["gate"]
    agent.close()

    agent = create_agent()
    final = agent.resume({"decision": "approve"}, thread_id=thread_id)
    final_snapshot = snapshot(agent, thread_id)

    other_thread = "submission-independent-thread"
    other = agent.start(REQUEST, thread_id=other_thread)
    other_snapshot = snapshot(agent, other_thread)
    other_gate = other["__interrupt__"][0].value["gate"]
    agent.close()

    results = {
        "plan_and_execute": {
            "planner_steps": first_snapshot["plan"],
            "current_step_at_first_pause": first_snapshot["current_step"],
        },
        "persistence": {
            "same_state_after_reopen": first_snapshot == restored_snapshot,
            "thread_id": thread_id,
            "independent_thread_id": other_thread,
            "independent_thread_gate": other_gate,
        },
        "agentic_rag_and_moderation": {
            "blocked": first_snapshot["blocked"],
            "needs_review": first_snapshot["needs_review"],
            "accepted_from_review": "boxingai01" in second_snapshot["final_top"],
            "rejected_from_review": "warnewsai1" not in second_snapshot["final_top"],
        },
        "hitl": {
            "first_gate": first_gate,
            "second_gate": second_gate,
            "campaign_status": final_snapshot["campaign_status"],
            "completed": final_snapshot["completed"],
            "final_has_interrupt": bool(final.get("__interrupt__")),
        },
        "snapshots": {
            "first_pause": first_snapshot,
            "after_moderation": second_snapshot,
            "final": final_snapshot,
            "independent_thread": other_snapshot,
        },
    }
    output = PROJECT_ROOT / "demo_results.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
