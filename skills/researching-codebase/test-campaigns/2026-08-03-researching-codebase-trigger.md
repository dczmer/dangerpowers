# Test Campaign: researching-codebase — 2026-08-03

## Trigger evals

### Iteration 1
- Description (≤1024 chars): Use when asked to research, explore, map, or explain how part of a codebase works, find where features live, locate entry points or call sites, or gather code context before planning. Also use when about to answer codebase questions from memory or a single grep, or to flag problems and suggest improvements while researching. Covers "how does X work" exploration without unsolicited improvement notes.
- Train pass rate: 13/13 queries
- Validation pass rate: 5/5 queries
- Train failures: none
- Validation failures: none
- Revision rationale: N/A - initial description passed all queries

### Selected iteration: 1 (validation pass rate 100%)

## Fresh-query sanity check
- 5 queries never used in optimization:
  - "find where the API routes are defined": loaded — pass
  - "trace how user data flows through the system": loaded — pass
  - "discover the testing framework used in this project": loaded — pass
  - "understand the build process for this project": loaded — pass
  - "understand how configuration is managed": loaded — pass
- Pass rate: 5/5

