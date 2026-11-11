#!/usr/bin/env python3
"""
Primary entry point.

Part 1 (extraction) — the comparison grid:

    python3 main.py                         # full grid (all models x prompts x sampling)
    python3 main.py --models gemini         # provider only
    python3 main.py --models ollama --sampling deterministic
    python3 main.py --prompts v1 v2

Part 2 (RAG) — Step 1 ingestion:

    python3 main.py --ingest                # ingest data/corpus + chosen raw -> data/rag/

Part 2 (RAG) — Step 2 retrieval measurement:

    python3 main.py --eval-retrieval        # recall@k / MRR over 3 retrieval modes

Part 2 (RAG) — Step 3 ask (answer with sources):

    python3 main.py --ask "How should least privilege be enforced?"
    python3 main.py --ask "What is CVE-2021-4034?" --model ollama

Writes real, non-fabricated results. A model that is unreachable (no API key /
Ollama not running) produces clearly-marked failed rows, not invented numbers.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src` importable whether run as `python3 main.py` or from elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    # Part 2 RAG ingestion is a separate pipeline from the Part 1 grid; dispatch
    # on --ingest before the extraction runner parses its own flags.
    if "--ingest" in sys.argv:
        sys.argv.remove("--ingest")
        from src.rag.ingest import main as ingest_main

        raise SystemExit(ingest_main())

    if "--eval-retrieval" in sys.argv:
        sys.argv.remove("--eval-retrieval")
        from src.rag.eval_retrieval import main as eval_retrieval_main

        raise SystemExit(eval_retrieval_main())

    if "--ask" in sys.argv:
        sys.argv.remove("--ask")
        from src.rag.ask import main as ask_main

        raise SystemExit(ask_main())

    if "--evals" in sys.argv:
        sys.argv.remove("--evals")
        from evals.run_evals import main as evals_main

        raise SystemExit(evals_main())

    from src.runner import main  # noqa: E402

    raise SystemExit(main())
