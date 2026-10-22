"""
Golden-set loader. Pairs each `NN_input.<ext>` with its `NN_expected.json`
(see data/golden/README.md). The input is the raw text handed to the extractor;
the expected JSON is the hand-labeled list of Finding objects.

Loading does NOT validate the model output — it just provides the ground truth
the evaluator scores against.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import GOLDEN_DIR


@dataclass
class GoldenEntry:
    """One labeled (input, expected) pair."""

    entry_id: str            # "01", "02", ...
    input_path: Path
    expected_path: Path
    input_text: str          # raw text given to the extractor
    expected: list[dict]     # hand-labeled list of findings


def _read_input(path: Path) -> str:
    """Read an input file. JSON inputs (e.g. Trivy 08_input.json) are passed to
    the extractor as their raw text, exactly as a real pipeline would receive
    the file contents."""
    return path.read_text(encoding="utf-8")


def load_golden_set(golden_dir: Path | None = None) -> list[GoldenEntry]:
    """Load all NN_input/NN_expected pairs, sorted by entry id."""
    golden_dir = golden_dir or GOLDEN_DIR
    entries: list[GoldenEntry] = []

    expected_files = sorted(golden_dir.glob("[0-9][0-9]_expected.json"))
    for expected_path in expected_files:
        entry_id = expected_path.name.split("_", 1)[0]
        # Input may be .txt or .json; take the first match for this id.
        input_candidates = sorted(golden_dir.glob(f"{entry_id}_input.*"))
        if not input_candidates:
            raise FileNotFoundError(f"No input file for golden entry {entry_id}")
        input_path = input_candidates[0]

        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if not isinstance(expected, list):
            raise ValueError(f"{expected_path.name} must contain a JSON array")

        entries.append(
            GoldenEntry(
                entry_id=entry_id,
                input_path=input_path,
                expected_path=expected_path,
                input_text=_read_input(input_path),
                expected=expected,
            )
        )
    return entries
