package com.example.benchmarks;

import org.openjdk.jmh.annotations.*;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.TimeUnit;

/**
 * PERFORMANCE BENCHMARK 2: Virtual Threads (Project Loom)
 * ───────────────────────────────────────────────────────
 * Demonstrates the massive throughput improvement from Virtual Threads.
 *
 * Java 17: Only platform threads available. Each thread costs ~1MB stack.
 *          Creating 100k threads is impractical → must use thread pools.
 *
 * Java 25: Virtual threads are mature and optimized. Can create millions
 *          of concurrent tasks with minimal memory. ~200 bytes per virtual thread.
 *
 * This benchmark simulates a typical server workload: many concurrent tasks
 * that each do a small amount of I/O-bound work (simulated with sleep).
 *
 * Expected improvement: 5-50x throughput for I/O-bound concurrent workloads.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Fork(value = 1, warmups = 1)
@Warmup(iterations = 2, time = 5)
@Measurement(iterations = 3, time = 5)
public class VirtualThreadsBenchmark {

    @Param({"10000", "50000"})
    private int taskCount;

    private static final int SIMULATED_IO_MS = 1; // simulates brief I/O

    /**
     * Platform threads with a fixed thread pool (Java 17 approach).
     * Limited by pool size — tasks queue up waiting for a thread.
     */
    @Benchmark
    public long platformThreadPool() throws Exception {
        ExecutorService executor = Executors.newFixedThreadPool(
                Runtime.getRuntime().availableProcessors() * 2
        );
        AtomicLong counter = new AtomicLong();

        List<Future<?>> futures = new ArrayList<>(taskCount);
        for (int i = 0; i < taskCount; i++) {
            futures.add(executor.submit(() -> {
                simulateIoWork();
                counter.incrementAndGet();
            }));
        }

        for (Future<?> f : futures) {
            f.get();
        }
        executor.shutdown();
        return counter.get();
    }

    /**
     * Virtual threads (Java 21+).
     * Each task gets its own virtual thread — no pool size limit.
     * The JVM multiplexes millions of virtual threads onto few OS threads.
     *
     * On Java 17 this will use platform threads (fallback), demonstrating
     * the performance difference.
     */
    @Benchmark
    public long virtualThreads() throws Exception {
        ExecutorService executor;
        try {
            // Java 21+: use virtual threads via reflection so code compiles on Java 17
            executor = (ExecutorService) Executors.class
                    .getMethod("newVirtualThreadPerTaskExecutor")
                    .invoke(null);
        } catch (ReflectiveOperationException e) {
            // Java 17 fallback: cached thread pool (closest equivalent)
            executor = Executors.newCachedThreadPool();
        }

        AtomicLong counter = new AtomicLong();
        List<Future<?>> futures = new ArrayList<>(taskCount);
        for (int i = 0; i < taskCount; i++) {
            futures.add(executor.submit(() -> {
                simulateIoWork();
                counter.incrementAndGet();
            }));
        }

        for (Future<?> f : futures) {
            f.get();
        }
        executor.shutdown();
        return counter.get();
    }

    private void simulateIoWork() {
        try {
            Thread.sleep(SIMULATED_IO_MS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

