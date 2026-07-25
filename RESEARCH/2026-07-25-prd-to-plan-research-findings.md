---
artifact: research-findings
date: 2026-07-25
git_commit: e70aebac8416adba54f7adaac7c54c6b2c961eb7
branch: master
request: "create a prd to describe requirements for a new skill. this skill will be a planning and preparation skill orchestrator. it will guide the user and agent through: 1. input: PRD document and optional user prompt with additional instructions 2. using the researching-codebase skill to map out relevant parts of the codebase and design architecture 3. transitioning to the scouting-codebase skill and producing a context bundle for planning. this should be able to run in a subagent to avoid polluting the orchestrator's context window. 4. transitioning to the writing-plans skill to write the plan file 5. presenting the plan to the user and working together to iterate on the plan until the user accepts (accepts the plan report is ready for human review, not setting the 'status' of the plan document)."
source_prd: PRDS/2026-07-25-prd-to-plan.md
status: complete
---

# Research Findings

## 1. Request Summary

Research the dangerpowers skills repository as it exists today, scoped to what is needed to create a new orchestrator skill named `prd-to-plan` that drives the pipeline researching-codebase → scouting-context → writing-plans, delegates phases to subagents, and runs a plan feedback loop via iterating-plans.

- **In scope:** the four pipeline skills (researching-codebase, scouting-context, writing-plans, iterating-plans) and their input/output contracts; executing-plans as the repo's only existing subagent-dispatch reference; writing-skills authoring conventions; repo layout, artifact naming, and provenance conventions; which skills spawn sub-agents (nesting-safety relevant).
- **Out of scope:** PRD authoring, prompt-shaping, plan execution, any changes to existing skills, pressure-test campaign design details beyond convention documentation.

## 2. File Map

### Implementation
- `/home/dave/source/dangerpowers/skills/researching-codebase/SKILL.md` — pipeline skill: produces `RESEARCH/<date>-<name>-research-findings.md` via parallel specialist sub-agents
- `/home/dave/source/dangerpowers/skills/scouting-context/SKILL.md` — pipeline skill: compresses research into `RESEARCH/<date>-<name>-context-bundle.md`
- `/home/dave/source/dangerpowers/skills/writing-plans/SKILL.md` — pipeline skill: produces `PLANS/<date>-<name>-plan.md`
- `/home/dave/source/dangerpowers/skills/iterating-plans/SKILL.md` — pipeline skill: applies human review edits to an existing plan; verifies facts via sub-agents
- `/home/dave/source/dangerpowers/skills/executing-plans/SKILL.md` — pipeline skill: executes one plan phase per invocation; the repo's only subagent-mode/dispatcher contract
- `/home/dave/source/dangerpowers/skills/writing-skills/SKILL.md` — authoring conventions for new skills
- `/home/dave/source/dangerpowers/skills/writing-prds/SKILL.md` — produces `PRDS/<date>-<name>.md`
- `/home/dave/source/dangerpowers/skills/prompt-shaping/SKILL.md` — confirms scope of vague requests
- `/home/dave/source/dangerpowers/skills/project-bootstrap-nix/SKILL.md` — bootstraps new projects; only skill with a `scripts/` dir

### Tests
- No executable tests exist in this repo. Each skill instead has `test-campaigns/` pressure-test records (plain markdown, no frontmatter): 16 files total across all 8 skills, named `YYYY-MM-DD-<skill-name>.md` and `YYYY-MM-DD-<skill-name>-fresh.md`. Example: `/home/dave/source/dangerpowers/skills/executing-plans/test-campaigns/2026-07-25-executing-plans.md`.
- New skill `prd-to-plan`: no test-campaigns exist (skill does not exist yet).

### Configuration
- `/home/dave/source/dangerpowers/.opencode/opencode.jsonc` — opencode config
- `/home/dave/source/dangerpowers/flake.nix`, `flake.lock`, `.envrc` — Nix dev shell
- `/home/dave/source/dangerpowers/.gitignore` — git ignore rules (`RESEARCH/` is NOT gitignored per `AGENTS.md:17`)

### Type Definitions
- None (markdown-only repository).

### Documentation
- `/home/dave/source/dangerpowers/AGENTS.md` — repo instructions: pipeline overview, artifact naming, provenance rules
- `/home/dave/source/dangerpowers/README.md` — 78-byte readme
- `/home/dave/source/dangerpowers/NOTES.md` — notes; line 8 expresses intent to "start orchestrating workflows with skills and subagents"
- `/home/dave/source/dangerpowers/EXAMPLE_AGENT_RULES.md` — example agent rules
- Reference templates: `skills/researching-codebase/references/findings-template.md`, `skills/scouting-context/references/bundle-template.md`, `skills/writing-plans/references/plan-template.md`, `skills/executing-plans/references/report-template.md`, `skills/writing-prds/references/prd-template.md`, `skills/writing-skills/references/pressure-testing.md`

### Entry Points
- Each skill's entry point is its `SKILL.md`, invoked via the skill tool; frontmatter `description:` field is the trigger (`skills/writing-skills/SKILL.md:45-51`).
- The planned skill's input PRD: `/home/dave/source/dangerpowers/PRDS/2026-07-25-prd-to-plan.md` (the only file in `PRDS/`).

### Related Directories
- `/home/dave/source/dangerpowers/skills/` — 8 skill directories; convention: exactly one `SKILL.md` per directory, optional `references/` (named `*-template.md`, except writing-skills' `pressure-testing.md`), `test-campaigns/`, and (only project-bootstrap-nix) `scripts/`
- `/home/dave/source/dangerpowers/PRDS/` — 1 file; naming `YYYY-MM-DD-<kebab>.md` (no suffix)
- `/home/dave/source/dangerpowers/PLANS/` — empty; documented pattern `PLANS/<date>-<name>-plan.md`, reports `<plan-base>-phase-<N>-report.md`
- `/home/dave/source/dangerpowers/RESEARCH/` — does not exist; documented patterns `<date>-<name>-research-findings.md`, `<date>-<name>-context-bundle.md`, `<date>-<name>-spec.md`
- No `skills/prd-to-plan/` directory exists.

## 3. Implementation Analysis

- **Overview:** The repo is a markdown skill library. The pipeline is a documented sequence (`AGENTS.md:7-15`) with no orchestrator; handoff between skills is artifact-based only, via provenance frontmatter fields (`AGENTS.md:17`). Every pipeline skill has an explicit standalone boundary forbidding auto-invocation or chaining: researching-codebase (`skills/researching-codebase/SKILL.md:69-71`), scouting-context (`skills/scouting-context/SKILL.md:79-81`), iterating-plans (`skills/iterating-plans/SKILL.md:95-97`), writing-prds (`skills/writing-prds/SKILL.md:52`). writing-plans has no chain-prohibition section but is read-only except its plan file (`skills/writing-plans/SKILL.md:28`).
- **Entry points:** A skill is entered by invocation through the skill tool; the `description:` frontmatter field is the selection trigger (`skills/writing-skills/SKILL.md:45-51`). Each pipeline skill's workflow begins by reading its input artifact: researching-codebase reads user-mentioned files fully before spawning sub-agents (`skills/researching-codebase/SKILL.md:46`); scouting-context ingests a research-findings path plus the original request (`skills/scouting-context/SKILL.md:12,57`); writing-plans reads a context-bundle path plus request (`skills/writing-plans/SKILL.md:12,53`); iterating-plans reads the plan file fully (`skills/iterating-plans/SKILL.md:56`).
- **Exit points:** Each skill ends when its checklist passes and its artifact is presented: researching-codebase scout-readiness checklist (`skills/researching-codebase/SKILL.md:57-67,71`); scouting-context bundle checklist (`skills/scouting-context/SKILL.md:67-77,81`); writing-plans plan checklist plus presentation for approval (`skills/writing-plans/SKILL.md:57-58,64-73`); iterating-plans ends with a diff summary presented to the user (`skills/iterating-plans/SKILL.md:93,97`).
- **Data flow:**
  1. `AGENTS.md:9-15` — pipeline order: prompt-shaping (optional spec) → writing-prds (`PRDS/<date>-<name>.md`) → researching-codebase (`RESEARCH/<date>-<name>-research-findings.md`) → scouting-context (`RESEARCH/<date>-<name>-context-bundle.md`) → writing-plans (`PLANS/<date>-<name>-plan.md`) → iterating-plans → executing-plans.
  2. `skills/scouting-context/SKILL.md:12` — scouting-context consumes the research-findings path; records `source_research` and `source_prd` (`skills/scouting-context/references/bundle-template.md:10-20`).
  3. `skills/writing-plans/SKILL.md:12-16` — writing-plans consumes the bundle path and optional PRD; records `source_prd`, `source_bundle`, `source_research` (`skills/writing-plans/references/plan-template.md:9-20`).
  4. `skills/iterating-plans/SKILL.md:56` — iterating-plans reads the plan and its provenance artifacts (`source_prd`, `source_bundle`, `source_research`).
  5. `AGENTS.md:17` — steps 2–4 of the pipeline are skippable when the input they produce already exists.
- **Key logic (sub-agent spawning, per skill):**
  - researching-codebase spawns parallel sub-agents itself: Locator (`explore`), Analyzer (`general`), Pattern-finder (`general`), "in one message" (`skills/researching-codebase/SKILL.md:48-52`); waits for all (`:53`); checklist failures route to "a targeted follow-up sub-agent" (`:55`).
  - iterating-plans spawns parallel ad hoc sub-agents for staleness verification — "`explore` for existence/location checks, `general` for symbol and command verification" (`skills/iterating-plans/SKILL.md:64`); evidentiary edits use "more targeted sub-agent research — never a full re-run of researching-codebase" (`:69`).
  - scouting-context and writing-plans spawn no sub-agents (no spawn instructions anywhere in either file; scouting-context uses targeted searches/reads in its own context, `skills/scouting-context/SKILL.md:58`).
  - executing-plans defines the repo's only subagent-mode contract: "Mode is determined by who gave you the report path" (`skills/executing-plans/SKILL.md:22`); parallel executor safety via per-phase file ownership (`:28`); plan file read-only in subagent mode (`:30`); it explicitly does not dispatch further ("do not dispatch anything... belong to the orchestration layer", `:104-106`).
  - Subagents do not auto-load skills: the with-skill prompt must name the skill file path explicitly; parallel dispatch in one message works (`skills/writing-skills/references/pressure-testing.md:70`).
- **Error handling:**
  - Missing input artifact: scouting-context proceeds anyway, records `source_research: none`, fills sections with its own reads, notes thin evidence as `[needs-deeper-research]` in §9; "Never demand the user run another skill first" (`skills/scouting-context/SKILL.md:16`). writing-plans likewise records `source_bundle: none` and resolves thin evidence in its workflow step 2 (`skills/writing-plans/SKILL.md:16`).
  - Checklist failure: researching-codebase ships `status: partial` only with §7 explanation (`skills/researching-codebase/SKILL.md:55`); scouting-context ships `status: partial` with §9 entry (`skills/scouting-context/SKILL.md:65`).
  - executing-plans' mismatch protocol reports BLOCKED with a structured template and routes humans to iterating-plans when the plan has drifted (`skills/executing-plans/SKILL.md:75-88`).
  - iterating-plans reverts `status: approved` to `draft` on any edit (`skills/iterating-plans/SKILL.md:29,89`) and offers to route back through scouting-context/researching-codebase when an edit invalidates bundle assumptions (`skills/iterating-plans/SKILL.md:69`).
- **Configuration & flags:** Artifact frontmatter status fields act as state flags: findings/bundle `status: complete | partial` (`skills/researching-codebase/references/findings-template.md:17`); plan `status: draft | approved` (`skills/writing-plans/references/plan-template.md:20`); executing-plans stops if the plan is `status: draft` (`skills/executing-plans/SKILL.md:20`). Report `status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT` (`skills/executing-plans/references/report-template.md:18`).

## 4. Patterns & Idioms

### Pattern: SKILL.md frontmatter (name + description only)
- **Location:** `skills/writing-plans/SKILL.md:1-4`; all 8 skills identical in shape; rules at `skills/writing-skills/SKILL.md:45-51`
- **Snippet:**
  ```yaml
  ---
  name: writing-plans
  description: Use when research findings or a context bundle exist and an implementation plan is needed before changing code; also use when tempted to plan with unresolved open questions, write plan steps that say what to do without showing how, leave a pattern conflict unpicked, pick a side of a team-standard or vendor question on the strength of usage counts, or edit anything other than the plan file while planning. Keywords: implementation plan, plan, phases, PLANS, planning, plan approval.
  ---
  ```
- **Key aspects:** Only `name` and `description` are permitted (`skills/writing-skills/SKILL.md:45`). Description is third person, when-to-use only, starts "Use when...", continues "also use when tempted to...", ends "Keywords: ..."; never summarizes the workflow (`skills/writing-skills/SKILL.md:48-51,106`). Name is lowercase/hyphens, gerund/verb-first (`skills/writing-skills/SKILL.md:47`). Variation: project-bootstrap-nix uses "Trigger phrases include..." instead of "Keywords:" (`skills/project-bootstrap-nix/SKILL.md:3`); writing-skills has neither suffix (`skills/writing-skills/SKILL.md:3`).

### Pattern: parallel sub-agent spawning (specialist roles)
- **Location:** `skills/researching-codebase/SKILL.md:48-52`
- **Snippet:**
  ```markdown
  3. Spawn parallel sub-agents in one message, one role each:
     - **Locator** (`explore`) — find WHERE: files grouped by purpose (implementation, tests, config, types, docs, entry points), full paths with one-line roles, directory file counts, naming conventions. No file contents.
     - **Analyzer** (`general`) — understand HOW: entry/exit points, data flow, key logic, error handling, configuration & flags. Every claim cited `file:line`.
     - **Pattern-finder** (`general`) — find WHAT TO MODEL: working snippets of similar implementations including test patterns. ALL variations, no recommendation.
     Tell each agent WHAT to find, not HOW to search. Restate the documentarian rules in every prompt.
  ```
- **Key aspects:** Roles typed by subagent kind (`explore` vs `general`); one message for parallel dispatch; orchestrator waits for all (`skills/researching-codebase/SKILL.md:53`). iterating-plans variation: ad hoc verification sub-agents rather than fixed roles (`skills/iterating-plans/SKILL.md:64`).

### Pattern: subagent-mode predicate (skill runs as the dispatched subagent)
- **Location:** `skills/executing-plans/SKILL.md:22`
- **Snippet:**
  ```markdown
  **Mode is determined by who gave you the report path.** A report path provided by a dispatching controller means subagent mode: the plan file is read-only and you report which criteria passed. If you are the interactive top-level agent executing for the user directly, you may check off that phase's Automated Verification items yourself.
  ```
- **Key aspects:** The dispatched subagent is told its mode by an input artifact (report path), not by a flag; parallel safety comes from disjoint file ownership (`skills/executing-plans/SKILL.md:28`) and read-only shared state (`:30`). The subagent returns a terminal status line (`DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`) because "the controller acts on it directly" (`skills/executing-plans/SKILL.md:94-102`).

### Pattern: user confirmation via the `question` tool
- **Location:** `skills/writing-skills/SKILL.md:17`; `skills/project-bootstrap-nix/SKILL.md:52-53`; `skills/writing-prds/SKILL.md:48`
- **Snippet:**
  ```markdown
  3. Otherwise, use the `question` tool to ask whether to accept the default `.opencode/skills/` or enter a specific path (e.g. `.agents/skills/` for cross-tool portability). Do not proceed until answered.
  ```
- **Key aspects:** Blocking gate — "Do not proceed until answered." Variation: iterating-plans presents a confirm-before-editing block with a literal template message (`skills/iterating-plans/SKILL.md:71-87`). Variation: writing-plans gets phase-outline buy-in before writing details (`skills/writing-plans/SKILL.md:55`).

### Pattern: artifact naming + provenance frontmatter
- **Location:** `skills/writing-plans/references/plan-template.md:9-20`; `AGENTS.md:17`
- **Snippet:**
  ```markdown
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
- **Key aspects:** Filenames `YYYY-MM-DD-<kebab>` with type suffixes (`-research-findings.md`, `-context-bundle.md`, `-plan.md`, `-phase-N-report.md`); `RESEARCH/` committed, not gitignored; "downstream artifacts cite this path, so it must stay valid" (`skills/researching-codebase/SKILL.md:54`). Absent inputs are recorded as `none`, never silently skipped (`skills/scouting-context/SKILL.md:16`, `skills/writing-plans/SKILL.md:16`).

### Pattern: present-then-iterate approval loop
- **Location:** `skills/writing-plans/SKILL.md:58`; `skills/writing-prds/SKILL.md:51`
- **Snippet:**
  ```markdown
  6. Present the plan location for approval. Iterate on feedback with surgical edits; do not rewrite the plan for a scoped change.
  ```
- **Key aspects:** Presentation is of the artifact location, not inline content; edits are surgical. iterating-plans' full loop adds staleness verification, confirm-before-editing, checklist re-run, and a diff summary (`skills/iterating-plans/SKILL.md:87-93`).

### Pattern: standalone boundary (no auto-chaining)
- **Location:** `skills/researching-codebase/SKILL.md:69-71`
- **Snippet:**
  ```markdown
  ## Standalone Boundary

  This skill ends when the checklist passes. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the artifact.
  ```
- **Key aspects:** Present in researching-codebase, scouting-context (`skills/scouting-context/SKILL.md:79-81`), iterating-plans (`skills/iterating-plans/SKILL.md:95-97`), writing-prds (`skills/writing-prds/SKILL.md:52`). These boundaries bind the agent running that skill; cross-skill handoff today is user-driven.

### Pattern: cross-skill reference by name
- **Location:** `skills/writing-skills/SKILL.md:122`
- **Snippet:**
  ```markdown
  Cross-reference other skills by name (`**REQUIRED SUB-SKILL:** use <name>`) instead of repeating content.
  ```
- **Key aspects:** Skills cite each other by name rather than duplicating instructions.

### Testing Patterns
No executable tests exist. The repo's verification convention is pressure-test campaigns under `skills/<name>/test-campaigns/YYYY-MM-DD-<name>.md`:
- **Location:** `skills/executing-plans/test-campaigns/2026-07-25-executing-plans.md:1-5`; governing rules `skills/writing-skills/SKILL.md:127-142`
- **Snippet:**
  ```markdown
  # Test Campaign: executing-plans — 2026-07-25

  **Campaign limitation (read first):** GREEN-only. No RED (baseline) results are trusted. Baseline subagents spawned in this workspace auto-see the repo's `AGENTS.md` ...
  ```
- **Key aspects:** Plain markdown, no frontmatter. Sections: `## Scenario N: <name> (targets "<rule>")` with `**Pressures:**`, `**Correct answer:**`, `### Baseline (no skill)`, `### With skill`, `### New rationalizations found`, `### Verdict`; ends with `## Campaign summary`. Iron Law: "NO SKILL WITHOUT A FAILING TEST FIRST" for new skills and discipline-rule edits (`skills/writing-skills/SKILL.md:129-131`); test status lives only in test-campaigns, never in SKILL.md (`skills/writing-skills/SKILL.md:140`). Baseline pollution rules in `AGENTS.md:19-24`.

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| name+description frontmatter | all 8 `skills/*/SKILL.md:1-4` |
| parallel specialist sub-agents | `skills/researching-codebase/SKILL.md:48-53` |
| ad hoc verification sub-agents | `skills/iterating-plans/SKILL.md:64,69` |
| subagent-mode predicate | `skills/executing-plans/SKILL.md:22,28,30` |
| `question`-tool confirmation gate | `skills/writing-skills/SKILL.md:17`, `skills/project-bootstrap-nix/SKILL.md:52-53`, `skills/writing-prds/SKILL.md:48` |
| artifact naming + provenance | `AGENTS.md:17`, all `skills/*/references/*-template.md` |
| present-then-iterate loop | `skills/writing-plans/SKILL.md:58`, `skills/writing-prds/SKILL.md:51`, `skills/iterating-plans/SKILL.md:87-93` |
| standalone boundary | `skills/researching-codebase/SKILL.md:69-71`, `skills/scouting-context/SKILL.md:79-81`, `skills/iterating-plans/SKILL.md:95-97`, `skills/writing-prds/SKILL.md:52` |
| cross-skill reference by name | `skills/writing-skills/SKILL.md:122` |

## 5. References & Usages

### `researching-codebase` (skill)
- **Definition:** `skills/researching-codebase/SKILL.md:2`
- **Call sites / dependents:** listed as pipeline step 3 in `AGENTS.md:11`; consumed by scouting-context's input contract (`skills/scouting-context/SKILL.md:12`); iterating-plans forbids full re-runs of it (`skills/iterating-plans/SKILL.md:69`); PRD FR-002 designates it pipeline phase 1 (`PRDS/2026-07-25-prd-to-plan.md:58`). No orchestrator invokes it today.

### `scouting-context` (skill)
- **Definition:** `skills/scouting-context/SKILL.md:2`
- **Call sites / dependents:** pipeline step 4 in `AGENTS.md:12`; consumed by writing-plans' input contract (`skills/writing-plans/SKILL.md:12`); iterating-plans offers routing back through it (`skills/iterating-plans/SKILL.md:69`); PRD FR-002 designates it pipeline phase 2.

### `writing-plans` (skill)
- **Definition:** `skills/writing-plans/SKILL.md:2`
- **Call sites / dependents:** pipeline step 5 in `AGENTS.md:13`; its checklist is re-run by iterating-plans (`skills/iterating-plans/SKILL.md:91`); PRD FR-002 designates it pipeline phase 3.

### `iterating-plans` (skill)
- **Definition:** `skills/iterating-plans/SKILL.md:2`
- **Call sites / dependents:** pipeline step 6 in `AGENTS.md:14`; executing-plans' mismatch protocol routes humans to it (`skills/executing-plans/SKILL.md:88`); PRD FR-009 designates it the plan-feedback mechanism.

### `writing-skills` (skill)
- **Definition:** `skills/writing-skills/SKILL.md:2`
- **Call sites / dependents:** governs creation of any new skill under `skills/` (checklist at `skills/writing-skills/SKILL.md:144-175`); no skill references it by name.

### `source_prd` / `source_bundle` / `source_research` (frontmatter fields)
- **Definition:** `AGENTS.md:17`; templates at `skills/writing-plans/references/plan-template.md:16-18`, `skills/scouting-context/references/bundle-template.md:16-17`, `skills/researching-codebase/references/findings-template.md:16`
- **Call sites / dependents:** read by iterating-plans during staleness verification (`skills/iterating-plans/SKILL.md:56`).

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator | Full file map of repo, skills/ layout, naming conventions, references/ contents per pipeline skill | Complete; confirmed no `skills/prd-to-plan/` and no `RESEARCH/` dir exist |
| Analyzer | How each pipeline skill works: inputs, outputs, entry/exit, sub-agent spawning, chaining rules, orchestration mechanisms | Complete; identified exactly two sub-agent-spawning skills (researching-codebase, iterating-plans) and the absence of any orchestrator |
| Pattern-finder | Verbatim snippets: frontmatter, sub-agent spawning, user-question, artifact conventions, feedback loops, descriptions, test-campaign format | Complete; 7 pattern families with verbatim snippets and file:line locations |

## 7. Known Gaps

- Whether the opencode runtime supports nested sub-agents (a subagent spawning its own sub-agents) is not determinable from this repository; the only in-repo evidence is the verified mechanics note that subagents do not auto-load skills and parallel dispatch works (`skills/writing-skills/references/pressure-testing.md:70`). PRD FR-004's safety check must account for this unknown.
- No prior example exists of a skill whose role is to invoke other skills; the executing-plans "orchestration layer" is named (`skills/executing-plans/SKILL.md:106`) but not implemented, so there is no in-repo controller pattern to trace call sites for.
