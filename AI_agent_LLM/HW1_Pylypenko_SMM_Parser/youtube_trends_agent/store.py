"""Потокобезпечне тимчасове сховище наборів відео між tool calls."""

from __future__ import annotations

import threading
import uuid
from copy import deepcopy


class DatasetNotFoundError(KeyError):
    """Набір не існує або належить іншому запуску."""


class TrendDataStore:
    """Зберігає проміжні результати одного ReAct-запуску."""

    def __init__(self) -> None:
        self._datasets: dict[str, dict] = {}
        self._lock = threading.RLock()

    def create(self, *, query: dict, videos: list[dict], source_mode: str) -> str:
        dataset_id = f"dataset-{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._datasets[dataset_id] = {
                "dataset_id": dataset_id,
                "query": deepcopy(query),
                "videos": deepcopy(videos),
                "source_mode": source_mode,
                "statistics_enriched": False,
                "rankings": {},
                "signals": {},
            }
        return dataset_id

    def get(self, dataset_id: str) -> dict:
        with self._lock:
            if dataset_id not in self._datasets:
                raise DatasetNotFoundError(f"Набір {dataset_id} не знайдено")
            return deepcopy(self._datasets[dataset_id])

    def update(self, dataset_id: str, **values: object) -> dict:
        with self._lock:
            if dataset_id not in self._datasets:
                raise DatasetNotFoundError(f"Набір {dataset_id} не знайдено")
            self._datasets[dataset_id].update(deepcopy(values))
            return deepcopy(self._datasets[dataset_id])

    def latest(self) -> dict | None:
        with self._lock:
            if not self._datasets:
                return None
            last_key = next(reversed(self._datasets))
            return deepcopy(self._datasets[last_key])
