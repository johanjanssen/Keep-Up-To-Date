# JaCoCo Production Agent Demo

JaCoCo is best known as a test-coverage tool. This demo shows its **production agent
mode**: attach the agent to a running JVM, let real traffic exercise the code, then
generate an HTML report showing exactly which methods were called — and which were not.

Two approaches are demonstrated side by side, each with its own script set:

| | **Port-based** | **File-based** |
|---|---|---|
| **Location** | `scripts/Retrieve Coverage From Port/` | `scripts/Retrieve Coverage From File/` |
| **Agent output** | TCP server (port 6300) | File written on JVM exit |
| **Collect data** | Dump while app is running | Stop the app |
| **Best for** | Live snapshots, multiple dumps | Simplicity, one-shot runs |

The app includes an `/admin/diagnostics` endpoint that is **intentionally never called**.
It will appear as 0% (red) in the report, simulating dead-code detection in production.

---

## Quickest start — fully automated

Both subdirectories include a `run-demo.sh` that runs the complete pipeline unattended:

```bash
# Port-based
bash "scripts/Retrieve Coverage From Port/run-demo.sh"

# File-based
bash "scripts/Retrieve Coverage From File/run-demo.sh"
```

Both scripts: build the JAR → start the app in the background → exercise all endpoints
→ collect coverage → generate the HTML report → stop the app.

---

## Port-based workflow (manual steps)

Coverage is dumped **while the app is still running** via the JaCoCo TCP agent.
Multiple snapshots can be taken without restarting.

```bash
# Step 1 — Build the JAR (once per code change)
bash "scripts/Retrieve Coverage From Port/build.sh"

# Step 2 — Terminal 1: start the app with the TCP agent (keep it running)
bash "scripts/Retrieve Coverage From Port/start-with-agent.sh"

# Step 3 — Terminal 2: exercise the endpoints
bash "scripts/Retrieve Coverage From Port/exercise-endpoints.sh"

# Step 4 — Terminal 2: dump live coverage from the running JVM
bash "scripts/Retrieve Coverage From Port/dump-coverage.sh"

# Step 5 — Terminal 2: generate the HTML report
bash "scripts/Retrieve Coverage From Port/generate-report.sh"
```

> `dump-coverage.sh` connects to the agent on TCP port 6300. Steps 4 and 5 must be
> run **while the app is still running** in Terminal 1. You can dump multiple times —
> `--reset` clears the in-memory counters after each dump so the next snapshot shows
> only traffic since the last one.

---

## File-based workflow (manual steps)

Coverage is written to `target/jacoco.exec` automatically when the JVM exits.
No TCP connection needed — just stop the app and generate the report.

```bash
# Step 1 — Build the JAR (once per code change)
bash "scripts/Retrieve Coverage From File/build.sh"

# Step 2 — Terminal 1: start the app with the file agent
bash "scripts/Retrieve Coverage From File/start-with-agent.sh"

# Step 3 — Terminal 2: exercise the endpoints
bash "scripts/Retrieve Coverage From File/exercise-endpoints.sh"

# Step 4 — Terminal 1: press Ctrl+C to stop the app
#           JaCoCo flushes coverage to target/jacoco.exec on JVM exit

# Step 5 — Terminal 2: generate the HTML report
bash "scripts/Retrieve Coverage From File/generate-report.sh"
```

---

## What to look for in the report

Report opens at `target/coverage-report/index.html`.

| Class | Method | Expected coverage |
|---|---|---|
| `HelloController` | `hello()` | GREEN — called with default and named params |
| `HelloController` | `users()` | GREEN — full list retrieved |
| `HelloController` | `user()` | GREEN — found (200) and not-found (404) branches |
| `HelloController` | `create()` | GREEN — three users created |
| `HelloController` | `diagnostics()` | **RED — never called** |
| `UserService` | `findAll()` | GREEN |
| `UserService` | `findById()` | GREEN — both branches |
| `UserService` | `create()` | GREEN |
| `UserService` | `diagnostics()` | **RED — never called** |

The red methods are removal candidates — exactly the signal you would get after running
the agent against a staging environment for a week.

---

## How each agent mode works

**Port mode** — agent stays attached, serves data on demand:
```bash
java -javaagent:jacocoagent.jar=output=tcpserver,port=6300,address=0.0.0.0,includes=com.example.* \
     -jar app.jar

# Dump at any time without stopping the app
java -jar jacococli.jar dump --address localhost --port 6300 \
     --destfile target/jacoco-live.exec --reset
```

**File mode** — agent writes to disk on JVM exit:
```bash
java -javaagent:jacocoagent.jar=destfile=target/jacoco.exec,output=file,append=false,includes=com.example.* \
     -jar app.jar

# Stop the app (Ctrl+C) → jacoco.exec is written automatically
```

---

## JaCoCo vs Azul Code Inventory

| | JaCoCo (production agent) | Azul Code Inventory |
|---|---|---|
| **Cost** | Free (open source) | Commercial (Azul Intelligence Cloud) |
| **Overhead** | Low (~1–3% CPU) | Near-zero (JVM native hooks) |
| **Data collection** | Dump on demand or on exit | Continuous streaming |
| **Granularity** | Line / branch / method | Method-level |
| **Fleet aggregation** | Manual | Built-in |
| **"Last seen" timestamp** | No | Yes — per method |

JaCoCo is the right choice for open source projects and teams getting started.
Azul Code Inventory is the right choice for large fleets where zero overhead and
continuous data matter.

