"""Мінімум три обов'язкові тести MCP tools плюс ризикова операція."""

import asyncio
from copy import deepcopy

from mcp_server import (
    apply_approved_corrections_payload,
    lookup_word_forms_payload,
    search_language_rules_payload,
)
from language_mas.analyzers import grammar_findings
from language_mas.fixtures import load_fixture
from language_mas.knowledge import SecureKnowledgeBase
from language_mas.models import AnalysisRequest
from language_mas.mcp_integration import list_language_mcp_tool_names, load_language_mcp_tools_for_agent


def test_search_language_rules_returns_provenance():
    result = search_language_rules_payload("відмінювання форма слова", "grammar")
    assert result["status"] == "ok"
    assert result["data"]
    assert result["data"][0]["source_url"].startswith("https://")
    assert len(result["data"][0]["checksum"]) == 64


def test_lookup_word_forms_known_word():
    result = lookup_word_forms_payload("документ")
    assert result["status"] == "ok"
    assert result["data"]["forms"]["орудний"] == "документом"


def test_lookup_terminology_returns_preferred_term():
    result = search_language_rules_payload("контракт договір", "terminology")
    assert result["status"] == "ok"
    assert result["data"]
    assert result["data"][0]["rule_id"].startswith("TERM")


def test_apply_changes_only_to_copy_after_decision():
    request = AnalysisRequest.model_validate(load_fixture())
    source = request.document.model_dump(mode="json", by_alias=True)
    untouched = deepcopy(source)
    finding = grammar_findings(request.document, SecureKnowledgeBase())[0]
    decision = {"finding_id": finding.finding_id, "decision": "approve", "reason": "test"}
    result = apply_approved_corrections_payload(source, [finding.model_dump(mode="json")], [decision])
    assert result["status"] == "ok"
    assert source == untouched
    assert result["data"]["document"] != source


def test_apply_reject_does_not_change_document():
    request = AnalysisRequest.model_validate(load_fixture())
    source = request.document.model_dump(mode="json", by_alias=True)
    finding = grammar_findings(request.document, SecureKnowledgeBase())[0]
    decision = {"finding_id": finding.finding_id, "decision": "reject", "reason": "test"}
    result = apply_approved_corrections_payload(source, [finding.model_dump(mode="json")], [decision])
    assert result["data"]["document"] == source
    assert result["data"]["rejected"] == [finding.finding_id]


def test_apply_preserves_capital_letter_at_sentence_start():
    request = AnalysisRequest.model_validate(load_fixture())
    source = request.document.model_dump(mode="json", by_alias=True)
    finding = next(
        item for item in grammar_findings(request.document, SecureKnowledgeBase())
        if item.original_text == "згідно наказу"
    )
    result = apply_approved_corrections_payload(
        source,
        [finding.model_dump(mode="json")],
        [{"finding_id": finding.finding_id, "decision": "approve", "reason": "test"}],
    )
    corrected = next(node["text"] for node in result["data"]["document"]["nodes"] if node["node_id"] == "p-003")
    assert corrected.startswith("Згідно з наказом")


def test_real_fastmcp_stdio_discovery():
    names = asyncio.run(list_language_mcp_tool_names())
    assert names == [
        "apply_approved_corrections",
        "lookup_word_forms",
        "parse_document",
        "search_language_rules",
    ]


def test_mcp_tools_are_filtered_per_agent_and_apply_is_never_given_to_specialists():
    grammar_names = sorted(tool.name for tool in asyncio.run(load_language_mcp_tools_for_agent("grammar")))
    structure_names = [tool.name for tool in asyncio.run(load_language_mcp_tools_for_agent("structure"))]
    assert grammar_names == ["lookup_word_forms", "search_language_rules"]
    assert structure_names == []
    assert "apply_approved_corrections" not in grammar_names
