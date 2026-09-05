"""Контрольований локальний RAG-корпус з provenance та перевіркою checksum."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from .models import Evidence


DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "language_rules.json"
ALLOWED_AUTHORITIES = {
    "Міністерство освіти і науки України",
    "Національна комісія зі стандартів державної мови",
    "Верховна Рада України",
    "Український мовно-інформаційний фонд НАН України",
}
ALLOWED_DOMAINS = ("mon.gov.ua", "mova.gov.ua", "zakon.rada.gov.ua", "lcorp.ulif.org.ua")


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[а-яіїєґa-z0-9]+", text.lower()) if len(token) > 2}


class SecureKnowledgeBase:
    def __init__(self, path: Path = DEFAULT_KNOWLEDGE_PATH) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.entries: list[dict] = []
        for item in payload:
            if item["authority"] not in ALLOWED_AUTHORITIES:
                raise ValueError("Недовірений authority у базі знань")
            if not any(domain in item["source_url"] for domain in ALLOWED_DOMAINS):
                raise ValueError("Джерело поза allowlist")
            expected = sha256(item["excerpt"].encode("utf-8")).hexdigest()
            if item["checksum"] != expected:
                raise ValueError(f"Checksum не збігається для {item['rule_id']}")
            self.entries.append(item)

    def search(self, query: str, *, category: str | None = None, limit: int = 3) -> list[Evidence]:
        query_tokens = _tokens(query)
        ranked: list[tuple[float, dict]] = []
        for item in self.entries:
            if category and item["category"] != category:
                continue
            haystack = _tokens(" ".join((item["title"], item["excerpt"], " ".join(item["keywords"]))))
            overlap = len(query_tokens & haystack)
            score = overlap / max(1, len(query_tokens))
            if score > 0 or not query_tokens:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (pair[0], pair[1]["trust_level"]), reverse=True)
        evidence_fields = set(Evidence.model_fields)
        return [
            Evidence.model_validate({key: value for key, value in item.items() if key in evidence_fields})
            for _, item in ranked[:limit]
        ]

    def word_forms(self, word: str) -> dict:
        normalized = word.lower().strip()
        forms = {
            "документ": {"родовий": "документа", "давальний": "документу", "орудний": "документом"},
            "договір": {"родовий": "договору", "давальний": "договору", "орудний": "договором"},
            "користувач": {"родовий": "користувача", "давальний": "користувачеві", "орудний": "користувачем"},
            "наказ": {"родовий": "наказу", "давальний": "наказу", "орудний": "наказом"},
        }
        return {"word": normalized, "forms": forms.get(normalized), "found": normalized in forms}

    def terminology(self, term: str, glossary: dict[str, str] | None = None) -> dict:
        normalized = term.lower().strip()
        glossary = glossary or {}
        preferred = glossary.get(normalized)
        built_in = {"контракт": "договір", "дедлайн": "кінцевий строк", "апрув": "погодження"}
        return {
            "term": normalized,
            "preferred": preferred or built_in.get(normalized),
            "source": "owner_glossary" if preferred else "curated_dictionary",
        }
