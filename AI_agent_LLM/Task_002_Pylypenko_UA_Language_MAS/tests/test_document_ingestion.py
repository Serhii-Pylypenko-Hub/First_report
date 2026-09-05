"""Візуалізовані в notebook інтеграційні тести чотирьох форматів документа."""

import pytest

from language_mas.document_ingestion import DocumentIntakeAgent
from language_mas.langgraph_mas import create_langgraph_mas
from language_mas.models import ActorContext


@pytest.mark.parametrize(
    ("file_name", "expected_format", "expected_method"),
    [
        ("example.txt", "txt", {"utf8_text"}),
        ("example.docx", "docx", {"python_docx"}),
        ("example.pdf", "pdf", {"pypdf_text_layer"}),
        ("example.png", "png", {"fixture_metadata_test_double", "local_tesseract_ocr"}),
    ],
)
def test_document_intake_returns_same_json_contract(file_name, expected_format, expected_method):
    result = DocumentIntakeAgent().parse(file_name, request_id=f"parse-{expected_format}")
    assert result["status"] == "ok"
    assert result["data"]["source"]["format"] == expected_format
    assert result["data"]["source"]["extraction_method"] in expected_method
    assert result["data"]["request"]["document"]["language"] == "uk"
    assert result["data"]["request"]["document"]["nodes"]


def test_document_intake_blocks_files_outside_scoped_directory():
    with pytest.raises(ValueError):
        DocumentIntakeAgent().parse("..\\demo_request.json", request_id="blocked-path")


def test_document_intake_audit_contains_metadata_but_not_document_text(tmp_path):
    trace_path = tmp_path / "intake.jsonl"
    result = DocumentIntakeAgent(trace_path).parse("example.txt", request_id="audit-intake")
    log = trace_path.read_text(encoding="utf-8")
    assert result["status"] == "ok"
    assert "document_intake_completed" in log
    assert result["data"]["source"]["sha256"] in log
    assert result["data"]["request"]["document"]["nodes"][0]["text"] not in log


def test_parsed_fixture_exercises_agents_and_preserves_original_locations():
    parsed = DocumentIntakeAgent().parse("example.txt", request_id="parsed-analysis")
    actor = ActorContext(tenant_id="test-tenant", user_id="test-user")
    mas = create_langgraph_mas()
    mas.start(parsed["data"]["request"], actor, thread_id="parsed-analysis")
    result = mas.result(actor, thread_id="parsed-analysis")

    findings = result["agent_results"]["verifier"]["findings"]
    categories = {item["category"] for item in findings}
    structure_rules = {item["rule_id"] for item in findings if item["agent"] == "structure"}

    assert {"orthography", "punctuation", "grammar", "calque", "terminology", "structure"} <= categories
    assert {"STRUCT.DUPLICATE.001", "STRUCT.REPEATED_WORD.001"} <= structure_rules
    assert all(item["section_ref"].startswith("Рядок ") for item in findings)
