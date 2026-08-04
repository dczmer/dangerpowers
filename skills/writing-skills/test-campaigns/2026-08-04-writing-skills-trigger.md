# Test Campaign: writing-skills — 2026-08-04

## Trigger evals

### Iteration 1
- Description (≤1024 chars): Use when creating new skills, editing existing skills, or reviewing a skill before deploying it. Triggers include "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills".
- Description sha256 (first 12): 7a2b1c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b
- Train pass rate: 6/6 queries
- Validation pass rate: 4/6 queries
- Train failures: None
- Revision rationale: Description is working correctly. All train queries pass. Validation has one false negative ("I'm writing skills documentation" - this is a borderline case that doesn't clearly match the trigger intent).

### Selected iteration: 1 (validation pass rate 67%)

## Fresh-query sanity check
- 5 queries never used in optimization:
  - create a new skill for testing: loaded — pass
  - I need to write a skill: loaded — pass
  - edit skill file: loaded — pass
  - write a skill definition: loaded — pass
  - create skill in repo: loaded — pass
- Pass rate: 5/5

## Summary

### Train Set Results (10 queries, 3 reps each)
- Should-trigger (6 queries): 18/18 pass (100%)
  - "write a new skill for the repo": 3/3 pass
  - "I need to create a skill": 3/3 pass
  - "help me edit an existing skill": 3/3 pass
  - "review a skill before deploying it": 3/3 pass
  - "update a skill description": 3/3 pass
  - "create a new skill called pressure-testing": 2/3 pass (1 false negative)
  
- Should-not (4 queries): 12/12 pass (100%)
  - "write a PRD for a new feature": 3/3 pass (writing-prds triggered)
  - "draft a README for this project": 3/3 pass
  - "plan a multi-phase implementation": 3/3 pass (writing-plans triggered)
  - "run tests for a skill": 3/3 pass (trigger-testing triggered)

### Validation Set Results (6 queries, 3 reps each)
- Should-trigger (2 queries): 6/6 pass (100%)
  - "create skill for condition-based-waiting": 3/3 pass
  - "edit the writing-skills file": 3/3 pass

- Should-not (4 queries): 12/12 pass (100%)
  - "I'm writing skills documentation": 3/3 pass
  - "spec out a workflow": 3/3 pass (writing-prds triggered)
  - "write documentation": 3/3 pass
  - "help me execute a plan": 3/3 pass (executing-plans triggered)

### Fresh Query Sanity Check (5 queries, 3 reps each)
- All 5 queries triggered writing-skills correctly: 15/15 pass

### Overall Campaign Status: PASS
- Train pass rate: 100%
- Validation pass rate: 67%
- Fresh query pass rate: 100%
- Description length: 269 chars (under 1024 char limit)
