# Compare Security Scans

Scans all Docker images with **Grype** and **Trivy**, then produces two comparison views:

1. **Severity count comparison** — Grype vs Trivy side-by-side (TOTAL/CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN) with unique-in-Trivy indicator
2. **OS vs Application breakdown** — OS-level package vulnerabilities and application-level (JAR/language) vulnerabilities shown separately, including OWASP DC results

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
| **Built images** | `bash "Build Docker Images/build-all-images.sh"` for `hello-conference:*` images |

---

## Images Scanned

Defined in `images.conf` at the project root (single source of truth).

---

## Output

### View 1: Grype vs Trivy — Severity Count Comparison

```
IMAGE                                              │  GRYPE (Tot/C/H/M/L/U)   │  TRIVY (Tot/C/H/M/L/U)   │ Unique in Trivy
───────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────────────┼──────────────────
eclipse-temurin:25-jre                             │    20    0    3   12    5    0 │    16    0    2   10    4    0 │ 3
gcr.io/distroless/static-debian12                  │     0    0    0    0    0    0 │     0    0    0    0    0    0 │ -
```

### View 2: OS Packages vs Application Dependencies

Separate tables for OS-level vulnerabilities (distro packages) and application-level
vulnerabilities (JARs/language deps), with OWASP DC included for the application layer.

---

## Directory Structure

```
Compare Security Scans/
├── README.md
├── scripts/
│   ├── run-all.sh          ← master script — runs all steps
│   ├── scan-grype.sh       ← delegates to Grype/scripts/
│   ├── scan-trivy.sh       ← delegates to Trivy/scripts/
│   └── compare.sh          ← parse results: 2 comparison views
└── target/
    └── results/             ← generated (gitignored)
        ├── grype/           ← JSON output per image
        └── trivy/           ← JSON output per image
```

---

## Key Takeaways

- **Grype and Trivy** scan OS packages + language deps (image-level)
- They use different vulnerability databases — differences are expected
- Using **both** gives the most comprehensive picture
- **Distroless and scratch images** consistently show fewer (or zero) vulnerabilities
