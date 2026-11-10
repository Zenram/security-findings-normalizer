"""Hybrid retrieval for Part 2 Step 2.

Adapts the course-lesson retriever (`lesson-08-rag/retrieval.py`) to this
project's chunk schema and approved stack:

    dense  : fastembed (paraphrase-multilingual-MiniLM-L12-v2) -> Qdrant cosine
    sparse : BM25Okapi over the same section+text
    fuse   : Reciprocal Rank Fusion (RRF)
    rerank : optional deterministic lexical-overlap rerank over the fused top-N
    filter : metadata filter on doc_type (the graded filter) and optional format

Three retrieval MODES are exposed so Step 2 can measure them against each other
(vector-only vs hybrid vs hybrid+rerank), as the plan requires:

    Retriever(mode="vector")          # dense only
    Retriever(mode="hybrid")          # dense + BM25 + RRF   (default)
    Retriever(mode="hybrid_rerank")   # + lexical rerank of the fused candidates

The LLM answerer (Step 3) consumes `search(...)` hits unchanged and routes their
text into the existing Gemini/Ollama adapters.
"""

from __future__ import annotations

import re
from pathlib import Path

from qdrant_client import QdrantClient, models

from src.config import REPO_ROOT
from src.rag.embed import EMBED_DIM, Embedder, text_for_embedding
from src.rag.index import COLLECTION, build_collection, load_chunks

CANDIDATES = 20        # candidates pulled from each retriever before fusion
RRF_K = 60             # RRF constant (standard default)

MODE_VECTOR = "vector"
MODE_HYBRID = "hybrid"
MODE_HYBRID_RERANK = "hybrid_rerank"
VALID_MODES = (MODE_VECTOR, MODE_HYBRID, MODE_HYBRID_RERANK)


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class Retriever:
    def __init__(self, mode: str = MODE_HYBRID, chunks: list[dict] | None = None,
                 client: QdrantClient | None = None, embedder: Embedder | None = None,
                 location: str = ":memory:"):
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")
        self.mode = mode
        self.embedder = embedder or Embedder()
        self.chunks = chunks if chunks is not None else load_chunks()
        self._by_id = {c["chunk_id"]: c for c in self.chunks}

        # Vector store: reuse a provided client or build an in-memory collection.
        if client is not None:
            self.client = client
        else:
            self.client = QdrantClient(location=location)
            build_collection(self.client, self.chunks, self.embedder)

        # BM25 over the same text the dense side sees.
        from rank_bm25 import BM25Okapi

        self._corpus_tokens = [tokenize(text_for_embedding(c)) for c in self.chunks]
        self.bm25 = BM25Okapi(self._corpus_tokens)

    # --- metadata filter -----------------------------------------------------

    @staticmethod
    def _qdrant_filter(doc_types: list[str] | None, formats: list[str] | None):
        must = []
        if doc_types:
            must.append(models.FieldCondition(key="doc_type",
                                              match=models.MatchAny(any=doc_types)))
        if formats:
            must.append(models.FieldCondition(key="format",
                                              match=models.MatchAny(any=formats)))
        return models.Filter(must=must) if must else None

    @staticmethod
    def _passes(chunk: dict, doc_types: list[str] | None, formats: list[str] | None) -> bool:
        if doc_types and chunk.get("doc_type") not in doc_types:
            return False
        if formats and chunk.get("format") not in formats:
            return False
        return True

    # --- individual retrievers ----------------------------------------------

    def vector_search(self, query: str, k: int, doc_types=None, formats=None) -> list[dict]:
        hits = self.client.query_points(
            COLLECTION,
            query=self.embedder.embed_one(query),
            limit=k,
            query_filter=self._qdrant_filter(doc_types, formats),
        ).points
        return [{**h.payload, "cosine": h.score} for h in hits]

    def bm25_search(self, query: str, k: int, doc_types=None, formats=None) -> list[dict]:
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(self.chunks)), key=lambda i: -scores[i])
        out = []
        for i in order:
            if scores[i] <= 0:
                break
            c = self.chunks[i]
            if self._passes(c, doc_types, formats):
                out.append({**c, "bm25": float(scores[i])})
            if len(out) >= k:
                break
        return out

    # --- fusion + rerank -----------------------------------------------------

    @staticmethod
    def _rrf(rankings: list[list[dict]]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, hit in enumerate(ranking, 1):
                cid = hit["chunk_id"]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
        return scores

    @staticmethod
    def _lexical_overlap(query: str, chunk: dict) -> float:
        """Fraction of distinct query terms present in the chunk (section+text).
        A cheap lexical signal, kept for diagnostics / comparison."""
        q = set(tokenize(query))
        if not q:
            return 0.0
        doc = set(tokenize(text_for_embedding(chunk)))
        return len(q & doc) / len(q)

    def _rerank_score(self, query: str, cid: str, cosine: dict[str, float],
                      fused: dict[str, float]) -> tuple[float, float]:
        """Reranking signal over fused candidates.

        Uses the DENSE cosine similarity (a real semantic signal already computed
        for the vector side) as the primary key, with the RRF score as a
        tiebreak. Cosine reranking re-floats semantically-strong chunks that RRF
        may have ranked below a lexically-matching but less relevant chunk. For
        a BM25-only candidate (no cosine), we fall back to its RRF score so it is
        not unfairly zeroed — but we embed it on demand to get a real cosine.
        """
        cos = cosine.get(cid)
        if cos is None:
            cos = self._cosine_on_demand(query, cid)
        return (cos, fused[cid])

    def _cosine_on_demand(self, query: str, cid: str) -> float:
        """Cosine of a BM25-only candidate that the vector search did not return,
        computed from cached embeddings (no extra model call for the chunk)."""
        import numpy as np

        qv = np.array(self.embedder.embed_one(query), dtype=float)
        cv = np.array(self.embedder.embed_one(text_for_embedding(self._by_id[cid])), dtype=float)
        denom = (np.linalg.norm(qv) * np.linalg.norm(cv)) or 1.0
        return float(qv @ cv / denom)

    # --- public API ----------------------------------------------------------

    def search(self, query: str, k: int = 5, doc_types: list[str] | None = None,
               formats: list[str] | None = None) -> list[dict]:
        """Return the top-k chunks for `query` under the retriever's mode.

        Every hit carries: `score` (ranking score), `cosine` (dense similarity,
        0.0 if only BM25 found it), and — in rerank mode — `rerank`.
        """
        vec = self.vector_search(query, CANDIDATES, doc_types, formats)
        cosine = {h["chunk_id"]: h["cosine"] for h in vec}

        if self.mode == MODE_VECTOR:
            ranked = vec[:k]
            return [{**self._by_id[h["chunk_id"]], "score": h["cosine"],
                     "cosine": h["cosine"]} for h in ranked]

        # hybrid: fuse dense + BM25 with RRF
        bm = self.bm25_search(query, CANDIDATES, doc_types, formats)
        fused = self._rrf([vec, bm])
        order = sorted(fused, key=lambda c: -fused[c])

        if self.mode == MODE_HYBRID:
            top = order[:k]
            return [{**self._by_id[c], "score": fused[c], "cosine": cosine.get(c, 0.0)}
                    for c in top]

        # hybrid_rerank: rerank the fused candidate pool by dense cosine, take top-k
        pool = order[:CANDIDATES]
        reranked = sorted(
            pool,
            key=lambda c: self._rerank_score(query, c, cosine, fused),
            reverse=True,
        )[:k]
        return [{**self._by_id[c], "score": fused[c], "cosine": cosine.get(c, 0.0),
                 "rerank": self._rerank_score(query, c, cosine, fused)[0]}
                for c in reranked]
