"""Локальна observability без запису сирого тексту документа."""

from __future__ import annotations

import json
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonlTracer:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.events: list[dict[str, Any]] = []
        self.previous_hash = "GENESIS"
        if self.path and self.path.is_file():
            try:
                records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
                if records and not self.verify_chain(records):
                    raise ValueError("Порушено цілісність audit hash-chain")
                self.previous_hash = records[-1].get("record_hash", "GENESIS") if records else "GENESIS"
            except (IndexError, OSError, ValueError, json.JSONDecodeError):
                raise ValueError("Неможливо безпечно продовжити пошкоджений audit log")

    @staticmethod
    def verify_chain(records: list[dict[str, Any]]) -> bool:
        previous = "GENESIS"
        for record in records:
            if record.get("previous_hash") != previous:
                return False
            body = {key: value for key, value in record.items() if key not in {"previous_hash", "record_hash"}}
            canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
            expected = sha256(f"{previous}|{canonical}".encode("utf-8")).hexdigest()
            if record.get("record_hash") != expected:
                return False
            previous = expected
        return True

    def emit(self, event: str, **fields: Any) -> None:
        body = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
        record = {
            **body,
            "previous_hash": self.previous_hash,
            "record_hash": sha256(f"{self.previous_hash}|{canonical}".encode("utf-8")).hexdigest(),
        }
        self.previous_hash = record["record_hash"]
        self.events.append(record)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
