---
name: julia-dmrjulia
description: DMRJulia tensor network operations. DMRG, MPS/MPO, time evolution (TEBD, TDVP), and entanglement analysis in Julia.
---

# DMRJulia Operations

## When to Use
- Working with DMRG ground state calculations
- MPS/MPO construction and manipulation
- Time evolution (TEBD, TDVP)
- Entanglement entropy and spectrum analysis
- Bond dimension convergence studies

## Key Functions
- `dmrg()`: ground state search with convergence monitoring
- `applyMPO()`: apply operator to MPS
- `meas()`: expectation value measurements
- `entropy()`: von Neumann entanglement entropy
- `truncate()`: SVD truncation with chi control

## Patterns
- Always check convergence by comparing energies at different bond dimensions
- Report chi (bond dimension), truncation error, and sweep count
- Validate against exact diagonalization for small systems (N <= 12)
- Use JLD2 for data persistence, CSV for human-readable results

## Common Pitfalls
- Forgetting to set random seed for reproducibility
- Not checking truncation error accumulation in time evolution
- Mixing up left/right canonical forms
