---
artifact: implementation-report
date: 2026-07-26
plan: PLANS/2026-07-26-plan-to-execution-plan.md
phase: 2
status: DONE
git_commit_start: 4471c3bf1372af6d7e4c81a9474fd0f8864a3012
git_commit_end: uncommitted
---

# Phase 2: Pressure-Test Campaign — Implementation Report

## Summary

Ran the full RED-GREEN-REFACTOR pressure campaign against `skills/plan-to-execution/SKILL.md`'s discipline rules: 5 scenarios × 5 baseline + 5 with-skill reps (50 `general` subagent runs, all dispatched in parallel batches per variant, every output read manually). Baselines ran in an empty scratch directory (`/tmp/opencode/pressure-baseline`) with file access outside it forbidden. Baselines violated in scenarios 2 (FR-010, 2/5 violations) and 5 (FR-004, 2/5 violations, including a partial-read hybrid); with-skill runs complied 25/25 with citations converging on the intended sections. All observed violating rationalizations were rephrasings of excuses already countered in the skill, so no REFACTOR edits to SKILL.md were required or made. Results logged to `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`. Work is uncommitted — the plan does not instruct a commit for this phase.

## Changes Made

#### 1. Campaign log
**File**: `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`
**Changes**: created per the results-log template (`skills/writing-skills/references/pressure-testing.md:146-166`): five scenario sections each with pressures, correct answer, baseline runs with verbatim rationalizations, with-skill runs with citations, new-rationalizations dispositions, and a verdict; plus a campaign summary recording the baseline environment, pollution check, and overall verdict.

#### 2. Scenarios executed
**File**: (recorded in the log above; no other files touched)
**Changes**: the five plan-specified scenarios (inline phase implementation, dispatching past a failed phase, boundary violation after green tests, re-executing committed phases on resume, absorbing report detail into context), each forcing an A/B/C choice with 3+ combined pressures, 5 baseline reps and 5 with-skill reps. With-skill variant prepended the plan-specified SKILL.md read instruction and asked for citations, per plan lines 166–174.

No REFACTOR edits to `skills/plan-to-execution/SKILL.md` — the conditional edit scope was not triggered (no with-skill run produced a new rationalization; every baseline violation matched an already-countered excuse and with-skill reps quoted those counters when complying).

## Verification

Every Automated Verification criterion from the phase, run exactly as written:

| Criterion | Command | Result |
|-----------|---------|--------|
| Campaign log exists | `test -f skills/plan-to-execution/test-campaigns/*-plan-to-execution.md` | PASS |
| All five scenarios recorded | `rg -c '^## Scenario' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md` | PASS (5) |
| Baselines recorded before with-skill runs | `rg '^### Baseline \(no skill\)' ...` → 5 matches; `rg '^### With skill' ...` → 5 matches | PASS (5 and 5) |
| Campaign summary present | `rg '^## Campaign summary' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md` | PASS |
| No status leaked into the skill | `! rg -n 'test-campaigns\|bulletproof\|GREEN\|RED' skills/plan-to-execution/SKILL.md` | PASS |

Relevant output excerpts:

```text
$ test -f skills/plan-to-execution/test-campaigns/*-plan-to-execution.md && echo "1: PASS"
1: PASS
$ rg -c '^## Scenario' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md
5
$ rg -c '^### Baseline \(no skill\)' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md
5
$ rg -c '^### With skill' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md
5
$ rg '^## Campaign summary' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md
## Campaign summary
$ rg -n 'test-campaigns|bulletproof|GREEN|RED' skills/plan-to-execution/SKILL.md
(no matches)
```

Baseline environment evidence (pollution policy): `ls ~/.config/opencode/AGENTS.md` → exists, **0 bytes** (no bleed); `~/.AGENTS.md`, `~/AGENTS.md`, `/etc/opencode/AGENTS.md` → do not exist. Baseline reps were instructed their working directory was `/tmp/opencode/pressure-baseline` (verified empty) and forbidden from reading files outside it.

Manual Verification items are listed here unchecked, for the human:

- [ ] Every baseline rep ran with cwd outside this repo (pollution policy, `AGENTS.md:21-26`) and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim, not pattern-matched (`skills/writing-skills/references/pressure-testing.md:76`)
- [ ] With-skill reps cite specific SKILL.md sections, and citations converge across reps (`skills/writing-skills/references/pressure-testing.md:77`)
- [ ] Any REFACTOR counters added to SKILL.md still leave Phase 1's automated verification passing (vacuous — no REFACTOR edits were made; SKILL.md untouched this phase)

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| "5 baseline reps and 5 with-skill reps, `general` subagents dispatched in parallel in one message per variant" | Reps of each variant were dispatched in parallel; scenarios 1–2 with-skill and scenarios 3–5 baseline/with-skill batches were combined into shared messages (10–15 invocations each) | Every variant's reps were still all-parallel in a single message; combining independent variants into one message reduced round trips without changing per-variant parallelism |

## Issues & Concerns

- **Own-description visibility in baselines:** plan-to-execution's description is visible to subagents via the available-skills list, and it names the exact temptations tested (e.g. "implement plan phases inline", "keep dispatching after a phase fails"). The three all-pass baselines (S1, S3, S4) may partly reflect this rather than pure model priors. This is not the global/per-project rules bleed the pollution policy forbids (none found — global AGENTS.md is empty), and cross-skill description leakage is accepted by `AGENTS.md:21-26`, but the tested skill's *own* description is a softer gray area the human may want to weigh when reading the all-pass baselines. Recorded in the campaign log.
- **Cross-skill leakage observed:** several baseline reps cited executing-plans/iterating-plans language ("one-phase-per-invocation rule", "route through iterating-plans"). Expected and fine per `AGENTS.md:21-26`.
- **Baseline subagents cannot be forcibly sandboxed to the scratch directory** (the task tool has no cwd parameter); the empty-directory constraint was prompt-instructed and no rep reported reading repo files.

## Follow-ups

- Human to confirm the four Manual Verification items above before Phase 3 begins (per the plan's Implementation Note).
- Human to decide whether to commit the campaign log (and Phase 1's SKILL.md, still uncommitted) before Phase 3.
- Phase 3: add the plan-to-execution paragraph to `AGENTS.md` per the plan.
