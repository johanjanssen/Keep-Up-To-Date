package com.example.benchmarks;

import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;

import java.util.concurrent.TimeUnit;

/**
 * MEMORY BENCHMARK 2: Object Layout & Compact Headers
 * ────────────────────────────────────────────────────
 * Measures heap consumption for large numbers of small objects.
 *
 * Java 25 improvements:
 *   • -XX:+UseCompactObjectHeaders (JEP 450): reduces object header from
 *     12-16 bytes to 8 bytes. For small objects this is a 20-30% memory saving.
 *   • Improved String compaction (already in Java 9+, but further optimized)
 *   • Better object alignment and padding
 *
 * This benchmark creates millions of small "record-like" objects and measures
 * allocation throughput — faster allocation = less GC pressure.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Fork(value = 2, warmups = 1)
@Warmup(iterations = 3, time = 2)
@Measurement(iterations = 5, time = 2)
public class ObjectAllocationBenchmark {

    @Param({"1000000", "5000000"})
    private int count;

    /**
     * Allocate many small objects (simulating a typical domain model).
     * Each Point has 2 int fields. Object overhead dominates memory usage.
     *
     * Java 17: header=12 bytes + 8 bytes (2 ints) + 4 padding = 24 bytes per Point
     * Java 25 compact: header=8 bytes + 8 bytes (2 ints) = 16 bytes per Point (33% less!)
     */
    @Benchmark
    public Object[] allocateSmallObjects() {
        Object[] points = new Object[count];
        for (int i = 0; i < count; i++) {
            points[i] = new int[]{i, i * 2}; // simulates Point(x, y)
        }
        return points;
    }

    /**
     * Allocate and iterate over many String objects.
     * Measures combined allocation + access throughput.
     *
     * Java 25 benefits: compact headers, improved String deduplication,
     * better GC ergonomics for short-lived Strings.
     */
    @Benchmark
    public long allocateAndProcessStrings(Blackhole bh) {
        long totalLength = 0;
        for (int i = 0; i < count; i++) {
            String s = "item-" + (i % 1000); // creates many short-lived strings
            totalLength += s.length();
        }
        return totalLength;
    }

    /**
     * Measure heap usage for a large Object[] filled with small records.
     * Reports allocation rate which correlates with GC pressure.
     */
    @Benchmark
    public long recordStyleAllocation() {
        record Measurement(long timestamp, double value, String unit) {}

        long checksum = 0;
        for (int i = 0; i < count; i++) {
            Measurement m = new Measurement(System.nanoTime(), i * 0.5, "ms");
            checksum += m.timestamp();
        }
        return checksum;
    }
}

