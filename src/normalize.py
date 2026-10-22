"""
D4 — Severity / status normalization: the CODE TABLE normalizes, the model only
extracts raw wording.

The model fills `severity_raw` / `status_raw` with the original source wording.
These deterministic maps turn that raw wording into the controlled enum. Unknown
raw values map to the UNKNOWN member and are FLAGGED (never invented). This keeps
normalization reproducible, testable, and auditable (CAPSTONE_PLAN D4).

Tables are intentionally explicit and version-controlled. When a new raw value
appears in the data, add it here deliberately rather than guessing in a prompt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from schema.finding import FindingType, Severity, Status


@dataclass
class NormalizationResult:
    """Outcome of mapping one raw value through a table."""

    value: object  # the resolved enum member
    matched: bool  # True if the raw value hit a known mapping
    note: Optional[str] = None  # flag text when unmatched / ambiguous


def _norm_key(raw: Optional[str]) -> str:
    """Lowercase + collapse whitespace for table lookup."""
    if raw is None:
        return ""
    return re.sub(r"\s+", " ", raw.strip().lower())


# --- Severity ----------------------------------------------------------------
# Keys are normalized (lowercased) raw values seen in real sources. LinPEAS
# emits state words ("vulnerable", "potentially vulnerable") that are NOT
# severity labels -> these intentionally map to UNKNOWN (D4: do not guess High).

_SEVERITY_EXACT: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "crit": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "med": Severity.MEDIUM,
    "moderate": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
    "informational": Severity.INFO,
    "information": Severity.INFO,
    "none": Severity.INFO,
    "negligible": Severity.LOW,
}


def normalize_severity(raw: Optional[str]) -> NormalizationResult:
    """Map a raw severity string to the Severity enum.

    Unknown / non-severity wording -> Severity.UNKNOWN, flagged. Never invents a
    level (LinPEAS 'Vulnerable' has no severity -> unknown).
    """
    key = _norm_key(raw)
    if not key:
        return NormalizationResult(Severity.UNKNOWN, matched=False,
                                   note="no severity wording in source -> unknown")
    if key in _SEVERITY_EXACT:
        return NormalizationResult(_SEVERITY_EXACT[key], matched=True)
    # Substring fallback for decorated labels like "high (public exploit)".
    for token, sev in _SEVERITY_EXACT.items():
        if re.search(rf"\b{re.escape(token)}\b", key):
            return NormalizationResult(sev, matched=True,
                                       note=f"severity matched token '{token}' in '{raw}'")
    return NormalizationResult(Severity.UNKNOWN, matched=False,
                               note=f"unmapped severity_raw '{raw}' -> unknown (not guessed)")


# --- Status ------------------------------------------------------------------
# Scanner / report vocab is messy: Trivy "FAIL", Ox "active", free-text
# "live in this snapshot", "remain open ... suggested accept-risk (not applied)".
# Exact keys first, then keyword heuristics over the raw phrase.

_STATUS_EXACT: dict[str, Status] = {
    "open": Status.OPEN,
    "active": Status.OPEN,
    "live": Status.OPEN,
    "fail": Status.OPEN,
    "failed": Status.OPEN,
    "new": Status.OPEN,
    "detected": Status.OPEN,
    "in_progress": Status.IN_PROGRESS,
    "in progress": Status.IN_PROGRESS,
    "in-progress": Status.IN_PROGRESS,
    "wip": Status.IN_PROGRESS,
    "remediating": Status.IN_PROGRESS,
    "resolved": Status.RESOLVED,
    "fixed": Status.RESOLVED,
    "closed": Status.RESOLVED,
    "pass": Status.RESOLVED,
    "passed": Status.RESOLVED,
    "mitigated": Status.RESOLVED,
    "reopened": Status.REOPENED,
    "re-opened": Status.REOPENED,
    "accepted_risk": Status.ACCEPTED_RISK,
    "accepted risk": Status.ACCEPTED_RISK,
    "accept-risk": Status.ACCEPTED_RISK,
    "risk accepted": Status.ACCEPTED_RISK,
    "wontfix": Status.ACCEPTED_RISK,
    "won't fix": Status.ACCEPTED_RISK,
}

# Ordered keyword rules applied to the full raw phrase when no exact key hits.
# Order matters: an *applied* accept-risk beats a bare "open"; a *suggested*
# accept-risk that is "not applied" must stay OPEN (golden entry 01).
_STATUS_PHRASE_RULES: list[tuple[str, Status]] = [
    ("not applied", Status.OPEN),            # "suggested accept-risk (not applied)"
    ("remain open", Status.OPEN),
    ("no fix branch", Status.OPEN),
    ("no remediation", Status.OPEN),
    ("vulnerable", Status.OPEN),             # LinPEAS state -> currently vulnerable
    ("reopen", Status.REOPENED),
    ("accept-risk", Status.ACCEPTED_RISK),
    ("accepted", Status.ACCEPTED_RISK),
    ("resolved", Status.RESOLVED),
    ("fixed", Status.RESOLVED),
    ("closed", Status.RESOLVED),
    ("in progress", Status.IN_PROGRESS),
    ("open", Status.OPEN),
    ("active", Status.OPEN),
    ("live", Status.OPEN),
]


def normalize_status(raw: Optional[str]) -> NormalizationResult:
    """Map a raw status string to the Status enum.

    Exact table first, then ordered keyword rules over the phrase. Unknown ->
    Status.UNKNOWN, flagged. Never invents a status.
    """
    key = _norm_key(raw)
    if not key:
        return NormalizationResult(Status.UNKNOWN, matched=False,
                                   note="no status wording in source -> unknown")
    if key in _STATUS_EXACT:
        return NormalizationResult(_STATUS_EXACT[key], matched=True)
    for phrase, status in _STATUS_PHRASE_RULES:
        if phrase in key:
            return NormalizationResult(status, matched=True,
                                       note=f"status matched phrase '{phrase}' in '{raw}'")
    return NormalizationResult(Status.UNKNOWN, matched=False,
                               note=f"unmapped status_raw '{raw}' -> unknown (not guessed)")


# --- Finding type ------------------------------------------------------------
# finding_type is a controlled vocab (schema/finding.py). The model proposes a
# category string; this table validates it against the enum. An out-of-vocab
# value is NOT invented into a new member: it maps to OTHER (real finding, no
# fitting member) and is flagged for review. Empty -> UNKNOWN.

_FINDING_TYPE_ALIASES: dict[str, FindingType] = {
    # direct enum values
    **{ft.value: ft for ft in FindingType},
    # common synonyms seen in sources
    "cmd injection": FindingType.COMMAND_INJECTION,
    "os command injection": FindingType.COMMAND_INJECTION,
    "shell injection": FindingType.COMMAND_INJECTION,
    "sqli": FindingType.SQL_INJECTION,
    "raw sql": FindingType.SQL_INJECTION,
    "sql interpolation": FindingType.SQL_INJECTION,
    "xml external entity": FindingType.XXE,
    "cross-site request forgery": FindingType.CSRF,
    "missing antiforgery": FindingType.CSRF,
    "insecure deserialization": FindingType.UNSAFE_DESERIALIZATION,
    "base image": FindingType.VULNERABLE_BASE_IMAGE,
    "vulnerable base image (cve) in dockerfile": FindingType.VULNERABLE_BASE_IMAGE,
    "vulnerable dependency": FindingType.VULNERABLE_PACKAGE,
    "outdated package": FindingType.VULNERABLE_PACKAGE,
    "dockerfile misconfiguration": FindingType.DOCKERFILE_MISCONFIGURATION,
    "dockerfile security check": FindingType.DOCKERFILE_MISCONFIGURATION,
    "kernel vuln": FindingType.KERNEL_VULNERABILITY,
    "cpu vuln": FindingType.CPU_VULNERABILITY,
    "stale repo": FindingType.STALE_REPOSITORY,
    "unmaintained repository": FindingType.STALE_REPOSITORY,
    "branch protection": FindingType.BRANCH_PROTECTION_MISSING,
    "code review policy": FindingType.CODE_REVIEW_POLICY_MISSING,
}


def normalize_finding_type(raw: Optional[str]) -> NormalizationResult:
    """Validate/normalize a raw finding_type into the FindingType enum.

    Known value/alias -> that member. Non-empty but unmapped -> OTHER (flagged),
    because it is a real finding that fits no member. Empty -> UNKNOWN.
    """
    key = _norm_key(raw)
    if not key:
        return NormalizationResult(FindingType.UNKNOWN, matched=False,
                                   note="no finding_type in source -> unknown")
    if key in _FINDING_TYPE_ALIASES:
        return NormalizationResult(_FINDING_TYPE_ALIASES[key], matched=True)
    return NormalizationResult(FindingType.OTHER, matched=False,
                               note=f"unmapped finding_type '{raw}' -> other (flagged, not invented)")
