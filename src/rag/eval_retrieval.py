"""Retrieval quality measurement for Part 2 Step 2.

Measures recall@k and MRR for the three retrieval modes (vector / hybrid /
hybrid+rerank) over a known-answer question set
(`evals/retrieval_questions.jsonl`). Ground truth is the EXPECTED SOURCE
document: a question is a hit at rank r if a retrieved chunk comes from any of
its `expected_sources`. (Source-level truth is robust — it does not depend on
exact chunk boundaries, which the chunker may change.)

Metrics (standard IR definitions):
  - recall@k : fraction of questions whose expected source appears in the top-k
  - MRR      : mean of 1/rank of the first correct hit (0 if none in top-k)

Run:
    python3 main.py --eval-retrieval          # build index once, measure 3 modes
    python3 -m src.rag.eval_retrieval

Writes:
    evals/results/retrieval_metrics.json      # the measured numbers
    REPORT_PART2.md                           # (created/updated) with the table
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient

from src.config import REPO_ROOT
from src.rag.embed import Embedder
from src.rag.index import build_collection, load_chunks
from src.rag.retrieve import (
    MODE_HYBRID,
    MODE_HYBRID_RERANK,
    MODE_VECTOR,
    Retriever,
)

QUESTIONS_PATH = REPO_ROOT / "evals" / "retrieval_questions.jsonl"
RESULTS_DIR = REPO_ROOT / "evals" / "results"
RESULTS_PATH = RESULTS_DIR / "retrieval_metrics.json"
REPORT_PATH = REPO_ROOT / "REPORT_PART2.md"

K_VALUES = (1, 3, 5, 10)
MODES = (MODE_VECTOR, MODE_HYBRID, MODE_HYBRID_RERANK)
MODE_LABELS = {
    MODE_VECTOR: "vector-only",
    MODE_HYBRID: "hybrid (BM25+vec+RRF)",
    MODE_HYBRID_RERANK: "hybrid + rerank",
}


def load_questions() -> list[dict]:
    return [json.loads(l) for l in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines() if l]


def _first_hit_rank(hits: list[dict], expected_sources: list[str]) -> int | None:
    """1-based rank of the first hit from an expected source, else None."""
    exp = set(expected_sources)
    for rank, h in enumerate(hits, 1):
        if h["source"] in exp:
            return rank
    return None


def evaluate_mode(retriever: Retriever, questions: list[dict], max_k: int) -> dict:
    """Run every question once at max_k, then derive recall@k / MRR per k."""
    per_q = []
    for q in questions:
        hits = retriever.search(q["question"], k=max_k)
        rank = _first_hit_rank(hits, q["expected_sources"])
        per_q.append({"id": q["id"], "rank": rank,
                      "top_source": hits[0]["source"] if hits else None})

    metrics = {}
    for k in K_VALUES:
        recall = sum(1 for r in per_q if r["rank"] is not None and r["rank"] <= k) / len(per_q)
        metrics[f"recall@{k}"] = round(recall, 4)
    mrr = sum(1.0 / r["rank"] for r in per_q if r["rank"] is not None) / len(per_q)
    metrics["mrr"] = round(mrr, 4)
    return {"metrics": metrics, "per_question": per_q}


def run() -> dict:
    questions = load_questions()
    chunks = load_chunks()
    max_k = max(K_VALUES)

    # Build the index ONCE and share the client + embedder across all modes, so
    # the only thing that varies between modes is the retrieval algorithm.
    embedder = Embedder()
    client = QdrantClient(location=":memory:")
    build_collection(client, chunks, embedder)

    results = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "questions": len(questions),
        "k_values": list(K_VALUES),
        "modes": {},
    }
    for mode in MODES:
        r = Retriever(mode=mode, chunks=chunks, client=client, embedder=embedder)
        results["modes"][mode] = evaluate_mode(r, questions, max_k)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


# --- reporting ---------------------------------------------------------------

def _table(results: dict) -> str:
    header = "| Mode | " + " | ".join(f"recall@{k}" for k in K_VALUES) + " | MRR |"
    sep = "|" + "---|" * (len(K_VALUES) + 2)
    lines = [header, sep]
    for mode in MODES:
        m = results["modes"][mode]["metrics"]
        cells = " | ".join(f"{m[f'recall@{k}']:.2f}" for k in K_VALUES)
        lines.append(f"| {MODE_LABELS[mode]} | {cells} | {m['mrr']:.3f} |")
    return "\n".join(lines)


def print_report(results: dict) -> None:
    print(f"\nRetrieval eval  ({results['generated']})  — {results['questions']} questions")
    print(f"\n{_table(results)}\n")
    # Show which questions each mode missed at k=5 (useful signal).
    for mode in MODES:
        missed = [p["id"] for p in results["modes"][mode]["per_question"]
                  if p["rank"] is None or p["rank"] > 5]
        print(f"  {MODE_LABELS[mode]:<24} missed@5: {missed or 'none'}")
    print(f"\n  -> {RESULTS_PATH.relative_to(REPO_ROOT)}\n")


def main() -> int:
    results = run()
    print_report(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
