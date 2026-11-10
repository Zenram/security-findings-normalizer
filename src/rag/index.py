"""Qdrant index build/load for Part 2 Step 2.

Loads the Step-1 `data/rag/chunks.jsonl`, embeds each chunk (fastembed, cached)
and upserts it into a Qdrant collection with the full chunk payload (so metadata
filters on `doc_type` / `format` work and citations have source + section).

Qdrant runs in-process:
  - `:memory:`  — default for a single run / tests (fast, nothing on disk)
  - a path      — persistent local file store under data/rag/qdrant/ (gitignored)

There is no server to deploy; `QdrantClient(location=...)` embeds the engine.
"""

from __future__ import annotations

import json
from pathlib import Path

from qdrant_client import QdrantClient, models

from src.config import REPO_ROOT
from src.rag.embed import EMBED_DIM, Embedder, text_for_embedding

CHUNKS_PATH = REPO_ROOT / "data" / "rag" / "chunks.jsonl"
QDRANT_PATH = REPO_ROOT / "data" / "rag" / "qdrant"
COLLECTION = "security_corpus"


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python3 main.py --ingest` (Step 1) first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def build_collection(client: QdrantClient, chunks: list[dict],
                     embedder: Embedder | None = None,
                     recreate: bool = True) -> QdrantClient:
    """Embed `chunks` and (re)create the Qdrant collection with full payloads."""
    embedder = embedder or Embedder()
    vectors = embedder.embed([text_for_embedding(c) for c in chunks])

    if recreate and client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            COLLECTION,
            vectors_config=models.VectorParams(size=EMBED_DIM, distance=models.Distance.COSINE),
        )
    client.upsert(
        COLLECTION,
        points=[
            models.PointStruct(id=i, vector=v, payload=c)
            for i, (c, v) in enumerate(zip(chunks, vectors))
        ],
    )
    return client


def open_client(persist: bool = False) -> QdrantClient:
    """In-memory by default; pass persist=True for the on-disk local store."""
    if persist:
        QDRANT_PATH.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(QDRANT_PATH))
    return QdrantClient(location=":memory:")
