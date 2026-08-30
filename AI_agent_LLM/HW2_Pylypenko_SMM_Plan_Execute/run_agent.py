"""CLI: start/resume/state для демонстрації persistence між процесами."""

from __future__ import annotations

import argparse
import json

from smm_plan_agent.factory import create_agent


DEFAULT_REQUEST = (
    "Проаналізуй YouTube тренди про AI agents за останні 7 днів, "
    "перевір brand safety та заплануй SMM-кампанію"
)


def _view(agent, thread_id: str, result: dict | None = None) -> dict:
    state = agent.state(thread_id=thread_id)
    values = state.values
    interrupts = []
    if result:
        interrupts = [item.value for item in result.get("__interrupt__", [])]
    return {
        "thread_id": thread_id,
        "goal": values.get("goal"),
        "plan": values.get("plan", []),
        "current_step": values.get("current_step", 0),
        "last_tool": values.get("last_tool"),
        "tool_history": values.get("tool_history", []),
        "approved_count": len(values.get("approved", [])),
        "needs_review_count": len(values.get("needs_review", [])),
        "blocked_count": len(values.get("blocked", [])),
        "final_top": [item["video"]["video_id"] for item in values.get("final_top", [])],
        "campaign_status": values.get("campaign_status"),
        "completed": values.get("completed", False),
        "interrupts": interrupts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SMM Plan-and-Execute Agent")
    parser.add_argument("--llm", choices=["scripted", "gemini", "ollama"], default="scripted")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Почати новий workflow")
    start.add_argument("request", nargs="?", default=DEFAULT_REQUEST)
    start.add_argument("--thread-id", default="demo-session")

    resume = sub.add_parser("resume", help="Продовжити interrupt із тієї самої SQLite БД")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument(
        "--decision",
        required=True,
        help='JSON, наприклад {"decision":"approve_all"} або {"decision":"approve"}',
    )

    state = sub.add_parser("state", help="Переглянути збережений checkpoint")
    state.add_argument("--thread-id", required=True)
    args = parser.parse_args()

    agent = create_agent(provider=args.llm)
    try:
        if args.command == "start":
            result = agent.start(args.request, thread_id=args.thread_id)
            output = _view(agent, args.thread_id, result)
        elif args.command == "resume":
            decision = json.loads(args.decision)
            result = agent.resume(decision, thread_id=args.thread_id)
            output = _view(agent, args.thread_id, result)
        else:
            output = _view(agent, args.thread_id)
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    finally:
        agent.close()


if __name__ == "__main__":
    main()
