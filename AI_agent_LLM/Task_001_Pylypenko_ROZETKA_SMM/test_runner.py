"""Створити демонстраційні артефакти approve/reject і persistence."""

from __future__ import annotations

import json
from pathlib import Path

from rozetka_smm_agent.factory import create_agent
from rozetka_smm_agent.reporting import DEFAULT_REQUEST


def snapshot(agent, thread_id: str) -> dict:
    state = agent.state(thread_id=thread_id)
    result = agent.result(thread_id=thread_id)
    result["next"] = list(state.next)
    return result


def main() -> None:
    approve_thread = "submission-approve"
    agent = create_agent(provider="scripted")
    agent.start(DEFAULT_REQUEST, thread_id=approve_thread)
    paused = snapshot(agent, approve_thread)
    gate = agent.pending_gate(thread_id=approve_thread)
    agent.close()

    restored = create_agent(provider="scripted")
    restored_before = snapshot(restored, approve_thread)
    restored.resume({"decision": "approve"}, thread_id=approve_thread)
    approved = snapshot(restored, approve_thread)

    reject_thread = "submission-reject"
    restored.start(DEFAULT_REQUEST, thread_id=reject_thread)
    restored.resume(
        {"decision": "reject", "reason": "Демонстрація відмови оператора"},
        thread_id=reject_thread,
    )
    rejected = snapshot(restored, reject_thread)
    restored.close()

    payload = {
        "single_agent": True,
        "react_guardrails": {"max_steps": 10, "timeout_seconds": 120, "repeat_detection": True},
        "approve_flow": {
            "paused": paused,
            "gate": gate,
            "restored_same_state": paused == restored_before,
            "final": approved,
        },
        "reject_flow": rejected,
    }
    Path("demo_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
