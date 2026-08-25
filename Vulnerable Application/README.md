# 🔓 Vulnerable Application

> **⚠️ FOR CONFERENCE DEMO PURPOSES ONLY — DO NOT DEPLOY TO PRODUCTION ⚠️**

Spring Boot 4.1 / Java 25 app (`HelloConference`) with two known-vulnerable dependencies
sitting on its classpath purely so security scanners have something real to find:

| Dependency | Version | CVE | CVSS |
|---|---|---|---|
| `log4j-core` | `2.14.1` | CVE-2021-44228 (Log4Shell) | **10.0** |
| `jackson-databind` | `2.13.4.1` | CVE-2022-42003 / CVE-2022-42004 | 7.5 |

The app itself uses Spring Boot's default SLF4J/Logback logging and never touches either
library at runtime — they're declared dependencies only, not exploited code paths. For a
**live, end-to-end exploit chain** (Log4Shell → RCE → PwnKit), see
[`Vulnerable Application Old Java/`](../Vulnerable%20Application%20Old%20Java) and
[`Callback Server/`](../Callback%20Server), which run an older Spring Boot/Java stack where
the JNDI lookup actually fires.

---

## What this app is used for

1. **Scan target** — [`OWASP Dependency Check`](../OWASP%20Dependency%20Check),
   [`Trivy`](../Trivy), and [`Grype`](../Grype) all scan this module's dependency tree and
   detect the CVEs above.
2. **Docker image optimization base** — [`Build Docker Images`](../Build%20Docker%20Images)
   builds this same app into a dozen different container variants (jlink, native image,
   CRaC, CDS, …) to compare size/startup/memory.

```bash
# Build the jar
../mvnw -f pom.xml package

# Run the OWASP Dependency Check scan against it
bash "../OWASP Dependency Check/scripts/run-check.sh"
```

## Endpoints

| Route | Purpose |
|---|---|
| `GET /hello` | Health check — used by Docker image build/benchmark scripts |
| `GET /api/products/search?q=` | Sample endpoint that logs the query — used by the *Docker image* benchmarks, not by any exploit in this directory |
