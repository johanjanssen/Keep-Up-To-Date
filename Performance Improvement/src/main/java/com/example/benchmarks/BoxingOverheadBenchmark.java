package com.example.benchmarks;

import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * MEMORY BENCHMARK 1: Boxing Overhead
 * ────────────────────────────────────
 * Demonstrates the cost of autoboxing Integer objects vs primitive int[].
 *
 * Java 25 improvements:
 *   • Compact Object Headers (-XX:+UseCompactObjectHeaders) reduces each
 *     Integer object from 16 bytes to 12 bytes header + 4 bytes payload
 *   • Project Valhalla (preview): value classes eliminate boxing entirely,
 *     allowing List<int> with zero object overhead
 *   • Improved GC (Generational ZGC) handles the object churn better
 *
 * Expected result: Java 25 with compact headers uses ~25% less heap for
 * the same ArrayList<Integer> workload. With Valhalla value types, the
 * improvement is ~75%.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Fork(value = 2, warmups = 1)
@Warmup(iterations = 3, time = 2)
@Measurement(iterations = 5, time = 2)
public class BoxingOverheadBenchmark {

    @Param({"1000000", "5000000"})
    private int size;

    /**
     * Baseline: sum using primitive int array (no boxing, minimal memory).
     */
    @Benchmark
    public long sumPrimitiveArray(Blackhole bh) {
        int[] arr = new int[size];
        for (int i = 0; i < size; i++) {
            arr[i] = i;
        }
        long sum = 0;
        for (int v : arr) {
            sum += v;
        }
        return sum;
    }

    /**
     * Boxed: sum using ArrayList<Integer> (each int boxed to Integer object).
     * On Java 17: each Integer = 16 byte header + 4 byte int = 16 bytes (aligned)
     * On Java 25 + CompactHeaders: 12 byte header + 4 byte int = 16 bytes
     * On Java 25 + Valhalla: zero boxing overhead (if value class used)
     *
     * The GC pressure from allocating millions of Integer objects is also
     * significantly reduced in newer Java versions (better escape analysis,
     * scalarization, Generational ZGC).
     */
    @Benchmark
    public long sumBoxedArrayList(Blackhole bh) {
        List<Integer> list = new ArrayList<>(size);
        for (int i = 0; i < size; i++) {
            list.add(i); // autoboxing: int → Integer
        }
        long sum = 0;
        for (Integer v : list) {
            sum += v; // unboxing: Integer → int
        }
        return sum;
    }
}

