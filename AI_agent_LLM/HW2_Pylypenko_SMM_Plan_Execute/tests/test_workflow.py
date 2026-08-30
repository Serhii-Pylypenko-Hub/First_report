"""Інтеграційні тести Plan-and-Execute, RAG, persistence та HITL."""

from __future__ import annotations

from pathlib import Path

from smm_plan_agent.factory import PROJECT_ROOT
from smm_plan_agent.graph import SMMPlanExecuteAgent
from smm_plan_agent.scripted import ScriptedPlanExecuteLLM


REQUEST = "Проаналізуй YouTube тренди про AI agents та заплануй кампанію"


def make_agent(tmp_path: Path) -> SMMPlanExecuteAgent:
    return SMMPlanExecuteAgent(
        llm=ScriptedPlanExecuteLLM(),
        fixture_path=PROJECT_ROOT / "fixtures" / "youtube_videos.json",
        knowledge_documents_path=PROJECT_ROOT / "knowledge_documents.json",
        chroma_path=tmp_path / "chroma",
        db_path=tmp_path / "state.db",
        action_log_path=tmp_path / "actions.jsonl",
    )


def test_first_pause_has_two_lists_and_hard_blocks(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    result = agent.start(REQUEST, thread_id="case-1")
    state = agent.state(thread_id="case-1").values
    assert result["__interrupt__"][0].value["gate"] == "content_moderation"
    assert len(state["plan"]) == 4
    assert state["current_step"] == 3
    assert {item["video"]["video_id"] for item in state["blocked"]} == {
        "adultbad01",
        "violent001",
    }
    assert {item["video"]["video_id"] for item in state["needs_review"]} == {
        "boxingai01",
        "warnewsai1",
    }
    assert state["tool_history"] == [
        "search_recent_videos",
        "search_knowledge",
        "evaluate_trends",
    ]
    assert agent.knowledge_base.collection.count() >= 8
    agent.close()


def test_human_selection_is_merged_into_existing_top(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    agent.start(REQUEST, thread_id="case-2")
    result = agent.resume(
        {"decision": "approve_selected", "acceptable_video_ids": ["boxingai01"]},
        thread_id="case-2",
    )
    state = agent.state(thread_id="case-2").values
    ids = [item["video"]["video_id"] for item in state["final_top"]]
    assert "boxingai01" in ids
    assert "warnewsai1" not in ids
    assert result["__interrupt__"][0].value["gate"] == "campaign_approval"
    agent.close()


def test_campaign_reject_does_not_execute_risky_tool(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    agent.start(REQUEST, thread_id="case-3")
    agent.resume({"decision": "reject_all"}, thread_id="case-3")
    result = agent.resume(
        {"decision": "reject", "reason": "Кампанія потребує доопрацювання"},
        thread_id="case-3",
    )
    state = agent.state(thread_id="case-3").values
    assert not result.get("__interrupt__")
    assert state["completed"] is True
    assert state["campaign_status"] == "rejected"
    assert not (tmp_path / "actions.jsonl").exists()
    agent.close()


def test_persistence_survives_agent_recreation_and_threads_are_isolated(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    agent.start(REQUEST, thread_id="persistent")
    before = agent.state(thread_id="persistent").values["current_step"]
    agent.close()

    agent = make_agent(tmp_path)
    assert agent.state(thread_id="persistent").values["current_step"] == before
    agent.start(REQUEST, thread_id="other")
    assert agent.state(thread_id="other").config["configurable"]["thread_id"] == "other"
    assert agent.state(thread_id="persistent").config["configurable"]["thread_id"] == "persistent"
    agent.close()


def test_campaign_edit_validates_and_executes_changed_parameters(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    agent.start(REQUEST, thread_id="case-edit")
    agent.resume({"decision": "reject_all"}, thread_id="case-edit")
    agent.resume(
        {
            "decision": "edit",
            "edits": {
                "planned_date": "2026-09-05",
                "note": "Оновлено людиною перед виконанням.",
            },
        },
        thread_id="case-edit",
    )
    state = agent.state(thread_id="case-edit").values
    action = (tmp_path / "actions.jsonl").read_text(encoding="utf-8")
    assert state["campaign_status"] == "scheduled"
    assert '"planned_date": "2026-09-05"' in action
    assert "Оновлено людиною" in action
    agent.close()
