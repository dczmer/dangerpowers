---
name: trigger-testing-skills
description: Use when the user asks to run a trigger test or trigger-testing campaign, check whether a skill triggers for a given query, or tune a skill description that fires too often or not often enough. Measures how reliably a skill's description causes it to load for one test query and reports pass/fail/void results.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Trigger Testing Skills

## Overview

Run one round of trigger evals for a single skill against a single test query and report the results. Triggering is non-deterministic, so one round is always 10 identical runs; the pass rate — not any single run — is the measurement.

## Inputs

Collect all three inputs before starting. Prompt the user for any that are missing.

- **Skill name** — the skill under test. It must appear in this session's available-skills list; subagents can only load skills the parent session can see. If it is not available, stop and tell the user instead of running the round.
- **Test query** — the exact prompt a real user would send.
- **Expectation** — whether the skill should `trigger` or `not-trigger` for this query.

## Workflow

1. Dispatch 10 subagents in parallel in a single message. Give each subagent the test query verbatim and nothing else: no added context, no instructions, no hint that this is a test, no mention of the target skill.
2. Abort any subagent still running after 30 seconds. A triggered skill may try to execute its entire workflow; the abort only stops the token burn and never invalidates the observation.
3. Classify each run by the skill-loaded signal in the subagent's returned output — the explicit indicator that the target skill was loaded. The signal is the only evidence; never infer a trigger from what the subagent did or said, and do not read session transcripts to decide.
   - Signal present → observed `triggered` (even if the run was aborted afterwards).
   - Run completed, no signal → observed `not-triggered`.
   - Run aborted, no signal → `void` (inconclusive; count separately, neither pass nor fail).
4. Score each non-void run against the expectation: matching observation = pass, mismatch = fail.
5. Account for all 10 runs. Never stop early at a passing majority.
6. Report the per-run classifications and the summary counts.

## Report format

    trigger test: writing-skills
    query: "turn this outline into a skill"
    expected: trigger

    run  1: triggered      pass
    run  2: triggered      pass
    run  3: not-triggered  fail
    run  4: triggered      pass
    run  5: triggered      pass
    run  6: triggered      pass
    run  7: void           —
    run  8: triggered      pass
    run  9: triggered      pass
    run 10: triggered      pass

    summary: 8 pass / 1 fail / 1 void (10 runs)

## Gotchas

- Keep the query verbatim within a round and across rounds of the same test case; editing it invalidates comparison with earlier rounds.
- An abort after the skill-loaded signal is a `triggered` observation, not a void.
- "It behaved like it used the skill" is not a signal. A completed run without the explicit signal is `not-triggered`.
- A skill that is not available in the current session cannot be tested this way. Confirm availability before dispatching.

## Checklist

- [ ] All three inputs collected before dispatching; user prompted for any missing
- [ ] Target skill confirmed available in the current session
- [ ] 10 subagents dispatched in parallel, each given the query verbatim and nothing else
- [ ] Every run classified from the skill-loaded signal only
- [ ] All 10 runs accounted for — none skipped, no early stop
- [ ] Report shows per-run results and pass/fail/void counts against the expectation
