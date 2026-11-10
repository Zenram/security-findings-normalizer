"""Embeddings for Part 2 Step 2 — local, free, reproducible.

Approved stack (A3): fastembed with `paraphrase-multilingual-MiniLM-L12-v2`
(384-dim, EN+UK, runs locally via onnxruntime — no API, no cost). A content-hash
cache on disk means re-indexing or re-querying the same text never re-embeds,
which keeps repeated runs (and CI) fast.

The embedder is lazy: the model is only loaded when something actually needs
embedding that is not already cached. That keeps `import` cheap for tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.config import REPO_ROOT

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBED_DIM = 384

MODELS_DIR = REPO_ROOT / ".models"               # fastembed model download cache
CACHE_PATH = REPO_ROOT / "data" / "rag" / "embeddings_cache.json"


def text_for_embedding(chunk: dict) -> str:
    """Prepend the section path so the embedding carries structural context
    (a chunk under 'Access Control > Least Privilege' embeds differently from
    the same prose with no heading)."""
    section = chunk.get("section") or ""
    return f"{section}\n{chunk['text']}" if section else chunk["text"]


class Embedder:
    """fastembed wrapper with a persistent content-hash cache."""

    def __init__(self, model_name: str = EMBED_MODEL, cache_path: Path = CACHE_PATH):
        self.model_name = model_name
        self.cache_path = cache_path
        self._model = None
        self._cache: dict[str, list[float]] = {}
        if cache_path.exists():
            try:
                self._cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model_name}\n{text}".encode("utf-8")).hexdigest()

    def _ensure_model(self):
        if self._model is None:
            from fastembed import TextEmbedding  # imported lazily (heavy)

            self._model = TextEmbedding(self.model_name, cache_dir=str(MODELS_DIR))
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, using the cache where possible."""
        keys = [self._key(t) for t in texts]
        missing = [(k, t) for k, t in zip(keys, texts) if k not in self._cache]
        if missing:
            model = self._ensure_model()
            vectors = model.embed([t for _, t in missing])
            for (k, _), vec in zip(missing, vectors):
                self._cache[k] = [round(float(x), 6) for x in vec]
            self._flush()
        return [self._cache[k] for k in keys]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _flush(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache), encoding="utf-8")
