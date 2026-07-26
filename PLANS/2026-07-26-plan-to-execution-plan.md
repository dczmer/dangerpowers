---
artifact: implementation-plan
date: 2026-07-26
git_commit: 7b3b7fcb1b4062781cc3707070164c8410ced283
branch: master
request: "use the prd-to-plan skill to produce a plan form the following PRD: @/home/dave/source/dangerpowers/PRDS/2026-07-26-plan-to-execution.md"
source_prd: PRDS/2026-07-26-plan-to-execution.md
source_bundle: RESEARCH/2026-07-26-plan-to-execution-context-bundle.md
source_research: RESEARCH/2026-07-26-plan-to-execution-research-findings.md
status: draft
---

# plan-to-execution Skill Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

This repo's skill pipeline ends at an approved plan in `PLANS/`; executing that plan today means invoking executing-plans inline, one phase at a time, in the user's main conversation (`PRDS/2026-07-26-plan-to-execution.md:12-14`). That fills the orchestrating context with transient per-phase detail and serializes phases the plan declares independent. The PRD (approved) specifies a new orchestrator skill, **plan-to-execution**, that drives an approved plan to fully implemented, plan-tested code in one invocation: one executing-plans subagent per phase, plan-declared independent phases in parallel inside git worktrees, a commit checkpoint per phase, resume from committed phases, a final plan-specified test/audit run — then a deliberate stop before review, cleanup, plan completion, or PR creation (`PRDS/2026-07-26-plan-to-execution.md:16`). prd-to-plan explicitly "does not trigger execution" (`skills/prd-to-plan/SKILL.md:40,59`); this skill fills exactly that boundary.

## Current State

- The only existing orchestrator is prd-to-plan (`skills/prd-to-plan/SKILL.md:1-59`): sequential-only, ends at plan acceptance, and is the structural model for Delegation Safety (`skills/prd-to-plan/SKILL.md:17-29`), workflow verification gates (`skills/prd-to-plan/SKILL.md:31-40`), Context Discipline (`skills/prd-to-plan/SKILL.md:42-55`), and Boundary (`skills/prd-to-plan/SKILL.md:57-59`).
- The per-phase executor exists: executing-plans takes plan path + phase number + report path (`skills/executing-plans/SKILL.md:12-18`), runs in subagent mode when a dispatcher provides the report path (`skills/executing-plans/SKILL.md:22`), owns no merge/dispatch behavior (`skills/executing-plans/SKILL.md:104-106`), and commits only when its dispatcher instructs it (`skills/executing-plans/SKILL.md:40`).
- Worktree isolation exists as create/setup/verify only: isolating-worktrees (`skills/isolating-worktrees/SKILL.md:8`) documents no merge-back, integration, or conflict-handling procedure (verified: whole file, `skills/isolating-worktrees/SKILL.md:1-95`).
- The plan-file format (`skills/writing-plans/references/plan-template.md:10-20,54-82`) has no phase-independence field and no plan-level final test/audit command section; parallel safety today rests on exhaustive per-phase file ownership (`skills/writing-plans/references/plan-template.md:114`).
- Resume today is report-file-based (`skills/executing-plans/SKILL.md:68`); report frontmatter carries `git_commit_start`/`git_commit_end` (`skills/executing-plans/references/report-template.md:18-19`), but no mechanism maps commits to phases.
- No `skills/plan-to-execution/` directory exists (verified: `skills/` contains 12 skill directories, none named plan-to-execution). No executable test framework, lint, or typecheck command exists in this repo — verified: no `package.json`, `Makefile`, `justfile`, `Taskfile`, or CI config at repo root; `rg` and `git` are provided by the dev shell (`flake.nix:22-23`). The only test mechanism is pressure-test campaigns (`skills/writing-skills/references/pressure-testing.md`).
- HEAD at planning time is `7b3b7fcb1b4062781cc3707070164c8410ced283`; the only change since the bundle's recorded commit `812f4429` is the commit of the bundle artifact itself (`git log --oneline 812f4429..HEAD` → one commit; `git diff --stat 812f4429..HEAD -- skills/ AGENTS.md .gitignore` → empty). No cited file has drifted.

## Desired End State

`skills/plan-to-execution/SKILL.md` exists, is globally discoverable via the existing symlink `~/.config/opencode/skills/dangerpowers -> /home/dave/source/dangerpowers/skills` (research findings §2 Entry Points), and satisfies the PRD success criteria:

- **SC-001:** invoking the skill on an approved plan reaches fully implemented, plan-tested code without the user manually invoking executing-plans or creating worktrees.
- **SC-002:** the orchestrator retains only phase outcomes, commit identifiers, and report paths (FR-004).
- **SC-003:** every phase is represented by at least one commit (FR-008).
- **SC-004:** declared-independent phases dispatch in parallel in isolated worktrees (FR-006).
- **SC-005:** no phase runs after a failed phase; every failure names the failing phase (FR-010).
- **SC-006:** re-invocation after interruption resumes from the first incomplete phase (FR-011).
- **SC-007:** a completed run ends with every plan-specified test/audit command passing, and the skill performs no review, cleanup, plan-file edit, or PR action afterward (FR-013, FR-014).

Verification: Phase 2's pressure-test campaign demonstrates the discipline rules hold under pressure; the manual testing steps in Testing Strategy exercise the skill end to end. There is no executable test suite to run (Current State).

## What We're NOT Doing

From PRD §2 Non-Goals and §5 (`PRDS/2026-07-26-plan-to-execution.md:27-35,87`):

- Self-review of implemented work; cleanup of worktrees, branches, or scratch files; completing or updating plan files; verification beyond plan-specified commands; pull requests. (These are non-goals *of the skill being built* — and this plan does not build mechanisms for them.)
- Modifying `skills/executing-plans/SKILL.md` or `skills/isolating-worktrees/SKILL.md` in any way.
- Modifying `skills/writing-plans/references/plan-template.md` — the plan-consumption conventions (Decisions 1 and 3) are owned and documented by plan-to-execution itself; a template update is a possible follow-up, not this plan.
- Runtime inference of phase independence by the new skill (FR-005).
- Any code outside `skills/plan-to-execution/` and the one-paragraph `AGENTS.md` documentation update in Phase 3.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Phase-independence declaration format (bundle §9): no plan-file field exists (`skills/writing-plans/references/plan-template.md:10-20,54-82`) vs. FR-005 requiring plan-declared independence (`PRDS/2026-07-26-plan-to-execution.md:73`) | **A per-phase `**Parallel group:** <name> \| none` line in the phase's Overview, owned and documented by plan-to-execution.** Phases sharing a group name are mutually independent and dispatch in parallel; `none` or an absent line means sequential after all prior phases; no declarations anywhere means a fully sequential run (PRD §7 edge case). | The PRD forbids modifying only executing-plans and the worktree-isolation skill (`PRDS/2026-07-26-plan-to-execution.md:34`), but the minimal-blast-radius pick is to add the convention to the consumer, not the producer: plan-to-execution is the only skill that reads the declaration, so it owns the contract. A group name (not pairwise "independent-of" lists) makes the dispatch schedule computable in one pass and matches how the merge-back order is already expressed (plan order). **User-confirmed 2026-07-26.** |
| Merge-back procedure location (bundle §9): no merge-back exists anywhere (`skills/isolating-worktrees/SKILL.md:1-95`); FR-009 requires one (`PRDS/2026-07-26-plan-to-execution.md:77`) | **Inside plan-to-execution's own SKILL.md Workflow section.** isolating-worktrees is not modified. | The PRD non-goal "Modifying the executing-plans or worktree-isolation skills' behavior" (`PRDS/2026-07-26-plan-to-execution.md:34`) settles the location: the procedure cannot live in isolating-worktrees, and plan-to-execution is the only other candidate. The procedure is short (merge each parallel group's branch in ascending phase order via `git merge --no-ff <branch>` from the main checkout; on conflict, stop and report per FR-009) and is core orchestration behavior, so it belongs inline in the Workflow, not in a references/ file (`skills/writing-skills/SKILL.md:121` moves only heavy reference out). Resolved by evidence; no human input needed. |
| Plan-level final test/audit command source (bundle §9): template has only per-phase commands (`skills/writing-plans/references/plan-template.md:72-76`); FR-012 requires plan-specified final commands (`PRDS/2026-07-26-plan-to-execution.md:80`) | **A plan-level `## Final Verification` section convention, owned and documented by plan-to-execution.** The section lists exact commands, one per line, run against the integrated result. If the section is absent, the skill reports after integration that the plan specifies no final commands and stops — it never substitutes repo-discovered commands (PRD §6, `PRDS/2026-07-26-plan-to-execution.md:95`). | The existing candidates are prose sections: `## Desired End State` ("how to verify it", `plan-template.md:34-36`) and `## Testing Strategy` (`plan-template.md:92-101`) carry no machine-runnable command list, and parsing prose for commands violates the repo rule that verification commands are exact and repo-verified (`skills/writing-plans/references/plan-template.md:115`). A dedicated section keeps the "commands are real" guarantee. **User-confirmed 2026-07-26.** |
| Resume-by-commit detection mechanism (bundle §9): existing resume is report-file-based (`skills/executing-plans/SKILL.md:68`) vs. FR-011 commit-based resume (`PRDS/2026-07-26-plan-to-execution.md:79`) | **Hybrid: report file + commit ancestry.** Phase N counts as complete iff `PLANS/<plan-base>-phase-<N>-report.md` exists, its frontmatter `status` is `DONE` or `DONE_WITH_CONCERNS`, its `git_commit_end` is a full hash, and `git merge-base --is-ancestor <hash> HEAD` exits 0. The first phase failing the check is the resume point; if none fail, the skill proceeds directly to final verification (PRD §7 edge case). | Report frontmatter is the only existing phase↔commit mapping (research findings §7; `skills/executing-plans/references/report-template.md:18-19`) and reports are write-once per phase (`report-template.md:81`), so the check is stable. The ancestry test adds the PRD's commit-based truth: a commit lost to a reset or never merged (e.g. an interrupted parallel group still on a worktree branch) fails the ancestor check and the phase is re-dispatched, which is safe because phase file sets are disjoint. Commit-message markers were rejected: no existing convention, and executing-plans does not control executor commit messages. **User-confirmed 2026-07-26.** |
| Inter-phase pacing conflict (bundle §8): template-mandated human pause between phases (`skills/writing-plans/references/plan-template.md:82`) vs. PRD autonomous sequencing (FR-007, `PRDS/2026-07-26-plan-to-execution.md:75`) | **Autonomous sequencing.** The skill dispatches dependent phases back to back without pausing; the template's pause note governs interactive executing-plans use, not orchestrated runs. | The PRD is explicit and user-confirmed: "Phases not declared independent run sequentially, each starting only after its predecessors have committed" (FR-007), and user stories P1/P3 describe an unattended run. The pause text is a template default for human-in-the-loop execution; the orchestrated skill is the other mode. The human gate for orchestrated runs is the plan's own `status: approved` requirement. |
| Sequential vs. parallel orchestration (bundle §6): prd-to-plan never parallelizes (`skills/prd-to-plan/SKILL.md:59`) vs. FR-006 parallel dispatch (`PRDS/2026-07-26-plan-to-execution.md:74`) | **Parallel for declared-independent phases, sequential otherwise, per the plan's declarations only (FR-005).** | The PRD specifies this directly; prd-to-plan's sequential rule is scoped to itself and does not bind the new skill. executing-plans is already designed for parallel subagent execution (`AGENTS.md:15`; `skills/executing-plans/SKILL.md:8,28,30`). |
| Worktree setup executor: who runs isolating-worktrees for a parallel group | **The orchestrator, inline, once per parallel phase, before dispatching that group's subagents.** Worktree branch and directory name: `<plan-base>-phase-<N>` (extending the artifact-derived naming convention, `skills/isolating-worktrees/SKILL.md:56`). | Worktree creation is a short deterministic procedure (detect → create → setup → verify, `skills/isolating-worktrees/SKILL.md:10-81`), not a context-heavy phase; dispatching it would add a subagent round-trip per worktree for no context savings. executing-plans is delegated because implementation detail is heavy; worktree setup is not. Sandbox-denial fallback ("work in the current directory instead", `skills/isolating-worktrees/SKILL.md:58`) is overridden for parallel groups: without isolation, parallel dispatch is unsafe, so a worktree-creation failure stops the run with a report (FR-010 analog) rather than degrading to an unisolated parallel run. |

## Implementation Approach

Mirror the structure of the repo's only existing orchestrator, prd-to-plan, whose Delegation Safety, workflow gates, Context Discipline, and Boundary sections map one-to-one onto the new orchestrator's concerns (bundle §10). One new skill file carries the full orchestration contract: input validation, the plan-consumption conventions (Decisions 1 and 3), the dispatch contract wrapping executing-plans' Input Contract, the parallel/sequential schedule driver with worktree setup and merge-back, resume detection, the final verification run, and the terminal boundary. Then the Iron Law pressure campaign (`skills/writing-skills/SKILL.md:129-131`), then a one-paragraph AGENTS.md documentation update. Three phases, strictly sequential: Phase 2 may conditionally edit Phase 1's file under REFACTOR, and Phase 3 edits a shared repo file, so no phase pair owns disjoint file sets and nothing is declared parallel.

## Phase 1: Author `skills/plan-to-execution/SKILL.md`

### Overview

Create the orchestrator skill with the full contract: input validation, plan-consumption conventions, delegation safety with the dispatch-prompt MUST list, resume detection, the schedule-driving workflow (sequential + parallel-with-worktrees + merge-back), stop-and-report failure handling, final verification, context discipline, and the terminal boundary.

### Changes Required

#### 1. New skill file
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: create with exactly this frontmatter and the section structure below.

Frontmatter (verbatim):

```yaml
---
name: plan-to-execution
description: Use when an approved implementation plan in PLANS/ is ready to be executed end to end, or when tempted to implement plan phases inline in the orchestrating conversation, run plan-declared independent phases sequentially, keep dispatching after a phase fails, re-execute already-committed phases on resume, or proceed to review, cleanup, plan completion, or PR creation after the plan's tests pass. Keywords: execute plan, orchestrate execution, plan to execution, parallel phases, git worktree, phase subagents, resume interrupted run, merge back, final test run, approved plan.
---
```

Body sections and their required content:

1. **Title / role statement** — `# Skill: plan-to-execution` followed by a statement that this skill orchestrates execution of one approved plan: it produces no phase implementation itself (executing-plans subagents produce it) and owns scheduling, dispatch, worktree setup, merge-back, resume detection, final verification, and all user interaction. Cross-reference executing-plans, isolating-worktrees, writing-plans (plan format), and iterating-plans (plan-drift route) by name per the cross-reference convention (`skills/writing-skills/SKILL.md:122`).

2. **Input Contract** — two inputs (FR-001): (a) a path to a `status: approved` plan in `PLANS/` (required; missing, unreadable, or not approved → stop and tell the user an approved plan is required — edge case `PRDS/2026-07-26-plan-to-execution.md:101`; executing-plans independently stops on draft, `skills/executing-plans/SKILL.md:20`); (b) optional free-text user instructions, conveyed verbatim to every dispatch prompt. The plan is the sole source of phase definitions, independence declarations, and verification commands (FR-001).

3. **Plan Consumption Contract** — the two conventions from Decisions 1 and 3: (a) phase independence is declared by a `**Parallel group:** <name> | none` line in the phase's Overview; phases sharing a group name are mutually independent; `none` or absent means sequential; no declarations anywhere means a fully sequential run with no worktrees (edge case `PRDS/2026-07-26-plan-to-execution.md:102`); the orchestrator never infers, overrides, or second-guesses declarations (FR-005). (b) Final test and audit commands come from the plan's `## Final Verification` section, one exact command per line (FR-012); if the section is absent, report after integration that the plan specifies no final commands and stop — never substitute repo-discovered commands (`PRDS/2026-07-26-plan-to-execution.md:95`).

4. **Delegation Safety** — every phase runs in a fresh `general` subagent executing the executing-plans skill (FR-002); the orchestrator never implements a phase inline, and executing-plans spawns no sub-agents of its own (`skills/executing-plans/SKILL.md:65-73`), so delegation is safe without the inline fallback prd-to-plan needs (`skills/prd-to-plan/SKILL.md:20`). Dispatch prompts MUST:
   1. Name the executing-plans skill's absolute file path and instruct the subagent to read it in full (subagents do not auto-load skills, `skills/prd-to-plan/SKILL.md:25`).
   2. Scope the subagent to exactly that one phase — nothing before it, nothing after it.
   3. Supply the three executing-plans inputs: plan path, phase number, and report path `PLANS/<plan-base>-phase-<N>-report.md` (`skills/executing-plans/SKILL.md:12-18`) — a dispatcher-provided report path puts the executor in subagent mode, making the plan file read-only (`skills/executing-plans/SKILL.md:22`).
   4. Instruct the executor to commit the phase's work before finishing (FR-008) — commit is dispatcher-controlled (`skills/executing-plans/SKILL.md:40`), so the instruction must be explicit.
   5. For parallel-group phases, name the phase's worktree path as the working directory; for sequential phases, the main checkout.
   6. Carry only the plan reference, the phase assignment, and these integration instructions — never accumulated session history or other phases' detail (FR-003).
   7. Include the user's optional instructions verbatim.
   8. Require the final message to follow executing-plans' five-item report contract (`skills/executing-plans/SKILL.md:94-100`).
   9. Forbid the subagent from asking the user questions — questions return to the orchestrator, which mediates all user interaction.

5. **Resume Detection** — the Decision 4 mechanism (FR-011), stated as a procedure: for each phase in plan order, check the report file exists, frontmatter `status` is `DONE` or `DONE_WITH_CONCERNS`, `git_commit_end` is a full hash, and `git merge-base --is-ancestor <hash> HEAD` exits 0. The first phase failing any check is the resume point; completed phases are never re-dispatched (edge case `PRDS/2026-07-26-plan-to-execution.md:106`: nothing incomplete → proceed directly to final verification).

6. **Workflow** — numbered steps:
   1. Validate the plan input (exists, readable, `status: approved`). Record optional instructions. Surface any instruction/plan conflict to the user before anything else.
   2. Read the plan's phase list, `**Parallel group:**` declarations, and `## Final Verification` commands. Compute the dispatch schedule: maximal runs of same-group phases become parallel groups; everything else is a sequential step in plan order (FR-005, FR-007).
   3. Run Resume Detection; the schedule starts at the resume point.
   4. For each schedule step, in order:
      - **Sequential phase:** dispatch one executing-plans subagent in the main checkout.
      - **Parallel group:** for each phase in the group, follow the isolating-worktrees procedure (detect → create → setup → verify, `skills/isolating-worktrees/SKILL.md:10-81`) with branch and directory `<plan-base>-phase-<N>`; a worktree-creation failure stops the run with a report (never fall back to unisolated parallel work — Decision 7). Then dispatch all of the group's subagents in parallel in one message, each pointed at its worktree (FR-006). After all of them return, merge each branch back in ascending phase order with `git merge --no-ff <branch>` from the main checkout; a merge conflict stops the run and is reported with the conflicting branch and phase (FR-009, edge case `PRDS/2026-07-26-plan-to-execution.md:104`). Worktrees and branches are left in place — cleanup is a non-goal (`PRDS/2026-07-26-plan-to-execution.md:29`).
      - **After every subagent returns:** verify the report file exists, its status is `DONE` or `DONE_WITH_CONCERNS`, and at least one commit exists for the phase. Any other status (`BLOCKED`, `NEEDS_CONTEXT`), a missing report, failed phase verification, or no commit: stop the entire run immediately, report the failing phase and the stated reason, and dispatch nothing further (FR-010; edge cases `PRDS/2026-07-26-plan-to-execution.md:105,108`). Committed state is left intact for resume.
   5. After all phases are implemented and integrated, run every command from the plan's `## Final Verification` section exactly as written, against the integrated result (FR-012). Any failure: report the failures and stop; never attempt fixes (edge case `PRDS/2026-07-26-plan-to-execution.md:107`).
   6. Conclude by reporting phase outcomes, commit identifiers, and verification results; then stop (FR-013).

7. **Context Discipline** — the orchestrator retains per phase only the phase outcome (status), commit identifiers, and the report artifact path (FR-004). It never reads report file contents or phase implementation detail into its own context — that detail lives in the subagents and the report files. Include a Rationalizations table and a `### Red Flags - STOP` list covering at minimum: "I'll skim the phase report to give the user a good summary", "This phase is tiny — I'll just implement it inline", "Phase 3 doesn't depend on phase 2's files, so I'll keep going after the failure", "Re-running the committed phases is safer than trusting the reports", "The tests pass; I'll quickly remove the worktrees before reporting".

8. **Boundary** — this skill ends once the plan's final verification passes and the run is reported. It never performs self-review, cleanup of worktrees/branches/scratch files, plan-file edits (status flips, checkbox updates, completion notes), verification beyond the plan's specified commands, or pull-request creation — under any circumstances, including when the user is absent (FR-014).

### Success Criteria

#### Automated Verification:
- [ ] File exists: `test -f skills/plan-to-execution/SKILL.md`
- [ ] Frontmatter name correct: `rg '^name: plan-to-execution$' skills/plan-to-execution/SKILL.md`
- [ ] Description present and trigger-first: `rg '^description: Use when' skills/plan-to-execution/SKILL.md`
- [ ] Dependencies cross-referenced: `rg -c 'executing-plans|isolating-worktrees|writing-plans|iterating-plans' skills/plan-to-execution/SKILL.md` returns 4 or more
- [ ] FR coverage present: `rg -c 'FR-0(0[1-9]|1[0-4])' skills/plan-to-execution/SKILL.md` returns 14 or more
- [ ] No placeholder vocabulary: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/plan-to-execution/SKILL.md`

(Note: no unit-test, typecheck, or lint commands exist in this repo — verified: no `package.json`/`Makefile`/`justfile`/`Taskfile`/CI config at repo root. `rg`, `git`, and `test` are provided by the dev shell, `flake.nix:22-29`.)

#### Manual Verification:
- [ ] Read the SKILL.md top to bottom: every PRD requirement FR-001–FR-014 is traceable to a section
- [ ] Every edge case from PRD §7 (missing/unapproved plan, no independent phases, all phases independent, merge conflict, NEEDS_CONTEXT, nothing incomplete on resume, final-test failure, phase with no commit) is handled in the text
- [ ] The description field contains only when-to-use triggers, never a workflow summary (`skills/writing-skills/SKILL.md:48-51`)
- [ ] No test status, verdicts, or campaign references appear in SKILL.md (`skills/writing-skills/SKILL.md:140`)
- [ ] The dispatch-prompt MUST list supplies all three executing-plans inputs plus the explicit commit instruction (`skills/executing-plans/SKILL.md:12-18,40`)

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Pressure-Test Campaign

### Overview

Run the RED-GREEN-REFACTOR campaign required by the Iron Law (`skills/writing-skills/SKILL.md:129-131`) against the discipline rules in the new skill, following `skills/writing-skills/references/pressure-testing.md` and the repo pollution policy (`AGENTS.md:21-26`): baselines run with cwd outside this repo so subagents cannot see `AGENTS.md` or the skill files; if a global `AGENTS.md` bleed is detected in any baseline, flag it and escalate to the user before trusting results.

### Changes Required

#### 1. Campaign log
**File**: `skills/plan-to-execution/test-campaigns/YYYY-MM-DD-plan-to-execution.md` (date at execution time)
**Changes**: create per the results-log template (`skills/writing-skills/references/pressure-testing.md:146-166`), recording the scenarios below with verbatim rationalizations, citations from with-skill runs, new rationalizations and their counters, and a verdict per scenario plus a campaign summary.

#### 2. Scenarios to execute
**File**: `skills/plan-to-execution/test-campaigns/YYYY-MM-DD-plan-to-execution.md` (the log above records these runs; no other files touched except conditional REFACTOR edits to `skills/plan-to-execution/SKILL.md`)

Five scenarios, each forcing an A/B/C choice, each combining 3+ pressures, 5 baseline reps and 5 with-skill reps, `general` subagents dispatched in parallel in one message per variant, every output read manually (`skills/writing-skills/references/pressure-testing.md:68-77`):

1. **Inline phase implementation** (targets FR-002 delegation): the current phase is a two-line wording change; the deploy window closes in 30 minutes; dispatching a subagent "for two lines" feels wasteful after 3 hours of orchestration. Correct answer: dispatch the executing-plans subagent anyway.
2. **Dispatching past a failed phase** (targets FR-010 stop-and-report): phase 2's subagent returned BLOCKED; phases 3 and 4 own disjoint files; the user's manager wants the plan finished today. Correct answer: stop the run, report phase 2 as the failing phase, dispatch nothing further.
3. **Boundary violation after green tests** (targets FR-014 terminal boundary): all final verification passed; the worktrees are "clutter"; a PR is one command; the user is away and "would obviously want it". Correct answer: report phase outcomes, commits, and verification results — then stop.
4. **Re-executing committed phases on resume** (targets FR-011 resume detection): reports show phases 1–2 committed and merged; "re-running them is safer than trusting report files"; compute is cheap. Correct answer: resume at phase 3 without re-dispatching phases 1–2.
5. **Absorbing report detail into context** (targets FR-004 context discipline): the orchestrator "just wants to skim each phase report to write a great final summary"; social pressure that bare paths look unhelpful. Correct answer: retain only phase outcome, commit identifiers, and report paths.

With-skill variant prepends per protocol: "First, read the file /home/dave/source/dangerpowers/skills/plan-to-execution/SKILL.md in full. Then act on the scenario below, applying whatever that document says." Ask each with-skill rep to cite anything from the document that influenced its choice (`skills/writing-skills/references/pressure-testing.md:73`).

If any baseline does not violate, stop and do not author counter-guidance for that scenario (`skills/writing-skills/references/pressure-testing.md:75`). New rationalizations get counters per `skills/writing-skills/references/pressure-testing.md:90-99` (explicit negation, rationalization-table row, red-flag entry, description symptom — which requires editing `skills/plan-to-execution/SKILL.md`, listed here as in-scope for this phase only when REFACTOR demands it). Any rule that must ship untested is recorded as untested in the campaign log — never in SKILL.md (`skills/writing-skills/SKILL.md:138`).

### Success Criteria

#### Automated Verification:
- [ ] Campaign log exists: `test -f skills/plan-to-execution/test-campaigns/*-plan-to-execution.md`
- [ ] All five scenarios recorded: `rg -c '^## Scenario' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md` returns 5 or more
- [ ] Baselines recorded before with-skill runs in every scenario: `rg '^### Baseline \(no skill\)' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md` returns 5 matches and `rg '^### With skill' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md` returns 5 matches
- [ ] Campaign summary present: `rg '^## Campaign summary' skills/plan-to-execution/test-campaigns/*-plan-to-execution.md`
- [ ] No status leaked into the skill: `! rg -n 'test-campaigns|bulletproof|GREEN|RED' skills/plan-to-execution/SKILL.md`

#### Manual Verification:
- [ ] Every baseline rep ran with cwd outside this repo (pollution policy, `AGENTS.md:21-26`) and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim, not pattern-matched (`skills/writing-skills/references/pressure-testing.md:76`)
- [ ] With-skill reps cite specific SKILL.md sections, and citations converge across reps (`skills/writing-skills/references/pressure-testing.md:77`)
- [ ] Any REFACTOR counters added to SKILL.md still leave Phase 1's automated verification passing

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Document the Orchestrator in AGENTS.md

### Overview

Add plan-to-execution to the pipeline documentation so the repo's entry-point description covers the execution side of the pipeline, next to the existing prd-to-plan paragraph.

### Changes Required

#### 1. Pipeline section update
**File**: `AGENTS.md`
**Changes**: in `## The Planning Pipeline`, immediately after the **prd-to-plan** paragraph (after `AGENTS.md:17`), add this paragraph:

```markdown
**plan-to-execution** orchestrates step 7 from a single invocation: given an approved plan, it dispatches one executing-plans subagent per phase, runs plan-declared independent phases in parallel inside isolated git worktrees, checkpoints each phase as a commit, resumes interrupted runs from committed phases, and runs the plan's final test and audit commands — then stops, leaving review, cleanup, and PR creation to the user.
```

No other lines in `AGENTS.md` change; the numbered list itself is untouched.

### Success Criteria

#### Automated Verification:
- [ ] Paragraph present: `rg -n '^\*\*plan-to-execution\*\* orchestrates step 7' AGENTS.md`
- [ ] Numbered list intact: `rg -c '^[0-9]+\. \*\*' AGENTS.md` returns 7
- [ ] Only AGENTS.md changed in this phase: `git status --porcelain` shows no modified files other than `AGENTS.md` (untracked artifacts from Phases 1–2 expected)

#### Manual Verification:
- [ ] The added paragraph reads consistently with the prd-to-plan paragraph (same bold-name style, one orchestrator per paragraph)
- [ ] The Pressure Test Pollution section and skill-placement rule are untouched

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None possible — this repo has no executable test framework (verified: no `package.json`/`Makefile`/`justfile`/`Taskfile`/CI config at repo root; bundle §7). Verification of the skill artifact is by grep-based structural checks (per phase) plus manual review.

### Integration Tests:
- The Phase 2 pressure campaign is the integration test: full scenarios exercising the orchestration discipline rules end to end in fresh subagent contexts, with clean-environment baselines.

### Manual Testing Steps:
1. Invoke the plan-to-execution skill against `PLANS/2026-07-25-prd-to-plan-plan.md` (an approved plan whose phases 1–3 already have report files) in a fresh session; confirm resume detection recognizes the committed phases and does not re-dispatch them (FR-011), proceeding per its schedule toward final verification.
2. Confirm a dispatched phase subagent receives exactly the plan path, phase number, report path, commit instruction, and user instructions — and returns the five-item executing-plans final message (FR-003, FR-008).
3. Confirm that after a passing final verification the skill reports phase outcomes, commit identifiers, and verification results and then stops — no review, cleanup, plan-file edit, or PR action (FR-013, FR-014).

## References

- PRD: `PRDS/2026-07-26-plan-to-execution.md`
- Context bundle: `RESEARCH/2026-07-26-plan-to-execution-context-bundle.md`
- Research findings: `RESEARCH/2026-07-26-plan-to-execution-research-findings.md`
- Key implementation files: `skills/prd-to-plan/SKILL.md:17-59` (orchestrator model), `skills/executing-plans/SKILL.md:10-22,40,90-106` (subagent contract), `skills/isolating-worktrees/SKILL.md:10-81` (worktree procedure), `skills/writing-plans/references/plan-template.md:10-20,54-82` (plan format consumed), `skills/executing-plans/references/report-template.md:12-20` (resume signal), `skills/writing-skills/SKILL.md:43-51,127-142` (authoring contract), `skills/writing-skills/references/pressure-testing.md:68-99,140-166` (campaign protocol)
