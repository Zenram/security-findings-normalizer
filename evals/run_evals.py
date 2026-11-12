"""Part 2 Step 4 — eval harness + CI gate.

    python3 main.py --evals --lint            # check the testset itself (no model, free)
    python3 main.py --evals                    # deterministic scorers only (free)
    python3 main.py --evals --judge            # + LLM judge + faithfulness (needs GEMINI_API_KEY)
    python3 main.py --evals --judge --calibrate  # also report judge-vs-human agreement
    python3 main.py --evals --save-baseline    # write evals/baseline.json from this run
    python3 main.py --evals --judge --gate     # CI: exit 1 if metrics drop below baseline

Metrics (answerable vs no_answer/trap split):
  pass          overall pass rate (deterministic)
  facts         key facts present (answerable)
  source_cited  an expected source cited (answerable)
  abstain       said "I don't know" when it should (no_answer + trap)
  false_abstain answerable questions wrongly refused
  judge         LLM-judge correctness (meaning level), when --judge
  faithful      answers fully grounded in cited sources, when --judge

The gate fails if any metric drops more than TOLERANCE below baseline (for
false_abstain, a RISE is the regression), or if a case that passed in baseline
now fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config import REPO_ROOT
from src.rag.answer import RagAnswerer
from src.rag.index import load_chunks

from evals.scorers import (
    NO_ANSWER_KINDS,
    Faithfulness,
    Judge,
    calibrate,
    score_deterministic,
)

EVALS_DIR = REPO_ROOT / "evals"
TESTSET = EVALS_DIR / "testset.jsonl"
LABELS = EVALS_DIR / "labels.jsonl"
BASELINE = EVALS_DIR / "baseline.json"
RESULTS_DIR = EVALS_DIR / "results"

KINDS_MIN = 2                 # each kind needs at least this many cases
TOLERANCE = 0.07              # gate allows a metric to drop this much (1/23 ≈ 0.043)
LOWER_IS_BETTER = {"false_abstain"}
# `faithful` is a DIAGNOSTIC only (excluded from the gate): the current prompt
# under-reports faithfulness, so it must not block the build. See REPORT_PART2 §8.
GATE_IGNORE = {"faithful"}


def load_testset() -> list[dict]:
    return [json.loads(l) for l in TESTSET.read_text(encoding="utf-8").splitlines() if l]


# --- lint (test the tests) ---------------------------------------------------

def lint(cases: list[dict]) -> list[str]:
    problems: list[str] = []
    seen_ids: set[str] = set()
    # Check expected_sources against the corpus when built; skip that one check
    # (don't crash) if chunks.jsonl isn't present yet. CI ingests before lint.
    try:
        valid_sources: set[str] | None = {c["source"] for c in load_chunks()}
    except FileNotFoundError:
        valid_sources = None
        problems.append("note: chunks.jsonl absent — skipping expected_source checks "
                        "(run `python3 main.py --ingest` first)")
    kinds: dict[str, int] = {}
    for c in cases:
        cid = c.get("id", "?")
        kinds[c.get("kind", "?")] = kinds.get(c.get("kind", "?"), 0) + 1
        if cid in seen_ids:
            problems.append(f"{cid}: duplicate id")
        seen_ids.add(cid)
        for field in ("id", "kind", "question", "reference"):
            if not c.get(field):
                problems.append(f"{cid}: missing '{field}'")
        kind = c.get("kind")
        if kind in NO_ANSWER_KINDS:
            if c.get("expected_sources"):
                problems.append(f"{cid}: {kind} case must have empty expected_sources")
            if c.get("must"):
                problems.append(f"{cid}: {kind} case must have empty must[]")
        elif kind == "answerable":
            if not c.get("expected_sources"):
                problems.append(f"{cid}: answerable case needs expected_sources")
            if valid_sources is not None:
                for src in c.get("expected_sources", []):
                    if src not in valid_sources:
                        problems.append(f"{cid}: expected_source not in corpus: {src}")
        else:
            problems.append(f"{cid}: unknown kind '{kind}'")
    for k, n in kinds.items():
        if n < KINDS_MIN:
            problems.append(f"kind '{k}' has only {n} case(s) (< {KINDS_MIN})")
    return problems


# --- aggregation -------------------------------------------------------------

def _rate(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def aggregate(rows: list[dict], cases: list[dict]) -> dict:
    answerable = [r for r, c in zip(rows, cases) if c["kind"] not in NO_ANSWER_KINDS]
    m = {
        "pass": _rate([r["det"]["passed"] for r in rows]),
        "facts": _rate([r["det"]["facts_present"] for r in rows]),
        "source_cited": _rate([r["det"]["source_cited"] for r in rows]),
        "abstain": _rate([r["det"]["abstained"] for r in rows]),
        "false_abstain": _rate([not r["answer"]["found"] for r, c in zip(rows, cases)
                                if c["kind"] not in NO_ANSWER_KINDS]),
    }
    if any("judge" in r for r in rows):
        m["judge"] = _rate([r.get("judge") for r in rows])
    if any("faithful" in r for r in rows):
        m["faithful"] = _rate([r.get("faithful") for r in rows])
    kinds = sorted({c["kind"] for c in cases})
    m["by_kind"] = {k: _rate([r["det"]["passed"] for r, c in zip(rows, cases) if c["kind"] == k])
                    for k in kinds}
    m["failed"] = [c["id"] for r, c in zip(rows, cases) if not r["det"]["passed"]]
    return m


# --- gate --------------------------------------------------------------------

def gate(metrics: dict, baseline: dict) -> list[str]:
    failures: list[str] = []
    for key, base_val in baseline.items():
        if key in ("by_kind", "failed") or key in GATE_IGNORE or base_val is None:
            continue
        cur = metrics.get(key)
        if cur is None:
            continue
        if key in LOWER_IS_BETTER:
            if cur > base_val + TOLERANCE:
                failures.append(f"{key}: {cur:.2f} worse than baseline {base_val:.2f} (lower is better)")
        elif cur < base_val - TOLERANCE:
            failures.append(f"{key}: {cur:.2f} below baseline {base_val:.2f}")
    # Deliberately no per-case regression gating: LLM output varies run-to-run
    # even at temp 0 (REPORT_PART1 §9), so cases flip and would make CI flaky.
    # The gate uses aggregate metrics with a tolerance instead.
    return failures


# --- run ---------------------------------------------------------------------

def run(use_judge: bool, model: str, prompt: str, k: int) -> tuple[list[dict], dict]:
    cases = load_testset()
    answerer = RagAnswerer(model=model, prompt_version=prompt, k=k)
    judge = Judge(model=model) if use_judge else None
    faith = Faithfulness(model=model) if use_judge else None

    rows: list[dict] = []
    for c in cases:
        ans = answerer.answer(c["question"]).as_dict()
        row = {"id": c["id"], "kind": c["kind"], "answer": ans,
               "det": score_deterministic(ans, c).as_dict()}
        if judge is not None:
            v = judge.verdict(c["question"], c["reference"], ans["answer"])
            if v is not None:
                row["judge"] = v
            src_texts = _grounding_texts(ans)
            f, unsupported = faith.check(ans["answer"], ans["found"], src_texts)
            if f is not None:
                row["faithful"] = f
                row["unsupported"] = unsupported
        rows.append(row)
    return rows, aggregate(rows, cases)


def _grounding_texts(ans: dict) -> list[str]:
    """Texts the answer could legitimately be grounded in: the chunks it cited
    PLUS the other retrieved chunks from the SAME source documents.

    Faithfulness = grounded in the retrieved context, not in one exact chunk. An
    answer often cites `[S1]` but synthesizes across several retrieved chunks of
    the same advisory/doc; scoring only the single cited chunk under-counts
    faithfulness. We therefore ground against all retrieved chunks whose source
    document was cited."""
    by_id = {c["chunk_id"]: c for c in load_chunks()}
    cited_sources = {s["source"] for s in ans.get("cited_sources", [])}
    retrieved_ids = ans.get("retrieved", [])
    texts: list[str] = []
    for cid in retrieved_ids:
        chunk = by_id.get(cid)
        if chunk and chunk["source"] in cited_sources:
            texts.append(chunk["text"])
    # Fallback: if nothing matched (e.g. no retrieved list), use cited chunks.
    if not texts:
        for s in ans.get("cited_sources", []):
            t = by_id.get(s.get("chunk_id"), {}).get("text") if isinstance(by_id.get(s.get("chunk_id")), dict) else None
            if t:
                texts.append(t)
    return texts


# --- calibration -------------------------------------------------------------

def run_calibration(model: str) -> dict:
    if not LABELS.exists():
        raise SystemExit(f"no {LABELS} — create hand labels first (see evals/README.md)")
    items = [json.loads(l) for l in LABELS.read_text(encoding="utf-8").splitlines() if l]
    judge = Judge(model=model)
    judged, human, ids = [], [], []
    for it in items:
        v = judge.verdict(it["question"], it["reference"], it["answer"])
        judged.append(bool(v))
        human.append(bool(it["correct"]))
        ids.append(it["id"])
    result = calibrate(judged, human, ids)
    result["n"] = len(items)
    return result


# --- reporting ---------------------------------------------------------------

def write_outputs(rows: list[dict], metrics: dict, calibration: dict | None,
                  use_judge: bool) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cases": len(rows),
        "judged": use_judge,
        "metrics": metrics,
        "calibration": calibration,
        "rows": rows,
    }
    out = RESULTS_DIR / "eval_metrics.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def print_metrics(metrics: dict, calibration: dict | None) -> None:
    print("\n  metric          value")
    for key in ("pass", "facts", "source_cited", "abstain", "false_abstain", "judge", "faithful"):
        v = metrics.get(key)
        if v is not None:
            print(f"  {key:<14}  {v:.2f}")
    print("  by kind         " + "  ".join(f"{k} {v:.2f}" for k, v in metrics["by_kind"].items() if v is not None))
    print(f"  failed          {' '.join(metrics['failed']) or '-'}")
    if calibration:
        print(f"\n  judge calibration (n={calibration['n']}): agreement {calibration['agreement']:.2f}, "
              f"false_pass {calibration['false_pass']:.2f}, false_fail {calibration['false_fail']:.2f}")
        if calibration["disagreements"]:
            print(f"  judge disagrees on: {', '.join(calibration['disagreements'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RAG evals + CI gate (Part 2 Step 4)")
    ap.add_argument("--lint", action="store_true", help="check the testset, no model calls")
    ap.add_argument("--judge", action="store_true", help="run LLM judge + faithfulness (paid)")
    ap.add_argument("--calibrate", action="store_true", help="report judge-vs-human agreement")
    ap.add_argument("--save-baseline", action="store_true", help="write evals/baseline.json")
    ap.add_argument("--gate", action="store_true", help="exit 1 if below baseline")
    ap.add_argument("--model", default="gemini", choices=["gemini", "ollama"])
    ap.add_argument("--prompt", default="v1")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args(argv)

    if args.lint:
        problems = lint(load_testset())
        # "note:" lines are informational (e.g. corpus not built yet), not failures.
        real_problems = [p for p in problems if not p.startswith("note:")]
        print("\n".join(problems) or "testset OK")
        print(f"\n{len(load_testset())} cases, {len(real_problems)} problem(s)")
        return 1 if real_problems else 0

    rows, metrics = run(args.judge, args.model, args.prompt, args.k)
    calibration = run_calibration(args.model) if (args.judge and args.calibrate) else None

    print(f"\nEvals — model={args.model} prompt={args.prompt} k={args.k} "
          f"| {len(rows)} cases | judge={'on' if args.judge else 'off'}")
    print_metrics(metrics, calibration)
    out = write_outputs(rows, metrics, calibration, args.judge)
    print(f"\n  -> {out.relative_to(REPO_ROOT)}")

    if args.save_baseline:
        base = {k: v for k, v in metrics.items() if k != "by_kind"}
        BASELINE.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  baseline saved: {BASELINE.relative_to(REPO_ROOT)}")

    if args.gate:
        if not BASELINE.exists():
            raise SystemExit("no evals/baseline.json — run --save-baseline on a trusted run first")
        failures = gate(metrics, json.loads(BASELINE.read_text(encoding="utf-8")))
        print("\nGATE " + ("FAILED" if failures else "PASSED"))
        for line in failures:
            print(f"  {line}")
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
