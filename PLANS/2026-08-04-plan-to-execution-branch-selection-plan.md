---
artifact: implementation-plan
date: 2026-08-04
git_commit: 622da60bde2858ece0e2e15ca1a1e44d60208078
branch: dev/sloptime
request: "analyze the plan-to-execution skill. i would like to propose a new rule: it should prefer to work in a task-specific local branch and not on master. we should detect, after verifying the plan file is approved and committed, that we are on master and then offer the user to create a feature branch. this is not required - the user can reject the request and work from master branch. if we are on a local dev branch and not master/main then we don't need to prompt the user, just keep using the current branch. it may be necessary to read .git/config to determine the mainline branch, since it may not be called "master". propse a solution but do not implement."
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: draft
---

# plan-to-execution Branch Selection Rule Implementation Plan

> **For the implementing agent:** Read this plan before starting. After completing the changes, run all automated verification; when it passes, pause for human confirmation of the manual criteria.

## Context

plan-to-execution orchestrates full execution of an approved plan, producing many commits. Today it runs wherever the user's checkout happens to point — including the mainline branch (`master`/`main`), where a multi-phase execution lands phase commits, worktree merge-backs, and resume state directly on mainline. The user wants the orchestrator to prefer a task-specific local branch: after the plan is validated as approved and committed, if the current branch is the mainline branch, offer to create a feature branch; the user may decline. If already on a non-mainline branch, proceed silently.

## Current State

- `skills/plan-to-execution/SKILL.md` is the only file touched. Its Workflow (skills/plan-to-execution/SKILL.md:54-65) goes straight from input validation (step 1, line 56) to schedule computation (step 2, line 57) with no branch awareness anywhere in the skill.
- Worktree branches for parallel phases are created from and merged back into current HEAD (skills/plan-to-execution/SKILL.md:62), so a feature branch selected up front is followed automatically — no change needed to **isolating-worktrees**.
- Resume Detection is HEAD-relative via `git merge-base --is-ancestor <hash> HEAD` (skills/plan-to-execution/SKILL.md:50); resuming on mainline after earlier phases committed to a feature branch fails the ancestor check and would wrongly re-dispatch completed phases — the new rule must cover this case.
- Skill validation tooling exists: `.venv/bin/agentskills validate skills/plan-to-execution` exits 0 on the current skill (verified 2026-08-04).

## Desired End State

`skills/plan-to-execution/SKILL.md` contains a **Branch Selection** rule that runs on every invocation after plan validation and before scheduling: detects the mainline branch via git plumbing (never by parsing `.git/config`), offers to create `dev/<plan-base>` when on mainline, respects a refusal for the run without remembering it, proceeds silently on non-mainline branches, stops on detached HEAD, and offers to check out the feature branch on resume when completed-phase commits are stranded there. Verified by `agentskills validate` passing and a manual read-through of the edited skill.

## What We're NOT Doing

- No changes to **isolating-worktrees**, **executing-plans**, or any other skill.
- No worktree/branch cleanup behavior (cleanup remains a non-goal per the skill's Boundary, skills/plan-to-execution/SKILL.md:101-103).
- No persistence of the user's branch refusal across sessions (re-ask each invocation, per user decision).
- No pressure-test campaign for the new rule — that is a separate downstream activity via **pressure-testing**, to be scheduled after this plan lands.
- No parsing of `.git/config` under any circumstances.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Detect mainline by parsing `.git/config` vs git plumbing | Git plumbing: `git symbolic-ref --short refs/remotes/origin/HEAD`, fallback to verifying local `main` then `master`, fallback to asking the user | plan-to-execution creates linked worktrees (skills/plan-to-execution/SKILL.md:62); `.git/config` is not the real config in a worktree checkout, so manual parsing breaks silently |
| Feature-branch name | `dev/<plan-base>`, where `<plan-base>` is the plan filename minus `-plan.md`; if taken, `dev/<plan-slug>` (user-supplied at prompt time) | Matches the existing `<plan-base>` convention used for report paths and worktree branches (skills/plan-to-execution/SKILL.md:35,62) |
| Declined branch offer: re-ask on later invocations? | Re-ask each fresh invocation, including resumes; refusal is per-run only, never recorded | User decision (2026-08-04); each invocation is a fresh session with no memory |
| Detached HEAD | Stop and surface; never silently branch from a detached state | Branching from detached HEAD without telling the user strands commits |
| Resume with phase commits stranded on `dev/<plan-base>` | Offer to check out the feature branch before dispatching | The ancestor check (skills/plan-to-execution/SKILL.md:50) already treats this as "not complete"; the prompt makes it recoverable instead of a destructive re-dispatch |
| Where the rule lives in the Workflow | New step 2, after input validation (current step 1, line 56), before schedule computation | The plan-approved-and-committed check is step 1's job; branch selection depends on it and must precede any dispatch or commit |

## Implementation Approach

Surgical edits to one markdown file: insert one new section, insert and renumber the Workflow steps, append three Rationalizations rows and one Red Flag. No code, no scripts, no other files.

## Changes Required

#### 1. New "Branch Selection" section
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: Insert the following section immediately after the Input Contract section (after line 15, before `## Plan Consumption Contract` at line 17):

```markdown
## Branch Selection

Runs on every invocation, after plan validation, before scheduling. Determine the current branch (`git symbolic-ref --short HEAD`) and the mainline branch: `git symbolic-ref --short refs/remotes/origin/HEAD`, falling back to verifying local `main` then `master` (`git rev-parse --verify`), falling back to asking the user. NEVER parse `.git/config` — worktrees relocate it.

- **Current branch is mainline:** offer the user a choice — create `dev/<plan-base>` (or `dev/<plan-slug>` if that name is taken) and continue there, or stay on mainline. A refusal is final for this run; proceed without commentary. Refusals are not remembered — re-ask on each fresh invocation, including resumes.
- **Current branch is not mainline:** proceed silently on the current branch.
- **Detached HEAD:** stop and surface; never silently branch from a detached state.
- **Resume case:** if phase reports reference commits present on `dev/<plan-base>` but not ancestors of HEAD, offer to check out that branch before dispatching — this is the recoverable form of the stranded-branch ancestor-check failure.
```

#### 2. Workflow step insertion and renumbering
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: In the Workflow section (lines 54-65), insert a new step 2 and renumber the existing steps 2-6 to 3-7:

- New step 2 text: `2. **Run Branch Selection.** Follow the Branch Selection section: detect mainline, offer \`dev/<plan-base>\` when on mainline, proceed per the user's choice.`
- Existing `2. **Read the plan and compute the schedule.**` becomes step 3.
- Existing `3. **Run Resume Detection.**` becomes step 4.
- Existing `4. **Execute each schedule step, in order:**` becomes step 5.
- Existing `5. **Final verification.**` becomes step 6.
- Existing `6. **Report and stop.**` becomes step 7.

Step bodies are unchanged; only the leading numbers change.

#### 3. Rationalizations rows
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: Append three rows to the Rationalizations table (after line 82):

```markdown
| "The user approved the plan, they obviously want it on master" | Branch placement is a separate decision. Ask once; it's one question. |
| "I'll parse .git/config for the default branch" | Worktrees relocate config. Use `git symbolic-ref refs/remotes/origin/HEAD` with the main/master fallback. |
| "User declined the branch — I'll ask again on resume" | A refusal is final for the run. Proceed on mainline without comment. |
```

#### 4. Red Flag entry
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: Append one bullet to the Red Flags - STOP list (after line 99):

```markdown
- "I'll just run it on master without asking — creating branches is cleanup churn"
```

### Success Criteria

#### Automated Verification:
- [ ] Skill validates: `.venv/bin/agentskills validate skills/plan-to-execution`

#### Manual Verification:
- [ ] The Branch Selection section appears between Input Contract and Plan Consumption Contract and contains all four bullet cases (mainline, non-mainline, detached HEAD, resume)
- [ ] Workflow steps are numbered 1-7 with Branch Selection as step 2 and all original step bodies intact
- [ ] The three new Rationalizations rows and one new Red Flag are present
- [ ] No other file in the repo was modified: `git status --short` shows only `skills/plan-to-execution/SKILL.md`

**Implementation Note**: After completing the changes and automated verification passes, pause for human confirmation of the manual criteria.

## Testing Strategy

### Unit Tests:
- None — this is a markdown skill-definition edit; `agentskills validate` is the structural check.

### Integration Tests:
- None in this plan. A pressure-test campaign (baseline run without the rule vs with-skill run) is the correct follow-up via **pressure-testing** and is explicitly out of scope here.

### Manual Testing Steps:
1. Read the edited `skills/plan-to-execution/SKILL.md` top to bottom and confirm the four manual criteria above.

## Final Verification

.venv/bin/agentskills validate skills/plan-to-execution

## References

- PRD: none
- Context bundle: none (quick pass) — evidence gathered in-session
- Research findings: none (quick pass) — evidence gathered in-session
- Key implementation files: `skills/plan-to-execution/SKILL.md:14-16` (Input Contract), `skills/plan-to-execution/SKILL.md:50` (ancestor check), `skills/plan-to-execution/SKILL.md:54-65` (Workflow), `skills/plan-to-execution/SKILL.md:62` (worktree merge-back), `skills/plan-to-execution/SKILL.md:73-82` (Rationalizations), `skills/plan-to-execution/SKILL.md:86-99` (Red Flags)
