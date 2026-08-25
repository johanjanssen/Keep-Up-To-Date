# Compare Security Scans

Scans all Docker images with **Grype**, **Trivy**, and **OSV-Scanner**, then produces two comparison views:

1. **Severity count comparison** — Grype, Trivy, and OSV-Scanner side-by-side (TOTAL/CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN each), plus a per-tool "Unique" column (a CVE that scanner found and neither of the other two did)
2. **OS vs Application breakdown** — OS-level package vulnerabilities and application-level (JAR/language) vulnerabilities shown separately, including OWASP DC results

OSV-Scanner is included as a third, independent data source — matched against
[OSV.dev](https://osv.dev) rather than Grype's/Trivy's own vulnerability feeds.
Its severity data is patchier for some OS ecosystems (notably Debian, which OSV
carries with no severity rating at all) — see [`OSV/README.md`](../OSV/README.md).

---

## Quick Start

```bash
# Run the full pipeline (all three scanners + comparison)
bash "Compare Security Scans/scripts/run-all.sh"
```

---

## Individual Steps

```bash
# Scan with each tool independently:
bash "Compare Security Scans/scripts/scan-grype.sh"
bash "Compare Security Scans/scripts/scan-trivy.sh"
bash "Compare Security Scans/scripts/scan-osv.sh"

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

### View 1: Grype vs Trivy vs OSV-Scanner — Severity Count Comparison

```
IMAGE                                              │  GRYPE (Tot/C/H/M/L/U)   │  TRIVY (Tot/C/H/M/L/U)   │   OSV (Tot/C/H/M/L/U)    │ Unique Grype │ Unique Trivy │ Unique OSV
─────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────────────┼──────────────────────────────┼──────────────┼──────────────┼────────────
eclipse-temurin:25-jre                             │    96    0    2   87    7    0 │    60    0    8   47    4    1 │    98    0    0   81    8    9 │ 1            │ 11           │ 18
gcr.io/distroless/static-debian13                  │     0    0    0    0    0    0 │     0    0    0    0    0    0 │     0    0    0    0    0    0 │ -            │ -            │ -
```

### View 2: OS Packages vs Application Dependencies

Separate tables for OS-level vulnerabilities (distro packages) and application-level
vulnerabilities (JARs/language deps), with OWASP DC included for the application layer.

### HTML report — OWASP Dependency Check table

The generated `custom-image-scans` HTML report (built by `generate-html-report.py`,
published at [`/custom-image-scans/`](https://johanjanssen.github.io/Keep-Up-To-Date/custom-image-scans/))
adds a separate one-row **OWASP Dependency Check** table below the Grype/Trivy/OSV-Scanner
one, with the same Total/Crit/High/Med/Low columns. It's a single row (not one per image)
because OWASP DC scans the app's dependency tree (`Vulnerable Application/pom.xml`) once,
and every `hello-conference:*` image embeds that same built jar. A "Unique in OWASP" column
shows CVEs OWASP DC found that neither Grype, Trivy, nor OSV-Scanner found in any scanned
image — and that same 4-way comparison is folded back into the Grype/Trivy/OSV table's own
"Unique" columns, so a CVE found by both (say) Grype and OWASP DC no longer counts as
"unique to Grype".

---

## Directory Structure

```
Compare Security Scans/
├── README.md
├── scripts/
│   ├── run-all.sh          ← master script — runs all steps
│   ├── scan-grype.sh       ← delegates to Grype/scripts/
│   ├── scan-trivy.sh       ← delegates to Trivy/scripts/
│   ├── scan-osv.sh         ← delegates to OSV/scripts/
│   └── compare.sh          ← parse results: 2 comparison views
└── target/
    └── results/             ← generated (gitignored)
        ├── grype/           ← JSON output per image
        ├── trivy/           ← JSON output per image
        └── osv/             ← JSON output per image
```

---

## Key Takeaways

- **Grype and Trivy** scan OS packages + language deps (image-level)
- They use different vulnerability databases — differences are expected
- **OSV-Scanner** adds a third, independent database (OSV.dev) with its own full severity breakdown — but many of its OS-level findings carry no severity rating at all (see [`OSV/README.md`](../OSV/README.md))
- Using **multiple tools** gives the most comprehensive picture
- **Distroless and scratch images** consistently show fewer (or zero) vulnerabilities
