import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DATA_PATH, EMBEDDING_DIM, chunk_fixed, chunk_semantic, maybe_create_pinecone_index

MODEL_NAME = "allenai/specter2_base"


def main() -> None:
    df = pd.read_parquet(DATA_PATH).copy()
    df["text_len"] = df["abstract"].astype(str).str.len()
    sample = df.sort_values("text_len", ascending=False).head(30)

    model = SentenceTransformer(MODEL_NAME)

    for name, strategy in [("fixed", chunk_fixed), ("semantic", lambda text: chunk_semantic(text, max_words=40))]:
        index = maybe_create_pinecone_index(f"arxiv-chunks-{name}")
        if index is None:
            print(f"Skipping Pinecone upload for {name}; local fallback only")
            continue
        vectors = []
        for _, row in sample.iterrows():
            chunks = strategy(str(row["abstract"]))
            for chunk_idx, chunk in enumerate(chunks[:10]):
                emb = model.encode([chunk], normalize_embeddings=True)[0]
                vectors.append((
                    f"{name}_{row['id']}_{chunk_idx}",
                    emb.tolist(),
                    {
                        "arxiv_id": row["id"],
                        "title": row["title"],
                        "chunk": chunk[:500],
                        "chunk_idx": chunk_idx,
                        "year": int(row["year"]),
                        "category": row["category"],
                    },
                ))
        for start in range(0, len(vectors), 100):
            batch = vectors[start:start + 100]
            index.upsert(vectors=batch)
        print(f"Uploaded {len(vectors)} {name} chunks")

        query = "learning with attention and transformers"
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        result = index.query(vector=q_emb.tolist(), top_k=5, include_metadata=True)
        print(f"[{name}] top results:")
        for match in result.matches:
            print(f"- {match.metadata.get('title')} | {match.metadata.get('chunk', '')[:100]}")


if __name__ == "__main__":
    main()
