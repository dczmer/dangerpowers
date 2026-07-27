# Plan Template

**Load this when writing a plan to `PLANS/YYYY-MM-DD-<kebab-description>-plan.md`.** The `-plan` suffix is required: executing-plans writes `<kebab-description>-phase-N-report.md` files beside the plan, and the pair must sort together.

Contract: the plan is the skill's only output. An implementing agent must be able to execute it without redoing research, without asking what a phase means, and without guessing which pattern won a conflict. Fill every section. "None" is a valid entry; a missing section is not.

## The Template

````markdown
---
artifact: implementation-plan
date: YYYY-MM-DD
git_commit: <full commit hash at planning time>
branch: <branch name>
request: <the user's request or spec block, verbatim>
source_prd: <path to PRD, or none>
source_bundle: <path to the context-bundle artifact, or none>
source_research: <path to the research-findings artifact, or none>
status: draft | approved
---

# <Feature/Task Name> Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

Why this change is being made — the problem or need it addresses, what prompted it, the intended outcome.

## Current State

What exists now, what's missing, key constraints discovered. Cited `file:line` from the bundle/research.

## Desired End State

Specification of the end state after this plan completes, and how to verify it.

## What We're NOT Doing

Explicitly out-of-scope items. Scope creep fails here, not during implementation.

## Decisions

Every conflict from the bundle (§6) and every judgment call, resolved:

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| <both sides, cited> | <the pick> | <why, auditable> |

## Implementation Approach

High-level strategy and reasoning. Only the recommended approach — alternatives were resolved with the user before this document was written.

## Phase 1: <Descriptive Name>

### Overview

What this phase accomplishes.

**Parallel group:** <name> | none

### Changes Required

#### 1. <Component/File Group>
**File**: `path/to/file.ext`
**Changes**: summary of changes

```<language>
<specific code to add/modify>
```

### Success Criteria

#### Automated Verification:
- [ ] <specific check>: `<repo-verified command>`
- [ ] Unit tests pass: `<command>`
- [ ] Type checking passes: `<command>`
- [ ] Linting passes: `<command>`

#### Manual Verification:
- [ ] <observable behavior to confirm>
- [ ] <edge case to verify manually>

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: <Descriptive Name>

<Same structure.>

---

## Testing Strategy

### Unit Tests:
- <what to test, key edge cases>

### Integration Tests:
- <end-to-end scenarios>

### Manual Testing Steps:
1. <specific verification step>

## Final Verification

Plan-level test and audit commands, run by plan-to-execution against the fully integrated result after every phase completes — one exact command per line, each repo-verified like every other command in the plan. `None` is a valid entry; an absent section is not.

## References

- PRD: <path>
- Context bundle: `RESEARCH/<date>-<name>-context-bundle.md`
- Research findings: `RESEARCH/<date>-<name>-research-findings.md`
- Key implementation files: `file:line`
````

## Rules

- **Exact file paths always.** Code-changing steps show the code or the exact signature.
- **Every phase's Changes Required lists exhaustively the files it may touch.** executing-plans treats this list as file ownership — it is what makes parallel phase execution safe. A file a phase needs but doesn't list is a plan failure, not an executor's judgment call.
- **Every command verified against the repo** — from bundle §7, or read from package.json scripts, Makefile, CI config. Never invented.
- **No placeholders.** "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures.
- **Names and signatures must be consistent across phases** — a symbol introduced in Phase 1 keeps its name in Phase 4.
- **Every phase declares its independence.** The `**Parallel group:** <name> | none` line is mandatory in each phase Overview. Derive groups from the exhaustive Changes Required file lists: phases may share a group name only if their file sets are disjoint and neither consumes the other's output. When overlap is uncertain, declare `none` — sequential is the safe default, and plan-to-execution never infers or overrides declarations.
- **The plan ends with `## Final Verification`.** Plan-level commands against the integrated result, one per line, repo-verified — or the literal entry `None`.
