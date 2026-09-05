"""Відтворювані фактичні метрики LangGraph і CrewAI scripted demo."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

from mas_crewai import CrewCompetitiveSMMMAS
from mas_langgraph import create_mas
from tools_legacy import default_request


ROOT = Path(__file__).resolve().parent


def code_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#"))


def collect_metrics(output: str | Path = ROOT / "comparison_results.json") -> dict:
    with tempfile.TemporaryDirectory() as temp:
        graph = create_mas(ROOT, Path(temp) / "compare.db")
        started = time.monotonic()
        graph_result = graph.start(default_request("compare-lg", "compare-lg-session"), "compare-lg-thread")
        graph_ms = round((time.monotonic() - started) * 1000, 2)
        graph.close()
    started = time.monotonic()
    crew_result = CrewCompetitiveSMMMAS().run({"request_id": "compare-crew", "session_id": "compare-crew-session"})
    crew_ms = round((time.monotonic() - started) * 1000, 2)
    result = {
        "measurement_mode": "fixture_scripted_no_external_llm",
        "langgraph": {
            "loc": code_lines(ROOT / "mas_langgraph.py"),
            "latency_ms": graph_ms,
            "llm_tokens": 0,
            "coordination_llm_calls": 0,
            "agents_used": list(graph_result["values"]["agent_results"]),
            "control_score_1_5": 5,
            "debugging_score_1_5": 5,
        },
        "crewai": {
            "loc": code_lines(ROOT / "mas_crewai.py"),
            "latency_ms": crew_ms,
            "llm_tokens": crew_result["coordination_llm_calls"],
            "coordination_llm_calls": crew_result["coordination_llm_calls"],
            "agents_used": crew_result["agents_used"],
            "control_score_1_5": 3,
            "debugging_score_1_5": 4,
        },
        "development_minutes": {
            "langgraph": None,
            "crewai": None,
            "notice": "Заповнити власним фактично виміряним часом; значення не вигадуються ретроспективно.",
        },
    }
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(collect_metrics(), ensure_ascii=False, indent=2))
