# `evals/` — RAG eval harness + CI gate (Part 2 Step 4)

Measures RAG answer quality and gates CI on it.

| File | Purpose |
|---|---|
| `testset.jsonl` | 23 questions with expected answer + source(s): 17 answerable, 3 no-answer, 3 traps. **Human-written**, grounded in real corpus content. `kind` ∈ `answerable` / `no_answer` / `trap`. |
| `labels.jsonl` | Hand-graded `correct` labels for the 23 answers, used to **calibrate the LLM judge** (report agreement %). Human-set, with a `note` per item. |
| `scorers.py` | Deterministic scorers (source cited / facts present / abstained) + LLM-judge + faithfulness, routed through the Gemini adapter. |
| `run_evals.py` | Runs the answerer over the testset, aggregates metrics, calibrates the judge, applies the CI gate. |
| `baseline.json` | Frozen metrics the gate compares against. Regenerate with `--save-baseline`. |
| `results/eval_metrics.json` | Latest run output (metrics + per-row answers + calibration). |

## Commands

```bash
python3 main.py --evals --lint                    # check the testset (no model, free)
python3 main.py --evals                            # deterministic scorers only (free)
python3 main.py --evals --judge                    # + LLM judge + faithfulness (needs GEMINI_API_KEY)
python3 main.py --evals --judge --calibrate        # also report judge-vs-human agreement
python3 main.py --evals --save-baseline            # write baseline.json from this run
python3 main.py --evals --judge --gate             # CI: exit 1 if below baseline
# or: make evals-ci
```

## Metrics

| Metric | Meaning | Applies to |
|---|---|---|
| `pass` | deterministic pass rate | all |
| `facts` | every `must` fact group present in the answer | answerable |
| `source_cited` | an expected source document is cited | answerable |
| `abstain` | correctly said "I don't know" | no_answer + trap |
| `false_abstain` | answerable question wrongly refused (lower is better) | answerable |
| `judge` | LLM-judge correctness (meaning level) | all |
| `faithful` | every answer claim grounded in the retrieved context of cited docs | answered |

## Question kinds

- **answerable** — the answer is in the corpus; needs the right source cited +
  the key facts.
- **no_answer** — not in the corpus; the system must abstain.
- **trap** — looks answerable but isn't: synthetic `CVE-2026-*` IDs (exist only
  in our findings, not as NVD advisories) and misattribution ("what password
  rotation does NIST 800-207 mandate?" — 800-207 is Zero Trust, not passwords).
  The system must abstain, not fabricate.

## Judge calibration

`labels.jsonl` holds human `correct` labels. `--calibrate` runs the judge on the
same answers and reports **agreement / false_pass / false_fail** so the judge is
trusted only as far as it matches people. The gate relies on the judge; a judge
with low agreement would be fixed (new `judge_vN.md`) before trusting its numbers.

## The gate (CI)

`.github/workflows/evals.yml` runs on PRs/pushes touching RAG code, prompts, or
the testset. Offline stages (unit tests, lint, ingest) run free; the judged gate
calls Gemini via the `GEMINI_API_KEY` repo secret over the bounded testset and
**fails the build** if any metric drops more than `TOLERANCE` (0.07) below
`baseline.json`, or if a case that passed in baseline now fails. CI runs on
**Python 3.13**.
