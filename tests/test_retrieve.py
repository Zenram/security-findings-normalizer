"""Offline tests for Part 2 Step 2 retrieval (`src/rag/retrieve.py`).

Uses a FAKE embedder (deterministic bag-of-words vectors) so there is no model
download, no network, and no onnxruntime dependency in the test run. The goal is
to protect the retrieval CONTRACT: RRF fusion, the three modes, the doc_type
metadata filter, and hit metadata — not embedding quality (that is measured
separately by `eval_retrieval` against the real model).
"""

import math

import pytest

qdrant_client = pytest.importorskip("qdrant_client")
pytest.importorskip("rank_bm25")

from qdrant_client import QdrantClient

from src.rag.embed import EMBED_DIM
from src.rag.index import build_collection
from src.rag.retrieve import (
    MODE_HYBRID,
    MODE_HYBRID_RERANK,
    MODE_VECTOR,
    Retriever,
)

VOCAB = ["iam", "least", "privilege", "encryption", "container", "root",
         "cve", "injection", "token", "branch"]


class FakeEmbedder:
    """Deterministic bag-of-words embedding over a fixed vocab, padded/truncated
    to EMBED_DIM. No model, no network."""

    def _vec(self, text: str) -> list[float]:
        t = text.lower()
        counts = [float(t.count(w)) for w in VOCAB]
        norm = math.sqrt(sum(c * c for c in counts)) or 1.0
        base = [c / norm for c in counts]
        return (base + [0.0] * EMBED_DIM)[:EMBED_DIM]

    def embed(self, texts):
        return [self._vec(t) for t in texts]

    def embed_one(self, text):
        return self._vec(text)


CHUNKS = [
    {"chunk_id": "a#0", "source": "doc_a", "doc_type": "standard", "format": "md",
     "title": "A", "section": "IAM", "text": "iam least privilege for roles"},
    {"chunk_id": "b#0", "source": "doc_b", "doc_type": "best_practice", "format": "pdf",
     "title": "B", "section": "Containers", "text": "container running as root is risky"},
    {"chunk_id": "c#0", "source": "doc_c", "doc_type": "cve", "format": "md",
     "title": "C", "section": "CVE", "text": "cve privilege escalation via injection"},
    {"chunk_id": "d#0", "source": "doc_d", "doc_type": "alert_cnapp", "format": "csv",
     "title": "D", "section": "Branch", "text": "default branch requires one reviewer token"},
]


def _retriever(mode: str) -> Retriever:
    emb = FakeEmbedder()
    client = QdrantClient(location=":memory:")
    build_collection(client, CHUNKS, emb)
    return Retriever(mode=mode, chunks=CHUNKS, client=client, embedder=emb)


def test_modes_are_validated():
    with pytest.raises(ValueError):
        _retriever("nonsense")


def test_vector_mode_returns_relevant_top_hit():
    r = _retriever(MODE_VECTOR)
    hits = r.search("iam least privilege", k=2)
    assert hits[0]["source"] == "doc_a"
    assert "cosine" in hits[0] and "score" in hits[0]


def test_hybrid_mode_fuses_and_finds_lexical_match():
    r = _retriever(MODE_HYBRID)
    # "reviewer" only appears lexically in doc_d — hybrid should surface it.
    hits = r.search("which branch requires a reviewer", k=4)
    assert any(h["source"] == "doc_d" for h in hits)


def test_doc_type_filter_restricts_results():
    r = _retriever(MODE_HYBRID)
    hits = r.search("privilege escalation", k=4, doc_types=["cve"])
    assert hits, "expected at least one cve hit"
    assert all(h["doc_type"] == "cve" for h in hits)


def test_rerank_mode_sets_rerank_field():
    r = _retriever(MODE_HYBRID_RERANK)
    hits = r.search("container root", k=2)
    assert hits
    assert "rerank" in hits[0]


def test_hit_carries_citation_metadata():
    r = _retriever(MODE_HYBRID)
    hits = r.search("iam", k=1)
    h = hits[0]
    for field in ("chunk_id", "source", "doc_type", "section", "title"):
        assert field in h
