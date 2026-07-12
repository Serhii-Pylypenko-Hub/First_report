import os
import json
import hashlib
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "arxiv_subset.parquet"
EMBEDDINGS_PATH = ROOT / "embeddings" / "embeddings.npy"
EMBEDDING_DIM = 768
MODEL_NAME = "allenai/specter2_base"


def ensure_dataset(output_path: Path = DATA_PATH) -> pd.DataFrame:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        return pd.read_parquet(output_path)

    sample_records = [
        {
            "id": "paper_1",
            "title": "Attention is all you need",
            "abstract": "The transformer architecture uses self-attention to model long-range dependencies in language data.",
            "authors": "Vaswani et al.",
            "year": 2017,
            "category": "cs.LG",
        },
        {
            "id": "paper_2",
            "title": "BERT: Pre-training of deep bidirectional transformers",
            "abstract": "Bidirectional encoders learn contextual word representations for natural language understanding tasks.",
            "authors": "Devlin et al.",
            "year": 2018,
            "category": "cs.CL",
        },
        {
            "id": "paper_3",
            "title": "Deep reinforcement learning with double Q-learning",
            "abstract": "This paper introduces double Q-learning to stabilize reinforcement learning with function approximation.",
            "authors": "Hasselt et al.",
            "year": 2015,
            "category": "cs.LG",
        },
        {
            "id": "paper_4",
            "title": "Convolutional neural networks for visual recognition",
            "abstract": "Convolutional networks are effective for object recognition, detection, and image understanding tasks.",
            "authors": "LeCun et al.",
            "year": 2012,
            "category": "cs.CV",
        },
        {
            "id": "paper_5",
            "title": "The emotional analysis of text with transformers",
            "abstract": "Neural language models are used to detect emotion and sentiment in short text fragments.",
            "authors": "Liu et al.",
            "year": 2021,
            "category": "cs.CL",
        },
    ]
    df = pd.DataFrame(sample_records)
    df.to_parquet(output_path, index=False)
    return df


def load_or_create_dataset() -> pd.DataFrame:
    if DATA_PATH.exists():
        return pd.read_parquet(DATA_PATH)
    return ensure_dataset()


def build_texts(df: pd.DataFrame) -> List[str]:
    texts = []
    for _, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        abstract = str(row.get("abstract", "")).strip()
        if title and abstract:
            texts.append(f"{title} [SEP] {abstract}")
        elif title:
            texts.append(title)
        elif abstract:
            texts.append(abstract)
    return texts


def fallback_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    vector = np.zeros(dim, dtype=np.float32)
    tokens = [t.lower() for t in text.replace("[SEP]", " ").split() if t]
    if not tokens:
        return vector
    for index, token in enumerate(tokens):
        digest = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
        vector[digest % dim] += 1.0 / (index + 1)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector


def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
        embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
        return np.asarray(embeddings, dtype=np.float32)
    except Exception as exc:
        print(f"Falling back to lightweight embeddings: {exc}")
        vectors = [fallback_embedding(text) for text in tqdm(texts, desc="Creating fallback embeddings")]
        return np.stack(vectors, axis=0).astype(np.float32)


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    embeddings = np.asarray(embeddings, dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return embeddings / norms


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def l2_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def chunk_fixed(text: str, chunk_size: int = 40, overlap: int = 10) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        piece = words[start:start + chunk_size]
        if piece:
            chunk = " ".join(piece)
            if chunk not in chunks:
                chunks.append(chunk)
    return chunks


def chunk_semantic(text: str, max_words: int = 40) -> List[str]:
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        return []
    chunks = []
    current = []
    for sentence in sentences:
        words = sentence.split()
        if len(current) + len(words) > max_words and current:
            chunks.append(" ".join(current).strip())
            current = []
        current.extend(words)
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def text_to_sparse(text: str) -> dict:
    indices = []
    values = []
    for word in text.lower().split():
        idx = abs(hash(word)) % 30000
        if idx not in indices:
            indices.append(idx)
            values.append(1.0)
    return {"indices": indices, "values": values}


def maybe_create_pinecone_index(index_name: str, dimension: int = EMBEDDING_DIM):
    try:
        from pinecone import Pinecone, ServerlessSpec
        import os

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print("PINECONE_API_KEY not set; using local fallback")
            return None

        pc = Pinecone(api_key=api_key)
        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            pc.create_index(name=index_name, dimension=dimension, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
        return pc.Index(index_name)
    except Exception as exc:
        print(f"Pinecone unavailable, using local fallback: {exc}")
        return None
