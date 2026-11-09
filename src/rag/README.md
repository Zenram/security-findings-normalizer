# `src/rag/` — RAG pipeline (Part 2)

Part 2 of the capstone: answer questions over the security corpus with cited
sources. This directory is added alongside the Part-1 extraction code and reuses
its infra (`src/config.py`, `src/models/`, `src/prompts.py`).

## Step 1 — Ingestion & chunking (done)

| File | Purpose |
|---|---|
| `ingest.py` | Discover sources → extract text per format → clean/normalize → content-hash dedup → chunk → write `chunks.jsonl` + manifest + report. Entry: `python3 main.py --ingest` or `python3 -m src.rag.ingest`. |
| `chunk.py` | Two chunkers: `chunk_structure_aware` (production, heading-aware block packing with block-level overlap) and `chunk_fixed` (fixed-size token-window baseline for the required comparison). CSV rows are emitted as atomic `record` chunks by the pipeline, not windowed. |
| `check_ingest.py` | Structural self-check of the output (scope, metadata completeness, size caps, comparison present). `python3 -m src.rag.check_ingest`. |

### Scope ingested (51 source files, 5 formats)

| doc_type | location | format |
|---|---|---|
| `standard` | `data/corpus/standard/` | PDF, MD |
| `best_practice` | `data/corpus/best_practice/` | PDF, HTML |
| `cve` | `data/corpus/cve/` | MD |
| `team_report` | `data/raw/team_reports/` | TXT |
| `scanner_linpeas` | `data/raw/oss_scanner/linpeas/` | TXT |
| `alert_aspm` | `data/raw/aspm/` | CSV (row = finding) |
| `alert_cnapp` | `data/raw/cnapp/` | CSV (row = finding) |

Trivy/Kubescape are deliberately out of scope for Step 1 (parser-shaped; add
later if time). Run `scripts/fetch_corpus.py` first to materialize the 30
downloadable corpus files.

### Output (`data/rag/`)

- `chunks.jsonl` — one JSON object per chunk (the index input for Step 2).
  Large and fully regenerated → **gitignored**.
- `ingest_manifest.json` — per-file record (doc_type, format, hashes, status,
  #chunks). Committed.
- `ingest_report.json` — totals + the fixed-vs-structure chunking comparison.
  Committed.

### Chunk record shape

```json
{
  "chunk_id": "data/corpus/cve/CVE-2021-4034.md#2",
  "source": "data/corpus/cve/CVE-2021-4034.md",
  "doc_type": "cve",
  "format": "md",
  "title": "CVE-2021-4034 — NVD advisory",
  "section": "Impact > Privilege Escalation",
  "doc_hash": "…",
  "chunk_index": 2,
  "n_tokens": 318,
  "strategy": "structure",
  "pipeline_version": "rag-ingest-v1",
  "ingested_at": "2026-11-09T…Z",
  "text": "…"
}
```

`doc_type` is the graded metadata filter used in Step 2 retrieval.
