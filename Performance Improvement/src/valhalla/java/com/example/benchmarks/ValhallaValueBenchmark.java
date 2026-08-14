package com.example.benchmarks;

import org.openjdk.jmh.annotations.*;
import java.util.concurrent.TimeUnit;

/**
 * VALHALLA VALUE TYPES: real value records (Project Valhalla, Java 28 EA, preview)
 * ──────────────────────────────────────────────────────────────────────────────
 * Only compiled for the Java 28 image (see the "valhalla" Maven profile and
 * Dockerfile.java28) because `value record` is preview syntax that does not
 * parse on Java 17/25 javac at all.
 *
 * This is {@code ValhallaBenchmark} with ONE change: `record` → `value record`.
 * That single keyword is what actually opts the type into Valhalla's
 * scalarization/flattening — nothing else about the code changes (see
 * ValhallaBenchmark's Javadoc for why the fields are `short`, not `int`: on
 * this JVM, nullable-array flattening only engages when the record's field
 * payload plus its 1-byte null marker fits in 8 bytes, and that constraint
 * applies equally here). Method names (sumPointsRecord, computeDistances)
 * intentionally match ValhallaBenchmark so the existing compare/report
 * tooling — which keys rows by method name — lines up "Java 25, identity
 * record" against "Java 28 EA, value record" automatically.
 *
 * Expected result: Point[] becomes a genuinely flat, header-free array
 * (~8 bytes/point instead of ~16-24), so sumPointsRecord/computeDistances go
 * from "pointer-chase 5M heap objects" to "scan contiguous memory" — a real,
 * mechanically-explained win, not a JIT hand-wave.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Fork(value = 2, warmups = 1)
@Warmup(iterations = 3, time = 2)
@Measurement(iterations = 5, time = 2)
public class ValhallaValueBenchmark {

    @Param({"1000000", "5000000"})
    private int size;

    value record Point(short x, short y) {}

    /**
     * Array of value-record Points. On Java 28 EA with --enable-preview, the
     * JVM flattens this into contiguous memory — no per-element header, no
     * pointer indirection.
     */
    @Benchmark
    public long sumPointsRecord() {
        Point[] points = new Point[size];
        for (int i = 0; i < size; i++) {
            points[i] = new Point((short) i, (short) (i * 2));
        }
        long sum = 0;
        for (Point p : points) {
            sum += p.x() + p.y();
        }
        return sum;
    }

    /**
     * Distance calculation — cache-friendly iteration: points[i] is a direct
     * offset into flat memory, not a pointer chase.
     */
    @Benchmark
    public double computeDistances() {
        Point[] points = new Point[size];
        for (int i = 0; i < size; i++) {
            points[i] = new Point((short) (i % 1000), (short) ((i * 7) % 1000));
        }
        double totalDistance = 0.0;
        for (int i = 1; i < size; i++) {
            int dx = points[i].x() - points[i - 1].x();
            int dy = points[i].y() - points[i - 1].y();
            totalDistance += Math.sqrt(dx * dx + dy * dy);
        }
        return totalDistance;
    }
}
