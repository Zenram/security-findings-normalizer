# Security Findings Normalizer

An applied-AI capstone over a real security corpus. Two parts are complete:

- **Part 1 — Extraction.** Turns "dirty" security texts (team reports, CNAPP/ASPM
  alert exports, scanner output) into valid structured JSON against one canonical
  schema, and proves — with numbers — which model and prompt to pick.
- **Part 2 — RAG.** Answers questions over the corpus with **cited sources** and
  an honest **"I don't know"**, with retrieval + answer quality measured and
  gated in CI.

> "Part" = one of the 4 capstone parts (Extraction → RAG → Agent → Service).
> Parts 1–2 are built; Parts 3–4 are future work.

## Quickstarts

- **Part 1 (Extraction):** see **[QUICKSTART_PART1.md](QUICKSTART_PART1.md)**
- **Part 2 (RAG):** see **[QUICKSTART_PART2.md](QUICKSTART_PART2.md)**

Reports with the measured results, error analysis, and conclusions:
**[REPORT_PART1.md](REPORT_PART1.md)** · **[REPORT_PART2.md](REPORT_PART2.md)**

## Setup (shared)

```bash
# Python 3.13 required for Part 2 (fastembed's onnxruntime has no 3.14/3.15 wheel).
# Part 1 alone runs on 3.10+. Use 3.13 so both parts work.
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY (keys live in .env only)
make test                       # offline test suite — no key or network needed
```

`.env` holds secrets and is gitignored; only `.env.example` is committed. The
code reads `GEMINI_API_KEY` from the environment or `.env` — never from source.
For the local model: `ollama pull qwen3:8b && ollama serve &`.

Every command is discoverable via `python3 main.py --help`.

---

## Part 1 — Extraction

Takes raw security text → **routes** it (structured Ox ASPM parsed in code; team
reports / LinPEAS go to the LLM) → extracts findings into a canonical Pydantic
schema → validates with 1 repair, else marks `failed` → scores against a
hand-labeled golden set. Severity/status/type enums come from a deterministic
code table, not the model.

**Single command:** `python3 main.py` (or `make run`) — full comparison grid
`{gemini, ollama} × {v1, v2, v3} × {deterministic, sampled}`.

- **Models:** Google Gemini `gemini-3.5-flash` (cloud) + Ollama `qwen3:8b`
  (local), behind one `extract(text, model, prompt_version, sampling)` interface.
- **Result:** production choice is Gemini + `v3` + deterministic — 100% valid
  JSON, best recall/precision. Full write-up and the model × prompt × sampling
  table in **REPORT_PART1.md**.

Details: **QUICKSTART_PART1.md** (run/flags), `schema/` (the frozen contract),
`src/README.md` (code map).

---

## Part 2 — RAG

Answers questions over the security corpus (standards, best-practice guides, CVE
advisories, team reports, scanner/alert exports) with cited sources, a context
token budget, and an honest refusal when the answer is not in the documents.

**Single command:** `make evals-ci` — lint the testset → ingest → judged evals +
CI gate. (`python3 main.py --ask "..."` answers a single question.)

- **Stack (local, free):** fastembed `paraphrase-multilingual-MiniLM-L12-v2`
  (384-dim) + Qdrant (in-process) + BM25 + RRF. Answerer routes context into the
  Part-1 Gemini/Ollama adapters.
- **Chunking (justified + measured):** structure-aware for prose (heading-aware
  block packing, 512-tok cap, block overlap; never cuts a table row) + record-as-
  chunk for CSV alerts, compared against a fixed-size baseline. Structure-aware
  wins on both quality metrics — table in REPORT_PART2.md §2.
- **Retrieval (measured):** hybrid (BM25 + dense + RRF) reaches **recall@3 = 1.00**,
  beating vector-only; `doc_type` metadata filter. REPORT_PART2.md §4.
- **Answers:** cite doc + section per claim (citations validated against real
  sources); **"I don't know"** on weak/empty retrieval or ungrounded output.
- **Evals in CI:** 23-question human-written test set (answerable + no-answer +
  `CVE-2026-*` traps); deterministic + **calibrated LLM-judge** (agreement 0.96,
  false_pass 0.00) + faithfulness; `.github/workflows/evals.yml` fails the build
  below baseline. One judged run costs **< $0.05**. REPORT_PART2.md §8.

Details: **QUICKSTART_PART2.md** (run/flags/pricing), `src/rag/README.md` (module
map), `evals/README.md` (eval harness).

---

## Repository layout

```
schema/        Canonical Pydantic schema (frozen Part 1 contract)
prompts/       Versioned prompts + CHANGELOG
                 extract_v1..v3  (Part 1)   rag_answer_v1  (Part 2)
                 judge_v1, faithfulness_v1  (Part 2 evals)
src/           Pipeline code — see src/README.md
  models/        Gemini + Ollama adapters behind one interface
  parsers/       Deterministic parsers for structured sources (ASPM)
  rag/           Part 2: ingest, chunk, embed, index, retrieve, answer — see src/rag/README.md
data/
  raw/           Part 1 inputs — gitignored (sanitized, local-only)
  golden/        Part 1 labeled ground truth (committed)
  corpus/        Part 2 RAG corpus (32 public docs, committed) + manifest + fetch script
  rag/           chunks.jsonl (gitignored, regenerated) + manifest + report
evals/         Part 2 test set, scorers, baseline, results — see evals/README.md
results/        Part 1 run outputs (committed)
tests/         Offline test suite
.github/workflows/evals.yml   Part 2 CI eval gate (Python 3.13)
REPORT_PART1.md / REPORT_PART2.md   measured results per part
QUICKSTART_PART1.md / QUICKSTART_PART2.md   how to run each part
```

## Data & safety

- Secrets live in `.env` only (gitignored); only `.env.example` is committed. No
  keys in source.
- Part 1 raw inputs (`data/raw/`) are sanitized but kept local-only / gitignored.
- The Part 2 corpus (`data/corpus/`, 32 public docs — NIST/CISA public domain,
  OWASP CC BY-SA, NVD) **is** committed for reproducibility; `scripts/fetch_corpus.py`
  re-fetches it as a fallback.
- The system never fabricates values: absent → `null`/`unknown` (Part 1) or an
  honest "I don't know" (Part 2). Source/document text is treated as **data, not
  instructions** (prompt-injection boundary in both parts).

## Scope

Built: Part 1 (Extraction), Part 2 (RAG). Out of scope for now: Part 3 (agent),
Part 4 (production service), plus UI, deploy, and fine-tuning.
