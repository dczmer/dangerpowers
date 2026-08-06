---
artifact: implementation-report
date: 2026-08-06
plan: PLANS/2026-08-06-portable-skill-paths-plan.md
phase: 3
status: DONE_WITH_CONCERNS
git_commit_start: 4c7838b51c07533c8e00a2475ab3e425ed3ca38f
git_commit_end: uncommitted
---

# Phase 3: pressure-testing reference — Implementation Report

## Summary

Reworded Execution Protocol step 2 in `skills/writing-skills/references/pressure-testing.md` so with-skill reps no longer assume the target skill lives in the cwd repo: the `--dir` placeholder is now `<skill-readable-cwd>` and the "MUST run with the repo as cwd" sentence is replaced by the generic permission requirement (cwd must permit `Read` of the target skill's absolute path; project root works when the skill is in the current project, otherwise use a directory covering the plugin install location). The `--agent eval-reader` reference and the Campaign-Execution Lessons "repo `AGENTS.md`" phrasing were left untouched, per the plan. All automated criteria pass except the plan-wide script-path grep, which still matches `skills/project-bootstrap-nix/SKILL.md:43` — that file is Phase 4's, outside this phase's ownership.

## Changes Made

#### 1. pressure-testing reference
**File**: `skills/writing-skills/references/pressure-testing.md`
**Changes**: In "Execution Protocol (opencode)" step 2, replaced `opencode run --dir <repo-root>` with `opencode run --dir <skill-readable-cwd>` (kept `--agent eval-reader`), and replaced the sentence "With-skill reps MUST run with the repo as cwd: from an external cwd, `Read` of the skill files by absolute path hits `external_directory` permission auto-rejection and the run is void." with the generic requirement: with-skill reps MUST run with a cwd from which `Read` of the target skill's absolute path is permitted (same auto-rejection consequence preserved), noting the project root satisfies this when the target lives in the current project and that a plugin-installed skill needs a directory whose permissions cover the install location. Campaign-Execution Lessons left as-is per the plan's second bullet.

## Verification

Every Automated Verification criterion from the plan (plan-wide greps; failures attributable to other phases' files are reported, not fixed):

| Criterion | Command | Result |
|-----------|---------|--------|
| No repo-relative script invocations remain | `grep -rn "skills/writing-skills/scripts\|skills/project-bootstrap-nix/scripts" skills --include="*.md" \| grep -v test-campaigns` | FAIL (see below) |
| No `skills/<name>`-style path instructions remain | `grep -rn "skills/<" skills --include="*.md" \| grep -v test-campaigns \| grep -v trigger-evals` | PASS |
| `agentskills validate` guarded, no hard-coded path | `grep -n "agentskills validate skills/" skills/writing-skills/SKILL.md` (empty) + every mention paired with `command -v` guard | PASS |
| "this repo" eliminated from instructional text | `grep -rn "this repo" skills --include="*.md" \| grep -v test-campaigns \| grep -v trigger-evals` | PASS |
| Harness self-test still passes | `bash skills/writing-skills/scripts/test-trigger-test.sh` | PASS |
| Edited skills still validate | `agentskills validate skills/writing-skills && agentskills validate skills/project-bootstrap-nix && agentskills validate skills/writing-quick-plans` | PASS |

Relevant output excerpts:

```text
$ grep -rn "skills/writing-skills/scripts\|skills/project-bootstrap-nix/scripts" skills --include="*.md" | grep -v test-campaigns
skills/project-bootstrap-nix/SKILL.md:43:   skills/project-bootstrap-nix/scripts/bootstrap.sh "PROJECT_NAME"
```

```text
$ grep -rn "skills/<" skills --include="*.md" | grep -v test-campaigns | grep -v trigger-evals
(empty, exit=1)

$ grep -n "agentskills validate skills/" skills/writing-skills/SKILL.md
(empty, exit=1)
# remaining mentions all guarded, e.g.:
85:If `command -v agentskills` succeeds, run `agentskills validate <resolved-skill-dir>` ...
195:- [ ] If `command -v agentskills` succeeds, `agentskills validate <resolved-skill-dir>` ...
207:- [ ] If `command -v agentskills` succeeds, `agentskills validate <resolved-skill-dir>` passes ...

$ grep -rn "this repo" skills --include="*.md" | grep -v test-campaigns | grep -v trigger-evals
(empty, exit=1)
```

```text
$ bash skills/writing-skills/scripts/test-trigger-test.sh
Ran 12 tests.
OK
```

```text
$ agentskills validate skills/writing-skills && agentskills validate skills/project-bootstrap-nix && agentskills validate skills/writing-quick-plans
Valid skill: skills/writing-skills
Valid skill: skills/project-bootstrap-nix
Valid skill: skills/writing-quick-plans
```

Manual Verification items are listed here unchecked, for the human:

- [ ] Read each edited file end-to-end: no remaining instruction assumes cwd is this repository (this phase: `pressure-testing.md` only)
- [ ] Every script invocation in `trigger-testing.md` and `project-bootstrap-nix/SKILL.md` expresses resolution via the skill's base directory (no script invocations exist in `pressure-testing.md`; the two named files belong to Phases 2 and 4)
- [ ] `trigger-test.sh` usage text accurately describes the `--source` default (Phase 6 file; not touched here)

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| Replace the sentence ending "...permission auto-rejection" | The replaced sentence in the file actually ends "...permission auto-rejection and the run is void."; the full sentence including the trailing clause was replaced, preserving the void-run consequence in the new wording | The plan's quoted text was a prefix of the actual sentence; replacing only the quoted prefix would have left an orphaned clause |

## Issues & Concerns

- **Verification failure outside this phase's file ownership:** the plan-wide grep for repo-relative script invocations still matches `skills/project-bootstrap-nix/SKILL.md:43` (`skills/project-bootstrap-nix/scripts/bootstrap.sh "PROJECT_NAME"`). That file is Phase 4's Changes Required item; per the Iron Rules it was not touched. Evidence above. Expected to clear once Phase 4 executes.
- **Plan drift note:** plan frontmatter records `git_commit: a6024dc7...`, but execution started at `4c7838b51c...`; sibling phases 1, 2, 5, and 6 appear already applied at HEAD (their greps pass). Phase 3's target text matched the plan exactly, so no mismatch protocol was triggered.

## Follow-ups

- Controller: run/confirm Phase 4 (`skills/project-bootstrap-nix/SKILL.md`) — it is the only remaining grep failure.
- Human: perform the Manual Verification items listed above for the `pressure-testing.md` portion.
