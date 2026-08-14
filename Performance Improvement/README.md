# 🚀 Performance Improvement — Java 17 vs 25 vs 28 EA (Valhalla)

> **Demonstrate that upgrading Java gives you FREE performance gains — same code, faster execution, less memory.**
> Plus the one part that needs a code change: Valhalla value types need a one-keyword opt-in (`record` →
> `value record`) — and, in the current Java 28 EA preview, a field-width limit before the JVM will actually
> flatten the array. Both are demonstrated and measured, not assumed from the JEP text.

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
| **ValhallaBenchmark** | `record Point(...)` in an array — run on Java 25 as the baseline | Baseline for the value-record comparison below, both speed and GC-profiled memory. |
| **ValhallaValueBenchmark** *(Java 28 only, `-Pvalhalla` build)* | The exact same benchmark, `record` → `value record` | Real language feature, honestly-reported preview performance and memory (see below). |

> Two benchmarks were removed after measurement didn't back up their claims — see
> "What we cut, and why" below rather than a Java-version-improvement fairy tale.

---

## 🔮 Valhalla: what's actually true right now

`ValhallaBenchmark` and `ValhallaValueBenchmark` are **the same code**, except one uses
`record Point(short x, short y) {}` and the other uses `value record Point(short x, short y) {}`.
That's the entire Valhalla story for application developers — same syntax, one keyword.

The important thing this repo verified by actually running it, not by assuming the JEP text:

**The `value` keyword alone isn't enough yet — the record also has to fit a size limit.** Earlier
versions of this benchmark used `record Point(int x, int y)` and measured *no* memory win: the `value
record` array sometimes used more memory than the plain one, not less. Digging into why (Docker,
`openjdk:28-ea-trixie`, `-XX:+UnlockDiagnosticVMOptions -XX:+PrintFlagsFinal`) turned up the actual
cause: this JVM's array-flattening only engages when a value record's fields, plus the 1-byte null
marker every element in a plain (nullable) array needs, fit inside a single 8-byte word. Two `int`s are
8 bytes on their own — one byte over the line — and never flatten, with or without every flattening flag
(`UseArrayFlattening`, `UseFieldFlattening`, `UseAtomicValueFlattening`, `UseNullableValueFlattening`, …)
forced on. Two `short`s are 4 bytes and flatten every time, with the JVM's *default* flags — no tuning
needed. (A third-party write-up hit the same wall independently and used `short x, short y, short z`
for the same reason — see [First look at Java Valhalla flattening](https://joemwangi985269.substack.com/p/first-look-at-java-valhalla-flattening).)

With that one field-width change, every workflow run now measures `ValhallaValueBenchmark` against
`ValhallaBenchmark` twice — once for speed, once with `-prof gc` for bytes allocated per operation — and
both come back a real win, not a coin flip: **~60% less memory** (20 → 8 bytes per `Point`, exactly the
"drop the object header" story JEP 401 promises) and **4-8x faster**, because summing/iterating flat
memory has no pointer to chase. This is measured from live JMH data on every run, not a remembered
anecdote or a number copied from the JEP — the published report only calls this section a win if the
*current* run's numbers back it up, same as before.

The language feature (JEP 401, Value Classes and Objects) and the runtime optimization it depends on
both work correctly here — the catch was a today's-preview-build size ceiling on which records are
flattenable, not a fundamental limitation of Valhalla. `Point` staying at two coordinates in `short`
range (0-999 for `computeDistances`, and deliberately overflow-wrapped for `sumPointsRecord` — identical
truncation on both sides of the comparison) keeps this an honest "one keyword changed" test rather than
a differently-shaped benchmark on each side.

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

# Valhalla baseline: plain record, on Java 25
echo "=== Java 25, plain record ==="
docker run --rm -v "$(pwd)/results:/results" bench:java25 \
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
2. **`benchmark-25-vs-28`** — the Valhalla `record` vs `value record` comparison described above
   (speed + GC-profiled memory).
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
   keyword: `value`), and this run shows the JEP 401 payoff for real: ~60% less memory and 4-8x faster
   for a flattenable `Point`. The catch found and documented here: today's preview build only flattens
   records that fit an 8-byte (fields + null marker) size ceiling — `short` fields qualify, `int` fields
   don't, regardless of flags. Worth knowing before reaching for `value record` on a wider type.
5. **Not everything about a new JDK is automatically faster** — two benchmarks were cut from this suite
   because measurement didn't back up the claim. That's the standard this report holds itself to.
