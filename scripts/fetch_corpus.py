#!/usr/bin/env python3
"""Build the HW2 RAG corpus described in hm2_corpus_sources.md.

Layout produced under data/corpus/:
  standard/        2 local MD (copied from data/raw/standarts) + 3 NIST PDFs
  best_practice/   6 NIST PDFs, 2 OWASP PDFs, 7 OWASP Top10 HTML, 2 CISA HTML
  cve/             one Markdown advisory per CVE in data/corpus/cve_list.txt (NVD API)
  manifest.json    per doc: path, doc_type, title, source_url, format, retrieved_date, sha256, bytes
  cve_list.txt     input list of real CVE IDs (already committed)

Usage:
  python scripts/fetch_corpus.py            # download what is missing, rebuild manifest
  python scripts/fetch_corpus.py --force    # re-download everything
  python scripts/fetch_corpus.py --verify   # check files/manifest only, no network
Set NVD_API_KEY to raise the NVD rate limit (without a key: 5 requests / 30 s).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
RAW_STANDARDS = ROOT / "data" / "raw" / "standarts"
MANIFEST = CORPUS / "manifest.json"
CVE_LIST = CORPUS / "cve_list.txt"

USER_AGENT = "Mozilla/5.0 (compatible; hw2-corpus-fetch/1.0)"
NIST = "https://nvlpubs.nist.gov/nistpubs/SpecialPublications"
OWASP_TOP10 = "https://owasp.org/Top10/2021"
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_PAGE = "https://nvd.nist.gov/vuln/detail"

# (doc_type, filename, title, format, source, license)
LOCAL = [
    ("standard", "HIPAA.md", "HIPAA Security — AWS operational best practices", "md", "HIPAA.md", "AWS documentation"),
    ("standard", "SOC2_Guide_on_AWS.md", "AICPA SOC 2 Compliance Guide on AWS", "md", "SOC2_Guide_on_AWS.md", "AWS documentation"),
]
REMOTE = [
    ("standard", "NIST.SP.800-53r5.pdf", "NIST SP 800-53 Rev. 5 — Security & Privacy Controls", "pdf", f"{NIST}/NIST.SP.800-53r5.pdf", "Public domain (NIST)"),
    ("standard", "NIST.SP.800-53B.pdf", "NIST SP 800-53B — Control Baselines", "pdf", f"{NIST}/NIST.SP.800-53B.pdf", "Public domain (NIST)"),
    ("standard", "NIST.SP.800-207.pdf", "NIST SP 800-207 — Zero Trust Architecture", "pdf", f"{NIST}/NIST.SP.800-207.pdf", "Public domain (NIST)"),
    ("best_practice", "NIST.SP.800-190.pdf", "NIST SP 800-190 — Application Container Security Guide", "pdf", f"{NIST}/NIST.SP.800-190.pdf", "Public domain (NIST)"),
    ("best_practice", "NIST.SP.800-61r2.pdf", "NIST SP 800-61 Rev. 2 — Computer Security Incident Handling", "pdf", f"{NIST}/NIST.SP.800-61r2.pdf", "Public domain (NIST)"),
    ("best_practice", "NIST.SP.800-63b.pdf", "NIST SP 800-63B — Authentication & Lifecycle Management", "pdf", f"{NIST}/NIST.SP.800-63b.pdf", "Public domain (NIST)"),
    ("best_practice", "NIST.SP.800-204.pdf", "NIST SP 800-204 — Security for Microservices", "pdf", f"{NIST}/NIST.SP.800-204.pdf", "Public domain (NIST)"),
    ("best_practice", "NIST.SP.800-218.pdf", "NIST SP 800-218 — Secure Software Development Framework", "pdf", f"{NIST}/NIST.SP.800-218.pdf", "Public domain (NIST)"),
    ("best_practice", "NIST.SP.800-92.pdf", "NIST SP 800-92 — Guide to Computer Security Log Management", "pdf", "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-92.pdf", "Public domain (NIST)"),
    ("best_practice", "OWASP_ASVS_4.0.3.pdf", "OWASP ASVS 4.0.3", "pdf", "https://raw.githubusercontent.com/OWASP/ASVS/v4.0.3/4.0/OWASP%20Application%20Security%20Verification%20Standard%204.0.3-en.pdf", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_Testing_Guide_v4.pdf", "OWASP Testing Guide v4", "pdf", "https://owasp.org/www-project-web-security-testing-guide/assets/archive/OWASP_Testing_Guide_v4.pdf", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_Top10_2021_overview.html", "OWASP Top 10:2021 overview", "html", f"{OWASP_TOP10}/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_A01_Broken_Access_Control.html", "OWASP A01:2021 Broken Access Control", "html", f"{OWASP_TOP10}/A01_2021-Broken_Access_Control/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_A02_Cryptographic_Failures.html", "OWASP A02:2021 Cryptographic Failures", "html", f"{OWASP_TOP10}/A02_2021-Cryptographic_Failures/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_A03_Injection.html", "OWASP A03:2021 Injection", "html", f"{OWASP_TOP10}/A03_2021-Injection/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_A05_Security_Misconfiguration.html", "OWASP A05:2021 Security Misconfiguration", "html", f"{OWASP_TOP10}/A05_2021-Security_Misconfiguration/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_A06_Vulnerable_and_Outdated_Components.html", "OWASP A06:2021 Vulnerable and Outdated Components", "html", f"{OWASP_TOP10}/A06_2021-Vulnerable_and_Outdated_Components/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "OWASP_A10_SSRF.html", "OWASP A10:2021 Server-Side Request Forgery (SSRF)", "html", f"{OWASP_TOP10}/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/", "CC BY-SA 4.0 (OWASP)"),
    ("best_practice", "CISA_Kubernetes_Hardening_Guidance.html", "CISA — Kubernetes Hardening Guidance (NSA/CISA)", "html", "https://www.cisa.gov/news-events/alerts/2022/03/15/updated-kubernetes-hardening-guide", "Public domain (CISA)"),
    ("best_practice", "CISA_Secure_by_Design.html", "CISA — Secure by Design", "html", "https://www.cisa.gov/securebydesign", "Public domain (CISA)"),
]

EXPECTED_COUNTS = {"standard": 5, "best_practice": 17, "cve": 10}
MIN_DOCS, MIN_FORMATS = 30, 2


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def http_get(url, headers=None, retries=4):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            retriable = not isinstance(error, urllib.error.HTTPError) or error.code in (403, 429, 500, 502, 503, 504)
            if attempt == retries or not retriable:
                raise
            wait = 10 * attempt
            print(f"  retry {attempt}/{retries - 1} in {wait}s ({error})", file=sys.stderr)
            time.sleep(wait)


def read_cve_ids():
    ids = []
    for line in CVE_LIST.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.append(line)
    return ids


def english(items):
    return next((item["value"] for item in items if item.get("lang") == "en"), "")


def render_cve(vuln, retrieved):
    cve = vuln["cve"]
    cve_id = cve["id"]
    lines = [f"# {cve_id}", "",
             f"- **Source:** NVD — {NVD_PAGE}/{cve_id}",
             f"- **Status:** {cve.get('vulnStatus', 'n/a')}",
             f"- **Published:** {cve['published'][:10]}",
             f"- **Last modified:** {cve['lastModified'][:10]}",
             f"- **Retrieved:** {retrieved}", "",
             "## Description", "", english(cve.get("descriptions", [])).strip(), ""]

    scores = []
    for key, entries in cve.get("metrics", {}).items():
        if not key.startswith("cvssMetric"):
            continue
        for entry in entries:
            data = entry["cvssData"]
            scores.append((data.get("version", ""), data.get("baseScore", ""),
                           data.get("baseSeverity") or entry.get("baseSeverity", ""),
                           data.get("vectorString", ""), entry.get("source", "")))
    if scores:
        lines += ["## CVSS", "", "| Version | Score | Severity | Vector | Source |", "|---|---|---|---|---|"]
        lines += [f"| {v} | {s} | {sev} | `{vec}` | {src} |" for v, s, sev, vec, src in sorted(scores, reverse=True)]
        lines.append("")

    weaknesses = sorted({english(w.get("description", [])) for w in cve.get("weaknesses", [])} - {""})
    if weaknesses:
        lines += ["## Weaknesses (CWE)", ""] + [f"- {w}" for w in weaknesses] + [""]

    criteria = []
    for config in cve.get("configurations", []):
        for node in config.get("nodes", []):
            criteria += [m["criteria"] for m in node.get("cpeMatch", []) if m.get("vulnerable")]
    if criteria:
        shown = criteria[:25]
        lines += ["## Affected products (CPE)", ""] + [f"- `{c}`" for c in shown]
        if len(criteria) > len(shown):
            lines.append(f"- … and {len(criteria) - len(shown)} more (see NVD)")
        lines.append("")

    refs = cve.get("references", [])
    if refs:
        lines += ["## References", ""]
        for ref in refs:
            tags = f" ({', '.join(ref['tags'])})" if ref.get("tags") else ""
            lines.append(f"- {ref['url']}{tags}")
        lines.append("")
    return "\n".join(lines)


def load_manifest():
    if MANIFEST.exists():
        return {doc["path"]: doc for doc in json.loads(MANIFEST.read_text())["documents"]}
    return {}


def build(force):
    CORPUS.mkdir(parents=True, exist_ok=True)
    previous = load_manifest()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs = []

    def record(doc_type, name, title, fmt, source, license_):
        rel = f"{doc_type}/{name}"
        path = CORPUS / rel
        old = previous.get(rel, {})
        digest = sha256(path)
        docs.append({"path": rel, "doc_type": doc_type, "title": title, "source_url": source, "format": fmt,
                     "license": license_,
                     "retrieved_date": old["retrieved_date"] if old.get("sha256") == digest else now,
                     "sha256": digest, "bytes": path.stat().st_size})

    for doc_type, name, title, fmt, source, license_ in LOCAL:
        target = CORPUS / doc_type / name
        target.parent.mkdir(parents=True, exist_ok=True)
        local_source = RAW_STANDARDS / source
        if force or not target.exists():
            if not local_source.exists():
                sys.exit(f"Missing local source file: {local_source}")
            shutil.copyfile(local_source, target)
            print(f"copied     {target.relative_to(CORPUS)}")
        record(doc_type, name, title, fmt, f"local:data/raw/standarts/{source}", license_)

    for doc_type, name, title, fmt, source, license_ in REMOTE:
        target = CORPUS / doc_type / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if force or not target.exists() or target.stat().st_size == 0:
            print(f"download   {source}")
            target.write_bytes(http_get(source))
        record(doc_type, name, title, fmt, source, license_)

    delay = 1 if os.environ.get("NVD_API_KEY") else 7
    headers = {"apiKey": os.environ["NVD_API_KEY"]} if os.environ.get("NVD_API_KEY") else {}
    for cve_id in read_cve_ids():
        target = CORPUS / "cve" / f"{cve_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        if force or not target.exists():
            print(f"NVD        {cve_id}")
            payload = json.loads(http_get(f"{NVD_API}?cveId={cve_id}", headers))
            if not payload.get("vulnerabilities"):
                sys.exit(f"NVD returned no record for {cve_id}")
            target.write_text(render_cve(payload["vulnerabilities"][0], now))
            time.sleep(delay)
        record("cve", target.name, f"{cve_id} — NVD advisory", "md", f"{NVD_PAGE}/{cve_id}", "Public (NVD)")

    MANIFEST.write_text(json.dumps({"generated": now, "documents": docs}, indent=2, ensure_ascii=False) + "\n")
    print(f"manifest   {MANIFEST.relative_to(ROOT)} ({len(docs)} documents)")


def verify():
    errors = []

    def fail(message):
        errors.append(message)

    if not CVE_LIST.exists():
        fail(f"missing {CVE_LIST.relative_to(ROOT)}")
        cve_ids = []
    else:
        cve_ids = read_cve_ids()
        if len(cve_ids) != len(set(cve_ids)):
            fail("duplicate IDs in cve_list.txt")
        for cve_id in cve_ids:
            if not re.fullmatch(r"CVE-\d{4}-\d{4,}", cve_id):
                fail(f"malformed CVE id in cve_list.txt: {cve_id}")

    if not MANIFEST.exists():
        fail("manifest.json missing (run without --verify first)")
        return errors
    docs = json.loads(MANIFEST.read_text())["documents"]

    expected = {f"{t}/{n}": t for t, n, *_ in LOCAL + REMOTE}
    expected.update({f"cve/{c}.md": "cve" for c in cve_ids})
    in_manifest = {d["path"] for d in docs}
    for missing in sorted(set(expected) - in_manifest):
        fail(f"requested but not in manifest: {missing}")
    for extra in sorted(in_manifest - set(expected)):
        fail(f"in manifest but not requested: {extra}")

    on_disk = {p.relative_to(CORPUS).as_posix() for p in CORPUS.rglob("*") if p.is_file() and p.name != ".DS_Store"}
    for stray in sorted(on_disk - in_manifest - {"manifest.json", "cve_list.txt"}):
        fail(f"file on disk but not in manifest: {stray}")

    hashes = {}
    for doc in docs:
        path = CORPUS / doc["path"]
        if doc["doc_type"] != doc["path"].split("/")[0] or expected.get(doc["path"], doc["doc_type"]) != doc["doc_type"]:
            fail(f"{doc['path']}: doc_type '{doc['doc_type']}' is not the one requested for its folder")
        if not path.is_file():
            fail(f"missing file: {doc['path']}")
            continue
        head = path.read_bytes()[:2048].lstrip().lower()
        if doc["sha256"] != sha256(path):
            fail(f"{doc['path']}: sha256 differs from manifest")
        if path.stat().st_size < 1000:
            fail(f"{doc['path']}: suspiciously small ({path.stat().st_size} bytes)")
        if doc["format"] == "pdf" and not head.startswith(b"%pdf"):
            fail(f"{doc['path']}: not a PDF")
        if doc["format"] == "html" and b"<html" not in head and b"<!doctype html" not in head:
            fail(f"{doc['path']}: not HTML")
        if doc["format"] == "md" and not path.read_text(errors="replace").strip():
            fail(f"{doc['path']}: empty markdown")
        hashes.setdefault(doc["sha256"], []).append(doc["path"])
    for same in hashes.values():
        if len(same) > 1:
            fail(f"duplicate content: {same}")

    counts = {t: sum(1 for d in docs if d["doc_type"] == t) for t in EXPECTED_COUNTS}
    for doc_type, want in EXPECTED_COUNTS.items():
        if counts[doc_type] != want:
            fail(f"{doc_type}: expected {want} docs, found {counts[doc_type]}")
    formats = {d["format"] for d in docs}
    if len(docs) < MIN_DOCS:
        fail(f"only {len(docs)} documents (need >= {MIN_DOCS})")
    if len(formats) < MIN_FORMATS:
        fail(f"only formats {sorted(formats)} (need >= {MIN_FORMATS})")

    print(f"documents: {len(docs)}  by type: {counts}  formats: {sorted(formats)}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="re-download/re-render everything")
    parser.add_argument("--verify", action="store_true", help="only verify existing files and manifest")
    args = parser.parse_args()

    if not args.verify:
        build(args.force)
    errors = verify()
    if errors:
        print(f"\nVERIFY FAILED ({len(errors)}):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    print("VERIFY OK")


if __name__ == "__main__":
    main()
