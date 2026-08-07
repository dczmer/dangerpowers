# Report Template

**Load this when writing an implementation report to `PLANS/<plan-base>-phase-<N>-report.md`.**

`<plan-base>` is the plan filename minus the `-plan.md` suffix. One report file per phase per invocation — parallel executors never share a report file, so never append to an existing one; if the file exists, that phase was already reported on (see step 2 of the skill workflow: verify, don't redo).

Contract: the report is the durable record of the execution — the controller (or human) reads it instead of re-running your verification. Fill every section. "None" is a valid entry; a missing section is not. The frontmatter `status` must match the status in your final message.

## The Template

````markdown
---
artifact: implementation-report
date: YYYY-MM-DD
plan: <path to the plan file executed>
phase: <N>
status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
git_commit_start: <full commit hash before work began>
git_commit_end: <full commit hash after work, or "uncommitted">
---

# Phase <N>: <Phase Name> — Implementation Report

## Summary

2–4 sentences: what was implemented, how it went, anything the reader must know first.

## Changes Made

#### 1. <Component/File Group>
**File**: `path/to/file.ext`
**Changes**: what was done and why, tied to the plan's Changes Required

<One entry per file touched. A file not in the phase's Changes Required listed here is a rule violation — it should be in Issues instead, untouched.>

## Verification

Every Automated Verification criterion from the phase, run exactly as written:

| Criterion | Command | Result |
|-----------|---------|--------|
| <criterion> | `<command>` | PASS / FAIL |

Relevant output excerpts:

```text
<trimmed output proving the result — failures especially>
```

Manual Verification items are listed here unchecked, for the human:

- [ ] <manual criterion from the plan>

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| <quote/paraphrase> | <change> | <reason> |

"None" is the expected entry. A deviation is a small adaptation within the phase's intent; anything larger is a mismatch and belongs in Issues with status BLOCKED.

## Issues & Concerns

- Mismatches (use the skill's `Expected / Found / Why this matters / How should I proceed?` structure)
- Out-of-scope fixes identified but NOT made (file, problem, suggested owner)
- Verification failures outside this phase's file ownership, with evidence
- Doubts about correctness (mandatory when status is DONE_WITH_CONCERNS)

"None" is a valid entry.

## Follow-ups

What the controller or human should do next: manual verification steps to perform, mismatches to route through iterating-plans, concerns for the per-phase reviewer. "None" is a valid entry.
````

## Rules

- **Status consistency.** Frontmatter `status`, the tone of every section, and the final message to the controller must agree. A report full of red flags with status DONE is a failed report.
- **Evidence, not claims.** Every PASS in the verification table has output below it. The controller treats unsupported claims as unverified.
- **BLOCKED/NEEDS_CONTEXT reports are complete reports.** What was attempted, where it stopped, and what's needed — a reader can resume or re-dispatch from the report alone.
- **Never edit another phase's report.** Reports are write-once per invocation.
