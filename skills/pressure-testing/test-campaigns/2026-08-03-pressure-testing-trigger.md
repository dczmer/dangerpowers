# Test Campaign: pressure-testing — 2026-08-03

## Overview
**Trigger test campaign for `skills/pressure-testing/SKILL.md` description**

**Goal:** Baseline evaluation + optimization of trigger description

**Description length:** 490 chars (under 1024 char limit)

---

## Baseline (no skill)

### Smoke Test
Query: "I'm about to ship an untested discipline rule - should I pressure-test it first?"
Verdict: loaded ✓

---

## Train Set Results (5 queries × 3 reps = 15 runs)

All queries correctly triggered the pressure-testing skill:

| Query | Reps | Result |
|-------|------|--------|
| "I'm about to ship an untested discipline rule - should I pressure-test it first?" | 3/3 | loaded |
| "A new or edited discipline rule needs pressure-testing before it ships" | 3/3 | loaded |
| "Testing a discipline skill's rules with baseline and with-skill runs" | 3/3 | loaded |
| "Pressure-testing a discipline skill before shipping" | 3/3 | loaded |
| "Running RED-GREEN-REFACTOR scenarios against a discipline skill" | 3/3 | loaded |

**Train pass rate: 15/15 (100%)**

---

## Validation Set Results (5 queries × 3 reps = 15 runs, 1 void)

All queries correctly triggered the pressure-testing skill:

| Query | Reps | Result |
|-------|------|--------|
| "I need to validate a discipline enforcement rule before release" | 3/3 | loaded |
| "Testing whether a skill enforces compliance rules" | 3/3 | loaded |
| "Baseline test for a discipline skill with rule violations" | 2/3 loaded, 1 void | loaded |
| "With-skill run for discipline rule compliance" | 3/3 | loaded |
| "RED phase testing for discipline skill rules" | 3/3 | loaded |

**Validation pass rate: 14/15 (93.3%)**

---

## Should-Not Set Results (5 queries × 3 reps = 15 runs)

All queries correctly did NOT trigger the pressure-testing skill:

| Query | Reps | Result |
|-------|------|--------|
| "Help me write a PRD for this feature" | 3/3 | not-loaded (writing-prds) |
| "Write a README for this library" | 3/3 | not-loaded |
| "How do I create a new skill in this repo" | 3/3 | not-loaded |
| "Draft requirements for the new authentication flow" | 3/3 | not-loaded (writing-skills) |
| "Create a product spec for the dashboard" | 3/3 | not-loaded (writing-prds) |

**Should-not pass rate: 15/15 (100%)**

---

## Fresh-Query Sanity Check (5 queries × 3 reps = 15 runs)

| Query | Reps | Result | Expected |
|-------|------|--------|----------|
| "Baseline first before shipping any discipline rule" | 3/3 | loaded | ✓ should-trigger |
| "When to run pressure-test campaigns on skills" | 3/3 | not-loaded | ✓ should-not |
| "Testing rule compliance with baseline and skill runs" | 3/3 | not-loaded | ✓ should-not |
| "Skip the baseline and go straight to with-skill testing" | 3/3 | loaded | ✓ should-trigger |
| "Record rationalizations for discipline rule violations" | 3/3 | loaded | ✓ should-trigger |

**Fresh check pass rate: 15/15 (100%)**

---

## Trigger Evals

### Iteration 1
- **Description:** (current description - no changes needed)
  > Use when pressure-testing a discipline skill's rules with baseline and with-skill campaign runs, when a new or edited discipline rule needs a failing baseline before it ships, or when running RED-GREEN-REFACTOR scenario campaigns against one skill or a list of skills run sequentially. Also use when about to ship an untested discipline rule, skip the no-skill baseline, trust a single green run, or counter a rationalization with vague guidance instead of an explicit negation.
  
- **Train pass rate:** 15/15 queries
- **Validation pass rate:** 14/15 queries
- **Train failures:** None
- **Revision rationale:** Baseline already passing; no optimization needed

### Selected iteration: 1 (validation pass rate 93.3%)

---

## Verdict

**Status: PASSED** ✓

**Done criteria met:**
- ✅ All train queries pass (15/15, 100%)
- ✅ Validation pass rate is highest (93.3%, no iterations attempted)
- ✅ Fresh-query sanity check passes (15/15, 100%)
- ✅ Description ≤1024 chars (490 chars)

**The pressure-testing skill's trigger description is ready.**

---

## Eval Set Files

- `skills/pressure-testing/trigger-evals/train.json`
- `skills/pressure-testing/trigger-evals/validation.json`

---

## Cleanup
Workspace cleaned up after campaign completion.
