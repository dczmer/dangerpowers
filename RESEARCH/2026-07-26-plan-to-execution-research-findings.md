---
artifact: research-findings
date: 2026-07-26
git_commit: 9899a8cf1d2f0c8480be27c8f1b42cd4e7207b77
branch: master
request: "use the prd-to-plan skill to produce a plan form the following PRD: @/home/dave/source/dangerpowers/PRDS/2026-07-26-plan-to-execution.md"
source_prd: PRDS/2026-07-26-plan-to-execution.md
status: complete
---

# Research Findings

## 1. Request Summary

Produce an implementation plan for a new orchestrator skill named **plan-to-execution**, per PRD `PRDS/2026-07-26-plan-to-execution.md`. The skill will drive execution of an approved plan file by dispatching one subagent per phase running the executing-plans skill, running plan-declared independent phases in parallel inside isolated git worktrees, checkpointing each phase as a git commit, resuming interrupted runs from committed phases, and running the plan's full test and audit commands at the end — then stopping deliberately before review, cleanup, plan completion, or PR creation.

- **In scope:** the existing skills the new skill depends on (executing-plans, isolating-worktrees), the orchestrator it models (prd-to-plan), the plan-file format it consumes (writing-plans template), skill-authoring conventions (writing-skills), artifact naming/frontmatter conventions, skill discovery mechanism, test-campaign conventions.
- **Out of scope:** designing the new skill itself; evaluating or recommending changes to existing skills; any code outside this repository.

## 2. File Map

### Implementation (skill definitions)
- `/home/dave/source/dangerpowers/skills/executing-plans/SKILL.md` — skill: executes one phase of an approved plan per invocation; subagent-dispatchable
- `/home/dave/source/dangerpowers/skills/isolating-worktrees/SKILL.md` — skill: git-worktree isolation for executing-plans phase executors
- `/home/dave/source/dangerpowers/skills/iterating-plans/SKILL.md` — skill: applies human review edits to existing plans
- `/home/dave/source/dangerpowers/skills/prd-to-plan/SKILL.md` — skill: orchestrates research → scouting → plan-writing pipeline (existing orchestrator)
- `/home/dave/source/dangerpowers/skills/project-bootstrap-nix/SKILL.md` — skill: bootstraps new projects with Nix flake
- `/home/dave/source/dangerpowers/skills/prompt-shaping/SKILL.md` — skill: confirms scope of vague requests
- `/home/dave/source/dangerpowers/skills/researching-codebase/SKILL.md` — skill: codebase research producing research-findings artifacts
- `/home/dave/source/dangerpowers/skills/scouting-context/SKILL.md` — skill: compresses research into context-bundle handoffs
- `/home/dave/source/dangerpowers/skills/writing-plans/SKILL.md` — skill: writes phased implementation plans to PLANS/
- `/home/dave/source/dangerpowers/skills/writing-prds/SKILL.md` — skill: writes PRDs to PRDS/
- `/home/dave/source/dangerpowers/skills/writing-quick-plans/SKILL.md` — skill: lightweight plan writing (SKILL.md + one test campaign only)
- `/home/dave/source/dangerpowers/skills/writing-skills/SKILL.md` — skill: authoring/reviewing skills; hosts pressure-testing methodology

### Tests
- `/home/dave/source/dangerpowers/skills/executing-plans/test-campaigns/2026-07-25-executing-plans.md` — pressure-test results for executing-plans
- `/home/dave/source/dangerpowers/skills/isolating-worktrees/test-campaigns/2026-07-26-isolating-worktrees.md` — pressure-test results for isolating-worktrees
- `/home/dave/source/dangerpowers/skills/prd-to-plan/test-campaigns/2026-07-25-prd-to-plan.md` — pressure-test results
- `/home/dave/source/dangerpowers/skills/prd-to-plan/test-campaigns/2026-07-26-prd-to-plan-status-gate.md` — follow-up campaign for a status:approved gate
- `/home/dave/source/dangerpowers/skills/writing-skills/test-campaigns/2026-07-23-writing-skills.md` and `2026-07-24-writing-skills-fresh.md` — pressure-test results
- Each other skill has an analogous `test-campaigns/` directory (12 skills, each with 1–2 campaign files)
- No executable test suite exists for skills; "tests" are pressure-test campaign logs per `skills/writing-skills/references/pressure-testing.md`

### Configuration
- `/home/dave/source/dangerpowers/.opencode/opencode.jsonc` — opencode config: `$schema`, permissions all-allow, watcher ignore list (lines 1–16); no skill configuration
- `/home/dave/source/dangerpowers/.gitignore` — ignores only `.direnv/` and `result`; RESEARCH/ is tracked
- `/home/dave/source/dangerpowers/.opencode/.gitignore` — ignores node_modules, package.json, lockfiles inside .opencode/
- `/home/dave/source/dangerpowers/flake.nix`, `flake.lock`, `.envrc` — Nix dev environment

### Type Definitions
- None; this repository contains markdown skills, no typed code.

### Documentation
- `/home/dave/source/dangerpowers/AGENTS.md` — repo instructions: pipeline description, artifact naming, RESEARCH/ is NOT gitignored
- `/home/dave/source/dangerpowers/README.md` — repo readme
- `/home/dave/source/dangerpowers/NOTES.md` — scratch notes
- `/home/dave/source/dangerpowers/EXAMPLE_AGENT_RULES.md` — example agent rules doc
- `/home/dave/source/dangerpowers/skills/executing-plans/references/report-template.md` — template for phase execution reports
- `/home/dave/source/dangerpowers/skills/writing-plans/references/plan-template.md` — template for plan artifacts
- `/home/dave/source/dangerpowers/skills/writing-prds/references/prd-template.md` — template for PRD artifacts
- `/home/dave/source/dangerpowers/skills/researching-codebase/references/findings-template.md` — template for research-findings artifacts
- `/home/dave/source/dangerpowers/skills/scouting-context/references/bundle-template.md` — template for context-bundle artifacts
- `/home/dave/source/dangerpowers/skills/writing-skills/references/pressure-testing.md` — pressure-test campaign methodology

### Entry Points
- Each skill's entry point is its `skills/<name>/SKILL.md`, surfaced via frontmatter `name`/`description` (e.g. `skills/prd-to-plan/SKILL.md:1-4`)
- `/home/dave/.config/opencode/skills/dangerpowers` is a symlink to `/home/dave/source/dangerpowers/skills` — every skill in this repo is globally discoverable

### Related Directories
- `skills/` — 40 files total across 12 skill directories; convention: kebab-case directory, exactly one uppercase `SKILL.md`, optional `references/`, `scripts/`, `test-campaigns/`
- `PRDS/` — 2 files; convention `YYYY-MM-DD-<kebab>.md`
- `PLANS/` — 3 files; convention `YYYY-MM-DD-<kebab>-plan.md` and `<plan-base>-phase-<N>-report.md`
- `RESEARCH/` — 2 files; convention `YYYY-MM-DD-<kebab>-research-findings.md` / `-context-bundle.md`
- `.opencode/` — config + npm dependencies; no `.opencode/skills/`, `.opencode/agents/`, or `.pi/` directories exist

## 3. Implementation Analysis

- **Overview:** The repo is a library of opencode skills (`AGENTS.md:1,3`). The closest existing orchestrator is prd-to-plan, which drives the planning pipeline but explicitly stops at plan acceptance and "does not trigger execution" (`skills/prd-to-plan/SKILL.md:40,59`). executing-plans is the per-phase executor, designed to run inline or as a dispatched subagent, one phase per invocation (`skills/executing-plans/SKILL.md:8,26`). isolating-worktrees provides workspace isolation and positions itself as "that [orchestration] layer" for executing-plans executors (`skills/isolating-worktrees/SKILL.md:8`). Plan files written by writing-plans contain per-phase file-ownership lists and verification commands but no formal phase-independence field (`skills/writing-plans/references/plan-template.md:54-82,114`).

- **Entry points:**
  - prd-to-plan: PRD path input; input contract at `skills/prd-to-plan/SKILL.md:10-15`
  - executing-plans: three required inputs — plan path, phase number, report file path (`skills/executing-plans/SKILL.md:10-18`)
  - isolating-worktrees: no input contract; begins with detection commands at `skills/isolating-worktrees/SKILL.md:14-18`
  - writing-plans: inputs are context-bundle path plus original request/spec (`skills/writing-plans/SKILL.md:12-16`)

- **Exit points:**
  - prd-to-plan ends at user acceptance of the plan; does not set `status`, does not trigger execution (`skills/prd-to-plan/SKILL.md:40,59`)
  - executing-plans "ends at the report": writes the report file, returns a final message ≤15 lines with Status, commits, verification summary, concerns, report path (`skills/executing-plans/SKILL.md:94-106`); does not merge, dispatch, or start the next phase (`skills/executing-plans/SKILL.md:106`)
  - isolating-worktrees ends at a "Worktree ready at <full-path>" report (`skills/isolating-worktrees/SKILL.md:75-80`) or a red-baseline report (`skills/isolating-worktrees/SKILL.md:81`); no merge-back or cleanup procedure is documented anywhere in the skill
  - writing-plans ends by presenting the plan location for approval (`skills/writing-plans/SKILL.md:58`)

- **Data flow:**
  1. User supplies a PRD path; prd-to-plan validates it exists, is a PRD, and has `status: approved` (`skills/prd-to-plan/SKILL.md:14,33`)
  2. Orchestrator derives expected artifact paths from naming conventions (`skills/prd-to-plan/SKILL.md:34`)
  3. Per pipeline phase, in fixed order researching-codebase → scouting-context → writing-plans: existing artifacts trigger a reuse-vs-regenerate user question (`skills/prd-to-plan/SKILL.md:35`)
  4. scouting-context and writing-plans are dispatched to `general` subagents with prompts naming the skill's absolute path; researching-codebase and iterating-plans run inline (`skills/prd-to-plan/SKILL.md:19-21,23-29`)
  5. Subagent returns only artifact path + one-line outcome; orchestrator retains only path + outcome per phase (`skills/prd-to-plan/SKILL.md:28,44`)
  6. Orchestrator verifies each artifact exists before advancing; on failure it reports and stops (`skills/prd-to-plan/SKILL.md:37`)
  7. Separately (not orchestrated today): executing-plans receives plan path + phase number + report path (`skills/executing-plans/SKILL.md:12-18`), reads plan and provenance artifacts (`skills/executing-plans/SKILL.md:67`), implements only files in its phase's Changes Required (`skills/executing-plans/SKILL.md:28,69-70`), runs every Automated Verification criterion (`skills/executing-plans/SKILL.md:71`), writes `PLANS/<plan-base>-phase-<N>-report.md` (`skills/executing-plans/SKILL.md:18,72`), returns the 5-line status message (`skills/executing-plans/SKILL.md:94-100`)
  8. isolating-worktrees runs before executor work: detect existing isolation (`skills/isolating-worktrees/SKILL.md:10-27`) → select directory (`.worktrees/` preferred; lines 31-37) → verify gitignore (lines 41-47) → `git worktree add "$LOCATION/$BRANCH_NAME" -b "$BRANCH_NAME"` (lines 51-54) → install deps (lines 60-69) → run baseline tests, report ready (lines 71-81)

- **Key logic:**
  - **Delegation rules (prd-to-plan):** scouting-context and writing-plans → `general` subagents (`skills/prd-to-plan/SKILL.md:19`); researching-codebase and iterating-plans → inline because they spawn their own sub-agents and nested-subagent support is unconfirmed (`skills/prd-to-plan/SKILL.md:20`); every inline fallback is announced (`skills/prd-to-plan/SKILL.md:21`); phases run in fixed order, never in parallel (`skills/prd-to-plan/SKILL.md:35,59`)
  - **Dispatch-prompt contract (prd-to-plan):** five MUSTs (`skills/prd-to-plan/SKILL.md:23-29`): (1) name the phase skill's absolute path, instruct reading it in full; (2) scope to exactly one phase; (3) include user instructions; (4) final message = artifact path + one-line outcome; (5) forbid user questions — questions return to the orchestrator, which mediates all user interaction (`skills/prd-to-plan/SKILL.md:36`)
  - **Verification gates:** prd-to-plan checks artifact existence after each phase (`skills/prd-to-plan/SKILL.md:37`); executing-plans requires every automated criterion to pass before reporting DONE (`skills/executing-plans/SKILL.md:34,71`); isolating-worktrees requires a green baseline before reporting ready (`skills/isolating-worktrees/SKILL.md:71-81`)
  - **Mode determination (executing-plans):** "Mode is determined by who gave you the report path" — dispatcher-provided = subagent mode, plan file read-only; interactive top-level = may check off Automated Verification items (`skills/executing-plans/SKILL.md:22,30,73`)
  - **Resume/checkpoint mechanisms as they exist today:** executing-plans resume is report-file-based, not commit-based — an existing phase report means the phase was executed; verify claims against the repo rather than redo (`skills/executing-plans/SKILL.md:68`; `skills/executing-plans/references/report-template.md:5`). Existing plan checkmarks are trusted as done (`skills/executing-plans/SKILL.md:68`). Commit is not automatic: "Commit only if the plan or your dispatcher instructs it" (`skills/executing-plans/SKILL.md:40`); report frontmatter records `git_commit_start`/`git_commit_end` (or `"uncommitted"`) (`skills/executing-plans/references/report-template.md:18-19`). Reports are write-once (`skills/executing-plans/references/report-template.md:81`). prd-to-plan resume is artifact-existence-based with mandatory reuse/regenerate confirmation (`skills/prd-to-plan/SKILL.md:35`)

- **Error handling:**
  - executing-plans BLOCKED: plan-vs-reality mismatch stops work; fixed report structure `Issue in Phase [N]: / Expected: / Found: [file:line] / Why this matters: / How should I proceed?` (`skills/executing-plans/SKILL.md:36,77-86`); plan drift routes the human to iterating-plans (`skills/executing-plans/SKILL.md:88`)
  - executing-plans statuses: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT (`skills/executing-plans/SKILL.md:96`); BLOCKED/NEEDS_CONTEXT specifics go in the final message (`skills/executing-plans/SKILL.md:102`); such reports are still complete, enabling resume/re-dispatch (`skills/executing-plans/references/report-template.md:80`)
  - isolating-worktrees failure paths: sandbox/permission error on `worktree add` → tell user, work in current directory (`skills/isolating-worktrees/SKILL.md:58,93`); unignored worktree directory → add to `.gitignore`, commit, proceed (lines 47,92); red baseline → report with evidence and ask, never report ready on red (lines 81,94). **No merge-conflict or merge-back handling is documented** — the skill covers create/setup/verify only (`skills/isolating-worktrees/SKILL.md:8`)
  - prd-to-plan failure: report the failure and the phase, do not advance (`skills/prd-to-plan/SKILL.md:37`)

- **Configuration & flags:**
  - **Skill discovery:** symlink `~/.config/opencode/skills/dangerpowers -> /home/dave/source/dangerpowers/skills`; AGENTS.md:3 mandates new skills live under `skills/`; each skill's trigger surface is its frontmatter `name`/`description`
  - **Naming:** plans `PLANS/YYYY-MM-DD-<kebab>-plan.md` (`skills/writing-plans/SKILL.md:56`); reports `PLANS/<plan-base>-phase-<N>-report.md` (`skills/executing-plans/SKILL.md:18`); worktree branch/dir derived from artifact name, e.g. plan `2026-07-26-payments-retry-plan.md` → `payments-retry` (`skills/isolating-worktrees/SKILL.md:56`); all artifacts committed to source control (`AGENTS.md:19`)
  - **Plan-file frontmatter** (`skills/writing-plans/references/plan-template.md:10-20`): `artifact: implementation-plan`, `date`, `git_commit`, `branch`, `request`, `source_prd`, `source_bundle`, `source_research`, `status: draft | approved`; executing-plans requires `status: approved` (`skills/executing-plans/SKILL.md:14,20,68`)
  - **Plan-file phase sections** (`skills/writing-plans/references/plan-template.md:54-82`): `### Overview`, `### Changes Required` (numbered, exact `**File**:` paths), `### Success Criteria` split into `#### Automated Verification:` (checkboxes with repo-verified commands, lines 72-76) and `#### Manual Verification:` (lines 78-80); Implementation Note mandates a human-confirmation pause between phases (line 82)
  - **Phase independence:** no frontmatter field or section declares which phases are independent. Parallel safety is implicit via exhaustive per-phase file ownership: "executing-plans treats this list as file ownership — it is what makes parallel phase execution safe" (`skills/writing-plans/references/plan-template.md:114`), echoed at `skills/executing-plans/SKILL.md:28` and `AGENTS.md:15` ("phases own disjoint file sets; the plan file is read-only in subagent mode")
  - **Test/audit commands:** present per phase in Automated Verification (`skills/writing-plans/references/plan-template.md:72-76`), guaranteed repo-verified (`skills/writing-plans/SKILL.md:26`; `plan-template.md:115`). No plan-level "final audit" command section exists; closest plan-level verification is `## Desired End State` with "how to verify it" (`plan-template.md:34-36`) and `## Testing Strategy` (lines 92-101)
  - **Report frontmatter** (`skills/executing-plans/references/report-template.md:12-20`): `artifact: implementation-report`, `date`, `plan`, `phase`, `status`, `git_commit_start`, `git_commit_end`

## 4. Patterns & Idioms

### Pattern: SKILL.md frontmatter (name + description only)
- **Location:** `skills/writing-skills/SKILL.md:43-51`
- **Snippet:**
  ```
  Two required fields: `name` and `description`.

  - `name`: lowercase letters, numbers, hyphens only. Prefer gerunds/verb-first: `writing-skills`, not `skill-writing`.
  - `description`: third person, describes ONLY when to use — never what the skill does or how it works.
    - Start with "Use when..." plus concrete triggering conditions and symptoms.
    - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body.
    - Include keywords an agent would search for: error messages, symptoms, synonyms, tool names.
  ```
- **Key aspects:** frontmatter is exactly two fields; description = triggers only + "Keywords:" tail

### Pattern: Delegation Safety + dispatch-prompt MUST list
- **Location:** `skills/prd-to-plan/SKILL.md:17-29`
- **Snippet:**
  ```
  ## Delegation Safety

  - **scouting-context** and **writing-plans** run in `general` subagents (FR-003).
  - **researching-codebase** and **iterating-plans** run **inline in the orchestrator**, because they spawn their own sub-agents and nested-subagent support is unconfirmed (FR-004). If nesting support is later confirmed, those phases may be delegated.
  - **Every inline fallback is noted to the user** — say which phase is running inline and why.

  Dispatch prompts for delegated phases MUST:

  1. Name the phase skill's absolute file path and instruct the subagent to read it in full (subagents do not auto-load skills).
  2. Scope the subagent to exactly that one phase — nothing before it, nothing after it.
  3. Include the user's optional instructions.
  4. Require the subagent's final message to contain only the produced artifact's path and a one-line outcome (FR-011).
  5. Forbid the subagent from asking the user questions — open questions are returned to the orchestrator instead.
  ```
- **Key aspects:** which-phase-delegates stated with reasons; inline fallbacks surfaced; numbered MUST list

### Pattern: Workflow with verification gates between phases
- **Location:** `skills/prd-to-plan/SKILL.md:31-40`
- **Snippet:**
  ```
  ## Workflow

  1. Validate the PRD input: it exists, it is a PRD, and its frontmatter says `status: approved`. Record the optional instructions. Surface any PRD/instruction conflict to the user before doing anything else.
  2. Derive the expected artifact path for each phase from the naming conventions: `RESEARCH/YYYY-MM-DD-<kebab>-research-findings.md`, `RESEARCH/YYYY-MM-DD-<kebab>-context-bundle.md`, `PLANS/YYYY-MM-DD-<kebab>-plan.md`.
  3. For each phase in fixed order — researching-codebase, then scouting-context, then writing-plans (FR-002): if that phase's artifact for this PRD already exists, use the `question` tool to ask whether to reuse or regenerate it **before** running the phase (FR-006). Never reuse silently. Never regenerate silently.
  4. Run or dispatch the phase per Delegation Safety. If a delegated phase returns questions (e.g. writing-plans' phase-outline buy-in), ask the user via the `question` tool and resume the phase with the answers. The orchestrator mediates all user interaction; subagents never ask directly.
  5. After each phase, verify the expected artifact file exists at the derived path before transitioning (FR-005). On failure, report the failure and the phase at which it occurred, and do not advance.
  6. When writing-plans completes, present the plan location to the user for review (FR-008).
  7. Feedback loop (FR-009): when the user gives feedback, invoke the **iterating-plans** skill (inline per Delegation Safety; its confirm-before-editing questions go to the user through the orchestrator), then re-present the revised plan. Repeat until the user accepts. There is no maximum-attempts cutoff.
  8. User acceptance concludes the skill. Do not set the plan document's `status` field. Do not trigger execution (FR-010).
  ```
- **Key aspects:** numbered steps; validation gate; existence verification gate; user-acceptance final gate

### Pattern: Context Discipline (orchestrator keeps only paths + outcomes)
- **Location:** `skills/prd-to-plan/SKILL.md:42-55`
- **Snippet:**
  ```
  ## Context Discipline

  The orchestrator retains per phase only the artifact path and the phase outcome (FR-011). It does not read research-findings or context-bundle content into its own context — that detail belongs to the subagents and to the pipeline skills that consume those artifacts.

  ### Red Flags - STOP

  - "I'll skim the research findings to summarize for the user"
  - "I'll keep the bundle content handy for the planning phase"
  - "The artifact exists so I'll reuse it without asking"
  - "The phase mostly worked so I'll advance anyway"
  - "These three edits are small; I'll just fix the plan myself"
  - "The PRD is basically final; the status field is a formality"
  - "I'll plan against the draft and re-verify once it's approved"
  - "I'll just run research against the draft — only plan-writing is gated"
  ```
- **Key aspects:** retained context enumerated; Red Flags quoted verbatim phrases

### Pattern: Subagent input contract + mode predicate
- **Location:** `skills/executing-plans/SKILL.md:10-22`
- **Snippet:**
  ```
  ## Input Contract

  Three inputs, all required before any work:

  1. A path to a `status: approved` plan in `PLANS/`
  2. The phase number to execute
  3. A report file path

  Reports live in `PLANS/` beside the plan, named `<plan-base>-phase-<N>-report.md`, where `<plan-base>` is the plan filename minus the `-plan.md` suffix. If a dispatcher did not provide the report path, derive it yourself from this convention. One report file per phase per invocation — never append to or edit another phase's report.

  If any of the three is missing, ask for it. If the plan is `status: draft`, stop — execution requires human approval, and any edit voids it (see iterating-plans).

  **Mode is determined by who gave you the report path.** A report path provided by a dispatching controller means subagent mode: the plan file is read-only and you report which criteria passed. If you are the interactive top-level agent executing for the user directly, you may check off that phase's Automated Verification items yourself.
  ```
- **Key aspects:** mode derived from an observable predicate (who provided the report path); dispatcher owns shared state

### Pattern: Report naming + final-message contract
- **Location:** `skills/executing-plans/SKILL.md:90-102`
- **Snippet:**
  ```
  ## Report Contract

  Write the full report to the report file per `references/report-template.md` — the template is the canonical structure; every section is required and "None" is a valid entry. The report covers: what was implemented, files changed, each automated criterion with command + result + output evidence, deviations, issues, and follow-ups. The frontmatter `status` must match your final-message status.

  Then report back with ONLY (under 15 lines — the detail lives in the report file):

  - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
  - Commits created (short SHA + subject), or "uncommitted changes in working tree"
  - One-line verification summary (e.g. "5/5 automated criteria passing")
  - Your concerns, if any
  - The report file path
  ```
- **Key aspects:** detail lives in report file; final message is a fixed 5-item summary

### Pattern: Iron Rules / file ownership for parallel safety
- **Location:** `skills/executing-plans/SKILL.md:24-42`
- **Snippet:**
  ```
  **One phase per invocation.** Do not start the next phase, do not "finish up" a previous one, do not check off criteria for any phase but your own.

  **Touch only files listed in your phase's Changes Required.** That list is your file ownership — it is what makes parallel execution safe. A needed fix outside the list is a report item, never an edit.

  **The plan file is read-only in subagent mode.** Parallel executors editing shared checkbox state produce lost updates and merge conflicts. Report criterion results; the controller flips the boxes.

  **Never check off Manual Verification items.** A human confirms those, in every mode.

  **Every automated criterion runs and passes before you report DONE.** Run the commands exactly as written in the plan — they were repo-verified at planning time. A criterion that fails for reasons outside your scope is a report item, not a pass and not a silent skip.

  **A plan-vs-reality mismatch stops you.** When the code doesn't match what the plan says, do not improvise a deviation and do not force the plan through. Report BLOCKED with the mismatch protocol below.

  **Read files fully.** No limit/offset on any file in your phase's Changes Required. Partial reads are how implementers break invariants they never saw.

  **Commit only if the plan or your dispatcher instructs it.** Otherwise leave the working tree changes and list every changed file in the report.

  **Violating the letter of these rules is violating the spirit of the rules.**
  ```
- **Key aspects:** bold rule headline followed by explanation; closing "letter/spirit" line

### Pattern: Rationalizations table
- **Location:** `skills/executing-plans/SKILL.md:44-54`
- **Snippet:**
  ```
  ### Rationalizations

  | Excuse | Reality |
  |--------|---------|
  | "This one-line fix in another file unblocks my phase" | That file may belong to a phase running in parallel right now. Report it; don't touch it. |
  | "The plan's approach is clearly wrong, my way is better" | A human approved the plan, not your improvisation. Mismatch → BLOCKED with the protocol below. |
  | "Flipping one checkbox is harmless" | Two executors flipping boxes in the same file is a lost update. In subagent mode the plan is read-only, no exceptions. |
  | "The code is obviously right; the test command is slow" | DONE without green verification is a claim, not a result. Run it. |
  | "I only need the relevant part of the file" | The invariant you break will be in the part you skipped. Read it fully. |
  | "Phase N+1 is tiny, I'll do it while I'm here" | Its files may be owned by another executor. One phase per invocation. |
  | "The failing check is unrelated to my changes, I'll note it and report DONE" | Unrelated failures are DONE_WITH_CONCERNS with evidence, never DONE. |
  ```
- **Key aspects:** two-column `| Excuse | Reality |` with quoted verbatim excuses

### Pattern: Red Flags - STOP
- **Location:** `skills/executing-plans/SKILL.md:56-63`
- **Snippet:**
  ```
  ### Red Flags - STOP

  - "I'll just fix this thing in a file outside my phase"
  - "The plan says X but the code does Y — I'll adapt quietly"
  - "I'll update the plan checkboxes so the controller doesn't have to"
  - "Verification mostly passed"
  - "I skimmed the file; the change is localized"
  - "Manual testing looks fine to me, checking it off"
  ```
- **Key aspects:** bulleted quoted phrases under the exact heading `### Red Flags - STOP`

### Pattern: Worktree detect → create → setup → verify
- **Location:** `skills/isolating-worktrees/SKILL.md:14-27` (detect), `43-58` (ignore check + create), `64-69` (setup), `75-81` (verify/report)
- **Snippet (create):**
  ```bash
  git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
  ```
  ```bash
  git worktree add "$LOCATION/$BRANCH_NAME" -b "$BRANCH_NAME"
  cd "$LOCATION/$BRANCH_NAME"
  ```
- **Snippet (ready report):**
  ```
  Worktree ready at <full-path>
  Tests passing (<N> tests, 0 failures)
  Ready to implement <feature-name>
  ```
- **Key aspects:** directory priority (user instruction > `.worktrees/` > `worktrees/` > default `.worktrees/`); name derivation from artifact filename; Quick Reference situation→action table at `skills/isolating-worktrees/SKILL.md:83-95`; no merge-back procedure documented

### Pattern: Artifact frontmatter + provenance fields
- **Location:** `PLANS/2026-07-25-prd-to-plan-plan.md:1-11`
- **Snippet:**
  ```yaml
  ---
  artifact: implementation-plan
  date: 2026-07-25
  git_commit: e70aebac8416adba54f7adaac7c54c6b2c961eb7
  branch: master
  request: "@/home/dave/source/dangerpowers/PRDS/2026-07-25-prd-to-plan.md contains a PRD describing a new skill, which turns a prd into an execution plan. follow the process details described by the PRD and use this process to create the implementation plan."
  source_prd: PRDS/2026-07-25-prd-to-plan.md
  source_bundle: RESEARCH/2026-07-25-prd-to-plan-context-bundle.md
  source_research: RESEARCH/2026-07-25-prd-to-plan-research-findings.md
  status: approved
  ---
  ```
- **Key aspects:** common core `artifact/date/git_commit/branch/request/status`; provenance chain plan → `source_prd` + `source_bundle` + `source_research`

### Pattern: "Match the Form to the Failure" table (skill-authoring)
- **Location:** `skills/writing-skills/SKILL.md:65-70`
- **Snippet:**
  ```
  | Observed failure | Right form | Wrong form |
  |---|---|---|
  | Violates a rule it knows (discipline) | Prohibition + rationalization table + red flags | Soft guidance ("prefer...", "consider...") |
  | Complies but output has wrong shape | Positive recipe: state what the output IS — its parts, in order | Prohibition list ("don't restate", "never narrate") |
  | Omits a required element | Structural: REQUIRED field or slot in the template | Prose reminders near the template |
  | Behavior depends on a condition | Conditional on an observable predicate ("if the plan file exists, reference it") | Unconditional rule + exemption clauses |
  ```
- **Key aspects:** discipline skills get bulletproofing: explicit loophole closures, rationalization table, Red Flags list, violation symptoms in description (`skills/writing-skills/SKILL.md:78-108`)

### Testing Patterns
Tests are pressure-test campaign logs, not executable tests (`skills/writing-skills/references/pressure-testing.md`).

### Pattern: Test-campaign log structure
- **Location:** `skills/writing-skills/test-campaigns/2026-07-23-writing-skills.md:1-30`; canonical template at `skills/writing-skills/references/pressure-testing.md:140-166`
- **Snippet:**
  ```
  # Test Campaign: writing-skills — 2026-07-23

  First campaign run with the new pressure-testing system. Includes harness verification (from plan Task 1) and the dogfood campaign (plan Task 4).

  **Deviation from protocol:** 3 reps per variant instead of 5+, to bound token cost on the inaugural run. Treat marginal results as provisional.
  ```
  Per-scenario structure (from pressure-testing.md:140-166): `**Pressures:**` / `**Correct answer:**` / `### Baseline (no skill) — N runs` / `### With skill — N runs` / `### New rationalizations found` / `### Verdict`
- **Key aspects:** no YAML frontmatter; rationalizations recorded verbatim; verdicts "bulletproof" or "outstanding loopholes"; naming `skills/<skill>/test-campaigns/YYYY-MM-DD-<skill-name>[-fresh|-<topic>].md`

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
- **Key aspects:** heavy reference → `references/`, one level deep; cross-reference skills by name (`**REQUIRED SUB-SKILL:** use <name>`); test status lives only in `test-campaigns/`, never in SKILL.md (`skills/writing-skills/SKILL.md:140`)

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| Frontmatter (name + description) | `skills/writing-skills/SKILL.md:43-59`; every `skills/*/SKILL.md:1-4` |
| Delegation Safety + dispatch MUST list | `skills/prd-to-plan/SKILL.md:17-29` |
| Workflow with verification gates | `skills/prd-to-plan/SKILL.md:31-40` |
| Context Discipline + Red Flags | `skills/prd-to-plan/SKILL.md:42-55` |
| Subagent input contract + mode predicate | `skills/executing-plans/SKILL.md:10-22` |
| Report final-message contract | `skills/executing-plans/SKILL.md:90-102` |
| Iron Rules / file ownership | `skills/executing-plans/SKILL.md:24-42` |
| Rationalizations table | `skills/executing-plans/SKILL.md:44-54` |
| Red Flags - STOP | `skills/executing-plans/SKILL.md:56-63`; `skills/prd-to-plan/SKILL.md:46-55` |
| Worktree detect → create → setup → verify | `skills/isolating-worktrees/SKILL.md:10-95` |
| Artifact frontmatter + provenance | `PLANS/2026-07-25-prd-to-plan-plan.md:1-11`; `RESEARCH/2026-07-25-prd-to-plan-research-findings.md:1-10`; `RESEARCH/2026-07-25-prd-to-plan-context-bundle.md:1-10` |
| Test-campaign log | `skills/writing-skills/test-campaigns/2026-07-23-writing-skills.md:1-30`; `skills/writing-skills/references/pressure-testing.md:140-166` |
| Skill directory structure | `skills/writing-skills/SKILL.md:110-124` |

## 5. References & Usages

### `executing-plans` (skill)
- **Definition:** `skills/executing-plans/SKILL.md:1-106`
- **Call sites / dependents:** referenced as the per-phase executor by `AGENTS.md:15`; by `skills/isolating-worktrees/SKILL.md:8` ("executing-plans executors assume isolation is provided by the orchestration layer"); description at `skills/executing-plans/SKILL.md:3` covers subagent dispatch; the PRD `PRDS/2026-07-26-plan-to-execution.md` FR-002 makes it the executor for plan-to-execution

### `isolating-worktrees` (skill)
- **Definition:** `skills/isolating-worktrees/SKILL.md:1-95`
- **Call sites / dependents:** self-identifies as "the orchestration layer" for executing-plans executors (`skills/isolating-worktrees/SKILL.md:8`); referenced by the PRD request text as "isolating-worktrees skill" and in FR-006 as "the worktree-isolation skill"; no other skill file references it by name

### `prd-to-plan` (skill)
- **Definition:** `skills/prd-to-plan/SKILL.md:1-59`
- **Call sites / dependents:** referenced by `AGENTS.md:11` (orchestrates steps 3–5); boundary at `skills/prd-to-plan/SKILL.md:59` explicitly does not trigger execution — the gap plan-to-execution would fill; no skill file dispatches it

### `writing-plans` plan template
- **Definition:** `skills/writing-plans/references/plan-template.md:1-115`
- **Call sites / dependents:** consumed by executing-plans (`skills/executing-plans/SKILL.md:12-18,28,67-73`); produced by writing-plans (`skills/writing-plans/SKILL.md:56`)

### `<plan-base>-phase-<N>-report.md` naming convention
- **Definition:** `skills/executing-plans/SKILL.md:18`
- **Call sites / dependents:** report template at `skills/executing-plans/references/report-template.md:12-20`; existing reports `PLANS/2026-07-25-prd-to-plan-phase-1-report.md`, `PLANS/2026-07-25-prd-to-plan-phase-2-report.md`; `-plan` suffix rationale at `skills/writing-plans/references/plan-template.md:3`

### Phase-independence declaration
- **Definition:** no definition found — no frontmatter field or plan section declares phase independence (`skills/writing-plans/references/plan-template.md:10-20,54-82`)
- **Call sites / dependents:** parallel safety currently rests on disjoint per-phase file ownership (`skills/writing-plans/references/plan-template.md:114`; `skills/executing-plans/SKILL.md:28`; `AGENTS.md:15`); the PRD FR-005 requires the plan to declare independence

### Merge-back procedure for worktrees
- **Definition:** no definition found — isolating-worktrees documents create/setup/verify only (`skills/isolating-worktrees/SKILL.md:8`)
- **Call sites / dependents:** no callers found; the PRD FR-009 requires merge-back in plan order

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator (explore) | Map WHERE: all files under skills/, PRDS/, PLANS/, RESEARCH/, config/docs, naming conventions, directory counts | Complete; 40 files in skills/, full file map with roles and conventions |
| Analyzer (general) | Understand HOW: prd-to-plan, executing-plans, isolating-worktrees, writing-plans internals, skill discovery, plan-file fields | Complete; entry/exit points, data flow, delegation rules, resume/error mechanics, all cited file:line |
| Pattern-finder (general) | Find WHAT TO MODEL: skill-authoring conventions, orchestrator patterns, subagent scoping, worktree pattern, frontmatter, test-campaigns, Red Flags/Rationalizations formats | Complete; 13 patterns with working snippets and usage map |

## 7. Known Gaps

- **Phase-independence declaration format:** no plan-file field or section declares phase independence today; the PRD (FR-005) assumes the plan declares it. How that declaration is expressed (and whether writing-plans gains a convention for it) is undetermined by the current codebase.
- **Merge-back procedure:** isolating-worktrees documents worktree creation, setup, and verification only; no merge-back, integration, or conflict-handling procedure exists anywhere in the repo. The PRD (FR-009) requires merge-back in plan order with conflict stop-and-report.
- **Plan-level final test/audit commands:** the plan template has per-phase Automated Verification commands but no plan-level "final full test and audit" section; closest are `## Desired End State` verification and `## Testing Strategy` (`skills/writing-plans/references/plan-template.md:34-36,92-101`).
- **Resume-by-commit detection:** existing resume is report-file-based (`skills/executing-plans/SKILL.md:68`); the PRD (FR-011) requires detecting completed phases from commits. No existing mechanism maps commits to phases beyond report frontmatter `git_commit_start`/`git_commit_end`.
