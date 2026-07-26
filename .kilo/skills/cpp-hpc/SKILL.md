---
name: cpp-hpc
description: HPC C++ patterns. Multithreading (OpenMP), multiprocessing (MPI), lean optimization, SLURM job scripts.
---

# C++ HPC Patterns

## When to Use
- Writing or optimizing C++ for high-performance workloads
- Multithreading with OpenMP or std::thread
- Multiprocessing with MPI
- SLURM job scripts for Cedar/Alliance Canada
- CMake build system setup

## Code Standards
- C++17 minimum, C++20 preferred
- `-O2` or `-O3` for release builds
- `-Wall -Wextra -Wpedantic` for all builds
- Use `const` and `constexpr` aggressively
- RAII for resource management

## Parallelism
- OpenMP: `#pragma omp parallel for` with explicit reduction
- MPI: prefer collective operations over point-to-point
- Report thread/process count and scaling characteristics
- Profile with `gprof` or `perf` before parallelizing

## Build System
- CMake with `target_link_libraries` (no manual `-l` flags)
- Separate debug and release configurations
- Use `find_package` for dependencies

## SLURM
- `--ntasks` for MPI, `--cpus-per-task` for OpenMP
- `--mem-per-cpu` with conservative estimates
- Time limits with 20% buffer
