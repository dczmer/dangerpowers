# PRD Template

**Load this when writing a PRD to `PRDS/`.**

**Contract:** the PRD is the skill's only output. Fill every section — "None" is a valid entry, a missing section is not.

```markdown
---
artifact: prd
date: YYYY-MM-DD
git_commit: <full commit hash at writing time>
branch: <branch name>
request: <the user's feature request, verbatim>
status: draft | approved
---

# <Feature Name> PRD

## 1. Problem & Context

Why this feature is being built — the problem, who has it, what prompted it.

## 2. Goals & Non-Goals

- **Goals:** ...
- **Non-goals:** explicit items a reader might assume are included but are not

## 3. User Stories & Acceptance Scenarios

Prioritized stories (P1, P2, ...), each independently testable, each with
Given/When/Then acceptance scenarios.

### P1: <story>
- **Independent test:** <how this story alone is verifiable>
- **Scenario:** Given <context>, When <action>, Then <observable outcome>

## 4. Requirements

Numbered, testable, WHAT/WHY only.

- **FR-001:** ...

## 5. Scope

- **In scope:** ...
- **Out of scope:** ...

## 6. Assumptions & Constraints

Assumptions the user confirmed during the interview; constraints that bound any solution.

## 7. Edge Cases

Enumerated edge cases and the required behavior for each. "None" is valid.

## 8. Success Criteria

Measurable, technology-agnostic.

- **SC-001:** ...

## 9. Open Questions

Must be empty when `status: approved`. Each entry: the question, its owner, why it blocks approval.
```

**WHAT/WHY rule:** no file paths, library names, schemas, endpoints, or architecture anywhere in the PRD — those belong to research and planning.

**Status rule:** `status: approved` requires §9 empty and every §6 assumption confirmed by the user.
