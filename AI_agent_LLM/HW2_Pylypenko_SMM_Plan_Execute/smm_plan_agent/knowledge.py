"""Персистентна ChromaDB база brand-safety знань."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import chromadb


def _embedding(text: str, dimensions: int = 256) -> list[float]:
    """Детермінований локальний embedding без мережевого завантаження моделі."""

    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-zа-яіїєґ0-9_-]{2,}", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class BrandSafetyKnowledgeBase:
    """Індексує ≥8 навчальних політик і виконує semantic retrieval."""

    def __init__(self, *, persist_path: str | Path, documents_path: str | Path) -> None:
        self.persist_path = Path(persist_path)
        self.documents_path = Path(documents_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(
            "smm_brand_safety",
            metadata={"hnsw:space": "cosine"},
        )
        self._load_documents()

    def _load_documents(self) -> None:
        documents = json.loads(self.documents_path.read_text(encoding="utf-8"))
        self.documents_by_id = {item["id"]: item for item in documents}
        ids = [item["id"] for item in documents]
        texts = [json.dumps(item, ensure_ascii=False) for item in documents]
        embeddings = [_embedding(f"{item['title']} {item['content']} {' '.join(item['keywords'])}") for item in documents]
        metadatas = [
            {"title": item["title"], "category": item["category"], "decision": item["decision"]}
            for item in documents
        ]
        self.collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def search(self, query: str, top_k: int = 6) -> list[dict]:
        """Повернути правила разом із provenance та distance."""

        result = self.collection.query(
            query_embeddings=[_embedding(query)],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        rows = []
        for index, document in enumerate(result["documents"][0]):
            rows.append(
                {
                    "policy_id": result["ids"][0][index],
                    "document": document,
                    "metadata": result["metadatas"][0][index],
                    "distance": round(float(result["distances"][0][index]), 4),
                }
            )
        # Критичні hard-block правила не повинні випадати через retrieval miss.
        # Вони все одно надходять із Chroma-індексованої бази знань, але входять
        # до policy set обов'язково, тоді як решта місць визначається similarity.
        mandatory_ids = ["POL-01", "POL-02"]
        existing = {row["policy_id"] for row in rows}
        pinned = []
        for policy_id in mandatory_ids:
            if policy_id in existing:
                continue
            item = self.documents_by_id[policy_id]
            pinned.append(
                {
                    "policy_id": policy_id,
                    "document": json.dumps(item, ensure_ascii=False),
                    "metadata": {
                        "title": item["title"],
                        "category": item["category"],
                        "decision": item["decision"],
                    },
                    "distance": None,
                    "mandatory": True,
                }
            )
        return [*pinned, *rows][:top_k]
