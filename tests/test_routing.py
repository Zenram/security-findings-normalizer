"""
D1 routing tests: structured ASPM -> deterministic parser; unstructured
(team reports, LinPEAS) and mixed/cross-source -> LLM path.

The parser path is validated against the golden ASPM entries (06, 07) WITHOUT
calling any model.
"""

import json
from pathlib import Path

from src.config import GOLDEN_DIR, SAMPLING_CONFIGS
from src.parsers import parse_aspm
from src.routing import detect_source, route_and_extract, route_for_source


def _read(entry_id: str) -> str:
    p = sorted(GOLDEN_DIR.glob(f"{entry_id}_input.*"))[0]
    return p.read_text(encoding="utf-8")


# --- source detection --------------------------------------------------------

def test_detect_aspm_block():
    assert detect_source(_read("06")) == "aspm"
    assert detect_source(_read("07")) == "aspm"


def test_detect_team_report():
    assert detect_source(_read("01")) == "team_report"
    assert detect_source(_read("10")) == "team_report"


def test_detect_linpeas():
    assert detect_source(_read("04")) == "linpeas"
    assert detect_source(_read("05")) == "linpeas"


def test_detect_mixed_cross_source_is_not_parsed():
    # Golden 09 pairs LinPEAS + ASPM on purpose -> must NOT hit the parser.
    assert detect_source(_read("09")) == "mixed"
    assert route_for_source("mixed") == "llm"


def test_routing_table():
    assert route_for_source("aspm") == "parser"
    assert route_for_source("team_report") == "llm"
    assert route_for_source("linpeas") == "llm"
    assert route_for_source("unknown") == "llm"


# --- parser correctness (no model) ------------------------------------------

def test_parser_matches_golden_06():
    findings = parse_aspm(_read("06"), raw_reference="06_input.txt")
    assert len(findings) == 1
    f = findings[0]
    assert f["source"] == "aspm"
    assert f["source_record_id"] == "issue-3513"
    assert f["severity_raw"] == "High"          # dual-severity: surfaced Severity
    assert "Critical" in (f["extraction_notes"] or "")  # Original Severity noted
    assert f["team"] == "DevOps"
    assert f["affected_assets"][0]["repository"] == "devops_app_1"
    assert len(f["cve_ids"]) >= 6               # CVE list extracted
    assert all(c.startswith("CVE-") for c in f["cve_ids"])


def test_parser_matches_golden_07():
    findings = parse_aspm(_read("07"), raw_reference="07_input.txt")
    assert len(findings) == 1
    f = findings[0]
    assert f["source_record_id"] == "issue-9804"
    assert f["team"] == "Dev"
    assert f["affected_assets"][0]["repository"] == "dev_app_1"
    assert f["cve_ids"] == []                   # CSRF finding has no CVEs


def test_parser_path_assigns_enums_via_code_table():
    # The parser fills *_raw; normalization (code table) assigns the enum.
    routed = route_and_extract(
        _read("06"), model="gemini", prompt_version="v1",
        sampling=SAMPLING_CONFIGS["deterministic"], source_id="06",
        raw_reference="06_input.txt",
    )
    assert routed.route == "parser"
    assert routed.result.status == "ok"
    f = routed.result.findings[0]
    assert f["severity"] == "high"       # assigned by code table from "High"
    assert f["status"] == "open"         # assigned from "active (...)"
    assert f["finding_type"] == "vulnerable_base_image"


def test_parser_rejects_non_aspm():
    import pytest
    with pytest.raises(ValueError):
        parse_aspm("just some free text with no Ox fields", raw_reference="x")
