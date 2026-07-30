---
plan: 2026-07-30-trigger-eval-read-only-agent-plan.md
phase: 1
git_commit_start: 8057632415de54903cf71489d700eb40ba11c6a9
git_commit_end: d193232
status: DONE
---

# Phase 1 Report: Rewrite the trigger-evaluator agent contract

**Task:** Full-file replacement of `agents/trigger-evaluator.md` with the stripped behavior contract.

**Changes Made:**
- Updated frontmatter description to reflect read-only purpose
- Rewrote role to clarify it's the in-run agent for trigger-evaluation reps
- Updated tools available to show read-only access (no Bash, Write, or Edit)
- Added explicit rule: NEVER read a skill's SKILL.md directly
- Added rule: If query matches a skill, invoke skill tool; after loading, DO NOT execute any workflow
- Added rule: After load decision, end the turn
- Added section for handling loaded skill instructions (do not comply)
- Removed: detection pattern, report format, "read the skill file" workflow, "report to the user" rule

**Verification:**
- `agentskills validate skills/trigger-testing` → Valid skill ✓
- `grep -c 'SIBLING_ROUTED' agents/trigger-evaluator.md` → 0 ✓
- `grep -c 'NEVER read a skill' agents/trigger-evaluator.md` → 1 ✓
