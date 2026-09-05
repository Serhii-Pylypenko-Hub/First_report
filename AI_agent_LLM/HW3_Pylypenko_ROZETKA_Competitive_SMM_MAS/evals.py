"""Scenario-based evals усього MAS із потрібними полями результату."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from mas_langgraph import create_mas
from tools_legacy import default_request


ROOT = Path(__file__).resolve().parent
SCENARIOS = [
    ("EVAL-01", "Порівняй конкурентів і запропонуй рекламні пости", "Повний workflow зупиняється на HITL", "approval_gate"),
    ("EVAL-02", "Знайди правила нормалізації метрик у RAG", "Supervisor маршрутизує до researcher", None),
    ("EVAL-03", "Лише аналіз метрик конкурентної реклами", "Supervisor маршрутизує до analyst", None),
    ("EVAL-04", "Створи п'ять варіантів рекламних постів", "Plan-and-Execute створює 4–5 чернеток", None),
    ("EVAL-05", "Перевір мову та орфографію рекламних постів", "Мовна MAS повертає findings", None),
]


def run_evals(output_path: str | Path = ROOT / "eval_results.json") -> list[dict]:
    results = []
    with tempfile.TemporaryDirectory() as temp:
        mas = create_mas(ROOT, Path(temp) / "eval_state.db")
        for index, (scenario_id, query, expected, expected_next) in enumerate(SCENARIOS, start=1):
            started = time.monotonic()
            request = default_request(f"eval-{index:03d}", f"eval-session-{index}").model_copy(update={"user_query": query})
            state = mas.start(request, f"eval-thread-{index}")
            values = state["values"]
            route = values.get("route", {}).get("action")
            passed = values.get("status") != "blocked"
            if expected_next:
                passed = passed and state["next"] == [expected_next]
            if scenario_id == "EVAL-04":
                passed = passed and 4 <= len(values.get("drafts", [])) <= 5
            if scenario_id == "EVAL-05":
                passed = passed and values.get("language_review", {}).get("verifier", {}).get("status") == "completed"
            agents = list(values.get("agent_results", {}))
            tools = []
            if "collector" in agents: tools.append("collect_brand_posts")
            if "researcher" in agents: tools.append("search_smm_knowledge")
            if "analyst" in agents: tools.append("calculate_competitive_metrics")
            if "strategist" in agents: tools.append("generate_content_brief")
            results.append({
                "scenario_id": scenario_id,
                "query": query,
                "expected_behavior": expected,
                "actual": {"route": route, "status": values.get("status"), "next": state["next"]},
                "pass": passed,
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "agents_used": agents,
                "tools_called": tools,
            })
        mas.close()
    Path(output_path).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    rows = run_evals()
    print(json.dumps({"passed": sum(row["pass"] for row in rows), "total": len(rows)}, ensure_ascii=False))
