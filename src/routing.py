"""
Extraction routing (CAPSTONE_PLAN D1): structured sources go through a
deterministic parser; genuinely unstructured sources go through the LLM.

This answers the mentor's Q1 ("where do you really need the LLM?") and makes the
routing decision a reportable result: every result records `route` = "parser"
or "llm". The comparison grid runs the LLM over the LLM-path sources; the parser
path is model-independent (same output regardless of model/sampling).

Source detection is content-based (not filename-based) so it also works on the
wider raw corpus, not just the golden set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from src.config import SamplingConfig
from src.extract import ExtractionResult, extract
from src.parsers import parse_aspm
from src.validate import apply_normalization
from schema.finding import Finding


# --- source detection --------------------------------------------------------

def detect_source(text: str) -> str:
    """Classify a raw document into a source family by content signature.

    Returns one of: "aspm", "team_report", "linpeas", "mixed", "unknown".
    Only a PURE structured ASPM record is routed to the parser; a mixed /
    cross-source document goes to the LLM.
    """
    low = text.lower()

    # A genuinely MIXED / cross-source document contains records from two tools
    # (golden 09: explicit "RECORD A: LinPEAS" + "RECORD B: Ox ASPM"). Detect by
    # the structural two-record marker, not a loose phrase, so that a mere
    # descriptive mention of "cross-source" does not misclassify a pure source.
    has_record_ab = bool(
        re.search(r"record a\s*:", low) and re.search(r"record b\s*:", low)
    )
    if has_record_ab and ("linpeas" in low or "aspm" in low):
        return "mixed"

    linpeas_sig = "linpeas" in low

    # Ox ASPM: real CSV header row, OR the `Field: value` block (golden format)
    # with Ox-specific field names anywhere in the text.
    first_line = text.lstrip().splitlines()[0] if text.strip() else ""
    is_csv_header = ("Application" in first_line and "Issue ID" in first_line
                     and "," in first_line)
    has_block_fields = bool(
        re.search(r"^\s*Application\s*:", text, re.MULTILINE)
        and re.search(r"^\s*Issue ID\s*:", text, re.MULTILINE)
    )
    aspm_sig = is_csv_header or has_block_fields

    # If BOTH an ASPM signature and a LinPEAS signature are present, it is a
    # mixed document -> LLM path, not the deterministic parser.
    if aspm_sig and linpeas_sig:
        return "mixed"
    if aspm_sig:
        return "aspm"

    # LinPEAS: its banners / section markers / the tool name.
    if "linpeas" in low:
        return "linpeas"
    if "privilege escalation" in low and "╔" in text:
        return "linpeas"

    # Team report: chat-style "#channel-security" or "Name (role):" speaker lines.
    if re.search(r"#\w[\w-]*-security", text) or re.search(
        r"\w+ \((analyst|engineer|developer)\):", text
    ):
        return "team_report"

    return "unknown"


def route_for_source(source: str) -> str:
    """Which path a source family takes: 'parser' or 'llm' (D1 table)."""
    return "parser" if source == "aspm" else "llm"


# --- parser path -------------------------------------------------------------

def _parser_extract(text: str, source: str, source_id: str, raw_reference: str) -> ExtractionResult:
    """Run the deterministic parser, then the SAME normalization + schema
    validation the LLM path uses. No model call, so metadata reflects 'parser'.
    """
    result = ExtractionResult(
        model="parser",
        model_name="deterministic-aspm",
        prompt_version="n/a",
        sampling={"name": "n/a", "temperature": None, "top_p": None},
        source_id=source_id,
    )
    try:
        raw_findings = parse_aspm(text, raw_reference=raw_reference)
    except ValueError as exc:
        result.status = "failed"
        result.error = f"parser error: {exc}"
        return result

    flags: list[str] = []
    out: list[dict] = []
    try:
        for rf in raw_findings:
            normalized = apply_normalization(rf, flags)
            model = Finding(**normalized)
            out.append(model.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001
        result.status = "failed"
        result.error = f"parser output failed schema validation: {exc}"
        result.normalization_flags = flags
        return result

    result.status = "ok"
    result.findings = out
    result.normalization_flags = flags
    result.latency_seconds = 0.0  # deterministic, effectively instant
    return result


# --- public entry ------------------------------------------------------------

@dataclass
class RoutedResult:
    route: str            # "parser" | "llm"
    source: str           # detected source family
    result: ExtractionResult


def route_and_extract(
    text: str,
    model: str,
    prompt_version: str,
    sampling: SamplingConfig,
    source_id: str = "adhoc",
    timeout: int = 60,
    raw_reference: Optional[str] = None,
) -> RoutedResult:
    """Detect the source, then either parse deterministically or call the LLM.

    The parser path ignores model/prompt/sampling (it is model-independent); the
    LLM path uses them as before.
    """
    source = detect_source(text)
    route = route_for_source(source)

    if route == "parser":
        res = _parser_extract(text, source, source_id, raw_reference or f"{source_id}")
        res.route = "parser"
        res.source = source
        return RoutedResult(route="parser", source=source, result=res)

    res = extract(
        text=text, model=model, prompt_version=prompt_version,
        sampling=sampling, source_id=source_id, timeout=timeout,
    )
    res.route = "llm"
    res.source = source
    return RoutedResult(route="llm", source=source, result=res)
