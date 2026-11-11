"""CLI for the Part 2 Step 3 RAG answerer.

    python3 main.py --ask "How should least privilege be enforced for IAM roles?"
    python3 main.py --ask "What is CVE-2021-4034?" --model ollama --k 8
    python3 main.py --ask "..." --doc-types cve,best_practice --prompt v1

Prints the answer, whether it was found, the cited sources (doc + section), and
the full retrieval list. Routes through the shared model adapters so the same
question can be answered by Gemini or Ollama for comparison.
"""

from __future__ import annotations

import argparse

from src.rag.answer import RagAnswerer


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ask the RAG system a question (Step 3)")
    ap.add_argument("question", nargs="+", help="the question to answer")
    ap.add_argument("--model", default="gemini", choices=["gemini", "ollama"])
    ap.add_argument("--prompt", default="v1", help="rag_answer prompt version")
    ap.add_argument("--sampling", default="deterministic", choices=["deterministic", "sampled"])
    ap.add_argument("--k", type=int, default=5, help="chunks to retrieve")
    ap.add_argument("--doc-types", default=None,
                    help="comma-separated doc_type filter (e.g. cve,best_practice)")
    args = ap.parse_args(argv)

    question = " ".join(args.question)
    doc_types = args.doc_types.split(",") if args.doc_types else None

    answerer = RagAnswerer(model=args.model, prompt_version=args.prompt,
                           sampling=args.sampling, k=args.k)
    ans = answerer.answer(question, doc_types=doc_types)

    print(f"\nQ: {question}")
    print(f"model={ans.model} prompt={ans.prompt_version} sampling={ans.sampling} "
          f"found={ans.found}")
    if ans.error:
        print(f"[error: {ans.error}]")
    print(f"\n{ans.answer}\n")
    if ans.citations:
        print("Cited sources:")
        cited = {s["label"]: s for s in ans.sources}
        for label in ans.citations:
            s = cited.get(label, {})
            sec = f" — {s.get('section')}" if s.get("section") else ""
            print(f"  [{label}] {s.get('source', '?')}{sec}")
    if ans.dropped_citations:
        print(f"\n(dropped invented citations: {', '.join(ans.dropped_citations)})")
    if ans.latency_seconds is not None:
        print(f"\nlatency: {ans.latency_seconds:.1f}s | "
              f"tokens in/out: {ans.input_tokens}/{ans.output_tokens}")
    print(f"retrieved: {', '.join(ans.retrieved)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
