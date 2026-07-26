---
artifact: context-bundle
date: 2026-07-26
git_commit: 812f442904d3f556e395f8ec7ba6ea39ffd87e10
branch: master
request: "use the prd-to-plan skill to produce a plan form the following PRD: @/home/dave/source/dangerpowers/PRDS/2026-07-26-plan-to-execution.md"
source_research: RESEARCH/2026-07-26-plan-to-execution-research-findings.md
source_prd: PRDS/2026-07-26-plan-to-execution.md
status: complete
---

# Context Bundle

## 1. Goal

Create a new orchestrator skill `plan-to-execution` under `skills/plan-to-execution/` that drives execution of an approved plan file: dispatching one subagent per phase running the executing-plans skill, running plan-declared independent phases in parallel inside isolated git worktrees (via the isolating-worktrees skill), checkpointing each phase as a git commit, resuming interrupted runs from committed phases, and running the plan's full test and audit commands at the end — then deliberately stopping before review, cleanup, plan completion, or PR creation (`PRDS/2026-07-26-plan-to-execution.md:10-16`).

- **In scope:** orchestration of plan execution; per-phase subagent dispatch driving executing-plans; parallel dispatch of plan-declared independent phases in isolated worktrees; merge-back in plan order; per-phase commit checkpoints; stop-and-report failure handling; resume from committed phases; final plan-specified test and audit run; end-of-run reporting (`PRDS/2026-07-26-plan-to-execution.md:84-87`). Dependencies to model: executing-plans (`skills/executing-plans/SKILL.md`), isolating-worktrees (`skills/isolating-worktrees/SKILL.md`), prd-to-plan as the orchestrator template (`skills/prd-to-plan/SKILL.md`), the plan-file format (`skills/writing-plans/references/plan-template.md`), authoring conventions (`skills/writing-skills/SKILL.md`).
- **Out of scope:** code review or self-review; cleanup of worktrees, branches, or scratch files; editing or completing the plan file; verification beyond plan-specified commands; pull requests; plan authoring or revision; changes to executing-plans or the worktree-isolation skill; runtime inference of phase independence (`PRDS/2026-07-26-plan-to-execution.md:27-35,87`).

## 2. Files Retrieved

- `skills/prd-to-plan/SKILL.md` (whole file, 59 lines) — the only existing orchestrator; the model for Delegation Safety, dispatch-prompt MUSTs, workflow verification gates, Context Discipline, and the Boundary section the new skill parallels (`skills/prd-to-plan/SKILL.md:17-29,31-40,42-55,57-59`)
- `skills/executing-plans/SKILL.md` (whole file, 106 lines) — the per-phase executor the new skill dispatches; its Input Contract, mode predicate, Iron Rules, and Report Contract define the subagent interface the orchestrator must satisfy (`skills/executing-plans/SKILL.md:10-22,24-42,90-102`)
- `skills/isolating-worktrees/SKILL.md` (whole file, 95 lines) — the worktree-isolation skill the PRD names for parallel isolation (FR-006); covers detect/create/setup/verify only (`skills/isolating-worktrees/SKILL.md:8,29-81`)
- `skills/writing-plans/references/plan-template.md` (whole file, 117 lines) — the plan-file format the new skill consumes: frontmatter, phase sections, file-ownership rule, verification-command rule (`skills/writing-plans/references/plan-template.md:9-20,54-82,111-117`)
- `skills/writing-skills/SKILL.md:L43-59,61-108,110-142,144-175` — the authoring contract: frontmatter rules, form-to-failure table, discipline bulletproofing, directory structure, pressure-test Iron Law, deploy checklist
- `skills/executing-plans/references/report-template.md` — the per-phase report artifact the orchestrator reads for resume and status (frontmatter `status`, `git_commit_start`/`git_commit_end`; per `RESEARCH/2026-07-26-plan-to-execution-research-findings.md:123`)
- `skills/writing-skills/references/pressure-testing.md` — test-campaign methodology; the only "test" mechanism in this repo (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:43,344`)
- `PRDS/2026-07-26-plan-to-execution.md` (whole file, 122 lines) — FR-001 through FR-014, edge cases §7, success criteria §8
- `AGENTS.md:1-3,5-19,21-26` — skill placement mandate, pipeline description, artifact naming/provenance, pressure-test pollution policy
- `PLANS/2026-07-25-prd-to-plan-plan.md:1-11` — working example of plan frontmatter with full provenance chain
- `RESEARCH/2026-07-25-prd-to-plan-context-bundle.md:1-10` — working example of a prior context bundle for the sibling orchestrator skill

## 3. Entry / Exit Points

- **Entry (new skill):** invocation of `plan-to-execution` with a plan-file path; the plan is the sole source of phase definitions, phase-scoped context, independence declarations, and verification commands (`PRDS/2026-07-26-plan-to-execution.md:69`). executing-plans additionally requires `status: approved` and stops on `status: draft` (`skills/executing-plans/SKILL.md:14,20`).
- **Entry (per dispatched subagent):** executing-plans requires three inputs before any work — plan path, phase number, report file path (`skills/executing-plans/SKILL.md:12-18`). Report path convention: `PLANS/<plan-base>-phase-<N>-report.md`, `<plan-base>` = plan filename minus `-plan.md` (`skills/executing-plans/SKILL.md:18`).
- **Exit (per subagent):** executing-plans ends at the report; final message is a fixed ≤15-line, 5-item summary — Status (DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT), commits, verification summary, concerns, report path (`skills/executing-plans/SKILL.md:90-100`). It never merges, dispatches, or starts the next phase (`skills/executing-plans/SKILL.md:104-106`).
- **Exit (worktree setup):** isolating-worktrees ends at a "Worktree ready at <full-path>" report on green baseline, or a red-baseline report with evidence (`skills/isolating-worktrees/SKILL.md:75-81`).
- **Exit (new skill overall):** concludes once the plan's tests and audits pass, reporting phase outcomes, commit identifiers, and verification results; then stops — no review, cleanup, plan-file edit, or PR under any circumstances (`PRDS/2026-07-26-plan-to-execution.md:81-82`).
- **Boundary the new skill fills:** prd-to-plan explicitly "does not trigger execution" and ends at user acceptance of the plan (`skills/prd-to-plan/SKILL.md:40,59`).

## 4. Key Code

### Plan-file frontmatter (consumed by executing-plans and the new skill)
- **Location:** `skills/writing-plans/references/plan-template.md:10-20`
- **Code:**
  ```yaml
  ---
  artifact: implementation-plan
  date: YYYY-MM-DD
  git_commit: <full commit hash at planning time>
  branch: <branch name>
  request: <the user's request or spec block, verbatim>
  source_prd: <path to PRD, or none>
  source_bundle: <path to the context-bundle artifact, or none>
  source_research: <path to the research-findings artifact, or none>
  status: draft | approved
  ---
  ```

### Plan-file phase sections (phase definitions the orchestrator iterates)
- **Location:** `skills/writing-plans/references/plan-template.md:54-82`
- **Code:**
  ```markdown
  ## Phase 1: <Descriptive Name>

  ### Overview

  What this phase accomplishes.

  ### Changes Required

  #### 1. <Component/File Group>
  **File**: `path/to/file.ext`
  **Changes**: summary of changes

  ### Success Criteria

  #### Automated Verification:
  - [ ] <specific check>: `<repo-verified command>`

  #### Manual Verification:
  - [ ] <observable behavior to confirm>

  **Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.
  ```
- **Note:** no frontmatter field or section declares phase independence; parallel safety today rests on exhaustive per-phase file ownership (`skills/writing-plans/references/plan-template.md:114`). See §8 and §9.

### executing-plans mode predicate (how a dispatched subagent behaves)
- **Location:** `skills/executing-plans/SKILL.md:22`
- **Code:**
  ```markdown
  **Mode is determined by who gave you the report path.** A report path provided by a dispatching controller means subagent mode: the plan file is read-only and you report which criteria passed. If you are the interactive top-level agent executing for the user directly, you may check off that phase's Automated Verification items yourself.
  ```

### executing-plans final-message contract (what the orchestrator receives back)
- **Location:** `skills/executing-plans/SKILL.md:94-100`
- **Code:**
  ```markdown
  Then report back with ONLY (under 15 lines — the detail lives in the report file):

  - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
  - Commits created (short SHA + subject), or "uncommitted changes in working tree"
  - One-line verification summary (e.g. "5/5 automated criteria passing")
  - Your concerns, if any
  - The report file path
  ```

### prd-to-plan dispatch-prompt MUST list (the existing dispatch contract)
- **Location:** `skills/prd-to-plan/SKILL.md:23-29`
- **Code:**
  ```markdown
  Dispatch prompts for delegated phases MUST:

  1. Name the phase skill's absolute file path and instruct the subagent to read it in full (subagents do not auto-load skills).
  2. Scope the subagent to exactly that one phase — nothing before it, nothing after it.
  3. Include the user's optional instructions.
  4. Require the subagent's final message to contain only the produced artifact's path and a one-line outcome (FR-011).
  5. Forbid the subagent from asking the user questions — open questions are returned to the orchestrator instead.
  ```

### Worktree create + ignore check (isolating-worktrees)
- **Location:** `skills/isolating-worktrees/SKILL.md:43-56`
- **Code:**
  ```bash
  git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
  ```
  ```bash
  git worktree add "$LOCATION/$BRANCH_NAME" -b "$BRANCH_NAME"
  cd "$LOCATION/$BRANCH_NAME"
  ```
- **Note:** branch/dir names are derived from the artifact filename (plan `2026-07-26-payments-retry-plan.md` → `payments-retry`) (`skills/isolating-worktrees/SKILL.md:56`).

### SKILL.md frontmatter convention (authoring rule for the new skill)
- **Location:** `skills/writing-skills/SKILL.md:43-51`
- **Code:**
  ```markdown
  Two required fields: `name` and `description`.

  - `name`: lowercase letters, numbers, hyphens only. Prefer gerunds/verb-first: `writing-skills`, not `skill-writing`.
  - `description`: third person, describes ONLY when to use — never what the skill does or how it works.
    - Start with "Use when..." plus concrete triggering conditions and symptoms.
    - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body.
    - Include keywords an agent would search for: error messages, symptoms, synonyms, tool names.
  ```

## 5. References & Usages

### `executing-plans` (skill)
- **Definition:** `skills/executing-plans/SKILL.md:1-106`
- **Call sites / dependents:** `AGENTS.md:15` (pipeline step 7); `skills/isolating-worktrees/SKILL.md:8` ("executing-plans executors assume isolation is provided by the orchestration layer"); PRD FR-002 makes it the per-phase executor for plan-to-execution (`PRDS/2026-07-26-plan-to-execution.md:70`)

### `isolating-worktrees` (skill)
- **Definition:** `skills/isolating-worktrees/SKILL.md:1-95`
- **Call sites / dependents:** self-identifies as "the orchestration layer" for executing-plans executors (`skills/isolating-worktrees/SKILL.md:8`); named by PRD FR-006 as the isolation mechanism (`PRDS/2026-07-26-plan-to-execution.md:74`); no other skill file references it by name (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:397`)

### `prd-to-plan` (skill)
- **Definition:** `skills/prd-to-plan/SKILL.md:1-59`
- **Call sites / dependents:** `AGENTS.md:17`; its Boundary explicitly does not trigger execution (`skills/prd-to-plan/SKILL.md:59`) — the gap plan-to-execution fills

### `writing-plans` plan template
- **Definition:** `skills/writing-plans/references/plan-template.md:1-117`
- **Call sites / dependents:** consumed by executing-plans (`skills/executing-plans/SKILL.md:12-18,28,67-73`); produced by writing-plans (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:405`)

### `<plan-base>-phase-<N>-report.md` naming convention
- **Definition:** `skills/executing-plans/SKILL.md:18`
- **Call sites / dependents:** report template at `skills/executing-plans/references/report-template.md`; existing instances `PLANS/2026-07-25-prd-to-plan-phase-1-report.md`, `PLANS/2026-07-25-prd-to-plan-phase-2-report.md` (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:409`); `-plan` suffix rationale at `skills/writing-plans/references/plan-template.md:3`

### Phase-independence declaration
- **Definition:** none found — no frontmatter field or plan section declares phase independence (`skills/writing-plans/references/plan-template.md:10-20,54-82`)
- **Call sites / dependents:** parallel safety currently rests on disjoint per-phase file ownership (`skills/writing-plans/references/plan-template.md:114`; `skills/executing-plans/SKILL.md:28`; `AGENTS.md:15`); PRD FR-005 requires the plan to declare independence (`PRDS/2026-07-26-plan-to-execution.md:73`). See §9.

### Merge-back procedure for worktrees
- **Definition:** none found — isolating-worktrees documents create/setup/verify only (`skills/isolating-worktrees/SKILL.md:8,83-95`)
- **Call sites / dependents:** no callers found; PRD FR-009 requires merge-back in plan order with conflict stop-and-report (`PRDS/2026-07-26-plan-to-execution.md:77`). See §9.

### Blast Radius
- **Likely to change:** `skills/plan-to-execution/SKILL.md` (new file) and `skills/plan-to-execution/test-campaigns/` (new, per the authoring Iron Law `skills/writing-skills/SKILL.md:127-142`); placement mandated at `AGENTS.md:3`. The PRD forbids modifying executing-plans or the worktree-isolation skill (`PRDS/2026-07-26-plan-to-execution.md:34`).
- **Must not break:** `skills/executing-plans/SKILL.md` — the new skill is a consumer of its Input Contract and Report Contract (`skills/executing-plans/SKILL.md:10-22,90-102`); `skills/isolating-worktrees/SKILL.md` — consumed for parallel isolation (FR-006); `skills/writing-plans/references/plan-template.md` — the plan format the new skill parses; `AGENTS.md:5-19` — the pipeline description in repo instructions (the new orchestrator is adjacent to it).
- **Transitive dependents worth attention:** `skills/prd-to-plan/SKILL.md:59` — its Boundary language ("does not trigger execution") frames the handoff point the new skill occupies; `PLANS/2026-07-25-prd-to-plan-plan.md:1-11` — existing approved-plan instance whose phase/report files exercise the naming conventions.

## 6. Patterns & Idioms

### Pattern: Delegation Safety + dispatch-prompt MUST list
- **Location:** `skills/prd-to-plan/SKILL.md:17-29`
- **Snippet:** see §4 "prd-to-plan dispatch-prompt MUST list"
- **Key aspects:** delegation decisions stated per-phase with reasons (`skills/prd-to-plan/SKILL.md:19-20`); researching-codebase and iterating-plans run inline because they spawn their own sub-agents and nested-subagent support is unconfirmed (`skills/prd-to-plan/SKILL.md:20`); every inline fallback announced (`skills/prd-to-plan/SKILL.md:21`). executing-plans spawns no sub-agents (its workflow is read → implement → verify → report, `skills/executing-plans/SKILL.md:65-73`), matching the profile of the phases prd-to-plan delegates.

### Pattern: Workflow with verification gates between phases
- **Location:** `skills/prd-to-plan/SKILL.md:31-40`
- **Snippet:**
  ```markdown
  5. After each phase, verify the expected artifact file exists at the derived path before transitioning (FR-005). On failure, report the failure and the phase at which it occurred, and do not advance.
  ```
- **Key aspects:** numbered steps; input validation gate first (`skills/prd-to-plan/SKILL.md:33`); per-phase existence verification; failure = report and stop, never advance (`skills/prd-to-plan/SKILL.md:37`)

### Pattern: Context Discipline (orchestrator keeps only paths + outcomes)
- **Location:** `skills/prd-to-plan/SKILL.md:42-44`
- **Snippet:**
  ```markdown
  The orchestrator retains per phase only the artifact path and the phase outcome (FR-011). It does not read research-findings or context-bundle content into its own context — that detail belongs to the subagents and to the pipeline skills that consume those artifacts.
  ```
- **Key aspects:** paired with a `### Red Flags - STOP` list of quoted verbatim phrases (`skills/prd-to-plan/SKILL.md:46-55`)

### Pattern: Iron Rules / file ownership for parallel safety
- **Location:** `skills/executing-plans/SKILL.md:24-42`
- **Snippet:**
  ```markdown
  **Touch only files listed in your phase's Changes Required.** That list is your file ownership — it is what makes parallel execution safe. A needed fix outside the list is a report item, never an edit.

  **The plan file is read-only in subagent mode.** Parallel executors editing shared checkbox state produce lost updates and merge conflicts. Report criterion results; the controller flips the boxes.
  ```
- **Key aspects:** bold rule headline + explanation; closing "Violating the letter of these rules is violating the spirit of the rules." line (`skills/executing-plans/SKILL.md:42`); "Commit only if the plan or your dispatcher instructs it" (`skills/executing-plans/SKILL.md:40`) — commit is dispatcher-controlled, not automatic

### Pattern: Rationalizations table + Red Flags - STOP
- **Location:** `skills/executing-plans/SKILL.md:44-63`; `skills/prd-to-plan/SKILL.md:46-55`
- **Snippet:**
  ```markdown
  | Excuse | Reality |
  |--------|---------|
  | "This one-line fix in another file unblocks my phase" | That file may belong to a phase running in parallel right now. Report it; don't touch it. |
  ```
- **Key aspects:** two-column `| Excuse | Reality |` with quoted verbatim excuses; Red Flags as bulleted quoted phrases under the exact heading `### Red Flags - STOP`; both mandated for discipline skills by `skills/writing-skills/SKILL.md:77-108`

### Pattern: Sequential-only vs. parallel orchestration (contrasting existing behavior)
- **Variation A (sequential):** `skills/prd-to-plan/SKILL.md:59` — "never runs phases in parallel"; phases run in fixed order (`skills/prd-to-plan/SKILL.md:35`). Evidence: the only existing orchestrator; last touched in the prd-to-plan skill line of work (campaigns `skills/prd-to-plan/test-campaigns/2026-07-25-prd-to-plan.md`, `2026-07-26-prd-to-plan-status-gate.md` per `RESEARCH/2026-07-26-plan-to-execution-research-findings.md:39-40`).
- **Variation B (parallel, specified but unimplemented):** PRD FR-006 requires parallel dispatch of plan-declared independent phases in worktrees (`PRDS/2026-07-26-plan-to-execution.md:74`); parallel safety is asserted as existing capability for executing-plans subagents at `AGENTS.md:15` and `skills/executing-plans/SKILL.md:8,28,30`.
- **Contrast:** the existing orchestrator is deliberately sequential; the new skill is specified to be parallel for declared-independent phases. No code currently performs parallel dispatch anywhere in the repo (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:104`).

### Pattern: Resume mechanisms (two bases in play)
- **Variation A (report-file-based, existing):** executing-plans resume is report-file-based — an existing phase report means the phase was executed; verify claims against the repo rather than redo (`skills/executing-plans/SKILL.md:68`); existing plan checkmarks are trusted as done (`skills/executing-plans/SKILL.md:68`); prd-to-plan resume is artifact-existence-based with mandatory reuse/regenerate confirmation (`skills/prd-to-plan/SKILL.md:35`).
- **Variation B (commit-based, specified but unimplemented):** PRD FR-011 requires detecting already-committed phases from prior runs and resuming from the first incomplete phase (`PRDS/2026-07-26-plan-to-execution.md:79`); report frontmatter records `git_commit_start`/`git_commit_end` (or `"uncommitted"`) (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:108,123`), but no mechanism maps commits to phases (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:432`).
- **Contrast:** the existing resume signal is report/checkmark files; the PRD's resume signal is commits. See §9.

### Pattern: Artifact frontmatter + provenance fields
- **Location:** `PLANS/2026-07-25-prd-to-plan-plan.md:1-11`
- **Snippet:**
  ```yaml
  ---
  artifact: implementation-plan
  date: 2026-07-25
  git_commit: e70aebac8416adba54f7adaac7c54c6b2c961eb7
  branch: master
  request: "..."
  source_prd: PRDS/2026-07-25-prd-to-plan.md
  source_bundle: RESEARCH/2026-07-25-prd-to-plan-context-bundle.md
  source_research: RESEARCH/2026-07-25-prd-to-plan-research-findings.md
  status: approved
  ---
  ```
- **Key aspects:** common core `artifact/date/git_commit/branch/request/status`; provenance chain per `AGENTS.md:19`

### Pattern: Skill directory structure
- **Location:** `skills/writing-skills/SKILL.md:110-124`
- **Snippet:**
  ```
  skills/
    skill-name/
      SKILL.md              # Required. Overview + workflow.
      references/           # Heavy reference (100+ lines), loaded on demand
        some-topic.md
      scripts/              # Reusable tools
  ```
- **Key aspects:** kebab-case directory, one uppercase `SKILL.md`, optional `references/`/`scripts/`/`test-campaigns/` one level deep (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:71`); cross-reference skills by name, don't repeat content (`skills/writing-skills/SKILL.md:122`); test status lives only in `test-campaigns/`, never in SKILL.md (`skills/writing-skills/SKILL.md:140`)

## 7. Testing

- **How similar code is tested:** skills are validated by pressure-test campaigns, not executable tests — baseline scenarios run WITHOUT the skill, then WITH it; results logged to `skills/<skill>/test-campaigns/YYYY-MM-DD-<skill-name>[-fresh|-<topic>].md` (`skills/writing-skills/SKILL.md:127-142`; `skills/writing-skills/references/pressure-testing.md` per `RESEARCH/2026-07-26-plan-to-execution-research-findings.md:347-357`). The Iron Law: "NO SKILL WITHOUT A FAILING TEST FIRST" (`skills/writing-skills/SKILL.md:129`); any rule shipped untested is recorded as untested in the campaign log (`skills/writing-skills/SKILL.md:138,174`).
- **Tests covering affected code:** `skills/executing-plans/test-campaigns/2026-07-25-executing-plans.md`; `skills/isolating-worktrees/test-campaigns/2026-07-26-isolating-worktrees.md`; `skills/prd-to-plan/test-campaigns/2026-07-25-prd-to-plan.md` and `2026-07-26-prd-to-plan-status-gate.md` (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:37-41`). No test-campaigns exist for `plan-to-execution` (new skill).
- **Validation commands:** none exist. Verified: the repo root has no `package.json`, `Makefile`, `justfile`, `Taskfile`, or CI config (only `flake.nix`, a Nix dev environment, per `RESEARCH/2026-07-26-plan-to-execution-research-findings.md:49`); `.gitignore` contains only `.direnv/` and `result` (`.gitignore:1-2`). The only verification mechanism is the pressure-testing protocol in `skills/writing-skills/references/pressure-testing.md` (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:43`). Pressure-test pollution policy for baseline runs is at `AGENTS.md:21-26`.

## 8. Constraints & Risks

- **Invariants the plan must respect:**
  - New skills live under `skills/`, never `.opencode/skills/` or `.pi/skills/` (`AGENTS.md:3`); the repo's skills are globally discoverable via the symlink `~/.config/opencode/skills/dangerpowers -> /home/dave/source/dangerpowers/skills` (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:68`).
  - SKILL.md frontmatter is exactly `name` + `description`; description is triggers-only, never a workflow summary (`skills/writing-skills/SKILL.md:43-51`).
  - The new skill must not modify executing-plans or isolating-worktrees behavior (`PRDS/2026-07-26-plan-to-execution.md:34`).
  - executing-plans requires a `status: approved` plan and stops on draft (`skills/executing-plans/SKILL.md:14,20`); in subagent mode the plan file is read-only (`skills/executing-plans/SKILL.md:22,30`).
  - Commits by phase executors are dispatcher-controlled: "Commit only if the plan or your dispatcher instructs it" (`skills/executing-plans/SKILL.md:40`) — the PRD's per-phase commit checkpoints (FR-008) therefore depend on the dispatcher instructing the commit.
  - All artifacts are committed to source control; `RESEARCH/` is not gitignored (`AGENTS.md:19`); `.gitignore` currently lacks a `.worktrees` entry (`.gitignore:1-2`), and isolating-worktrees' own procedure adds the ignore entry and commits it before creating a worktree (`skills/isolating-worktrees/SKILL.md:41-47`).
  - executing-plans' BLOCKED path uses a fixed mismatch report structure and routes plan drift to iterating-plans (`skills/executing-plans/SKILL.md:75-88`); PRD FR-010 treats any phase failure as a full-run stop (`PRDS/2026-07-26-plan-to-execution.md:78`).
  - The plan template mandates a human-confirmation pause between phases (`skills/writing-plans/references/plan-template.md:82`); the PRD specifies autonomous sequential dispatch of dependent phases (FR-007, `PRDS/2026-07-26-plan-to-execution.md:75`) — the pause text exists in every plan written from the current template.
- **Dependencies / ordering:** the new skill consumes plans produced by writing-plans and dispatches executing-plans; it occupies the boundary prd-to-plan explicitly stops at (`skills/prd-to-plan/SKILL.md:59`). Skill discovery depends only on the symlink + frontmatter (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:67-68`).
- **Likely failure modes (evidence-backed):**
  - Merge conflicts on integration: no merge-back, integration, or conflict-handling procedure exists anywhere in the repo (`skills/isolating-worktrees/SKILL.md:8,83-95`; `RESEARCH/2026-07-26-plan-to-execution-research-findings.md:416-417`); PRD FR-009 requires merge-back in plan order with conflict stop-and-report (`PRDS/2026-07-26-plan-to-execution.md:77`).
  - Sandbox/permission denial on `git worktree add`: isolating-worktrees' fallback is "tell the user and work in the current directory instead" (`skills/isolating-worktrees/SKILL.md:58`) — working in the current directory removes the isolation FR-006 depends on.
  - Nested-subagent support is unconfirmed (`skills/prd-to-plan/SKILL.md:20`); the new skill dispatches executing-plans in subagents, and executing-plans spawns no sub-agents of its own (`skills/executing-plans/SKILL.md:65-73`).
  - Phase executors leaving uncommitted work: the default executing-plans behavior leaves changes uncommitted unless instructed (`skills/executing-plans/SKILL.md:40`); PRD treats "a phase produces no commit" as an incomplete phase and stops the run (`PRDS/2026-07-26-plan-to-execution.md:108`).
- **Conflicting findings:**
  - Resume signal: report-file/checkmark-based (existing, `skills/executing-plans/SKILL.md:68`) vs. commit-based (PRD FR-011, `PRDS/2026-07-26-plan-to-execution.md:79`). See §6 "Resume mechanisms".
  - Inter-phase pacing: template-mandated human pause (`skills/writing-plans/references/plan-template.md:82`) vs. PRD autonomous sequencing (`PRDS/2026-07-26-plan-to-execution.md:75`).
- **Provenance note:** the PRD's own frontmatter reads `status: draft` (`PRDS/2026-07-26-plan-to-execution.md:7`) and the file is currently untracked in git (`git status` at bundle time). Research was conducted at commit `9899a8cf1d2f0c8480be27c8f1b42cd4e7207b77` (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:4`); HEAD is now `812f4429`, and the only intervening change is the research-findings artifact itself — no cited file changed (`git diff --stat 9899a8c..HEAD -- skills/ AGENTS.md .gitignore` empty).

## 9. Open Questions

- `[needs-human]` — **Phase-independence declaration format:** no plan-file field or section declares phase independence today (`skills/writing-plans/references/plan-template.md:10-20,54-82`); PRD FR-005 assumes the plan declares it (`PRDS/2026-07-26-plan-to-execution.md:73`). How that declaration is expressed — and whether writing-plans' template gains a convention for it, given the PRD forbids modifying only executing-plans and the worktree-isolation skill (`PRDS/2026-07-26-plan-to-execution.md:34`) — is a design decision the code cannot answer.
- `[needs-human]` — **Merge-back procedure:** no merge-back, integration, or conflict-handling procedure exists in the repo (`skills/isolating-worktrees/SKILL.md:8`); PRD FR-009 requires one (`PRDS/2026-07-26-plan-to-execution.md:77`). Where the procedure lives (inside plan-to-execution vs. added to isolating-worktrees, which the PRD appears to forbid modifying) is undecidable from the code.
- `[needs-human]` — **Plan-level final test/audit commands:** the plan template has per-phase Automated Verification commands (`skills/writing-plans/references/plan-template.md:72-76`) but no plan-level "final full test and audit" section; closest are `## Desired End State` (`skills/writing-plans/references/plan-template.md:34-36`) and `## Testing Strategy` (`skills/writing-plans/references/plan-template.md:92-101`). FR-012 assumes the plan specifies these commands (`PRDS/2026-07-26-plan-to-execution.md:80`); which plan section supplies them is undetermined.
- `[needs-human]` — **Resume-by-commit detection:** existing resume is report-file-based (`skills/executing-plans/SKILL.md:68`); FR-011 requires detecting completed phases from commits (`PRDS/2026-07-26-plan-to-execution.md:79`), and no existing mechanism maps commits to phases beyond report frontmatter `git_commit_start`/`git_commit_end` (`RESEARCH/2026-07-26-plan-to-execution-research-findings.md:432`). The detection mechanism is a design decision.

## 10. Start Here

- **Start:** `skills/prd-to-plan/SKILL.md` — it is the repo's only orchestrator skill and the structural template the new skill most directly parallels: its Delegation Safety block (`skills/prd-to-plan/SKILL.md:17-29`), workflow verification gates (`skills/prd-to-plan/SKILL.md:31-40`), Context Discipline (`skills/prd-to-plan/SKILL.md:42-55`), and Boundary section (`skills/prd-to-plan/SKILL.md:57-59`) are the four structures every orchestrator concern in the PRD (FR-002/FR-003/FR-004 subagent dispatch, FR-010 stop-and-report, FR-013/FR-014 terminal boundary) maps onto, and it is the file whose explicit non-execution boundary (`skills/prd-to-plan/SKILL.md:59`) defines exactly where plan-to-execution begins.
