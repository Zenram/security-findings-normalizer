"""Deterministic parsers for structured sources (CAPSTONE_PLAN D1 routing).

Structured inputs (e.g. Ox ASPM CSV) are parsed in code — no LLM. The LLM path
is reserved for genuinely unstructured sources (team reports, LinPEAS).
"""

from __future__ import annotations

from src.parsers.aspm_parser import parse_aspm

__all__ = ["parse_aspm"]
