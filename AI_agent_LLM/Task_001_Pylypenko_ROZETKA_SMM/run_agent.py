"""CLI для start/resume/state із file-backed persistence."""

from __future__ import annotations

import argparse
import json

from rozetka_smm_agent.factory import create_agent
from rozetka_smm_agent.reporting import DEFAULT_REQUEST


def parse_decision(raw: str, *, reason: str = "", path: str | None = None) -> dict:
    """Прийняти просте CLI-рішення або повний JSON без залежності від shell quoting."""

    normalized = raw.strip().lower()
    if normalized in {"approve", "edit", "reject"}:
        payload: dict = {"decision": normalized}
    else:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Некоректне рішення. Використайте --decision approve, "
                "--decision reject або валідний JSON."
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON-рішення повинно бути об'єктом.")
    if reason:
        payload["reason"] = reason
    if path:
        payload["path"] = path
    return payload


def view(agent, thread_id: str) -> dict:
    snapshot = agent.state(thread_id=thread_id)
    result = agent.result(thread_id=thread_id)
    result["execution"] = {
        "thread_id": thread_id,
        "next": list(snapshot.next),
        "pending_gate": agent.pending_gate(thread_id=thread_id),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="ROZETKA cross-platform SMM Agent")
    parser.add_argument("--llm", choices=["scripted", "gemini", "ollama"], default="scripted")
    parser.add_argument("--live", action="store_true", help="Спробувати public HTML перед fallback")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("request", nargs="?", default=DEFAULT_REQUEST)
    start.add_argument("--thread-id", default="rozetka-demo")

    resume = sub.add_parser("resume")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument(
        "--decision",
        required=True,
        help="approve/edit/reject або повний JSON-об'єкт",
    )
    resume.add_argument("--reason", default="", help="Причина рішення для audit trail")
    resume.add_argument("--path", help="Новий відносний JSON-шлях для рішення edit")

    state = sub.add_parser("state")
    state.add_argument("--thread-id", required=True)
    args = parser.parse_args()

    agent = create_agent(provider=args.llm, live_enabled=args.live)
    try:
        if args.command == "start":
            agent.start(args.request, thread_id=args.thread_id)
        elif args.command == "resume":
            try:
                decision = parse_decision(args.decision, reason=args.reason, path=args.path)
                agent.resume(decision, thread_id=args.thread_id)
            except ValueError as exc:
                parser.error(str(exc))
        print(json.dumps(view(agent, args.thread_id), ensure_ascii=False, indent=2, default=str))
    finally:
        agent.close()


if __name__ == "__main__":
    main()
