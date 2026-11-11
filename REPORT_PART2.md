# REPORT — Part 2 (RAG on the security corpus)

Separate from the Part-1 `REPORT.md` (which stays frozen under review). Every
number here is measured — reproduce with the commands shown. Branch `part-2-rag`.

> **Status:** Step 1 (corpus & chunking), Step 2 (index & hybrid search), and
> Step 3 (RAG answerer + citations + "I don't know") done. Step 4 (eval set +
> scorers + CI gate) is next.

## Contents

1. [Stack](#1-stack)
2. [Step 1 — Corpus & chunking](#2-step-1--corpus--chunking)
3. [Step 2 — Index & hybrid search](#3-step-2--index--hybrid-search)
4. [Retrieval quality (recall@k / MRR)](#4-retrieval-quality-recallk--mrr)
5. [Error analysis](#5-error-analysis)
6. [Choice + next steps](#6-choice--next-steps)
7. [Step 3 — RAG with sources](#7-step-3--rag-with-sources)

## 1. Stack

Approved architecture (A3): **fastembed + Qdrant + BM25 + RRF**, all local/free.

| Layer | Choice | Notes |
|---|---|---|
| Embeddings | fastembed `paraphrase-multilingual-MiniLM-L12-v2` | 384-dim, EN+UK, local via onnxruntime, cached to `.models/` + a content-hash cache |
| Vector store | Qdrant (in-process) | `:memory:` per run; optional on-disk `data/rag/qdrant/`. No server to deploy. |
| Sparse | BM25Okapi (`rank-bm25`) | over the same `section + text` the dense side embeds |
| Fusion | Reciprocal Rank Fusion (RRF, k=60) | combines dense + sparse rankings |
| Filter | `doc_type` (+ optional `format`) | the graded metadata filter |

> **Environment note (blocker resolved):** the dev machine's default Python moved
> to **3.15**, for which `onnxruntime` (a fastembed dependency) has **no wheel**.
> The project `.venv` is therefore pinned to **Python 3.13**; all deps install
> there. See README "Setup". This is the same class of wheel issue Part 1 hit
> with `pydantic-core` on 3.14.

LLM routing: retrieved chunks feed the existing Part-1 adapters
(`src/models/`, Gemini `gemini-3.5-flash` + Ollama `qwen3:8b`) unchanged, so
Step 3 can A/B both models on identical retrieved context.

## 2. Step 1 — Corpus & chunking

`python3 main.py --ingest` → `data/rag/chunks.jsonl` + manifest + report.
`python3 -m src.rag.check_ingest` → 11/11 structural checks.

**51 source files → 3,209 chunks** (3,176 structure-aware prose + 33 CSV record
chunks), 5 formats, 0 extraction errors.

| doc_type | files | chunks |
|---|---|---|
| standard | 5 | 1,406 |
| best_practice | 17 | 1,422 |
| cve | 10 | 76 |
| team_report | 10 | 10 |
| scanner_linpeas | 5 | 262 |
| alert_aspm | 2 | 13 |
| alert_cnapp | 2 | 20 |

**Chunking comparison (required).** Structure-aware (heading sections, whole-block
packing, 512-tok cap, block-level overlap) vs a fixed-size token-window baseline,
over the same prose documents:

| Strategy | Chunks | Mid-sentence starts | Cut tables | Avg tokens | Keeps section |
|---|---|---|---|---|---|
| **Structure-aware** | 3,176 | 957 | 472 | 349 | 3,031 |
| Fixed-size 512/64 | 2,503 | 1,314 | 697 | 508 | 0 |

Structure-aware wins on both quality metrics (27% fewer mid-sentence starts, 32%
fewer cut tables) and is the only strategy that keeps section context for
citations. CSV alerts use record-as-chunk (one row = one atomic chunk; exempt
from the token cap). The remaining absolute counts are dominated by pypdf
extraction artifacts that affect both strategies equally. Full detail in the
repo `README.md` and `src/rag/README.md`.

## 3. Step 2 — Index & hybrid search

`python3 main.py --eval-retrieval` builds the index once and measures three
retrieval modes against a 15-question known-answer set
(`evals/retrieval_questions.jsonl`), covering all 7 doc_types (CVE lookups,
standards/best-practice concepts, team-report/LinPEAS free text, CSV alerts).

Modes:
- **vector-only** — dense (fastembed → Qdrant cosine) only.
- **hybrid** — dense + BM25 fused with RRF. *(default / production)*
- **hybrid + rerank** — rerank the fused candidate pool by dense cosine, then top-k.

Ground truth is the **expected source document**: a question is a hit at rank r
if a retrieved chunk comes from the right source. Source-level truth is robust —
it does not depend on exact chunk boundaries.

## 4. Retrieval quality (recall@k / MRR)

Measured 2026-11-10, 15 questions (`evals/results/retrieval_metrics.json`):

| Mode | recall@1 | recall@3 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|---|
| vector-only | 0.93 | 0.93 | 0.93 | 0.93 | 0.933 |
| **hybrid (BM25+vec+RRF)** | 0.87 | **1.00** | **1.00** | **1.00** | 0.933 |
| hybrid + rerank | 0.93 | 0.93 | 0.93 | 0.93 | 0.933 |

**Reads:**
- **Hybrid is the winner.** It is the only mode that reaches **recall@3 = 1.00**:
  BM25 recovers the one question (r12) that pure dense retrieval misses. Same top
  MRR (0.933) as the others.
- **vector-only** is strong on MRR but caps at recall 0.93 — it never retrieves
  the right source for r12 at any k (it returns an OWASP PDF instead).
- **rerank did not help here.** Re-ordering the fused pool by dense cosine ties
  vector-only and pushes r12 back out of the top-5, because r12 is a lexical
  (BM25) win, not a dense one. On a 15-question set this is a real, honest result:
  a cosine reranker trades a lexical win for marginal precision@1 and is not worth
  enabling over plain hybrid. (A cross-encoder reranker is the stronger option if
  reranking is pursued further; deferred — the plan lists reranker tuning as
  first-to-cut.)

## 5. Error analysis

1. **r12 (team-report free text) — dense retrieval's blind spot.** "What did the
   dev team report about the command injection pattern in the workflow URL
   helper?" Vector-only and cosine-rerank both return an OWASP Testing Guide PDF
   chunk (topically "injection") instead of the actual team report. Hybrid fixes
   it: BM25 matches the concrete lexical terms ("workflow URL helper") that the
   multilingual MiniLM embedding blurs. This single case is the whole argument
   for hybrid over vector-only on this corpus.
2. **CVE lookups are easy and dense-dominated.** r01–r04 (PwnKit, runc escape,
   Dirty Pipe, Looney Tunables) retrieve the exact advisory at rank 1 with high
   cosine (0.78+). Short, named, distinctive — dense retrieval alone nails them.
3. **CSV record chunks retrieve cleanly.** r14/r15 (Ox ASPM CSRF alert, Orca
   branch-reviewer alert) land the right row, confirming record-as-chunk + the
   `doc_type` filter work for structured alerts.
4. **rerank demotes lexical wins (observed trade-off).** The cosine reranker
   improves nothing and costs r12 — documented so the choice (plain hybrid) is
   evidence-based, not assumed.

## 6. Choice + next steps

**Production retrieval: hybrid (BM25 + dense + RRF), no rerank**, with the
`doc_type` metadata filter available for scoped queries. It gives the best recall
(1.00 @k≥3) at the same MRR, and BM25 covers the lexical/free-text cases dense
retrieval misses.

**Caveats:** 15-question set → directional, not statistically tight (same honesty
caveat as Part 1's 10-doc golden set). Expand the question set alongside the
Step-4 answer eval.

**Next (Step 3):** build `src/rag/answer.py` — context under a token budget,
answer only from retrieved chunks, **cite doc + section per claim**, and an
explicit **"I don't know / not in the documents"** path for weak retrieval.
Route the context into the Gemini/Ollama adapters. (Step 4: ≥20-question eval set
with no-answer + trap questions, deterministic + calibrated-judge + faithfulness
scorers, CI gate.)

## 7. Step 3 — RAG with sources

`src/rag/answer.py` (`RagAnswerer`) + `python3 main.py --ask "..."`. Pipeline:
retrieve (Step 2 hybrid) → build numbered context `[S1]..[Sn]` under a token
budget → model answers ONLY from context → parse `{found, answer, citations}` →
validate citations → honest refusal when unsupported. Prompt:
`prompts/rag_answer_v1.md` (logged in `prompts/CHANGELOG.md`). Runs on either
model via the Part-1 adapters.

**Graded behaviors — enforced in code, not just prompted:**
- **Cite doc + section per claim.** Citations are validated against the real
  source labels; invented labels (e.g. `[S9]` when 5 sources were given) are
  dropped. Each cited label maps back to a retrieved chunk (doc + section).
- **Context token budget.** `build_context` packs numbered sources up to
  `DEFAULT_CONTEXT_BUDGET_TOKENS` (2000); a chunk that doesn't fit is skipped.
- **"I don't know" path.** Honest refusal (`found=false`, empty citations) when:
  nothing is retrieved; the model refuses; output is unparseable; OR the model
  claims an answer but cites nothing real (ungrounded → downgraded to not-found).
- **Injection resistance.** Sources are wrapped as untrusted data; the Part-1
  data-not-instructions boundary carries into RAG.

**Live behavior (2026-11-10, verified on both models):**

| Question | Model | Result |
|---|---|---|
| "How should least privilege be enforced for IAM roles?" | gemini-3.5-flash | **found**, cited `[S3][S5]` → HIPAA.md, 5.3s |
| "What is the runc container escape in CVE-2019-5736?" (`--doc-types cve`) | qwen3:8b | **found**, cited `[S1]` → CVE-2019-5736.md, 13.4s |
| "What is CVE-2026-99999 and its CVSS score?" (synthetic trap) | gemini-3.5-flash | **not found** — refused, no fabricated score |
| "Best recipe for chocolate chip cookies?" (off-topic) | gemini-3.5-flash | **not found** — refused honestly |

The synthetic-CVE trap is the important one: retrieval returned *other* real CVE
advisories as near neighbours, and the answerer still refused rather than answer
about the wrong CVE — exactly the "I don't know" behaviour Step 4 will measure
with the `CVE-2026-*` trap questions.

**Next (Step 4):** ≥20-question eval set (incl. no-answer + `CVE-2026-*` traps),
deterministic + calibrated-LLM-judge + faithfulness scorers, CI gate that fails
below threshold.
