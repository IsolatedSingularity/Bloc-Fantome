---
name: julia-tensorpack
description: TensorPack custom tensor contraction, decomposition, and manipulation operations in Julia.
---

# TensorPack Operations

## When to Use
- Custom tensor contractions beyond standard DMRJulia
- Tensor decomposition (SVD, QR, eigendecomposition)
- Building custom Hamiltonians as MPOs
- Performance-critical tensor operations

## Key Operations
- Tensor contraction with index management
- SVD with truncation control
- QR decomposition for canonical forms
- Eigendecomposition for Hamiltonian diagonalization
- Reshape and permute for index reordering

## Performance Guidelines
- Pre-allocate output tensors when possible
- Use in-place operations (mutating functions with `!`) for hot loops
- Profile with `@time` and `@btime` before optimizing
- Consider BLAS threading for large contractions
