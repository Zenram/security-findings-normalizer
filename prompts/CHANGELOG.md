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
