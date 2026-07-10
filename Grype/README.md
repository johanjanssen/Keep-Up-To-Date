# Grype

Container image vulnerability scanning with **Grype** (by Anchore).
Scans base and application images and reports CVEs broken down by severity.

---

## Prerequisites

- **Docker** — Grype runs as a container, no local installation needed
- **jq** — for JSON parsing in `compare-images.sh`

---

## Scripts

| Script | Description |
|---|---|
| `scripts/update-db.sh` | Download/update the Grype vulnerability database (Docker volume `grype-db`) |
| `scripts/scan-image.sh <image>` | Scan a single image (table output) |
| `scripts/compare-images.sh` | Scan all base + app images and print a severity breakdown table |

---

## Quick Start

```bash
# 1. Update the vulnerability database (cached in Docker volume)
bash scripts/update-db.sh

# 2. Scan a single image
bash scripts/scan-image.sh eclipse-temurin:25-jre

# 3. Compare all images side-by-side
bash scripts/compare-images.sh
```

---

## Example Output

```
IMAGE                                               TOTAL  CRITICAL      HIGH    MEDIUM       LOW   UNKNOWN
--------------------------------------------------  --------  --------  --------  --------  --------  --------
eclipse-temurin:25-jre                                    42         2        10        22         8         0
gcr.io/distroless/base-debian12                           15         0         3         7         5         0
gcr.io/distroless/static-debian12                          0         0         0         0         0         0
```

*(Exact counts vary by image build date and database version.)*

---

## Save JSON Results

```bash
# Save per-image JSON to a directory (used by Compare Security Scans)
bash scripts/compare-images.sh --json-out /path/to/results/grype
```

---

## CI Integration (GitHub Actions)

```yaml
- name: Grype scan
  uses: anchore/scan-action@v4
  with:
    image: my-app:latest
    fail-build: true
    severity-cutoff: critical
    output-format: sarif

- name: Upload Grype SARIF
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: results.sarif
```
