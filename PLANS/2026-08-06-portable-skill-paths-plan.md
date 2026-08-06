---
artifact: implementation-plan
date: 2026-08-06
git_commit: a6024dc7b01689aca90f2613aea17632ccae0549
branch: dev/sloptime
request: "the agentskills check should only run if `agentskills` is in PATH and then it should not use a hard-coded repo-specific path. we expect the agents and skills to be available to the other projects as this repo's content would be installed as a plugin - so referencing specific skills or agents from this repo is fine, but assuming the path is not."
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: approved
---

# Portable Skill Paths (Plugin-Install Model) Implementation Plan

> **For the implementing agent:** Read this plan before starting. After completing the changes, run all automated verification; when it passes, pause for human confirmation of the manual criteria.

## Context

These skills ship as a plugin installed globally and used in sessions against arbitrary projects. Several skills and reference files hard-code paths (`skills/<name>/...`, `skills/writing-skills/scripts/trigger-test.sh`) and repo-identity language ("this repo", "the repo AGENTS.md") that only resolve when the current working directory is this repository. Under the plugin model, name references to sibling skills and agents (`writing-plans`, `trigger-evaluator`, `eval-reader`) are valid everywhere; path assumptions are not. Additionally, `agentskills validate` must only run when `agentskills` is on `PATH`, and must receive the resolved skill directory rather than `skills/<name>`.

## Current State

- `skills/writing-skills/SKILL.md` — description says "deploying it to this repo's skills/ directory" (line 3); Placement rule step 2 and Invocation Branch guard assume `./skills` in cwd (lines 16, 24); `agentskills validate skills/<name>` appears three times unconditionally (lines 85, 195, 207); anecdotal "invalidated 11 skills in this repo" (line 82).
- `skills/writing-skills/references/trigger-testing.md` — invokes the harness as `skills/writing-skills/scripts/trigger-test.sh` from "the repo root" (steps 4a, 4c, 10; Optimization Loop; Harness; Common Mistakes); target check, train/validation split, results-log paths, and the hash command all hard-code `skills/<name>/...`; Contamination Rules cite "repo AGENTS.md" and "this repo's skills/".
- `skills/writing-skills/references/pressure-testing.md` — `opencode run --dir <repo-root> --agent eval-reader` and "with-skill reps MUST run with the repo as cwd" presume the target skill lives in the cwd repo; "Baseline cwd check" lesson references "repo AGENTS.md".
- `skills/project-bootstrap-nix/SKILL.md:43` — invokes `skills/project-bootstrap-nix/scripts/bootstrap.sh` repo-relatively.
- `skills/writing-quick-plans/SKILL.md:25` — references the plan template by the sibling-relative path `writing-plans/references/plan-template.md`.
- `skills/writing-skills/scripts/trigger-test.sh` — usage text says SOURCE defaults to "the repository root containing this script"; the actual default (`../../..` from the script) already works when the plugin preserves the repo layout (`skills/` + `agents/` siblings).
- The skill-loading runtime injects a "Base directory for this skill: <abs path>" line when a skill loads, and states that relative paths in the skill are relative to that base. This is the generic resolution mechanism.

## Desired End State

No skill body, reference file, or script usage text instructs the agent to resolve skill files via a cwd-relative `skills/...` path or refers to "this repo" as the skills' home. Script invocations resolve via the loading skill's reported base directory. `agentskills validate` runs only when `command -v agentskills` succeeds, against the resolved skill directory. Verification: the grep gates below find no residual repo-specific path instructions, and the trigger-test harness still passes its self-test.

## What We're NOT Doing

- Not changing the `PLANS/`, `PRDS/`, `RESEARCH/`, `.worktrees/` conventions — those target the current project and are portable by design.
- Not rewriting historical `test-campaigns/` logs or `trigger-evals/` data.
- Not extending `trigger-test.sh` to stub project-local skills outside the plugin source tree (recorded as a known limitation).
- Not changing the `--source` default resolution logic in `trigger-test.sh` (it already resolves relative to the script, which survives plugin install); only its usage text is reworded.
- Not renaming or moving any skill, agent, script, or directory.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| How to reference skill scripts/files generically | "the base directory reported when the skill loads" (e.g. `<writing-skills base>/scripts/trigger-test.sh`) | The runtime injects this path at load time; it is correct under every install layout with zero configuration |
| `agentskills validate` unconditional vs guarded | Guard with `command -v agentskills`; skip with a note if absent | User directive; the tool lives in this repo's `.venv` and won't exist in every install |
| `trigger-test.sh --source` default: rework or keep | Keep; reword usage text from "repository root" to "the plugin/repo root containing this script" and document the stubs-plugin-skills-only limitation | `../../..` from the script resolves correctly whenever the plugin preserves the `skills/` + `agents/` layout; a rework adds risk for no portability gain |
| "this repo" rewording target | "the current project" when meaning the user's cwd repo; "the plugin" / "the skill library" when meaning the skills' home | Two distinct referents were collapsed into one phrase; separating them is what makes instructions unambiguous |
| "the repo root" / "the repo" cwd language in trigger-testing.md | Keep — per user direction, it correctly refers to the current project the user is working in, whatever repo that is | Only cwd-*relative skill file paths* (`skills/writing-skills/scripts/...`) are broken under the plugin model; cwd-as-project-root is exactly right |
| Target-skill lookup in campaigns | Resolve the named skill from the session's loaded skills (its reported base directory), not a `./skills` glob | Matches how every other skill reference works under the plugin model |

## Implementation Approach

Pure documentation/wording edits across five markdown files plus usage-text edits in one shell script. No behavior changes except the `agentskills` guard wording. Edit file-by-file; each file's edits are independent.

## Changes Required

#### 1. writing-skills SKILL.md
**File**: `skills/writing-skills/SKILL.md`
**Changes**:
- Description (line 3): replace "reviewing a skill before deploying it to this repo's skills/ directory" with "reviewing a skill before deployment".
- Placement rule step 2 (line 16): replace "If this repo is a skill library (its AGENTS.md directs where skills live — e.g. this repo uses `skills/`), follow that direction." with wording that checks the current project's AGENTS.md for skill-placement direction.
- Invocation Branch guard (line 24): replace "if the named skill has no `skills/<name>/SKILL.md` in this repo, report that the target cannot be found" with "resolve the named skill from the session's loaded skills (the base directory reported when a skill loads); if it is not loaded and cannot be found, report that the target cannot be found".
- Colon-in-scalar bullet (line 82): replace "invalidated 11 skills in this repo" with "invalidated 11 skills in practice".
- All three `agentskills validate skills/<name>` sites (lines 85, 195, 207): replace with a guarded form — "if `command -v agentskills` succeeds, run `agentskills validate <resolved-skill-dir>` (the skill's base directory); it must print `Valid skill`. If `agentskills` is not on PATH, note the skip and continue."

#### 2. trigger-testing reference
**File**: `skills/writing-skills/references/trigger-testing.md`
**Changes**:
- Step 1: replace "`skills/<name>/SKILL.md` in this repo" with resolution via the session's loaded skills / the target skill's base directory.
- Step 4a: keep "From the repo root" — it correctly means the root of the current project the user is working in (per user direction). Change only the script path: invoke as `<base>/scripts/trigger-test.sh init` where `<base>` is the writing-skills base directory reported at load. Apply the same script-path substitution to every `skills/writing-skills/scripts/trigger-test.sh` invocation (steps 4c, 10, Optimization Loop sync command, Harness invoke block, Common Mistakes references).
- Step 4 (workspace description), Train/Validation Split, Results Log Format, `trigger-evals/` directory convention: replace `skills/<skill-name>/...` with "the target skill's own directory (where its SKILL.md resides)" — the existing parenthetical already says this; make it the primary statement and drop the `skills/` prefix and the "never a repo-root `<skill-name>/` directory" clause.
- Contamination Rules: replace only plugin-identity phrasing — "Per repo `AGENTS.md`, these skills ship together" → "these skills ship together in the same plugin"; "a skill absent from this repo's `skills/`" → "a skill not shipped in this plugin"; "this repo's descriptions" → "the plugin's descriptions". Leave "the repo `AGENTS.md`" / "the repo codebase" untouched where they mean the current project (correct per user direction).
- Hash command: `sed -n 's/^description: //p' <target-skill-base>/SKILL.md | sha256sum | cut -c1-12`.

#### 3. pressure-testing reference
**File**: `skills/writing-skills/references/pressure-testing.md`
**Changes**:
- Execution Protocol step 2: replace `opencode run --dir <repo-root>` and "With-skill reps MUST run with the repo as cwd: from an external cwd, `Read` of the skill files by absolute path hits `external_directory` permission auto-rejection" with the generic requirement: run with a cwd from which `Read` of the target skill's absolute path is permitted (when the target lives in the current project, the project root satisfies this; for a plugin-installed skill, use a directory whose permissions cover the install location). Keep the `--agent eval-reader` reference (valid by name).
- Campaign-Execution Lessons: leave "repo `AGENTS.md`" phrasing as-is — it correctly means the current project.

#### 4. project-bootstrap-nix SKILL.md
**File**: `skills/project-bootstrap-nix/SKILL.md`
**Changes**:
- Line 43: replace `skills/project-bootstrap-nix/scripts/bootstrap.sh "PROJECT_NAME"` with an instruction to run `bootstrap.sh` from the skill's `scripts/` directory, resolved via the base directory reported when the skill loads: `<base>/scripts/bootstrap.sh "PROJECT_NAME"`.

#### 5. writing-quick-plans SKILL.md
**File**: `skills/writing-quick-plans/SKILL.md`
**Changes**:
- Line 25: replace "per `writing-plans/references/plan-template.md`" with "per the plan template in the `writing-plans` skill (`references/plan-template.md`, resolved via that skill's base directory)".

#### 6. trigger-test.sh usage text
**File**: `skills/writing-skills/scripts/trigger-test.sh`
**Changes**:
- Usage text: replace "SOURCE defaults to the repository root containing this script" (init entry) and "defaulting to the repository root" (sync/status entries) with "SOURCE defaults to the plugin/repo root containing this script (resolved two directories up from the script, expecting `skills/` and `agents/` beneath it)". No logic changes.

### Success Criteria

#### Automated Verification:
- [ ] No repo-relative script invocations remain: `grep -rn "skills/writing-skills/scripts\|skills/project-bootstrap-nix/scripts" skills --include="*.md" | grep -v test-campaigns` returns empty
- [ ] No `skills/<name>`-style path instructions remain: `grep -rn "skills/<" skills --include="*.md" | grep -v test-campaigns | grep -v trigger-evals` returns empty
- [ ] `agentskills validate` no longer invoked with a hard-coded path: `grep -n "agentskills validate skills/" skills/writing-skills/SKILL.md` returns empty, and every remaining `agentskills validate` mention is paired with a `command -v` guard
- [ ] "this repo" eliminated from instructional text: `grep -rn "this repo" skills --include="*.md" | grep -v test-campaigns | grep -v trigger-evals` returns empty (or only matches inside quoted historical anecdotes reworded per Change 1)
- [ ] Harness self-test still passes: `bash skills/writing-skills/scripts/test-trigger-test.sh`
- [ ] Edited skills still validate: `agentskills validate skills/writing-skills && agentskills validate skills/project-bootstrap-nix && agentskills validate skills/writing-quick-plans` (each prints `Valid skill`)

#### Manual Verification:
- [ ] Read each edited file end-to-end: no remaining instruction assumes cwd is this repository
- [ ] Every script invocation in `trigger-testing.md` and `project-bootstrap-nix/SKILL.md` expresses resolution via the skill's base directory
- [ ] `trigger-test.sh` usage text accurately describes the `--source` default (`bash skills/writing-skills/scripts/trigger-test.sh` with no args prints usage)

## Testing Strategy

### Unit Tests:
- None — documentation-only changes; `test-trigger-test.sh` covers the script's behavior (unchanged logic).

### Integration Tests:
- `bash skills/writing-skills/scripts/test-trigger-test.sh` — verifies the harness script still functions after usage-text edits.

### Manual Testing Steps:
1. From a directory outside this repo, simulate resolution: confirm the wording in each edited file lets an agent derive script paths from a reported base directory alone.

## Final Verification

grep -rn "skills/writing-skills/scripts\|skills/project-bootstrap-nix/scripts" skills --include="*.md" | grep -v test-campaigns
grep -rn "this repo" skills --include="*.md" | grep -v test-campaigns | grep -v trigger-evals
bash skills/writing-skills/scripts/test-trigger-test.sh
agentskills validate skills/writing-skills
agentskills validate skills/project-bootstrap-nix
agentskills validate skills/writing-quick-plans

## References

- PRD: none
- Context bundle: none (quick pass) — evidence gathered in-session
- Research findings: none (quick pass) — evidence gathered in-session
- Key implementation files: `skills/writing-skills/SKILL.md`, `skills/writing-skills/references/trigger-testing.md`, `skills/writing-skills/references/pressure-testing.md`, `skills/project-bootstrap-nix/SKILL.md:43`, `skills/writing-quick-plans/SKILL.md:25`, `skills/writing-skills/scripts/trigger-test.sh`
