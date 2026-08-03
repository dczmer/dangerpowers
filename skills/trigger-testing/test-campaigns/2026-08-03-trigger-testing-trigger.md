# Test Campaign: trigger-testing — 2026-08-03

## Setup

- **Date:** 2026-08-03
- **Skill:** trigger-testing
- **Workspace:** /tmp/trigger-test.Z0CYtDl0Uc
- **Description:** Use when testing or optimizing a skill's trigger description with eval queries, train and validation splits, and detection-harness campaigns, when a new or edited description needs a passing eval set before it ships, or when running trigger-eval or trigger-test campaigns against one skill or a list of skills run sequentially.

## Trigger evals

### Iteration 1

- Description (≤1024 chars): Use when testing or optimizing a skill's trigger description with eval queries, train and validation splits, and detection-harness campaigns, when a new or edited description needs a passing eval set before it ships, or when running trigger-eval or trigger-test campaigns against one skill or a list of skills run sequentially.
- Train pass rate: 8/10 queries
- Validation pass rate: 3/4 queries
- Train failures:
  - "help me understand when to use the trigger-testing skill" - should-not false-positives (2/3 reps triggered prompt-shaping)
  - "write a PRD for this new feature with user stories and acceptance criteria" - should-not false-positive (3/3 reps triggered writing-prds)
- Revision rationale: The description contains "eval queries" which overlaps with prompt-shaping's domain of "help me understand". Also "trigger-eval" and "trigger-test" keywords are too specific and don't generalize well. Need to broaden the trigger framing to focus on the intent (testing skill behavior) rather than specific terminology.

### Iteration 2

- Description (≤1024 chars): Use when testing how your skill description triggers on user prompts, measuring whether it loads on the right queries and not on the wrong ones, or when you need to validate that a skill's description causes the correct loading behavior before it ships.
- Train pass rate: 10/10 queries
- Validation pass rate: 4/4 queries
- Train failures: none
- Revision rationale: Reworded to focus on the core intent ("testing how your skill description triggers") rather than specific terms like "trigger description". This should reduce overlap with prompt-shaping while maintaining the correct trigger behavior.

### Selected iteration: 2 (validation pass rate 100%)

## Fresh-query sanity check

- 5 queries never used in optimization:
  - "test if my skill loads on the correct user prompts": triggered trigger-testing — pass
  - "validate my skill's description triggers on the right queries": triggered trigger-testing — pass
  - "how do I check if a skill description causes correct loading behavior": triggered trigger-testing — pass
  - "write a new feature with detailed requirements and acceptance criteria": triggered writing-prds — pass
  - "fix the login bug in the auth module": not triggered — pass
- Pass rate: 5/5
