---
artifact: implementation-report
date: 2026-07-25
plan: PLANS/2026-07-25-prd-to-plan-plan.md
phase: 2
status: DONE_WITH_CONCERNS
git_commit_start: e70aebac8416adba54f7adaac7c54c6b2c961eb7
git_commit_end: uncommitted
---

# Phase 2: Pressure-Test Campaign — Implementation Report

## Summary

Ran the full RED-GREEN campaign against `skills/prd-to-plan/SKILL.md`: 4 scenarios × (5 baseline + 5 with-skill) = 40 `general` subagent runs, baselines against clean fixtures in `/tmp/opencode/prd-to-plan-scenarios/`. Scenarios 1 and 4 showed real baseline violations (3/5 and 5/5) with 5/5 with-skill compliance and convergent citations — bulletproof. Scenarios 2 and 3 showed no baseline failure, so no counter-guidance was authored (per protocol). No REFACTOR was needed: zero new rationalizations in with-skill runs, SKILL.md unchanged. One pollution event (repo AGENTS.md bleeding into Scenario 1 baselines) was detected and is flagged below for the human per the repo pollution policy.

## Changes Made

#### 1. Campaign log
**File**: `skills/prd-to-plan/test-campaigns/2026-07-25-prd-to-plan.md`
**Changes**: created per the results-log template (`skills/writing-skills/references/pressure-testing.md:146-166`): environment description (including pollution observations), four scenario sections each with baseline results + verbatim rationalizations, with-skill results + citations, new-rationalizations section, verdict, and a campaign summary table.

No other files were created or modified. `skills/prd-to-plan/SKILL.md` is untouched (no REFACTOR counters were required).

## Verification

| Criterion | Command | Result |
|-----------|---------|--------|
| Campaign log exists | `test -f skills/prd-to-plan/test-campaigns/*-prd-to-plan.md` | PASS |
| All four scenarios recorded | `rg -c '^## Scenario' ...` → 4 | PASS |
| Baselines recorded in every scenario | `rg '^### Baseline \(no skill\)' ...` → 4 matches | PASS |
| With-skill recorded in every scenario | `rg '^### With skill' ...` → 4 matches | PASS |
| Campaign summary present | `rg '^## Campaign summary' ...` → match at line 130 | PASS |
| No status leaked into the skill | `! rg -n 'test-campaigns|bulletproof|GREEN|RED' skills/prd-to-plan/SKILL.md` → no matches (exit 1) | PASS |

```text
1 PASS: log exists
4                     # '^## Scenario' count
4 / 4                 # Baseline / With skill counts
130:## Campaign summary
rg on SKILL.md: exit=1 (no leak)
```

Manual Verification items are listed here unchecked, for the human:

- [ ] Every baseline rep ran with cwd outside this repo (pollution policy, `AGENTS.md:19-24`) and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim, not pattern-matched (`skills/writing-skills/references/pressure-testing.md:76`)
- [ ] With-skill reps cite specific SKILL.md sections, and citations converge across reps (`skills/writing-skills/references/pressure-testing.md:77`)
- [ ] Any REFACTOR counters added to SKILL.md still leave Phase 1's automated verification passing (vacuous — no counters added; SKILL.md untouched)

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| None | — | — |

## Issues & Concerns

- **Pollution event (escalating per `AGENTS.md:19-24`):** Scenario 1 baseline reps 2 and 5 quoted this repo's `AGENTS.md` ("Steps 2–4 are skippable when the input they produce already exists") despite prompts confining them to `/tmp/opencode/prd-to-plan-scenarios/`. Repo-root rules bleed into subagent baselines regardless of prompt instruction. Direction of bias was toward the violation (silent reuse), so it does not mask a compliant baseline and the Scenario 1 verdict stands — but per policy this is flagged for the human before trusting baseline results. Suggested owner: human reviewing this campaign; a fix (e.g. running baseline subagents with a different workspace root) is out of this phase's scope.
- **Scenarios 2 and 3 produced no baseline violation** (5/5 and 5/5 compliance). Scenario 3's compliance arrived via cross-skill leakage of the `iterating-plans` description — which repo policy deems expected and a good outcome. Per `pressure-testing.md:75` no counter-guidance was authored for these scenarios; the FR-005 and FR-009 rules remain because the PRD mandates them, and the log flags both as not-validated-by-baseline rather than bulletproof.
- Meta-testing was not applicable: no with-skill run violated, so there was nothing to meta-test.

## Follow-ups

- Human: confirm the four Manual Verification items above, and weigh the flagged AGENTS.md pollution before accepting the Scenario 1 baseline.
- Human: decide whether the repo needs a mechanical fix for AGENTS.md bleed into subagent baselines (e.g. dispatching baselines from a non-repo cwd) before future campaigns.
- Phase 3 (document prd-to-plan in AGENTS.md) is unblocked once the manual criteria are confirmed.
