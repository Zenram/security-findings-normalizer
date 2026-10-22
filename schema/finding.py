"""
Canonical schema — DRAFT for Stage 1 (extraction baseline).

This is a PLANNING artifact. The Developer specialist moves this into the repo
as `schema/finding.py`, wires validation/retry around it, and may extend it —
but field names, enums, and nullability below are the frozen Stage 1 contract.

Scope decision: this is a focused subset of the 18-field model in
3_full_project_plan.md. It satisfies the course minimum (>=6 fields, >=1 enum,
>=1 nested/list) and keeps source traceability + the required hard cases.
Fields deferred to later stages are listed at the bottom (DEFERRED), not deleted.

Core principles (from the plans):
- Never fabricate. Absent -> None (null) or the UNKNOWN enum member.
- Preserve the ORIGINAL source-reported severity/status separately from the
  normalized enum value. Normalization must not lose the source wording.
- A CVE match is not identity; multiple CVEs per finding are allowed.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums (normalized controlled vocab) ------------------------------------

class Severity(str, Enum):
    """Normalized severity. Original source wording kept in severity_raw."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


class Status(str, Enum):
    """Normalized status. Original source wording kept in status_raw.

    NOTE: `resolved` here means source-REPORTED resolved, not verified fixed.
    """
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REOPENED = "reopened"
    ACCEPTED_RISK = "accepted_risk"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    """Originating tool / document family."""
    TEAM_REPORT = "team_report"
    CNAPP = "cnapp"            # cloud infra security platform alert export
    ASPM = "aspm"             # code/app security platform alert export
    OSS_SCANNER = "oss_scanner"  # Kubescape / Trivy / Prowler / TruffleHog / LinPEAS
    UNKNOWN = "unknown"


class FindingType(str, Enum):
    """Normalized finding category (controlled vocab).

    Values derived from the golden set. Like severity/status, the normalized
    value is assigned by a code-side mapping; the model's raw interpretation
    can be preserved in `extraction_notes` when it does not fit cleanly.
    Use OTHER for a real finding that fits no member; UNKNOWN when the category
    cannot be determined. Extend this enum as new categories appear — do not
    force-fit.
    """
    # Code / application security
    COMMAND_INJECTION = "command_injection"
    SQL_INJECTION = "sql_injection"
    XXE = "xxe"
    CSRF = "csrf"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"

    # Dependencies / images / packages
    VULNERABLE_BASE_IMAGE = "vulnerable_base_image"
    VULNERABLE_PACKAGE = "vulnerable_package"
    DOCKERFILE_MISCONFIGURATION = "dockerfile_misconfiguration"

    # Host / kernel / platform
    KERNEL_VULNERABILITY = "kernel_vulnerability"
    CPU_VULNERABILITY = "cpu_vulnerability"

    # Governance / repo hygiene
    STALE_REPOSITORY = "stale_repository"
    BRANCH_PROTECTION_MISSING = "branch_protection_missing"
    CODE_REVIEW_POLICY_MISSING = "code_review_policy_missing"

    # Escape hatches
    OTHER = "other"
    UNKNOWN = "unknown"


# --- Nested / list structures ------------------------------------------------

class AffectedAsset(BaseModel):
    """One affected asset. A finding may list several (nested + list field)."""
    asset: Optional[str] = Field(
        default=None, description="Stable asset/workload identifier where available."
    )
    repository: Optional[str] = Field(
        default=None, description="Affected repository, if applicable."
    )
    environment: Optional[str] = Field(
        default=None, description="Environment/deployment context (prod/stage/...)."
    )


# --- The canonical record ----------------------------------------------------

class Finding(BaseModel):
    """One security finding extracted from one source document.

    Field count well above the >=6 minimum; >=1 enum (4 of them);
    >=1 nested/list (affected_assets, cve_ids).
    """

    # Traceability (who/where it came from)
    source: SourceType = Field(
        default=SourceType.UNKNOWN,
        description="Originating tool/report family. UNKNOWN if not determinable.",
    )
    source_record_id: Optional[str] = Field(
        default=None, description="Original record ID in the source. Null if absent."
    )
    raw_reference: Optional[str] = Field(
        default=None, description="Locator back to the original record (file/line/URL)."
    )

    # What the finding is
    title: str = Field(description="Short finding title. Required; preserve source context.")
    description: Optional[str] = Field(
        default=None, description="Longer description if present in source."
    )
    finding_type: FindingType = Field(
        default=FindingType.UNKNOWN,
        description="Normalized finding category. OTHER if it fits no member, "
                    "UNKNOWN if undeterminable. Never invent a category.",
    )

    # Normalized + raw severity/status (keep both)
    severity: Severity = Field(
        default=Severity.UNKNOWN, description="Normalized severity enum."
    )
    severity_raw: Optional[str] = Field(
        default=None, description="Exact severity wording as it appeared in the source."
    )
    status: Status = Field(
        default=Status.UNKNOWN, description="Normalized, source-REPORTED status enum."
    )
    status_raw: Optional[str] = Field(
        default=None, description="Exact status wording as it appeared in the source."
    )

    # Identity-ish fields (NOT unique keys on their own)
    cve_ids: list[str] = Field(
        default_factory=list,
        description="Zero, one, or many CVE IDs. A shared CVE is NOT proof of duplicate.",
    )
    affected_assets: list[AffectedAsset] = Field(
        default_factory=list,
        description="One or more affected assets. Empty list if none stated.",
    )

    # Ownership + evidence
    team: Optional[str] = Field(
        default=None, description="Responsible/affected team. Null if unknown."
    )
    evidence: Optional[str] = Field(
        default=None, description="Short supporting excerpt from the source text."
    )

    # --- Extraction self-report (helps evaluation, optional) ---
    extraction_notes: Optional[str] = Field(
        default=None,
        description="Model's note on ambiguity/low confidence. Not a value, metadata.",
    )


# --- DEFERRED (documented, NOT part of Stage 1) ------------------------------
# These exist in the full 18-field model and will be added in later stages
# (correlation / historical tracking). Do NOT implement in Stage 1:
#   first_seen, last_seen, resolved_at, reporting_period
# Rationale: labeling timestamps by hand for the golden set is expensive and
# not needed to prove extraction quality for the course assignment.
