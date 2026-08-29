"""Невеликий CLI для запуску агента поза notebook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from youtube_trends_agent import YouTubeTrendsAgent
from youtube_trends_agent.factory import create_youtube_client


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Trends ReAct Agent")
    parser.add_argument("query", nargs="?", default="Знайди загальні тренди YouTube за останні 7 днів в Україні")
    parser.add_argument("--mode", choices=["fixture", "html"], default="fixture")
    parser.add_argument("--llm", choices=["gemini", "ollama"], default="gemini")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    agent = YouTubeTrendsAgent(client=create_youtube_client(args.mode), llm_provider=args.llm)
    result = agent.run(args.query, trajectory_path=project_root / "trajectory.json")
    print(json.dumps(result["report"], ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
