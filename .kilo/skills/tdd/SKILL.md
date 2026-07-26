---
name: tdd
description: Test-driven development workflow. Red-green-refactor cycle for building features or fixing bugs test-first.
---

# TDD (Test-Driven Development)

## When to Use
- Building new features test-first
- Fixing bugs with regression tests
- User mentions "red-green-refactor"

## Workflow
1. **Red:** Write a failing test that describes the desired behavior
2. **Green:** Write the minimum code to make the test pass
3. **Refactor:** Clean up while keeping tests green

## Rules
- One test at a time
- Run tests after each change
- Never skip the refactor step
- Test names describe behavior, not implementation
- Use the repo's existing test framework (pytest, Pester, Julia Test, etc.)
