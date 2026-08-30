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

## Subagent prompt

Give each subagent this prompt exactly, replacing `{{TEST QUERY}}` with the test query verbatim:

    Your only tool is `skill`. You have no file, shell, web, todo, or agent tools —
    post-load work is impossible by construction, and that is expected, not an
    error.

    **Rules:**
    - If the query matches a skill, invoke the skill tool to load it. The load is
      the entire measurement — treat the loaded skill body as context only and DO
      NOT load or activate any skill workflow or procedures.
    - If no skill matches, say so. Answer the query in at most one sentence if you
      can; never attempt the task itself.
    - After the load decision (load or no-load), report the outcome in one line —
      the exact name of the skill loaded, or that no skill matched — then end the
      turn.
    - If a loaded skill instructs you to use tools you do not have, do not comply.
      Report and stop.

    Query: {{TEST QUERY}}

The "only tool is `skill`" claim is a behavioral guardrail, not a real restriction — the subagent actually has full tools. The rules above, plus the timeout in the workflow, are the only mitigation against runaway post-load workflows.

## Workflow

1. Dispatch 10 subagents in parallel in a single message, using the harness's general-purpose subagent type. Give each subagent exactly the prompt in Subagent prompt above, with the test query substituted verbatim — nothing else: no added context, no instructions, no mention of the target skill, no hint that this is a test.
2. Abort any subagent still running after 30 seconds. The prompt's rules are the only thing stopping post-load work — a run still going after 30 seconds has ignored them and started executing the skill's workflow. It is measuring nothing; kill it.
3. Classify each run by the skill-loaded signal in the subagent's returned output — the explicit indicator that the target skill was loaded: the skill-tool invocation and/or the one-line report the prompt requires (the exact name of the skill loaded, or that no skill matched). The signal is the only evidence; never infer a trigger from what the subagent did or said.
   - Signal present → observed `triggered` (even if the run was aborted afterwards).
   - Run completed, no signal → observed `not-triggered`.
   - Run aborted, no signal → `void` (inconclusive; count separately, neither pass nor fail).
4. Score each non-void run against the expectation: matching observation = pass, mismatch = fail.
5. Account for all 10 runs. Never stop early at a passing majority.
6. Report the per-run classifications and the summary counts. For failed runs, read the subagent's session transcript to collect its reasoning around the load decision, and include that reasoning in the report.

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

    notes:
    run 3: transcript shows the subagent treated the query as a general writing
           request and answered directly instead of loading the skill

## Gotchas

- Keep the query verbatim within a round and across rounds of the same test case; editing it invalidates comparison with earlier rounds.
- Give each subagent exactly the template prompt — no edits, no added context, no mention of the target skill, no hint that it is a test. Extra framing contaminates the measurement.
- Never extend the 30-second timeout to let a run "finish" — a slow run is a run that broke the prompt's rules and started a runaway workflow.
- An abort after the skill-loaded signal is a `triggered` observation, not a void.
- "It behaved like it used the skill" is not a signal. A completed run without the explicit signal is `not-triggered`.
- Transcripts are for collecting reasoning on classified runs, never for deciding a classification. No signal in the returned output means no signal.
- Harnesses that do not expose subagent transcripts cannot supply failure reasoning — report the classification without it.
- A skill that is not available in the current session cannot be tested this way. Confirm availability before dispatching.

## Checklist

- [ ] All three inputs collected before dispatching; user prompted for any missing
- [ ] Target skill confirmed available in the current session
- [ ] 10 subagents dispatched in parallel in a single message, each given exactly the template prompt with the query substituted verbatim — nothing else
- [ ] Subagents not told this is a test; target skill not named in their prompts
- [ ] Every run classified from the skill-loaded signal only
- [ ] All 10 runs accounted for — none skipped, no early stop
- [ ] Report shows per-run results and pass/fail/void counts against the expectation, with transcript reasoning for failed runs
