#!/usr/bin/env python3
"""
Primary entry point. Run the full Stage 1 comparison:

    python3 main.py                         # full grid (all models x v1 x both sampling)
    python3 main.py --models gemini         # provider only
    python3 main.py --models ollama --sampling deterministic
    python3 main.py --prompts v1 v2         # once v2 exists

Writes real, non-fabricated results to results/. A model that is unreachable
(no API key / Ollama not running) produces clearly-marked failed rows, not
invented numbers.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src` importable whether run as `python3 main.py` or from elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.runner import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
