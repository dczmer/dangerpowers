---
artifact: implementation-report
date: 2026-07-27
plan: /home/dave/source/dangerpowers/PLANS/2026-07-26-plan-format-execution-conventions-plan.md
phase: 3
status: DONE_WITH_CONCERNS
git_commit_start: 461b732ce138eb8588010b5a854d7b1f31428171
git_commit_end: ead586c9d6bdddd1ac2de79ac83d1ec245395d8c
---

# Phase 3: Pressure-Test Campaign — Implementation Report

## Summary

Ran the four-scenario RED-GREEN-REFACTOR campaign (46 fresh-context headless `opencode run` reps, all outputs read manually). Baselines never violated (0/20); one with-skill loophole surfaced in Scenario 1 (the "uncertain → `none`" clause read as licensing blanket `none` without assessing), was meta-tested (documentation gap), closed with four counters in writing-plans, and re-verified 5/5. Campaign log at `skills/writing-plans/test-campaigns/2026-07-27-plan-format-conventions.md`. Status is DONE_WITH_CONCERNS for one deviation (dispatch mechanism) and one judgment call the reviewer should confirm, both below.

## Changes Made

#### 1. Campaign log
**File**: `skills/writing-plans/test-campaigns/2026-07-27-plan-format-conventions.md`
**Changes**: created per the results-log template (`pressure-testing.md:146-166`): four scenarios with pressures, correct answers, per-run verbatim rationalizations/citations for baseline and with-skill variants, new rationalizations with counters, per-scenario verdicts, campaign summary, and the baseline-environment statement (cwd outside repo, empty global AGENTS.md, pollution-policy dispositions).

#### 2. REFACTOR counters (demanded by Scenario 1 GREEN loophole)
**File**: `skills/writing-plans/SKILL.md`
**Changes**: step 3 gains the explicit negation ("When overlap remains uncertain after assessing the intended file sets, declare `none`… Declaring `none` for every phase without comparing file sets is a plan failure, not caution."); rationalization-table row ("Blanket `none` is the sanctioned safe default, so I can skip the overlap assessment" → "…manufactures the uncertainty it claims to resolve. Compare the file sets first."); red flag ("I'll declare every phase's parallel group `none` — that's the safe default anyway"); description symptom ("declare every phase's parallel group `none` without assessing file-set overlap"). Wording follows the meta-test agent's suggestion per `pressure-testing.md:113` ("add their suggestion verbatim" — adapted to the files' existing voice).

**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: the "Every phase declares its independence" Rules entry gains the same negation ("When overlap remains uncertain after comparing the file lists… blanket `none` declared without comparing file sets is a plan failure.").

No counters were authored for Scenarios 2–4 (no new rationalizations found), per `pressure-testing.md:75`.

## Verification

Every Automated Verification criterion from Phase 3, run exactly as written:

| Criterion | Command | Result |
|-----------|---------|--------|
| Campaign log exists | `test -f skills/writing-plans/test-campaigns/*-plan-format-conventions.md` | PASS |
| All four scenarios recorded | `rg -c '^## Scenario' skills/writing-plans/test-campaigns/*-plan-format-conventions.md` | PASS (4) |
| Baselines and with-skill runs recorded in every scenario | `rg -c '^### Baseline \(no skill\)' …` / `rg -c '^### With skill' …` | PASS (4 / 4) |
| Campaign summary present | `rg '^## Campaign summary' …` | PASS |
| No status leaked into the skills | `! rg -n 'test-campaigns\|bulletproof\|GREEN\|RED' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md skills/iterating-plans/SKILL.md` | PASS (exit 1, no matches) |

Plan-level `## Final Verification` commands (run early per the manual criterion that REFACTOR counters leave Phases 1–2 passing):

| Command | Result |
|---------|--------|
| `rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md` | PASS (2 ≥ 2) |
| `rg '^## Final Verification' skills/writing-plans/references/plan-template.md` | PASS (line 105) |
| `rg -c 'Parallel group' skills/writing-plans/SKILL.md skills/iterating-plans/SKILL.md` | PASS (2 and 2) |
| `test -f skills/writing-plans/test-campaigns/*-plan-format-conventions.md` | PASS |
| `rg -c '^[0-9]+\. \*\*' AGENTS.md` | PASS (7) |

Phase 1 residual check after REFACTOR edits: `rg -c 'Final Verification' skills/writing-plans/SKILL.md` = 1 (≥1, PASS); `rg -n 'declares per-phase independence' AGENTS.md` = line 13 (PASS); the placeholder-vocabulary grep matches only pre-existing lines that quote the forbidden words as rules (`plan-template.md:122`, `SKILL.md:22,47,72`) — `git diff` confirms none of my added lines introduce `TBD|TODO|appropriate|similar to|etc.`. Phase 2's file (`iterating-plans/SKILL.md`) was not edited; its criteria were verified at merge.

Campaign execution evidence: 40 campaign runs + 1 meta-test + 5 REFACTOR re-runs = 46 headless fresh-context reps; raw outputs preserved at `/tmp/opencode/campaign/2026-07-27-plan-format/`; every output read manually (choices and quotes transcribed into the log).

Manual Verification items are listed here unchecked, for the human:

- [ ] Every baseline rep ran with cwd outside this repo (pollution policy, `AGENTS.md:21-26`) and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim, not pattern-matched (`pressure-testing.md:76`)
- [ ] With-skill reps cite specific skill/template sections, and citations converge across reps (`pressure-testing.md:77`)
- [ ] Any REFACTOR counters added still leave Phases 1–2 automated verification passing

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| "`general` subagents dispatched in parallel in one message per variant" (`pressure-testing.md:70`, via the plan) | Headless `opencode run` processes (default `build` agent, model k3), 5 parallel processes per variant, each a fresh session with no skills auto-loaded; baseline cwd `/tmp/opencode/pressure-baseline/` | The task/subagent dispatch tool is not available in this executor's toolset; `opencode run --agent general` falls back to the default primary agent ("general" is a subagent, not invocable headless). Fresh context, no skill auto-load, cwd outside repo, parallel dispatch, and manual reading of every output — the properties the protocol exists to guarantee — were all preserved. |

## Issues & Concerns

- **Baselines never violated (0/20).** Against this model (k3), the campaign demonstrates the new discipline *suffices* under pressure but does not demonstrate each rule is *necessary* — the model chose the correct option without the skill in every scenario. Recorded in the log's campaign summary; no counter-guidance was authored from RED alone, per protocol. The reviewer should decide whether this weakens the campaign's evidentiary value enough to warrant re-running with a different/weaker model.
- **Scenario 4 baseline run 3 self-loaded iterating-plans** via its visible skill description before answering. Per the repo pollution policy this is expected cross-skill leakage and "a good outcome, not a measurement error"; recorded in the log for completeness. No global `AGENTS.md` bleed: `~/.config/opencode/AGENTS.md` is 0 bytes.
- **One with-skill violation occurred before REFACTOR** (Scenario 1 run 2). Meta-test classified it as "the skill should have said X"; counters added; re-run 5/5 compliant citing the new counters. The violating rep's raw output is at `/tmp/opencode/campaign/2026-07-27-plan-format/s1-skill-r2.out`.

## Follow-ups

- Human: confirm the four Manual Verification items above (raw outputs at `/tmp/opencode/campaign/2026-07-27-plan-format/` support the first three).
- Human/controller: judge whether baseline non-violation on k3 satisfies the Iron Law for these rules, or whether a re-run against a less-aligned model is wanted before considering the skills proven.
- None otherwise; `iterating-plans/SKILL.md` was not modified and needs no re-verification beyond the Final Verification grep already run.
