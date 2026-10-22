# Data

## `raw/` — input corpus (NOT committed)

Gitignored. Input texts grouped by source family so the router can tag `source`.
Mentor-approved Part 1 scope is **3 source families proven end-to-end**: team
reports, Ox ASPM, LinPEAS. The other folders are corpus material for later Parts.

```
raw/
├── team_reports/   # source=team_report   (sanitized Slack-style reports)  — LLM path
├── aspm/           # source=aspm          (Ox ASPM alert export CSV)        — PARSER path
├── cnapp/          # source=cnapp         (Orca CNAPP CSV)                   — corpus only
├── oss_scanner/
│   ├── linpeas/    # source=oss_scanner   (LinPEAS output)                  — LLM path
│   ├── trivy/      # source=oss_scanner   (Trivy JSON/txt)                  — corpus only
│   └── kubescape/  # source=oss_scanner   (Kubescape blocks)                — corpus only
└── standarts/      # AWS HIPAA/SOC2 md — REFERENCE only, NOT extracted (RAG, Part 2)
```

**Do not count `standarts/` toward the extraction texts** — compliance
references are not findings. They are kept for the RAG Part (Part 2).

## `real/` — original sanitized exports (NOT committed)

Gitignored. The original sanitized source files + helper scripts (`linpeas.sh`,
scan scripts) that `raw/` samples were drawn from. Never committed.

## `golden/` — labeled ground truth (COMMITTED)

The golden set is the measurement baseline, not just "example output". Each
entry is a **pair**: the raw input text and the *correct* extracted JSON that a
human labeled by hand. The evaluation harness runs the model on the input and
scores its output against the labeled JSON. See `golden/README.md` for the full
scoring method (D2), normalization (D4), granularity (D5), and team-inference
(D6) rules.

**Settled format** (10 pairs, one file each — not JSONL):

```
golden/
├── 01_input.txt        # raw text given to the extractor
├── 01_expected.json    # hand-labeled correct Finding(s), a JSON array
├── 02_input.txt
├── 02_expected.json
└── ...                 # 08_input.json is JSON (Trivy); the rest are .txt
```

### Golden set hard-case coverage (see `golden/README.md` manifest)

| Case | Entry(ies) | Why it matters |
|---|---|---|
| Multiple findings in one text | 01, 02, 03 | Extractor must return a list |
| Dual severity (Severity vs Original) | 06, 07 | D4 normalization rule |
| Many CVEs in one finding | 06 | `cve_ids` list, not duplicate findings |
| One check across many assets | 08 | One finding, many `affected_assets` (D5) |
| Same CVE across sources / tools | 09 | CVE not a unique key; not auto-merged |
| Missing team / repo | 01, 04, 05 | Must become null, not invented |
| Noisy unstructured output | 04, 05 | LinPEAS LLM path |
| Prompt injection | 10 | Text is data, not instructions (D3) |

> Only synthetic or fully sanitized data goes in `golden/` (public repo).
> Synthetic/adversarial entries (e.g. 10) say so inside the file.
