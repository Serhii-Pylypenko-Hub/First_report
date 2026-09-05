"""Guardrails, tenant isolation і deny-by-default контроль інструментів."""

from __future__ import annotations

import re
from collections import defaultdict
from copy import deepcopy
from typing import Any

from .models import ActorContext, AnalysisRequest


INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"(reveal|show|print)\s+(the\s+)?system\s+prompt", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"відкинь\s+(усі\s+)?попередні\s+інструкції", re.I),
    re.compile(r"покажи\s+системн(ий|і)\s+промпт", re.I),
    re.compile(r"(disable|bypass|вимкни|обійди).{0,30}(guardrail|захист|правил)", re.I),
    re.compile(r"(ігноруй|игнорируй|забудь|не виконуй|не следуй).{0,60}(інструкц|инструкц|правил|system)", re.I),
    re.compile(r"(ти|вы|you)\s+(тепер|теперь|are now).{0,60}(агент|assistant|system|admin)", re.I),
    re.compile(r"(?:<\s*system\s*>|\[\s*INST\s*\]|\b(?:system|assistant)\s*prompt\s*:)", re.I),
    re.compile(r"(виклич|вызови|call|execute|запусти).{0,40}(tool|інструмент|инструмент|shell|powershell|cmd)", re.I),
    re.compile(r"(прочитай|покажи|виведи|видали|запиши|read|reveal|delete|write).{0,50}(\.env|api[_ -]?key|секрет|парол|файл|каталог|server)", re.I),
    re.compile(r"(надішли|відправ|отправь|exfiltrate|upload).{0,50}(дані|данные|document|файл|secret)", re.I),
)

ENCODED_BLOCK = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{160,}={0,2}(?![A-Za-z0-9+/])")
MAX_DOCUMENT_CHARS = 60_000
MAX_INPUT_TOKENS = 20_000


def estimate_tokens(text: str) -> int:
    """Консервативна offline-оцінка для бюджетування без виклику tokenizer API."""

    return max(1, (len(text) + 3) // 4)

PII_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "PHONE": re.compile(r"(?<!\d)(?:\+?38)?0\d{2}[\s()-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)"),
    "CARD": re.compile(r"(?<!\d)(?:\d[ -]*?){16}(?!\d)"),
}

TOOL_PERMISSIONS = {
    "document_intake": {"parse_document"},
    "supervisor": set(),
    "grammar": {"search_language_rules", "lookup_word_forms"},
    "style": {"search_language_rules"},
    "terminology": {"search_language_rules"},
    "structure": set(),
    "verifier": {"search_language_rules", "lookup_word_forms"},
    "approval_executor": {"apply_approved_corrections"},
}


class SecurityError(ValueError):
    pass


class ToolGuardrail:
    def __init__(self, max_calls: int = 30) -> None:
        self.max_calls = max_calls
        self._counts: dict[str, int] = defaultdict(int)

    def authorize(self, agent: str, tool: str, args: dict[str, Any]) -> None:
        if tool not in TOOL_PERMISSIONS.get(agent, set()):
            raise SecurityError(f'Агент "{agent}" не має дозволу на tool "{tool}"')
        key = f"{agent}:{tool}"
        self._counts[key] += 1
        if self._counts[key] > self.max_calls:
            raise SecurityError(f"Перевищено ліміт викликів {key}")
        serialized = str(args).lower()
        dangerous = ("../", "..\\", "<script", "drop table", "delete from", "file://", "powershell", "cmd.exe")
        if any(item in serialized for item in dangerous):
            raise SecurityError("Аргументи tool містять заборонений шаблон")


def input_guardrail(request: AnalysisRequest) -> list[dict[str, str]]:
    """Текст є даними, але активні injection-послідовності відправляються в quarantine."""

    alerts: list[dict[str, str]] = []
    total_length = sum(len(node.text) for node in request.document.nodes)
    token_estimate = estimate_tokens("\n".join(node.text for node in request.document.nodes))
    if total_length > MAX_DOCUMENT_CHARS or token_estimate > MAX_INPUT_TOKENS:
        raise SecurityError(
            f"Документ перевищує бюджет: {total_length}/{MAX_DOCUMENT_CHARS} символів, "
            f"≈{token_estimate}/{MAX_INPUT_TOKENS} токенів"
        )
    for node in request.document.nodes:
        if ENCODED_BLOCK.search(node.text):
            alerts.append({"node_id": node.node_id, "code": "ENCODED_PAYLOAD_QUARANTINED"})
            continue
        for pattern in INJECTION_PATTERNS:
            if pattern.search(node.text):
                alerts.append({"node_id": node.node_id, "code": "PROMPT_INJECTION_DETECTED"})
                break
    return alerts


def redact_pii(value: Any) -> Any:
    """Рекурсивно маскує PII у зовнішньому результаті та аудиті."""

    if isinstance(value, str):
        for label, pattern in PII_PATTERNS.items():
            value = pattern.sub(f"[{label}_REDACTED]", value)
        return value
    if isinstance(value, list):
        return [redact_pii(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_pii(item) for key, item in value.items()}
    return value


def assert_scope(actor: ActorContext, expected_tenant: str, expected_user: str) -> None:
    if actor.tenant_id != expected_tenant or actor.user_id != expected_user:
        raise SecurityError("Доступ до іншого tenant/user заборонено")


def assert_admin(actor: ActorContext) -> None:
    """Будь-яка майбутня зміна глобальних правил має проходити цей server-side gate."""

    if actor.role != "admin":
        raise SecurityError("Змінювати глобальні правила може лише адміністратор")


def immutable_copy(request: AnalysisRequest) -> AnalysisRequest:
    return AnalysisRequest.model_validate(deepcopy(request.model_dump()))
