---
artifact: implementation-report
date: 2026-07-27
plan: PLANS/2026-07-27-execution-mode-declaration-plan.md
phase: 3
status: DONE
git_commit_start: c5810944fdb5a1742910b53a5d9639f665753250
git_commit_end: <this report is committed in the phase commit; the phase commit SHA is reported to the controller>
---

# Phase 3: Pressure-Test Campaign and Addendum Supersede — Implementation Report

## Summary

Ran the RED-GREEN-REFACTOR pressure-test campaign against the new execution-mode-declaration discipline (writing-plans), the declaration-consumption contract (plan-to-execution), and the extended step-6 consistency check (iterating-plans): four scenarios, A/B/C choice, 3+ pressures each, 5 baseline + 5 with-skill reps per scenario, parallel headless dispatch per variant, every output read manually. Baselines did not violate in any scenario (0/20 valid reps), so per protocol no counter-guidance was authored and no REFACTOR round was required; with-skill reps complied 20/20 with citations converging on the sections Phases 1–2 added. No skill files were edited in this phase. The 2026-07-26 addendum's untested inference-based rule is marked superseded.

## Changes Made

#### 1. Pressure-test campaign
**File**: `skills/writing-plans/test-campaigns/2026-07-27-execution-mode-declaration.md`
Created per the results-log template. Four scenarios as specified by the plan: (1) grouping a test phase parallel, (2) misclassifying execution mode, (3) reclassifying at execution time, (4) stranded pairing after a split. Baselines ran headless with cwd `/tmp/opencode/pressure-baseline/` (outside this repo); with-skill reps ran with repo cwd after observing that headless runs from outside the repo cannot read the skill files (`external_directory` auto-reject). Global `~/.config/opencode/AGENTS.md` verified 0 bytes. Four baseline reps attempted to load a repo skill via the skill tool (description leakage, expected per `AGENTS.md` pollution policy), were auto-rejected, and were rerun fresh. Raw outputs: `/tmp/opencode/campaign/2026-07-27-execution-mode/`.

Interaction finding recorded in the log: the 2026-07-27 plan-format campaign's "disjoint ⇒ group" teaching needs no erratum — with-skill reps cite the integrated-result exception as part of the independence criterion itself (SKILL.md:59, plan-template.md:126), and no rep read the two rules as conflicting.

#### 2. Supersede the untested-rule addendum
**File**: `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`
Appended the plan-specified supersede note to the "Addendum 2026-07-27" section.

## Verification

### Automated Verification
- [x] Campaign log exists: `test -f skills/writing-plans/test-campaigns/*-execution-mode-declaration.md` — pass
- [x] All four scenarios recorded: `rg -c '^## Scenario'` returns 4 — pass
- [x] Baselines and with-skill runs recorded in every scenario: `^### Baseline \(no skill\)` count 4, `^### With skill` count 4 — pass
- [x] Campaign summary present: `^## Campaign summary` matches — pass
- [x] Addendum superseded: `rg -n 'Superseded 2026-07-27'` matches at line 148 — pass
- [x] No status leaked into the skills: `! rg -n 'test-campaigns|bulletproof|GREEN|RED'` over the four skill files — pass

### Manual Verification
- [x] Every baseline rep ran with cwd outside this repo (`/tmp/opencode/pressure-baseline/`); the log's Environment section states the baseline environment — pending human confirmation
- [x] Every run's output was read manually, with rationalizations recorded verbatim in the log — pending human confirmation
- [x] With-skill reps cite specific skill/template sections, and citations converge across reps (per-scenario convergence recorded in each Verdict) — pending human confirmation
- [x] No REFACTOR counters were added, so Phases 1–2 automated verification is untouched; Phase 2's criteria were re-verified after the pre-campaign red-flag alignment edit (`c581094`) — pending human confirmation

## Concerns

- Baseline compliance was total (0/20 violations). The log records this plainly: the declaration-based discipline matches what the model reasons unaided under these pressures; the campaign demonstrates the text binds and is citable, not that it reverses a observed failure. Three of four baseline reps in scenario 4 initially reached for the iterating-plans skill (auto-rejected), suggesting the skill descriptions alone already signal the correct behavior — recorded in the log per the pollution policy.
- No rule shipped untested: no REFACTOR counters were needed, and nothing was added to the skills in this phase.
