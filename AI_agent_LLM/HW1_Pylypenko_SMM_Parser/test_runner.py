"""Запуск 5 тест-кейсів і формування обов'язкових JSON-артефактів."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from youtube_trends_agent.agent import YouTubeTrendsAgent
from youtube_trends_agent.factory import DEFAULT_FIXTURE
from youtube_trends_agent.llm_factory import create_chat_model
from youtube_trends_agent.safety import SafetyConfig
from youtube_trends_agent.testing import LoopingToolLLM, ScriptedReActLLM, SlowScriptedLLM
from youtube_trends_agent.youtube_client import FixtureYouTubeClient


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


TEST_CASES = [
    {
        "id": "TC-001",
        "query": "Знайди загальні тренди YouTube за останні 7 днів в Україні та сформуй топ-20",
        "expected": "Загальний рейтинг за переглядами та trend score з посиланнями",
        "complexity": "medium",
        "scenario": "normal",
    },
    {
        "id": "TC-002",
        "query": "Знайди тренди YouTube про AI agents за останні 7 днів і сформуй топ-20",
        "expected": "Тематичний рейтинг відео про AI agents",
        "complexity": "complex",
        "scenario": "normal",
    },
    {
        "id": "TC-003",
        "query": "Знайди тренди про маркетинг за останні 7 днів",
        "expected": "Контрольована часткова відповідь через max_steps",
        "complexity": "guardrail",
        "scenario": "max_steps",
    },
    {
        "id": "TC-004",
        "query": "Знайди загальні тренди за тиждень",
        "expected": "Контрольована часткова відповідь через timeout",
        "complexity": "guardrail",
        "scenario": "timeout",
    },
    {
        "id": "TC-005",
        "query": "Знайди тренди про AI",
        "expected": "Зупинка після трьох однакових tool calls",
        "complexity": "guardrail",
        "scenario": "loop",
    },
]


def primary_llm():
    """Gemini для ручного прогону з ключем; test double — для офлайн CI."""

    if os.getenv("RUN_GEMINI_TESTS") == "1" and os.getenv("GOOGLE_API_KEY"):
        return create_chat_model("gemini"), "gemini-2.5-flash"
    return ScriptedReActLLM(), "scripted_test_double"


def build_agent(scenario: str) -> tuple[YouTubeTrendsAgent, str]:
    client = FixtureYouTubeClient(DEFAULT_FIXTURE)
    if scenario == "normal":
        llm, provider = primary_llm()
        return YouTubeTrendsAgent(client=client, llm=llm), provider
    if scenario == "max_steps":
        return (
            YouTubeTrendsAgent(
                client=client,
                llm=ScriptedReActLLM(),
                safety=SafetyConfig(max_steps=2, timeout_seconds=120, max_repeats=3),
            ),
            "scripted_guardrail_demo",
        )
    if scenario == "timeout":
        return (
            YouTubeTrendsAgent(
                client=client,
                llm=SlowScriptedLLM(),
                safety=SafetyConfig(max_steps=12, timeout_seconds=0.005, max_repeats=3),
            ),
            "scripted_guardrail_demo",
        )
    return (
        YouTubeTrendsAgent(
            client=client,
            llm=LoopingToolLLM(),
            safety=SafetyConfig(max_steps=12, timeout_seconds=120, max_repeats=3),
        ),
        "scripted_loop_demo",
    )


def main() -> None:
    results: list[dict] = []
    trajectories: list[dict] = []
    for test_case in TEST_CASES:
        agent, provider = build_agent(test_case["scenario"])
        run = agent.run(test_case["query"])
        report = run["report"]
        results.append(
            {
                "test_id": test_case["id"],
                "query": test_case["query"],
                "expected": test_case["expected"],
                "actual": report["summary"][:500],
                "status": report["status"],
                "stop_reason": report["stop_reason"],
                "steps": run["steps"],
                "tool_calls": run["tool_calls"],
                "elapsed_ms": run["elapsed_ms"],
                "complexity": test_case["complexity"],
                "llm_provider": provider,
                "data_mode": "fixture",
                "max_steps_reached": report["stop_reason"] == "max_steps",
                "timeout_reached": report["stop_reason"] == "timeout",
                "loop_detected": report["stop_reason"] == "loop_detected",
            }
        )
        trajectories.append(run["trajectory"])

    (ROOT / "test_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (ROOT / "trajectory.json").write_text(
        json.dumps({"runs": trajectories}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Збережено {len(results)} тест-кейсів у test_results.json")
    for row in results:
        print(
            f"{row['test_id']}: {row['status']} / {row['stop_reason']} "
            f"({row['steps']} steps, {row['elapsed_ms']} ms)"
        )


if __name__ == "__main__":
    main()
