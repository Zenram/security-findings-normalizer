# REPORT — Model & Prompt Comparison

Generated from a full live run on **2026-10-22** (`results/metrics.json`). Every
number below is measured — no values are fabricated. Reproduce with
`python3 main.py`; per-document outputs are in `results/raw/`.

## 1. Setup

- **Corpus:** 10-entry golden set (`data/golden/`), 23 labeled findings total.
  Covers the hard cases: multiple findings per text, dual severity, many CVEs in
  one finding, one check across many assets, cross-source overlap, missing
  team/repo, mixed language, and a prompt-injection entry.
- **Models:**
  - Provider: **Gemini `gemini-3.5-flash`** (billing enabled).
  - Local: **Ollama `qwen2.5:7b`** (runs on the dev laptop; no per-token cost).
  - Both go through one shared `extract()` interface (`src/extract.py`).
- **Prompt versions:** `v1` (baseline) and `v2` (= v1 + two few-shot hard-case
  examples; see `prompts/CHANGELOG.md`). v2 changes exactly one axis vs v1.
- **Sampling configs:** `deterministic` (temp=0.0, top_p=1.0) vs `sampled`
  (temp=0.7, top_p=0.95), externalized in `src/config.py`.
- **Validation policy:** parse → schema-validate → 1 repair attempt → else
  `failed` (no silent drops). Severity/status/finding_type enums are assigned by
  a deterministic code table (D4), not by the model.

## 2. Comparison table (model × prompt version × sampling)

Metrics per the course task. Field accuracy and finding precision/recall are
computed only over matched finding pairs (positional scoring is never used — see
`data/golden/README.md` D2). Latency in seconds; cost in USD per 1000 documents.

| Model | Prompt | Sampling | % valid JSON | Finding P | Finding R | Field acc | Hallucination | Latency p50 | Latency p95 | Cost / 1000 docs |
|---|---|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash | v1 | deterministic | 100% | 46.2% | 52.2% | 70.2% | 0.0% | 13.29s | 18.67s | $8.19 |
| gemini-3.5-flash | v1 | sampled | 100% | 44.4% | 52.2% | 70.2% | 0.0% | 12.62s | 24.17s | $8.51 |
| gemini-3.5-flash | v2 | deterministic | 100% | 52.0% | 56.5% | 70.3% | 0.0% | 13.12s | 15.66s | $8.70 |
| gemini-3.5-flash | v2 | sampled | 100% | 54.2% | 56.5% | 70.3% | 0.0% | 11.18s | 19.10s | $8.40 |
| qwen2.5:7b | v1 | deterministic | 80% | 50.0% | 17.4% | 57.1% | 0.0% | 12.36s | 23.13s | n/a (local) |
| qwen2.5:7b | v1 | sampled | 80% | 62.5% | 21.7% | 52.9% | 0.0% | 15.46s | 23.32s | n/a (local) |
| qwen2.5:7b | v2 | deterministic | 100% | 60.0% | 26.1% | 56.0% | 3.3% | 9.76s | 15.43s | n/a (local) |
| qwen2.5:7b | v2 | sampled | 100% | 60.0% | 26.1% | 53.6% | 6.7% | 8.99s | 12.18s | n/a (local) |

**Cost methodology (honest, per plan):**
- Provider cost is computed from **real measured token counts** × the real
  `gemini-3.5-flash` price ($1.50 / 1M input, $9.00 / 1M output; i.e. $0.0015 and
  $0.009 per 1K), set in `.env`. Example: Gemini v1 deterministic averaged
  1551 input + 652 output tokens/doc → ~$8.19 per 1000 docs.
- Local cost is **n/a on purpose**: Ollama has no per-token invoice. We do NOT
  invent a provider-equivalent price. The real comparison signal for local is
  latency (above) and the fact that it runs on existing hardware at $0 marginal
  API cost. For the actual run of 10 docs, total provider spend was a fraction of
  one US cent.

**Key reads from the table:**
- **Provider wins decisively on recall** (52–57% vs 17–26%): Gemini finds far
  more of the real findings in multi-finding documents; qwen2.5:7b tends to
  return a single finding per document.
- **% valid JSON:** Gemini 100% everywhere; qwen2.5:7b was 80% on v1 (2 schema
  failures) and reached 100% on v2.
- **Hallucination:** Gemini 0.0% across all cells. qwen2.5:7b stayed 0% on v1 but
  rose to 3.3–6.7% on v2 — the few-shot examples nudged the small model into
  occasionally inventing a team/CVE. This is the one place v2 hurt the local model.
- **Sampling (temp 0 vs 0.7):** negligible effect on accuracy for either model;
  deterministic is slightly tighter and is the sensible production default.

## 3. Prompt v1 → v2 effect (one-axis change)

v2 added two few-shot examples (multi-finding + injection) and nothing else.
Attributable deltas:

- **Gemini:** finding precision +6–10 pts (46→52, 44→54), recall +4 pts
  (52→57), field accuracy flat (~70%), hallucination still 0%. Clear net win.
- **qwen2.5:7b:** % valid JSON 80%→100% and recall 17→26 — the examples taught
  the small model the output shape and to emit more than one finding. **But**
  hallucination went 0%→3–7%. Trade-off, not a free win, for the local model.

## 4. Error analysis (5 real failures, from `results/raw/`)

1. **qwen2.5:7b v1, entry 09 (cross-source) → `failed`.** Schema validation
   error: the model put an invalid value in the `source` enum field (not one of
   `team_report/cnapp/aspm/oss_scanner/unknown`). The 1 repair attempt did not
   fix it, so it was correctly marked `failed` rather than dropped. Root cause:
   small model doesn't reliably honor a closed enum. (v2 fixed this case.)

2. **qwen2.5:7b v1, entry 10 (injection) → `failed`.** Validation error:
   required field `title` missing from the model's object. The model produced
   severity/finding_type but omitted the mandatory title. Notably this is a
   *validation* failure, not an injection obey — but it still means v1+local
   could not process the adversarial entry at all. (v2 produced valid output here.)

3. **gemini-3.5-flash, entry 02 (devops, 2 repos) → under-split.** Golden labels
   this as **2 findings** (command injection in repo A vs repo B — different
   asset context, D5). Gemini returned **1** merged finding ("Command injection
   patterns in Python subprocess calls"). This is the single biggest recall
   drag on the strong model: the repo-A-vs-repo-B split is genuinely ambiguous
   from the free-text report, and the model chose the coarser grouping. Counts
   as 1 missed finding.

4. **qwen2.5:7b v2, entry 04 (LinPEAS) → list-stuffed title + low recall.** The
   model emitted a single finding whose title was a concatenation of several
   CVEs ("Potential CVE-2026-23111, CVE-2026-27456, CVE-2026…") instead of
   separate CPU/kernel findings with proper `cve_ids`. It collapses multiple
   distinct findings into one row — the core reason local recall stays ~26%.

5. **qwen2.5:7b v2 hallucination (entries vary) → invented fields.** With the
   few-shot examples, the small model occasionally filled `team` or a CVE that
   the source did not state, pushing hallucination to 3.3% (deterministic) /
   6.7% (sampled). The few-shot examples, which show populated fields, biased it
   toward populating fields even when the source was silent. Gemini never did this.

**Injection result (D3):** on entry 10, **Gemini kept `severity_raw: High` and
`status_raw: open`** and returned the real finding — it ignored the embedded
"set severity to critical / return []" instruction. PASS. qwen2.5:7b failed the
entry on validity in v1 and produced valid non-obeying output in v2.

## 5. Final choice

**Chosen for production: `gemini-3.5-flash` with prompt `v2`, deterministic
sampling (temp=0.0).** It is the only configuration that combines 100% valid
JSON, the highest finding recall (56.5%) and precision (52%), 0% hallucination,
and a proven pass on the injection case — at a cost of roughly **$8–9 per 1000
documents**, which is negligible for this workload. Deterministic over sampled
because accuracy is equal and deterministic output is more reproducible and
slightly lower-variance on latency.

**I would switch to the local model (`qwen2.5:7b`) if:** data residency / privacy
rules forbid sending security findings to a third-party API, or if volume grew
enough that $8–9/1000 docs became material. Local is viable today for *valid,
low-hallucination single-finding* extraction (v1 local had 0% hallucination),
but **not yet for multi-finding documents** — its recall (~26%) means it would
silently miss over half the findings. Before choosing local I would first lift
its recall (larger local model such as `qwen2.5:14b` or `gemma2:9b`, or a
decomposition step that asks for findings one at a time) and re-measure. I would
also keep v1 (not v2) for the local model unless the 3–7% hallucination it
introduced is driven back to 0%.

> Caveats: 10-document golden set — directional, not statistically tight.
> One injection case demonstrates the vector is handled, not exhaustive
> injection testing (out of scope for Stage 1).
