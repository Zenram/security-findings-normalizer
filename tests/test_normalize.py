"""
D4 normalization-table tests. The code table normalizes; unknown raw values
map to UNKNOWN and are flagged, never invented.
"""

from schema.finding import FindingType, Severity, Status
from src.normalize import (
    normalize_finding_type,
    normalize_severity,
    normalize_status,
)


# --- severity ---------------------------------------------------------------

def test_severity_known_values():
    assert normalize_severity("High").value is Severity.HIGH
    assert normalize_severity("HIGH").value is Severity.HIGH
    assert normalize_severity("Critical").value is Severity.CRITICAL
    assert normalize_severity("medium").value is Severity.MEDIUM
    assert normalize_severity("Low").value is Severity.LOW


def test_severity_linpeas_state_words_are_unknown_not_guessed():
    # LinPEAS "Vulnerable" / "Potentially vulnerable" are NOT severity labels.
    r1 = normalize_severity("Vulnerable")
    r2 = normalize_severity("Potentially vulnerable")
    r3 = normalize_severity("vulnerable version installed")
    assert r1.value is Severity.UNKNOWN and not r1.matched
    assert r2.value is Severity.UNKNOWN and not r2.matched
    assert r3.value is Severity.UNKNOWN and not r3.matched
    assert r1.note  # flagged


def test_severity_none_is_unknown():
    r = normalize_severity(None)
    assert r.value is Severity.UNKNOWN and not r.matched


# --- status -----------------------------------------------------------------

def test_status_known_and_scanner_vocab():
    assert normalize_status("open").value is Status.OPEN
    assert normalize_status("FAIL").value is Status.OPEN
    assert normalize_status("active (Is Fix Available: false)").value is Status.OPEN
    assert normalize_status("live").value is Status.OPEN
    assert normalize_status("resolved").value is Status.RESOLVED
    assert normalize_status("PASS").value is Status.RESOLVED


def test_status_suggested_accept_risk_not_applied_stays_open():
    # Golden entry 01: accept-risk only suggested, not applied -> open.
    r = normalize_status("remain open in this snapshot; suggested accept-risk (not applied)")
    assert r.value is Status.OPEN


def test_status_applied_accept_risk():
    assert normalize_status("accepted risk").value is Status.ACCEPTED_RISK
    assert normalize_status("risk accepted").value is Status.ACCEPTED_RISK


def test_status_unknown_flagged():
    r = normalize_status("some novel status wording")
    assert r.value is Status.UNKNOWN and not r.matched and r.note


# --- finding_type -----------------------------------------------------------

def test_finding_type_known_and_alias():
    assert normalize_finding_type("sql_injection").value is FindingType.SQL_INJECTION
    assert normalize_finding_type("sqli").value is FindingType.SQL_INJECTION
    assert normalize_finding_type("dockerfile security check").value is FindingType.DOCKERFILE_MISCONFIGURATION


def test_finding_type_unmapped_is_other_flagged_not_invented():
    r = normalize_finding_type("some_brand_new_category")
    assert r.value is FindingType.OTHER and not r.matched and r.note


def test_finding_type_empty_is_unknown():
    r = normalize_finding_type(None)
    assert r.value is FindingType.UNKNOWN and not r.matched
