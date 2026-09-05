from __future__ import annotations

from pathlib import Path

from hitl import approve_all_payload, reject_all_payload
from hw3_smm.models import ExecutionPlan, PlanOperation, PlanStep
from mas_langgraph import create_mas
from tools_legacy import default_request, export_smm_report_payload


def test_structured_plan_does_not_route_by_text_marker():
    step = PlanStep(step_id=1, operation=PlanOperation.GENERATE_DRAFTS, agent_name="strategist", arguments={"description": "довільний текст без маркера"})
    assert step.operation is PlanOperation.GENERATE_DRAFTS


def test_plan_rejects_invalid_dependency():
    import pytest
    with pytest.raises(ValueError):
        ExecutionPlan(goal="Достатньо довга ціль", steps=[
            PlanStep(step_id=1, operation=PlanOperation.SEARCH_KNOWLEDGE, agent_name="r", depends_on=[2]),
            PlanStep(step_id=2, operation=PlanOperation.GENERATE_DRAFTS, agent_name="s"),
            PlanStep(step_id=3, operation=PlanOperation.VERIFY_RESULTS, agent_name="v"),
        ])


def test_full_graph_outputs_every_agent_and_pauses_twice(tmp_path):
    mas = create_mas(Path(__file__).parents[1], tmp_path / "state.db")
    state = mas.start(default_request("flow-001", "session-flow"), "thread-flow")
    assert state["next"] == ["approval_gate"]
    assert len(state["values"]["posts"]) == 50
    assert len(state["values"]["drafts"]) == 5
    assert len(state["values"]["analysis"]["recommendations"]) == 5
    assert {"collector", "researcher", "analyst", "strategist", "language", "verifier"} <= set(state["values"]["agent_results"])
    state = mas.resume_selection("thread-flow", approve_all_payload(state))
    assert state["next"] == ["risky_export"]
    state = mas.resume_export("thread-flow", "edit", "outputs/test_report.json")
    assert state["values"]["status"] == "completed"
    assert (Path(__file__).parents[1] / "outputs" / "test_report.json").exists()


def test_reject_all_filters_everything(tmp_path):
    mas = create_mas(Path(__file__).parents[1], tmp_path / "reject.db")
    state = mas.start(default_request("flow-002", "session-reject"), "thread-reject")
    state = mas.resume_selection("thread-reject", reject_all_payload())
    assert state["values"]["approved_drafts"] == []
    state = mas.resume_export("thread-reject", "reject")
    assert state["values"]["status"] == "rejected"


def test_approve_export_and_persistence_across_process_like_instances(tmp_path):
    root = Path(__file__).parents[1]
    database = tmp_path / "persistent.db"
    first = create_mas(root, database)
    state = first.start(default_request("flow-approve", "session-approve"), "thread-persistent")
    first.close()
    second = create_mas(root, database)
    restored = second.state("thread-persistent")
    assert restored["next"] == ["approval_gate"]
    restored = second.resume_selection("thread-persistent", approve_all_payload(restored))
    assert restored["next"] == ["risky_export"]
    restored = second.resume_export("thread-persistent", "approve")
    assert restored["values"]["export_result"]["status"] == "ok"
    second.close()


def test_supervisor_supports_with_structured_output(tmp_path):
    class Structured:
        def invoke(self, messages):
            from hw3_smm.models import RouteDecision
            assert messages[0][0] == "system"
            return RouteDecision(action="research", reasoning="Тест structured output")

    class Router:
        def with_structured_output(self, schema):
            from hw3_smm.models import RouteDecision
            assert schema is RouteDecision
            return Structured()

    mas = create_mas(Path(__file__).parents[1], tmp_path / "router.db", router_model=Router())
    request = default_request("route-001", "session-route").model_copy(update={"user_query": "Довільний запит"})
    state = mas.start(request, "thread-router")
    assert state["values"]["route"]["action"] == "research"
    mas.close()


def test_export_blocks_traversal_and_is_idempotent(tmp_path):
    blocked = export_smm_report_payload("../bad.json", {}, "abcdefgh", project_root=tmp_path)
    assert blocked["status"] == "error"
    first = export_smm_report_payload("outputs/good.json", {"ok": True}, "unique-key-1", project_root=tmp_path)
    second = export_smm_report_payload("outputs/good.json", {"ok": True}, "unique-key-1", project_root=tmp_path)
    assert first["status"] == second["status"] == "ok"
    assert second["data"]["idempotent_replay"] is True


def test_no_nan_and_ad_ranking_is_honest(tmp_path):
    mas = create_mas(Path(__file__).parents[1], tmp_path / "nan.db")
    state = mas.start(default_request("flow-003", "session-nan"), "thread-nan")
    posts = state["values"]["analysis"]["posts"]
    assert all(row["views"] is not None or row["views_status"] != "available" for row in posts)
    assert all(row["ad_status"] == "confirmed" for row in state["values"]["analysis"]["ad_rankings"]["top_by_views"])
