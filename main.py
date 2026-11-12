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

TOP_LEVEL_HELP = """\
Security Findings Normalizer — unified entry point.

USAGE
  python3 main.py [COMMAND] [OPTIONS]        (or: make <target>)

With no command, runs the Part 1 extraction grid.

PART 1 — Extraction
  (default)              Full grid: {gemini,ollama} x {v1,v2,v3} x {deterministic,sampled}
    --models M [M ...]   Limit models: gemini and/or ollama
    --prompts V [V ...]  Limit prompt versions: v1 v2 v3
    --sampling S [S ...] Limit sampling: deterministic sampled
    --corpus             Also process the full unlabeled raw corpus
    --corpus-only        Only process the raw corpus (skip the grid)
    --rescore            Recompute metrics from results/raw/ (no model calls, free)

PART 2 — RAG
  --ingest               Ingest the corpus -> data/rag/chunks.jsonl + manifest + report
  --eval-retrieval       Measure retrieval: recall@k / MRR over 3 modes (free)
  --ask "QUESTION"       Answer one question with cited sources / honest "I don't know"
      [--model gemini|ollama] [--doc-types cve,best_practice] [--k N]
      [--prompt v1] [--sampling deterministic]
  --evals                Run the eval harness over the testset
      [--lint]           Validate the testset only — no model calls (free)
      [--judge]          Add LLM judge + faithfulness (paid)
      [--calibrate]      Report judge-vs-human agreement
      [--save-baseline]  Write evals/baseline.json from this run
      [--gate]           Exit non-zero if metrics drop below baseline (CI)

COMMON
  -h, --help             Show this overview and exit
  Each command also has its own --help, e.g.:
      python3 main.py --ask --help
      python3 main.py --evals --help

Keys live in .env only (never in source). Python 3.13 required for Part 2.
Quickstarts: QUICKSTART_PART1.md, QUICKSTART_PART2.md. Results: REPORT_PART1.md,
REPORT_PART2.md.
"""


def _wants_top_level_help(argv: list[str]) -> bool:
    """True when the user asked for help WITHOUT selecting a sub-command (so a
    sub-command's own --help still works, e.g. `--ask --help`)."""
    subcommands = {"--ingest", "--eval-retrieval", "--ask", "--evals"}
    has_help = "-h" in argv or "--help" in argv
    has_subcommand = any(a in subcommands for a in argv)
    return has_help and not has_subcommand


if __name__ == "__main__":
    if _wants_top_level_help(sys.argv[1:]):
        print(TOP_LEVEL_HELP)
        raise SystemExit(0)

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
