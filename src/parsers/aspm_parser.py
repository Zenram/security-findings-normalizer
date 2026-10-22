"""
Deterministic parser for Ox ASPM alert exports (CAPSTONE_PLAN D1 routing).

Structured sources do NOT need the LLM. This parser turns an Ox ASPM record into
Finding dicts using only code — no model call. It handles two input shapes:

1. Real CSV export (`ox_issues_active_sanitized.csv`): header row + data rows.
2. Golden-set single-record block (`NN_input.txt`): `Field: value` lines, one
   record (the format used in data/golden/06_input.txt and 07_input.txt).

Field mapping (Ox column -> schema), all deterministic:
  Application "Team / app"   -> team (Team part) + repository (app part); team
                                also follows the *_app_N convention (D6).
  Issue ID                   -> source_record_id
  Issue Name                 -> title
  Issue Description          -> description
  Severity                   -> severity_raw   (D4: dual-severity rule)
  Original Severity          -> noted in extraction_notes (NOT severity_raw)
  Is Fix Available           -> status_raw ("active (Is Fix Available: <v>)")
  Vulnerabilities            -> cve_ids (comma-split, CVE-pattern filtered)
  Policy / Category          -> finding_type (via normalize table)
  Count                      -> instance count, recorded in extraction_notes

Severity/status ENUMS are assigned downstream by src/normalize.py (same code
table the LLM path uses), so the parser only fills the raw fields — identical
contract to the model path.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Optional

_CVE_RE = re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE)


def _clean(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _split_application(app: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """'Dev / dev_app_1' -> ('Dev', 'dev_app_1'). Handles missing parts."""
    if not app:
        return None, None
    parts = [p.strip() for p in app.split("/", 1)]
    if len(parts) == 2:
        return (_clean(parts[0]), _clean(parts[1]))
    return (_clean(parts[0]), None)


def _team_from_app(team_part: Optional[str], app_part: Optional[str]) -> Optional[str]:
    """Prefer the explicit Team part; else infer from *_app_N convention (D6)."""
    if team_part:
        return team_part
    if app_part:
        m = re.match(r"(data|dev|devops)_app_\d+", app_part, re.IGNORECASE)
        if m:
            return {"data": "Data", "dev": "Dev", "devops": "DevOps"}[m.group(1).lower()]
    return None


def _extract_cves(vuln_cell: Optional[str]) -> list[str]:
    if not vuln_cell:
        return []
    return [m.group(0).upper() for m in _CVE_RE.finditer(vuln_cell)]


def _finding_type_hint(policy: Optional[str], category: Optional[str], name: Optional[str]) -> str:
    """Map Ox Policy/Category/Name to a finding_type string that the normalize
    table recognizes. Deterministic keyword rules; normalize() resolves the enum
    and flags anything unmapped as OTHER (never invents)."""
    blob = " ".join(x for x in (policy, category, name) if x).lower()
    if "base image" in blob or "dockerfile" in blob:
        return "vulnerable_base_image"
    if "antiforgery" in blob or "csrf" in blob or "cross-site request forgery" in blob:
        return "csrf"
    if "sql" in blob:
        return "sql_injection"
    if "command injection" in blob or "os command" in blob:
        return "command_injection"
    if "deserializ" in blob:
        return "unsafe_deserialization"
    if "xxe" in blob or "xml external entity" in blob:
        return "xxe"
    if "package" in blob or "dependency" in blob:
        return "vulnerable_package"
    return "unknown"  # normalize() keeps this as UNKNOWN; not guessed


def _row_to_finding(row: dict[str, str], raw_reference: str) -> dict:
    app = _clean(row.get("Application"))
    team_part, app_part = _split_application(app)
    team = _team_from_app(team_part, app_part)

    issue_id = _clean(row.get("Issue ID"))
    severity_raw = _clean(row.get("Severity"))
    original_severity = _clean(row.get("Original Severity"))
    is_fix = _clean(row.get("Is Fix Available"))
    count = _clean(row.get("Count"))
    # Active export lists CVEs in "Vulnerabilities"; resolved export in
    # "Resolved Vulnerabilities".
    cves = _extract_cves(row.get("Vulnerabilities") or row.get("Resolved Vulnerabilities"))

    # Status: a resolved export carries a Resolved Issue Date -> resolved;
    # otherwise the record is active/open.
    resolved_date = _clean(row.get("Resolved Issue Date"))
    if resolved_date:
        status_raw = f"resolved ({resolved_date})"
    elif is_fix is not None:
        status_raw = f"active (Is Fix Available: {is_fix})"
    else:
        status_raw = "active"

    notes_bits = []
    if original_severity:
        notes_bits.append(
            f"D4 dual-severity: severity_raw=Severity '{severity_raw}'; "
            f"Original Severity '{original_severity}' kept here, not in severity_raw."
        )
    if count:
        notes_bits.append(f"Count={count} is an instance count, not the finding count.")
    if team:
        src = team_part or app_part
        notes_bits.append(f"team={team} from Application '{app}' ({src}).")

    return {
        "source": "aspm",
        "source_record_id": issue_id,
        "raw_reference": f"{raw_reference}#{issue_id}" if issue_id else raw_reference,
        "title": _clean(row.get("Issue Name")) or "ASPM finding (title missing)",
        "description": _clean(row.get("Issue Description")),
        "finding_type": _finding_type_hint(
            row.get("Policy"), row.get("Category"), row.get("Issue Name")
        ),
        "severity_raw": severity_raw,
        "status_raw": status_raw,
        "cve_ids": cves,
        "affected_assets": [{
            "asset": _asset_from_name(row.get("Issue Name")),
            "repository": app_part,
            "environment": None,
        }],
        "team": team,
        "evidence": _clean(row.get("Issue Description")),
        "extraction_notes": " ".join(notes_bits) or None,
    }


def _asset_from_name(name: Optional[str]) -> Optional[str]:
    """Best-effort asset label from the issue name (e.g. the base image)."""
    name = _clean(name)
    if not name:
        return None
    m = re.match(r"([\w.@/:+-]+ base image)", name, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _parse_block(text: str) -> Optional[dict[str, str]]:
    """Parse a single `Field: value` block (golden NN_input.txt format)."""
    row: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        # Only accept known Ox field names so narrative lines don't pollute.
        if key in _OX_FIELDS:
            row[key] = val.strip()
    return row or None


_OX_FIELDS = {
    "Application", "Business Priority", "Severity", "Count", "Original Severity",
    "Category", "Issue Name", "SLA", "Policy", "Issue Owner", "First Seen Date",
    "Issue ID", "Issue Description", "Recommendation", "CWE", "Vulnerabilities",
    "Severity Factors", "Is Fix Available", "Source tools",
    # resolved-issues export variants:
    "Resolved Issue Date", "Resolved Vulnerabilities",
}

# Strong field names that identify an Ox record even without an Issue ID (the
# resolved-issues export has no Issue ID).
_OX_IDENTIFYING = ("Issue ID", "Issue Name")


def parse_aspm(text: str, raw_reference: str = "ox_issues.csv") -> list[dict]:
    """Parse an Ox ASPM export (CSV or single-record block) into Finding dicts.

    Returns one finding per record. Raises ValueError if the text cannot be
    parsed as ASPM (so the router can fall back / mark failed rather than guess).
    """
    stripped = text.lstrip()

    # CSV path: a header line with Application + an identifying Ox column.
    first_line = stripped.splitlines()[0] if stripped else ""
    if ("Application" in first_line and "," in first_line
            and any(k in first_line for k in _OX_IDENTIFYING)):
        reader = csv.DictReader(io.StringIO(stripped))
        findings = [_row_to_finding(r, raw_reference) for r in reader
                    if any((v or "").strip() for v in r.values())]
        if not findings:
            raise ValueError("ASPM CSV had a header but no data rows")
        return findings

    # Block path: single `Field: value` record (golden format). Accept records
    # that have Application + an identifying field (Issue ID or Issue Name).
    row = _parse_block(stripped)
    if row and row.get("Application") and any(row.get(k) for k in _OX_IDENTIFYING):
        return [_row_to_finding(row, raw_reference)]

    raise ValueError("input does not look like an Ox ASPM export")
