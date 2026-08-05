---
artifact: research-findings
date: 2026-08-05
git_commit: 94a7a06099b91b9d8f8291a41a826b76ef45765a
branch: dev/sloptime
request: "write a plan based on this prd @/home/dave/source/dangerpowers/PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md"
source_prd: PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md
status: complete
---

# Research Findings

## 1. Request Summary

Produce a plan to merge the `pressure-testing` skill into the `writing-skills` skill per the PRD: one skill covering authoring and pressure-testing, campaign-execution content moved to an on-demand reference file, opt-in end-of-flow prompts for pressure testing and trigger eval, deletion of the `pressure-testing` directory, and verification via a pressure-test campaign plus a clean-context review.

- **In scope:** `skills/writing-skills/` and `skills/pressure-testing/` directories in full; cross-references between them; repo skill-structure conventions (`references/` on-demand loading, branching workflows, opt-in prompts); git history of the original split.
- **Out of scope:** `trigger-testing` content/structure changes; references to `pressure-testing` in other skills' files, docs, PLANS/, PRDS/, RESEARCH/; pressure-testing methodology changes beyond consolidation.

## 2. File Map

### Implementation
- `skills/writing-skills/SKILL.md` — skill definition for authoring skills (190 lines)
- `skills/pressure-testing/SKILL.md` — skill definition for pressure-test campaigns (223 lines)

### Tests
- `skills/writing-skills/test-campaigns/2026-07-30-writing-skills.md` — pressure-test campaign report for writing-skills
- `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md` — trigger-test campaign report for writing-skills
- `skills/pressure-testing/test-campaigns/2026-07-30-pressure-testing.md` — pressure-test campaign report for pressure-testing itself
- `skills/pressure-testing/test-campaigns/2026-07-30-trigger-testing.md` — pressure-test campaign report for trigger-testing (stored under pressure-testing's directory)
- `skills/pressure-testing/test-campaigns/2026-08-03-pressure-testing-trigger.md` — trigger-test campaign report for pressure-testing

### Configuration
- `skills/writing-skills/trigger-evals/train.json` — trigger-eval training split
- `skills/writing-skills/trigger-evals/validation.json` — trigger-eval validation split
- `skills/pressure-testing/trigger-evals/train.json` — trigger-eval training split
- `skills/pressure-testing/trigger-evals/validation.json` — trigger-eval validation split

### Type Definitions
- None.

### Documentation
- `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md` — the approved PRD driving this work
- `PLANS/2026-07-30-extract-testing-skills-plan.md` — plan for the original split of writing-skills into three skills

### Entry Points
- `skills/writing-skills/SKILL.md:3` — frontmatter `description` trigger; workflow begins at Overview/Placement (`skills/writing-skills/SKILL.md:14-17`)
- `skills/pressure-testing/SKILL.md:3` — frontmatter `description` trigger; workflow begins at Workflow step 1 (`skills/pressure-testing/SKILL.md:16`)

### Related Directories
- `skills/writing-skills/` — 5 files; root = 1, `test-campaigns/` = 2, `trigger-evals/` = 2; no `references/` directory
- `skills/pressure-testing/` — 6 files; root = 1, `test-campaigns/` = 3, `trigger-evals/` = 2; no `references/` directory
- `skills/trigger-testing/` — `SKILL.md`, `scripts/`, `test-campaigns/`, `trigger-evals/` (top-level only; content out of scope)
- Skills with a `references/` directory: `executing-plans` (`report-template.md`), `researching-codebase` (`findings-template.md`), `scouting-context` (`bundle-template.md`), `writing-plans` (`plan-template.md`), `writing-prds` (`prd-template.md`)
- `RESEARCH/` naming convention: `YYYY-MM-DD-<topic-slug>-research-findings.md` / `YYYY-MM-DD-<topic-slug>-context-bundle.md`
- `PLANS/` naming convention: `YYYY-MM-DD-<topic-slug>-plan.md`, `YYYY-MM-DD-<topic-slug>-phase-N-report.md`

### Files containing "pressure-testing" / "pressure testing" (excl. `.git`, `.venv`, `.worktrees`)
- Inside `skills/writing-skills/`: `SKILL.md`, `test-campaigns/2026-08-04-writing-skills-trigger.md`, `trigger-evals/train.json`
- Inside `skills/pressure-testing/`: all 6 files except `trigger-evals/validation.json`
- Inside other skills: `skills/trigger-testing/SKILL.md`
- Elsewhere: `README.md`, `NOTES.md`, `agents/eval-reader.md`, 10 files under `PLANS/`, 3 files under `PRDS/`, 4 files under `RESEARCH/`
- `AGENTS.md` contains no match.

## 3. Implementation Analysis

- **Overview:** Two skills describe one intertwined process. `writing-skills` (190 lines) covers skill authoring: overview/placement, when to create, skill types, frontmatter rules, form-to-failure matching, bulletproofing, structure, testing handoff, trigger optimization, checklist. `pressure-testing` (223 lines) covers campaign execution: workflow, scope, RED-GREEN-REFACTOR, scenario design, execution protocol, micro-tests, rationalization plugging, meta-testing, done criteria, lessons, mistakes, multi-skill campaigns, results-log template, boundary.

### writing-skills/SKILL.md
- **Entry points:** `skills/writing-skills/SKILL.md:3` — description trigger; `:14-17` — Placement decision before writing anything; `:41` — skill-type classification.
- **Exit points:** `:154-190` — flow ends at the Checklist; final items are deployment validation (`:179`, `agentskills validate` prints `Valid skill`) and handoff directions telling the user to run `pressure-testing` (`:182`) and `trigger-testing` (`:188`) manually; authoring performs no campaign or eval steps (`:185`, `:190`).
- **Data flow:**
  1. `:14-17` — decide skill file placement (prompt > repo AGENTS.md > `question` tool)
  2. `:32-41` — classify skill type (Technique, Pattern, Reference, Discipline)
  3. `:43-70` — write frontmatter per name/description rules; validate with `agentskills validate skills/<name>` (`:70`)
  4. `:121-136` — structure `skills/<name>/` directory; heavy reference to `references/` one level deep (`:132`)
  5. `:138-144` — Testing Discipline Skills: Iron Law "NO SKILL WITHOUT A FAILING TEST FIRST" (`:140`); RED-GREEN-REFACTOR (`:142`); agent does not run testing, directs user to `pressure-testing` manually (`:144`)
  6. `:146-152` — Trigger Optimization: "NO DESCRIPTION SHIPS WITHOUT A PASSING EVAL SET" (`:148`); directs user to `trigger-testing` manually (`:152`)
  7. `:154-190` — run the Checklist; end
- **Key logic — instructions about interpreting/acting on pressure-test results:**
  - `:72-86` — "Match the Form to the Failure": failure-type → guidance-form table (`:76-81`); no nuance clauses / exemption clauses (`:83-85`)
  - `:88-119` — "Bulletproofing Discipline Skills": explicit loophole closure (`:92-100`), spirit-vs-letter cutoff (`:101-104`), rationalization table (`:105-110`), red-flags list (`:111-116`), violation symptoms in description (`:117`)
  - `:142` — RED-GREEN-REFACTOR including REFACTOR re-runs
  - `:171`, `:182-185` — checklist items tying authoring to campaign outcomes
- **Error handling:** `:63-70` — Description YAML safety (colon-in-plain-scalar pitfall, 1024-char limit, validation command).
- **Configuration & flags:** Frontmatter fields are exactly `name` and `description` (`:1-4`).

### pressure-testing/SKILL.md
- **Entry points:** `skills/pressure-testing/SKILL.md:3` — description trigger; `:14` — input is one target skill name or a list; `:16` — step 1 reads target `SKILL.md` fully and checks Scope.
- **Exit points:** `:21` — write results log per target skill; `:22`, `:191` — advance through skill lists sequentially, log must exist before advancing; `:223` — Standalone Boundary, skill ends when logs are written, no chaining. Early exits: no violable rule → say so and move on (`:16`, `:35`); baseline shows no failure → stop (`:18`, `:114`, `:125`).
- **Data flow:**
  1. `:16` — read target SKILL.md fully; check Scope (`:24-35`)
  2. `:37-45` — RED-GREEN-REFACTOR phase table
  3. `:47-85` — scenario design: 5 rules, 7 pressure types (`:58-66`), example scenario (`:70-83`)
  4. `:87-118` — execution protocol: baseline dispatch with `--dir <empty-dir>` (`:91-97`), no `--pure` (`:97`), smoke test (`:99`), with-skill prepend + `eval-reader` agent (`:100-107`), void runs (`:108`), contamination reporting (`:110`), 5+ reps (`:112`), baseline first (`:114`), manual output reading (`:116`), variance metric (`:118`)
  5. `:120-129` — micro-tests at wording level
  6. `:131-140` — plugging rationalizations: four counters per excuse (`:135-138`); counter-form choice defers to writing-skills' "Match the Form to the Failure" (`:140`)
  7. `:142-155` — meta-testing question and three-way answer classification
  8. `:157-168` — done criteria (bulletproof vs outstanding loopholes)
  9. `:193-219` — results log written per template; log is the only place test status lives (`:197`)
- **Key logic — duplication/cross-reference with writing-skills:**
  - Baseline-first principle: `skills/pressure-testing/SKILL.md:8`, `:114` ↔ `skills/writing-skills/SKILL.md:12`
  - RED-GREEN-REFACTOR: `skills/pressure-testing/SKILL.md:37-43` ↔ `skills/writing-skills/SKILL.md:140-142`
  - Rationalization counters: `skills/pressure-testing/SKILL.md:133-138` ↔ `skills/writing-skills/SKILL.md:105-117`
  - Named cross-reference: `skills/pressure-testing/SKILL.md:140` — "follow 'Match the Form to the Failure' in the writing-skills skill" ↔ `skills/writing-skills/SKILL.md:72-86`
  - Spirit-vs-letter: `skills/pressure-testing/SKILL.md:153` ↔ `skills/writing-skills/SKILL.md:101-104`
  - No test status in SKILL.md: `skills/pressure-testing/SKILL.md:197` ↔ `skills/writing-skills/SKILL.md:183-184`
  - Untested-content prohibition: `skills/pressure-testing/SKILL.md:45` ↔ `skills/writing-skills/SKILL.md:12`, `:142`
- **Error handling:** `:170-176` — Campaign-Execution Lessons (silent permission auto-rejection `:174`, baseline cwd check `:175`, with-skill cwd asymmetry `:176`); `:178-187` — Common Mistakes table.
- **Configuration & flags:** Frontmatter fields are exactly `name` and `description` (`:1-4`). No mentions of trigger-testing or trigger evals in the file body.

### Campaign-log format
- Naming: `test-campaigns/YYYY-MM-DD-<skill-name>.md`; same-day collision → `YYYY-MM-DD-NN-<skill-name>.md` (`skills/pressure-testing/SKILL.md:195`)
- No frontmatter; H1 `# Test Campaign: <skill-name> — <date>` (`skills/pressure-testing/test-campaigns/2026-07-30-pressure-testing.md:1`)
- Sections per template (`skills/pressure-testing/SKILL.md:199-219`): `## Scenario N: <name>` with `**Pressures:**` / `**Correct answer:**`; `### Baseline (no skill) — N runs`; `### With skill — N runs`; `### New rationalizations found`; `### Verdict`
- Trigger campaign logs use `YYYY-MM-DD-<skill-name>-trigger.md` with sections `## Trigger evals`, `## Fresh-query sanity check`, `## Summary` (`skills/writing-plans/test-campaigns/2026-08-04-writing-plans-trigger.md`)

## 4. Patterns & Idioms

### Pattern: on-demand reference file loaded from a workflow step
- **Location:** `skills/researching-codebase/SKILL.md:82`, `skills/scouting-context/SKILL.md:64`, `skills/writing-plans/SKILL.md:64`, `skills/writing-prds/SKILL.md:49`, `skills/executing-plans/SKILL.md:96`
- **Snippet (researching-codebase):**
  ```markdown
  5. Write the artifact per `references/findings-template.md`. Location: `RESEARCH/YYYY-MM-DD-<kebab-description>-research-findings.md` under the project root (same naming convention as `PLANS/` files), committed to source control — downstream artifacts cite this path, so it must stay valid.
  ```
- **Key aspects:** no standalone "load on demand" section; the reference is named inline in the workflow step that uses it; paths are relative to the skill's own directory. The convention is defined in `skills/writing-skills/SKILL.md:127` ("references/ # Heavy reference (100+ lines), loaded on demand") and `:132` (one level deep from SKILL.md).
- **Variation:** `skills/writing-quick-plans/SKILL.md:25` references another skill's reference file via cross-skill relative path (`writing-plans/references/plan-template.md`).

### Pattern: conditional workflow branching on invocation reason
- **Location:** `skills/writing-prds/SKILL.md:47`, `skills/executing-plans/SKILL.md:22`, `skills/pressure-testing/SKILL.md:14-16`, `skills/prd-to-plan/SKILL.md:35`
- **Snippet (writing-prds):**
  ```markdown
  1. **Intake & grounding** — if the user names an existing PRD file, that file is the PRD: read it in full as your grounding, keep its path, and run every later step as a revision of it (reset `status: draft`). Otherwise restate the feature request; scan the repo for context that informs scope...
  ```
- **Snippet (pressure-testing):**
  ```markdown
  Input: one target skill name, or a list of target skills.
  1. Read the target skill's `SKILL.md` fully. Check Scope — if the skill has no violable rule, pressure testing does not apply; say so and move on.
  ```
- **Key aspects:** branch stated at the first workflow step; each branch names its condition and its procedure; missing-input branches stop or ask.

### Pattern: opt-in user gate via the question tool
- **Location:** `skills/project-bootstrap-nix/SKILL.md:52-53`, `skills/prd-to-plan/SKILL.md:35`, `skills/iterating-plans/SKILL.md:78`
- **Snippet (project-bootstrap-nix):**
  ```markdown
  3. Interview the user for optional extras using the `question` tool. Ask each question below and act on the answers:
  - **Create a default opencode config?** Ask using the `question` tool (Yes/No). If yes, create `.opencode/opencode.jsonc` with these contents:
  ```
- **Key aspects:** each optional follow-on is its own Yes/No question; "no" continues or ends the flow without the extra.

### Pattern: frontmatter shape
- **Location:** every SKILL.md in the repo (15 files)
- **Snippet (writing-skills):**
  ```yaml
  ---
  name: writing-skills
  description: Use when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo's skills/ directory. Triggers include "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills".
  ---
  ```
- **Key aspects:** exactly two fields, `name` and `description`, in all 15 skills.

### Testing Patterns
- **Discipline campaign log** — `skills/writing-plans/test-campaigns/2026-07-29-writing-plans.md`; headers: `# Test Campaign: <name> — <date>`, `## Scenario N: <name>`, `### Baseline (no skill) — 5 runs`, `### With skill — 5 runs`, `### New rationalizations found`, `### Verdict`
- **Trigger campaign log** — `skills/writing-plans/test-campaigns/2026-08-04-writing-plans-trigger.md`; headers: `## Trigger evals`, `### Iteration N`, `### Selected iteration: ...`, `## Fresh-query sanity check`, `## Summary`

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| On-demand reference | `skills/researching-codebase/SKILL.md:82`, `skills/scouting-context/SKILL.md:64`, `skills/writing-plans/SKILL.md:64`, `skills/writing-prds/SKILL.md:49`, `skills/executing-plans/SKILL.md:96` |
| Conditional workflow branch | `skills/writing-prds/SKILL.md:47`, `skills/executing-plans/SKILL.md:22`, `skills/pressure-testing/SKILL.md:14-16`, `skills/trigger-testing/SKILL.md:14`, `skills/plan-to-execution/SKILL.md:21-24` |
| Opt-in question gate | `skills/project-bootstrap-nix/SKILL.md:52-53`, `skills/prd-to-plan/SKILL.md:35`, `skills/iterating-plans/SKILL.md:78` |
| Two-field frontmatter | all 15 `skills/*/SKILL.md:1-4` |

## 5. References & Usages

### `writing-skills` (skill)
- **Definition:** `skills/writing-skills/SKILL.md:2`
- **Call sites / dependents:** `skills/pressure-testing/SKILL.md:140` (named cross-reference to its "Match the Form to the Failure" section); `skills/writing-skills/trigger-evals/train.json` (trigger queries); `skills/trigger-testing/SKILL.md` (mentions pressure testing, not writing-skills directly — no direct dependent found); README.md/NOTES.md mentions (documentation, out of scope)

### `pressure-testing` (skill)
- **Definition:** `skills/pressure-testing/SKILL.md:2`
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:144`, `:182` (handoff directions); `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md`; `skills/writing-skills/trigger-evals/train.json`; `skills/trigger-testing/SKILL.md`; `README.md`; `NOTES.md`; `agents/eval-reader.md`; 10 `PLANS/` files; 3 `PRDS/` files; 4 `RESEARCH/` files

### "Match the Form to the Failure" (section)
- **Definition:** `skills/writing-skills/SKILL.md:72-86`
- **Call sites / dependents:** `skills/pressure-testing/SKILL.md:140`

### `eval-reader` (agent)
- **Definition:** `agents/eval-reader.md`
- **Call sites / dependents:** `skills/pressure-testing/SKILL.md:100-107` (with-skill run evaluation)

### Git history of the original split (2026-07-30, per `git log`)
- `634fb99` — "Phase 1: create pressure-testing skill extracted from writing-skills" — created `skills/pressure-testing/SKILL.md` (223 lines); no deletions
- `3db50ae` / `ae4f817` — created `skills/trigger-testing/SKILL.md` (218 lines)
- `6163c31` — "Phase 3: revise writing-skills pointers/checklists, remove extracted references, update AGENTS.md" — deleted `skills/writing-skills/references/pressure-testing.md` (-198 lines) and `skills/writing-skills/references/trigger-optimizing.md` (-185 lines); edited `skills/writing-skills/SKILL.md` and `AGENTS.md`
- No SKILL.md file or whole skill directory has ever been deleted in repo history; one directory move exists (`ba39b6a`, `.opencode/skills/` → `skills/`)

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator | Map both skill directories, find all "pressure-testing" mentions repo-wide, list references/ conventions and RESEARCH/PLANS naming | Complete; full file inventories and cross-reference groupings returned |
| Analyzer | Read both SKILL.md files fully; outline sections; identify duplication pairs, entry/exit points, campaign-log format | Complete; section outlines with line ranges and 8 duplication/cross-reference pairs with citations on both sides |
| Pattern-finder | Find on-demand reference, branching, opt-in gate, frontmatter, campaign-log patterns; git history of splits/deletions | Complete; verbatim snippets with citations; git history of the 2026-07-30 split recovered |

## 7. Known Gaps

- The exact content of `skills/trigger-testing/SKILL.md` was not analyzed in depth (out of scope per PRD); only its mention of "pressure testing" is recorded. The plan's cross-reference fixes (FR-009) are limited to the merged skill's own files per PRD §7, so this gap does not block planning.
- `skills/writing-skills/trigger-evals/train.json` and `validation.json` contents were not read; their existence and role are recorded. Whether the merged skill's description change (FR-006) requires eval-set updates is a planning decision, not a research gap — the PRD states no separate trigger-eval campaign is required.
