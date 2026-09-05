"""CLI запуск того самого ядра, що використовується у Jupyter Notebook."""

from __future__ import annotations

import argparse
import json
import sys

from hitl import approve_all_payload, reject_all_payload
from mas_langgraph import create_mas
from tools_legacy import default_request


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ROZETKA Competitive SMM MAS")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--thread-id", required=True)
    start.add_argument("--full", action="store_true")
    state = sub.add_parser("state")
    state.add_argument("--thread-id", required=True)
    state.add_argument("--full", action="store_true")
    review = sub.add_parser("review")
    review.add_argument("--thread-id", required=True)
    review.add_argument("--decision", choices=["approve", "reject"], required=True)
    review.add_argument("--full", action="store_true")
    export = sub.add_parser("export")
    export.add_argument("--thread-id", required=True)
    export.add_argument("--decision", choices=["approve", "reject", "edit"], required=True)
    export.add_argument("--path")
    export.add_argument("--full", action="store_true")
    args = parser.parse_args()
    mas = create_mas()
    try:
        if args.command == "start":
            result = mas.start(default_request(args.thread_id, f"session-{args.thread_id}"), args.thread_id)
        elif args.command == "state":
            result = mas.state(args.thread_id)
        elif args.command == "review":
            current = mas.state(args.thread_id)
            if not current.get("values"):
                parser.error(f"thread-id '{args.thread_id}' не знайдено; спочатку виконайте start")
            payload = approve_all_payload(current) if args.decision == "approve" else reject_all_payload()
            result = mas.resume_selection(args.thread_id, payload)
        else:
            current = mas.state(args.thread_id)
            if not current.get("values"):
                parser.error(f"thread-id '{args.thread_id}' не знайдено; спочатку виконайте start")
            result = mas.resume_export(args.thread_id, args.decision, args.path)
    finally:
        mas.close()
    if args.full:
        shown = result
    else:
        values = result.get("values", {})
        missing = not values
        shown = {
            "status": "not_found" if missing else values.get("status"),
            "next": result.get("next", []),
            "brands": list(values.get("analysis", {}).get("brand_summary", {})),
            "posts": len(values.get("posts", [])),
            "top_ads": len(values.get("analysis", {}).get("ad_rankings", {}).get("top_by_normalized_score", [])),
            "drafts": len(values.get("drafts", [])),
            "approved_drafts": len(values.get("approved_drafts", [])),
            "export_result": values.get("export_result"),
            "instruction": (
                f"Thread '{args.thread_id}' не знайдено. Спочатку виконайте start."
                if missing else
                "Виконайте review --decision approve/reject."
                if result.get("next") == ["approval_gate"] else
                "Виконайте export --decision approve/reject/edit."
                if result.get("next") == ["risky_export"] else
                "Workflow завершено."
            ),
        }
    print(json.dumps(shown, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
