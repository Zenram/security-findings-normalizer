"""
D2 — evaluation harness. Two layers, never scored by position.

1. MATCH predicted findings to expected findings by a stable key:
   - source_record_id if both present and equal, else
   - CVE-overlap + asset overlap, else
   - fuzzy similarity on (title + assets + finding_type).
   Greedy best-match assignment; each prediction/expected used at most once.
2. CLASSIFY each pair as matched / missed (expected, unpredicted) /
   spurious (predicted, unexpected).
3. FINDING-LEVEL precision & recall over the set.
4. FIELD-LEVEL per-field accuracy computed ONLY over matched pairs.
   Exact match for enums / CVE / IDs; fuzzy for free text; set compare for
   lists; null==null counts as correct.

Aggregate metrics per (model x prompt x sampling) run: % valid JSON,
hallucination rate, latency p50/p95, cost per 1000 docs. Local cost is reported
with a transparent methodology, never a fabricated provider price (CAPSTONE_PLAN
Stage 2 metrics + Open Questions).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

# Fields scored at the field level (over matched pairs). Grouped by comparison
# style so the accuracy computation stays explicit.
_EXACT_FIELDS = ["source", "source_record_id", "finding_type", "severity", "status", "team"]
_RAW_TEXT_FIELDS = ["title", "description", "severity_raw", "status_raw", "evidence", "extraction_notes"]
_LIST_FIELDS = ["cve_ids"]  # order-insensitive set compare
_ASSET_FIELD = "affected_assets"

ALL_SCORED_FIELDS = _EXACT_FIELDS + _RAW_TEXT_FIELDS + _LIST_FIELDS + [_ASSET_FIELD]

_FUZZY_THRESHOLD = 0.60  # free-text considered "correct" at/above this ratio
_MATCH_THRESHOLD = 0.45  # minimum similarity to accept a finding match


# --- similarity helpers ------------------------------------------------------

def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _ratio(a: Optional[str], b: Optional[str]) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _cve_set(finding: dict) -> set[str]:
    return {c.strip().upper() for c in (finding.get("cve_ids") or []) if c}


def _asset_tokens(finding: dict) -> set[str]:
    tokens: set[str] = set()
    for asset in finding.get(_ASSET_FIELD) or []:
        for key in ("asset", "repository", "environment"):
            val = _norm(asset.get(key))
            if val:
                tokens.add(val)
    return tokens


def match_score(pred: dict, exp: dict) -> float:
    """Similarity in [0,1] used to align a predicted finding to an expected one.

    Strong signals (shared record id, CVE overlap) boost the score; otherwise we
    fall back to fuzzy title/type/asset similarity. Never uses list position.
    """
    # Strong key: same source_record_id.
    pid, eid = pred.get("source_record_id"), exp.get("source_record_id")
    if pid and eid and _norm(pid) == _norm(eid):
        return 1.0

    score = 0.0
    # CVE overlap.
    pcve, ecve = _cve_set(pred), _cve_set(exp)
    if pcve and ecve and (pcve & ecve):
        score += 0.4
    # Asset token overlap.
    pa, ea = _asset_tokens(pred), _asset_tokens(exp)
    if pa and ea and (pa & ea):
        score += 0.2
    # finding_type agreement.
    if _norm(pred.get("finding_type")) == _norm(exp.get("finding_type")):
        score += 0.15
    # Title similarity (always contributes).
    score += 0.25 * _ratio(pred.get("title"), exp.get("title"))
    return min(score, 1.0)


# --- matching ----------------------------------------------------------------

@dataclass
class MatchPair:
    pred_index: int
    exp_index: int
    score: float


@dataclass
class MatchResult:
    pairs: list[MatchPair] = field(default_factory=list)   # matched
    missed_exp: list[int] = field(default_factory=list)    # expected, not matched
    spurious_pred: list[int] = field(default_factory=list)  # predicted, not matched


def match_findings(preds: list[dict], exps: list[dict]) -> MatchResult:
    """Greedy best-first matching between predicted and expected findings."""
    candidates: list[MatchPair] = []
    for pi, pred in enumerate(preds):
        for ei, exp in enumerate(exps):
            s = match_score(pred, exp)
            if s >= _MATCH_THRESHOLD:
                candidates.append(MatchPair(pi, ei, s))
    candidates.sort(key=lambda p: p.score, reverse=True)

    used_pred: set[int] = set()
    used_exp: set[int] = set()
    result = MatchResult()
    for cand in candidates:
        if cand.pred_index in used_pred or cand.exp_index in used_exp:
            continue
        used_pred.add(cand.pred_index)
        used_exp.add(cand.exp_index)
        result.pairs.append(cand)

    result.missed_exp = [i for i in range(len(exps)) if i not in used_exp]
    result.spurious_pred = [i for i in range(len(preds)) if i not in used_pred]
    return result


# --- field-level scoring (matched pairs only) --------------------------------

def _field_correct(field_name: str, pred: dict, exp: dict) -> bool:
    pv, ev = pred.get(field_name), exp.get(field_name)

    if field_name in _EXACT_FIELDS:
        return _norm(pv) == _norm(ev) if (pv is not None or ev is not None) else True

    if field_name in _RAW_TEXT_FIELDS:
        if not pv and not ev:
            return True  # null == null
        if bool(pv) != bool(ev):
            return False  # one side null, other not
        return _ratio(pv, ev) >= _FUZZY_THRESHOLD

    if field_name in _LIST_FIELDS:  # cve_ids: exact set match
        return _cve_set(pred) == _cve_set(exp)

    if field_name == _ASSET_FIELD:
        # Correct if asset-token sets match (order-insensitive); both empty = ok.
        pa, ea = _asset_tokens(pred), _asset_tokens(exp)
        return pa == ea

    return _norm(pv) == _norm(ev)


@dataclass
class FieldAccumulator:
    """Per-field correct/total counters across all matched pairs in a run."""

    correct: dict[str, int] = field(default_factory=lambda: {f: 0 for f in ALL_SCORED_FIELDS})
    total: dict[str, int] = field(default_factory=lambda: {f: 0 for f in ALL_SCORED_FIELDS})

    def add_pair(self, pred: dict, exp: dict) -> None:
        for fname in ALL_SCORED_FIELDS:
            self.total[fname] += 1
            if _field_correct(fname, pred, exp):
                self.correct[fname] += 1

    def accuracy(self) -> dict[str, Optional[float]]:
        return {
            f: (self.correct[f] / self.total[f] if self.total[f] else None)
            for f in ALL_SCORED_FIELDS
        }

    def overall(self) -> Optional[float]:
        tot = sum(self.total.values())
        cor = sum(self.correct.values())
        return (cor / tot) if tot else None


# --- hallucination -----------------------------------------------------------

def count_hallucinated_fields(pred: dict, exp: dict) -> tuple[int, int]:
    """Count fields the model INVENTED: predicted non-null where expected is
    null/empty, for fields where a value must come from the source.

    Returns (hallucinated, considered). Used to compute a hallucination rate.
    """
    considered = 0
    hallucinated = 0
    invent_sensitive = ["team", "source_record_id", "severity_raw", "status_raw"]
    for fname in invent_sensitive:
        considered += 1
        ev = exp.get(fname)
        pv = pred.get(fname)
        if (ev is None or ev == "") and pv not in (None, ""):
            hallucinated += 1
    # CVEs invented (predicted CVEs absent from expected).
    considered += 1
    if _cve_set(pred) - _cve_set(exp):
        hallucinated += 1
    return hallucinated, considered


# --- top-level run evaluation ------------------------------------------------

@dataclass
class RunMetrics:
    model: str
    prompt_version: str
    sampling_name: str

    documents: int = 0
    valid_json: int = 0          # results with status ok (post-retry)
    failed: int = 0
    repaired: int = 0

    matched: int = 0
    missed: int = 0
    spurious: int = 0

    hallucinated_fields: int = 0
    considered_fields: int = 0

    latencies: list[float] = field(default_factory=list)
    output_tokens: list[int] = field(default_factory=list)
    input_tokens: list[int] = field(default_factory=list)

    field_acc: FieldAccumulator = field(default_factory=FieldAccumulator)

    # --- derived metrics ---
    @property
    def pct_valid_json(self) -> Optional[float]:
        return (self.valid_json / self.documents) if self.documents else None

    @property
    def finding_precision(self) -> Optional[float]:
        denom = self.matched + self.spurious
        return (self.matched / denom) if denom else None

    @property
    def finding_recall(self) -> Optional[float]:
        denom = self.matched + self.missed
        return (self.matched / denom) if denom else None

    @property
    def hallucination_rate(self) -> Optional[float]:
        return (self.hallucinated_fields / self.considered_fields) if self.considered_fields else None

    def latency_percentile(self, p: float) -> Optional[float]:
        if not self.latencies:
            return None
        data = sorted(self.latencies)
        k = (len(data) - 1) * p
        f = int(k)
        c = min(f + 1, len(data) - 1)
        if f == c:
            return data[f]
        return data[f] + (data[c] - data[f]) * (k - f)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "sampling": self.sampling_name,
            "documents": self.documents,
            "pct_valid_json": self.pct_valid_json,
            "failed": self.failed,
            "repaired": self.repaired,
            "finding_precision": self.finding_precision,
            "finding_recall": self.finding_recall,
            "matched": self.matched,
            "missed": self.missed,
            "spurious": self.spurious,
            "overall_field_accuracy": self.field_acc.overall(),
            "field_accuracy": self.field_acc.accuracy(),
            "hallucination_rate": self.hallucination_rate,
            "latency_p50": self.latency_percentile(0.50),
            "latency_p95": self.latency_percentile(0.95),
            "latencies_measured": len(self.latencies),
            "avg_output_tokens": (statistics.mean(self.output_tokens) if self.output_tokens else None),
            "avg_input_tokens": (statistics.mean(self.input_tokens) if self.input_tokens else None),
        }


def evaluate_result(metrics: RunMetrics, result: dict, expected: list[dict]) -> None:
    """Fold one extraction result (as dict) + its expected findings into metrics."""
    metrics.documents += 1

    if result.get("latency_seconds") is not None:
        metrics.latencies.append(result["latency_seconds"])
    if result.get("output_tokens") is not None:
        metrics.output_tokens.append(result["output_tokens"])
    if result.get("input_tokens") is not None:
        metrics.input_tokens.append(result["input_tokens"])

    if result.get("status") != "ok":
        metrics.failed += 1
        # A failed doc still counts as missed findings for recall honesty.
        metrics.missed += len(expected)
        return

    metrics.valid_json += 1
    if result.get("repaired"):
        metrics.repaired += 1

    preds = result.get("findings") or []
    mr = match_findings(preds, expected)
    metrics.matched += len(mr.pairs)
    metrics.missed += len(mr.missed_exp)
    metrics.spurious += len(mr.spurious_pred)

    for pair in mr.pairs:
        pred = preds[pair.pred_index]
        exp = expected[pair.exp_index]
        metrics.field_acc.add_pair(pred, exp)
        h, c = count_hallucinated_fields(pred, exp)
        metrics.hallucinated_fields += h
        metrics.considered_fields += c
