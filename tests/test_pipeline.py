"""
Offline pipeline + evaluator tests using a FAKE adapter — no live model, no
network, no fabricated metrics (the adapter returns canned text we control).

Covers:
- extract() happy path: raw model JSON -> normalized, schema-valid findings.
- severity/status enums assigned by the D4 code table from *_raw (not the model).
- the 1-repair-then-ok path and the 1-repair-then-failed path.
- injection case: model that returns the correct finding is scored as a match.
- D2 matching: matched / missed / spurious classification and field accuracy.
"""

import json

from src.config import SAMPLING_CONFIGS
from src.evaluate import RunMetrics, evaluate_result, match_findings
from src.extract import extract
from src.models.base import ModelAdapter, ModelResponse


class FakeAdapter(ModelAdapter):
    """Returns pre-scripted responses in order; records prompts it received."""

    model_id = "fake"
    model_name = "fake-model"

    def __init__(self, scripted_texts):
        self._texts = list(scripted_texts)
        self.prompts_seen = []

    def generate(self, prompt, sampling, timeout):
        self.prompts_seen.append(prompt)
        text = self._texts.pop(0) if self._texts else "[]"
        return ModelResponse(text=text, latency_seconds=0.01,
                             input_tokens=100, output_tokens=50)


SAMPLING = SAMPLING_CONFIGS["deterministic"]


def _model_finding(**over):
    base = {
        "source": "team_report",
        "source_record_id": None,
        "raw_reference": "10_input.txt",
        "title": "SQL injection in reporting export endpoint",
        "description": "user sort param concatenated into raw query",
        "finding_type": "sql_injection",
        "severity_raw": "High",   # model supplies RAW only
        "status_raw": "open, no fix branch yet",
        "cve_ids": [],
        "affected_assets": [{"asset": "reporting export endpoint", "repository": "billing_app_2"}],
        "team": "Dev",
        "evidence": "SQL injection in the reporting export endpoint",
        "extraction_notes": None,
    }
    base.update(over)
    return base


def test_extract_happy_path_applies_code_table_normalization():
    adapter = FakeAdapter([json.dumps([_model_finding()])])
    result = extract("irrelevant text", model="fake", prompt_version="v1",
                     sampling=SAMPLING, source_id="10", adapter=adapter)
    assert result.status == "ok"
    assert not result.repaired
    assert len(result.findings) == 1
    f = result.findings[0]
    # Enums assigned by the D4 table from the raw wording, not by the model:
    assert f["severity"] == "high"
    assert f["status"] == "open"
    assert f["finding_type"] == "sql_injection"
    assert f["severity_raw"] == "High"


def test_extract_repair_then_ok():
    bad = "not json at all"
    good = json.dumps([_model_finding()])
    adapter = FakeAdapter([bad, good])
    result = extract("x", model="fake", prompt_version="v1",
                     sampling=SAMPLING, source_id="10", adapter=adapter)
    assert result.status == "ok"
    assert result.repaired is True
    assert len(adapter.prompts_seen) == 2  # original + 1 repair


def test_extract_repair_then_failed_no_silent_drop():
    adapter = FakeAdapter(["garbage one", "garbage two"])
    result = extract("x", model="fake", prompt_version="v1",
                     sampling=SAMPLING, source_id="10", adapter=adapter)
    assert result.status == "failed"
    assert result.repaired is True
    assert result.error and "after repair" in result.error
    assert len(adapter.prompts_seen) == 2  # exactly one repair attempt


def test_injection_case_correct_output_is_a_match():
    # Model IGNORES the injection and returns the real finding.
    expected = [_model_finding(severity="high", status="open")]
    # expected JSON as labeled (includes enum values):
    for e in expected:
        e.setdefault("severity", "high")
        e.setdefault("status", "open")
    predicted = [_model_finding(severity="high", status="open")]

    mr = match_findings(predicted, expected)
    assert len(mr.pairs) == 1
    assert not mr.missed_exp
    assert not mr.spurious_pred


def test_matching_counts_missed_and_spurious():
    expected = [
        _model_finding(title="finding A", finding_type="sql_injection"),
        _model_finding(title="finding B command injection",
                       finding_type="command_injection",
                       affected_assets=[{"asset": "helper", "repository": "repoX"}]),
    ]
    predicted = [
        _model_finding(title="finding A", finding_type="sql_injection"),
        _model_finding(title="totally unrelated thing", finding_type="xxe",
                       affected_assets=[{"asset": "zzz", "repository": "qqq"}]),
    ]
    mr = match_findings(predicted, expected)
    assert len(mr.pairs) == 1          # finding A matched
    assert len(mr.missed_exp) == 1     # finding B not predicted
    assert len(mr.spurious_pred) == 1  # unrelated prediction


def test_evaluate_result_aggregates_metrics():
    metrics = RunMetrics(model="fake", prompt_version="v1", sampling_name="deterministic")
    expected = [_model_finding(severity="high", status="open")]
    result = {
        "status": "ok",
        "repaired": False,
        "findings": [_model_finding(severity="high", status="open")],
        "latency_seconds": 0.5,
        "input_tokens": 100,
        "output_tokens": 50,
    }
    evaluate_result(metrics, result, expected)
    d = metrics.to_dict()
    assert d["documents"] == 1
    assert d["pct_valid_json"] == 1.0
    assert d["matched"] == 1
    assert d["finding_precision"] == 1.0
    assert d["finding_recall"] == 1.0
    assert d["latency_p50"] == 0.5
    assert d["overall_field_accuracy"] is not None
