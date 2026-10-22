"""
Parsing + schema validation + normalization application.

Policy (CAPSTONE_PLAN Stage 3, confirmed): parse -> validate; on failure, the
caller performs ONE repair attempt, then marks the record `failed`. No silent
drops. This module provides the building blocks; the 1-retry loop lives in
extract.py so the control flow is explicit.

The model emits ONLY `*_raw` wording for severity/status (per prompt v1). This
module applies the D4 code-side normalization tables to assign the enum values,
so the Finding objects are fully populated and reproducible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from schema.finding import Finding
from src.normalize import (
    normalize_finding_type,
    normalize_severity,
    normalize_status,
)


@dataclass
class ValidationOutcome:
    """Result of trying to turn raw model text into validated Findings."""

    ok: bool
    findings: list[Finding] = field(default_factory=list)
    findings_json: list[dict] = field(default_factory=list)  # normalized dicts
    error: str | None = None
    normalization_flags: list[str] = field(default_factory=list)


_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` fences a model may add despite instructions."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _JSON_FENCE_RE.sub("", stripped)
    return stripped.strip()


def parse_json_array(raw_text: str) -> list[dict]:
    """Parse model text into a list of finding dicts.

    Accepts a JSON array, or a single object (wrapped into a 1-element list), or
    an object with a top-level "findings" key. Raises ValueError on anything
    that is not usable.
    """
    text = _strip_code_fences(raw_text)
    if not text:
        raise ValueError("empty model output")

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        # Last-ditch: grab the outermost [...] array if the model added prose.
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            raise ValueError(f"output is not valid JSON: {exc}") from exc
        data = json.loads(match.group(0))

    if isinstance(data, dict):
        if isinstance(data.get("findings"), list):
            data = data["findings"]
        else:
            data = [data]
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of findings")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("array elements must be finding objects")
    return data


def apply_normalization(raw_finding: dict, flags: list[str]) -> dict:
    """Assign D4 enum values from the model's raw wording.

    The model supplies severity_raw/status_raw and a proposed finding_type; the
    code tables assign the authoritative enums. Unknown values are flagged.
    """
    out = dict(raw_finding)

    sev = normalize_severity(out.get("severity_raw"))
    out["severity"] = sev.value.value
    if sev.note:
        flags.append(f"severity: {sev.note}")

    status = normalize_status(out.get("status_raw"))
    out["status"] = status.value.value
    if status.note:
        flags.append(f"status: {status.note}")

    ftype = normalize_finding_type(out.get("finding_type"))
    out["finding_type"] = ftype.value.value
    if ftype.note:
        flags.append(f"finding_type: {ftype.note}")

    return out


def validate_findings(raw_text: str) -> ValidationOutcome:
    """Full pipeline for one model output: parse -> normalize -> schema-validate.

    Returns ok=False with an error message if any step fails; the caller decides
    whether to trigger the single repair attempt.
    """
    flags: list[str] = []
    try:
        raw_list = parse_json_array(raw_text)
    except ValueError as exc:
        return ValidationOutcome(ok=False, error=f"parse error: {exc}")

    findings: list[Finding] = []
    normalized_dicts: list[dict] = []
    for idx, raw_finding in enumerate(raw_list):
        normalized = apply_normalization(raw_finding, flags)
        try:
            model = Finding(**normalized)
        except ValidationError as exc:
            return ValidationOutcome(
                ok=False,
                error=f"schema validation failed on finding[{idx}]: {exc}",
                normalization_flags=flags,
            )
        findings.append(model)
        normalized_dicts.append(model.model_dump(mode="json"))

    return ValidationOutcome(
        ok=True,
        findings=findings,
        findings_json=normalized_dicts,
        normalization_flags=flags,
    )
