import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DATA_PATH

load_dotenv()

INDEX_NAME = "arxiv-papers"
MODEL_NAME = "allenai/specter2_base"
TOP_K = 5


def reciprocal_rank_fusion(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def main() -> None:
    df = pd.read_parquet(DATA_PATH).reset_index(drop=True)
    corpus = [f"{row.title} {row.abstract}" for _, row in df.iterrows()]
    tokenized = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    model = SentenceTransformer(MODEL_NAME)

    queries = [
        "BERT fine-tuning",
        "Yann LeCun convolutional networks",
        "making computers understand human emotions from text",
    ]

    for query in queries:
        bm25_scores = bm25.get_scores(query.lower().split())
        bm25_ranking = list(np.argsort(bm25_scores)[::-1][:TOP_K])

        q_emb = model.encode([query], normalize_embeddings=True)[0]
        texts = [f"{row.title} [SEP] {row.abstract}" for _, row in df.iterrows()]
        vecs = model.encode(texts, normalize_embeddings=True)
        vec_scores = vecs @ q_emb
        vec_ranking = list(np.argsort(vec_scores)[::-1][:TOP_K])

        fused = reciprocal_rank_fusion([bm25_ranking, vec_ranking])[:TOP_K]
        print(f"\nQuery: {query}")
        print("BM25:")
        for doc_id in bm25_ranking:
            print(f"- {df.iloc[doc_id].title} | {df.iloc[doc_id].category}")
        print("Vector:")
        for doc_id in vec_ranking:
            print(f"- {df.iloc[doc_id].title} | {df.iloc[doc_id].category}")
        print("Hybrid RRF:")
        for doc_id, score in fused:
            print(f"- {df.iloc[doc_id].title} | score={score:.4f}")


if __name__ == "__main__":
    main()
