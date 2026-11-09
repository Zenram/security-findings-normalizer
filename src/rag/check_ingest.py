"""Sanity checks for the RAG ingest output (Part 2 Step 1).

Not a model eval — a structural self-check that the ingest produced a well-formed
index input: expected scope, every chunk has the metadata Step 2 needs, no
oversized chunks, the two chunking strategies were both measured, and CSV rows
became record chunks. Run AFTER `python3 main.py --ingest`:

    python3 -m src.rag.check_ingest
"""

from __future__ import annotations

import json
import sys

from src.config import REPO_ROOT
from src.rag.chunk import CHUNK_MAX_TOKENS
from src.rag.ingest import SOURCE_SETS

OUT = REPO_ROOT / "data" / "rag"

REQUIRED_FIELDS = [
    "chunk_id", "source", "doc_type", "format", "title", "section",
    "doc_hash", "chunk_index", "n_tokens", "strategy", "pipeline_version", "text",
]
EXPECTED_DOC_TYPES = {ss.doc_type for ss in SOURCE_SETS}
# A little headroom over the cap for the block-level overlap seed.
MAX_TOKENS_ALLOWED = CHUNK_MAX_TOKENS * 2


def main() -> int:
    if not (OUT / "chunks.jsonl").exists():
        sys.exit("no data/rag/chunks.jsonl — run `python3 main.py --ingest` first")

    chunks = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l]
    report = json.loads((OUT / "ingest_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUT / "ingest_manifest.json").read_text(encoding="utf-8"))

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    # 1. Scope: all 51 source files ingested, no errors.
    files = manifest["files"]
    check("51 source files in manifest", len(files) == 51, f"got {len(files)}")
    errors = [f["source"] for f in files if f["status"] == "error"]
    check("no extraction errors", not errors, f"errors: {errors[:3]}")

    # 2. Formats: all 5 expected formats present.
    check("5 formats present (pdf/html/md/txt/csv)",
          set(report["formats"]) >= {"pdf", "html", "md", "txt", "csv"},
          f"got {report['formats']}")

    # 3. doc_type coverage: every expected type produced chunks.
    present = {c["doc_type"] for c in chunks}
    missing = EXPECTED_DOC_TYPES - present
    check("all 7 doc_types produced chunks", not missing, f"missing: {missing}")

    # 4. Metadata completeness on every chunk.
    bad = sorted({f for c in chunks for f in REQUIRED_FIELDS if f not in c})
    check("every chunk has required metadata fields", not bad, f"missing: {bad}")

    # 5. Non-empty text everywhere.
    empties = sum(1 for c in chunks if not c["text"].strip())
    check("no empty chunks", empties == 0, f"{empties} empty")

    # 6. Size cap enforced on windowed prose (records are atomic and exempt:
    #    an alert row is never split, so a long alert may exceed the cap).
    oversized = [c["chunk_id"] for c in chunks
                 if c["strategy"] != "record" and c["n_tokens"] > MAX_TOKENS_ALLOWED]
    check(f"no prose chunk over {MAX_TOKENS_ALLOWED} tokens", not oversized,
          f"{len(oversized)} oversized, e.g. {oversized[:2]}")

    # 7. CSV rows became record chunks.
    record = [c for c in chunks if c["strategy"] == "record"]
    check("CSV rows chunked as records", len(record) > 0, f"{len(record)} record chunks")

    # 8. Chunking comparison present (both strategies measured).
    comp = report.get("chunking_comparison", {})
    have_both = "structure_aware" in comp and "fixed_size" in comp and \
        comp["structure_aware"]["chunks"] > 0 and comp["fixed_size"]["chunks"] > 0
    check("fixed-vs-structure comparison measured", have_both)

    # 9. Structure-aware keeps sections; fixed-size does not.
    check("structure-aware keeps section paths, fixed does not",
          comp.get("structure_aware", {}).get("with_section", 0) > 0 and
          comp.get("fixed_size", {}).get("with_section", 1) == 0)

    # 10. Unique chunk ids.
    ids = [c["chunk_id"] for c in chunks]
    check("chunk_ids are unique", len(ids) == len(set(ids)),
          f"{len(ids) - len(set(ids))} duplicate ids")

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok or not detail else f"  ({detail})"))
    print(f"\n{passed}/{len(checks)} checks passed  |  {len(chunks)} chunks over {len(files)} files")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
