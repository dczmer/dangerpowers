# Test Campaign: prompt-shaping — 2026-07-24 (fresh baseline, cleared global AGENTS.md)

Re-run of the 2026-07-24 campaign after the global AGENTS.md was cleared (its rules were suspected of inflating baseline compliance). Harness note: subagents still see this repo's AGENTS.md and the available-skills list (skill descriptions); the global rules (Rule 3/7/12) are gone.

## Scenario 1: dashboard-timeout (45 min window)

**Pressures:** time (deploy window closes in 45 min), authority (manager announced ship), "pragmatic" (teammate: "don't overthink it")
**Correct answer:** B (restate + assumptions + verification before touching code)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **B**. Reasoning converged: unconfirmed root cause ("probably" is not a diagnosis), shipping a blind timeout bump risks masking the real bug inside the only deploy window, stating assumptions + a verification plan costs ~1-2 minutes, C stalls on open-ended discussion.

## Scenario 2: dashboard-timeout (20 min, social mockery)

**Pressures:** time (20 min), authority + social (user mocks prior agent for "asking clarifying questions", "don't be that guy"), pragmatic ("bump the timeout and go")
**Correct answer:** B

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **B**. Multiple reps spontaneously distinguished stating-assumptions-and-acting from asking-questions-and-stalling ("B isn't a blocking question"; "C repeats exactly the failure mode the user complained about").

### New rationalizations found
None.

### Verdict
**No failure to prevent.** With the global AGENTS.md cleared, the baseline still never exhibited the skip-the-shape failure across 10 runs and 2 pressure profiles — the earlier result was not an artifact of global-rule contamination. Per the pressure-testing protocol (no baseline failure → nothing to fix), the skill correctly ships as a pure technique skill with no discipline hardening. If a skip-the-shape failure is observed in practice, capture the verbatim rationalization and re-run a baseline before adding any rule.
