"""
Corpus loader — the full ~30-text input set for Step 1 ("проженіть усі тексти").

Distinct from the golden set: corpus texts are UNLABELED, so they are processed
(extracted + validated + saved) but NOT scored (no answer key to compare to).
This mirrors the accepted pattern: run the whole corpus, measure quality only on
the labeled golden subset.

Counting convention for "one text":
- a team report file  -> 1 text
- a LinPEAS file       -> 1 text
- an ASPM CSV          -> 1 text PER ROW (each row is one alert/record)

Only the 3 mentor-approved sources are included (team reports, Ox ASPM, LinPEAS).
Trivy/Kubescape/Orca/standards stay out until a later stage.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from src.config import REPO_ROOT

RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass
class CorpusText:
    """One unlabeled corpus document fed to the pipeline."""

    doc_id: str          # stable id, e.g. "team_report__team_report_dev_2026-09-14"
    source_hint: str     # "team_report" | "aspm" | "linpeas" (for reference)
    text: str            # the raw text handed to routing/extraction
    origin: str          # file path (+ row) it came from


def _csv_row_to_block(header: list[str], row: list[str]) -> str:
    """Render one ASPM CSV row as a `Field: value` block so the ASPM parser's
    block path handles it (same shape as the golden 06/07 inputs)."""
    lines = []
    for key, val in zip(header, row):
        if val is not None and val.strip():
            lines.append(f"{key}: {val.strip()}")
    return "\n".join(lines)


def load_corpus() -> list[CorpusText]:
    """Enumerate the full in-scope raw corpus as individual texts."""
    texts: list[CorpusText] = []

    # 1) Team reports — one text per file.
    tr_dir = RAW_DIR / "team_reports"
    for p in sorted(tr_dir.glob("*.txt")):
        texts.append(CorpusText(
            doc_id=f"team_report__{p.stem}",
            source_hint="team_report",
            text=p.read_text(encoding="utf-8"),
            origin=str(p.relative_to(REPO_ROOT)),
        ))

    # 2) LinPEAS — one text per file.
    lp_dir = RAW_DIR / "oss_scanner" / "linpeas"
    for p in sorted(lp_dir.glob("*.txt")):
        texts.append(CorpusText(
            doc_id=f"linpeas__{p.stem}",
            source_hint="linpeas",
            text=p.read_text(encoding="utf-8"),
            origin=str(p.relative_to(REPO_ROOT)),
        ))

    # 3) ASPM CSV — one text per row (each alert is a record).
    aspm_dir = RAW_DIR / "aspm"
    for p in sorted(aspm_dir.glob("*.csv")):
        content = p.read_text(encoding="utf-8")
        reader = list(csv.reader(io.StringIO(content)))
        if not reader:
            continue
        header = reader[0]
        for i, row in enumerate(reader[1:], start=1):
            if not any(cell.strip() for cell in row):
                continue
            block = _csv_row_to_block(header, row)
            texts.append(CorpusText(
                doc_id=f"aspm__{p.stem}__row{i}",
                source_hint="aspm",
                text=block,
                origin=f"{p.relative_to(REPO_ROOT)}#row{i}",
            ))

    return texts
