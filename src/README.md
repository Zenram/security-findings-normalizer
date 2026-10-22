# `src/` — implementation map

Brief guide to what each file does. The pipeline per document is:

```
raw text ─► routing.detect_source ─► PARSER path (aspm)   ─┐
                                 └─► LLM path (everything) ─┤
                                                            ▼
            prompts.render ─► models/* (Gemini|Ollama) ─► validate.parse
            ─► normalize (code table assigns enums) ─► schema-validate
            ─► 1 repair if invalid, else "failed" ─► evaluate vs golden
```

## Files

| File | Responsibility |
|---|---|
| `config.py` | All configuration: env/`.env` loading, model ids (`GEMINI_MODEL`, `OLLAMA_MODEL`), `SamplingConfig` (deterministic vs sampled), `RunConfig` (the model × prompt × sampling grid), timeouts, pacing, price vars. |
| `routing.py` | **D1 routing.** `detect_source(text)` classifies a doc (aspm / team_report / linpeas / mixed / unknown); `route_and_extract(...)` sends structured ASPM to the parser and everything else to the LLM. Stamps `route`/`source` on each result. |
| `parsers/aspm_parser.py` | Deterministic Ox ASPM parser (CSV + golden block format). Maps columns → schema fields, applies D4 dual-severity + D6 team inference + CVE extraction. **No model call.** |
| `prompts.py` | Loads versioned prompt files (`prompts/extract_vN.md`) and injects the source text into the `{source_text}` data-boundary. |
| `models/base.py` | The shared `ModelAdapter` contract + `ModelResponse` dataclass. Adapters only return raw text + timing + token usage; parsing/validation happens upstream. |
| `models/gemini_adapter.py` | Gemini (cloud) adapter via `google-genai`. Structured-output request, timeout, and quota-aware retry (parses the server's `retryDelay` on 429/503). |
| `models/ollama_adapter.py` | Ollama (local) adapter via REST. `format:"json"` + `think:false` (so reasoning models like qwen3 return the answer fast). |
| `models/__init__.py` | `get_adapter(model_id)` registry ("gemini" / "ollama"). |
| `extract.py` | The shared `extract(text, model, prompt_version, sampling) -> ExtractionResult` interface. Owns the **1-repair-then-fail** loop and the per-result metadata log (model, prompt version, sampling, latency, tokens, route). |
| `validate.py` | `parse_json_array` (tolerant JSON parsing), `apply_normalization` (runs the D4 tables), `validate_findings` (parse → normalize → schema-validate against `Finding`). |
| `normalize.py` | **D4 code tables.** `normalize_severity` / `normalize_status` / `normalize_finding_type`: map the model's `*_raw` wording to the controlled enums. Unknown → `unknown`/`other` + a flag, never invented. |
| `golden.py` | Loads the `NN_input` / `NN_expected.json` pairs from `data/golden/`. |
| `corpus.py` | Loads the full **unlabeled** raw corpus (team reports + LinPEAS + Ox ASPM rows) for `--corpus` mode. One text per report/LinPEAS file; one text per ASPM CSV **row**. Processed, not scored. |
| `evaluate.py` | **D2 scoring.** `match_findings` (match predicted↔golden by stable key → matched/missed/spurious, never by position), field accuracy over matched pairs, finding-level P/R, % valid JSON, hallucination rate, latency p50/p95. `RunMetrics` aggregates per grid cell. |
| `cost.py` | Cost-per-1000-docs. Provider: real token counts × real prices from `.env` (null if unset — never fabricated). Local: null on purpose (no per-token invoice), reports latency instead. |
| `runner.py` | Ties it together. Sweeps the grid over the golden set, routes each doc, scores, writes `results/raw/*.json`, `results/metrics.json`, `results/REPORT_DATA.json`, prints a summary. Flags: `--models/--prompts/--sampling`; `--corpus` (also process the full unlabeled raw corpus → `results/corpus/`, not scored); `--corpus-only`. |
| `main.py` | Module entry (`python -m src.main`). The primary entry point is `main.py` at the repo root (`python3 main.py`). |
| `__init__.py` | Package markers (required for imports). |

## Where the key decisions live (from CAPSTONE_PLAN)

- **D1 routing** → `routing.py` + `parsers/`
- **D2 scoring** → `evaluate.py`
- **D3 injection defense** → the data-boundary in `prompts/extract_v*.md` (tested by golden entry 10)
- **D4 normalization** → `normalize.py` (enums are code-assigned, model only extracts `*_raw`)
- **D5 granularity / D6 team inference** → encoded in the prompts and in `parsers/aspm_parser.py`

## Extending

- **New structured source** (e.g. Trivy): add a parser under `parsers/`, teach
  `routing.detect_source` to recognize it, and route it to the parser.
- **New finding category / enum value**: add to `schema/finding.py` and the
  alias map in `normalize.py`.
- **New prompt version**: add `prompts/extract_v3.md`, log it in
  `prompts/CHANGELOG.md`, add `"v3"` to `RunConfig.prompt_versions`.
