---
artifact: implementation-report
date: 2026-07-26
plan: PLANS/2026-07-26-plan-format-execution-conventions-plan.md
phase: 1
status: DONE_WITH_CONCERNS
git_commit_start: 376fdbb492cf43a881fb4a7083a7699e96c549c7
git_commit_end: 53b8041 (amended; final hash in controller's merge)
---

# Phase 1: Emit the Conventions from writing-plans — Implementation Report

## Summary

All six Changes Required items were implemented exactly as specified: the plan template gained the `**Parallel group:**` Overview field, a `## Final Verification` section, and two new Rules; writing-plans' SKILL.md gained the independence-assessment sentence in workflow step 3 and two Plan Checklist items; AGENTS.md's step-5 pipeline line was extended. 6 of 7 automated criteria pass as written. Criterion 7 (`! rg 'TBD|TODO|appropriate|similar to|etc\.'`) fails as written, but only on lines that pre-exist at the base commit (the no-placeholder rules and checklist item that quote the vocabulary as prohibitions); a diff against the base commit confirms zero placeholder vocabulary was introduced, which is the criterion's stated intent.

## Changes Made

#### 1. Template: phase Overview gains the declaration
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: added `**Parallel group:** <name> | none` after "What this phase accomplishes." in the Phase 1 Overview block (Change 1).

#### 2. Template: `## Final Verification` section
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: inserted the `## Final Verification` section (with its explanatory paragraph) immediately before `## References`, after the `## Testing Strategy` block (Change 2).

#### 3. Template: two new rules
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: appended the "Every phase declares its independence" and "The plan ends with `## Final Verification`" rules to the `## Rules` list (Change 3).

#### 4. Skill: independence assessment in the workflow
**File**: `skills/writing-plans/SKILL.md`
**Changes**: appended the `**Parallel group:**` declaration-derivation sentence to Workflow step 3, verbatim from the plan (Change 4).

#### 5. Skill: two checklist items
**File**: `skills/writing-plans/SKILL.md`
**Changes**: appended the `**Parallel group:**` and `## Final Verification` checklist items to the Plan Checklist, verbatim from the plan (Change 5).

#### 6. Pipeline description touch-up
**File**: `AGENTS.md`
**Changes**: replaced the step-5 line with the version declaring per-phase independence and final verification commands; no other AGENTS.md lines touched (Change 6).

## Verification

| Criterion | Command | Result |
|-----------|---------|--------|
| Template declaration present (>=2) | `rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md` | PASS |
| Template section present | `rg '^## Final Verification' skills/writing-plans/references/plan-template.md` | PASS |
| Skill workflow updated (>=2) | `rg -c 'Parallel group' skills/writing-plans/SKILL.md` | PASS |
| Skill checklist updated (>=1) | `rg -c 'Final Verification' skills/writing-plans/SKILL.md` | PASS |
| AGENTS.md updated | `rg -n 'declares per-phase independence' AGENTS.md` | PASS |
| AGENTS.md numbered list intact (=7) | `rg -c '^[0-9]+\. \*\*' AGENTS.md` | PASS |
| No placeholder vocabulary introduced | `! rg -n 'TBD\|TODO\|appropriate\|similar to\|etc\.' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md` | FAIL as written / PASS by intent (see evidence) |

Relevant output excerpts:

```text
== 1 == rg -c '\*\*Parallel group:\*\*' plan-template.md
2
== 2 == rg '^## Final Verification' plan-template.md
105:## Final Verification
== 3 == rg -c 'Parallel group' SKILL.md
2
== 4 == rg -c 'Final Verification' SKILL.md
1
== 5 == rg -n 'declares per-phase independence' AGENTS.md
13:5. **writing-plans** — `PLANS/<date>-<name>-plan.md`: resolved decisions, phased execution; declares per-phase independence (`**Parallel group:**`) and plan-level final verification commands
== 6 == rg -c '^[0-9]+\. \*\*' AGENTS.md
7
== 7 == rg -n 'TBD|TODO|appropriate|similar to|etc\.' (both files)
skills/writing-plans/references/plan-template.md:122:- **No placeholders.** "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures.
skills/writing-plans/SKILL.md:22:**No placeholders.** ... "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures, not plans.
skills/writing-plans/SKILL.md:46:- "This phase just needs appropriate tests"
skills/writing-plans/SKILL.md:70:- [ ] No placeholders: scan for "TBD", "TODO", "appropriate", "similar to", "etc."
```

Criterion 7 disambiguation evidence — every match is pre-existing at the base commit (`376fdbb`), and no added line contains the vocabulary:

```text
$ git show 376fdbb:skills/writing-plans/SKILL.md | rg -n 'TBD|TODO|appropriate|similar to|etc\.'
22, 46, 70  (identical pre-existing lines)
$ git show 376fdbb:skills/writing-plans/references/plan-template.md | rg -n '...'
116  (identical pre-existing line)
$ git diff 376fdbb -- <both files> | rg '^\+' | rg 'TBD|TODO|appropriate|similar to|etc\.'
(no output — no placeholder vocabulary in added lines)
```

The four matches are the repo's own no-placeholder prohibitions quoting the vocabulary they ban. The plan command could never have passed on the pristine repo, so the criterion can only mean "introduced by this phase" — which the diff proves is satisfied.

Manual Verification items are listed here unchecked, for the human:

- [ ] The template's Phase 2 `<Same structure.>` placeholder still reads correctly with the new Overview line (it inherits it)
- [ ] The new Rules entries are consistent with the existing rule at `plan-template.md:114` (file ownership) and do not contradict it
- [ ] The step-3 addition reads as part of the outline proposal, not as a post-hoc check

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| Criterion 7 passes via `! rg 'TBD\|TODO\|appropriate\|similar to\|etc\.'` | Reported FAIL-as-written with diff evidence that the intent ("introduced") is satisfied | The command matches 4 lines that pre-exist at the base commit; no edit within this phase's intent could remove them (they are the no-placeholder rules themselves) |

## Issues & Concerns

- Criterion 7's command as written fails on the unmodified base commit (verified: `git show 376fdbb:<file> | rg ...` returns the same 4 matches). The plan states verification commands were repo-verified at planning time, but this one cannot have been run against the pristine repo. All matches are the skill/template's own anti-placeholder prohibitions. This phase's diff introduces zero matches. Suggest the controller treat the criterion as satisfied-by-intent; if a literal pass is required, the plan needs an iterating-plans revision of the command (e.g. diff-based), not a code change.

## Follow-ups

- Human to confirm the three Manual Verification items above.
- Controller to decide how to record criterion 7 (intent-satisfied per evidence above, or route the command wording through iterating-plans).
