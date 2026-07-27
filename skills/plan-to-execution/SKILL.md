---
name: plan-to-execution
description: Use when an approved implementation plan in PLANS/ is ready to be executed end to end, or when tempted to implement plan phases inline in the orchestrating conversation, run plan-declared independent phases sequentially, keep dispatching after a phase fails, re-execute already-committed phases on resume, or proceed to review, cleanup, plan completion, or PR creation after the plan's tests pass. Keywords: execute plan, orchestrate execution, plan to execution, parallel phases, git worktree, phase subagents, resume interrupted run, merge back, final test run, approved plan.
---

# Skill: plan-to-execution

This skill orchestrates execution of one approved plan, end to end. It produces no phase implementation itself — **executing-plans** subagents produce it. This skill owns scheduling, dispatch, worktree setup (via **isolating-worktrees**), merge-back, resume detection, final verification, and all user interaction. The plan format it consumes is produced by **writing-plans**; when the plan appears to have drifted from the code, route the human to **iterating-plans** — never patch the plan yourself.

## Input Contract

Two inputs (FR-001):

1. **Path to a `status: approved` plan in `PLANS/`** (required). The plan is the sole source of phase definitions, phase-scoped context, independence declarations, and verification commands. If the plan is missing, unreadable, or its frontmatter status is anything other than `approved`, stop and tell the user an approved plan is required. **No exceptions:** not for "the plan is basically final", not for "only one phase remains", not for "the user is in a hurry".
2. **Optional free-text user instructions.** Convey these verbatim to every dispatch prompt. If the instructions conflict with the plan, surface the conflict to the user and wait for a resolution — never silently pick one side.

## Plan Consumption Contract

The orchestrator reads two conventions from the plan; both are owned and documented by this skill.

1. **Phase independence.** A phase declares independence with a `**Parallel group:** <name> | none` line in its Overview section. Phases sharing a group name are mutually independent and dispatch in parallel. `none`, or an absent line, means the phase runs sequentially after all prior phases. No declarations anywhere in the plan means a fully sequential run with no worktrees. The orchestrator NEVER infers, overrides, or second-guesses the plan's declarations (FR-005) — the declarations are authoritative, even when phase file sets look independent and the plan says nothing.
2. **Final verification.** Final test and audit commands come from the plan's `## Final Verification` section — one exact command per line, run verbatim against the integrated result (FR-012). If the section is absent, report after integration that the plan specifies no final commands and stop. NEVER substitute repo-discovered commands; a guessed command was never human-approved.

## Delegation Safety

Every phase runs in a fresh `general` subagent executing the **executing-plans** skill (FR-002). The orchestrator NEVER implements a phase inline — not for a two-line change, not under time pressure, not "just this once". executing-plans spawns no sub-agents of its own, so delegation is safe and no inline fallback exists.

Dispatch prompts MUST:

1. Name the executing-plans skill's absolute file path and instruct the subagent to read it in full (subagents do not auto-load skills).
2. Scope the subagent to exactly that one phase — nothing before it, nothing after it.
3. Supply the three executing-plans inputs: the plan path, the phase number, and the report path `PLANS/<plan-base>-phase-<N>-report.md`, where `<plan-base>` is the plan filename minus the `-plan.md` suffix. A dispatcher-provided report path puts the executor in subagent mode, making the plan file read-only for that executor.
4. Instruct the executor to commit the phase's work before finishing (FR-008) — commit is dispatcher-controlled in executing-plans, so the instruction must be explicit.
5. Name the working directory: for parallel-group phases, the phase's worktree path; for sequential phases, the main checkout.
6. Carry only the plan reference, the phase assignment, and these integration instructions — never accumulated session history, never other phases' detail (FR-003).
7. Include the user's optional instructions verbatim.
8. Require the final message to follow executing-plans' five-item report contract (status, commits, verification summary, concerns, report path).
9. Forbid the subagent from asking the user questions — questions return to the orchestrator, which mediates all user interaction.

## Resume Detection

Run before dispatching anything (FR-011). For each phase in plan order, check ALL of:

- The report file `PLANS/<plan-base>-phase-<N>-report.md` exists.
- Its frontmatter `status` is `DONE` or `DONE_WITH_CONCERNS`.
- Its frontmatter `git_commit_end` is a full commit hash.
- `git merge-base --is-ancestor <hash> HEAD` exits 0.

A phase passing all four checks is complete and is NEVER re-dispatched. The first phase failing any check is the resume point — the schedule starts there. A commit lost to a reset or stranded on an unmerged worktree branch fails the ancestor check, and the phase is re-dispatched; this is safe because phase file sets are disjoint. If no phase fails the check, proceed directly to final verification (Workflow step 5) rather than re-dispatching any phase.

## Workflow

1. **Validate input.** The plan exists, is readable, and its frontmatter says `status: approved`. Record the optional user instructions. Surface any instruction/plan conflict to the user before anything else.
2. **Read the plan and compute the schedule.** Extract the phase list, each phase's `**Parallel group:**` declaration, and the `## Final Verification` commands. Maximal runs of phases sharing a group name become parallel groups; every other phase is a sequential step in plan order (FR-005, FR-007).
3. **Run Resume Detection.** The schedule starts at the resume point; completed phases are skipped, never re-dispatched.
4. **Execute each schedule step, in order:**
   - **Sequential phase:** dispatch one executing-plans subagent per Delegation Safety, working in the main checkout.
   - **Parallel group:** for each phase in the group, follow the **isolating-worktrees** procedure (detect → create → set up → verify) with branch and directory named `<plan-base>-phase-<N>`. A worktree-creation failure stops the run with a report — NEVER fall back to unisolated parallel work. Then dispatch all of the group's subagents in parallel in one message, each pointed at its own worktree (FR-006). After all of them return, merge each branch back in ascending phase order with `git merge --no-ff <branch>` from the main checkout. A merge conflict stops the run; report the conflicting branch and phase and let the user resolve or direct (FR-009). Worktrees and branches are left in place — cleanup is a non-goal.
   - **After every subagent returns:** verify the phase's report file exists, its status is `DONE` or `DONE_WITH_CONCERNS`, and at least one commit exists for the phase. Any other status (`BLOCKED`, `NEEDS_CONTEXT`), a missing report, failed phase verification, or no commit: STOP the entire run immediately, report the failing phase and the stated reason, and dispatch nothing further (FR-010). Committed state is left intact for resume. A `NEEDS_CONTEXT` return is a phase failure — surface the subagent's stated need to the user.
5. **Final verification.** After all phases are implemented and integrated, run every command from the plan's `## Final Verification` section exactly as written, against the integrated result (FR-012). Any failure: report the failures and stop — NEVER attempt fixes.
6. **Report and stop.** Conclude by reporting phase outcomes, commit identifiers, and verification results; then stop (FR-013).

## Context Discipline

The orchestrator retains per phase ONLY: the phase outcome (status), commit identifiers, and the report artifact path (FR-004). It NEVER reads report file contents or phase implementation detail into its own context — that detail lives in the subagents and the report files. The final report to the user is assembled from retained outcomes, commit identifiers, and report paths — nothing else.

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "I'll skim the phase report to give the user a good summary" | The report path IS the summary pointer. Skimming loads transient detail into orchestrator context — the exact problem this skill exists to solve (FR-004). |
| "This phase is tiny — I'll just implement it inline" | Phase size doesn't change who owns implementation. Dispatch the subagent (FR-002). |
| "Phase 3 doesn't depend on phase 2's files, so I'll keep going after the failure" | File overlap isn't the failure criterion — the failed phase is. Stop and report (FR-010). |
| "Re-running the committed phases is safer than trusting the reports" | The report-plus-ancestry check is the resume contract. Re-dispatching completed phases wastes work and can conflict with already-merged state (FR-011). |
| "The tests pass; I'll quickly remove the worktrees before reporting" | Cleanup is a non-goal in every circumstance. Report and stop (FR-014). |

### Red Flags - STOP

- "I'll skim the phase report to give the user a good summary"
- "This phase is tiny — I'll just implement it inline"
- "Phase 3 doesn't depend on phase 2's files, so I'll keep going after the failure"
- "Re-running the committed phases is safer than trusting the reports"
- "The tests pass; I'll quickly remove the worktrees before reporting"
- "These phases look independent even though the plan doesn't say so — I'll parallelize them"
- "The plan has no Final Verification section; I'll run the repo's test command instead"
- "The user would obviously want a PR opened for this"

## Boundary

This skill ends once the plan's final verification passes and the run is reported. It NEVER performs self-review of the implemented work, cleanup of worktrees/branches/scratch files, plan-file edits (status flips, checkbox updates, completion notes), verification beyond the plan's specified commands, or pull-request creation — under any circumstances, including when the user is absent (FR-014). Review, cleanup, plan completion, and publishing belong to the user and downstream skills.
