"""Offline tests for the Part 2 Step 4 eval harness (deterministic parts).

No model calls: covers the deterministic scorer, calibration math, the lint
rules, and the CI gate logic — the pieces CI runs for free and relies on.
"""

from evals.run_evals import gate, lint
from evals.scorers import calibrate, score_deterministic


def _answer(found=True, answer="", citations=None, cited_sources=None, retrieved=None):
    return {
        "found": found, "answer": answer, "citations": citations or [],
        "cited_sources": cited_sources or [], "retrieved": retrieved or [],
    }


# --- deterministic scorer ---------------------------------------------------

def test_answerable_pass_needs_source_and_facts():
    case = {"kind": "answerable", "expected_sources": ["docA"],
            "must": [["least privilege"], ["iam", "role"]]}
    ans = _answer(found=True, answer="Enforce least privilege on every IAM role.",
                  cited_sources=[{"label": "S1", "source": "docA", "chunk_id": "docA#0"}])
    s = score_deterministic(ans, case)
    assert s.source_cited is True and s.facts_present is True and s.passed is True


def test_answerable_fails_when_fact_missing():
    case = {"kind": "answerable", "expected_sources": ["docA"], "must": [["bitlocker"]]}
    ans = _answer(found=True, answer="Something unrelated.",
                  cited_sources=[{"label": "S1", "source": "docA", "chunk_id": "docA#0"}])
    s = score_deterministic(ans, case)
    assert s.facts_present is False and s.passed is False


def test_answerable_fails_when_wrong_source_cited():
    case = {"kind": "answerable", "expected_sources": ["docA"], "must": [["x"]]}
    ans = _answer(found=True, answer="x",
                  cited_sources=[{"label": "S1", "source": "docB", "chunk_id": "docB#0"}])
    s = score_deterministic(ans, case)
    assert s.source_cited is False and s.passed is False


def test_no_answer_pass_requires_abstention():
    case = {"kind": "no_answer", "expected_sources": [], "must": []}
    assert score_deterministic(_answer(found=False, answer="not in docs"), case).passed is True
    assert score_deterministic(_answer(found=True, answer="made up"), case).passed is False


def test_trap_pass_requires_abstention():
    case = {"kind": "trap", "expected_sources": [], "must": []}
    assert score_deterministic(_answer(found=False), case).abstained is True
    assert score_deterministic(_answer(found=True, answer="CVSS 9.8"), case).passed is False


# --- calibration ------------------------------------------------------------

def test_calibrate_perfect_agreement():
    c = calibrate([True, False, True], [True, False, True], ["a", "b", "c"])
    assert c["agreement"] == 1.0 and c["false_pass"] == 0.0 and c["false_fail"] == 0.0
    assert c["disagreements"] == []


def test_calibrate_false_pass_and_fail():
    # judge says correct where human said wrong (false_pass), and vice versa.
    c = calibrate([True, False], [False, True], ["a", "b"])
    assert c["false_pass"] == 0.5 and c["false_fail"] == 0.5
    assert set(c["disagreements"]) == {"a", "b"}


# --- lint -------------------------------------------------------------------

def test_lint_flags_bad_cases(monkeypatch):
    import evals.run_evals as re_mod
    # Stub the corpus so lint does not need the real chunks.jsonl.
    monkeypatch.setattr(re_mod, "load_chunks", lambda: [{"source": "docA"}])
    bad = [
        {"id": "x1", "kind": "answerable", "question": "q", "reference": "r",
         "expected_sources": ["ghost"], "must": [["a"]]},          # bad source
        {"id": "x1", "kind": "no_answer", "question": "q", "reference": "r",
         "expected_sources": ["docA"], "must": [["a"]]},            # dup id + no_answer with must/sources
    ]
    problems = lint(bad)
    joined = " ".join(problems)
    assert "duplicate id" in joined
    assert "not in corpus" in joined
    assert "empty expected_sources" in joined or "empty must" in joined


# --- gate -------------------------------------------------------------------

def test_gate_passes_when_metrics_hold():
    base = {"pass": 0.80, "judge": 0.80, "false_abstain": 0.20}
    cur = {"pass": 0.85, "judge": 0.82, "false_abstain": 0.15, "by_kind": {}, "failed": []}
    assert gate(cur, base) == []


def test_gate_fails_on_metric_drop():
    base = {"pass": 0.90, "judge": 0.90}
    cur = {"pass": 0.70, "judge": 0.90, "by_kind": {}, "failed": []}   # 0.20 drop > tolerance
    failures = gate(cur, base)
    assert any("pass" in f for f in failures)


def test_gate_fails_on_false_abstain_rise():
    base = {"false_abstain": 0.10}
    cur = {"false_abstain": 0.30, "by_kind": {}, "failed": []}         # higher is worse
    assert any("false_abstain" in f for f in gate(cur, base))


def test_gate_ignores_faithful_metric():
    # faithful is diagnostic-only; a drop must NOT fail the gate.
    base = {"pass": 0.80, "faithful": 0.90}
    cur = {"pass": 0.82, "faithful": 0.30, "by_kind": {}, "failed": []}
    assert gate(cur, base) == []
