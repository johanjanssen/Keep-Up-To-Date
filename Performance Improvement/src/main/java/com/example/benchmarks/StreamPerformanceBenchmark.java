package com.example.benchmarks;

import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;

import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;

/**
 * PERFORMANCE BENCHMARK 1: Stream & JIT Compiler Improvements
 * ────────────────────────────────────────────────────────────
 * Demonstrates how JIT compiler improvements across Java versions
 * make the SAME code run faster without any changes.
 *
 * Java 25 improvements:
 *   • Better auto-vectorization (C2 compiler, JEP 489)
 *   • Improved loop optimizations and escape analysis
 *   • Better inlining heuristics
 *   • Improved Stream pipeline optimization
 *   • Faster Math operations
 *
 * This is the best demo for "just upgrade Java and your code gets faster."
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Fork(value = 2, warmups = 1)
@Warmup(iterations = 3, time = 2)
@Measurement(iterations = 5, time = 2)
public class StreamPerformanceBenchmark {

    @Param({"1000000", "10000000"})
    private int size;

    private int[] data;

    @Setup
    public void setup() {
        data = IntStream.range(0, size).toArray();
    }

    /**
     * Sequential stream pipeline — filter, map, reduce.
     * Java 25's JIT compiler optimizes the lambda chain better,
     * often fusing operations and eliminating intermediate allocations.
     */
    @Benchmark
    public long streamFilterMapReduce() {
        return IntStream.of(data)
                .filter(i -> i % 2 == 0)
                .map(i -> i * 3)
                .asLongStream()
                .sum();
    }

    /**
     * Parallel stream — benefits from improved ForkJoinPool in Java 25,
     * better work-stealing, and reduced synchronization overhead.
     */
    @Benchmark
    public long parallelStreamFilterMapReduce() {
        return IntStream.of(data)
                .parallel()
                .filter(i -> i % 2 == 0)
                .map(i -> i * 3)
                .asLongStream()
                .sum();
    }

    /**
     * Manual loop — demonstrates C2 auto-vectorization improvements.
     * Java 25's JIT is better at recognizing SIMD-friendly patterns
     * and generating AVX2/AVX-512 instructions automatically.
     */
    @Benchmark
    public long manualLoopVectorizable() {
        long sum = 0;
        for (int i = 0; i < data.length; i++) {
            if (data[i] % 2 == 0) {
                sum += (long) data[i] * 3;
            }
        }
        return sum;
    }

    /**
     * Math-heavy computation — benefits from improved Math intrinsics
     * and better floating-point optimization in newer JVMs.
     */
    @Benchmark
    public double mathHeavyComputation() {
        double result = 0.0;
        for (int i = 1; i < size; i++) {
            result += Math.sqrt(i) * Math.log(i) / Math.sin(i * 0.001);
        }
        return result;
    }
}

