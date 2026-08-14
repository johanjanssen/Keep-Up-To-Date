package com.example.benchmarks;

import org.openjdk.jmh.annotations.*;
import java.util.concurrent.TimeUnit;

/**
 * VALHALLA BASELINE: plain identity records (Project Valhalla, Java 28 EA)
 * ──────────────────────────────────────────────────────────────────────────
 * This class uses an ordinary `record Point(short x, short y)` — the same
 * code you'd write today. It's run on Java 25 to produce the "before" side
 * of the Valhalla comparison: a plain record is an identity class, so this
 * is what `Point[]` costs, in time and memory, without opting into value
 * types.
 *
 * Why `short`, not `int`: verified empirically (Docker, openjdk:28-ea-trixie,
 * javac/java --enable-preview) that this JVM's current nullable-array
 * flattening only engages when the record's total field payload fits in a
 * single machine word alongside its 1-byte null marker — 8 bytes total, so
 * ≤7 bytes of fields. Two `int`s (8 bytes) sit exactly one byte over that
 * line and never flatten, with or without `-XX:+UnlockDiagnosticVMOptions
 * -XX:+UseArrayFlattening -XX:+UseFieldFlattening` forced on; two `short`s
 * (4 bytes) flatten every time, with the JVM's default flags, no tuning
 * needed. This isn't a workaround for a benchmark trick — it's a real,
 * documented constraint of today's preview implementation, and the same
 * threshold that a `short x, short y, short z` record needed in independent
 * third-party testing (see README). `computeDistances` already bounds its
 * generated coordinates to 0-999, well inside `short`'s range; the deliberate
 * overflow-wrapping `(short)` casts in `sumPointsRecord` are the only other
 * change from the `int` version, and they're identical on both sides of the
 * comparison, so this stays a fair "one keyword changed" test.
 *
 * The actual Valhalla payoff — recompiling the *same shape* of code as
 * `value record Point(...)` — lives in {@code ValhallaValueBenchmark}
 * (src/valhalla/java), which only compiles under the Java 28 image via the
 * "valhalla" Maven profile. That class uses the same benchmark method names
 * (sumPointsRecord, computeDistances) on purpose, so the comparison scripts
 * line the two up automatically: Java 25 (this class) vs Java 28
 * (ValhallaValueBenchmark) is the real "what did Valhalla buy us" story,
 * for both speed and memory (GC-profiled allocation).
 *
 * Expected results once you opt in with `value`:
 *   record Point[]       = array of pointers to heap objects (~16-24 bytes/point)
 *   value record Point[] = flat array of data (~8 bytes/point, no indirection)
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Fork(value = 2, warmups = 1)
@Warmup(iterations = 3, time = 2)
@Measurement(iterations = 5, time = 2)
public class ValhallaBenchmark {

    @Param({"1000000", "5000000"})
    private int size;

    record Point(short x, short y) {}

    /**
     * Array of Point records. Plain records are identity objects, so this
     * array is really Point[] = pointers to 5M separately-headed heap objects.
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
     * Distance calculation — cache-unfriendly iteration: each points[i]
     * access is a pointer chase to a separately allocated object.
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
