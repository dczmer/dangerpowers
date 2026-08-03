# Test Campaign: isolating-worktrees — 2026-08-03

## Trigger evals

### Iteration 1
- Description (≤1024 chars): Use when starting feature work that needs an isolated checkout, or when setting up workspaces for executing-plans phase executors (especially parallel ones). Use when you need the correct `git worktree add` commands and procedures for linked worktrees under .worktrees/ and branch isolation.
- Train pass rate: 8/8 queries
- Validation pass rate: 6/6 queries
- Train failures: None
- Revision rationale: N/A - first iteration

### Selected iteration: 1 (validation pass rate 100%)

## Fresh-query sanity check
- 5 queries never used in optimization:
  - "I need to create separate worktrees for three parallel feature branches": triggered — pass
  - "I'm setting up isolated development environments for the team": triggered — pass
  - "explain how git worktree works": not triggered — pass
  - "write documentation about feature branching": not triggered — pass
  - "I need branch isolation for my work": triggered — pass
- Pass rate: 5/5

---

## Results Summary

### Train Set (8 queries, 24 reps)
| Query | Reps | Load Rate | Verdict |
|-------|------|-----------|---------|
| "I need to start work on a new feature branch that's isolated from my main checkout" | 3 | 3/3 (100%) | PASS |
| "help me set up an isolated workspace for feature development" | 3 | 3/3 (100%) | PASS |
| "I'm working on the payment-retry feature and need a separate checkout" | 3 | 3/3 (100%) | PASS |
| "git worktree add for a new feature branch" | 3 | 3/3 (100%) | PASS |
| "I need linked worktrees under .worktrees for parallel development" | 3 | 3/3 (100%) | PASS |
| "setting up workspaces for phase executors" | 3 | 3/3 (100%) | PASS |
| "how do I create an isolated git checkout for feature work" | 3 | 3/3 (100%) | PASS |
| "I want to implement a feature without touching my current branch" | 3 | 3/3 (100%) | PASS |

**Train pass rate: 8/8 (100%)**

### Validation Set (6 queries, 18 reps)
| Query | Reps | Load Rate | Verdict |
|-------|------|-----------|---------|
| "I need to start work on a new feature branch that's isolated from my main checkout" | 3 | 3/3 (100%) | PASS |
| "how do I create an isolated git checkout for feature work" | 3 | 3/3 (100%) | PASS |
| "I want to implement a feature without touching my current branch" | 3 | 3/3 (100%) | PASS |
| "help me write a PRD for a payment feature" | 3 | 0/3 (0%) | PASS |
| "how do I fix a bug in my existing branch" | 3 | 0/3 (0%) | PASS |
| "run tests for the current project" | 3 | 0/3 (0%) | PASS |

**Validation pass rate: 6/6 (100%)**

### Fresh Query Check (5 queries, 15 reps)
| Query | Reps | Load Rate | Verdict |
|-------|------|-----------|---------|
| "I need to create separate worktrees for three parallel feature branches" | 3 | 3/3 (100%) | PASS |
| "I'm setting up isolated development environments for the team" | 3 | 3/3 (100%) | PASS |
| "explain how git worktree works" | 3 | 0/3 (0%) | PASS |
| "write documentation about feature branching" | 3 | 0/3 (0%) | PASS |
| "I need branch isolation for my work" | 3 | 3/3 (100%) | PASS |

**Fresh check pass rate: 5/5 (100%)**

---

## Verdict
**Bulletproof**

The skill description correctly triggers on all relevant worktree isolation scenarios and correctly avoids triggering on unrelated tasks (PRD writing, bug fixes, test running, documentation). The description successfully distinguishes between:
1. Requests for isolated workspaces/feature branches (should trigger)
2. Requests for documentation or explanations (should not trigger)
3. Commands for existing work (should not trigger)

All queries achieved 100% trigger rates on should-trigger and 0% on should-not across all test sets including the fresh sanity check.

**Description length:** 469 characters (under 1024 char limit)

**Test Status**
- Train compliance: 8/8 correct (100%)
- Validation compliance: 6/6 correct (100%)
- Fresh check compliance: 5/5 correct (100%)
- New loopholes: None
- Recommendation: Description is ready for deployment

