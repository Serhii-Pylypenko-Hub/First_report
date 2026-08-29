"""Захисні механізми: max_steps, timeout і детекція повторів."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyConfig:
    """Ліміти одного запуску агента."""

    max_steps: int = 12
    timeout_seconds: float = 120.0
    max_repeats: int = 3

    def __post_init__(self) -> None:
        if not 1 <= self.max_steps <= 50:
            raise ValueError("max_steps має бути від 1 до 50")
        if not 0 < self.timeout_seconds <= 600:
            raise ValueError("timeout_seconds має бути більше 0 і не більше 600")
        if not 2 <= self.max_repeats <= 10:
            raise ValueError("max_repeats має бути від 2 до 10")


def execution_limit_reason(
    *,
    step_count: int,
    started_at: float,
    config: SafetyConfig,
    now: float | None = None,
) -> str:
    """Повернути причину примусової зупинки або порожній рядок."""

    if step_count >= config.max_steps:
        return "max_steps"
    current = time.monotonic() if now is None else now
    if current - started_at >= config.timeout_seconds:
        return "timeout"
    return ""


class LoopDetector:
    """Виявляє однакові послідовні tool calls."""

    def __init__(self, max_repeats: int = 3) -> None:
        if max_repeats < 2:
            raise ValueError("max_repeats має бути не менше 2")
        self.max_repeats = max_repeats

    @staticmethod
    def signature(tool_name: str, arguments: dict) -> str:
        payload = json.dumps(
            {"name": tool_name, "arguments": arguments},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def update(self, recent: list[str], tool_calls: list[dict]) -> tuple[list[str], bool]:
        updated = list(recent)
        loop_detected = False
        for call in tool_calls:
            signature = self.signature(str(call.get("name", "")), dict(call.get("args") or {}))
            updated.append(signature)
            if len(updated) >= self.max_repeats:
                loop_detected = len(set(updated[-self.max_repeats :])) == 1
            if loop_detected:
                break
        return updated[-20:], loop_detected
