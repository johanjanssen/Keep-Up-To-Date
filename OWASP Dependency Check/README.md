# OWASP Dependency Check

Dependency vulnerability scanning with **OWASP Dependency Check**.
Scans application dependencies (JARs, libraries) against the NVD database.

---

## Prerequisites

- **Docker** — all tools run as containers
- **NVD cache** — local NVD mirror for fast, offline scanning

---

## Scripts

| Script | Description |
|---|---|
| `scripts/start-cache.sh` | Start the local NVD data-feed cache server (port 7070) |
| `scripts/update-cache.sh` | Download/update NVD data in the cache container |
| `scripts/run-check.sh` | Run DC against the demo Maven project (intentionally vulnerable) |

---

## Quick Start

```bash
# 1. Start the NVD cache (one-time setup)
bash scripts/start-cache.sh

# 2. Update the vulnerability database
bash scripts/update-cache.sh

# 3. Scan the demo Maven project
bash scripts/run-check.sh
```

---

## Example Output

The scan reports vulnerabilities found in the Maven project's dependencies:

```
  log4j-core-2.0.jar           : CVE-2021-44228 (CRITICAL, CVSS 10.0)
  jackson-databind-2.9.10.jar  : CVE-2019-14379 (CRITICAL, CVSS 9.8)
  ...
```

Reports are generated in `Vulnerable Application/target/`:
- `dependency-check-report.html`
- `dependency-check-report.json`
- `dependency-check-report.sarif`

---

## Demo Project (Intentional Vulnerabilities)

| Dependency | Version | CVE | CVSS |
|---|---|---|---|
| `log4j-core` | `2.0` | CVE-2021-44228 (Log4Shell) | **10.0** |
| `jackson-databind` | `2.9.10` | CVE-2019-14379 | 9.8 |

> To make the build **fail** on HIGH+ CVEs, uncomment `<failBuildOnCVSS>7</failBuildOnCVSS>`
> in `Vulnerable Application/pom.xml`.

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
