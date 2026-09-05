"""Бонус: той самий кейс у CrewAI з безпечним scripted demo без API-витрат."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from guardrails import input_guardrail, redact_pii
from hw3_smm.content import generate_drafts
from hw3_smm.language_review import apply_language_fixes, review_drafts
from hw3_smm.react import GuardedCollectorReAct
from tools_legacy import calculate_competitive_metrics_payload, default_request, search_smm_knowledge_payload


ROOT = Path(__file__).resolve().parent


def create_crew():
    """Створити справжні CrewAI Agent/Task; kickoff потребує налаштованого LLM."""
    from crewai import Agent, Crew, Process, Task

    collector = Agent(role="Content Intelligence Collector", goal="Зібрати верифіковані пости п'яти брендів", backstory="ReAct-аналітик джерел", allow_delegation=False, verbose=False)
    analyst = Agent(role="Competitive Analyst", goal="Порівняти рекламу, аудиторії та funnel", backstory="Маркетинговий аналітик", allow_delegation=False, verbose=False)
    strategist = Agent(role="Content Strategist", goal="Створити оригінальні brief і рекламні пости", backstory="SMM-стратег", allow_delegation=False, verbose=False)
    verifier = Agent(role="Language and Safety Verifier", goal="Перевірити мову, докази й brand safety", backstory="Незалежний редактор", allow_delegation=False, verbose=False)
    tasks = [
        Task(description="Збери fixture-пости всіх брендів.", expected_output="JSON постів", agent=collector),
        Task(description="Порівняй метрики, теми, аудиторію та funnel.", expected_output="JSON-аналітика", agent=analyst),
        Task(description="Створи п'ять оригінальних постів.", expected_output="П'ять чернеток", agent=strategist),
        Task(description="Перевір мову і безпеку чернеток.", expected_output="Перевірені пости", agent=verifier),
    ]
    return Crew(agents=[collector, analyst, strategist, verifier], tasks=tasks, process=Process.sequential, verbose=False)


class CrewCompetitiveSMMMAS:
    """Відтворюваний локальний прогін тих самих ролей для чесного порівняння."""

    def run(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.monotonic()
        parsed = default_request() if request is None else default_request(request.get("request_id", "crew-demo"), request.get("session_id", "crew-session"))
        safe, alerts = input_guardrail(parsed.user_query)
        if not safe:
            return {"status": "blocked", "alerts": alerts}
        collector = GuardedCollectorReAct().run(
            [parsed.target_brand.value, *[item.value for item in parsed.competitors]],
            [item.value for item in parsed.platforms], parsed.period_days,
        )
        rag = search_smm_knowledge_payload("реклама аудиторія funnel нормалізація", 5)
        analysis_result = calculate_competitive_metrics_payload(collector["posts"], parsed.top_k)
        analysis = analysis_result["data"]
        drafts = generate_drafts(analysis, parsed.draft_count)
        language = review_drafts(drafts, ROOT)
        corrected = apply_language_fixes(drafts, language["verifier"]["findings"])
        output, pii = redact_pii({
            "status": "awaiting_approval",
            "analysis": analysis,
            "drafts": corrected,
            "language_review": language,
            "agents_used": ["collector", "researcher", "analyst", "strategist", "language", "verifier"],
            "tools_called": ["collect_brand_posts", "search_smm_knowledge", "calculate_competitive_metrics", "generate_content_brief"],
            "coordination_llm_calls": 0,
            "rag": rag,
        })
        output["pii_types_redacted"] = pii
        output["elapsed_ms"] = round((time.monotonic() - started) * 1000, 2)
        return output


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Альтернативна CrewAI-реалізація конкурентного SMM-аналізу")
    parser.add_argument("--full", action="store_true", help="Показати повний технічний JSON")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = CrewCompetitiveSMMMAS().run()
    shown = result if args.full else {
        "status": result["status"],
        "brands": list(result["analysis"]["brand_summary"]),
        "posts": len(result["analysis"]["posts"]),
        "top_ads": len(result["analysis"]["ad_rankings"]["top_by_normalized_score"]),
        "drafts": len(result["drafts"]),
        "language_findings": len(result["language_review"]["verifier"]["findings"]),
        "agents_used": result["agents_used"],
        "tools_called": result["tools_called"],
        "elapsed_ms": result["elapsed_ms"],
    }
    print(json.dumps(shown, ensure_ascii=False, indent=2, default=str))
