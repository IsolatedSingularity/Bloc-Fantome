---
name: python-quantum
description: Quantum circuit patterns for Qiskit, PennyLane, and Cirq. VQE, QAOA, Grover's, QEC, and QML implementations.
---

# Python Quantum Patterns

## When to Use
- Implementing quantum circuits in Qiskit, PennyLane, or Cirq
- VQE, QAOA, or other variational algorithms
- Grover's search, amplitude estimation
- Quantum error correction codes
- Quantum machine learning circuits

## Framework Patterns

### Qiskit
- Use `QuantumCircuit` for circuit construction
- `Estimator` / `Sampler` primitives (not deprecated `execute()`)
- Transpile with optimization level 2+ for hardware targets
- Use `SparsePauliOp` for Hamiltonian construction

### PennyLane
- `qml.device()` for backend selection
- `@qml.qnode` decorator for quantum functions
- Automatic differentiation with `qml.grad()`
- Parameter-shift rule for gradient estimation

### Cirq
- `cirq.Circuit()` with moment-based construction
- `cirq.Simulator()` for state vector simulation
- Noise models via `cirq.ConstantQubitNoiseModel`

## Validation
- Compare against known analytical results
- Report qubit count, circuit depth, gate count
- Test with and without noise models
