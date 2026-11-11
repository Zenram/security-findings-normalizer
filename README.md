# Security Findings Normalizer

Part 1 (Extraction) of a 4-part AI Engineering capstone. Turns "dirty" security
texts (team reports, CNAPP/ASPM alert exports, open-source scanner output) into
valid structured JSON against one canonical schema, and proves — with numbers —
which model and prompt to pick for production.

> **Status:** Part 1 (Extraction) complete. Schema, shared model interface,
> validation + 1-retry, versioned prompts (v1/v2), eval harness, and a full
> measured run are in place. See `REPORT.md` for results. The schema under
> `schema/` is the frozen Part 1 contract. ("Part" = one of the 4 big project
> steps: Extraction → RAG → Agent → Service.)

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY to run the provider model
make test                       # offline test suite — no key or network needed
python3 main.py                 # full measured comparison run (needs a model)
```

**Prerequisites:** Python 3.11+ (tested on 3.14). A `GEMINI_API_KEY` is needed
only for the cloud model; the local model instead needs Ollama (`ollama serve`
+ `ollama pull qwen3:8b`). The test suite needs neither.

## What it does

1. Takes raw text + metadata.
2. **Routes** each document: structured sources (Ox ASPM) are parsed
   deterministically in code; genuinely unstructured sources (team reports,
   LinPEAS) go through the LLM. (D1 — the routing decision is itself a result.)
3. Extracts one or more security findings into a canonical Pydantic schema.
   Severity/status/finding_type enums are assigned by a deterministic code table
   (D4), not the model — the model only extracts the original `*_raw` wording.
4. Validates against the schema; on invalid output, **one** repair attempt,
   else the record is marked `failed` (no silent drops).
5. Logs each result with model, prompt version, sampling params, and route.
6. Scores output against a hand-labeled golden set (D2 — match by stable key,
   then field accuracy over matched pairs; never by position).

## Models compared

- **Provider (cloud):** Google Gemini — default `gemini-3.5-flash` (set in
  `.env`; `gemini-2.5-flash` is retired for new users). Needs `GEMINI_API_KEY`
  and billing enabled (the free tier's ~5 req/min cap is too low for a full run).
  Full-run cost is a fraction of a US cent (~$8 per **1000** docs). For key-free
  local testing you can set `GEMINI_MODEL=gemma-4-26b-a4b-it` (separate free
  quota bucket).
- **Local:** Ollama `qwen3:8b` — no key, runs on the laptop. Needs `ollama serve`
  running and the model pulled. (Reasoning model; the adapter sends `think=false`
  so it returns the JSON answer fast, ~7s/doc.)
- Both behind one shared `extract(text, model, prompt_version, sampling)` interface.

## Setup

```bash
# Part 1 runs on Python 3.11+. Part 2 (RAG) requires Python 3.13: fastembed
# pulls onnxruntime, which has NO wheel for Python 3.14/3.15 yet.
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # then set GEMINI_API_KEY and (optional) prices
# For the local model:
#   ollama pull qwen3:8b && ollama serve &
```

`.env` holds secrets and is gitignored; only `.env.example` is committed. The
code reads `GEMINI_API_KEY` from your environment or from `.env`.

## Run

```bash
python3 main.py                         # full grid: {gemini,ollama} x {v1,v2} x {deterministic,sampled}
make run                                # equivalent wrapper
```

### CLI flags

| Flag | Effect |
|---|---|
| `--models gemini` / `--models ollama` | Run only the provider, or only the local model. |
| `--prompts v1` | Run a single prompt version (default: both). |
| `--sampling deterministic` | Run a single sampling config (default: both). |
| `--corpus` | ALSO process the full unlabeled raw corpus (~28 texts) after the golden grid. |
| `--corpus-only` | ONLY process the raw corpus (skip the golden grid). |

By default the run processes the **10 golden** texts (the labeled set used for
all quality metrics). Add `--corpus` to also process the wider **unlabeled
corpus** (team reports + LinPEAS + Ox ASPM in `data/raw/`) — **28 corpus texts,
for 38 total with the golden set**. Corpus texts are **processed and saved, not
scored** (no answer key) — outputs go to `results/corpus/` and a
`results/corpus_summary.json` (valid %, latency, cost, routing). This satisfies
Step 1's "run all texts" while keeping accuracy measured only on the golden set.
See REPORT.md §6.

Each run writes per-document outputs to `results/raw/`, aggregated metrics to
`results/metrics.json`, and a report feed to `results/REPORT_DATA.json`. The
comparison write-up is in `REPORT.md`. A model that is unreachable (no key /
Ollama down) produces clearly-marked `failed` rows — never fabricated numbers.

```bash
make test        # run the test suite (pytest)
```

## Repository layout

```
schema/        Canonical Pydantic schema (frozen Part 1 contract)
prompts/       Versioned extraction prompts (v1, v2) + CHANGELOG
src/           Pipeline code — see src/README.md for the per-file map
  models/      Gemini + Ollama adapters behind one interface
  parsers/     Deterministic parsers for structured sources (ASPM)
data/          Inputs + golden set — see data/README.md
  raw/         INPUT DOCUMENTS — gitignored, never committed
  real/        Original sanitized exports — gitignored, never committed
  golden/      Labeled ground truth (committed; see data/golden/README.md)
results/       Run outputs — JSON results committed; logs gitignored
tests/         Offline test suite — see tests/README.md
REPORT.md      Model x prompt x sampling comparison + routing table + final choice
```

Each major directory has its own README: `src/README.md` (file map),
`tests/README.md` (what each test covers), `data/README.md` +
`data/golden/README.md` (corpus + labeling rules).

## Data & safety

- Input corpus (`data/raw/`) and the original sanitized exports (`data/real/`)
  are **not** committed.
- Only synthetic / fully sanitized examples live in `data/golden/`.
- Model outputs under `results/` (`metrics.json`, `REPORT_DATA.json`,
  `raw/*.json`) **are** committed as the course requires; only run logs are
  gitignored.
- No DB files, `.env`, or secrets are ever committed (see `.gitignore`).
- The system never fabricates values: absent -> `null` / `unknown`.
- Report text is treated as **data, not instructions** (prompt-injection safe).

## Scope (Part 1 — Extraction)

In scope: canonical schema, extraction, schema validation, model/prompt
comparison, source traceability, evaluation vs golden set.

Out of scope (later Parts): correlation/deduplication, historical tracking,
RAG (Part 2), agent (Part 3), production service (Part 4).

---

## Part 2 — RAG (in progress, branch `part-2-rag`)

Part 2 answers questions over the security corpus with cited sources. See
`src/rag/README.md` for the module map and `hm2_plan.md` for the full plan.

### Step 1 — Corpus & chunking (done)

Ingests **51 source files across 5 formats** into clean, deduplicated chunks:

```bash
python3 main.py --ingest             # -> data/rag/chunks.jsonl + manifest + report
python3 -m src.rag.check_ingest      # structural self-check (11 checks)
```

| doc_type | files | format |
|---|---|---|
| `standard` | 5 | PDF, MD |
| `best_practice` | 17 | PDF, HTML |
| `cve` | 10 | MD |
| `team_report` | 10 | TXT |
| `scanner_linpeas` | 5 | TXT |
| `alert_aspm` | 2 | CSV (row = finding) |
| `alert_cnapp` | 2 | CSV (row = finding) |

**Real numbers (latest run):** 51 files → **3,209 chunks** (3,176 structure-aware
prose chunks + 33 CSV record chunks). 0 extraction errors, 0 OCR-required.

### Chunking: strategy + the required comparison

The pipeline uses **structure-aware chunking for prose** and **record-as-chunk
for CSV alerts**, and runs a **fixed-size baseline** over the same prose docs so
the choice is measured, not asserted.

- **Prose (standards, best-practice, CVE, reports, LinPEAS):** split on headings
  into sections, then pack whole blocks (paragraphs, list groups, table blocks)
  up to a 512-token cap with a **block-level** 64-token overlap. A paragraph or a
  table row is never cut mid-content; each chunk carries its heading path in
  `section`. A single block larger than the cap is split on safe boundaries
  (table rows, or a token window for pathological unbroken text).
- **CSV (Ox ASPM, Orca CNAPP):** each alert row is one atomic `record` chunk —
  splitting an alert would destroy the record, so rows are exempt from the token
  cap. Identical rows within a file are dropped (content hash).
- **Dedup:** normalized content hash across prose files (exact duplicates), and
  per-row for CSV.

**Measured comparison** (same prose documents, lower is better for the first two):

| Strategy | Chunks | Mid-sentence starts | Cut tables | Avg tokens | Keeps section |
|---|---|---|---|---|---|
| **Structure-aware** | 3,176 | 957 | 472 | 349 | 3,031 |
| Fixed-size 512/64 | 2,503 | 1,314 | 697 | 508 | 0 (none) |

Structure-aware wins on both quality metrics (27% fewer mid-sentence starts, 32%
fewer cut tables) and is the only strategy that preserves section context for
citations. The remaining absolute counts are dominated by **PDF extraction
artifacts** (pypdf emits control-ID names like `(1) ACCOUNT MANAGEMENT | …`
containing stray `|`, and wraps sentences) — these affect *both* strategies
equally, so the head-to-head comparison is still fair. On the clean formats
(MD/HTML/CSV) structure-aware produces near-zero mid-sentence/cut-table chunks.

> **Still open for Step 2 (architecture):** the embedding model + vector store
> (A3). The plan recommends the course-lesson stack (Qdrant + fastembed + BM25 +
> RRF); this is a major architecture choice flagged for the maintainer / AI
> Solution Architect, not decided solo.

### Step 2 — Index & hybrid search (done)

Approved stack (A3): **fastembed + Qdrant + BM25 + RRF**, all local/free.

```bash
python3 main.py --eval-retrieval     # build index + measure recall@k/MRR (3 modes)
```

- **Embeddings:** fastembed `paraphrase-multilingual-MiniLM-L12-v2` (384-dim,
  local, cached). **Vector store:** Qdrant in-process (no server).
- **Hybrid retrieval:** dense (Qdrant cosine) + BM25, fused with RRF, with a
  `doc_type`/`format` metadata filter and 3 modes (`vector`/`hybrid`/`hybrid_rerank`).
- **Measured (15-question set):** hybrid reaches **recall@3 = 1.00** (best),
  beating vector-only, which misses a free-text team-report question. Full table
  + error analysis in `REPORT_PART2.md`.

> **Environment:** the stack requires **Python 3.13** — `onnxruntime` (a
> fastembed dependency) has no wheel for Python 3.15. The project `.venv` is
> pinned to 3.13; see Setup. Retrieved context routes into the existing
> Gemini/Ollama adapters for Step 3.

### Step 3 — RAG with sources (done)

Answer questions over the corpus with cited sources and an honest "I don't know".

```bash
python3 main.py --ask "How should least privilege be enforced for IAM roles?"
python3 main.py --ask "What is CVE-2019-5736?" --model ollama --doc-types cve
```

- Retrieve (hybrid) → numbered context under a **token budget** → model answers
  **only from context** → structured `{found, answer, citations}` → citations
  validated against real sources → explicit **"I don't know / not in the
  documents"** when unsupported. Prompt `prompts/rag_answer_v1.md`.
- Runs on Gemini or Ollama via the same answerer. Verified live: grounded
  questions cite doc+section; synthetic `CVE-2026-*` and off-topic questions
  refuse. See `REPORT_PART2.md` §7.
