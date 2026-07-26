---
name: repo-onboard
description: Onboard a new or existing repo with Kilo Code scaffolding. Creates .kilo/, .kilocodeignore, AGENTS.md, and updates .gitignore.
---

# Repo Onboard

## When to Use
- Setting up a new repo for Kilo Code agent use
- Migrating an existing repo to the Kilo Code stack
- Standardizing repo configuration across the workspace

## Scaffolding Steps
1. Create `.kilo/` directory with `kilo.jsonc` (from Jenova template)
2. Create `.kilo/agents/` (empty or with repo-specific agents)
3. Create `.kilo/skills/` (empty or with repo-specific skills)
4. Create `.kilocodeignore` (from Jenova template, customized for repo type)
5. Create or update `AGENTS.md` with base operating rules
6. Update `.gitignore` to include `.kilo/node_modules/`, `.kilo/worktrees/`

## Customization by Repo Type
- **Scientific/Julia:** add `*.jld2`, `Results/`, `Data/` to kilocodeignore
- **Python:** add standard Python ignores
- **Web/JS:** add `dist/`, `build/`, `coverage/`
- **Config-only (Jenova):** add `archive/`, `logs/`, `identity/`

## Rules
- Never overwrite an existing `.kilo/kilo.jsonc` (repo may have custom config)
- Always check for existing AGENTS.md before creating
- Add Jenova gitignore entry if deploying as junction
