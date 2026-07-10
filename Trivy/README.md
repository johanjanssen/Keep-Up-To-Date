# Trivy

Container image vulnerability scanning with **Trivy** (by Aqua Security).
Scans base and application images and reports CVEs broken down by severity.

---

## Prerequisites

- **Docker** — Trivy runs as a container, no local installation needed
- **jq** — for JSON parsing in `compare-images.sh`

---

## Scripts

| Script | Description |
|---|---|
| `scripts/update-db.sh` | Download/update the Trivy vulnerability database (Docker volume `trivy-db`) |
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
eclipse-temurin:25-jre                                    47         3        12        24         8         0
gcr.io/distroless/base-debian12                           17         0         4         8         5         0
gcr.io/distroless/static-debian12                          0         0         0         0         0         0
```

*(Exact counts vary by image build date and database version.)*

---

## Save JSON Results

```bash
# Save per-image JSON to a directory (used by Compare Security Scans)
bash scripts/compare-images.sh --json-out /path/to/results/trivy
```

---

## CI Integration (GitHub Actions)

```yaml
- name: Trivy scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: my-app:latest
    format: sarif
    output: trivy-results.sarif
    exit-code: '1'
    severity: CRITICAL

- name: Upload Trivy SARIF
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: trivy-results.sarif
```
