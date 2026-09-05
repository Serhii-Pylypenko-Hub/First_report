"""CLI для відтворюваного та native CrewAI запусків."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from language_mas.crewai_mas import create_crewai_mas
from language_mas.models import ActorContext


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="CrewAI MAS для перевірки українського тексту")
    parser.add_argument("--input", default=str(ROOT / "fixtures" / "demo_request.json"))
    parser.add_argument("--mode", choices=["scripted", "native"], default="scripted")
    parser.add_argument("--model", default=os.getenv("CREWAI_MODEL", "gemini/gemini-2.5-flash"))
    parser.add_argument("--tenant-id", default="demo-tenant")
    parser.add_argument("--user-id", default="demo-user")
    args = parser.parse_args()

    request = json.loads(Path(args.input).read_text(encoding="utf-8"))
    actor = ActorContext(tenant_id=args.tenant_id, user_id=args.user_id)
    mas = create_crewai_mas(trace_path=ROOT / "traces" / "crewai_secure.jsonl")
    result = mas.run_scripted(request, actor) if args.mode == "scripted" else mas.run_native(request, actor, model=args.model)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
