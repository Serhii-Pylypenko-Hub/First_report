"""CLI для перевірки Document Intake Agent та опційного запуску мовної MAS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from language_mas.document_ingestion import DocumentIntakeAgent
from language_mas.langgraph_mas import create_langgraph_mas
from language_mas.models import ActorContext


def main() -> None:
    parser = argparse.ArgumentParser(description="Безпечне перетворення документа у JSON")
    parser.add_argument("--file", required=True, help="Ім'я файла у fixtures/documents")
    parser.add_argument("--request-id", default="cli-document-intake")
    parser.add_argument("--analyze", action="store_true", help="Запустити мовних агентів до HITL")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    parsed = DocumentIntakeAgent(root / "traces" / "intake_secure.jsonl").parse(
        args.file, request_id=args.request_id
    )
    output: dict = {"intake": parsed}
    if args.analyze and parsed["status"] == "ok":
        actor = ActorContext(tenant_id="cli-tenant", user_id="cli-user")
        mas = create_langgraph_mas()
        mas.start(parsed["data"]["request"], actor, thread_id=f"intake-{args.request_id}")
        output["analysis"] = mas.result(actor, thread_id=f"intake-{args.request_id}")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
