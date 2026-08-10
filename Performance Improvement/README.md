# 🚀 Performance Improvement — Java 17 vs 25 vs 28 EA (Valhalla)

> **Demonstrate that upgrading Java gives you FREE performance gains — same code, faster execution, less memory.**

This module runs identical JMH benchmarks on **Java 17**, **Java 25**, and **Java 28 EA** (with Project Valhalla) to show measurable improvements in performance and memory consumption.

---

## 📊 Five Benchmarks

### Memory Benchmarks

| # | Benchmark | What it measures | Java 25 / 28 advantage |
|---|-----------|-----------------|------------------------|
| 1 | **BoxingOverheadBenchmark** | ArrayList\<Integer\> vs int[] — cost of autoboxing | Compact Object Headers reduce overhead. Valhalla (Java 28) eliminates boxing. |
| 2 | **ObjectAllocationBenchmark** | Allocating millions of small objects | Compact headers save 4 bytes per object (20-30%). ZGC handles pressure better. |

### Performance Benchmarks

| # | Benchmark | What it measures | Java 25 / 28 advantage |
|---|-----------|-----------------|------------------------|
| 3 | **StreamPerformanceBenchmark** | Stream pipelines, loops, math | Better JIT auto-vectorization, improved inlining. Same code 10-40% faster. |
| 4 | **VirtualThreadsBenchmark** | Concurrent I/O-bound workloads | Virtual Threads: 100k tasks use ~20MB vs ~100GB. 5-50x throughput. |

### Valhalla Benchmark (Java 25 vs 28 EA)

| # | Benchmark | What it measures | Java 28 Valhalla advantage |
|---|-----------|-----------------|---------------------------|
| 5 | **ValhallaBenchmark** | Point records in arrays, distance calculation, Mandelbrot | Value classes flatten into arrays: 3x less memory, 2-3x faster (no pointer-chasing). |

---

## 🏗️ Quick Start

### Run with Docker (recommended for conference demos)

```bash
# Build all three images
docker build -f Dockerfile.java17 -t bench:java17 .
docker build -f Dockerfile.java25 -t bench:java25 .
docker build -f Dockerfile.java28 -t bench:java28 .

# Run quick benchmark (single fork, reduced iterations for demo)
mkdir -p results

echo "=== Java 17 ===" 
docker run --rm -v "$(pwd)/results:/results" bench:java17 \
  -f 1 -wi 2 -i 3 ".*StreamPerformance.*"

echo "=== Java 25 ==="
docker run --rm -v "$(pwd)/results:/results" bench:java25 \
  -f 1 -wi 2 -i 3 ".*StreamPerformance.*"

# Valhalla comparison
echo "=== Java 28 EA (Valhalla) ==="
docker run --rm -v "$(pwd)/results:/results" bench:java28 \
  -f 1 -wi 2 -i 3 ".*Valhalla.*"
```

### Run all benchmarks with comparison script

```bash
chmod +x scripts/run-benchmarks.sh
./scripts/run-benchmarks.sh
```

### Run specific benchmark

```bash
# Only stream performance
./scripts/run-benchmarks.sh ".*StreamPerformance.*"

# Only virtual threads
./scripts/run-benchmarks.sh ".*VirtualThreads.*"

# Only memory (boxing + allocation)
./scripts/run-benchmarks.sh ".*Boxing.*|.*ObjectAllocation.*"
```

---

## 🎯 What Each Benchmark Demonstrates

### 1. Boxing Overhead (Memory)

```java
// This innocent-looking code creates millions of Integer wrapper objects:
List<Integer> list = new ArrayList<>();
for (int i = 0; i < 5_000_000; i++) {
    list.add(i);  // autoboxing: each int becomes a 16-byte Integer object
}
```

**Java 17:** Each `Integer` = 12-byte header + 4-byte int + padding = **16 bytes**  
**Java 25 + Compact Headers:** 8-byte header + 4-byte int + padding = **12 bytes** (25% less)  
**Java 25 + Valhalla (preview):** Zero boxing = **4 bytes** per element (75% less!)

### 2. Object Allocation (Memory)

Small domain objects (Point, Measurement, etc.) are dominated by header overhead.
Java 25's compact object headers (JEP 450) save 4 bytes per object — significant
when you have millions of them.

### 3. Stream Performance (Speed)

The **exact same code** runs faster on Java 25 because:
- C2 JIT compiler has better auto-vectorization (uses AVX2/AVX-512)
- Improved loop optimizations and escape analysis
- Better inlining decisions
- Optimized Stream pipeline internals

**No code changes needed — just upgrade the JVM.**

### 4. Virtual Threads (Speed/Throughput)

```java
// Java 17: limited by thread pool size, each thread = ~1MB
ExecutorService exec = Executors.newFixedThreadPool(16);

// Java 25: unlimited virtual threads, each = ~200 bytes
ExecutorService exec = Executors.newVirtualThreadPerTaskExecutor();
```

For I/O-bound workloads (HTTP servers, database queries), virtual threads
provide 5-50x throughput improvement with the same hardware.

---

## 🔮 5. Valhalla Value Classes (Java 28 EA)

```java
// Java 17/25: records are regular objects — heap-allocated, with 12-16 byte headers
record Point(int x, int y) {}
Point[] points = new Point[5_000_000];
// → 5M heap objects, 5M pointers, ~120 MB memory, terrible cache behavior

// Java 28 Valhalla: value classes are identity-free — flattened into arrays
// (preview feature, same syntax, radically different runtime behavior)
// → 0 heap objects, contiguous memory, ~40 MB, cache-friendly sequential access
```

**Why this matters:**
- **3x less memory** for arrays of small objects (Points, Complex numbers, Colors, etc.)
- **2-3x faster** iteration because data is contiguous (no pointer-chasing cache misses)
- **Zero GC pressure** — value types are never individually garbage collected
- **Same code** — just add `value` keyword to your record/class declaration

---

## 📈 Expected Results

### Java 17 → Java 25 (same code, free improvement)

| Benchmark | Java 17 | Java 25 | Improvement |
|-----------|---------|---------|-------------|
| streamFilterMapReduce | ~18 ms | ~12 ms | **~33% faster** |
| parallelStreamFilterMapReduce | ~5 ms | ~3 ms | **~40% faster** |
| manualLoopVectorizable | ~8 ms | ~5 ms | **~35% faster** |
| mathHeavyComputation | ~45 ms | ~35 ms | **~22% faster** |
| sumBoxedArrayList (5M) | ~55 ms | ~40 ms | **~25% faster** (less GC) |
| virtualThreads (50k tasks) | ~25s | ~500ms | **~50x faster** |
| platformThreadPool (50k tasks) | ~25s | ~24s | ~same |

*Results vary by hardware. Run on your own machine for accurate numbers.*

### Java 25 → Java 28 EA (Valhalla value types)

| Benchmark | Java 25 | Java 28 EA | Improvement |
|-----------|---------|------------|-------------|
| sumPointsRecord (5M) | ~55 ms | ~18 ms | **~3x faster** |
| sumPointsFlattened (5M) | ~10 ms | ~10 ms | same (already flat) |
| computeDistances (5M) | ~70 ms | ~25 ms | **~2.8x faster** |
| mandelbrotComputation | ~45 ms | ~30 ms | **~33% faster** |

*The `sumPointsFlattened` benchmark uses primitive arrays and serves as
the theoretical best case — Valhalla's `sumPointsRecord` approaches this
performance with the ergonomics of real objects.*

---

## 🤖 GitHub Actions

The workflow `.github/workflows/benchmark-java-versions.yml` runs two parallel jobs:

1. **Java 17 vs 25** — core benchmarks (boxing, allocation, streams, virtual threads)
2. **Java 25 vs 28 EA** — Valhalla-specific benchmarks (value class flattening)

---

## 🛡️ Key Takeaways

1. **Free performance** — Upgrading Java 17→25 gives 10-40% speed improvement with zero code changes
2. **Less memory** — Compact Object Headers reduce heap by 20-30% for object-heavy workloads
3. **Virtual Threads** — Revolutionary for I/O-bound apps: handle millions of concurrent connections
4. **Better GC** — Generational ZGC minimizes pause times and handles allocation pressure better
5. **Valhalla (Java 28)** — Value classes eliminate boxing overhead entirely: 3x less memory, 2-3x faster for small objects in arrays
6. **Just upgrade** — No code migration needed for most improvements (Valhalla benefits require adding `value` keyword)







