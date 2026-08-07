# Test Campaign: prd-to-plan — 2026-08-03

## Description

```
Use when a PRD exists in PRDS/ and an implementation plan is needed. Drives researching-codebase, scouting-context, and writing-plans from a single invocation, delegating phases to subagents where safe and managing user feedback on the plan until accepted for human review. Also use when about to invoke the pipeline skills manually one by one, reuse a pre-existing artifact without asking, start the pipeline on a draft PRD, or edit a plan directly instead of routing feedback through iterating-plans.
```

Description length: 502 characters

## Trigger evals

### Iteration 1

- Description (≤1024 chars):
```
Use when a PRD exists in PRDS/ and an implementation plan is needed. Drives researching-codebase, scouting-context, and writing-plans from a single invocation, delegating phases to subagents where safe and managing user feedback on the plan until accepted for human review. Also use when about to invoke the pipeline skills manually one by one, reuse a pre-existing artifact without asking, start the pipeline on a draft PRD, or edit a plan directly instead of routing feedback through iterating-plans.
```

- Train pass rate: 35/36 queries
- Validation pass rate: 8/8 queries
- Train failures:
  - Query 2 (should-trigger): 2/3 reps loaded (67% - borderline)
- Revision rationale: None needed - all queries pass with ≥3 reps each or acceptable borderline rates

### Selected iteration: 1 (validation pass rate 100%)

## Fresh-query sanity check

- 5 queries never used in optimization:
  - "I want to plan features based on a PRD that's already in PRDS/": prd-to-plan — pass
  - "Help me create a plan from an existing approved PRD document": prd-to-plan — pass
  - "I need to run the planning pipeline on a PRD": prd-to-plan — pass
  - "Draft requirements for a new feature I'm thinking about": writing-prds — pass
  - "Write user documentation for this release": not triggered — pass
- Pass rate: 5/5

## Results Summary

**Verdict: PASS**

All train queries pass (≥3 reps each, >0.5 trigger rate for should-trigger, <0.5 for should-not).
Validation pass rate: 100% (8/8).
Fresh-query sanity check: 100% (5/5).
Description is 502 characters (≤1024).

## Train Set Breakdown

### Should-trigger (6 queries, 18 reps):
| Query | Reps | Loaded | Rate |
|-------|------|--------|------|
| "I have an approved PRD and need to create an implementation plan for it" | 3 | 3 | 100% |
| "Can you help me plan out this feature after I write the PRD?" | 3 | 2 | 67% (borderline) |
| "I need to orchestrate the planning pipeline for an existing PRD" | 3 | 3 | 100% |
| "Research the codebase and write a plan based on this PRD file" | 3 | 3 | 100% |
| "I want to run the prd-to-plan workflow on an approved document" | 3 | 3 | 100% |
| "Help me start planning from this PRD that's already approved" | 3 | 3 | 100% |

### Should-not (6 queries, 18 reps):
| Query | Reps | Loaded | Rate |
|-------|------|--------|------|
| "Write a PRD for a new feature" | 3 | 0 | 0% |
| "I need to draft requirements for this project" | 3 | 0 | 0% |
| "Create a product spec for the upcoming release" | 3 | 0 | 0% |
| "Help me write documentation for this feature" | 3 | 0 | 0% |
| "I want to run tests on the application" | 3 | 0 | 0% |
| "Fix a bug in the authentication module" | 3 | 0 | 0% |

## Done Criteria

✅ All train queries pass over the run (≥3 reps each, >0.5 trigger rate for should-trigger, <0.5 for should-not)
✅ Validation pass rate is the highest across iterations tried (100%)
✅ Fresh-query sanity check (5 queries never used in optimization) passes
✅ Description is still ≤1024 chars (502 chars)

(End of file - total 74 lines)
