import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DATA_PATH, EMBEDDINGS_PATH, EMBEDDING_DIM, build_texts, embed_texts, normalize_embeddings


def main() -> None:
    df = pd.read_parquet(DATA_PATH)
    texts = build_texts(df)
    embeddings = embed_texts(texts)
    embeddings = normalize_embeddings(embeddings)
    print(f"Processed {len(texts)} texts")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Norm of first embedding: {np.linalg.norm(embeddings[0]):.4f}")
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"Saved embeddings to {EMBEDDINGS_PATH}")


if __name__ == "__main__":
    main()
