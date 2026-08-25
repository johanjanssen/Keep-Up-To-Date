# OSV-Scanner

Container image vulnerability scanning with **OSV-Scanner** (by Google), matched
against the [OSV.dev](https://osv.dev) database.
Scans base and application images and reports CVEs broken down by severity.

---

## Prerequisites

- **Docker** — OSV-Scanner runs as a container, no local installation needed
- **jq** — for JSON parsing in `compare-images.sh`

---

## Scripts

| Script | Description |
|---|---|
| `scripts/update-db.sh` | Pull/refresh the OSV-Scanner image (no offline DB — see below) |
| `scripts/scan-image.sh <image>` | Scan a single image (table output) |
| `scripts/compare-images.sh` | Scan all base + app images and print a severity breakdown table |

---

## Quick Start

```bash
# 1. Pull/refresh the OSV-Scanner image
bash scripts/update-db.sh

# 2. Scan a single image
bash scripts/scan-image.sh eclipse-temurin:25-jre

# 3. Compare all images side-by-side
bash scripts/compare-images.sh
```

---

## How image scanning works here

OSV-Scanner's own container image doesn't bundle the `docker` CLI, so unlike
running it natively it can't `docker save` an image by itself. Instead, these
scripts run `docker save` **on the host** for each image and hand OSV-Scanner
the resulting archive with `osv-scanner scan image --archive <tar>` — see the
[Container Image Scanning docs](https://google.github.io/osv-scanner/usage/scan-image/).
No local vulnerability database is downloaded up front: by default OSV-Scanner
matches extracted packages against the live OSV.dev API on every scan.

---

## Example Output

```
IMAGE                                               TOTAL  CRITICAL      HIGH    MEDIUM       LOW   UNKNOWN
--------------------------------------------------  --------  --------  --------  --------  --------  --------
eclipse-temurin:25-jre                                    98         0         0        81         8         9
debian:13-slim                                            78         0         0         0         0        78
alpine:3                                                   0         0         0         0         0         0
```

*(Exact counts vary by image build date and OSV.dev data at scan time.)*

⚠ Severity is derived from `database_specific.severity` (set by GHSA-sourced
advisories) or a vendor-rated entry in `severity[]` (e.g. Ubuntu's OSV feed
rates "medium"/"high"/etc.). Many OS-level advisories — notably Debian's — and
Go's stdlib advisories carry **no** severity rating in OSV at all, so they're
counted as `UNKNOWN` here rather than guessed at from a raw CVSS vector.

---

## Save JSON Results

```bash
# Save per-image JSON to a directory (used by Compare Security Scans)
bash scripts/compare-images.sh --json-out /path/to/results/osv
```
