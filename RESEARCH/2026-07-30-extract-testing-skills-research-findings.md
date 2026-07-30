---
artifact: research-findings
date: 2026-07-30
git_commit: 5068d47cc65f6f04c56f0cab0e12054b64b91c3d
branch: dev/sloptime
request: turn this prd into a multi-phase plan @/home/dave/source/dangerpowers/PRDS/2026-07-30-extract-testing-skills.md
source_prd: PRDS/2026-07-30-extract-testing-skills.md
status: complete
---

# Research Findings

## 1. Request Summary

Plan a multi-phase implementation that extracts the pressure-testing and trigger-optimization processes out of the `writing-skills` skill into two new standalone skills (`pressure-testing`, `trigger-testing`), and revises `writing-skills` so it retains the testing mandates but never auto-launches campaigns, instead directing the user to invoke the new skills manually.

- **In scope:** creating `skills/pressure-testing/` and `skills/trigger-testing/`; extracting `skills/writing-skills/references/pressure-testing.md` and `references/trigger-optimizing.md`; revising `skills/writing-skills/SKILL.md` (Testing Discipline Skills section, Trigger Optimization section, testing checklist items); single-skill and sequential list-based campaign support in both new skills; description best-practice rules carried by `trigger-testing` (from `writing-skills` frontmatter guidance and https://agentskills.io/skill-creation/optimizing-descriptions).
- **Out of scope:** self-testing the two new skills; changing testing methodology substance; changing other skills; automating/scheduling campaign execution.

## 2. File Map

### Implementation
- `skills/writing-skills/SKILL.md` — the skill being revised; contains the two testing mandate sections and the testing checklist blocks
- `skills/writing-skills/references/pressure-testing.md` — pressure-testing process reference; extraction source for the new `pressure-testing` skill
- `skills/writing-skills/references/trigger-optimizing.md` — trigger-optimization process reference; extraction source for the new `trigger-testing` skill
- `agents/eval-reader.md` — read-only agent definition used by pressure-test with-skill runs
- `agents/trigger-evaluator.md` — trigger-evaluation agent definition; its JSON detection pattern matches `trigger-optimizing.md:85,88`
- `AGENTS.md` — repo operating rules; references the pressure-testing reference file at line 13
- `NOTES.md` — root doc; mentions pressure testing at lines 95 and 107

### Tests
- `skills/writing-skills/test-campaigns/` — exists, empty (0 files)
- `skills/researching-codebase/test-campaigns/2026-07-29-researching-codebase.md` — campaign log example
- `skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md` — campaign log example with `-01` same-day disambiguation
- `skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md` — campaign log example with hoisted h2 verdict sections
- 11 of 13 skills have `test-campaigns/` directories (all except `project-bootstrap-nix`); `scouting-context/test-campaigns/` is empty
- No `trigger-evals/` directory exists anywhere in the repo; no file with the `-trigger` suffix exists in the working tree or git history

### Configuration
- `pyproject.toml` — declares dependency `skills-ref>=0.1.1` (line 9), which provides the `agentskills` CLI
- `uv.lock` — pins `skills-ref` 0.1.1 (lines 88–97)
- `flake.nix` — devShell shellHook runs `which agentskills || $(uv sync && uv python install)` (line 38)
- `.venv/bin/agentskills` — generated console-script entry point (`from skills_ref.cli import main`)
- `.opencode/opencode.jsonc` — opencode config; no `agentskills` reference

### Type Definitions
- None (markdown-only skill content; `trigger-evals/*.json` files are JSON arrays of `{"query": "<str>", "should_trigger": <bool>}` per `skills/writing-skills/references/trigger-optimizing.md:185`)

### Documentation
- `README.md` — human-edited overview
- `PRDS/2026-07-30-extract-testing-skills.md` — the source PRD (status: approved)
- `PLANS/` — exists, empty
- `RESEARCH/` — created by this effort

### Entry Points
- `skills/writing-skills/SKILL.md:1-4` — frontmatter (name, description); the skill's load surface
- `skills/writing-skills/SKILL.md:153` — `**REQUIRED:**` pointer to `references/pressure-testing.md`
- `skills/writing-skills/SKILL.md:168` — `**REQUIRED:**` pointer to `references/trigger-optimizing.md`
- `skills/writing-skills/references/pressure-testing.md:3` — `**Load this reference when:**` reciprocal pointer
- `skills/writing-skills/references/trigger-optimizing.md:3` — `**Load this reference when:**` reciprocal pointer

### Related Directories
- `skills/` — 13 skill directories; naming convention kebab-case verb-first (`writing-skills`, `executing-plans`); each contains exactly one `SKILL.md`
- `skills/*/references/` — present in 6 skills (`researching-codebase`, `scouting-context`, `writing-plans`, `writing-prds`, `executing-plans`, `writing-skills`); exactly one reference file per skill except `writing-skills` (2 files); naming: kebab-case descriptive or `<artifact>-template.md`
- `.opencode/skills/dangerpowers` — symlink to `../../skills`; `.opencode/agents/dangerpowers` — symlink to `../../agents` (per `AGENTS.md:9`, commit real files, never symlinks)
- `agents/` — 2 files, kebab-case `.md` agent definitions

## 3. Implementation Analysis

- **Overview:** `writing-skills` is a single SKILL.md (211 lines) with two reference files. Testing content lives in: the `## Testing Discipline Skills` section (`skills/writing-skills/SKILL.md:138-153`), the `## Trigger Optimization` section (`skills/writing-skills/SKILL.md:155-168`), the `**Testing (discipline skills only):**` checklist block (`skills/writing-skills/SKILL.md:197-203`), the `**Trigger Optimization:**` checklist block (`skills/writing-skills/SKILL.md:205-211`), and the two reference files in full.
- **Entry points:** `skills/writing-skills/SKILL.md:3` — the frontmatter `description` is the routing surface that causes the skill to load; `skills/writing-skills/SKILL.md:153` and `:168` — the two `**REQUIRED:**` load instructions that pull the reference files into an authoring run.
- **Exit points:** `skills/writing-skills/SKILL.md:170-211` — the `## Checklist` section ends the skill; there is no Boundary section. The checklist's testing items (`skills/writing-skills/SKILL.md:198-200`) instruct the agent to perform campaign steps (run baseline scenarios, re-run with skill, close loopholes).
- **Data flow:**
  1. `skills/writing-skills/SKILL.md:140` — the Iron Law (`NO SKILL WITHOUT A FAILING TEST FIRST`) mandates a failing baseline before any discipline rule.
  2. `skills/writing-skills/SKILL.md:142` — the mandate prescribes RED → GREEN → REFACTOR performed during authoring.
  3. `skills/writing-skills/SKILL.md:153` — the author is directed to `references/pressure-testing.md` for scenario design, execution protocol, meta-testing, done criteria, results-log format.
  4. `skills/writing-skills/references/pressure-testing.md:70-101` — the execution protocol dispatches `opencode run` baseline and with-skill reps.
  5. `skills/writing-skills/references/pressure-testing.md:172-198` — results are logged to `test-campaigns/YYYY-MM-DD-<skill-name>.md` in the skill under test's directory.
  6. `skills/writing-skills/SKILL.md:157` — the Trigger Eval Rule (`NO DESCRIPTION SHIPS WITHOUT A PASSING EVAL SET`) mandates a passing eval set for every skill's description.
  7. `skills/writing-skills/SKILL.md:168` — the author is directed to `references/trigger-optimizing.md` for eval query design, train/validation split, the ≤3-iteration loop, harness, contamination rules, done criteria, log format.
  8. `skills/writing-skills/references/trigger-optimizing.md:76-114` — the opencode NDJSON harness detects candidate skill loads via `"tool":"skill"` + `input.name`.
  9. `skills/writing-skills/references/trigger-optimizing.md:153,185` — trigger campaigns log to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` and eval sets live in `trigger-evals/` beside `test-campaigns/`.
- **Key logic:**
  - Mandates retained per the PRD: Iron Law at `skills/writing-skills/SKILL.md:140`, Trigger Eval Rule at `skills/writing-skills/SKILL.md:157`, untested-recording rules at `skills/writing-skills/SKILL.md:149` and `:166`, status-never-in-SKILL.md rule at `skills/writing-skills/SKILL.md:151`.
  - Reference-skill exemption: `skills/writing-skills/SKILL.md:149` exempts pure-reference skills from pressure testing; `skills/writing-skills/references/trigger-optimizing.md:12` states reference skills are NOT exempt from trigger evals.
  - Cross-references inside the extraction sources that point back at `writing-skills` (these become cross-skill references after extraction):
    - `skills/writing-skills/references/pressure-testing.md:123` — "follow 'Match the Form to the Failure' in SKILL.md" (the section at `skills/writing-skills/SKILL.md:72`)
    - `skills/writing-skills/references/trigger-optimizing.md:12` — cites `SKILL.md:138–149` for the reference-skill exemption
    - `skills/writing-skills/references/trigger-optimizing.md:74` — cites `SKILL.md:53` (weave trigger terms, no labeled keyword list)
    - `skills/writing-skills/references/trigger-optimizing.md:135` — cites `SKILL.md:3` (the live description line)
    - `skills/writing-skills/references/trigger-optimizing.md:181` — cites `SKILL.md:151` (status-only-in-test-campaigns rule)
    - `skills/writing-skills/references/trigger-optimizing.md:92` — sibling citation "matching `pressure-testing.md`'s inline bash pattern"
    - `skills/writing-skills/references/trigger-optimizing.md:153` — sibling citation "the existing campaign log format (which lives at `pressure-testing.md:172`)"
  - References into the extraction sources from outside `writing-skills`:
    - `AGENTS.md:13` — `When running pressure test campaigns (see `skills/writing-skills/references/pressure-testing.md`)` — a full path into the file slated for removal
    - `NOTES.md:95` and `NOTES.md:107` — prose mentions of pressure testing (no path reference)
  - Description best-practice rules currently in `writing-skills` frontmatter guidance: `skills/writing-skills/SKILL.md:48-53` (imperative "Use when...", WHAT + WHEN, no workflow summary, concise, trigger terms woven into prose), `skills/writing-skills/SKILL.md:63-68` (YAML safety: colon-in-scalar pitfall, 1024-char limit), `skills/writing-skills/SKILL.md:70` (`agentskills validate` gate).
- **Error handling:** the void-run convention at `skills/writing-skills/references/pressure-testing.md:91` (a rep that attempts a skill-tool load or emits only permission errors is void and re-dispatched); contamination rules at `skills/writing-skills/references/trigger-optimizing.md:116-120` and `skills/writing-skills/references/pressure-testing.md:155-159` (verify global `~/.config/opencode/AGENTS.md` empty/absent; sibling description visibility is expected, not contamination — mirrors `AGENTS.md:11-16`).
- **Configuration & flags:** `opencode run --dir <empty-dir-outside-repo>` strips skill descriptions for baselines (`skills/writing-skills/references/pressure-testing.md:78-80`); `--pure` has no effect on this contamination source (`skills/writing-skills/references/pressure-testing.md:80`); with-skill reps run with repo cwd and `--agent eval-reader` (`skills/writing-skills/references/pressure-testing.md:87-90`); trigger harness uses `--format json` (`skills/writing-skills/references/trigger-optimizing.md:80-82`); `agentskills validate skills/<name>` must print `Valid skill` (`skills/writing-skills/SKILL.md:70`).

## 4. Patterns & Idioms

### Pattern: standalone skill with references/ (anatomy)
- **Location:** `skills/researching-codebase/SKILL.md:1-4,82,97-99`
- **Snippet:**
  ```markdown
  ---
  name: researching-codebase
  description: Use when asked to research, explore, map, or explain how part of a codebase works, find where features live, locate entry points or call sites, or gather code context before planning. Also use when about to answer codebase questions from memory or a single grep, or to flag problems and suggest improvements while researching. Covers "how does X work" exploration without unsolicited improvement notes.
  ---
  ```
- **Key aspects:** two-field frontmatter; section skeleton `# Title`, `## The Iron Rules` (with `### Rationalizations`, `### Red Flags - STOP`), `## Workflow`, checklist section, `## Standalone Boundary`; reference file pointed at from a workflow step (`skills/researching-codebase/SKILL.md:82`).

### Pattern: SKILL.md ↔ reference reciprocal pointers
- **Location:** `skills/writing-skills/SKILL.md:153`, `skills/writing-skills/references/pressure-testing.md:3`
- **Snippet:**
  ```markdown
  **REQUIRED:** See `references/pressure-testing.md` for scenario design, execution protocol, meta-testing, done criteria, and the results-log format.
  ```
  ```markdown
  **Load this reference when:** creating or editing a discipline-enforcing skill, before deployment.
  ```
- **Key aspects:** bolded `**REQUIRED:**` callout at end of a body section; reference opens with a `**Load this reference when:**` line. Variation: `skills/researching-codebase/SKILL.md:82` and `skills/writing-plans/SKILL.md:64` name the reference inline in a numbered workflow step; `skills/executing-plans/SKILL.md:96` names it inside a contract section.

### Pattern: frontmatter description styles
- **Location:** `skills/scouting-context/SKILL.md:3`, `skills/prompt-shaping/SKILL.md:3`, `skills/project-bootstrap-nix/SKILL.md:3`, `skills/executing-plans/SKILL.md:3`
- **Snippet:**
  ```yaml
  description: Use when preparing to plan a code change and needing to compress research findings into a handoff brief — affected files, call sites, blast radius, constraints, risks, validation commands, and where to start. Also use when a research findings document exists and needs to become actionable context, or when about to embed a recommended approach in the handoff, pick one of two competing patterns for the planner, or ship a handoff brief with empty sections. Covers pre-planning context bundles.
  ```
- **Key aspects:** all open with "Use when..." or "Use to..."; variations include "Also use when about to..." violation-symptom triggers (scouting-context, writing-plans, writing-quick-plans), "Does not apply when..." boundary clauses (`skills/prompt-shaping/SKILL.md:3`), and `Triggers include "..."` quoted-phrase lists (`skills/project-bootstrap-nix/SKILL.md:3`, `skills/writing-skills/SKILL.md:3`).

### Pattern: sequential list processing
- **Location:** `skills/plan-to-execution/SKILL.md:45-52,59-63`
- **Snippet:**
  ```markdown
  Run before dispatching anything. For each phase in plan order, check ALL of:

  - The report file `PLANS/<plan-base>-phase-<N>-report.md` exists.
  - Its frontmatter `status` is `DONE` or `DONE_WITH_CONCERNS`.
  - Its frontmatter `git_commit_end` is a full commit hash.
  - `git merge-base --is-ancestor <hash> HEAD` exits 0.
  ```
- **Key aspects:** iterate the list in order, one item at a time; per-item completion artifacts verified before advancing. Variation for multi-skill trigger campaigns: `skills/writing-skills/references/trigger-optimizing.md:133-137` (Multi-Skill Campaigns section with Final-Verification regression smoke) and the checklist encoding at `skills/writing-skills/SKILL.md:211`.

### Pattern: opencode-run evaluation harness
- **Location:** `skills/writing-skills/references/pressure-testing.md:76-90`, `skills/writing-skills/references/trigger-optimizing.md:80-90`
- **Snippet:**
  ```bash
  opencode run --dir <empty-dir-outside-repo> "<scenario>"
  ```
  ```bash
  opencode run --dir <repo-root> --agent eval-reader "$(cat prepend.txt scenario.txt)"
  ```
- **Key aspects:** baseline strips skill descriptions via external `--dir`; with-skill uses repo cwd + `eval-reader` agent; trigger detection greps NDJSON for `"tool":"skill"` + `"name":"<candidate>"` and must be candidate-specific (`skills/writing-skills/references/trigger-optimizing.md:88-90`).

### Pattern: skill boundary declarations
- **Location:** `skills/researching-codebase/SKILL.md:97-99`, `skills/plan-to-execution/SKILL.md:101-103`, `skills/writing-prds/SKILL.md:52`
- **Snippet:**
  ```markdown
  ## Standalone Boundary

  This skill ends when the checklist passes. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the artifact.
  ```
- **Key aspects:** variations: dedicated `## Standalone Boundary` / `## Boundary` final section (researching-codebase, executing-plans, plan-to-execution) vs. boundary as a workflow step (writing-prds). `writing-skills` currently has neither a Boundary nor a Red Flags section; it ends on `## Checklist` (`skills/writing-skills/SKILL.md:170`).

### Testing Patterns
- **Campaign log template** — `skills/writing-skills/references/pressure-testing.md:172-198`:
  ```markdown
  # Test Campaign: <skill-name> — <date>

  ## Scenario 1: <name>
  **Pressures:** <list>
  **Correct answer:** <option>

  ### Baseline (no skill) — N runs
  - Run 1: chose <X>. Rationalization: "<verbatim>"

  ### With skill — N runs
  - Run 1: chose <X>. Cited: "<section>". Notes: ...

  ### New rationalizations found
  - "<verbatim>" → counter added: <where>

  ### Verdict
  <bulletproof | outstanding loopholes: ...>
  ```
- **Real log skeleton** — `skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md:1,3,7,14,21,150`: `# Test Campaign: prompt-shaping — 2026-07-29`, per-scenario `### Baseline (no skill) — N runs` / `### With skill — N runs` / `### New rationalizations found`, final `## Verdict`. Variation: `skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md:96-101` hoists `## New rationalizations found` and `## Verdict` to h2 and uses variable run counts.
- **Trigger log sections** — `skills/writing-skills/references/trigger-optimizing.md:151-179`: `## Trigger evals` with per-iteration blocks (description verbatim, train/validation pass rates, train failures, revision rationale, selected iteration) and `## Fresh-query sanity check`.
- **Filename conventions** — `test-campaigns/YYYY-MM-DD-<skill-name>.md` (`skills/writing-skills/references/pressure-testing.md:174`); `-trigger` suffix for trigger campaigns (`skills/writing-skills/references/trigger-optimizing.md:153`); observed `-01` same-day disambiguation in two current files with no defining rule text.

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| `**REQUIRED:**` reference pointer | `skills/writing-skills/SKILL.md:153`, `skills/writing-skills/SKILL.md:168` |
| `**Load this reference when:**` opener | `skills/writing-skills/references/pressure-testing.md:3`, `skills/writing-skills/references/trigger-optimizing.md:3` |
| By-name cross-skill reference | `skills/prd-to-plan/SKILL.md:8`, `skills/plan-to-execution/SKILL.md:8`, `skills/executing-plans/SKILL.md:20`, `skills/writing-quick-plans/SKILL.md:8` |
| Boundary section | `skills/researching-codebase/SKILL.md:97`, `skills/executing-plans/SKILL.md:108`, `skills/plan-to-execution/SKILL.md:101`, `skills/writing-prds/SKILL.md:52` |
| Campaign log title | `skills/writing-skills/references/pressure-testing.md:179`, `skills/writing-plans/test-campaigns/2026-07-29-writing-plans.md:1` |

## 5. References & Usages

### `references/pressure-testing.md`
- **Definition:** `skills/writing-skills/references/pressure-testing.md:1`
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:153` (REQUIRED load instruction); `AGENTS.md:13` (full-path reference in "Pressure Test Pollution" section); `skills/writing-skills/references/trigger-optimizing.md:92` (sibling bash-pattern citation); `skills/writing-skills/references/trigger-optimizing.md:153` (sibling log-format citation); `agents/eval-reader.md:1-4` (agent the protocol dispatches, referenced at `skills/writing-skills/references/pressure-testing.md:87-90`)

### `references/trigger-optimizing.md`
- **Definition:** `skills/writing-skills/references/trigger-optimizing.md:1`
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:168` (REQUIRED load instruction); `agents/trigger-evaluator.md:32,37` (detection pattern matches `trigger-optimizing.md:85,88`); no other repo references found

### `## Testing Discipline Skills` (writing-skills section)
- **Definition:** `skills/writing-skills/SKILL.md:138-153`
- **Call sites / dependents:** `skills/writing-skills/references/trigger-optimizing.md:12` (cites the `SKILL.md:138–149` line range for the reference-skill exemption); checklist block at `skills/writing-skills/SKILL.md:197-203`

### `## Trigger Optimization` (writing-skills section)
- **Definition:** `skills/writing-skills/SKILL.md:155-168`
- **Call sites / dependents:** checklist block at `skills/writing-skills/SKILL.md:205-211`; `skills/writing-skills/references/trigger-optimizing.md:181` (extends the `SKILL.md:151` rule)

### `agentskills validate`
- **Definition:** `.venv/bin/agentskills:1-13` (console script from `skills-ref` package, `pyproject.toml:9`)
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:65`, `skills/writing-skills/SKILL.md:70`, `skills/writing-skills/SKILL.md:183`, `skills/writing-skills/SKILL.md:195`

### `agents/eval-reader.md`
- **Definition:** `agents/eval-reader.md:1-4`
- **Call sites / dependents:** `skills/writing-skills/references/pressure-testing.md:87-90`

### `agents/trigger-evaluator.md`
- **Definition:** `agents/trigger-evaluator.md:1-4`
- **Call sites / dependents:** detection pattern paralleled at `skills/writing-skills/references/trigger-optimizing.md:85,88`; no explicit by-name invocation found in the reference file's prose

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator (explore) | Map skills/ layout, writing-skills contents, test-campaigns/trigger-evals presence, repo conventions, .opencode symlinks, validation tooling, naming conventions | Complete; all 7 areas reported with full paths |
| Analyzer (general) | Trace all references to the two reference files, SKILL.md testing section ranges and checklist items, back-references from reference files, cross-skill invocation patterns, agentskills validate, log conventions | Complete; all 6 areas reported with file:line citations |
| Pattern-finder (general) | Exemplars for skill anatomy, description styles, sequential list processing, dispatch harnesses, results logs, boundary conventions | Complete; all 6 areas reported with verbatim snippets |

## 7. Known Gaps

- The external description-optimization guidance at https://agentskills.io/skill-creation/optimizing-descriptions was not fetched during research (PRD FR-007 requires its content be incorporated into `trigger-testing`; the content itself is external, not part of this codebase).
- No rule text defines the `-01` same-day disambiguation variant in campaign log filenames; only two observed instances.
- `RESEARCH/` did not exist before this effort; this file is its first entry.
