"""Chunking for Part 2 Step 1.

Two strategies, so the README can show the required comparison (RD2 / grading):

1. `chunk_structure_aware` — the production chunker for PROSE documents
   (standards, best-practice guides, CVE advisories, team reports). It splits on
   Markdown-style headings into sections, then packs whole blocks (paragraphs,
   list groups, table blocks) up to a token cap with a small overlap. A table
   block or a paragraph is never cut in the middle, and every chunk carries its
   section path (e.g. "Access Control > Least Privilege").

2. `chunk_fixed` — the fixed-size baseline (sliding token window with overlap).
   Simple, but it cuts sentences, tables and sections. We run it only to MEASURE
   the cost of naive chunking (mid-sentence starts, cut tables) and justify the
   structure-aware choice.

CSV rows are NOT chunked here: each alert row is already one atomic record and is
emitted as a single chunk by the ingest pipeline (record-as-chunk, RD2).

Token counting uses tiktoken's `cl100k_base` (a stable, API-free tokenizer); it
is only a length heuristic for sizing, not tied to any specific model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

# --- Tunables ----------------------------------------------------------------
# Security docs are dense and table-heavy; 512 tokens keeps a control/section
# mostly whole while staying well under any embedding model's input window.
CHUNK_MAX_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64          # overlap carried between packed chunks
FIXED_SIZE_TOKENS = 512            # baseline window (same cap, for a fair compare)
FIXED_OVERLAP_TOKENS = 64

_ENC = tiktoken.get_encoding("cl100k_base")

# A Markdown heading ("## Section") or a short numbered title ("3. Eligibility").
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_NUM_TITLE_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+([A-Z].{0,80})$")


def n_tokens(text: str) -> int:
    """Token count under cl100k_base. Used for sizing only."""
    return len(_ENC.encode(text))


@dataclass
class Chunk:
    """One retrievable unit. `section` is the heading path; `strategy` records
    which chunker produced it so the comparison table can separate the two."""

    text: str
    section: str          # "Parent > Child" heading path, or "" at the top level
    chunk_index: int
    n_tokens: int
    strategy: str         # "structure" | "fixed" | "record"


# --- Block splitting ---------------------------------------------------------

def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _heading_of(line: str) -> tuple[int, str] | None:
    """Return (level, title) if `line` is a heading, else None.

    Markdown '#' headings use their '#' count as the level. A short numbered
    title like "2. Eligibility" is treated as a level-2 heading. A numbered list
    item ("1. Open the console.") is a sentence, not a heading, so it is excluded
    (ends with punctuation / is long)."""
    m = _HEADING_RE.match(line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    s = line.strip()
    m = _NUM_TITLE_RE.match(s)
    if m and not s.endswith((".", ":", ";")) and len(s) < 80:
        depth = s.split()[0].count(".") + 1
        return min(depth, 6), m.group(2).strip()
    return None


def _split_blocks(text: str) -> list[str]:
    """Split prose into atomic blocks: paragraphs (blank-line separated), with
    consecutive table rows glued into one table block so a table is never torn
    apart across blocks."""
    raw_blocks = re.split(r"\n\s*\n", text)
    blocks: list[str] = []
    for rb in raw_blocks:
        rb = rb.strip("\n")
        if not rb.strip():
            continue
        # Glue runs of table lines together; keep non-table runs as-is.
        lines = rb.split("\n")
        buf: list[str] = []
        table_buf: list[str] = []
        for line in lines:
            if _is_table_line(line):
                if buf:
                    blocks.append("\n".join(buf)); buf = []
                table_buf.append(line)
            else:
                if table_buf:
                    blocks.append("\n".join(table_buf)); table_buf = []
                buf.append(line)
        if table_buf:
            blocks.append("\n".join(table_buf))
        if buf:
            blocks.append("\n".join(buf))
    return blocks


# --- Structure-aware chunker -------------------------------------------------

def _is_table_block(block: str) -> bool:
    lines = [l for l in block.split("\n") if l.strip()]
    return bool(lines) and all(_is_table_line(l) for l in lines)


def _split_oversized_block(block: str, max_tokens: int) -> list[str]:
    """Split a single block that is itself larger than the cap.

    - A table block is split on ROW boundaries (each piece keeps whole rows), so
      a table row is never torn in half.
    - Any other block falls back to a token window (hard cap enforcement). This
      only triggers for pathological single blocks (e.g. a PDF page extracted as
      one unbroken run of text) — the common path never reaches it.
    """
    if n_tokens(block) <= max_tokens:
        return [block]

    if _is_table_block(block):
        rows = [l for l in block.split("\n") if l.strip()]
        pieces: list[str] = []
        cur: list[str] = []
        cur_tokens = 0
        for row in rows:
            rt = n_tokens(row)
            if cur and cur_tokens + rt > max_tokens:
                pieces.append("\n".join(cur))
                cur, cur_tokens = [], 0
            cur.append(row)
            cur_tokens += rt
        if cur:
            pieces.append("\n".join(cur))
        return pieces

    # Prose fallback: token window over the single block.
    toks = _ENC.encode(block)
    pieces = []
    for start in range(0, len(toks), max_tokens):
        piece = _ENC.decode(toks[start:start + max_tokens]).strip()
        if piece:
            pieces.append(piece)
    return pieces


def _pack(blocks: list[str], section: str, start_index: int,
          max_tokens: int, overlap_tokens: int) -> list[Chunk]:
    """Pack whole blocks into chunks up to `max_tokens`, carrying `overlap_tokens`
    of trailing text from the previous chunk for context continuity. A single
    block larger than the cap is first split on safe boundaries (table rows, or a
    token window for pathological prose) so no chunk exceeds the cap."""
    chunks: list[Chunk] = []
    cur: list[str] = []
    cur_tokens = 0
    idx = start_index
    prev_blocks: list[str] = []   # the blocks that went into the last flushed chunk

    def flush() -> None:
        nonlocal cur, cur_tokens, idx, prev_blocks
        if not cur:
            return
        body = "\n\n".join(cur).strip()
        if body:
            chunks.append(Chunk(text=body, section=section, chunk_index=idx,
                                n_tokens=n_tokens(body), strategy="structure"))
            idx += 1
            prev_blocks = cur.copy()

    def overlap_seed() -> tuple[list[str], int]:
        """Block-level overlap: carry the LAST whole block of the previous chunk
        forward if it fits in the overlap budget. Block-level (never mid-token)
        so every chunk still starts at a real block boundary — keeps sentences
        and table rows intact."""
        if not overlap_tokens or not prev_blocks:
            return [], 0
        last = prev_blocks[-1]
        if n_tokens(last) <= overlap_tokens:
            return [last], n_tokens(last)
        return [], 0

    for block in blocks:
        for piece in _split_oversized_block(block, max_tokens):
            bt = n_tokens(piece)
            if cur and cur_tokens + bt > max_tokens:
                flush()
                cur, cur_tokens = overlap_seed()
            cur.append(piece)
            cur_tokens += bt
    flush()
    return chunks


def chunk_structure_aware(text: str, max_tokens: int = CHUNK_MAX_TOKENS,
                          overlap_tokens: int = CHUNK_OVERLAP_TOKENS) -> list[Chunk]:
    """Split on headings into sections, then pack whole blocks per section.

    Each chunk keeps its heading path in `section`. Headings that nest (## under
    #) produce a "Parent > Child" path."""
    lines = text.split("\n")
    sections: list[tuple[str, list[str]]] = []   # (section_path, body_lines)
    path: list[tuple[int, str]] = []             # stack of (level, title)
    body: list[str] = []

    def section_path() -> str:
        return " > ".join(title for _, title in path)

    def close_section() -> None:
        if any(l.strip() for l in body):
            sections.append((section_path(), body.copy()))

    for line in lines:
        h = _heading_of(line)
        if h is not None:
            close_section()
            body = []
            level, title = h
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, title))
        else:
            body.append(line)
    close_section()

    # A document with no headings at all: one implicit top-level section.
    if not sections:
        sections = [("", lines)]

    chunks: list[Chunk] = []
    running_index = 0
    for sec_path, sec_lines in sections:
        blocks = _split_blocks("\n".join(sec_lines))
        if not blocks:
            continue
        packed = _pack(blocks, sec_path, running_index, max_tokens, overlap_tokens)
        chunks.extend(packed)
        running_index += len(packed)
    return chunks


# --- Fixed-size baseline (for the required comparison) -----------------------

def chunk_fixed(text: str, size: int = FIXED_SIZE_TOKENS,
                overlap: int = FIXED_OVERLAP_TOKENS) -> list[Chunk]:
    """Sliding token window. Ignores structure on purpose — this is the baseline
    we compare against, not the production path."""
    tokens = _ENC.encode(text)
    chunks: list[Chunk] = []
    start = 0
    idx = 0
    step = max(1, size - overlap)
    while start < len(tokens):
        piece = _ENC.decode(tokens[start:start + size]).strip()
        if piece:
            chunks.append(Chunk(text=piece, section="", chunk_index=idx,
                                n_tokens=n_tokens(piece), strategy="fixed"))
            idx += 1
        if start + size >= len(tokens):
            break
        start += step
    return chunks


# --- Quality stats (drives the README comparison) ----------------------------

def chunk_stats(chunks: list[Chunk]) -> dict:
    """Measure the cost of a chunking strategy: how often a chunk starts
    mid-sentence (lowercase first char) or cuts a Markdown table row."""
    if not chunks:
        return {"chunks": 0, "starts_mid_sentence": 0, "cut_tables": 0,
                "avg_tokens": 0, "max_tokens": 0, "with_section": 0}
    mid = sum(1 for c in chunks if c.text[:1].islower())
    cut = 0
    for c in chunks:
        for line in c.text.strip().split("\n"):
            s = line.strip()
            if "|" in s and not (s.startswith("|") and s.endswith("|")):
                cut += 1
                break
    sizes = [c.n_tokens for c in chunks]
    return {
        "chunks": len(chunks),
        "starts_mid_sentence": mid,
        "cut_tables": cut,
        "avg_tokens": round(sum(sizes) / len(sizes)),
        "max_tokens": max(sizes),
        "with_section": sum(1 for c in chunks if c.section),
    }
