"""
Schema contract tests (DEV_HANDOFF step 2): a valid record passes; a missing
required `title` fails; a bad enum fails; nulls are allowed where specified.
Also: every golden expected record validates against the Finding model.
"""

import json

import pytest
from pydantic import ValidationError

from schema.finding import AffectedAsset, Finding, FindingType, Severity, SourceType, Status
from src.config import GOLDEN_DIR


def _valid_record() -> dict:
    return {
        "source": "team_report",
        "title": "SQL injection in reporting export endpoint",
        "finding_type": "sql_injection",
        "severity": "high",
        "severity_raw": "High",
        "status": "open",
        "status_raw": "open",
        "cve_ids": [],
        "affected_assets": [{"asset": "endpoint", "repository": "billing_app_2"}],
        "team": "Dev",
    }


def test_valid_record_passes():
    f = Finding(**_valid_record())
    assert f.title == "SQL injection in reporting export endpoint"
    assert f.severity is Severity.HIGH
    assert f.status is Status.OPEN
    assert f.finding_type is FindingType.SQL_INJECTION
    assert f.source is SourceType.TEAM_REPORT
    assert isinstance(f.affected_assets[0], AffectedAsset)


def test_missing_required_title_fails():
    rec = _valid_record()
    del rec["title"]
    with pytest.raises(ValidationError):
        Finding(**rec)


def test_bad_enum_fails():
    rec = _valid_record()
    rec["severity"] = "super-duper-critical"
    with pytest.raises(ValidationError):
        Finding(**rec)


def test_nulls_allowed_where_specified():
    # Only title is required; everything else may be null / defaulted.
    f = Finding(title="minimal finding")
    assert f.source_record_id is None
    assert f.description is None
    assert f.team is None
    assert f.severity is Severity.UNKNOWN
    assert f.status is Status.UNKNOWN
    assert f.finding_type is FindingType.UNKNOWN
    assert f.cve_ids == []
    assert f.affected_assets == []


def test_defaults_are_unknown_enums():
    f = Finding(title="x")
    assert f.severity.value == "unknown"
    assert f.status.value == "unknown"
    assert f.finding_type.value == "unknown"
    assert f.source.value == "unknown"


def test_all_golden_expected_records_validate():
    expected_files = sorted(GOLDEN_DIR.glob("[0-9][0-9]_expected.json"))
    assert expected_files, "no golden expected files found"
    failures = []
    for path in expected_files:
        records = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(records, list), f"{path.name} is not a JSON array"
        for i, rec in enumerate(records):
            try:
                Finding(**rec)
            except ValidationError as exc:  # pragma: no cover - should not happen
                failures.append(f"{path.name}[{i}]: {exc}")
    assert not failures, "golden records failed schema validation:\n" + "\n".join(failures)
