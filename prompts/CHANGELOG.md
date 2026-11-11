# Prompt Changelog

Every prompt version is a separate file (`extract_vN.md`) and is referenced by
name in every logged result. Never edit a released version in place — add a new
one and record the change here.

## v1 — baseline
- **Goal:** straightforward extraction to the canonical schema.
- **Approach:** describe the schema, give the rules (never fabricate; absent ->
  null/unknown; keep original severity/status wording in the `_raw` fields;
  multiple findings allowed), ask for strict JSON only.
- **Injection safety:** report text wrapped in explicit data boundaries; model
  told to treat it as data, not instructions.

## v2 — few-shot hard-case examples
- **Released.** Base: identical to v1 in schema, rules, and injection boundary.
- **The ONE axis changed vs v1:** added a "Worked examples" section with two
  few-shot hard-case demonstrations — (A) multiple findings in one report that
  must not collapse into one, and (B) a prompt-injection attempt embedded in the
  data that must be ignored. Nothing else was changed (same rules text, same
  schema, same boundary), so any metric delta vs v1 is attributable to the
  few-shot examples alone.
- **Why this axis:** v1 baseline measurements showed the main weakness was
  finding-level RECALL — the model returned one finding per document and missed
  multi-finding cases, plus the cross-source (09) and injection (10) hard cases.
  Few-shot examples target exactly that failure mode.
- **Expected effect:** higher recall on multi-finding docs and a cleaner pass on
  the injection case; watch for any precision drop (spurious findings) or longer
  latency from the larger prompt.

## v3 — explicit enumerate-then-extract procedure
- **Released.** Base: identical to v2 in schema, rules, injection boundary, and
  the two v2 few-shot examples (A multi-finding, B injection). All of that is
  carried over unchanged.
- **The ONE axis changed vs v2:** added an "Extraction procedure" section that
  forces a two-phase method — (1) scan the whole document, (2) ENUMERATE every
  distinct root cause internally, (3) DEDUPLICATE/GROUP per Rules 4–5/7,
  (4) EMIT one object per surviving item, (5) SELF-CHECK that array length ==
  enumerated count. The reasoning is explicitly internal — visible output stays
  JSON-only (Rule 8). A third few-shot example (C) was added to anchor the
  hardest measured case: the same check reported as two tickets = two findings,
  while a header "candidate CVE overlap" list is NOT a finding. Nothing else
  changed, so any metric delta vs v2 is attributable to the enumerate-then-
  extract procedure (+ its anchoring example) alone.
- **Why this axis:** the v1/v2 measurements (REPORT §3–5) showed the dominant
  error is finding-level RECALL, and v2's few-shot examples did NOT move it
  (Gemini P/R unchanged 50%/52%; qwen collapses every multi-finding doc to ONE
  finding -> 26% recall). The two concrete failures were qwen single-finding
  collapse and Gemini under-split on entry 02 (2 command-injection tickets
  merged to 1). REPORT §7 names the fix directly: "prompt it to enumerate
  findings one at a time". v3 implements exactly that, plus a precision guard
  against the LinPEAS "candidate CVE overlap" spurious-finding pattern (§5.3).
- **Expected effect:** higher recall on multi-finding docs (qwen should stop
  collapsing; Gemini should stop under-splitting entry 02) with precision held
  or improved by the explicit grouping/negative-line guards. Watch for: longer
  latency and token cost from the larger prompt, and any over-splitting (recall
  up but precision down) from the enumerate step being too eager — the
  DEDUPLICATE/GROUP step and Example C are there to counter that.

---

# RAG answerer prompts (Part 2, Step 3)

Separate prompt family from extraction: `rag_answer_vN.md`, loaded via
`src/prompts.render_rag_prompt`. Two placeholders injected as data inside
explicit boundaries: `{sources}` (numbered retrieved chunks) and `{question}`.
Referenced by name in every logged answer (`RagAnswer.prompt_version`).

## rag_answer_v1 — baseline cited answerer
- **Goal:** answer a question using ONLY the retrieved sources, cite doc +
  section per claim, and refuse honestly when the answer is not in the sources.
- **Approach:** numbered sources `[S1]..[Sn]`; strict JSON output
  `{found, answer, citations}`; rules forbidding outside knowledge, invented
  citations, and guessing; an explicit "I don't know / not in the documents"
  path (`found=false`, empty citations).
- **Injection safety:** sources wrapped in `<sources>` boundaries and declared
  untrusted data — the model is told not to obey instructions embedded in source
  text (carries the Part-1 data-not-instructions boundary into RAG).
- **Enforced in code (`src/rag/answer.py`), not just asked for:** citations are
  validated against the real source labels (invented labels dropped); a `found`
  answer with no valid citation is downgraded to not-found; empty/unparseable
  output becomes an honest refusal; context is assembled under a token budget.

---

# Eval prompts (Part 2, Step 4)

Loaded via `src/prompts.render_named_prompt`. Used by `evals/scorers.py`, not by
the answerer. Fields injected as data by explicit-token replacement.

## judge_v1 — LLM-as-judge (correctness)
- **Goal:** meaning-level grade of an answer vs a hand-written reference —
  `correct` / `incorrect` with a one-sentence reason.
- **Key rule:** for no-answer/trap references, an answer is `correct` only if it
  also abstains; fabricating facts for such a question is `incorrect`.
- **Calibrated:** run against 23 hand labels (`evals/labels.jsonl`) →
  agreement 0.96, false_pass 0.00, false_fail 0.04. A false_pass of 0 means the
  judge never credited a wrong answer, so metrics built on it are not inflated.

## faithfulness_v1 — groundedness check
- **Goal:** decompose an answer into claims and mark each supported / not by the
  sources; catches answers that add facts beyond the retrieved context.
- **Status:** DIAGNOSTIC only, **excluded from the CI gate.** The current prompt
  marks paraphrased summary sentences as unsupported even when the content is in
  the cited context (verified manually), so it under-reports faithfulness. A
  stronger version (cross-chunk claim crediting) is future work. A miscalibrated
  metric must not gate the build.
