"""Багаторівневі guardrails для MAS і MCP executor."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from pathlib import PurePosixPath
from typing import Any


INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"(reveal|show|print).{0,30}system\s+prompt", re.I),
    re.compile(r"(bypass|disable).{0,30}(guardrail|security|policy)", re.I),
    re.compile(r"(ігноруй|відкинь|забудь).{0,60}(попередн|інструкц|правил)", re.I),
    re.compile(r"(покажи|розкрий|виведи).{0,40}(системн.*промпт|секрет|api.?key|парол)", re.I),
    re.compile(r"(обійди|вимкни).{0,30}(захист|правил|обмеженн)", re.I),
    re.compile(r"(?:<\s*system\s*>|\[\s*INST\s*\]|system\s*prompt\s*:)", re.I),
    re.compile(r"(call|execute|виклич|запусти).{0,40}(shell|powershell|cmd|tool)", re.I),
)
ENCODED_PAYLOAD = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{160,}={0,2}(?![A-Za-z0-9+/])")

PII_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "PHONE": re.compile(r"(?<!\d)(?:\+?38)?0\d{2}[\s()-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)"),
    "CARD": re.compile(r"(?<!\d)(?:\d[ -]*?){16}(?!\d)"),
    "IBAN_UA": re.compile(r"\bUA\d{27}\b", re.I),
    "IPN": re.compile(r"(?<!\d)\d{10}(?!\d)"),
    "PASSPORT": re.compile(r"\b(?:[А-ЯІЇЄҐ]{2}\s?\d{6}|\d{9})\b"),
}

FORBIDDEN_TOPICS = {
    "weapons": ("зброя", "вибухівка", "weapon", "explosive"),
    "hate": ("мова ворожнечі", "ненависть до", "hate speech"),
    "adult": ("порнограф", "18+ контент", "pornograph"),
    "fraud": ("обманути покупця", "фальшивий відгук", "fake review"),
    "self_harm": ("самогуб", "самоушкод", "self-harm", "suicide"),
}

TOOL_PERMISSIONS: dict[str, set[str]] = {
    "supervisor": set(),
    "collector": {"collect_brand_posts"},
    "researcher": {"search_smm_knowledge"},
    "analyst": {"calculate_competitive_metrics"},
    "strategist": {"generate_content_brief"},
    "language": {"search_smm_knowledge"},
    "verifier": {"search_smm_knowledge"},
    "approval_executor": {"export_smm_report"},
}


class SecurityError(ValueError):
    pass


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def input_guardrail(text: str, max_chars: int = 20_000, max_tokens: int = 6_000) -> tuple[bool, list[str]]:
    if not isinstance(text, str):
        return False, ["INPUT_NOT_STRING"]
    alerts: list[str] = []
    if len(text) > max_chars or estimate_tokens(text) > max_tokens:
        alerts.append("INPUT_BUDGET_EXCEEDED")
    if ENCODED_PAYLOAD.search(text):
        alerts.append("ENCODED_PAYLOAD_QUARANTINED")
    if any(pattern.search(text) for pattern in INJECTION_PATTERNS):
        alerts.append("PROMPT_INJECTION_DETECTED")
    return not alerts, alerts


def scan_forbidden_topics(text: str) -> list[dict[str, Any]]:
    lowered = text.casefold()
    return [
        {"topic": topic, "matched_terms": [term for term in terms if term in lowered]}
        for topic, terms in FORBIDDEN_TOPICS.items()
        if any(term in lowered for term in terms)
    ]


def redact_pii(value: Any) -> tuple[Any, list[str]]:
    found: set[str] = set()

    def walk(item: Any) -> Any:
        if isinstance(item, str):
            for label, pattern in PII_PATTERNS.items():
                if pattern.search(item):
                    found.add(label)
                    item = pattern.sub(f"[{label}_REDACTED]", item)
            return item
        if isinstance(item, list):
            return [walk(child) for child in item]
        if isinstance(item, dict):
            return {key: walk(child) for key, child in item.items()}
        return item

    return walk(value), sorted(found)


def authorize_tool(agent_name: str, tool_name: str, arguments: dict[str, Any]) -> None:
    if tool_name not in TOOL_PERMISSIONS.get(agent_name, set()):
        raise SecurityError(f'Агент "{agent_name}" не має дозволу на tool "{tool_name}"')
    serialized = str(arguments).casefold()
    dangerous = ("../", "..\\", "file://", "powershell", "cmd.exe", "<script", "drop table")
    if any(token in serialized for token in dangerous):
        raise SecurityError("Аргументи tool містять заборонений шаблон")
    if "path" in arguments:
        path = PurePosixPath(str(arguments["path"]).replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not str(path).startswith("outputs/"):
            raise SecurityError("Файлова операція дозволена лише в outputs/")


class RateLimiter:
    """Rolling-window rate limiter окремо для кожного session_id."""

    def __init__(self, max_calls: int = 30, window_seconds: float = 60.0) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def check(self, session_id: str, now: float | None = None) -> tuple[bool, str]:
        timestamp = time.monotonic() if now is None else now
        queue = self._calls[session_id]
        while queue and timestamp - queue[0] >= self.window_seconds:
            queue.popleft()
        if len(queue) >= self.max_calls:
            return False, f"RATE_LIMIT_EXCEEDED:{self.max_calls}/{self.window_seconds:g}s"
        queue.append(timestamp)
        return True, f"OK:{len(queue)}/{self.max_calls}"
