# Quickstart — Part 2 (RAG)

How to run the RAG slice end to end: ingest → index → ask → evals in CI.
Full results + rationale: **REPORT_PART2.md**. Module map: `src/rag/README.md`.
Eval harness: `evals/README.md`.

## Setup

```bash
python3.13 -m venv .venv && source .venv/bin/activate   # 3.13 required (see note)
pip install -r requirements.txt
cp .env.example .env          # set GEMINI_API_KEY for answering + the judge
```

> **Python 3.13 is required** for Part 2: `fastembed` pulls `onnxruntime`, which
> has no wheel for Python 3.14/3.15 yet. 3.10–3.13 all work; use 3.13.

The RAG corpus (`data/corpus/`, 32 public docs) is committed, so a fresh clone
can ingest immediately. If it is ever missing: `python3 scripts/fetch_corpus.py`.

## Single command (proves the whole slice)

```bash
make evals-ci
```

Runs: lint the testset → ingest the corpus → judged evals + CI gate. This is the
command the CI workflow runs. Needs `GEMINI_API_KEY` for the judged stage.

## Step-by-step

```bash
# 1. Ingest: corpus -> chunks + manifest + report
python3 main.py --ingest
python3 -m src.rag.check_ingest          # 11 structural checks (free)

# 2. Measure retrieval quality (recall@k / MRR over 3 modes)
python3 main.py --eval-retrieval

# 3. Ask a question (cited answer, or an honest "I don't know")
python3 main.py --ask "How should least privilege be enforced for IAM roles?"
python3 main.py --ask "What is CVE-2019-5736?" --model ollama --doc-types cve
python3 main.py --ask "What is CVE-2026-0965 and its CVSS score?"   # trap -> refuses

# 4. Evals
python3 main.py --evals --lint               # check the testset (free, no model)
python3 main.py --evals                        # deterministic scorers (free)
python3 main.py --evals --judge --calibrate    # + LLM judge + faithfulness + calibration (paid)
python3 main.py --evals --judge --gate         # the CI gate
```

### `--ask` flags

| Flag | Effect |
|---|---|
| `--model gemini` / `--model ollama` | Which model answers (default: gemini). |
| `--doc-types cve,best_practice` | Restrict retrieval to doc types (metadata filter). |
| `--k 8` | Number of chunks retrieved (default: 5). |
| `--prompt v1` | RAG answer prompt version. |
| `--sampling deterministic` | Sampling config. |

### `--evals` flags

| Flag | Effect |
|---|---|
| `--lint` | Validate the testset only — no model calls (free). |
| `--judge` | Run the LLM judge + faithfulness (paid). |
| `--calibrate` | Report judge-vs-human agreement from `evals/labels.jsonl`. |
| `--save-baseline` | Write `evals/baseline.json` from this run. |
| `--gate` | Exit non-zero if metrics drop below baseline (CI). |

## Stack

fastembed `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, local) + Qdrant
(in-process) + BM25 + RRF. The answerer routes retrieved context into the Part-1
Gemini/Ollama adapters.

## Results (measured — see REPORT_PART2.md)

- **Retrieval:** hybrid (BM25 + dense + RRF) → recall@3 = 1.00.
- **Answering:** cites doc + section; abstain = 1.00 on no-answer/trap questions.
- **Judge:** calibrated — agreement 0.96, false_pass 0.00 vs 23 hand labels.

## Cost (paid model)

Only the judged stage calls the API; embeddings and retrieval are local/free, and
deterministic scorers are free. Gemini `gemini-3.5-flash` at `$0.0015 / 1K` input
and `$0.009 / 1K` output tokens.

- **Per 1000 questions (answer only):** ~$3–5 (≈2–3K input tokens of context +
  a short cited answer per question).
- **Per 1000 questions (answer + judge + faithfulness):** ~$6–10.
- **One full CI eval run (23-question set, judged):** **< $0.05**.

Exact figures are computed from real token counts; see REPORT_PART2.md §8.

## CI

`.github/workflows/evals.yml` runs on PRs/pushes touching RAG code, prompts, or
the testset. Python 3.13. Offline stages (tests, lint, ingest) are free; the
judged gate uses the `GEMINI_API_KEY` **repository secret** and fails the build
if metrics drop >0.07 below `evals/baseline.json`.
