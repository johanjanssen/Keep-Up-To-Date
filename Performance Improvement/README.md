# 🚀 Performance Improvement — Java 17 vs 25 vs 28 EA (Valhalla)

> **Demonstrate that upgrading Java gives you FREE performance gains — same code, faster execution, less memory.**
> And be honest about the one part that isn't free (yet): Valhalla value types need a one-keyword code change,
> and its performance payoff isn't fully realized in the current Java 28 EA preview build.

This module runs JMH benchmarks on **Java 17**, **Java 25**, and **Java 28 EA** (with Project Valhalla
preview support) to show measurable, *verified* improvements in performance and memory consumption.

**Results are published as HTML overview tables on GitHub Pages** after every workflow run:
`https://johanjanssen.github.io/Keep-Up-To-Date/Benchmarks/`. The report is generated straight from the
JMH JSON output — a comparison only shows up as a headline "improvement" if the newer version measured
at least 3% better; anything flat or regressed is left out rather than presented as a win it isn't.

---

## 📊 Benchmarks

### Memory — Java 17 → Java 25

| Benchmark | What it measures | Why Java 25 wins |
|-----------|-----------------|------------------|
| **BoxingOverheadBenchmark** | `ArrayList<Integer>` vs `int[]` — cost of autoboxing | Compact Object Headers (JEP 519, product feature since Java 25) shrink every `Integer`'s header. |
| **ObjectAllocationBenchmark** | Millions of small objects/records/strings | Same compact-header saving, applied to arrays and records. |

### Speed — Java 17 → Java 25

| Benchmark | What it measures | Why Java 25 wins |
|-----------|-----------------|------------------|
| **StreamPerformanceBenchmark** | A normal filter/map/reduce stream pipeline, and a `sqrt`/`log`/`sin`-heavy loop | Math intrinsics and general JIT/runtime improvements. `mathHeavyComputation` was the standout in local testing (~40% faster). |
| **VirtualThreadsBenchmark** | Many short blocking I/O-bound tasks, platform-thread pool vs virtual threads | Virtual threads (JEP 444) remove the thread-per-task memory ceiling entirely. |

### Valhalla — Java 25 → Java 28 EA (preview)

| Benchmark | What it measures | Status |
|-----------|-----------------|--------|
| **ValhallaBenchmark** | `record Point(...)` in an array — run on Java 25 as the baseline | Baseline for the value-record comparison below. |
| **ValhallaValueBenchmark** *(Java 28 only, `-Pvalhalla` build)* | The exact same benchmark, `record` → `value record` | Real language feature, honestly-reported preview performance (see below). |

> Two benchmarks were removed after measurement didn't back up their claims — see
> "What we cut, and why" below rather than a Java-version-improvement fairy tale.

---

## 🔮 Valhalla: what's actually true right now

`ValhallaBenchmark` and `ValhallaValueBenchmark` are **the same code**, except one uses
`record Point(int x, int y) {}` and the other uses `value record Point(int x, int y) {}`.
That's the entire Valhalla story for application developers — same syntax, one keyword.

The important thing this repo verified by actually running it, not by assuming the JEP text:

**The `value` keyword alone doesn't guarantee a win yet, in this preview.** We measured
`ValhallaValueBenchmark` against two independent Valhalla-enabled JDK builds (mainline `openjdk:28-ea`
and the dedicated `jdk.java.net/valhalla` early-access build). In both, the array-flattening
optimization did not consistently engage: the `value record` array sometimes used **more** memory
(56 MB vs 40 MB per 2M-element array in one GC-profiled run) and ran **slower**, not less/faster.
The language feature (JEP 401, Value Classes and Objects) works correctly here; the runtime
optimization it depends on for the performance payoff is still catching up in this EA build.
No memory comparison for Valhalla is wired into the automated report — only speed is benchmarked
there; the memory figure above comes from a one-off local GC-profiled run.

The published report shows this run's real numbers, with that context attached, instead of a promised
`3x less memory, 2-3x faster` figure that a curious audience member could disprove on their own laptop.

---

## ✂️ What we cut, and why

Two benchmarks were removed from `StreamPerformanceBenchmark` after local measurement (Temurin 17 vs 25,
run directly, then cross-checked with the actual `-XX:+UseCompactObjectHeaders` flag used in CI):

- **`manualLoopVectorizable`** — a hand-written "sum every even number × 3" loop, claimed to benefit from
  "better C2 auto-vectorization". There is no delivered JEP for implicit auto-vectorization of ordinary
  scalar loops in this JDK range — the real, explicit vectorization story is the incubating
  **Vector API** (JEP 489/508), which requires different code entirely. Measured: **11% slower** on
  Java 25 in local testing, and too small in absolute magnitude (sub-millisecond) to trust either way.
- **`parallelStreamFilterMapReduce`** — dominated by `ForkJoinPool` common-pool sizing and core count,
  not JVM version. Measured **23% slower** on Java 25 on a CPU-constrained runner — exactly the kind of
  environment a GitHub Actions runner is. Not a reproducible "Java got faster" story.

Rather than swap in a different benchmark to force a win, these were simply removed: `streamFilterMapReduce`
and `mathHeavyComputation` cover the "JIT/runtime improved" story with numbers that held up.

Also removed: `mandelbrotComputation` from the Valhalla suite — it never used `Point`/records/value types
at all (just raw `double`s), so Valhalla had nothing to flatten. Keeping it there implied a benefit that
the code couldn't possibly demonstrate.

---

## 🏗️ Quick Start

### Run with Docker (recommended for conference demos)

```bash
# Build all three images
docker build -f Dockerfile.java17 -t bench:java17 .
docker build -f Dockerfile.java25 -t bench:java25 .
docker build -f Dockerfile.java28 -t bench:java28 .   # -Pvalhalla, needs a Valhalla-capable Java 28 EA javac

# Run quick benchmark (single fork, reduced iterations for demo)
mkdir -p results

echo "=== Java 17 ==="
docker run --rm -v "$(pwd)/results:/results" bench:java17 \
  -f 1 -wi 2 -i 3 ".*StreamPerformance.*"

echo "=== Java 25 ==="
docker run --rm -v "$(pwd)/results:/results" bench:java25 \
  -f 1 -wi 2 -i 3 ".*StreamPerformance.*"

# Valhalla: same record, unchanged, on Java 28 EA (expect ~0% difference)
echo "=== Java 28 EA, plain record ==="
docker run --rm -v "$(pwd)/results:/results" bench:java28 \
  -f 1 -wi 2 -i 3 "\.ValhallaBenchmark\."

# Valhalla: value record, on Java 28 EA (the real comparison)
echo "=== Java 28 EA, value record ==="
docker run --rm -v "$(pwd)/results:/results" bench:java28 \
  -f 1 -wi 2 -i 3 "\.ValhallaValueBenchmark\."
```

### Run all benchmarks with comparison script

```bash
chmod +x scripts/run-benchmarks.sh
./scripts/run-benchmarks.sh
```

### Generate the HTML report locally

```bash
python3 scripts/generate-html-report.py results/ results/html/index.html
open results/html/index.html   # or xdg-open on Linux
```

---

## 🎯 What Each Benchmark Demonstrates

### Boxing Overhead & Object Allocation (Memory)

```java
List<Integer> list = new ArrayList<>();
for (int i = 0; i < 5_000_000; i++) {
    list.add(i);  // autoboxing: each int becomes an Integer object
}
```

Compact Object Headers (JEP 450 → JEP 519, a stable *product* feature as of Java 25 — no experimental
unlock flag needed) shrink every object's header from 12–16 bytes down to 8. For millions of small
boxed `Integer`s or domain records, that's a real, measured double-digit percentage of heap.

### Stream & Math Performance (Speed)

The **exact same code** runs faster on Java 25 for `mathHeavyComputation` — no code changes needed,
just a JVM upgrade. `streamFilterMapReduce` is included as the "ordinary business logic" baseline; it
measured roughly flat, and the report says so rather than rounding it up to a win.

### Virtual Threads (Speed/Throughput)

```java
// Java 17: limited by thread pool size, each thread = ~1MB
ExecutorService exec = Executors.newFixedThreadPool(16);

// Java 21+: virtual threads, each = ~a few hundred bytes
ExecutorService exec = Executors.newVirtualThreadPerTaskExecutor();
```

For I/O-bound workloads (HTTP servers, database queries), virtual threads remove the thread-pool
ceiling entirely — this is the largest, most reliable win in the whole suite.

---

## 🤖 GitHub Actions

`.github/workflows/benchmark-java-versions.yml` runs three jobs:

1. **`benchmark-17-vs-25`** — boxing, allocation, streams, virtual threads (speed + GC-profiled memory).
2. **`benchmark-25-vs-28`** — the Valhalla `record` vs `value record` comparison described above.
3. **`publish-report`** — downloads both jobs' raw JSON, builds the HTML overview tables, and publishes
   them to `https://johanjanssen.github.io/Keep-Up-To-Date/Benchmarks/`.

The Pages publish step uses `peaceiris/actions-gh-pages` with `destination_dir: Benchmarks` and
`keep_files: true` rather than `actions/deploy-pages`, because this repo has several other workflows
publishing to the same Pages site (JaCoCo, security scan comparison, the reveal.js deck) — `deploy-pages`
replaces the *entire* site on every run, which was silently wiping out each other's content. See those
workflows for the same fix. **First-time setup:** the repo's Pages source needs to be set to
"Deploy from a branch → `gh-pages`" under Settings → Pages (instead of "GitHub Actions").

---

## 🛡️ Key Takeaways

1. **Free performance** — Upgrading Java 17→25 measurably speeds up math-heavy code and shrinks the
   heap for object-heavy workloads, with zero code changes.
2. **Virtual Threads** — the single biggest, most reliable win here for I/O-bound applications.
3. **Compact Object Headers** — now a stable product feature (JEP 519); meaningfully less heap for
   boxed values and small domain objects.
4. **Valhalla (Java 28, preview)** — the language feature is real and demonstrated correctly (one
   keyword: `value`). The performance payoff described in JEP 401 is not yet consistently realized in
   the current early-access build — worth watching, not yet worth promising.
5. **Not everything about a new JDK is automatically faster** — two benchmarks were cut from this suite
   because measurement didn't back up the claim. That's the standard this report holds itself to.
