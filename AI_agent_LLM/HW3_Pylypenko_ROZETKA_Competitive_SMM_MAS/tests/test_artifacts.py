from __future__ import annotations

import json
from pathlib import Path

import nbformat

from mas_crewai import CrewCompetitiveSMMMAS
from mas_langgraph import create_mas
from tools_legacy import default_request
from trajectory_logger import TrajectoryLogger


ROOT = Path(__file__).parents[1]


def test_required_artifacts_exist():
    required = [
        "mas_langgraph.py", "mas_crewai.py", "mcp_server.py", "test_mcp_server.py",
        "tools_legacy.py", "trajectory_logger.py", "agent_state.db", "trajectory.json",
        "guardrails.py", "hitl.py", "observability.py", "evals.py", "red_team.py",
        "eval_results.json", "red_team_results.json", "comparison_results.json",
        "README.md", "USER_GUIDE.md", "requirements.txt", ".env.example",
        "HW3_Пилипенко_ROZETKA_Competitive_SMM_MAS.ipynb",
    ]
    assert not [name for name in required if not (ROOT / name).exists()]


def test_notebook_is_executed_and_contains_user_ui():
    notebook = nbformat.read(ROOT / "HW3_Пилипенко_ROZETKA_Competitive_SMM_MAS.ipynb", as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code_cells)
    content = "\n".join(cell.source for cell in notebook.cells)
    assert "display_review_widget" in content
    assert "Вибрати всю TOP-рекламу" in (ROOT / "notebook_ui.py").read_text(encoding="utf-8")
    assert "Попередження про заборонені теми" in content
    assert "Фінальний статус" in content


def test_eval_and_red_team_outputs_have_five_passing_cases():
    evals = json.loads((ROOT / "eval_results.json").read_text(encoding="utf-8"))
    red = json.loads((ROOT / "red_team_results.json").read_text(encoding="utf-8"))
    assert len(evals) >= 5 and all(item["pass"] for item in evals)
    assert len(red) >= 5 and all(item["pass"] for item in red)


def test_trajectory_is_hash_chained_and_has_agent_name():
    rows = json.loads((ROOT / "trajectory.json").read_text(encoding="utf-8"))
    assert rows and all(row.get("agent_name") for row in rows)
    assert TrajectoryLogger(ROOT / "trajectory.json").verify()


def test_crewai_scripted_case_has_same_five_brands_and_drafts():
    result = CrewCompetitiveSMMMAS().run({"request_id": "artifact-crew", "session_id": "artifact-session"})
    assert len(result["analysis"]["brand_summary"]) == 5
    assert len(result["drafts"]) == 5


def test_langgraph_cli_and_crewai_scripted_results_are_equivalent(tmp_path):
    """Обидві реалізації мають повертати ті самі детерміновані бізнес-результати."""
    langgraph = create_mas(ROOT, tmp_path / "parity.db")
    state = langgraph.start(
        default_request("parity-langgraph", "parity-session"),
        "parity-thread",
    )["values"]
    crewai = CrewCompetitiveSMMMAS().run(
        {"request_id": "parity-crewai", "session_id": "parity-session"}
    )
    langgraph.close()

    assert state["analysis"]["brand_summary"] == crewai["analysis"]["brand_summary"]
    assert state["analysis"]["ad_rankings"] == crewai["analysis"]["ad_rankings"]
    assert [draft["text"] for draft in state["drafts"]] == [
        draft["text"] for draft in crewai["drafts"]
    ]
    assert state["language_review"] == crewai["language_review"]
