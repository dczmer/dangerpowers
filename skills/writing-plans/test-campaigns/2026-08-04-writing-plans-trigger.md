# Test Campaign: writing-plans — 2026-08-04

## Trigger evals

### Iteration 1
- Description (≤1024 chars): Use when research findings or a context bundle exist and an implementation plan in PLANS/ is needed before changing code. Also use when about to plan with unresolved open questions, write plan steps that say what to do without showing how, leave a pattern conflict unpicked, declare every phase's parallel group none without assessing file-set overlap, pick a side of a team-standard or vendor question on usage counts alone, or edit anything other than the plan file while planning. Covers implementation plans, phases, and plan approval.
- Description sha256 (first 12): 398694020562
- Train pass rate: 15/15 queries
- Validation pass rate: 10/10 queries
- Train failures: none
- Revision rationale: Initial evaluation run

### Selected iteration: 1 (validation pass rate 100%)

## Fresh-query sanity check
- 5 queries never used in optimization:
  - "I need to create a detailed plan for the feature implementation": loaded — pass
  - "before writing code, help me outline the implementation": loaded — pass
  - "write a project plan document": not triggered — pass
  - "generate API documentation": not triggered — pass
  - "build the application": not triggered — pass
- Pass rate: 5/5

## Summary
All train and validation queries pass with 100% success rate. The description correctly triggers on implementation planning scenarios and does not trigger on documentation, coding, or deployment requests.
