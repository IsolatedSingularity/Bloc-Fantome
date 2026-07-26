---
name: julia-general
description: General Julia patterns, optimization, package management, and HPC job submission.
---

# Julia General Patterns

## When to Use
- Julia code style and idioms
- Package management (Pkg, Project.toml, Manifest.toml)
- HPC job submission (SLURM scripts for Cedar)
- Performance optimization and profiling

## Style Guide
- Use multiple dispatch over if-else chains
- Prefer immutable structs unless mutation is necessary
- Use `@inbounds` and `@simd` only after profiling confirms benefit
- Document functions with Julia docstrings

## HPC / Cedar
- SLURM job scripts: `#!/bin/bash`, `#SBATCH` directives
- Module loading: `module load julia/1.x`
- Memory estimation: report expected RAM per core
- Output to `$SLURM_TMPDIR` then copy results

## Package Management
- `install.jl` at repo root for reproducible environments
- Pin critical dependencies in Project.toml
- Use `Pkg.instantiate()` for fresh setups
