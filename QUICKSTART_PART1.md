# Quickstart — Part 1 (Extraction)

How to run the extraction pipeline and reproduce the measured comparison.
Full results + rationale: **REPORT_PART1.md**. Code map: `src/README.md`.

## Setup

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set GEMINI_API_KEY for the cloud model
```

- `GEMINI_API_KEY` is needed only for the Gemini (cloud) model, with billing
  enabled (the free tier's ~5 req/min cap is too low for a full run).
- Local model: `ollama pull qwen3:8b && ollama serve &` (no key).
- The offline test suite needs neither: `make test`.

## Run (single command)

```bash
python3 main.py        # or: make run
```

Runs the full grid `{gemini, ollama} × {v1, v2, v3} × {deterministic, sampled}`
over the 10-doc golden set, writes per-doc outputs + aggregated metrics, and the
comparison into REPORT_PART1.md.

### Flags

| Flag | Effect |
|---|---|
| `--models gemini` / `--models ollama` | Run only one model (default: both). |
| `--prompts v1 v2 v3` | Run specific prompt version(s) (default: all). |
| `--sampling deterministic` | Run one sampling config (default: both). |
| `--corpus` | Also process the full unlabeled raw corpus after the golden grid. |
| `--corpus-only` | Only process the raw corpus (skip the golden grid). |
| `--rescore` | Recompute metrics from committed `results/raw/` — no model calls (free). |

Examples:

```bash
python3 main.py --models gemini --prompts v3 --sampling deterministic   # the production config
python3 main.py --rescore                                               # regenerate metrics, no API cost
python3 main.py --corpus                                                # golden + full corpus sweep
```

## What gets written

- `results/raw/*.json` — per-document outputs (committed).
- `results/metrics.json`, `results/REPORT_DATA.json` — aggregated metrics feed.
- `REPORT_PART1.md` — the model × prompt × sampling comparison, routing table,
  error analysis, and the production choice.

A model that is unreachable (no key / Ollama down) produces clearly-marked
`failed` rows — never fabricated numbers.

## Cost (paid model)

Gemini `gemini-3.5-flash` at `$0.0015 / 1K` input, `$0.009 / 1K` output tokens
(set in `.env` as `GEMINI_*_PRICE_PER_1K`). Full golden run ≈ **$8–10 per 1000
docs**; a single run is a fraction of a US cent. Local (Ollama) is $0 API cost.

## Notes

- Keys live in `.env` only (gitignored); only `.env.example` is committed.
- Part 1 raw inputs (`data/raw/`) are sanitized but kept local-only; the golden
  set (`data/golden/`) is committed.
- Python 3.13 recommended (shared with Part 2); Part 1 alone runs on 3.10+.
