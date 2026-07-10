# Keep Up To Date

Companion repository for the **"Keep Up To Date"** conference talk.
Each directory is a self-contained demo covering a different aspect of keeping
Java applications and Docker images secure, up-to-date, and well-tested.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Docker** | All tools run as containers — no local installations needed |
| **Java 25** | Only if running Maven outside Docker (`./mvnw` wrapper is included) |
| **jq** | Required by scanning/comparison scripts ([download](https://jqlang.github.io/jq/download/)) |
| **Bash 4+** | Git Bash / WSL2 on Windows; native on macOS / Linux |
| **curl** | Used by exercise/readiness scripts |

---

## Repository Overview

| Directory | What it demonstrates | Quick Start |
|---|---|---|
| [Vulnerable Application/](#vulnerable-application) | Spring Boot app with **intentionally vulnerable** dependencies — the scan target | `./mvnw -f "Vulnerable Application/pom.xml" package` |
| [Build Docker Images/](#build-docker-images) | 11 Docker image strategies (JRE, jlink, CRaC, GraalVM native) with size & startup benchmarks | `bash "Build Docker Images/build-all-images.sh"` |
| [Grype/](#grype) | Image vulnerability scanning with Grype (Anchore) | `bash Grype/scripts/compare-images.sh` |
| [Trivy/](#trivy) | Image vulnerability scanning with Trivy (Aqua Security) | `bash Trivy/scripts/compare-images.sh` |
| [OWASP Dependency Check/](#owasp-dependency-check) | Maven dependency scanning against the NVD database | `bash "OWASP Dependency Check/scripts/run-check.sh"` |
| [Compare Security Scans/](#compare-security-scans) | Run Grype + Trivy + OWASP DC and compare results side-by-side | `bash "Compare Security Scans/scripts/run-all.sh"` |
| [OpenRewrite/](#openrewrite) | Automated migration: Spring Boot 2→4, Java 17→25, JUnit 4→5 | `bash OpenRewrite/scripts/run-openrewrite.sh` |
| [Testcontainers/](#testcontainers) | Integration testing with real PostgreSQL via `@ServiceConnection` | `bash Testcontainers/scripts/run-tests.sh` |
| [JaCoCo/](#jacoco) | Production-agent code coverage — detect dead code in running applications | `bash "Jacoco/scripts/Retrieve Coverage From Port/run-demo.sh"` |
| [Renovate/](#renovate) | Local Gitea + Jenkins + Renovate bot — automated dependency update PRs | `bash Renovate/scripts/demo.sh` |

---

## Shared Configuration

**`images.conf`** at the project root is the single source of truth for all base
and application image names. It is sourced by every scanning and measurement script.

---

## Vulnerable Application

Spring Boot 4.1 / Java 25 web application with **intentionally vulnerable** dependencies:

| Dependency | Version | CVE | CVSS |
|---|---|---|---|
| `log4j-core` | `2.0` | CVE-2021-44228 (Log4Shell) | **10.0** |
| `jackson-databind` | `2.9.10` | CVE-2019-14379 + others | 9.8 |

Used as the scan target for Grype, Trivy, OWASP DC, and the Docker image builds.

---

## Build Docker Images

Builds Docker image variants of the same Spring Boot app to compare size,
startup time, memory usage, and attack surface.

```bash
bash "Build Docker Images/build-all-images.sh"      # build everything
bash "Build Docker Images/measure-images.sh"         # image sizes + package counts
bash "Build Docker Images/measure-performance.sh"    # startup time + memory
```

| Image tag | Strategy | Runtime base |
|---|---|---|
| `jre-temurin` | Full JRE | `eclipse-temurin:25-jre` |
| `jlink-full-distroless-base` | jlink (all modules) | `distroless/base-debian12` |
| `jlink-distroless-base` | jlink (minimal modules) | `distroless/base-debian12` |
| `jlink-netty-distroless-base` | jlink (Netty-optimised) | `distroless/base-debian12` |
| `jlink-cds-distroless-base` | jlink + CDS archive | `distroless/base-debian12` |
| `jlink-tuned-distroless-base` | jlink + CDS + JVM tuning | `distroless/base-debian12` |
| `crac-azul-distroless-base` | CRaC checkpoint/restore | `distroless/base-debian12` |
| `native-debian-slim` | GraalVM native image | `debian:12-slim` |
| `native-minimal-distroless-static` | GraalVM native (minimal) | `distroless/static-debian12` |
| `native-scratch` | GraalVM native | `scratch` |
| `native-netty-scratch` | GraalVM native (Netty) | `scratch` |

---

## Grype

Container image vulnerability scanning with [Grype](https://github.com/anchore/grype)
(by Anchore). Scans OS packages + language dependencies.

```bash
bash Grype/scripts/update-db.sh                         # update vuln DB
bash Grype/scripts/scan-image.sh eclipse-temurin:25-jre  # scan one image
bash Grype/scripts/compare-images.sh                     # compare all images
```

---

## Trivy

Container image vulnerability scanning with [Trivy](https://github.com/aquasecurity/trivy)
(by Aqua Security). Scans OS packages + language dependencies.

```bash
bash Trivy/scripts/update-db.sh                         # update vuln DB
bash Trivy/scripts/scan-image.sh eclipse-temurin:25-jre  # scan one image
bash Trivy/scripts/compare-images.sh                     # compare all images
```

---

## OWASP Dependency Check

Scans Maven dependencies (not OS packages) against the NVD database.
Requires a local NVD cache server.

```bash
bash "OWASP Dependency Check/scripts/start-cache.sh"    # start local NVD mirror
bash "OWASP Dependency Check/scripts/update-cache.sh"    # download/refresh NVD data
bash "OWASP Dependency Check/scripts/run-check.sh"       # scan vulnerable dependencies
```

---

## Compare Security Scans

Runs Grype, Trivy, and OWASP DC against all images and produces comparison tables:
severity counts side-by-side, and OS-level vs application-level breakdown.

```bash
bash "Compare Security Scans/scripts/run-all.sh"
```

---

## OpenRewrite

Automated code migration using [OpenRewrite](https://docs.openrewrite.org) recipes:
Spring Boot 2.7→4.1, Java 17→25, JUnit 4→5, code style fixes.

```bash
bash OpenRewrite/scripts/run-openrewrite.sh                # apply all recipes
DRY_RUN=true bash OpenRewrite/scripts/run-openrewrite.sh   # preview only
```

---

## Testcontainers

Integration tests with a real PostgreSQL container using Spring Boot's
`@ServiceConnection` — no `@DynamicPropertySource` boilerplate.

```bash
bash Testcontainers/scripts/run-tests.sh
```

---

## JaCoCo

Production-agent code coverage with JaCoCo — detect dead code by attaching the agent
to a running application. Two modes: TCP port-based (live dumps) and file-based (on JVM exit).

```bash
bash "Jacoco/scripts/Retrieve Coverage From Port/run-demo.sh"   # port-based (fully automated)
bash "Jacoco/scripts/Retrieve Coverage From File/run-demo.sh"   # file-based (fully automated)
```

---

## Renovate

Local Gitea + Jenkins + Renovate bot — fully automated dependency update PRs with CI
feedback. Renovate opens PRs, Jenkins builds them, and reports back to Gitea.

```bash
bash Renovate/scripts/demo.sh           # full automated demo (~10-15 min first run)
bash Renovate/scripts/reset-demo.sh     # clean up everything
```

---

## Run Everything

A master script `run-all-demos.sh` exercises every demo in sequence to verify the
full setup is working:

```bash
bash run-all-demos.sh
```

> ⚠ **This takes a long time** (native image builds alone can take 20+ minutes each).
> It requires Docker, Java 25, jq, curl, and git. See the script header for details.

