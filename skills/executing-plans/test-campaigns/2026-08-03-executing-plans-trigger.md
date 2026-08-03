# Test Campaign: executing-plans — 2026-08-03

## Description
```
Use to implement a single phase of a multi-phase plan when you're executing one discrete task, not orchestrating the whole plan. Use this skill when the user provides a plan path, phase number, and report path — even if they don't explicitly mention "phase" or "orchestration."
```
Character count: 338

## Train Set (6 queries, 3 reps each = 18 total)

### Query 0: "Use the plan execution workflow to implement a single phase."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
Result: 3/3 loaded (should-trigger) ✓

### Query 1: "I have an approved plan with phases. I want to implement phase 3 now."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
Result: 3/3 loaded (should-trigger) ✓

### Query 2: "Help me write a README for this library."
- Rep 1: not-loaded ✓
- Rep 2: not-loaded (prompt-shaping loaded instead) ✓
- Rep 3: not-loaded ✓
Result: 3/3 not-loaded (should-not) ✓

### Query 3: "I need to create a new skill for the team."
- Rep 1: not-loaded (writing-skills loaded instead) ✓
- Rep 2: not-loaded (writing-skills loaded instead) ✓
- Rep 3: not-loaded (writing-skills loaded instead) ✓
Result: 3/3 not-loaded (should-not) ✓

### Query 4: "Can you help me design a workflow?"
- Rep 1: not-loaded ✓
- Rep 2: not-loaded (prompt-shaping loaded instead) ✓
- Rep 3: not-loaded (prompt-shaping loaded instead) ✓
Result: 3/3 not-loaded (should-not) ✓

### Query 5: "Write a PRD for a new feature."
- Rep 1: not-loaded (writing-prds loaded instead) ✓
- Rep 2: not-loaded (writing-prds loaded instead) ✓
- Rep 3: not-loaded (writing-prds loaded instead) ✓
Result: 3/3 not-loaded (should-not) ✓

**Train Pass Rate: 18/18 = 100%**

## Validation Set (4 queries, 5 reps each = 20 total)

### Query 0: "Help me execute one phase of a multi-phase plan that was approved."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
- Rep 4: loaded ✓
- Rep 5: loaded ✓
Result: 5/5 loaded (should-trigger) ✓

### Query 1: "I need to implement phase 2 of an approved plan. The plan is in PLANS/my-plan-plan.md and the report should go to PLANS/my-plan-phase-2-report.md."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
- Rep 4: loaded ✓
- Rep 5: loaded ✓
Result: 5/5 loaded (should-trigger) ✓

### Query 2: "What's the weather today?"
- Rep 1: not-loaded ✓
- Rep 2: not-loaded ✓
- Rep 3: not-loaded ✓
- Rep 4: not-loaded ✓
- Rep 5: not-loaded ✓
Result: 5/5 not-loaded (should-not) ✓

### Query 3: "I'm running a phase executor for an approved plan."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
- Rep 4: loaded ✓
- Rep 5: loaded ✓
Result: 5/5 loaded (should-trigger) ✓

**Validation Pass Rate: 20/20 = 100%**

## Fresh-Query Sanity Check (5 queries, 3 reps each = 15 total)

### Query 0: "I want to run a phase of my approved development plan."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
Result: 3/3 loaded (should-trigger) ✓

### Query 1: "Execute phase 5 of the approved infrastructure plan."
- Rep 1: loaded ✓
- Rep 2: loaded ✓
- Rep 3: loaded ✓
Result: 3/3 loaded (should-trigger) ✓

### Query 2: "I'm a phase executor working on an approved plan."
- Rep 1: not-loaded ✓
- Rep 2: not-loaded ✓
- Rep 3: not-loaded ✓
Result: 3/3 not-loaded (should-not) ✓

### Query 3: "What's the capital of France?"
- Rep 1: not-loaded ✓
- Rep 2: not-loaded ✓
- Rep 3: not-loaded ✓
Result: 3/3 not-loaded (should-not) ✓

### Query 4: "Help me write a blog post about my project."
- Rep 1: not-loaded ✓
- Rep 2: not-loaded ✓
- Rep 3: not-loaded (prompt-shaping loaded instead) ✓
Result: 3/3 not-loaded (should-not) ✓

**Fresh-Query Pass Rate: 15/15 = 100%**

## Iteration Summary

### Iteration 1
- Description: "Use to implement a single phase of a multi-phase plan when you're executing one discrete task, not orchestrating the whole plan. Use this skill when the user provides a plan path, phase number, and report path — even if they don't explicitly mention "phase" or "orchestration.""
- Train pass rate: 18/18 queries
- Validation pass rate: 20/20 queries
- Train failures: None
- Revision rationale: Initial baseline

### Selected iteration: 1 (validation pass rate 100%)

## Trigger-evals directory
- train.json: 6 queries (3 should-trigger, 3 should-not)
- validation.json: 4 queries (3 should-trigger, 1 should-not)

## Verdict
**Bulletproof**

All train queries pass (100%), validation pass rate is highest (100%), fresh-query sanity check passes (100%), description is 338 chars (under 1024 limit).
