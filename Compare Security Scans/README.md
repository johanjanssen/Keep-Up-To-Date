# Compare Security Scans

Scans all Docker images with **Grype** and **Trivy**, then produces four comparison views:

1. **Severity count comparison** — Grype vs Trivy side-by-side (TOTAL/CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN)
2. **CVE matrix** — lists every CVE found and marks which tool(s) detected it
3. **Trivy only** — severity counts per image
4. **Grype only** — severity counts per image

---

## Quick Start

```bash
# Run the full pipeline (both scanners + comparison)
bash "Compare Security Scans/scripts/run-all.sh"
```

---

## Individual Steps

```bash
# Scan with each tool independently:
bash "Compare Security Scans/scripts/scan-grype.sh"
bash "Compare Security Scans/scripts/scan-trivy.sh"

# Generate comparison tables from existing results:
bash "Compare Security Scans/scripts/compare.sh"
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Docker** | All tools run as containers — no local installation needed |
| **jq** | JSON parsing ([download](https://jqlang.github.io/jq/download/)) |
| **Built images** | `bash build/build-all-images.sh` for `hello-conference:*` images |

---

## Images Scanned

Defined in `images.conf` at the project root (single source of truth).

---

## Output

### View 1: Grype vs Trivy

```
IMAGE                                              │  GRYPE (Tot/C/H/M/L/U)   │  TRIVY (Tot/C/H/M/L/U)
──────────────────────────────────────────────────────┼───────────────────────────┼───────────────────────────
eclipse-temurin:25-jre                             │    20    0    3   12    5 │    16    0    2   10    4
gcr.io/distroless/static-debian12                  │     0    0    0    0    0 │     0    0    0    0    0
```

### View 2: CVE Matrix

```
┌─ eclipse-temurin:25-jre (25 unique CVEs)
  CVE ID                    SEVERITY     │ Grype │ Trivy
  CVE-2024-0727             Medium       │ X     │ X
  CVE-2023-4911             High         │ X     │ X
```

### View 3 & 4: Individual tool tables

Per-image severity breakdown for Trivy and Grype independently.

---

## Directory Structure

```
Compare Security Scans/
├── README.md
├── scripts/
│   ├── run-all.sh          ← master script — runs all steps
│   ├── scan-grype.sh       ← delegates to Grype/scripts/
│   ├── scan-trivy.sh       ← delegates to Trivy/scripts/
│   └── compare.sh          ← parse results: 4 comparison views
└── results/                 ← generated (gitignored)
    ├── grype/              ← JSON output per image
    └── trivy/              ← JSON output per image
```

---

## Key Takeaways

- **Grype and Trivy** scan OS packages + language deps (image-level)
- They use different vulnerability databases — differences are expected
- Using **both** gives the most comprehensive picture
- **Distroless and scratch images** consistently show fewer (or zero) vulnerabilities
