"""Персистентна ChromaDB база знань із локальними embeddings."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import chromadb


def _embedding(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-zа-яіїєґ0-9_-]{2,}", text.casefold()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [item / norm for item in vector]


class SMMKnowledgeBase:
    """Індексує доменні документи та повертає provenance."""

    def __init__(self, *, persist_path: str | Path, documents_path: str | Path) -> None:
        self.persist_path = Path(persist_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.documents = json.loads(Path(documents_path).read_text(encoding="utf-8"))
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(
            "rozetka_smm_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
        self.collection.upsert(
            ids=[item["id"] for item in self.documents],
            documents=[json.dumps(item, ensure_ascii=False) for item in self.documents],
            metadatas=[{"title": item["title"], "topic": item["topic"]} for item in self.documents],
            embeddings=[_embedding(f"{item['title']} {item['content']}") for item in self.documents],
        )

    def search(self, query: str, top_k: int) -> list[dict]:
        result = self.collection.query(
            query_embeddings=[_embedding(query)],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "document_id": result["ids"][0][index],
                "document": document,
                "metadata": result["metadatas"][0][index],
                "distance": round(float(result["distances"][0][index]), 4),
            }
            for index, document in enumerate(result["documents"][0])
        ]
