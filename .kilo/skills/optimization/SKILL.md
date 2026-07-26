---
name: optimization
description: General code optimization techniques across languages. Profiling, algorithmic improvements, memory management, caching.
---

# Optimization Techniques

## When to Use
- Performance bottleneck investigation
- Algorithmic complexity reduction
- Memory footprint optimization
- Cache-friendly data access patterns

## Process
1. **Measure first:** profile before changing anything
2. **Identify hotspots:** focus on the 20% of code causing 80% of runtime
3. **Algorithmic fixes:** reduce O(n^2) to O(n log n) before micro-optimizing
4. **Data layout:** struct-of-arrays vs array-of-structs for cache locality
5. **Validate:** confirm optimization preserves correctness

## Language-Specific Tools
- Python: `cProfile`, `line_profiler`, `memory_profiler`
- Julia: `@time`, `@btime` (BenchmarkTools), `@profile`
- C++: `gprof`, `perf`, `valgrind --tool=callgrind`

## Anti-Patterns
- Premature optimization without profiling
- Micro-optimizing cold code paths
- Breaking readability for marginal gains
- Optimizing without a benchmark baseline
