"""CLI: start/resume/state для LangGraph MAS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from language_mas.correction_memory import UserCorrectionMemory
from language_mas.langgraph_mas import create_langgraph_mas
from language_mas.models import ActorContext
from language_mas.reporting import save_corrected_document


ROOT = Path(__file__).resolve().parent


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Безпечна LangGraph MAS для перевірки українського тексту")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--input", default=str(ROOT / "fixtures" / "demo_request.json"))
    start.add_argument("--thread-id", default="language-demo")
    start.add_argument("--tenant-id", default="demo-tenant")
    start.add_argument("--user-id", default="demo-user")
    start.add_argument("--review-template", default=str(ROOT / "outputs" / "review_template.json"))
    resume = sub.add_parser("resume")
    resume.add_argument("--review", required=True, help="Шлях до JSON із decisions")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument("--tenant-id", default="demo-tenant")
    resume.add_argument("--user-id", default="demo-user")
    state = sub.add_parser("state")
    state.add_argument("--thread-id", required=True)
    state.add_argument("--tenant-id", default="demo-tenant")
    state.add_argument("--user-id", default="demo-user")
    args = parser.parse_args()

    with SqliteSaver.from_conn_string(str(ROOT / "workflow_state.db")) as saver:
        mas = create_langgraph_mas(
            checkpointer=saver,
            trace_path=ROOT / "traces" / "langgraph_secure.jsonl",
            correction_memory=UserCorrectionMemory(ROOT / "user_correction_memory.db"),
        )
        if args.command == "start":
            actor = ActorContext(tenant_id=args.tenant_id, user_id=args.user_id)
            mas.start(
                _read_json(args.input),
                actor,
                thread_id=args.thread_id,
            )
            pending = mas.result(actor, thread_id=args.thread_id)
            findings = [*pending.get("certain_findings", []), *pending.get("needs_review", [])]
            if findings:
                template = {
                    "request_id": pending["request_id"],
                    "decisions": [
                        {"finding_id": item["finding_id"], "decision": "reject", "reason": "Змініть рішення після перегляду"}
                        for item in findings
                    ],
                }
                target = Path(args.review_template)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        elif args.command == "resume":
            actor = ActorContext(tenant_id=args.tenant_id, user_id=args.user_id)
            mas.resume(_read_json(args.review), actor, thread_id=args.thread_id)
        else:
            actor = ActorContext(tenant_id=args.tenant_id, user_id=args.user_id)
        result = mas.result(actor, thread_id=args.thread_id)
        if result.get("status") == "completed" and result.get("corrected_document"):
            result["corrected_text_path"] = str(save_corrected_document(
                result, ROOT / "outputs" / f'corrected_{result["request_id"]}.txt'
            ))
            mas.tracer.emit(
                "corrected_copy_saved", request_id=result["request_id"], status="completed",
                output_name=Path(result["corrected_text_path"]).name,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
