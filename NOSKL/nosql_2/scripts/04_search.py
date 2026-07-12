import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DATA_PATH, EMBEDDINGS_PATH, normalize_embeddings, cosine_similarity, l2_distance

load_dotenv()

INDEX_NAME = "arxiv-papers"
MODEL_NAME = "allenai/specter2_base"
TOP_K = 5


def main() -> None:
    df = pd.read_parquet(DATA_PATH)
    embeddings = normalize_embeddings(np.load(EMBEDDINGS_PATH))
    model = SentenceTransformer(MODEL_NAME)

    query = "teaching machines to recognize objects in pictures"
    q_emb = model.encode([query], normalize_embeddings=True)[0]
    q_emb = q_emb / np.linalg.norm(q_emb)

    scores = embeddings @ q_emb
    ranked = np.argsort(scores)[::-1][:TOP_K]
    print("Semantic search:")
    for idx in ranked:
        row = df.iloc[idx]
        print(f"- {row.title} | {row.category} | {row.year} | {row.abstract[:120]}")

    print("\nFiltered search example:")
    filtered = df[(df["category"] == "cs.LG") & (df["year"] >= 2018)].head(5)
    for _, row in filtered.iterrows():
        print(f"- {row.title} | {row.year} | {row.category}")

    print("\nMetric comparison:")
    for metric_name, metric_fn in [("cosine", lambda a, b: float(np.dot(a, b))), ("dot", lambda a, b: float(np.dot(a, b))), ("l2", lambda a, b: float(np.linalg.norm(a - b)))]:
        if metric_name in {"cosine", "dot"}:
            scores = embeddings @ q_emb
        else:
            scores = -np.linalg.norm(embeddings - q_emb, axis=1)
        ranked = np.argsort(scores)[::-1][:TOP_K]
        print(f"[{metric_name}]")
        for idx in ranked:
            row = df.iloc[idx]
            print(f"- {row.title} | {row.year}")


if __name__ == "__main__":
    main()
