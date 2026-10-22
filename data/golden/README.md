# Golden Set — labeled ground truth

This is the measurement baseline for extraction quality. Each entry is a **pair**:

- `NN_input.<ext>` — the raw input text given to the extractor (copied from the
  corresponding `data/raw/...` source so the golden set is self-contained).
- `NN_expected.json` — the **hand-labeled correct output**: a JSON array of
  `Finding` objects (matching `schema/finding.py`) that a human decided is correct.

The evaluation harness runs each model on `NN_input` and scores its output
against `NN_expected`.

## What the golden set is FOR (plain-language)

The golden set is a **measuring instrument, not training data and not product
output.** The models are never fine-tuned on it — it is used purely to *evaluate*.

Its one job: tell you **which model + prompt + sampling config to trust** on the
real, unlabeled data (`data/raw/`, run via `--corpus`). You label 10
representative hard cases once, score every model/config against them, and the
winner is the config you then apply to the 28 corpus texts (and all future
files) — which you never have to label, because the golden set already proved
which config is reliable.

Think of it as a taste test with 10 dishes where you already know the correct
recipe: you're not teaching the chefs, you're deciding which chef to hire. The
hire then cooks everything else.

Consequence: the answer is only as good as the golden set is *representative*.
10 examples covering the hard cases give a **directional** answer, not a
statistically tight one. Grow the golden set as new edge cases appear.

## How scoring works (important — see CAPSTONE_PLAN D2)

A text can contain several findings; the model may return a different count or
order. **Do not compare by position.** The harness must:

1. **Match** predicted findings to expected findings by a stable key:
   `source_record_id` or `cve_ids`+asset where present; else fuzzy match on
   `title` + `affected_assets` + `finding_type`.
2. Classify each as **matched** / **missed** (expected, not predicted) /
   **spurious** (predicted, not expected).
3. **Finding-level:** report precision & recall over the set.
4. **Field-level:** compute per-field accuracy **only over matched pairs**.
   Exact match for enums / CVE / IDs; fuzzy for free text + lists; explicit
   rules for dates and missing values (null == null is a correct match).

Missed/spurious findings are reported separately — never folded into field
accuracy.

## Normalization (see CAPSTONE_PLAN D4)

`severity` / `status` enums come from a **code-side mapping table**, not the
model. The model fills `severity_raw` / `status_raw` with the original wording.
In the expected JSON both are filled: the raw string as it appears in source,
and the normalized enum the table should produce.

**Dual-severity rule (settled):** when a source has two severity columns
(e.g. Ox `Severity` vs `Original Severity`), `severity_raw` takes the surfaced
`Severity` value; the other is noted in `extraction_notes`.

## Finding granularity (see CAPSTONE_PLAN D5)

One finding per (root cause + distinct asset context). One check failing on many
assets, reported as one issue = one finding with many `affected_assets`
(Trivy DS-0002 across Dockerfiles). Separate records / different asset context =
separate findings (devops repo A vs repo B). Never inflate finding count by
instance/alert count; record the count in `extraction_notes`.

## Team inference (settled)

Infer `team` whenever the source carries an app reference `*_app_N` — including
a cross-source association note (e.g. Trivy `RelatedASPMApplication`) — else
`null`; never guess from unrelated text, and an explicit "team missing" in the
source always wins (stays `null`). Corpus convention: the Ox `Application`
column is `Team / app`, so `data_app_* -> Data`, `dev_app_* -> Dev`,
`devops_app_* -> DevOps`. Examples: LinPEAS `Related ASPM app: data_app_2` ->
Data; Trivy `RelatedASPMApplication: data_app_4` -> Data; `app: unknown`
(entry 04) -> `null`. Record the inference source in `extraction_notes`.

## Entry manifest (10) — hard-case coverage

| NN | Source | Hard case(s) exercised |
|----|--------|------------------------|
| 01 | team report (dev, Sep 14) | multiple findings in one text; missing team/repo (unknown); accept-risk status; "don't say fixed" |
| 02 | team report (devops, Sep 10) | finding-count vs root-cause-count split; multiple call sites; low exploitability context |
| 03 | team report (data, Oct 14) | expanded instance count != new issue; closed finding excluded from live count; mixed severity reasoning |
| 04 | LinPEAS (ubuntu 24.04) | noisy unstructured; CVE-overlap header; "CVE refs alone != vulnerable"; cross-source to Ox apps |
| 05 | LinPEAS (rocky 8.9) | noisy; privesc findings; missing asset ownership (unknown) |
| 06 | Ox ASPM CSV row (CSRF) | structured parse; dual severity (High vs Medium Original); CWE; status open |
| 07 | Ox ASPM CSV row (alpine base image) | MANY CVEs in one finding (cve_ids list); dual severity (High vs Critical) |
| 08 | Trivy JSON (data_repo_3) | structured parser path; multiple findings; same DS-0002 across many Dockerfiles (same issue, many targets) |
| 09 | cross-source overlap (LinPEAS + Ox) | SAME ISSUE FROM MULTIPLE TOOLS — must NOT be auto-merged; both kept, flagged related |
| 10 | injection test (synthetic) | prompt-injection: input tries to change behavior; expected output IGNORES it |

> Entries 01-08 are labeled against real sanitized source files. Entry 09 is an
> overlap pairing drawn from real files. Entry 10 is clearly-labeled synthetic
> adversarial input. Synthetic/adversarial entries say so inside the file.

## Status of this folder

All 10 pairs exist and every `_expected.json` is valid JSON. Granularity (D5)
and dual-severity (D4) rules are applied consistently across the labeled
entries. Labeling status:

- **Fully labeled against real source:** 01, 02, 03, 04, 05, 06, 07, 08, 09, 10.

Review these as **labeling decisions**, not just inputs. If a label looks wrong,
that is a finding about the golden set, not the model. Entries 03 and 09 note an
optional extra record each if you want maximum coverage.
