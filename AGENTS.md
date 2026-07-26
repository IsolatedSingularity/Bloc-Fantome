# Jenova Operating Rules

> Kilo Code auto-loads this file. All agents inherit these rules.

## Working Method
- Inspect before editing.
- Search narrowly before reading entire directories.
- State intended file changes before multi-file edits.
- Prefer the smallest correct patch.
- Do not rewrite unrelated code.
- Stop after two failed attempts at the same approach.
- Keep terminal output concise.
- Use subagents only when isolation materially helps.

## Style
- **camelCase** for new code. Existing files: match local convention.
- **ZERO em-dashes** in any output. Use commas, colons, semicolons, parentheses.
- **Banned phrases:** `architected`, `leveraged`, `enterprise`, `delve`, `translated X into Y`.

## Cache Preservation
- Structure outputs static-first, dynamic-last for Anthropic KV prefix cache.
- Never dump entire directories or brute-force `grep` on large trees.
- Use LSP/AST routing for codebase navigation when available.
- Targeted extraction over raw file reads.

## Safety
- `Jenova/` is always gitignored in target repos.
- Index before editing: read relevant files before any modification.
- Forbidden repos (listed in `context/permissions.md`) are invisible to all agents.
- No Jenova self-edit during normal work. Changes go through proper agent channels.
- Use small non-fatal terminal commands. No `exit 1` in ad hoc shells, no bare `python`.
- Max response: 300-400 words unless code/audit output requires more.
- After 3 failed attempts at the same approach, stop and report the blocker.

## Scientific Code
- Preserve mathematical meaning before optimizing.
- Separate physical assumptions from numerical assumptions.
- Report basis conventions, units, shapes, tolerances, seeds, and boundaries.
- Add or update tests for changed numerical behavior.
- Validate against an analytic limit, invariant, or independent baseline.
- Keep LaTeX exact.

## Validation
- Run the narrowest relevant tests first.
- Report the commands run and their results.
- Distinguish verified results from hypotheses.
- Never claim a test passed when it was not run.

## Moon (Paused Indefinitely)
- Moon/Raspberry Pi operations are archived. Pi is unplugged, vault sealed.
- No active Moon agents. Reference `archive/moon/` for historical context.
