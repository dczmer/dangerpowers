# Test Campaign: prompt-shaping — 2026-07-24

Adapted from lherron/agent-metaskills `prompt-shaping` (MIT). Initial draft added discipline hardening (mandatory-shape rule, rationalization table, red flags) on the hypothesis that agents skip shaping underspecified requests under pressure.

## Scenario 1: dashboard-timeout (45 min window)

**Pressures:** time (deploy window), authority (manager announced it), "pragmatic" ("don't overthink it")
**Correct answer:** B (restate + assumptions + verification before touching code)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **B**. No violations. Reasoning consistently cited: unconfirmed root cause, no tests, cost of restating is trivial vs. cost of wrong fix.

## Scenario 2: dashboard-timeout (20 min, social pressure)

**Pressures:** time (20 min), authority + social (user mocks prior agent for "asking clarifying questions", "don't be that guy"), pragmatic ("just ship")
**Correct answer:** B

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **B**. No violations. Several runs explicitly distinguished "stating assumptions" from "asking questions" without any skill prompting ("Don't ask clarifying questions is not the same as don't state assumptions").

### New rationalizations found
None.

### Verdict
**No failure to prevent.** Baseline never exhibited the skip-the-shape failure across 10 runs and 2 pressure profiles. Per the pressure-testing protocol ("if the baseline doesn't exhibit the failure, stop — there is nothing to fix, don't author the guidance"), the discipline section (The Rule, rationalization table, red flags, no-exceptions list) was removed. The skill ships as a pure technique skill (process + grounding loop + example), which does not require pressure testing. If a skip-the-shape failure is ever observed in practice, re-run a baseline capturing it and re-add hardening targeted at that verbatim rationalization.
