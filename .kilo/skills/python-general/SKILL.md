---
name: python-general
description: Python optimization patterns, profiling, virtual environments, and scientific computing best practices.
---

# Python General Patterns

## When to Use
- Python code optimization and profiling
- Virtual environment and dependency management
- NumPy/SciPy numerical patterns
- Matplotlib/plotting conventions
- Code quality (ruff, mypy, pytest)

## Optimization
- Profile before optimizing (`cProfile`, `line_profiler`)
- Vectorize with NumPy before reaching for Cython/Numba
- Use generators for large data streams
- Pre-allocate arrays instead of appending

## Environment
- Use `uv` or `pip` with `requirements.txt` or `pyproject.toml`
- Repo venv at `.venv/` (never global Python)
- Pin critical versions

## Testing
- pytest as default runner
- Use fixtures for shared setup
- Parametrize for edge cases
- Keep tests fast (mock I/O, use small inputs)
