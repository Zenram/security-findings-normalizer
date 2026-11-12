"""Part 2 Step 1 — ingest the RAG corpus into clean, deduplicated chunks.

Pipeline:  discover sources -> extract text (per format) -> normalize/clean ->
content-hash dedup -> chunk (structure-aware for prose, record-as-chunk for CSV)
-> attach metadata -> write chunks.jsonl + ingest_manifest.json + a comparison
report.

Scope (locked in hm2_plan §3 / DEV_HANDOFF2 §4): 51 source files across 5 formats

    doc_type          location                          format
    ---------------   -------------------------------   ------
    standard          data/corpus/standard/             PDF, MD
    best_practice     data/corpus/best_practice/        PDF, HTML
    cve               data/corpus/cve/                  MD
    team_report       data/raw/team_reports/            TXT
    scanner_linpeas   data/raw/oss_scanner/linpeas/      TXT
    alert_aspm        data/raw/aspm/                     CSV (row = finding)
    alert_cnapp       data/raw/cnapp/                    CSV (row = finding)

Run:
    python3 main.py --ingest            # ingest -> data/rag/
    python3 -m src.rag.ingest           # same, module entry

Output (data/rag/, gitignored like other run artifacts):
    chunks.jsonl            one JSON object per chunk (the index input for Step 2)
    ingest_manifest.json    per-file record: doc_type, format, hashes, #chunks, status
    ingest_report.json      summary + fixed-vs-structure chunking comparison
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from pypdf import PdfReader

from src.config import REPO_ROOT
from src.rag.chunk import (
    Chunk,
    chunk_fixed,
    chunk_stats,
    chunk_structure_aware,
    n_tokens,
)

PIPELINE_VERSION = "rag-ingest-v1"

CORPUS_DIR = REPO_ROOT / "data" / "corpus"
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_DIR = REPO_ROOT / "data" / "rag"

# A PDF page with fewer usable chars than this has no real text layer -> flag for OCR.
MIN_CHARS_PER_PAGE = 50


# --- Source registry ---------------------------------------------------------
# CSV doc_types are chunked row-per-record; everything else is prose.

@dataclass(frozen=True)
class SourceSet:
    doc_type: str
    base: Path
    pattern: str
    is_csv: bool = False


SOURCE_SETS: list[SourceSet] = [
    SourceSet("standard",        CORPUS_DIR / "standard",            "*"),
    SourceSet("best_practice",   CORPUS_DIR / "best_practice",       "*"),
    SourceSet("cve",             CORPUS_DIR / "cve",                 "*.md"),
    SourceSet("team_report",     RAW_DIR / "team_reports",           "*.txt"),
    SourceSet("scanner_linpeas", RAW_DIR / "oss_scanner" / "linpeas", "*.txt"),
    SourceSet("alert_aspm",      RAW_DIR / "aspm",                   "*.csv", is_csv=True),
    SourceSet("alert_cnapp",     RAW_DIR / "cnapp",                  "*.csv", is_csv=True),
]


@dataclass
class Doc:
    source: str                 # path relative to repo root
    doc_type: str
    fmt: str                    # pdf | html | md | txt | csv
    raw_hash: str               # sha256 of file bytes
    title: str = ""
    text: str = ""              # normalized full text (prose docs)
    status: str = "ok"          # ok | ocr_required | exact_duplicate | error
    note: str = ""
    doc_hash: str = ""          # sha256 of normalized content (dedup key)
    chunks: list[Chunk] = field(default_factory=list)


# ---------------------------------------------------------------- extract

def _decode_bytes(data: bytes) -> str:
    """Decode unknown-encoding text robustly (LinPEAS/reports may not be UTF-8)."""
    best = from_bytes(data).best()
    text = str(best) if best is not None else data.decode("utf-8", errors="replace")
    return text.lstrip("\ufeff")


def extract_text_file(path: Path) -> str:
    return _decode_bytes(path.read_bytes())


def extract_markdown(path: Path) -> str:
    # Markdown is already structured text; keep as-is (decode-safe).
    return _decode_bytes(path.read_bytes())


def extract_html(path: Path) -> str:
    """Keep the article; drop nav/scripts/styles/cookie banners/footers. Convert
    headings to Markdown '#' so the structure-aware chunker can see sections, and
    list items to '- ' lines."""
    soup = BeautifulSoup(_decode_bytes(path.read_bytes()), "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer",
                     "form", "svg", "iframe", "aside"]):
        tag.decompose()
    # Drop obvious cookie/consent/banner containers by id/class hints.
    for el in soup.find_all(attrs={"class": re.compile(r"cookie|consent|banner|nav|menu|footer", re.I)}):
        el.decompose()
    for el in soup.find_all(attrs={"id": re.compile(r"cookie|consent|banner|nav|menu|footer", re.I)}):
        el.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    parts: list[str] = []
    for el in root.descendants:
        name = getattr(el, "name", None)
        if name is None:
            continue
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(name[1])
            txt = el.get_text(" ", strip=True)
            if txt:
                parts.append(f"\n{'#' * level} {txt}\n")
        elif name == "li":
            txt = el.get_text(" ", strip=True)
            if txt:
                parts.append(f"- {txt}")
        elif name == "p":
            txt = el.get_text(" ", strip=True)
            if txt:
                parts.append(txt)
    if not parts:  # fallback: flat text
        parts = [root.get_text("\n", strip=True)]
    return "\n".join(parts)


def extract_pdf(path: Path) -> tuple[str, bool]:
    """Return (text, needs_ocr). Pages joined with form-feed so the normalizer
    can strip repeating headers/footers per page."""
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\f".join(pages)
    usable = len(re.sub(r"\s", "", text))
    needs_ocr = usable < MIN_CHARS_PER_PAGE * max(1, len(pages))
    return text, needs_ocr


def extract(path: Path, fmt: str) -> tuple[str, bool]:
    if fmt == "pdf":
        return extract_pdf(path)
    if fmt in ("html", "htm"):
        return extract_html(path), False
    if fmt == "md":
        return extract_markdown(path), False
    if fmt == "txt":
        return extract_text_file(path), False
    raise ValueError(f"unsupported prose format: {fmt}")


# ---------------------------------------------------------------- normalize

_PAGE_NUMBER = re.compile(r"^\s*(page\s+)?\d+\s*(of|/)\s*\d+\s*$", re.IGNORECASE)
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
# LinPEAS / ANSI terminal noise: escape sequences + decorative banner rules.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_BANNER_RULE = re.compile(r"^\s*[=#\-_*]{6,}\s*$")


def _strip_repeating_lines(pages: list[str]) -> list[str]:
    """Remove lines that repeat on most PDF pages (running headers/footers)."""
    if len(pages) < 3:
        return pages
    from collections import Counter
    counts: Counter[str] = Counter()
    for pg in pages:
        for line in {l.strip() for l in pg.split("\n") if l.strip()}:
            counts[line] += 1
    threshold = max(3, int(len(pages) * 0.6))
    boilerplate = {l for l, c in counts.items() if c >= threshold and len(l) < 120}
    return ["\n".join(l for l in pg.split("\n") if l.strip() not in boilerplate) for pg in pages]


def _dehyphenate(text: str) -> str:
    # "secur-\nity" -> "security"
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def normalize(text: str, fmt: str) -> str:
    """One canonical text form for hashing, dedup and chunking."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _ZERO_WIDTH.sub("", text)
    text = _ANSI.sub("", text)

    if fmt == "pdf" and "\f" in text:
        pages = _strip_repeating_lines(text.split("\f"))
        text = "\n".join(pages)

    text = _dehyphenate(text)

    out_lines: list[str] = []
    for line in text.split("\n"):
        line = line.rstrip()
        if _PAGE_NUMBER.match(line):
            continue
        if _BANNER_RULE.match(line):
            continue
        line = re.sub(r"[ \t]{2,}", " ", line)
        out_lines.append(line)
    text = "\n".join(out_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)      # at most one blank line
    return text.strip()


# ---------------------------------------------------------------- dedup

def content_hash(text: str) -> str:
    """Hash a whitespace-canonical form so trivial spacing differences collapse."""
    canonical = re.sub(r"\s+", " ", text).strip().casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- CSV rows

def _csv_row_to_text(header: list[str], row: list[str]) -> str:
    """Render one alert row as a readable 'Field: value' block (record-as-chunk).
    Empty cells are dropped so the chunk is not padded with blanks."""
    lines = []
    for key, val in zip(header, row):
        if val is not None and str(val).strip():
            lines.append(f"{key}: {str(val).strip()}")
    return "\n".join(lines)


def _csv_title(header: list[str], row: list[str]) -> str:
    """Pick a human title for a CSV alert row: prefer an Issue Name / Title
    column, else the first non-empty cell."""
    hl = [h.strip().lower() for h in header]
    for want in ("issue name", "title", "name"):
        if want in hl:
            v = row[hl.index(want)].strip()
            if v:
                return v[:120]
    for v in row:
        if v.strip():
            return v.strip()[:120]
    return "row"


# ---------------------------------------------------------------- titles

def _title_of(doc: Doc) -> str:
    for line in doc.text.splitlines():
        s = line.strip()
        if s:
            return s.lstrip("#").strip()[:120]
    return Path(doc.source).stem


def _pdf_title(path: Path) -> str:
    try:
        meta = PdfReader(str(path)).metadata
        return (meta.title or "").strip()[:120] if meta else ""
    except Exception:
        return ""


# ---------------------------------------------------------------- discovery

def _fmt_of(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def discover() -> list[tuple[Path, str, str]]:
    """Return (path, doc_type, fmt) for every in-scope source file, skipping
    manifest/list sidecar files."""
    found: list[tuple[Path, str, str]] = []
    skip_names = {"manifest.json", "cve_list.txt"}
    for ss in SOURCE_SETS:
        if not ss.base.exists():
            continue
        for p in sorted(ss.base.glob(ss.pattern)):
            if not p.is_file() or p.name.startswith(".") or p.name in skip_names:
                continue
            found.append((p, ss.doc_type, _fmt_of(p)))
    return found


# ---------------------------------------------------------------- pipeline

def _chunk_records(doc: Doc, now: str) -> list[dict]:
    """Serialize a doc's chunks to the flat JSONL records Step 2 will index."""
    records = []
    for c in doc.chunks:
        records.append({
            "chunk_id": f"{doc.source}#{c.chunk_index}",
            "source": doc.source,
            "doc_type": doc.doc_type,
            "format": doc.fmt,
            "title": doc.title,
            "section": c.section,
            "doc_hash": doc.doc_hash,
            "chunk_index": c.chunk_index,
            "n_tokens": c.n_tokens,
            "strategy": c.strategy,
            "pipeline_version": PIPELINE_VERSION,
            "ingested_at": now,
            "text": c.text,
        })
    return records


def run() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    docs: list[Doc] = []
    # Accumulate prose chunks under both strategies for the fixed-vs-structure
    # comparison (CSV records excluded — not windowed).
    fixed_all: list[Chunk] = []
    structure_all: list[Chunk] = []

    for path, doc_type, fmt in discover():
        source = path.relative_to(REPO_ROOT).as_posix()
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        # ---- CSV: one record (row) -> one chunk ----
        if fmt == "csv":
            try:
                content = _decode_bytes(path.read_bytes())
                rows = list(csv.reader(content.splitlines()))
            except Exception as e:
                docs.append(Doc(source=source, doc_type=doc_type, fmt=fmt,
                                raw_hash=raw_hash, status="error",
                                note=f"{type(e).__name__}: {e}"))
                continue
            if not rows:
                continue
            header = rows[0]
            doc = Doc(source=source, doc_type=doc_type, fmt=fmt, raw_hash=raw_hash,
                      title=path.stem)
            seen_rows: set[str] = set()
            idx = 0
            for r_i, row in enumerate(rows[1:], start=1):
                if not any(str(c).strip() for c in row):
                    continue
                rec_text = _csv_row_to_text(header, row)
                rh = content_hash(rec_text)
                if rh in seen_rows:           # dedup identical rows within a file
                    continue
                seen_rows.add(rh)
                doc.chunks.append(Chunk(
                    text=rec_text,
                    section=_csv_title(header, row),
                    chunk_index=idx,
                    n_tokens=n_tokens(rec_text),
                    strategy="record",
                ))
                idx += 1
            doc.doc_hash = content_hash("\n".join(c.text for c in doc.chunks))
            docs.append(doc)
            continue

        # ---- prose: pdf / html / md / txt ----
        doc = Doc(source=source, doc_type=doc_type, fmt=fmt, raw_hash=raw_hash)
        try:
            raw_text, needs_ocr = extract(path, fmt)
        except Exception as e:
            doc.status, doc.note = "error", f"{type(e).__name__}: {e}"
            docs.append(doc)
            continue
        if needs_ocr:
            doc.status = "ocr_required"
            doc.note = "no usable text layer (scanned PDF): route to OCR, not the index"
            docs.append(doc)
            continue
        doc.text = normalize(raw_text, fmt)
        doc.doc_hash = content_hash(doc.text)
        doc.title = (_pdf_title(path) if fmt == "pdf" else "") or _title_of(doc)
        docs.append(doc)

    # ---- cross-file exact dedup (prose only; CSV handled per-row above) ----
    seen: dict[str, Doc] = {}
    for doc in docs:
        if doc.status != "ok" or doc.fmt == "csv":
            continue
        if doc.doc_hash in seen:
            doc.status = "exact_duplicate"
            doc.note = f"same content as {seen[doc.doc_hash].source}"
        else:
            seen[doc.doc_hash] = doc

    # ---- chunk prose docs (both strategies for the comparison) ----
    for doc in docs:
        if doc.status != "ok" or doc.fmt == "csv":
            continue
        structure_chunks = chunk_structure_aware(doc.text)
        doc.chunks = structure_chunks
        structure_all.extend(structure_chunks)
        fixed_all.extend(chunk_fixed(doc.text))

    # ---- write chunks.jsonl ----
    all_records: list[dict] = []
    for doc in docs:
        if doc.status in ("ok",) and doc.chunks:
            all_records.extend(_chunk_records(doc, now))
    with (OUT_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- manifest (per file) ----
    manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "generated": now,
        "files": [
            {
                "source": d.source,
                "doc_type": d.doc_type,
                "format": d.fmt,
                "title": d.title,
                "status": d.status,
                "note": d.note,
                "raw_hash": d.raw_hash,
                "doc_hash": d.doc_hash,
                "chunks": len(d.chunks) if d.status == "ok" else 0,
            }
            for d in docs
        ],
    }
    (OUT_DIR / "ingest_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- report (summary + chunking comparison) ----
    by_type: dict[str, dict[str, int]] = {}
    for d in docs:
        t = by_type.setdefault(d.doc_type, {"files": 0, "chunks": 0})
        t["files"] += 1
        if d.status == "ok":
            t["chunks"] += len(d.chunks)

    record_chunks = sum(len(d.chunks) for d in docs if d.fmt == "csv" and d.status == "ok")
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "generated": now,
        "totals": {
            "files": len(docs),
            "ok": sum(1 for d in docs if d.status == "ok"),
            "exact_duplicate": sum(1 for d in docs if d.status == "exact_duplicate"),
            "ocr_required": sum(1 for d in docs if d.status == "ocr_required"),
            "error": sum(1 for d in docs if d.status == "error"),
            "chunks": len(all_records),
            "prose_chunks": len(all_records) - record_chunks,
            "record_chunks": record_chunks,
        },
        "by_doc_type": by_type,
        "formats": sorted({d.fmt for d in docs}),
        # The graded comparison: structure-aware vs fixed-size baseline (same prose docs).
        "chunking_comparison": {
            "structure_aware": chunk_stats(structure_all),
            "fixed_size": chunk_stats(fixed_all),
        },
    }
    (OUT_DIR / "ingest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def print_report(report: dict) -> None:
    t = report["totals"]
    print(f"\nIngest {report['pipeline_version']}  ({report['generated']})")
    print(f"  files {t['files']} | ok {t['ok']} | dup {t['exact_duplicate']} | "
          f"ocr {t['ocr_required']} | error {t['error']}")
    print(f"  chunks {t['chunks']}  (prose {t['prose_chunks']} + records {t['record_chunks']})")
    print(f"  formats: {', '.join(report['formats'])}")
    print("\n  by doc_type        files  chunks")
    for dt, c in report["by_doc_type"].items():
        print(f"    {dt:<16} {c['files']:>5} {c['chunks']:>7}")
    comp = report["chunking_comparison"]
    print("\n  chunking (prose)   chunks  mid-sentence  cut-tables  avg-tok  max-tok  w/section")
    for name, key in (("structure-aware", "structure_aware"), ("fixed 512/64", "fixed_size")):
        s = comp[key]
        print(f"    {name:<16} {s['chunks']:>6} {s['starts_mid_sentence']:>13} "
              f"{s['cut_tables']:>11} {s['avg_tokens']:>8} {s['max_tokens']:>8} {s['with_section']:>10}")
    print(f"\n  -> data/rag/chunks.jsonl, ingest_manifest.json, ingest_report.json\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RAG corpus ingestion (Part 2 Step 1)")
    ap.parse_args(argv)
    if not CORPUS_DIR.exists():
        sys.exit(f"no corpus dir {CORPUS_DIR} — run scripts/fetch_corpus.py first")
    print_report(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
