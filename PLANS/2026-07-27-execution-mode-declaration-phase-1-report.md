---
artifact: implementation-report
date: 2026-07-27
plan: PLANS/2026-07-27-execution-mode-declaration-plan.md
phase: 1
status: DONE_WITH_CONCERNS
git_commit_start: 1e1df498dec1f16685a22bb666062f87d9199abb
git_commit_end: <this report is committed in the phase commit; the phase commit SHA is reported to the controller>
---

# Phase 1: Emit the Execution-Mode Declaration from writing-plans — Implementation Report

## Summary

All six Changes Required items were applied exactly as written to `skills/writing-plans/SKILL.md` and `skills/writing-plans/references/plan-template.md`: the `**Execution:** subagent | inline` declaration in the template phase Overview, the extended independence rule plus the new execution-mode rule in template Rules, the workflow step-3 assessment, the two checklist items, the rationalization row, the red flag, and the description symptom. Six of eight automated criteria pass cleanly. Two criteria fail *as written*: one has a threshold inconsistent with the plan's own Changes Required (a plan defect), and one fails on pre-existing anti-placeholder lines that quote the scanned vocabulary (nothing was introduced). Evidence below; both are routed as follow-ups rather than silently fixed, since fixing either would require deviating from the plan's exact text.

## Changes Made

#### 1. Template: phase Overview gains the declaration + Rules extended
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: Added `**Execution:** subagent | inline` line after `**Parallel group:** <name> | none` in the phase Overview (Change 1). In `## Rules`, inserted the integrated-result disqualifier ("its dependency is ordering, not files") into the independence rule and appended the new "Every phase declares its execution mode" rule with the `inline` ⇒ `none` pairing (Change 2). Replacement text verbatim from the plan.

#### 2. Skill: workflow, checklist, rationalization, red flag, description
**File**: `skills/writing-plans/SKILL.md`
**Changes**: Workflow step 3 gained the integrated-result sentence and a new paragraph on the `**Execution:**` declaration (Change 3). The parallel-group checklist item was extended and a new execution-mode checklist item added (Change 4). Appended the "test phase touches no source files" rationalization row and the "only runs tests" red flag (Change 5). Frontmatter description gained the "group a test-only or campaign phase as parallel because its file set is disjoint" symptom (Change 6). All replacement text verbatim from the plan.

## Verification

| Criterion | Command | Result |
|-----------|---------|--------|
| Template declaration | `rg -c '\*\*Execution:\*\*' skills/writing-plans/references/plan-template.md` returns 3 or more | FAIL as written — returns 2 (see Issues) |
| Template integrated-result rule | `rg -n 'its dependency is ordering, not files' skills/writing-plans/references/plan-template.md` | PASS |
| Skill step 3 updated | `rg -c 'Execution:\*\*' skills/writing-plans/SKILL.md` returns 2 or more | PASS — returns 2 |
| Skill integrated-result rule | `rg -n 'ordering, not files' skills/writing-plans/SKILL.md` | PASS |
| Skill red flag | `rg -n 'only runs tests' skills/writing-plans/SKILL.md` | PASS |
| Description symptom | `rg -n 'group a test-only or campaign phase' skills/writing-plans/SKILL.md` | PASS |
| Prior conventions intact | `rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md` returns 2 or more; `rg '^## Final Verification' skills/writing-plans/references/plan-template.md` matches | PASS — returns 3; `## Final Verification` matched |
| No placeholder vocabulary introduced | `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md` | FAIL as written — matches pre-existing lines only (see Issues) |

Relevant output excerpts:

```text
$ rg -c '\*\*Execution:\*\*' skills/writing-plans/references/plan-template.md
2

$ rg -n 'its dependency is ordering, not files' skills/writing-plans/references/plan-template.md
126:- **Every phase declares its independence.** ... declares `none` regardless of file overlap: its dependency is ordering, not files. ...

$ rg -c 'Execution:\*\*' skills/writing-plans/SKILL.md
2

$ rg -n 'ordering, not files' skills/writing-plans/SKILL.md
43:| "The test phase touches no source files, so it's disjoint and parallel-safe" | Test and campaign phases depend on ordering, not files — ... |
59:3. Propose a phase outline ... declares `none` regardless of file overlap: its dependency is ordering, not files. ...

$ rg -n 'only runs tests' skills/writing-plans/SKILL.md
53:- "This phase only runs tests — its file set is disjoint, so it can join the parallel group"

$ rg -n 'group a test-only or campaign phase' skills/writing-plans/SKILL.md
3:description: ... group a test-only or campaign phase as parallel because its file set is disjoint, ...

$ rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md
3
$ rg '^## Final Verification' skills/writing-plans/references/plan-template.md
## Final Verification

$ rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md
skills/writing-plans/references/plan-template.md:124:- **No placeholders.** "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures.
skills/writing-plans/SKILL.md:22:**No placeholders.** ... "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures, not plans.
skills/writing-plans/SKILL.md:48:- "This phase just needs appropriate tests"
skills/writing-plans/SKILL.md:76:- [ ] No placeholders: scan for "TBD", "TODO", "appropriate", "similar to", "etc."
```

Manual Verification items are listed here unchecked, for the human:

- [ ] The integrated-result disqualifier reads as part of the independence criterion, not a bolt-on exception
- [ ] The `inline` ⇒ `none` pairing rule is stated identically in template rule and skill step 3

## Deviations

None — all six edits applied with the plan's replacement text verbatim; `git diff` confirms the changed hunks match the plan's Changes Required exactly.

## Issues & Concerns

1. **Criterion "Template declaration" threshold is inconsistent with the plan's own Changes Required (plan defect).**
   - Expected: `rg -c '\*\*Execution:\*\*' skills/writing-plans/references/plan-template.md` returns 3 or more.
   - Found: returns 2 after applying the plan's edits verbatim. The Changes Required introduce exactly two occurrences of the literal `**Execution:**` in that file: one in the phase Overview (Change 1) and one inside backticks in the new Rules bullet (Change 2, "The `**Execution:** subagent | inline` line is mandatory…"). No faithful application of the plan's specified text can produce a third occurrence; reaching 3 would require adding text the plan does not specify.
   - Why this matters: the criterion as written can never pass for this plan's own changes — the plan is internally inconsistent (threshold likely miscounted at planning time).
   - How should I proceed? Not fixed (would be an unapproved deviation). Recommend routing through iterating-plans: either correct the threshold to "2 or more" or amend Change 2 to add a third occurrence. Note the plan's `## Final Verification` section uses the same `rg -c` command with no threshold, so the dogfooded final check is unaffected.

2. **Criterion "No placeholder vocabulary introduced" command fails on pre-existing content (defective command, intent satisfied).**
   - Expected: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' …` succeeds.
   - Found: `rg` matches four lines, all pre-existing: the skills' own anti-placeholder rules and checklist, which quote the scanned vocabulary (`plan-template.md:124`, `SKILL.md:22`, `SKILL.md:48`, `SKILL.md:76`). `git diff` confirms none of these lines were added or modified by this phase — the command fails identically on the pristine checkout.
   - Why this matters: the criterion's *intent* ("no placeholder vocabulary introduced") is satisfied — the phase introduced none — but the literal command cannot distinguish introduced from pre-existing matches.
   - How should I proceed? Treated as an unrelated/pre-existing failure with evidence, per executing-plans. No edit made (the matched lines are the skill's own rules; touching them is out of scope). The controller may accept the intent-level pass or route the command wording through iterating-plans.

## Follow-ups

- Human: perform the two Manual Verification items above.
- Controller/human: resolve criterion-1 threshold via iterating-plans (plan defect: `3 or more` unattainable by the plan's own Changes Required).
- Controller: judge criterion-8 as intent-passed (evidence: `git diff` shows zero placeholder-vocabulary lines added) or route the command wording through iterating-plans.
- Per-phase reviewer: the `inline` ⇒ `none` pairing wording differs slightly between template rule ("`inline` implies `**Parallel group:** none`; declaring `inline` with a named group is a plan failure") and skill step 3 ("`inline` implies `**Parallel group:** none`") — both verbatim from the plan; Manual Verification item 2 asks whether this counts as "stated identically."
