# `tests/` — test suite

Run them:

```bash
source .venv/bin/activate
make test          # or: python3 -m pytest -q
```

All tests are **offline** — no network, no API key, no running Ollama. The
pipeline test uses a fake in-memory model adapter, so the suite is deterministic
and fast (~0.1s). 35 tests total.

## Files

| File | What it covers | Count |
|---|---|---|
| `test_schema.py` | The `Finding` schema contract: valid record passes; missing required `title` fails; bad enum fails; nulls allowed where specified; defaults are `unknown`; **every golden `*_expected.json` record validates** against the model. | 6 |
| `test_normalize.py` | D4 code tables: known severity/status/finding_type map correctly; LinPEAS state words ("Vulnerable") → `unknown` (not guessed); "suggested accept-risk (not applied)" → `open`; unmapped values → `unknown`/`other` + a flag. | 10 |
| `test_pipeline.py` | The `extract()` flow with a **fake adapter**: happy path applies the code-table normalization; the 1-repair-then-ok path; the 1-repair-then-**failed** path (no silent drop); D2 matching classifies matched/missed/spurious; `evaluate_result` aggregates metrics. | 6 |
| `test_routing.py` | D1 routing: ASPM detected → parser, team reports/LinPEAS → LLM, cross-source "mixed" → LLM (not parsed); the ASPM parser output matches golden entries 06 & 07 **without a model**; parser output still gets code-table enums; parser rejects non-ASPM text. | 9 |
| `test_corpus.py` | Corpus loader: all 3 sources present; ASPM CSVs expand to one text per row; doc ids unique; ASPM routes to parser, others to LLM. | 4 |
| `conftest.py` | Puts the repo root on `sys.path` so `import src...` / `import schema...` work under pytest from any directory. | — |
| `__init__.py` | Package marker. | — |

## What is intentionally NOT tested here

- **Live model quality** (Gemini/Ollama output accuracy) — that is measured by
  the real run (`python3 main.py` → `results/` + `REPORT.md`), not by unit tests,
  because it needs live models and is non-deterministic.
- Network/quota/billing behavior — exercised during real runs, not in CI.

## Adding tests

- New parser → add cases to `test_routing.py` (detection + output vs a golden
  entry).
- New normalization rule → add a case to `test_normalize.py`.
- New schema field/enum → extend `test_schema.py`.
