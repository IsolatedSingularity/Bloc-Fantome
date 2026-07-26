---
name: agent-optimize
description: Meta-skill for refining agent definitions, skill collections, and scope allocation. Used by Void Lord Mon.
---

# Agent Optimize

## When to Use
- After a sprint or major repo change (rebalance agent scopes)
- When an agent's body exceeds 150 lines
- When skills overlap between agents
- When prompt caching efficiency needs improvement

## Optimization Checklist
1. **Body size:** agent definition under 150 lines?
2. **Scope clarity:** no ambiguous ownership with other agents?
3. **Skill relevance:** all assigned skills used in last 30 days?
4. **Model routing:** could this agent run on Haiku instead of Sonnet?
5. **Cache efficiency:** static context before dynamic in the agent body?
6. **Constraint completeness:** safety guardrails in place?

## Process
1. Read target agent `.kilo/agents/<name>.md`
2. List associated skills
3. Check for scope overlap with other agents
4. Produce optimization report with proposed changes
5. Wait for approval before modifying any files
6. Update `manifest/manifest.json` after changes

## Output Format
```
## Agent Optimization Report: <name>
- Body size: X lines (target: <150)
- Skills: [list]
- Scope overlap: [findings]
- Model recommendation: [Sonnet/Haiku + rationale]
- Proposed changes: [diffs]
```
