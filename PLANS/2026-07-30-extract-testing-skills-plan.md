---
artifact: implementation-plan
date: 2026-07-30
git_commit: 5068d47cc65f6f04c56f0cab0e12054b64b91c3d
branch: dev/sloptime
request: turn this prd into a multi-phase plan
source_prd: PRDS/2026-07-30-extract-testing-skills.md
source_bundle: RESEARCH/2026-07-30-extract-testing-skills-context-bundle.md
source_research: RESEARCH/2026-07-30-extract-testing-skills-research-findings.md
status: approved
---

# Extract Pressure-Testing and Trigger-Testing into Standalone Skills Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

The `writing-skills` skill currently bundles three concerns: authoring guidance, the pressure-testing campaign process, and the trigger-description optimization process. The two testing processes live as reference files inside `writing-skills`, which instructs the agent to launch testing campaigns automatically during skill authoring. Testing campaigns are expensive (dozens of subagent dispatches), and the processes are also useful outside the authoring flow. This plan extracts each testing process into its own standalone, manually invocable skill (`pressure-testing`, `trigger-testing`), and revises `writing-skills` so it retains the testing mandates (Iron Law, Trigger Eval Rule) at full force but never auto-launches campaigns — it directs the user to run the new skills manually.

## Current State

- `skills/writing-skills/SKILL.md` (211 lines) holds: the Iron Law (`:140`) and Trigger Eval Rule (`:157`) mandates; the pure-reference exemption and untested-recording rules (`:149`, `:151`, `:166`); two `**REQUIRED:**` auto-load pointers to the reference files (`:153`, `:168`); two checklist blocks that instruct the agent to *perform* campaign steps (`:197-203`, `:205-211`); and the description best-practice guidance (`:43-70`).
- `skills/writing-skills/references/pressure-testing.md` (198 lines) is the full pressure-test protocol: scope, RED-GREEN-REFACTOR, scenario design, execution protocol (dispatch harness at `:78-90`), micro-tests, rationalization plugging, meta-testing, done criteria, campaign lessons, common mistakes, results-log template (`:172-198`).
- `skills/writing-skills/references/trigger-optimizing.md` (185 lines) is the full trigger-eval protocol: scope, eval query design, train/validation split, ≤3-iteration loop, opencode NDJSON harness (`:80-114`), contamination rules, done criteria, multi-skill campaigns, common mistakes, results-log format and `trigger-evals/` convention (`:151-185`).
- Known defects in the extraction sources (bundle §8): the eval-loop bash skeleton reads each line into `query` but expands an unassigned `$row` (`trigger-optimizing.md:98-99`) and hardcodes a repo path (`:100`); five citations point at `writing-skills` SKILL.md by line number (`trigger-optimizing.md:12,74,135,181`; `pressure-testing.md:123`); two sibling citations point at `pressure-testing.md` by filename (`trigger-optimizing.md:92,153`); the split section says "~20 queries" (`trigger-optimizing.md:49`) contradicting the ≤10-query design cap (`:17`).
- `AGENTS.md:13` references the pressure-testing reference file by full path; removal creates a dangling reference. The user has confirmed the replacement edit.
- Real campaign logs exist as format exemplars: `skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md` (uses the `-01` same-day disambiguation variant, undefined in rule text), `skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md` (hoisted h2 verdict variation).
- Validation tooling: `agentskills validate skills/<name>` (CLI from `skills-ref>=0.1.1`, `pyproject.toml:9`; entry point `.venv/bin/agentskills`; installed via `uv sync` in the devShell `flake.nix:38`) must print `Valid skill`. Verified against the repo on 2026-07-30. No Makefile or CI config exists; there are no other check commands.

## Desired End State

- `skills/pressure-testing/SKILL.md` exists: a standalone, self-contained skill carrying the full pressure-test protocol, supporting a single target skill or a list campaigned sequentially, invocable end-to-end without reading `writing-skills`.
- `skills/trigger-testing/SKILL.md` exists: a standalone, self-contained skill carrying the full trigger-eval protocol, the description best-practice rules (from `writing-skills` frontmatter guidance and https://agentskills.io/skill-creation/optimizing-descriptions), and sequential list support.
- `skills/writing-skills/SKILL.md` retains the Iron Law and Trigger Eval Rule text unchanged, contains no auto-execution instruction and no pointer to the removed reference files, and its testing checklist items direct the user to run the new skills manually.
- `skills/writing-skills/references/pressure-testing.md` and `references/trigger-optimizing.md` are deleted; every operational rule they held is accounted for in exactly one new skill or intentionally retained in `writing-skills`.
- `AGENTS.md` Pressure Test Pollution section names the test skills by name only, with no path reference.
- Verify: `agentskills validate` prints `Valid skill` for all three skills, and no dangling references to the removed files remain.

## What We're NOT Doing

- Pressure-testing or trigger-testing the two new skills themselves (deferred to a separate session after creation).
- Changing the substance of the testing methodologies (RED-GREEN-REFACTOR protocol, eval-set design caps, harness mechanics, log formats) beyond what extraction requires.
- Changing any skill other than `writing-skills` and the two new skills; not touching `agents/eval-reader.md`, `agents/trigger-evaluator.md`, `NOTES.md`, or `README.md`.
- Automating or scheduling test campaign execution.
- Creating any `trigger-evals/` directory or `test-campaigns/` logs (those are created by campaign runs, not by this plan).
- Deduplicating the description best-practice rules out of `writing-skills`; duplication across `writing-skills` (authoring) and `trigger-testing` (optimization) is accepted.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| `AGENTS.md:13` holds a full path to the file being removed (`AGENTS.md:13` vs. removal) | Drop the path reference; prose reads "When the user runs test campaigns via the pressure-testing or trigger-testing skills..." — skills named by NAME only, never by path | User-resolved decision 1; the repo's operational rules require user confirmation for AGENTS.md edits, and the user confirmed this exact change |
| `-01` same-day campaign-log filename variant observed (`skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md:1`) with no defining rule text | Document the variant in BOTH new skills' log conventions as `YYYY-MM-DD-NN-<skill>.md` (two-digit sequence, incrementing per same-day campaign) | User-resolved decision 2; two shipped logs already use the variant, so the new skills must be able to reproduce it |
| Where description best-practice rules live (`writing-skills` only vs. `trigger-testing` only vs. both) | Both: `writing-skills` keeps its frontmatter guidance unchanged (primary, authoring); `trigger-testing` carries a Description Best Practices section for optimization, incorporating the agentskills.io guidance | User-resolved decision 3; the PRD's edge case explicitly accepts duplication |
| Eval-set size and iteration caps: repo `trigger-optimizing.md:17,53-64` (≤10 queries, ≤3 iterations) vs. external agentskills.io (~20 queries, ~5 iterations) | Repo caps stay operative; external guidance is carried only as description-writing principles (pushiness, user-intent phrasing, near-miss negatives, fresh-query sanity check) | The PRD declares changing testing methodology substance a non-goal; the external source's required contribution is description best practices, which are compatible with the repo caps |
| Internal contradiction: `trigger-optimizing.md:49` says "Split the ~20 queries" while `:17` caps the set at ≤10 | Reword to "Split the eval queries ~60/40" during extraction | The ≤10 design cap governs; the "~20" is leftover from the external source the loop was adapted from |
| Campaign log structure: template per-scenario h3 sections (`pressure-testing.md:178-198`) vs. hoisted h2 verdicts in one shipped log (`skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md:96-101`) | The template's per-scenario h3 layout is canonical in the new skills; the hoisted h2 layout is noted as an acceptable variation when rationalizations span scenarios | The template matches the majority of shipped logs and prescribes per-scenario verdicts; banning the variation would change methodology, which is out of scope |
| New skill anatomy: single `SKILL.md` vs. `SKILL.md` + `references/` | Single `SKILL.md` per new skill, no `references/` directory | Each new skill must be completable end-to-end with no external reads; a ~200-line single file matches the repo's largest existing skill (`writing-skills`, 211 lines), and there is no second document to lazy-load |
| Broken eval-loop bash skeleton: `$row` never assigned (`trigger-optimizing.md:98-99`), hardcoded repo path (`:100`) | Ship the corrected skeleton (shown verbatim in Phase 2): read both tab-separated fields directly in the `while read` line; parameterize the repo path as `<repo-root>` | Extraction must not propagate a known bug; the fix is mechanical, not a methodology change |
| Five line-number citations into `writing-skills` SKILL.md and two sibling filename citations inside the extraction sources | Replace with by-name cross-skill references (repo-established pattern at `skills/prd-to-plan/SKILL.md:8`): `writing-skills` cited by skill name + section title; the `pressure-testing.md` sibling citations become references to "the pressure-testing skill" | Line numbers drift when `writing-skills` is revised (bundle §8 failure mode); by-name references are stable |
| `trigger-optimizing.md:153` cites the base campaign log format by location in `pressure-testing.md` | Inline the shared conventions (title format, filename rule, status-only-in-logs rule) directly in `trigger-testing` — no cross-skill read needed | The PRD requires a trigger campaign to complete end-to-end without consulting another skill; a by-name pointer would still force the read |
| `trigger-optimizing.md:74` cites `SKILL.md:53` for the weave-trigger-terms principle | Redirect to the new skill's own Description Best Practices section | `trigger-testing` carries that rule itself after this plan; an internal citation is shortest and stable |
| Sequential list support for `pressure-testing` (source file has none) | Add a Multi-Skill Campaigns section modeled on `trigger-optimizing.md:133-137` but without the routing regression smoke (that concern is specific to description routing) | The PRD requires list support in both new skills; pressure campaigns edit rule bodies, not routing surfaces, so cross-campaign routing regression does not apply |

## Implementation Approach

Phases 1 and 2 create the two new skills in parallel (disjoint new directories; each reads the extraction sources, which still exist, and references the other new skill by name only). Phase 3 then revises `writing-skills`, deletes the extracted reference files, and applies the confirmed `AGENTS.md` edit — it must run after Phases 1 and 2 because it deletes the files those phases read and its "once extracted" ordering is a semantic dependency, not a file overlap. Phase 4 is an inline audit against the fully integrated result: structural validation of all three skills, a dangling-reference sweep, and a rule-by-rule content-accounting check proving nothing was silently dropped.

Both new skills are authored per the `writing-skills` process minus its testing campaigns: two-field frontmatter with an imperative "Use when..." description (≤1024 chars, trigger terms woven into prose, no colon-in-plain-scalar), ordered process sections, a workflow, and a standalone boundary. Extraction is verbatim section carriage wherever possible; every deviation from the source text is an exact old→new edit specified in the phase, never an instruction to paraphrase.

## Phase 1: Create the pressure-testing skill

### Overview

Create `skills/pressure-testing/SKILL.md` carrying the complete pressure-test protocol from `skills/writing-skills/references/pressure-testing.md`, plus a workflow, sequential list support, the `-NN` filename disambiguation rule, and a standalone boundary.

**Parallel group:** new-skills

**Execution:** subagent

### Changes Required

#### 1. New skill file
**File**: `skills/pressure-testing/SKILL.md` (create)
**Changes**: create the file with the following exact structure. Sections marked **verbatim** are copied unchanged from `skills/writing-skills/references/pressure-testing.md` (line ranges cited); sections marked **edit** are copied with the exact replacement shown; sections marked **new** use the exact text shown.

**Frontmatter (new):**

```markdown
---
name: pressure-testing
description: Use when pressure-testing a discipline skill's rules with baseline and with-skill campaign runs, when a new or edited discipline rule needs a failing baseline before it ships, or when running RED-GREEN-REFACTOR scenario campaigns against one skill or a list of skills run sequentially. Also use when about to ship an untested discipline rule, skip the no-skill baseline, trust a single green run, or counter a rationalization with vague guidance instead of an explicit negation.
---
```

**Title and intro (new):**

```markdown
# Pressure Testing

**Core principle:** If you didn't watch an agent fail without the skill, you don't know what the skill prevents. Baseline first, always.

Run this campaign when a discipline skill's rules are created or edited, before the skill ships, or any time an existing skill needs its rules pressure-tested.
```

(The source's `**Load this reference when:**` opener at `pressure-testing.md:3` is dropped — the frontmatter description replaces it.)

**`## Workflow` (new):**

```markdown
## Workflow

Input: one target skill name, or a list of target skills.

1. Read the target skill's `SKILL.md` fully. Check Scope — if the skill has no violable rule, pressure testing does not apply; say so and move on.
2. Design scenarios per Scenario Design (3+ pressures, forced A/B/C choice).
3. Run the baseline (RED) per Execution Protocol. If the baseline does not exhibit the failure, stop — there is nothing to fix.
4. Run with-skill reps (GREEN). Record rationalizations verbatim.
5. Close each loophole per Plugging Rationalizations and re-run (REFACTOR) until the Done Criteria hold.
6. Write the results log per Results Log Template — one log per target skill.
7. Given a list of skills, advance to the next skill per Multi-Skill Campaigns.
```

**`## Scope`** — verbatim from `pressure-testing.md:7-18`.

**`## RED-GREEN-REFACTOR for Skills`** — verbatim from `pressure-testing.md:20-28`.

**`## Scenario Design`** — verbatim from `pressure-testing.md:30-68`.

**`## Execution Protocol (opencode)`** — verbatim from `pressure-testing.md:70-101`.

**`## Micro-Tests (wording level)`** — verbatim from `pressure-testing.md:103-112`.

**`## Plugging Rationalizations`** — from `pressure-testing.md:114-123` with one edit:

- Old (`:123`): `Which counter form to use depends on the failure type — follow "Match the Form to the Failure" in SKILL.md. Prohibitions only for discipline failures; wrong-shaped output gets a recipe, not a "don't" list.`
- New: `Which counter form to use depends on the failure type — follow "Match the Form to the Failure" in the writing-skills skill. Prohibitions only for discipline failures; wrong-shaped output gets a recipe, not a "don't" list.`

**`## Meta-Testing`** — verbatim from `pressure-testing.md:125-138`.

**`## Done Criteria`** — verbatim from `pressure-testing.md:140-151`.

**`## Campaign-Execution Lessons`** — verbatim from `pressure-testing.md:153-159`.

**`## Common Mistakes`** — verbatim from `pressure-testing.md:161-170`.

**`## Multi-Skill Campaigns` (new):**

```markdown
## Multi-Skill Campaigns

When invoked with a list of target skills, campaign them sequentially — one skill at a time, in the order given. For each skill, run the full campaign (baseline, with-skill, REFACTOR loop) and write its results log to that skill's `test-campaigns/` directory before advancing. Verify the log file exists before starting the next skill. Do not interleave scenarios or reps across skills, and do not run skills in parallel: later skills' campaigns may depend on edits made while closing earlier skills' loopholes.
```

**`## Results Log Template`** — from `pressure-testing.md:172-198` with one edit:

- Old (`:174`): `Save campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>.md` in the skill under test's directory (where its SKILL.md resides).`
- New: `Save campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>.md` in the skill under test's directory (where its SKILL.md resides). If a campaign log for the same skill already exists for that date, insert a two-digit sequence number: `test-campaigns/YYYY-MM-DD-NN-<skill-name>.md` (e.g. `2026-07-29-01-prompt-shaping.md`), incrementing NN per additional same-day campaign.`

(The remainder of the section — the status-only-in-logs rule and the markdown template — is verbatim.)

**`## Standalone Boundary` (new):**

```markdown
## Standalone Boundary

This skill ends when each target skill's results log is written. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the campaign results.
```

### Success Criteria

#### Automated Verification:
- [ ] File exists: `test -f skills/pressure-testing/SKILL.md`
- [ ] Skill validation passes: `agentskills validate skills/pressure-testing` (must print `Valid skill`)

#### Manual Verification:
- [ ] Every section of `skills/writing-skills/references/pressure-testing.md` (Scope, RED-GREEN-REFACTOR, Scenario Design, Execution Protocol, Micro-Tests, Plugging Rationalizations, Meta-Testing, Done Criteria, Campaign-Execution Lessons, Common Mistakes, Results Log Template) is present in the new skill, verbatim except the two specified edits
- [ ] The `-NN` filename disambiguation rule appears in the Results Log Template section
- [ ] The Multi-Skill Campaigns section prescribes strictly sequential, one-log-per-skill processing
- [ ] The description starts with "Use when...", contains no `: ` (colon-space) sequence, and is ≤1024 chars
- [ ] No line-number citations and no `**Load this reference when:**` opener remain

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Create the trigger-testing skill

### Overview

Create `skills/trigger-testing/SKILL.md` carrying the complete trigger-eval protocol from `skills/writing-skills/references/trigger-optimizing.md`, the description best-practice rules (from `writing-skills` frontmatter guidance and the agentskills.io description-optimization guidance), the corrected harness skeleton, sequential list support, the `-NN` filename disambiguation rule, and a standalone boundary.

**Parallel group:** new-skills

**Execution:** subagent

### Changes Required

#### 1. New skill file
**File**: `skills/trigger-testing/SKILL.md` (create)
**Changes**: create the file with the following exact structure. Same convention as Phase 1: **verbatim** sections copy unchanged from `skills/writing-skills/references/trigger-optimizing.md`; **edit** sections apply the exact replacement shown; **new** sections use the exact text shown.

**Frontmatter (new):**

```markdown
---
name: trigger-testing
description: Use when testing or optimizing a skill's trigger description with eval queries, train and validation splits, and detection-harness campaigns, when a new or edited description needs a passing eval set before it ships, or when running trigger-eval campaigns against one skill or a list of skills run sequentially. Also use when about to tune a description against the full eval set without a split, paste failed-query keywords into a description, pick the last iteration instead of the best validation pass rate, or ship a description with no fresh-query sanity check. Carries description-writing best practices.
---
```

**Title and intro (new):**

```markdown
# Trigger Testing

**Core principle:** A skill description causes loading on the right user prompts and not on the wrong ones. If you didn't measure that, you don't know it ships. Eval set first, always.

Run this campaign when a skill's description is designed or revised, before the skill ships, or any time an existing skill's trigger behavior needs measuring. Applies to every skill, including pure reference.
```

(The source's `**Load this reference when:**` opener at `trigger-optimizing.md:3` is dropped.)

**`## Workflow` (new):**

```markdown
## Workflow

Input: one target skill name, or a list of target skills.

1. Read the target skill's `SKILL.md` and its current frontmatter `description`.
2. Build the eval set per Trigger Eval Query Design; split it per Train/Validation Split into `trigger-evals/train.json` and `trigger-evals/validation.json`.
3. Smoke-test the harness: run ONE query through the opencode Harness and read its output before dispatching full runs.
4. Run the Optimization Loop: evaluate, revise per failure class, repeat — selecting the best iteration by validation pass rate.
5. Run the fresh-query sanity check; at most one train-expansion re-opt.
6. Check the Done Criteria, then write the results log per Results Log Format — one log per target skill.
7. Given a list of skills, advance per Multi-Skill Campaigns.
```

**`## Scope`** — from `trigger-optimizing.md:7-13` with one edit:

- Old (`:12`): `Reference skills (exempt from pressure testing per `SKILL.md:138–149`) are NOT exempt here:`
- New: `Reference skills (exempt from pressure testing per the writing-skills skill's Testing Discipline Skills section) are NOT exempt here:`

**`## Description Best Practices` (new)** — placed immediately after Scope, since revisions in the Optimization Loop draw on it:

```markdown
## Description Best Practices

Rules for writing and revising skill descriptions, from this repo's writing-skills guidance and https://agentskills.io/skill-creation/optimizing-descriptions:

- **Imperative opener.** Start with "Use when..." plus concrete triggering conditions and symptoms.
- **WHAT + WHEN.** State what the skill produces (one clause) so the agent can match user intent, and when to use it. Write for user intent, not implementation mechanics.
- **Err on the side of being pushy.** List contexts where the skill applies, including situations where the user doesn't name the domain — the description is the primary trigger mechanism, and under-triggering makes the skill invisible.
- **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body.
- **Concise.** A few sentences to a short paragraph, hard limit 1024 chars. Every token competes with all other skills' descriptions at startup. Move exhaustive anti-pattern enumerations into the body; keep only the most discriminating trigger or symptom in the description.
- **Weave trigger terms into prose** (error messages, symptoms, synonyms, tool names). Never append a `Keywords:` or `Trigger phrases:` label.
- **YAML safety.** The description is a YAML scalar: a plain scalar cannot contain a colon followed by a space, and the 1024-char limit is hard. Prefer plain prose; use a block scalar (`description: >`) only if a list-like term is genuinely unavoidable.
- **Generalize failures.** When an eval query fails, address the general category the query represents — never paste the failed query's specific keywords into the description (that overfits).
```

**`## Trigger Eval Query Design`** — verbatim from `trigger-optimizing.md:15-45`.

**`## Train/Validation Split`** — from `trigger-optimizing.md:47-51` with one edit:

- Old (`:49`): `Split the ~20 queries ~60/40 into `trigger-evals/train.json` and `trigger-evals/validation.json``
- New: `Split the eval queries ~60/40 into `trigger-evals/train.json` and `trigger-evals/validation.json``

**`## The Optimization Loop`** — from `trigger-optimizing.md:53-74` with one edit:

- Old (`:74`): `(Cross-reference: this is the same principle already encoded in `SKILL.md`'s Frontmatter guidance — weave trigger terms into prose, never enumerate them as a labeled list — see `SKILL.md:53`.)`
- New: `(Cross-reference: this is the same principle encoded in this skill's Description Best Practices — weave trigger terms into prose, never enumerate them as a labeled list.)`

**`## opencode Harness`** — from `trigger-optimizing.md:76-114` with two edits:

Edit 1 (`:92`):
- Old: `**Eval loop skeleton** (matching `pressure-testing.md`'s inline bash pattern):`
- New: `**Eval loop skeleton** (matching the pressure-testing skill's inline bash pattern):`

Edit 2 (`:94-107`): replace the broken skeleton with this corrected version verbatim:

```bash
SKILL="<candidate>"
for q_set in train validation; do
  for f in trigger-evals/${q_set}/*.json; do
    while IFS=$'\t' read -r query should_trigger; do
      out=$(mktemp); opencode run --dir <repo-root> \
        --format json "$query" > "$out" 2>&1
      triggered=$(grep '"tool":"skill"' "$out" | grep -q "\"name\":\"$SKILL\"" && echo yes || echo no)
      # record (query, should_trigger, triggered)
      rm "$out"
    done < <(jq -rc '.[] | "\(.query)\t\(.should_trigger)"' "$f")
  done
done
```

(The original read each line into `query` but expanded an unassigned `$row`, and hardcoded a repo path; the replacement reads both tab-separated fields directly and parameterizes the repo path.)

**`## Contamination Rules`** — verbatim from `trigger-optimizing.md:116-120`.

**`## Done Criteria`** — verbatim from `trigger-optimizing.md:122-131`.

**`## Multi-Skill Campaigns`** — from `trigger-optimizing.md:133-137` with one edit:

- Old (`:135`): `When a plan campaigns multiple skills in sequence against a shared live `SKILL.md:3` state,`
- New: `When a plan campaigns multiple skills in sequence against a shared live description state,`

**`## Common Mistakes`** — verbatim from `trigger-optimizing.md:139-149`.

**`## Results Log Format`** — from `trigger-optimizing.md:151-185` with three edits:

Edit 1 (`:153`):
- Old: `Trigger eval logs extend the existing campaign log format (which lives at `pressure-testing.md:172`). Save trigger campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` — the `-trigger` suffix distinguishes them from discipline pressure-test campaigns at `test-campaigns/YYYY-MM-DD-<skill-name>.md`.`
- New: `Trigger eval logs use the campaign log format: title `# Test Campaign: <skill-name> — <date>`, with per-run bullets recording verdicts and verbatim evidence. Save trigger campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` — the `-trigger` suffix distinguishes them from discipline pressure-test campaigns at `test-campaigns/YYYY-MM-DD-<skill-name>.md`. If a log for the same skill and suffix already exists for that date, insert a two-digit sequence number: `test-campaigns/YYYY-MM-DD-NN-<skill-name>-trigger.md`, incrementing NN per additional same-day campaign.`

Edit 2: the two optional-section templates and the `trigger-evals/` directory convention (`:155-179`, `:183-185`) carry verbatim.

Edit 3 (`:181`):
- Old: `The campaign log is the ONLY place trigger status lives. Never add trigger status, verdicts, `test-campaigns/`, or `trigger-evals/` references to `SKILL.md` — `SKILL.md` is loaded into working context on every run, and status notes there bloat context and invite agents to read the logs. (Extends the existing rule at `SKILL.md:151`.)`
- New: `The campaign log is the ONLY place trigger status lives. Never add trigger status, verdicts, `test-campaigns/`, or `trigger-evals/` references to `SKILL.md` — `SKILL.md` is loaded into working context on every run, and status notes there bloat context and invite agents to read the logs.`

**`## Standalone Boundary` (new):**

```markdown
## Standalone Boundary

This skill ends when each target skill's trigger results log is written. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the campaign results.
```

### Success Criteria

#### Automated Verification:
- [ ] File exists: `test -f skills/trigger-testing/SKILL.md`
- [ ] Skill validation passes: `agentskills validate skills/trigger-testing` (must print `Valid skill`)

#### Manual Verification:
- [ ] Every section of `skills/writing-skills/references/trigger-optimizing.md` (Scope, Trigger Eval Query Design, Train/Validation Split, The Optimization Loop, opencode Harness, Contamination Rules, Done Criteria, Multi-Skill Campaigns, Common Mistakes, Results Log Format including the `trigger-evals/` convention) is present in the new skill, verbatim except the specified edits
- [ ] The Description Best Practices section is present and carries both the writing-skills rules (imperative opener, WHAT + WHEN, no workflow summary, conciseness, woven trigger terms, YAML safety) and the agentskills.io principles (user intent over implementation, err pushy, generalize failures)
- [ ] The corrected bash skeleton assigns both `query` and `should_trigger` in the `while read` line and contains no hardcoded absolute repo path
- [ ] The `-NN` filename disambiguation rule appears in the Results Log Format section for `-trigger` logs
- [ ] The eval-set caps remain ≤5+≤5 queries and ≤3 iterations (methodology unchanged); the "~20 queries" wording is gone
- [ ] The description starts with "Use when...", contains no `: ` (colon-space) sequence, and is ≤1024 chars
- [ ] No line-number citations into `writing-skills` and no filename citations of `pressure-testing.md` remain

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Revise writing-skills, remove extracted references, update AGENTS.md

### Overview

Rewrite the two testing sections' pointers and the two testing checklist blocks in `skills/writing-skills/SKILL.md` so the mandates stand but execution is redirected to manual invocation of the new skills; delete the two extracted reference files; apply the user-confirmed `AGENTS.md:13` prose edit. Runs after Phases 1 and 2 because it deletes the files those phases read, and removal is only valid once extraction is complete.

**Parallel group:** none

**Execution:** subagent

### Changes Required

#### 1. Testing Discipline Skills section pointer
**File**: `skills/writing-skills/SKILL.md`
**Changes**: the Iron Law, applies-to text, no-exceptions list, pure-reference exemption, untested-recording rule, and status rule (`:140-151`) stay byte-for-byte unchanged. Replace only the pointer (`:153`):

- Old: `**REQUIRED:** See `references/pressure-testing.md` for scenario design, execution protocol, meta-testing, done criteria, and the results-log format.`
- New: `**Testing is part of the skill-creation process, but the agent does not run it.** Tell the user the skill must be pressure-tested and direct them to run the `pressure-testing` skill manually to complete the process. Never begin any campaign step as part of authoring.`

#### 2. Trigger Optimization section pointer
**File**: `skills/writing-skills/SKILL.md`
**Changes**: the Trigger Eval Rule, applies-to-every-skill text, no-exceptions list, and untested-recording rule (`:157-166`) stay byte-for-byte unchanged. Replace only the pointer (`:168`):

- Old: `**REQUIRED:** See `references/trigger-optimizing.md` for eval query design (≤5 should-trigger + ≤5 should-not), train/validation split, the ≤3-iteration optimization loop, the opencode detection harness, contamination rules, done criteria, and the trigger results-log format.`
- New: `**Testing is part of the skill-creation process, but the agent does not run it.** For every skill — including pure reference — tell the user the description must pass a trigger eval and direct them to run the `trigger-testing` skill manually to complete the process. Never begin any campaign step as part of authoring.`

#### 3. Testing checklist block
**File**: `skills/writing-skills/SKILL.md`
**Changes**: replace the block at `:197-203`:

- Old:
  ```markdown
  **Testing (discipline skills only):**
  - [ ] Baseline scenarios run WITHOUT the skill; rationalizations documented verbatim (RED)
  - [ ] Scenarios re-run WITH the skill; agent complies and cites the skill (GREEN)
  - [ ] New loopholes closed (rule negation + rationalization row + red flag + description symptom) and re-tested (REFACTOR)
  - [ ] Results log written to `test-campaigns/` in the skill's directory
  - [ ] Any rule shipped untested is recorded as untested in the campaign log — never in SKILL.md
  - [ ] No test status, campaign results, or `test-campaigns/` references in SKILL.md
  ```
- New:
  ```markdown
  **Testing (discipline skills only):**
  - [ ] User told the skill must be pressure-tested and directed to run the `pressure-testing` skill manually (skipped only for pure-reference skills with no violable rule)
  - [ ] User told any rule shipping untested must be recorded as untested in the campaign log — never in SKILL.md
  - [ ] No test status, campaign results, or `test-campaigns/` references in SKILL.md
  - [ ] No campaign steps (baseline runs, with-skill reps, loophole re-tests) performed during authoring
  ```

#### 4. Trigger Optimization checklist block
**File**: `skills/writing-skills/SKILL.md`
**Changes**: replace the block at `:205-211`:

- Old:
  ```markdown
  **Trigger Optimization:**
  - [ ] Trigger eval set exists (`trigger-evals/train.json` + `trigger-evals/validation.json`), or trigger evals marked not applicable in `test-campaigns/` (e.g. for skills whose triggering surface is trivially unique)
  - [ ] Selected description chosen by **validation** pass rate, not the last iteration
  - [ ] Fresh-query sanity check passed (5 queries never used in optimization); at most 1 train-expansion re-opt performed
  - [ ] Borderline bumps limited to consecutive-opposite-outcome queries, ≤25% of queries/iteration, per-rep outcomes recorded
  - [ ] Early-abort stopped each rep once the verdict was observable (candidate load for should-trigger; substantive non-skill work for should-not)
  - [ ] For multi-skill plans: Final Verification ran 1 rep of each campaigned skill's canonical should-trigger smoke query against the final description state (no cross-phase routing regression)
  ```
- New:
  ```markdown
  **Trigger Optimization:**
  - [ ] User told the description must pass a trigger eval and directed to run the `trigger-testing` skill manually — applies to every skill, including pure reference
  - [ ] Pending its eval, the description complies with the Frontmatter rules (imperative, WHAT + WHEN, no workflow summary, trigger terms woven into prose, ≤1024 chars)
  - [ ] No eval-set creation, harness runs, or description iterations performed during authoring
  ```

(The removed operational items — eval-set existence, validation-rate selection, sanity check, bump limits, early-abort, regression smoke — all live in the new `trigger-testing` skill after Phase 2; nothing is dropped.)

#### 5. Delete the extracted reference files
**File**: `skills/writing-skills/references/pressure-testing.md`, `skills/writing-skills/references/trigger-optimizing.md`
**Changes**: delete both files and the now-empty directory:

```bash
git rm skills/writing-skills/references/pressure-testing.md skills/writing-skills/references/trigger-optimizing.md
```

#### 6. AGENTS.md Pressure Test Pollution edit (user-confirmed)
**File**: `AGENTS.md`
**Changes**: replace line 13:

- Old: `When running pressure test campaigns (see `skills/writing-skills/references/pressure-testing.md`), watch for two contamination sources in baseline runs:`
- New: `When the user runs test campaigns via the pressure-testing or trigger-testing skills, watch for two contamination sources in baseline runs:`

### Success Criteria

#### Automated Verification:
- [ ] Reference files gone: `test ! -e skills/writing-skills/references/pressure-testing.md && test ! -e skills/writing-skills/references/trigger-optimizing.md`
- [ ] Skill validation passes: `agentskills validate skills/writing-skills` (must print `Valid skill`)
- [ ] No dangling path references: `grep -rn "writing-skills/references" skills/ agents/ AGENTS.md NOTES.md` (must produce no output)
- [ ] No filename references to the removed files: `grep -rn "trigger-optimizing\.md\|references/pressure-testing\.md" skills/ agents/ AGENTS.md NOTES.md` (must produce no output)

#### Manual Verification:
- [ ] The Iron Law and Trigger Eval Rule mandate text is byte-for-byte unchanged
- [ ] The pure-reference exemption asymmetry survives: pressure-testing checklist block says "discipline skills only" with the pure-reference skip; trigger block says "every skill, including pure reference"
- [ ] Every remaining testing reference in `writing-skills` states testing is part of the process and names a skill (`pressure-testing` / `trigger-testing`) to run manually; no sentence instructs the agent to perform a campaign step
- [ ] The `AGENTS.md` Pressure Test Pollution section names the skills by name only — no path
- [ ] `writing-skills` frontmatter description and Frontmatter/Description YAML safety sections are unchanged (description best practices stay in place)

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 4: Integrated content-accounting audit

### Overview

Audit the fully integrated result: all three skills validate, no dangling references exist, and every operational rule from the removed reference material is accounted for in exactly one destination. Runs against the integrated tree, so it is inline and sequential.

**Parallel group:** none

**Execution:** inline

### Changes Required

None — this phase writes no files. It is a verification gate over the merged result of Phases 1-3.

### Success Criteria

#### Automated Verification:
- [ ] All three skills validate:
  `agentskills validate skills/writing-skills`
  `agentskills validate skills/pressure-testing`
  `agentskills validate skills/trigger-testing`
  (each must print `Valid skill`)
- [ ] No dangling references: `grep -rn "writing-skills/references" skills/ agents/ AGENTS.md NOTES.md` (no output)
- [ ] No auto-launch residue: `grep -n "REQUIRED.*references/\|references/pressure-testing\|references/trigger-optimizing" skills/writing-skills/SKILL.md` (no output)
- [ ] The removed files are gone from the worktree and the `references/` directory is absent: `test ! -d skills/writing-skills/references`

#### Manual Verification:
- [ ] Content accounting, pressure-test side — each of these is present in `skills/pressure-testing/SKILL.md`: scope rules (incl. pure-reference exemption), RED-GREEN-REFACTOR table, scenario design rules and pressure types, execution protocol (dispatch commands, smoke-test rule, void-run convention, contamination reporting, rep counts, control-first ordering, manual reading, variance metric), micro-tests, rationalization plugging (four counter forms), meta-testing (question + three-way classification), done criteria, campaign-execution lessons, common mistakes table, results-log template with status-only-in-logs rule and the `-NN` filename rule
- [ ] Content accounting, trigger side — each of these is present in `skills/trigger-testing/SKILL.md`: scope (incl. reference skills NOT exempt), description best practices, eval query design (axes, near-miss negatives, realism tips), train/validation split (60/40, fixed across iterations), the optimization loop (≤3 iterations, failure-class table, 1024-char re-check, fresh-query sanity check with at-most-one train expansion), opencode harness (invoke, detect, candidate-specificity, corrected loop skeleton, pass criterion, bump rule, early-abort, rep parallelism), contamination rules (all three), done criteria, multi-skill campaigns with Final-Verification regression smoke, common mistakes table, results-log format (both optional sections, `-trigger` suffix, `-NN` rule, status-only-in-logs rule) and the `trigger-evals/` directory convention
- [ ] Content accounting, retained side — these remain in `skills/writing-skills/SKILL.md`: Iron Law, Trigger Eval Rule, both no-exceptions lists, pure-reference exemption, both untested-recording rules, status-never-in-SKILL.md rule, frontmatter description guidance
- [ ] Nothing operational appears in zero or two destinations unintentionally (the only intentional duplications are the description best-practice rules, in `writing-skills` and `trigger-testing`, and the status-only-in-logs rule, restated in both new skills)
- [ ] A simulated authoring walkthrough: reading only the revised `writing-skills`, an agent reaching the testing checklist items would tell the user to run `pressure-testing` / `trigger-testing` manually and would not begin any campaign step

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before considering the plan complete.

---

## Testing Strategy

### Unit Tests:
- None — this plan changes only markdown skill content and one AGENTS.md line; the repo has no unit test suite (verified: no Makefile, no CI config, no test scripts).

### Integration Tests:
- `agentskills validate` on each of the three skills is the repo's structural integration gate (per-phase and again in Final Verification).
- The dangling-reference and auto-launch-residue greps in Phase 4 are the cross-file integration checks.

### Manual Testing Steps:
1. Read each new skill top to bottom once, checking it is completable without opening `writing-skills` (the PRD's independent-test scenarios).
2. Perform the Phase 4 content-accounting checklist against the removed files as they exist in git history (`git show HEAD:skills/writing-skills/references/pressure-testing.md` if the removal is already committed, or the pre-Phase-3 worktree otherwise).
3. Walk the revised `writing-skills` checklist as an author would and confirm every testing item directs manual invocation.

## Final Verification

agentskills validate skills/writing-skills
agentskills validate skills/pressure-testing
agentskills validate skills/trigger-testing
grep -rn "writing-skills/references" skills/ agents/ AGENTS.md NOTES.md
grep -rn "trigger-optimizing\.md\|references/pressure-testing\.md" skills/ agents/ AGENTS.md NOTES.md

(The two greps must produce no output; non-zero grep exit status is the pass condition.)

## References

- PRD: `PRDS/2026-07-30-extract-testing-skills.md`
- Context bundle: `RESEARCH/2026-07-30-extract-testing-skills-context-bundle.md`
- Research findings: `RESEARCH/2026-07-30-extract-testing-skills-research-findings.md`
- Key implementation files: `skills/writing-skills/SKILL.md:138-211`, `skills/writing-skills/references/pressure-testing.md:1-198`, `skills/writing-skills/references/trigger-optimizing.md:1-185`, `AGENTS.md:13`
