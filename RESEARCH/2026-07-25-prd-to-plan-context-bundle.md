---
artifact: context-bundle
date: 2026-07-25
git_commit: e70aebac8416adba54f7adaac7c54c6b2c961eb7
branch: master
request: "create a prd to describe requirements for a new skill. this skill will be a planning and preparation skill orchestrator. it will guide the user and agent through: 1. input: PRD document and optional user prompt with additional instructions 2. using the researching-codebase skill to map out relevant parts of the codebase and design architecture 3. transitioning to the scouting-codebase skill and producing a context bundle for planning. this should be able to run in a subagent to avoid polluting the orchestrator's context window. 4. transitioning to the writing-plans skill to write the plan file 5. presenting the plan to the user and working together to iterate on the plan until the user accepts (accepts the plan report is ready for human review, not setting the 'status' of the plan document)."
source_research: RESEARCH/2026-07-25-prd-to-plan-research-findings.md
source_prd: PRDS/2026-07-25-prd-to-plan.md
status: complete
---

# Context Bundle

## 1. Goal

Create a new skill `prd-to-plan` under `skills/prd-to-plan/` that orchestrates the pipeline researching-codebase → scouting-context → writing-plans from a single invocation, delegates artifact-producing phases to subagents where safe, verifies each phase's artifact before advancing, asks before reusing pre-existing artifacts, and runs a plan feedback loop via iterating-plans until the user accepts the plan as ready for human review.

- **In scope:** orchestration of the four pipeline skills; subagent delegation with a nesting-safety check (PRD FR-003/FR-004); artifact-existence verification between phases (FR-005); existing-artifact reuse prompts (FR-006); pass-through of optional user instructions (FR-007); the present/iterate/accept loop (FR-008–FR-010); orchestrator context limited to artifact paths and phase outcomes (FR-011).
- **Out of scope:** PRD authoring, prompt-shaping, plan execution, any modification to the four pipeline skills, parallel phase execution, setting the plan's `status` field (PRD §2 Non-Goals, `PRDS/2026-07-25-prd-to-plan.md:26-31`).

## 2. Files Retrieved

- `skills/writing-skills/SKILL.md` (whole file; esp. L14-17, L34-51, L106, L110-142, L144-175) — the authoring contract every new skill must satisfy: placement, frontmatter rules, description rules, structure, pressure-test Iron Law, deploy checklist
- `skills/researching-codebase/SKILL.md:L44-71` — phase-1 skill's input contract (optional PRD, `source_prd`), output path convention, sub-agent spawning (L48-52), standalone boundary (L69-71)
- `skills/scouting-context/SKILL.md:L12-16,57-81` — phase-2 skill's input contract (research-findings path; `source_research: none` fallback), output path, no sub-agent spawning, standalone boundary
- `skills/writing-plans/SKILL.md:L12-16,53-58` — phase-3 skill's input contract (bundle path + optional PRD), phase-outline buy-in step, present-for-approval exit; no sub-agent spawning; read-only except plan file (L28)
- `skills/iterating-plans/SKILL.md:L12-17,56-97` — feedback-loop skill's two required inputs (plan path + requested edits), sub-agent staleness verification (L64), status reversion on edit (L29,89), boundary (L95-97)
- `skills/executing-plans/SKILL.md:L18-30,94-106` — the repo's only subagent-dispatch contract: mode predicate, report-path derivation, terminal status line for controllers, "orchestration layer" boundary language
- `skills/writing-skills/references/pressure-testing.md:L70` (per research findings §3) — verified mechanics: subagents do NOT auto-load skills; with-skill prompts must name the skill file path explicitly; parallel dispatch in one message works
- `AGENTS.md:L7-24` — pipeline order, artifact naming/provenance, skippability of steps 2–4, pressure-test pollution policy
- `PRDS/2026-07-25-prd-to-plan.md` (whole file) — FR-001 through FR-011, edge cases §7, success criteria §8

## 3. Entry / Exit Points

- **Entry:** skill invocation of `prd-to-plan` — inputs: PRD document path + optional free-text instructions (FR-001, `PRDS/2026-07-25-prd-to-plan.md:57`) → output: accepted plan at `PLANS/YYYY-MM-DD-<kebab>-plan.md`; side effects: writes up to three artifacts (research-findings, context-bundle, plan) via delegated phases, all committed to source control per `AGENTS.md:17`.
- **Exit (per delegated phase):** each pipeline skill ends when its own checklist passes and its artifact exists — researching-codebase scout-readiness checklist (`skills/researching-codebase/SKILL.md:57-67`), scouting-context bundle checklist (`skills/scouting-context/SKILL.md:67-77`), writing-plans plan checklist + presentation (`skills/writing-plans/SKILL.md:57-58,64-73`).
- **Exit (feedback iteration):** iterating-plans ends with a diff summary presented to the user (`skills/iterating-plans/SKILL.md:93,97`).
- **Exit (skill overall):** user acceptance concludes the skill; it does not set the plan's `status` field and does not trigger execution (FR-010, `PRDS/2026-07-25-prd-to-plan.md:66`).

## 4. Key Code

### Sub-agent spawning roles (phase 1 skill spawns its own — nesting-relevant)
- **Location:** `skills/researching-codebase/SKILL.md:48-52`
- **Code:**
  ```markdown
  3. Spawn parallel sub-agents in one message, one role each:
     - **Locator** (`explore`) — find WHERE: files grouped by purpose (implementation, tests, config, types, docs, entry points), full paths with one-line roles, directory file counts, naming conventions. No file contents.
     - **Analyzer** (`general`) — understand HOW: entry/exit points, data flow, key logic, error handling, configuration & flags. Every claim cited `file:line`.
     - **Pattern-finder** (`general`) — find WHAT TO MODEL: working snippets of similar implementations including test patterns. ALL variations, no recommendation.
  ```

### Subagent-mode predicate + controller status contract (only existing dispatch pattern)
- **Location:** `skills/executing-plans/SKILL.md:22`
- **Code:**
  ```markdown
  **Mode is determined by who gave you the report path.** A report path provided by a dispatching controller means subagent mode: the plan file is read-only and you report which criteria passed. If you are the interactive top-level agent executing for the user directly, you may check off that phase's Automated Verification items yourself.
  ```

### `question`-tool confirmation gate
- **Location:** `skills/writing-skills/SKILL.md:17`
- **Code:**
  ```markdown
  3. Otherwise, use the `question` tool to ask whether to accept the default `.opencode/skills/` or enter a specific path (e.g. `.agents/skills/` for cross-tool portability). Do not proceed until answered.
  ```

### SKILL.md frontmatter contract
- **Location:** `skills/writing-plans/SKILL.md:1-4`; rules at `skills/writing-skills/SKILL.md:45-51`
- **Code:**
  ```yaml
  ---
  name: writing-plans
  description: Use when research findings or a context bundle exist and an implementation plan is needed before changing code; also use when tempted to plan with unresolved open questions, write plan steps that say what to do without showing how, leave a pattern conflict unpicked, pick a side of a team-standard or vendor question on the strength of usage counts, or edit anything other than the plan file while planning. Keywords: implementation plan, plan, phases, PLANS, planning, plan approval.
  ---
  ```

### Cross-skill reference by name
- **Location:** `skills/writing-skills/SKILL.md:122`
- **Code:**
  ```markdown
  Cross-reference other skills by name (`**REQUIRED SUB-SKILL:** use <name>`) instead of repeating content.
  ```

## 5. References & Usages

### `researching-codebase`
- **Definition:** `skills/researching-codebase/SKILL.md:2`
- **Call sites / dependents:** pipeline step 3 (`AGENTS.md:11`); its artifact is scouting-context's primary input (`skills/scouting-context/SKILL.md:12`); iterating-plans forbids full re-runs of it (`skills/iterating-plans/SKILL.md:69`). Spawns sub-agents itself (`skills/researching-codebase/SKILL.md:48-52`).

### `scouting-context`
- **Definition:** `skills/scouting-context/SKILL.md:2`
- **Call sites / dependents:** pipeline step 4 (`AGENTS.md:12`); its artifact is writing-plans' primary input (`skills/writing-plans/SKILL.md:12`). Spawns no sub-agents.

### `writing-plans`
- **Definition:** `skills/writing-plans/SKILL.md:2`
- **Call sites / dependents:** pipeline step 5 (`AGENTS.md:13`); its checklist is re-run by iterating-plans (`skills/iterating-plans/SKILL.md:91`). Spawns no sub-agents.

### `iterating-plans`
- **Definition:** `skills/iterating-plans/SKILL.md:2`
- **Call sites / dependents:** pipeline step 6 (`AGENTS.md:14`); executing-plans' mismatch protocol routes humans to it (`skills/executing-plans/SKILL.md:88`). Spawns sub-agents itself (`skills/iterating-plans/SKILL.md:64,69`).

### Blast Radius
- **Likely to change:** none — the PRD's non-goals forbid modifying the pipeline skills (`PRDS/2026-07-25-prd-to-plan.md:30`); the work creates new files only: `skills/prd-to-plan/SKILL.md` (required, `skills/writing-skills/SKILL.md:110-122`), optional `skills/prd-to-plan/references/`, and `skills/prd-to-plan/test-campaigns/` per the Iron Law (`skills/writing-skills/SKILL.md:129-131`). `AGENTS.md`'s pipeline list (L7-15) currently has 7 entries and no orchestrator.
- **Must not break:** the four pipeline skills' standalone boundaries — researching-codebase (`skills/researching-codebase/SKILL.md:69-71`), scouting-context (`skills/scouting-context/SKILL.md:79-81`), iterating-plans (`skills/iterating-plans/SKILL.md:95-97`) each forbid the agent running them from auto-chaining into other skills; artifact contracts cited by downstream skills: findings path cited as `source_research` (`skills/scouting-context/references/bundle-template.md:16`), bundle path cited as `source_bundle` (`skills/writing-plans/references/plan-template.md:17`).
- **Transitive dependents worth attention:** executing-plans reads plan frontmatter `status` and stops on `draft` (`skills/executing-plans/SKILL.md:20`) — FR-010's prohibition on setting plan status keeps prd-to-plan consistent with this; iterating-plans reads plan provenance fields during iteration (`skills/iterating-plans/SKILL.md:56`), so phases must record provenance correctly for the feedback loop to work.

## 6. Patterns & Idioms

### Pattern: artifact path convention + provenance frontmatter
- **Location:** `AGENTS.md:17`; `skills/writing-plans/references/plan-template.md:9-20`
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
- **Key aspects:** `YYYY-MM-DD-<kebab>` filenames with type suffixes (`-research-findings.md`, `-context-bundle.md`, `-plan.md`); absent inputs recorded as `none`, never silently (`skills/scouting-context/SKILL.md:16`).

### Pattern: present-then-iterate approval loop
- **Location:** `skills/writing-plans/SKILL.md:58`; `skills/iterating-plans/SKILL.md:87-93`
- **Snippet:**
  ```markdown
  6. Present the plan location for approval. Iterate on feedback with surgical edits; do not rewrite the plan for a scoped change.
  ```
- **Key aspects:** iterating-plans adds staleness verification sub-agents, confirm-before-editing, checklist re-run, diff summary; no maximum-attempts cutoff exists in any loop in this repo.

### Pattern: description-field structure
- **Location:** all `skills/*/SKILL.md:3`; rules `skills/writing-skills/SKILL.md:48-51,106`
- **Key aspects:** 7 of 8 descriptions follow "Use when...; also use when tempted to...; Keywords: ...". Variations: project-bootstrap-nix uses "Trigger phrases include..." (`skills/project-bootstrap-nix/SKILL.md:3`); writing-skills has neither suffix (`skills/writing-skills/SKILL.md:3`).

### Conflicting Variations
- **Variation A — orchestrator runs phases inline:** every existing pipeline skill is written for the agent that loaded it to do the work in its own context (e.g. scouting-context's targeted reads in its own context, `skills/scouting-context/SKILL.md:58`; writing-plans reads the bundle fully, `skills/writing-plans/SKILL.md:53`). Evidence: 4 of 4 pipeline skills written this way.
- **Variation B — orchestrator dispatches phases to subagents:** PRD FR-003 requires subagent delegation for context isolation (`PRDS/2026-07-25-prd-to-plan.md:59`); the only in-repo dispatch mechanics are executing-plans' subagent-mode predicate (`skills/executing-plans/SKILL.md:22`) and the verified fact that subagents do NOT auto-load skills — prompts must name the skill file path explicitly (`skills/writing-skills/references/pressure-testing.md:70`).
- **Conflict:** the pipeline skills' standalone boundaries forbid the agent running them from chaining (`skills/researching-codebase/SKILL.md:69-71`, `skills/scouting-context/SKILL.md:79-81`, `skills/iterating-plans/SKILL.md:95-97`), while FR-002 requires the orchestrator to drive them in sequence. A subagent dispatched to run one phase is not "chaining" only if its prompt scopes it to that single phase — how the skill text reconciles the boundaries with orchestrated dispatch is a design decision with no in-repo precedent.

## 7. Testing

- **How similar code is tested:** no executable tests exist; the convention is pressure-test campaigns per `skills/writing-skills/SKILL.md:127-142` (RED baseline → GREEN with-skill → REFACTOR on new rationalizations), stored at `skills/<name>/test-campaigns/YYYY-MM-DD-<name>.md`. Format example `skills/executing-plans/test-campaigns/2026-07-25-executing-plans.md:1-5`:
  ```markdown
  # Test Campaign: executing-plans — 2026-07-25

  **Campaign limitation (read first):** GREEN-only. No RED (baseline) results are trusted. Baseline subagents spawned in this workspace auto-see the repo's `AGENTS.md` ...
  ```
  Campaign scenario sections target specific rules under combined pressures; status lives only in campaign logs, never in SKILL.md (`skills/writing-skills/SKILL.md:140`). Pollution policy: baselines must not see repo `AGENTS.md` or skill files (`AGENTS.md:19-24`).
- **Tests covering affected code:** none found for any skill (markdown-only repo); the new skill will need its own campaign per the Iron Law "NO SKILL WITHOUT A FAILING TEST FIRST" (`skills/writing-skills/SKILL.md:129-131`).
- **Validation commands:** none exist — no root `package.json` scripts, no Makefile, no CI config; `flake.nix:16-37` provides only a dev shell; `.opencode/package.json:1-5` has no scripts. Verification of skill artifacts is by checklist + pressure campaign, per `skills/writing-skills/SKILL.md:144-175`.

## 8. Constraints & Risks

- **Invariants the plan must respect:**
  - SKILL.md frontmatter is exactly `name` + `description`; description is when-to-use only, never a workflow summary (`skills/writing-skills/SKILL.md:45-51`).
  - New skills live under `skills/`, never per-project dirs (`AGENTS.md:1-3`).
  - Artifact paths must follow `YYYY-MM-DD-<kebab>` conventions because downstream skills cite them (`skills/researching-codebase/SKILL.md:54`).
  - Provenance fields must be recorded so iterating-plans can do staleness verification later (`skills/iterating-plans/SKILL.md:56`).
  - The orchestrator may not set plan `status` (FR-010) and must not modify the pipeline skills (PRD §2, `PRDS/2026-07-25-prd-to-plan.md:30`).
  - Iron Law: no skill without a failing pressure test first (`skills/writing-skills/SKILL.md:129-131`); campaigns must avoid baseline pollution from repo `AGENTS.md`/skill files (`AGENTS.md:19-24`).
- **Dependencies / ordering:** pipeline is strictly sequential (PRD §6, `PRDS/2026-07-25-prd-to-plan.md:76`); each phase's artifact feeds the next skill's declared input contract (`skills/scouting-context/SKILL.md:12`, `skills/writing-plans/SKILL.md:12`).
- **Likely failure modes:**
  - Nested subagents: researching-codebase and iterating-plans spawn their own sub-agents (`skills/researching-codebase/SKILL.md:48-52`, `skills/iterating-plans/SKILL.md:64`); whether a dispatched subagent can spawn further subagents is not documented in-repo and not answered by the opencode agents docs (they document per-agent `permission.task` gating Task-tool access and describe the general subagent as having "full tool access (except todo)", but do not state nesting support). FR-004 anticipates this with an inline fallback (`PRDS/2026-07-25-prd-to-plan.md:60`); edge case §7 requires noting the fallback to the user (`PRDS/2026-07-25-prd-to-plan.md:86`).
  - Skill loading in subagents: subagents do not auto-load skills; the dispatch prompt must name the skill file path explicitly (`skills/writing-skills/references/pressure-testing.md:70`).
  - Interactive skills inside subagents: writing-plans gets phase-outline buy-in from the user mid-workflow (`skills/writing-plans/SKILL.md:55`) and iterating-plans confirms before editing (`skills/iterating-plans/SKILL.md:87`) — user-interaction steps inside a subagent conflict with the context-isolation goal of FR-003/FR-011; PRD §8 SC-002 requires orchestrator context to hold only paths and outcomes.
  - Phase failure must surface, not advance silently (FR-005, edge cases `PRDS/2026-07-25-prd-to-plan.md:85`).
- **Conflicting findings:** the chaining-boundary conflict in §6 (standalone boundaries vs. FR-002 orchestration) — both sides cited there.

## 9. Open Questions

- `[needs-deeper-research]` — Does the opencode runtime support a subagent spawning its own sub-agents (nesting)? In-repo evidence and opencode docs are inconclusive (see §8). This determines whether researching-codebase and iterating-plans phases can ever be delegated or always run inline (FR-004).
- `[needs-human]` — When a delegated phase's skill contains mid-workflow user-interaction steps (writing-plans phase-outline buy-in, `skills/writing-plans/SKILL.md:55`; iterating-plans confirm-before-editing, `skills/iterating-plans/SKILL.md:87`), should the subagent ask the user directly, or should the orchestrator mediate? FR-011 limits orchestrator context but the PRD does not say who owns mid-phase questions.
- `[needs-human]` — Where do subagents for this repo's skills get dispatched from in practice: the orchestrating primary agent's Task tool (as in this session) is the only observed mechanism; no config in `.opencode/opencode.jsonc:1-16` defines custom subagents. Confirm that built-in `general` subagents are the intended dispatch target for phases.

## 10. Start Here

- **Start:** `skills/writing-skills/SKILL.md` — it is the governing contract for the only artifact this work produces (a new skill): frontmatter rules (L45-51), description rules (L48-51,106), directory structure (L110-122), the pressure-test Iron Law (L129-131), and the deploy checklist (L144-175). Every other design input (PRD FRs, pipeline contracts, dispatch mechanics) is constrained by what this file permits a skill to be.
