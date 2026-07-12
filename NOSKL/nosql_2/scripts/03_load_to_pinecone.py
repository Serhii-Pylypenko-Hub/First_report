import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DATA_PATH, EMBEDDINGS_PATH, EMBEDDING_DIM, maybe_create_pinecone_index


def main() -> None:
    df = pd.read_parquet(DATA_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)
    index = maybe_create_pinecone_index("arxiv-papers", EMBEDDING_DIM)

    if index is None:
        print("Local fallback: saved metadata to ./embeddings/local_index.json")
        local_meta = []
        for i, row in enumerate(df.itertuples(index=False)):
            local_meta.append({
                "id": f"paper_{i}",
                "title": row.title,
                "category": row.category,
                "year": row.year,
                "abstract": row.abstract[:500],
            })
        import json
        Path("embeddings").mkdir(exist_ok=True)
        with open("embeddings/local_index.json", "w", encoding="utf-8") as fh:
            json.dump(local_meta, fh, indent=2)
        print(f"Local fallback records: {len(local_meta)}")
        return

    for start in range(0, len(df), 200):
        batch_df = df.iloc[start:start + 200]
        batch_emb = embeddings[start:start + 200]
        vectors = []
        for idx, row in enumerate(batch_df.itertuples(index=False)):
            vectors.append((
                f"paper_{start + idx}",
                batch_emb[idx].tolist(),
                {
                    "arxiv_id": str(row.id),
                    "title": row.title,
                    "abstract": row.abstract[:500],
                    "authors": row.authors[:200],
                    "year": int(row.year),
                    "category": row.category,
                },
            ))
        index.upsert(vectors=vectors)
        print(f"Upserted batch {start // 200 + 1}")

    stats = index.describe_index_stats()
    print(f"Inserted vectors: {stats.total_vector_count}")


if __name__ == "__main__":
    main()
