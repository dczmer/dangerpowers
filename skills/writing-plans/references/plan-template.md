# Plan Template

**Load this when writing a plan to `PLANS/`.**

Contract: the plan is the skill's only output. An implementing agent must be able to execute it without redoing research, without asking what a phase means, and without guessing which pattern won a conflict. Fill every section. "None" is a valid entry; a missing section is not.

## The Template

````markdown
---
artifact: implementation-plan
date: YYYY-MM-DD
git_commit: <full commit hash at planning time>
branch: <branch name>
request: <the user's request or spec block, verbatim>
source_bundle: <path to context-bundle.md, or none>
source_research: <path to research-findings.md, or none>
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

## References

- Context bundle: `RESEARCH/context-bundle.md`
- Research findings: `RESEARCH/research-findings.md`
- Key implementation files: `file:line`
````

## Rules

- **Exact file paths always.** Code-changing steps show the code or the exact signature.
- **Every command verified against the repo** — from bundle §7, or read from package.json scripts, Makefile, CI config. Never invented.
- **No placeholders.** "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures.
- **Names and signatures must be consistent across phases** — a symbol introduced in Phase 1 keeps its name in Phase 4.
