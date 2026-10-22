"""
Module entry point so `python -m src.main` works too (used by the Makefile).
The real logic lives in src/runner.py; main.py at the repo root is the primary,
documented entry point (`python3 main.py`).
"""

from __future__ import annotations

from src.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
