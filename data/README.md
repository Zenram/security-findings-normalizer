# Data

## `raw/` — input corpus (NOT committed)

Gitignored. Put the 30 input texts here, grouped by source family so the
extractor can tag `source` and the golden set can cover >=3 families.

```
raw/
├── team_reports/   # source=team_report   (sanitized/synthetic Slack-style reports)
├── cnapp/          # source=cnapp          (CNAPP alert export CSV)
├── aspm/           # source=aspm           (ASPM alert export CSV)
├── oss_scanner/    # source=oss_scanner    (Kubescape/Trivy/Prowler/LinPEAS output)
└── standards/      # AWS JSON + PDF — REFERENCE context only, NOT extracted in Stage 1
```

**Do not count `standards/` toward the 30 extraction texts** — compliance
references are not findings. They are kept for the later RAG stage.

## `golden/` — labeled ground truth (COMMITTED)

The golden set is the measurement baseline, not just "example output". Each
entry is a **pair**: the raw input text and the *correct* extracted JSON that a
human labeled by hand. The evaluation harness runs the model on the input and
scores its output against the labeled JSON.

Suggested layout (10 pairs):

```
golden/
├── 01_input.txt        # raw text
├── 01_expected.json    # hand-labeled correct Finding(s) for 01_input.txt
├── 02_input.txt
├── 02_expected.json
└── ...
```

(Or a single `golden.jsonl` where each line = `{"input": ..., "expected": [...]}`.
Developer picks the format; keep it consistent.)

### Golden set must include these hard cases (course requirement)

| Case | Why it matters |
|---|---|
| Same CVE across multiple repos | CVE is not a unique key |
| Same issue reported by multiple tools | Duplicate candidate, not auto-merge |
| Ambiguous / non-standard status | Tests status normalization + `status_raw` |
| Remediation claimed without evidence | `resolved` != verified fixed |
| Missing team / repo / date | Must become null/unknown, not invented |
| Multiple findings in one text | Extractor must return a list |
| Mixed languages | Local model likely weaker here — measured separately |

> Only synthetic or fully sanitized data goes in `golden/` (public repo).
> Clearly label synthetic examples as synthetic inside the file.
