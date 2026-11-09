"""Offline tests for the Part 2 Step 1 chunker (`src/rag/chunk.py`).

No network, no model: pure text in -> chunks out. Protects the graded
invariants of structure-aware chunking vs the fixed-size baseline.
"""

from src.rag.chunk import (
    CHUNK_MAX_TOKENS,
    chunk_fixed,
    chunk_stats,
    chunk_structure_aware,
    n_tokens,
)

DOC = """# Access Control

Least privilege means every identity gets only the permissions it needs.
Review entitlements quarterly and remove unused grants.

## Encryption

Enable encryption at rest for all volumes holding sensitive data.

| Control | Requirement | Owner |
| --- | --- | --- |
| EBS encryption | Enabled by default | Platform |
| S3 SSE | KMS-managed keys | Data |

# Logging

Centralize logs and retain them per the applicable standard.
"""


def test_structure_aware_sets_section_paths():
    chunks = chunk_structure_aware(DOC)
    assert chunks
    sections = {c.section for c in chunks}
    # Nested heading produces a "Parent > Child" path.
    assert any(s == "Access Control" for s in sections)
    assert any(s == "Access Control > Encryption" for s in sections)
    assert any(s == "Logging" for s in sections)


def test_structure_aware_keeps_table_rows_whole():
    chunks = chunk_structure_aware(DOC)
    # Every markdown table row that appears must appear as a complete `| … |`
    # line in some chunk — never split across the `|`.
    table_rows = [
        "| EBS encryption | Enabled by default | Platform |",
        "| S3 SSE | KMS-managed keys | Data |",
    ]
    joined = "\n".join(c.text for c in chunks)
    for row in table_rows:
        assert row in joined


def test_fixed_has_no_sections_structure_does():
    fixed = chunk_fixed(DOC)
    structure = chunk_structure_aware(DOC)
    assert all(c.section == "" for c in fixed)
    assert any(c.section for c in structure)


def test_size_cap_enforced_on_prose():
    # A single huge paragraph (no headings, no blank lines) must still be split
    # below the cap rather than emitted as one giant chunk.
    big = " ".join(f"word{i}" for i in range(5000))
    chunks = chunk_structure_aware(big)
    assert chunks
    assert all(c.n_tokens <= CHUNK_MAX_TOKENS + 1 for c in chunks)


def test_big_table_split_on_row_boundaries():
    # A table larger than the cap is split, but only between rows.
    rows = ["| Control | Requirement | Owner |", "| --- | --- | --- |"]
    rows += [f"| control-{i} | requirement text number {i} here | team-{i} |" for i in range(400)]
    doc = "# Big Table\n\n" + "\n".join(rows)
    chunks = chunk_structure_aware(doc)
    assert len(chunks) > 1  # actually got split
    for c in chunks:
        for line in c.text.strip().split("\n"):
            s = line.strip()
            if s.startswith("|"):
                # A kept row is a complete pipe-delimited row.
                assert s.endswith("|")


def test_chunk_stats_shape():
    stats = chunk_stats(chunk_structure_aware(DOC))
    for key in ("chunks", "starts_mid_sentence", "cut_tables", "avg_tokens",
                "max_tokens", "with_section"):
        assert key in stats
    assert stats["chunks"] == len(chunk_structure_aware(DOC))


def test_empty_input_is_safe():
    assert chunk_structure_aware("") == []
    assert chunk_fixed("") == []
    assert chunk_stats([])["chunks"] == 0
