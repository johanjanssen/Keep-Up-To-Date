# OWASP Dependency Check

Dependency vulnerability scanning with **OWASP Dependency Check**.
Scans application dependencies (JARs, libraries) against the NVD database.

---

## Prerequisites

- **Docker** — all tools run as containers
- **jq** — for JSON parsing in `compare-images.sh`
- **NVD cache** — local NVD mirror for fast, offline scanning

---

## Scripts

| Script | Description |
|---|---|
| `scripts/start-cache.sh` | Start the local NVD data-feed cache server (port 7070) |
| `scripts/update-cache.sh` | Download/update NVD data in the cache container |
| `scripts/run-check.sh` | Run DC against the demo Maven project (intentionally vulnerable) |
| `scripts/scan-image.sh <image>` | Scan a single Docker image (via Syft SBOM → DC) |
| `scripts/compare-images.sh` | Scan all base + app images and print a severity breakdown table |

---

## Quick Start

```bash
# 1. Start the NVD cache (one-time setup)
bash scripts/start-cache.sh

# 2. Update the vulnerability database
bash scripts/update-cache.sh

# 3. Scan the demo Maven project (expected: BUILD FAILURE)
bash scripts/run-check.sh

# 4. Scan a single Docker image
bash scripts/scan-image.sh eclipse-temurin:25-jre

# 5. Compare all images side-by-side
bash scripts/compare-images.sh
```

---

## Example Output

```
IMAGE                                               TOTAL  CRITICAL      HIGH    MEDIUM       LOW   UNKNOWN
--------------------------------------------------  --------  --------  --------  --------  --------  --------
eclipse-temurin:25-jre                                     0         0         0         0         0         0
hello-conference:jre-temurin                                3         1         1         1         0         0
gcr.io/distroless/static-debian12                          0         0         0         0         0         0
```

*(OWASP DC scans application dependencies, not OS packages. Base images without
application JARs will typically show 0 vulnerabilities.)*

---

## How It Works for Image Scanning

1. **Syft** generates a CycloneDX SBOM from the Docker image
2. **OWASP DC** scans the SBOM against the local NVD cache
3. Results are parsed for severity counts

This approach finds vulnerabilities in application libraries (JARs, etc.)
but does **not** detect OS-level package vulnerabilities. Use Trivy or Grype
for comprehensive OS + language scanning.

---

## Save JSON Results

```bash
# Save per-image JSON to a directory (used by Compare Security Scans)
bash scripts/compare-images.sh --json-out /path/to/results/owasp
```

---

## Demo Project (Intentional Vulnerabilities)

| Dependency | Version | CVE | CVSS |
|---|---|---|---|
| `log4j-core` | `2.0` | CVE-2021-44228 (Log4Shell) | **10.0** |
| `jackson-databind` | `2.9.10` | CVE-2019-14379 | 9.8 |

The plugin is configured with `<failBuildOnCVSS>7</failBuildOnCVSS>`.

---

## CI Integration (GitHub Actions)

```yaml
- name: OWASP Dependency Check
  run: ./mvnw dependency-check:check
  env:
    NVD_API_KEY: ${{ secrets.NVD_API_KEY }}

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: target/dependency-check-report.sarif
```
