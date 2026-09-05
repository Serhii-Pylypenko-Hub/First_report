"""Структурований append-only журнал MAS із hash chain та agent_name."""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from guardrails import redact_pii


class TrajectoryLogger:
    def __init__(self, path: str | Path = "trajectory.json", max_events: int = 2000) -> None:
        self.path = Path(path)
        self.max_events = max_events
        self._lock = threading.Lock()

    @contextmanager
    def _process_lock(self):
        """Серіалізує записи також між CLI, notebook і pytest-процесами."""
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = None
        for _ in range(500):
            try:
                descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(descriptor, f"{os.getpid()} {time.time()}".encode("ascii"))
                break
            except FileExistsError:
                # Після аварійного завершення старий lock не має блокувати систему назавжди.
                try:
                    if time.time() - lock_path.stat().st_mtime > 30:
                        lock_path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                time.sleep(0.01)
        if descriptor is None:
            raise TimeoutError("Не вдалося отримати блокування trajectory logger за 5 секунд")
        try:
            yield
        finally:
            os.close(descriptor)
            lock_path.unlink(missing_ok=True)

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def log(
        self,
        *,
        agent_name: str,
        node_name: str,
        event: str,
        thread_id: str,
        status: str = "ok",
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
        budget_remaining: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_details, pii = redact_pii(details or {})
        with self._lock, self._process_lock():
            rows = self._read()
            if len(rows) >= self.max_events:
                # Журнал обмежений: це захищає довготривалий процес від необмеженого RAM/disk growth.
                rows = rows[-(self.max_events - 1):]
                previous = "GENESIS"
                for retained in rows:
                    retained["previous_hash"] = previous
                    retained.pop("event_hash", None)
                    retained["event_hash"] = sha256(
                        json.dumps(retained, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest()
                    previous = retained["event_hash"]
            previous_hash = rows[-1]["event_hash"] if rows else "GENESIS"
            event_row = {
                "timestamp": datetime.now(UTC).isoformat(),
                "agent_name": agent_name,
                "node_name": node_name,
                "event": event,
                "thread_id": thread_id,
                "status": status,
                "tool_name": tool_name,
                "details": safe_details,
                "pii_types_redacted": pii,
                "budget_remaining": budget_remaining or {},
                "previous_hash": previous_hash,
            }
            event_row["event_hash"] = sha256(
                json.dumps(event_row, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            rows.append(event_row)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(
                self.path.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp"
            )
            temporary.write_text(
                json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
            return event_row

    def verify(self) -> bool:
        rows = self._read()
        previous = "GENESIS"
        for row in rows:
            if row.get("previous_hash") != previous:
                return False
            expected = dict(row)
            actual_hash = expected.pop("event_hash", None)
            if sha256(json.dumps(expected, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest() != actual_hash:
                return False
            previous = actual_hash
        return True
