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

## Step 2 — Index & hybrid search (done)

| File | Purpose |
|---|---|
| `embed.py` | fastembed wrapper (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim) with a persistent content-hash embedding cache. Lazy model load. |
| `index.py` | Build/load the Qdrant collection from `chunks.jsonl` (in-memory or on-disk). Full chunk payload stored so metadata filters + citations work. |
| `retrieve.py` | Hybrid retriever: dense (Qdrant cosine) + sparse (BM25) fused with RRF, `doc_type`/`format` filter, three modes (`vector` / `hybrid` / `hybrid_rerank`). |
| `eval_retrieval.py` | Measure recall@k / MRR over the 3 modes against `evals/retrieval_questions.jsonl`. Entry: `python3 main.py --eval-retrieval`. |

```python
from src.rag.retrieve import Retriever
r = Retriever(mode="hybrid")                       # builds the in-memory index
hits = r.search("What is CVE-2021-4034?", k=5, doc_types=["cve"])
hits[0]["source"], hits[0]["section"], hits[0]["score"], hits[0]["cosine"]
```

Each hit carries full citation metadata (`source`, `doc_type`, `section`,
`title`) plus `score` (ranking) and `cosine` (dense similarity). Step 3's
answerer routes `hits` text into the Part-1 Gemini/Ollama adapters.

**Measured:** hybrid reaches recall@3 = 1.00 (best); see `REPORT_PART2.md` §4.
Stack runs on **Python 3.13** (`onnxruntime` has no 3.15 wheel).

## Step 3 — RAG with sources (done)

| File | Purpose |
|---|---|
| `answer.py` | `RagAnswerer`: retrieve → numbered context under a token budget → model answers only from context → parse `{found, answer, citations}` → validate citations → honest "I don't know". Routes through the Part-1 Gemini/Ollama adapters. |
| `ask.py` | CLI: `python3 main.py --ask "…" [--model gemini|ollama] [--doc-types cve,…] [--k N]`. |
| `prompts/rag_answer_v1.md` | Answerer prompt: cite doc+section per claim, strict JSON, "I don't know" path, data-not-instructions boundary. Logged in `prompts/CHANGELOG.md`. |

```python
from src.rag.answer import RagAnswerer
a = RagAnswerer(model="gemini", prompt_version="v1", k=5)
ans = a.answer("How should least privilege be enforced for IAM roles?")
ans.found, ans.answer, ans.citations        # citations map back to retrieved chunks
```

**Graded behaviors enforced in code (not just prompted):**
- cite doc + section per claim — citations validated against real source labels;
- context assembled under a **token budget** (`DEFAULT_CONTEXT_BUDGET_TOKENS`);
- explicit **"I don't know / not in the documents"** when retrieval is empty, the
  model refuses, output is unparseable, or an answer cites nothing real
  (ungrounded → downgraded to not-found);
- injection resistance carried over from Part 1 (sources are untrusted data).

Verified live on both models: grounded questions return cited answers; synthetic
`CVE-2026-*` and off-topic questions correctly refuse. See `REPORT_PART2.md` §7.
