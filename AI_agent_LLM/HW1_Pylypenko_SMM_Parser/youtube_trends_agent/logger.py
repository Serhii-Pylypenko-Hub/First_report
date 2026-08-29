"""JSON-логування повної траєкторії ReAct-графа."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def compact(value: Any, limit: int = 800) -> str:
    """Безпечно перетворити значення на короткий текст для audit trail."""

    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    return text[:limit]


class TrajectoryLogger:
    """Накопичує кроки виконання одного запуску агента."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.started_at = time.monotonic()
        self.started_wall_time = datetime.now(UTC)
        self.steps: list[dict] = []

    def log_step(
        self,
        *,
        node_name: str,
        input_data: Any,
        output_data: Any,
        tool_calls: list[dict] | None = None,
        duration_ms: int = 0,
    ) -> None:
        self.steps.append(
            {
                "step_number": len(self.steps) + 1,
                "node_name": node_name,
                "input": compact(input_data),
                "output": compact(output_data),
                "tool_calls": tool_calls or [],
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": duration_ms,
                "elapsed_ms": int((time.monotonic() - self.started_at) * 1000),
            }
        )

    def as_dict(self, *, stop_reason: str = "completed") -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_wall_time.isoformat(),
            "total_steps": len(self.steps),
            "total_time_ms": int((time.monotonic() - self.started_at) * 1000),
            "stop_reason": stop_reason,
            "trajectory": self.steps,
        }

    def save(self, path: str | Path, *, stop_reason: str = "completed") -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.as_dict(stop_reason=stop_reason), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
