---
artifact: prd
date: 2026-07-26
git_commit: 9899a8cf1d2f0c8480be27c8f1b42cd4e7207b77
branch: master
request: "write a PRD for a new orchestrator skill for executing a plan file. the skill should drive execution of the executing-plans skill using subagents to keep the orchestrator context clean and because each job's context is already provided and scoped. parallel subagents should be used when multiple phases can be applied independently without causing conflicts, by using git worktrees with the isolationg-worktrees skill. each phase should produce a git commit to checkpoint work. after all phases are implemented, run full test and audits. this skill should execute the plan, but intentionally stops after the tests are passing and does not proceed to self-review, cleaning up, completing the plan file, doing final verification, or creating a pull request."
status: approved
---

# plan-to-execution Skill PRD

## 1. Problem & Context

This repository's pipeline currently ends at an approved plan in `PLANS/`. Executing that plan is done by invoking the executing-plans skill inline, one phase at a time, in the user's main conversation. That fills the orchestrating context window with per-phase implementation detail that is only needed transiently, and it serializes phases even when the plan declares them independent — wasting wall-clock time on plans whose phases own disjoint file sets.

The plan-to-execution skill orchestrates execution of an approved plan: it dispatches one subagent per phase running the executing-plans skill, runs independent phases in parallel inside isolated git worktrees, checkpoints each phase as a git commit, and finishes by running the plan's full test and audit commands — then deliberately stops, leaving review, cleanup, and PR creation to the user and downstream skills.

## 2. Goals & Non-Goals

- **Goals:**
  - Take an approved plan file to fully implemented, tested code through a single skill invocation.
  - Keep the orchestrator's context clean: per-phase implementation detail lives in subagents, since each phase's context is already provided and scoped by the plan.
  - Exploit plan-declared phase independence by running independent phases concurrently in isolated git worktrees.
  - Checkpoint every phase as a git commit so progress is durable and resumable.
  - Verify the whole result with the plan's specified full test and audit commands before finishing.
  - Support resuming an interrupted run from the last completed phase commit.
- **Non-goals:**
  - Self-review of the implemented work (code review, re-reading for quality).
  - Cleanup of any kind (worktree removal, branch tidying, scratch-file deletion).
  - Completing or updating the plan file (status flips, checkmarks, completion notes).
  - Final verification beyond the plan's specified test and audit commands.
  - Creating a pull request or otherwise publishing the work.
  - Writing or revising the plan itself; the plan is an input.
  - Modifying the executing-plans or worktree-isolation skills' behavior.
  - Deciding phase independence at runtime; the plan declares it.

## 3. User Stories & Acceptance Scenarios

### P1: Full plan execution via per-phase subagents
- **Independent test:** Invoke the skill with an approved multi-phase plan; verify every phase is implemented and the plan's tests pass, with the orchestrator never reading phase implementation detail.
- **Scenario:** Given an approved plan with declared phases, When the user invokes the skill with that plan, Then each phase is executed by a fresh subagent running the executing-plans skill, each completed phase produces a git commit, and the skill reports phase outcomes and commit identifiers without holding phase content in its own context.

### P2: Parallel execution of independent phases
- **Independent test:** Invoke with a plan declaring two or more independent phases; verify they run concurrently in separate worktrees and their results are integrated.
- **Scenario:** Given a plan declares phases A and B as independent (disjoint file sets), When execution reaches them, Then they are dispatched as parallel subagents in separate git worktrees, and their commits are merged back in plan order after both complete.

### P3: Sequential execution of dependent phases
- **Independent test:** Invoke with a plan where phase B depends on phase A; verify B starts only after A's commit exists.
- **Scenario:** Given a plan where phase B is not declared independent of phase A, When execution runs, Then phase B's subagent is dispatched only after phase A has completed and committed.

### P4: Per-phase checkpoint commits
- **Independent test:** After a run, inspect the commit history; verify one or more commits per phase attributable to that phase.
- **Scenario:** Given a phase completes successfully, When the subagent finishes, Then the work for that phase is captured in a git commit before the next dependent phase begins.

### P5: Final full test and audit run
- **Independent test:** After all phases complete, verify the plan's specified test and audit commands are run once against the integrated result and their outcomes reported.
- **Scenario:** Given all phases are implemented and integrated, When the skill reaches its final step, Then it runs the full test and audit commands specified in the plan and reports pass/fail, stopping after they pass.

### P6: Stop-and-report on phase failure
- **Independent test:** Force a phase subagent to fail or report BLOCKED; verify the run halts and reports the failing phase.
- **Scenario:** Given a phase subagent fails or cannot complete its phase, When the failure is returned, Then the skill stops the entire run, reports which phase failed and why, and leaves committed state intact for resume.

### P7: Resume an interrupted run
- **Independent test:** Interrupt a run after some phases commit, re-invoke the skill, and verify it continues from the first incomplete phase without redoing completed ones.
- **Scenario:** Given a previous run committed phases 1–2 before stopping, When the skill is re-invoked on the same plan, Then it detects the completed phase commits and resumes at phase 3.

## 4. Requirements

- **FR-001:** The skill accepts as input a plan file; the plan is the sole source of phase definitions, phase-scoped context, independence declarations, and verification commands.
- **FR-002:** Each phase is executed by dispatching a fresh subagent that runs the executing-plans skill scoped to that single phase; the orchestrator never implements phases inline.
- **FR-003:** Subagent dispatch prompts are self-contained: each carries only the plan reference, the phase assignment, and integration instructions — never accumulated session history or other phases' detail.
- **FR-004:** The orchestrator's retained context per phase is limited to phase outcome, commit identifiers, and report artifact paths.
- **FR-005:** Phase independence is taken from the plan's declarations; the orchestrator does not infer, override, or second-guess them.
- **FR-006:** Phases declared independent are dispatched as parallel subagents, each in its own isolated git worktree created via the worktree-isolation skill.
- **FR-007:** Phases not declared independent run sequentially, each starting only after its predecessors have committed.
- **FR-008:** Every completed phase produces at least one git commit checkpointing that phase's work before any dependent phase begins.
- **FR-009:** After all parallel subagents for a group of independent phases complete, their commits are merged back in plan order; a merge conflict stops the run and is reported to the user.
- **FR-010:** If any phase subagent fails, is blocked, or its phase tests do not pass, the skill stops the entire run immediately, reports the failing phase and reason, and does not dispatch further phases.
- **FR-011:** On invocation, the skill detects already-committed phases from prior runs and resumes from the first incomplete phase rather than re-executing completed work.
- **FR-012:** After all phases are implemented and integrated, the skill runs the full test and audit commands specified in the plan against the integrated result.
- **FR-013:** The skill concludes once the plan's tests and audits pass, by reporting phase outcomes, commit identifiers, and verification results; it then stops.
- **FR-014:** The skill does not perform self-review, cleanup, plan-file completion, additional final verification, or pull-request creation under any circumstances, including when the user is absent.

## 5. Scope

- **In scope:** orchestration of plan execution; per-phase subagent dispatch driving the executing-plans skill; parallel dispatch of plan-declared independent phases in isolated worktrees; merge-back in plan order; per-phase commit checkpoints; stop-and-report failure handling; resume from committed phases; final plan-specified test and audit run; end-of-run reporting.
- **Out of scope:** code review or self-review; cleanup of worktrees, branches, or scratch files; editing or completing the plan file; verification beyond plan-specified commands; pull requests; plan authoring or revision; changes to executing-plans or the worktree-isolation skill; runtime inference of phase independence.

## 6. Assumptions & Constraints

- Phase independence is declared in the plan and trusted as authoritative (user-confirmed).
- Parallel worktree results are merged back by the orchestrator in plan order (user-confirmed).
- A phase failure stops the entire run rather than skipping or retrying (user-confirmed).
- Interrupted runs resume from the last completed phase commit (user-confirmed).
- Final verification runs the commands specified in the plan, not repo-discovered ones (user-confirmed).
- The skill's name is plan-to-execution (user-confirmed).
- The existing executing-plans skill already scopes each subagent's job to a single phase and produces a per-phase report artifact; the orchestrator consumes but does not duplicate that behavior.

## 7. Edge Cases

- **Plan missing, unreadable, or not approved:** the skill stops and tells the user an approved plan is required.
- **Plan declares no independent phases:** the entire run is sequential; no worktrees are created.
- **All phases declared mutually independent:** all run in parallel; merge-back still occurs in plan order.
- **Merge conflict when integrating parallel worktrees:** the run stops and the conflict is reported; the user resolves or directs.
- **Phase subagent reports it cannot complete without more context:** treated as a phase failure under FR-010; the skill stops and surfaces the subagent's stated need to the user.
- **Re-invoked with no incomplete phases:** the skill proceeds directly to the final test and audit run rather than re-dispatching phases.
- **Final tests or audits fail:** the skill reports the failures and stops; it does not attempt fixes itself.
- **A phase produces no commit:** treated as an incomplete phase; dependent phases are not dispatched and the run stops with a report.

## 8. Success Criteria

- **SC-001:** A user can go from an approved plan to fully implemented, plan-tested code through one skill invocation without manually invoking executing-plans or creating worktrees.
- **SC-002:** After a full run, the orchestrator's context contains no phase implementation detail — only phase outcomes, commit identifiers, and report paths.
- **SC-003:** Every phase of the plan is represented by at least one commit in the resulting history.
- **SC-004:** Independent phases of a plan complete in less wall-clock time than the same phases run sequentially, with no cross-phase file conflicts.
- **SC-005:** No phase runs after a failed phase in the same run; every failure produces a report naming the failing phase.
- **SC-006:** Re-invoking the skill after an interruption completes the plan without re-executing already-committed phases.
- **SC-007:** A completed run ends with a passing result for every test and audit command the plan specifies, and the skill performs no review, cleanup, plan-file edit, or pull-request action afterward.

## 9. Open Questions

None.
