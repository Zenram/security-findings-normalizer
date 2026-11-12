"""Scorers for the Part 2 Step 4 eval harness.

Three layers, cheapest first:

1. DETERMINISTIC (free, no model) — on one RagAnswer vs its test case:
     - source_cited : an expected source document is among the cited sources
     - facts_present: every `must` group has at least one option in the answer
     - abstained    : for no_answer/trap cases, the system said "I don't know"
     - passed       : facts_present AND source_cited (answerable) / abstained (no_answer+trap)

2. LLM-AS-JUDGE (paid, calibrated) — meaning-level correctness via `judge_v1`,
   compared against hand labels (`evals/labels.jsonl`) to report agreement %.

3. FAITHFULNESS (paid) — every claim in the answer supported by the cited
   sources (`faithfulness_v1`); catches answers that add facts beyond the sources.

Judge + faithfulness route through the existing Gemini adapter (same key/pacing
as Part 1), so there is one provider and one cost model. Deterministic scorers
need no key and run in CI for free.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.config import REQUEST_TIMEOUT_SECONDS, SAMPLING_CONFIGS
from src.models import get_adapter
from src.models.base import ModelError
from src.prompts import render_named_prompt

NO_ANSWER_KINDS = {"no_answer", "trap"}
JUDGE_PROMPT = "judge_v1"
FAITHFULNESS_PROMPT = "faithfulness_v1"


def _norm(text: str) -> str:
    text = text.lower().replace("\u2212", "-").replace("\u2013", "-").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


# --- 1. deterministic --------------------------------------------------------

@dataclass
class DetScore:
    source_cited: bool | None       # None when not applicable (no_answer/trap)
    facts_present: bool | None
    abstained: bool | None          # None when not applicable (answerable)
    passed: bool

    def as_dict(self) -> dict:
        return {"source_cited": self.source_cited, "facts_present": self.facts_present,
                "abstained": self.abstained, "passed": self.passed}


def score_deterministic(answer: dict, case: dict) -> DetScore:
    """Score one answer (RagAnswer.as_dict()) against its test case, no model."""
    kind = case["kind"]
    ans_text = _norm(answer.get("answer", ""))
    found = bool(answer.get("found", False))

    if kind in NO_ANSWER_KINDS:
        # Correct behavior is to abstain: found == False.
        abstained = not found
        return DetScore(source_cited=None, facts_present=None,
                        abstained=abstained, passed=abstained)

    # answerable: need the right source cited AND the key facts present.
    cited_sources = {s["source"] for s in answer.get("cited_sources", [])}
    expected = set(case.get("expected_sources", []))
    source_cited = bool(cited_sources & expected) if expected else None

    must_groups = case.get("must", [])
    if must_groups:
        facts_present = all(
            any(_norm(opt) in ans_text for opt in group) for group in must_groups
        )
    else:
        facts_present = None

    passed = found and (source_cited is not False) and (facts_present is not False)
    # Require a positive signal so a vacuous all-None answer does not pass.
    if source_cited is None and facts_present is None:
        passed = found
    return DetScore(source_cited=source_cited, facts_present=facts_present,
                    abstained=None, passed=bool(passed))


# --- shared tiny model-call helper ------------------------------------------

def _call_json(adapter, prompt: str, timeout: int) -> dict | None:
    try:
        resp = adapter.generate(prompt, SAMPLING_CONFIGS["deterministic"], timeout)
    except ModelError:
        return None
    text = resp.text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


# --- 2. LLM-as-judge ---------------------------------------------------------

class Judge:
    """Meaning-level correctness grader (calibrated against human labels)."""

    def __init__(self, model: str = "gemini", prompt: str = JUDGE_PROMPT,
                 timeout: int = REQUEST_TIMEOUT_SECONDS):
        self.prompt = prompt
        self.timeout = timeout
        self._adapter = get_adapter(model)

    def verdict(self, question: str, reference: str, answer: str) -> bool | None:
        """True if the judge says correct, False if incorrect, None on failure."""
        rendered = render_named_prompt(self.prompt, question=question,
                                       reference=reference, answer=answer)
        data = _call_json(self._adapter, rendered, self.timeout)
        if not data or "verdict" not in data:
            return None
        return str(data["verdict"]).strip().lower() == "correct"


# --- 3. faithfulness ---------------------------------------------------------

class Faithfulness:
    """Every claim in the answer must be supported by the cited sources."""

    def __init__(self, model: str = "gemini", prompt: str = FAITHFULNESS_PROMPT,
                 timeout: int = REQUEST_TIMEOUT_SECONDS):
        self.prompt = prompt
        self.timeout = timeout
        self._adapter = get_adapter(model)

    def check(self, answer_text: str, found: bool, source_texts: list[str]
              ) -> tuple[bool | None, list[str]]:
        """Return (all_supported, unsupported_claims). (None, []) when there is
        nothing to check (abstained answer or no cited sources)."""
        if not found or not source_texts:
            return None, []
        sources = "\n\n".join(source_texts)
        rendered = render_named_prompt(self.prompt, sources=sources, answer=answer_text)
        data = _call_json(self._adapter, rendered, self.timeout)
        if not data or "claims" not in data:
            return None, []
        claims = data["claims"] or []
        unsupported = [c.get("claim", "") for c in claims if not c.get("supported", False)]
        all_supported = len(unsupported) == 0 and len(claims) > 0
        return all_supported, unsupported


# --- calibration -------------------------------------------------------------

def calibrate(judge_flags: list[bool], human_flags: list[bool], ids: list[str]) -> dict:
    """Agreement between judge and human labels. false_pass = judge said correct
    but human said wrong; false_fail = the opposite."""
    n = len(human_flags)
    if n == 0:
        return {"agreement": None, "false_pass": None, "false_fail": None, "disagreements": []}
    agree = sum(1 for j, h in zip(judge_flags, human_flags) if j == h) / n
    false_pass = sum(1 for j, h in zip(judge_flags, human_flags) if j and not h) / n
    false_fail = sum(1 for j, h in zip(judge_flags, human_flags) if (not j) and h) / n
    disagreements = [i for i, (j, h) in zip(ids, zip(judge_flags, human_flags)) if j != h]
    return {"agreement": round(agree, 3), "false_pass": round(false_pass, 3),
            "false_fail": round(false_fail, 3), "disagreements": disagreements}
