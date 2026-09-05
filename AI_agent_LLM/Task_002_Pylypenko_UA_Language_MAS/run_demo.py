"""Повний offline demo без API: LangGraph HITL, CrewAI parity, TXT і JSON."""

from __future__ import annotations

import json
from pathlib import Path

from language_mas.crewai_mas import create_crewai_mas
from language_mas.fixtures import demo_review_payload, load_fixture
from language_mas.langgraph_mas import create_langgraph_mas
from language_mas.models import ActorContext
from language_mas.reporting import save_corrected_document, save_text_report


ROOT = Path(__file__).resolve().parent


def main() -> None:
    request = load_fixture()
    actor = ActorContext(tenant_id="demo-tenant", user_id="demo-user")
    graph = create_langgraph_mas(trace_path=ROOT / "traces" / "langgraph_demo_secure.jsonl")
    graph.start(request, actor, thread_id="offline-demo")
    pending = graph.result(actor, thread_id="offline-demo")

    review = demo_review_payload(pending)
    graph.resume(review, actor, thread_id="offline-demo")
    final = graph.result(actor, thread_id="offline-demo")

    crew = create_crewai_mas(trace_path=ROOT / "traces" / "crewai_demo_secure.jsonl")
    crew_result = crew.run_scripted(request, actor)
    def signature(result: dict) -> set[tuple[str, str, str]]:
        items = [*result.get("certain_findings", []), *result.get("needs_review", [])]
        return {(item["rule_id"], item["node_id"], item.get("suggested_fix") or "") for item in items}

    parity = signature(pending) == signature(crew_result)
    if not parity:
        raise RuntimeError("LangGraph і CrewAI scripted повернули різні findings")
    output_json = ROOT / "outputs" / "demo_result.json"
    output_json.parent.mkdir(exist_ok=True)
    output_json.write_text(json.dumps({"langgraph": final, "crewai": crew_result}, ensure_ascii=False, indent=2), encoding="utf-8")
    report = save_text_report(final, ROOT / "outputs" / "linguistic_report.txt")
    corrected = save_corrected_document(final, ROOT / "outputs" / "corrected_document.txt")
    graph.tracer.emit(
        "corrected_copy_saved", request_id=final["request_id"], status="completed",
        output_name=corrected.name,
    )
    print(json.dumps({
        "status": final["status"],
        "applied": len(final["applied"]),
        "rejected": len(final["rejected"]),
        "json": str(output_json),
        "text_report": str(report),
        "corrected_document": str(corrected),
        "langgraph_crewai_findings_equal": parity,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
