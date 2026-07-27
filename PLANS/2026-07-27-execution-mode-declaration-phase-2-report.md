---
artifact: implementation-report
date: 2026-07-27
plan: PLANS/2026-07-27-execution-mode-declaration-plan.md
phase: 2
status: DONE
git_commit_start: 1e1df498dec1f16685a22bb666062f87d9199abb
git_commit_end: 649a9fea5b49fab894d40e504ec280976b2f62dc
---

# Phase 2: Consume the Declaration in plan-to-execution and iterating-plans — Implementation Report

## Summary

Replaced plan-to-execution's inference-based inline-only rule with consumption of the plan-declared `**Execution:** subagent | inline` convention (Plan Consumption Contract item 3, rewritten Delegation Safety, Workflow steps 2 and 4, Rationalizations, Red Flags, description). Extended iterating-plans' step-6 declaration-consistency check to cover execution-mode declarations and the `inline` ⇒ `none` pairing, plus a new red flag. Updated the AGENTS.md plan-to-execution paragraph to reference the declaration. All 7 automated criteria pass.

## Changes Made

#### 1. plan-to-execution consumes the declaration
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: Plan Consumption Contract lead-in changed to "three conventions ... all are owned and documented" and item 3 (Execution mode) appended. Delegation Safety exception-class paragraph replaced with the declaration-based version (subagent-by-default, inline runs in main session, inline implies `**Parallel group:** none`). Workflow step 2 now extracts the `**Execution:**` declaration (absent means `subagent`) instead of identifying inline-only phases. Workflow step 4's inline bullet reworded to "for each phase declared `inline`" with the NEVER-dispatch/NEVER-concurrent sentence deleted. The two inline-related Rationalizations rows replaced with the authoritative-declaration versions. The two named Red Flags replaced ("This phase looks inline to me even though the plan says `subagent` — I'll reclassify it" added; "The executor can run the pressure-test subagents via headless processes instead" kept verbatim per the plan). Description: "dispatch a pressure-test campaign or test-only phase to a subagent executor," → "reclassify a plan-declared phase's execution mode," and keyword "inline phase." → "inline phase, execution mode declaration."

#### 2. iterating-plans step-6 check extended
**File**: `skills/iterating-plans/SKILL.md`
**Changes**: Step 6 sentence replaced verbatim with the version covering `**Execution:**` declarations, both declarations per phase, and the `inline` ⇒ `**Parallel group:** none` pairing. Red Flags list appended with "I only renamed/split a phase — no need to re-check the execution-mode declarations".

#### 3. AGENTS.md documentation
**File**: `AGENTS.md`
**Changes**: "Phases whose work itself spawns subagents" → "Phases declaring `**Execution:** inline`" in the plan-to-execution paragraph, parenthetical examples kept.

## Verification

| Criterion | Command | Result |
|-----------|---------|--------|
| plan-to-execution consumes | `rg -n 'Execution mode' skills/plan-to-execution/SKILL.md` | PASS |
| plan-to-execution inference removed | `! rg -n 'Identify inline-only phases' skills/plan-to-execution/SKILL.md` | PASS |
| plan-to-execution declaration extract | `rg -n "absent means \`subagent\`" skills/plan-to-execution/SKILL.md` | PASS |
| iterating-plans extended | `rg -n 'execution-mode declarations' skills/iterating-plans/SKILL.md` | PASS |
| AGENTS.md updated | `rg -n 'Execution:\*\* inline' AGENTS.md` | PASS |
| AGENTS.md numbered list intact | `rg -c '^[0-9]+\. \*\*' AGENTS.md` returns 7 | PASS |
| No placeholder vocabulary | `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/plan-to-execution/SKILL.md skills/iterating-plans/SKILL.md` | PASS |

Relevant output excerpts:

```text
$ rg -n 'Execution mode' skills/plan-to-execution/SKILL.md
23:3. **Execution mode.** A phase declares `**Execution:** subagent | inline` in its Overview. ...

$ rg -n 'Identify inline-only phases' skills/plan-to-execution/SKILL.md
(no matches, exit 1)

$ rg -n "absent means \`subagent\`" skills/plan-to-execution/SKILL.md
57:2. **Read the plan and compute the schedule.** ... Extract each phase's `**Execution:**` declaration (absent means `subagent`). ...

$ rg -n 'execution-mode declarations' skills/iterating-plans/SKILL.md
55:- "I only renamed/split a phase — no need to re-check the execution-mode declarations"

$ rg -n 'Execution:\*\* inline' AGENTS.md
19:**plan-to-execution** orchestrates step 7 ... Phases declaring `**Execution:** inline` (pressure-test campaigns, ...

$ rg -c '^[0-9]+\. \*\*' AGENTS.md
7

$ rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/plan-to-execution/SKILL.md skills/iterating-plans/SKILL.md
(no matches, exit 1)
```

Manual Verification items are listed here unchecked, for the human:

- [ ] plan-to-execution's Delegation Safety no longer contains any inference or override language — classification is purely declaration-consumption
- [ ] The `inline` ⇒ `none` pairing appears in iterating-plans' step-6 check with the same meaning as in writing-plans

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| Step 4 bullet edit: replace the first sentence and delete the NEVER sentence, "keeping the rest of the bullet" | Also renamed the bullet label from `**Inline-only phase:**` to `**Inline phase:**` | The Delegation Safety rewrite (same plan change) eliminated the "inline-only phase" term entirely; leaving the old label would strand a dead term the plan's own rewrite removed from every other location. |

## Issues & Concerns

- Out-of-scope observation (NOT changed): the Red Flag "The test phase changes no files, so it can join the parallel group" was kept because the plan named only two red flags for replacement. Its Rationalizations-table counterpart was replaced with declaration-defect language, so the red flag and the new rationalization row now coexist with slightly different framings. Cosmetic; the human reviewer may want to confirm intent.
- The description rewrite removed the "pressure test phase, test-only phase" dispatch-temptation symptom in favor of "reclassify a plan-declared phase's execution mode" — this is exactly what the plan specified; noted only so the reviewer is aware the trigger surface changed.

## Follow-ups

- Human to confirm the two Manual Verification items above before Phase 3 starts (per the plan's Implementation Note).
- Reviewer may wish to check whether Phase 1's writing-plans text (parallel group `convention-text`, merged separately) and this phase's text agree on the `inline` ⇒ `none` wording — that is Manual Verification item 2.
