# Security Findings Normalizer

Part 1 (Extraction) of a 4-part AI Engineering capstone. Turns "dirty" security
texts
(team reports, CNAPP/ASPM alert exports, open-source scanner output) into
valid structured JSON against one canonical schema, and proves — with numbers —
which model and prompt to pick for production.

> **Status:** Part 1 (Extraction) complete. Schema, shared model interface,
> validation + 1-retry, versioned prompts (v1/v2), eval harness, and a full
> measured run are in place. See `REPORT.md` for results. The schema under
> `schema/` is the frozen Part 1 contract. ("Part" = one of the 4 big project
> steps: Extraction → RAG → Agent → Service.)

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
  Full-run cost is a fraction of a US cent (~$8 per **1000** docs).
- **Local:** Ollama `qwen3:8b` — no key, runs on the laptop. Needs `ollama serve`
  running and the model pulled. (Reasoning model; the adapter sends `think=false`
  so it returns the JSON answer fast, ~7s/doc.)
- Both behind one shared `extract(text, model, prompt_version, sampling)` interface.

## Setup

```bash
# Python 3.11+ (tested on 3.14). A venv is recommended.
python3 -m venv .venv && source .venv/bin/activate
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
python3 main.py --models gemini         # provider only
python3 main.py --models ollama         # local only
python3 main.py --prompts v1            # one prompt version
python3 main.py --sampling deterministic  # one sampling config
python3 main.py --corpus                # ALSO process the full raw corpus (~30 texts)
python3 main.py --corpus-only           # ONLY process the raw corpus (skip the golden grid)
make run                                # equivalent wrapper
```

By default the run processes the **10 golden** texts (the labeled set used for
all quality metrics). To also process the wider **unlabeled corpus** (team
reports + LinPEAS + Ox ASPM in `data/raw/`, **28 corpus texts → 38 total with the
golden set**), add `--corpus`. Corpus texts are **processed and saved, not
scored** (no answer key) — outputs go to `results/corpus/` and a
`results/corpus_summary.json` (valid %, latency, cost, routing). This satisfies
Step 1's "run all texts" while keeping accuracy measured only on the golden set.
See REPORT.md §6.

Runs extraction across every model × prompt version × sampling config over the
golden set, writes per-document outputs to `results/raw/`, aggregated metrics to
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
