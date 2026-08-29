"""Невеликий CLI для запуску агента поза notebook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from youtube_trends_agent import YouTubeTrendsAgent
from youtube_trends_agent.factory import create_youtube_client
from youtube_trends_agent.reporting import write_html_report
from youtube_trends_agent.testing import ScriptedReActLLM


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Trends ReAct Agent")
    parser.add_argument("query", nargs="?", default="Знайди загальні тренди YouTube за останні 7 днів в Україні")
    parser.add_argument("--mode", choices=["fixture", "html"], default="fixture")
    parser.add_argument(
        "--llm",
        choices=["scripted", "gemini", "ollama"],
        default="scripted",
        help="scripted працює без API-ключа; gemini та ollama запускають реальну LLM",
    )
    parser.add_argument(
        "--format",
        choices=["json", "html", "both"],
        default="both",
        help="Формат результату: JSON у консолі, HTML-файл або обидва",
    )
    parser.add_argument(
        "--output",
        default="youtube_trends_report.html",
        help="Шлях для HTML-звіту",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    llm = ScriptedReActLLM() if args.llm == "scripted" else None
    provider = None if args.llm == "scripted" else args.llm
    agent = YouTubeTrendsAgent(
        client=create_youtube_client(args.mode),
        llm=llm,
        llm_provider=provider,
    )
    result = agent.run(args.query, trajectory_path=project_root / "trajectory.json")
    if args.format in {"json", "both"}:
        print(json.dumps(result["report"], ensure_ascii=False, indent=2, default=str))
    if args.format in {"html", "both"}:
        output_path = write_html_report(result["report"], args.output)
        print(f"\nHTML-звіт збережено: {output_path}")


if __name__ == "__main__":
    main()
