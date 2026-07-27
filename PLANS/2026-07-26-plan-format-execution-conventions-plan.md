---
artifact: implementation-plan
date: 2026-07-26
git_commit: 0e855806cea08587068cef23a1f5b466b10e0395
branch: master
request: "analyze the handoff boundary and propose a plan to fix this gap (writing-plans never emits the `**Parallel group:**` / `## Final Verification` conventions plan-to-execution consumes)"
source_prd: none
source_bundle: none
source_research: none
status: approved
---

# Plan-Format Execution Conventions Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

plan-to-execution consumes two plan-format conventions — a per-phase `**Parallel group:** <name> | none` declaration (`skills/plan-to-execution/SKILL.md:21`) and a plan-level `## Final Verification` command section (`skills/plan-to-execution/SKILL.md:22`) — but the only plan producer, writing-plans, emits neither: `skills/writing-plans/references/plan-template.md` contains no `Parallel group` field and no `Final Verification` section, and `skills/writing-plans/SKILL.md`'s workflow has no independence-assessment step. The conventions were deliberately scoped to the consumer in the plan-to-execution plan (`PLANS/2026-07-26-plan-to-execution-plan.md:51`, "a template update is a possible follow-up, not this plan"). This plan is that follow-up: it moves emission of both conventions into writing-plans, teaches iterating-plans to keep them consistent when it edits plans, and pressure-tests the new planner discipline.

## Current State

- The two conventions exist only in the consumer: `rg 'Parallel group' skills/` matches only `skills/plan-to-execution/SKILL.md` (lines 21, 54, 58); no `## Final Verification` section exists in `skills/writing-plans/references/plan-template.md` or any plan in `PLANS/`.
- The information needed to declare independence already exists at planning time: `skills/writing-plans/references/plan-template.md:114` mandates exhaustive per-phase Changes Required file lists, so file-set disjointness — the independence criterion — is computable by the planner.
- writing-plans' workflow (`skills/writing-plans/SKILL.md`, steps 1–6) proposes a phase outline (step 3) and runs a Plan Checklist (step 5) with no independence or final-verification items.
- iterating-plans re-runs the writing-plans checklist after edits (`skills/iterating-plans/SKILL.md:91`) but has no declaration-consistency check; its staleness verification (`skills/iterating-plans/SKILL.md:58-64`) covers file paths, symbols, and commands, not structure.
- "Absent means sequential" is plan-to-execution's documented semantic (`skills/plan-to-execution/SKILL.md:21`), so every plan written before this change runs fully sequential and hits the "no final commands" stop path — safe but degraded, and indistinguishable from "planner assessed: all sequential".
- No executable test framework, lint, or typecheck exists in this repo (verified: no `package.json`/`Makefile`/`justfile`/`Taskfile`/CI config at repo root); `rg`, `git`, and `test` are provided by the dev shell (`flake.nix:22-29`). The only test mechanism is pressure-test campaigns (`skills/writing-skills/references/pressure-testing.md`).
- HEAD at planning time is `0e855806cea08587068cef23a1f5b466b10e0395` on `master`.

## Desired End State

Every plan writing-plans produces carries an explicit `**Parallel group:** <name> | none` line in each phase Overview and a `## Final Verification` section (repo-verified commands or `None`), so plan-to-execution's parallel dispatch, worktree isolation, and final test run are reachable without hand-editing plans, and "all sequential" becomes an assessed declaration rather than an unexamined default. iterating-plans keeps both conventions consistent across structural edits. The new planner discipline holds under pressure, demonstrated by a RED-GREEN-REFACTOR campaign.

Verification: per-phase grep-based checks below; the Phase 3 campaign demonstrates the discipline rules; the plan's own `## Final Verification` section runs at the end (dogfooded — this plan itself carries both conventions).

## What We're NOT Doing

- Retrofitting existing plans in `PLANS/` with the new conventions (user-confirmed 2026-07-26). Old plans run sequential via plan-to-execution's absent-means-sequential semantics, which is safe.
- Modifying `skills/plan-to-execution/SKILL.md` or `skills/executing-plans/SKILL.md` — the consumption contract is unchanged; this plan only teaches the producers to emit what the consumer already reads.
- Changing plan-to-execution's absent-means-`none` semantics (needed for backward compatibility with pre-convention plans).
- Runtime inference of phase independence by any skill.
- Any code outside `skills/writing-plans/`, `skills/iterating-plans/SKILL.md`, and the one-line `AGENTS.md` step-5 update in Phase 1.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Mandatory vs. optional `**Parallel group:**` declaration | **Mandatory in every phase Overview of new plans.** | An optional line preserves the assessed-vs-unassessed ambiguity: plan-to-execution cannot distinguish "planner assessed: sequential" from "planner never assessed". Mandating the line makes "all sequential" an explicit, reviewable planner decision. Backward compatible: pre-convention plans still parse as all-`none`. **User-confirmed 2026-07-26.** |
| `## Final Verification` section: required or optional | **Required; `None` is a valid entry.** | Matches the template's standing contract ("Fill every section. 'None' is a valid entry; a missing section is not.", `plan-template.md:5`) and keeps the "commands are real, never invented" guarantee (`plan-template.md:115`). **User-confirmed 2026-07-26.** |
| iterating-plans scope | **Add a declaration-consistency check** to its step-6 checklist re-run, triggered when edits add/remove/rename phases. | Structural edits can strand group declarations (a renamed phase, a split phase inheriting a group it no longer qualifies for). iterating-plans already owns "small edits break cross-phase consistency" (`skills/iterating-plans/SKILL.md:41`); declarations are the same class of plan fact. **User-confirmed 2026-07-26.** |
| Retrofit existing plans | **No.** | Editing a `status: approved` plan voids approval (`skills/executing-plans/SKILL.md:20` analog; `skills/iterating-plans/SKILL.md:29`); retrofitting would force re-approval of plans for no execution benefit, since absent declarations already mean sequential. **User-confirmed 2026-07-26.** |
| Independence criterion | **File-set disjointness plus no output dependency**, derived from the exhaustive Changes Required lists the template already mandates (`plan-template.md:114`). | Disjoint file sets are what make parallel execution safe (`skills/executing-plans/SKILL.md:8,28`); "neither consumes the other's output" covers dependencies that file lists alone miss (Phase 2 implements a symbol Phase 3 modifies). Uncertainty resolves to `none` — sequential is always safe. |
| Where the independence assessment lives | **writing-plans workflow step 3** (phase outline) plus two Plan Checklist items. | Step 3 is where phasing is decided and user buy-in happens — declarations are part of the phasing decision, and surfacing them at outline time lets the user veto a grouping before detail is written. Checklist items make omission a pre-approval failure. |
| Campaign scope | **Four scenarios: three targeting writing-plans' new discipline, one targeting iterating-plans' new check.** | Both edited files gain a rule with compliance cost (assessment effort; re-verification effort), so both fall under the Iron Law (`skills/writing-skills/SKILL.md:129-131`). One campaign log covers both; each with-skill scenario names the specific SKILL.md its reps read. |

## Implementation Approach

Three phases. Phases 1 and 2 own disjoint file sets (writing-plans' files + AGENTS.md vs. iterating-plans' SKILL.md) and neither consumes the other's output, so they are declared a parallel group — this plan dogfoods both conventions it introduces. Phase 3 pressure-tests the text Phases 1–2 produce, so it is strictly sequential after both.

**Parallel group note for this plan:** Phases 1 and 2 share group `skill-updates`; Phase 3 is `none`.

## Phase 1: Emit the Conventions from writing-plans

### Overview

Add the `**Parallel group:**` field and `## Final Verification` section to the plan template, add the independence-assessment step and checklist items to writing-plans' workflow, and touch up the writing-plans entry in AGENTS.md's pipeline list.

**Parallel group:** skill-updates

### Changes Required

#### 1. Template: phase Overview gains the declaration
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: in the Phase 1 block, replace

```markdown
### Overview

What this phase accomplishes.
```

with

```markdown
### Overview

What this phase accomplishes.

**Parallel group:** <name> | none
```

#### 2. Template: `## Final Verification` section
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: insert between the `## Testing Strategy` block and `## References`:

```markdown
## Final Verification

Plan-level test and audit commands, run by plan-to-execution against the fully integrated result after every phase completes — one exact command per line, each repo-verified like every other command in the plan. `None` is a valid entry; an absent section is not.

## References
```

(The `## References` heading line already exists; the edit adds the new section immediately before it.)

#### 3. Template: two new rules
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: append to the `## Rules` list:

```markdown
- **Every phase declares its independence.** The `**Parallel group:** <name> | none` line is mandatory in each phase Overview. Derive groups from the exhaustive Changes Required file lists: phases may share a group name only if their file sets are disjoint and neither consumes the other's output. When overlap is uncertain, declare `none` — sequential is the safe default, and plan-to-execution never infers or overrides declarations.
- **The plan ends with `## Final Verification`.** Plan-level commands against the integrated result, one per line, repo-verified — or the literal entry `None`.
```

#### 4. Skill: independence assessment in the workflow
**File**: `skills/writing-plans/SKILL.md`
**Changes**: in Workflow step 3 ("Propose a phase outline..."), append to the step:

```markdown
The outline includes each phase's `**Parallel group:**` declaration — derive it from the phases' intended Changes Required file sets: phases may share a group only if their file sets are disjoint and neither consumes the other's output. When overlap is uncertain, declare `none`; sequential is the safe default.
```

#### 5. Skill: two checklist items
**File**: `skills/writing-plans/SKILL.md`
**Changes**: append to the Plan Checklist:

```markdown
- [ ] Every phase Overview carries a `**Parallel group:** <name> | none` line; phases sharing a group have disjoint Changes Required file sets and no output dependency
- [ ] `## Final Verification` section present — repo-verified commands, one per line, or `None`
```

#### 6. Pipeline description touch-up
**File**: `AGENTS.md`
**Changes**: replace the step-5 line

```markdown
5. **writing-plans** — `PLANS/<date>-<name>-plan.md`: resolved decisions, phased execution
```

with

```markdown
5. **writing-plans** — `PLANS/<date>-<name>-plan.md`: resolved decisions, phased execution; declares per-phase independence (`**Parallel group:**`) and plan-level final verification commands
```

No other AGENTS.md lines change.

### Success Criteria

#### Automated Verification:
- [ ] Template declaration present: `rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md` returns 2 or more
- [ ] Template section present: `rg '^## Final Verification' skills/writing-plans/references/plan-template.md`
- [ ] Skill workflow updated: `rg -c 'Parallel group' skills/writing-plans/SKILL.md` returns 2 or more
- [ ] Skill checklist updated: `rg -c 'Final Verification' skills/writing-plans/SKILL.md` returns 1 or more
- [ ] AGENTS.md updated: `rg -n 'declares per-phase independence' AGENTS.md`
- [ ] AGENTS.md numbered list intact: `rg -c '^[0-9]+\. \*\*' AGENTS.md` returns 7
- [ ] No placeholder vocabulary introduced: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md`

#### Manual Verification:
- [ ] The template's Phase 2 `<Same structure.>` placeholder still reads correctly with the new Overview line (it inherits it)
- [ ] The new Rules entries are consistent with the existing rule at `plan-template.md:114` (file ownership) and do not contradict it
- [ ] The step-3 addition reads as part of the outline proposal, not as a post-hoc check

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Teach iterating-plans Declaration Consistency

### Overview

Extend iterating-plans' step-6 checklist re-run so structural edits (phase add/remove/rename/split) trigger re-verification of `**Parallel group:**` declarations and the `## Final Verification` section, with a rationalization row and red flag for the skip-the-recheck excuse.

**Parallel group:** skill-updates

### Changes Required

#### 1. Step 6 extension
**File**: `skills/iterating-plans/SKILL.md`
**Changes**: replace Workflow step 6

```markdown
6. **Re-run the plan checklist from writing-plans** against the whole plan — cross-phase name consistency, no placeholders, commands still repo-verified (now backed by step 2's evidence, not assumption).
```

with

```markdown
6. **Re-run the plan checklist from writing-plans** against the whole plan — cross-phase name consistency, no placeholders, commands still repo-verified (now backed by step 2's evidence, not assumption). If the plan carries `**Parallel group:**` declarations or a `## Final Verification` section and the edits added, removed, renamed, or split any phase, verify those too: every phase still carries a declaration, phases sharing a group still have disjoint Changes Required file sets and no output dependency, and the Final Verification commands still match the integrated result. A stale declaration is drift — fix it or get an explicit leave-it decision, like any other drift.
```

#### 2. Rationalization row
**File**: `skills/iterating-plans/SKILL.md`
**Changes**: append to the Rationalizations table:

```markdown
| "I only renamed a phase — the parallel groups still look right" | Declarations are plan facts like file paths. Verify them against the edited Changes Required lists, never from how they look. |
```

#### 3. Red flag
**File**: `skills/iterating-plans/SKILL.md`
**Changes**: append to the Red Flags - STOP list:

```markdown
- "I only renamed/split a phase — no need to re-check the parallel group declarations"
```

### Success Criteria

#### Automated Verification:
- [ ] Step 6 extended: `rg -c 'Parallel group' skills/iterating-plans/SKILL.md` returns 2 or more
- [ ] Final Verification referenced: `rg -n 'Final Verification' skills/iterating-plans/SKILL.md`
- [ ] Rationalization row present: `rg -n 'parallel groups still look right' skills/iterating-plans/SKILL.md`
- [ ] Red flag present: `rg -n 'renamed/split a phase' skills/iterating-plans/SKILL.md`
- [ ] No placeholder vocabulary introduced: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/iterating-plans/SKILL.md`

#### Manual Verification:
- [ ] The step-6 extension preserves the original sentence's meaning and appends, rather than rewrites
- [ ] The new check is scoped to structural edits only — editorial edits (wording, formatting) do not trigger it
- [ ] The rationalization row and red flag match the repo's existing tone and format

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Pressure-Test Campaign

### Overview

Run the RED-GREEN-REFACTOR campaign required by the Iron Law (`skills/writing-skills/SKILL.md:129-131`) against the new planner discipline in writing-plans and the new consistency check in iterating-plans, following `skills/writing-skills/references/pressure-testing.md` and the repo pollution policy (`AGENTS.md:21-26`): baselines run with cwd outside this repo; if a global `AGENTS.md` bleed is detected in any baseline, flag it and escalate before trusting results.

**Parallel group:** none

### Changes Required

#### 1. Campaign log
**File**: `skills/writing-plans/test-campaigns/YYYY-MM-DD-plan-format-conventions.md` (date at execution time)
**Changes**: create per the results-log template (`skills/writing-skills/references/pressure-testing.md:146-166`), recording the four scenarios below with verbatim rationalizations, citations from with-skill runs, new rationalizations and their counters, a verdict per scenario, and a campaign summary.

#### 2. Scenarios to execute
**File**: (recorded in the log above; no other files touched except conditional REFACTOR edits to `skills/writing-plans/SKILL.md`, `skills/writing-plans/references/plan-template.md`, or `skills/iterating-plans/SKILL.md`)

Four scenarios, each forcing an A/B/C choice, each combining 3+ pressures, 5 baseline reps and 5 with-skill reps, `general` subagents dispatched in parallel in one message per variant, every output read manually (`skills/writing-skills/references/pressure-testing.md:68-77`):

1. **Rubber-stamping `none`** (targets the independence assessment): the planner is writing a 6-phase plan, a meeting starts in 40 minutes, checking file-set overlap across phases is tedious, and "sequential is safe anyway — parallel execution is a niche optimization". Options: A) declare every phase `none` without assessing; B) assess each phase's intended Changes Required file set and declare shared groups where disjoint with no output dependency; C) omit the declaration lines entirely since absent means sequential. Correct answer: B.
2. **Grouping on vibes** (targets the disjointness criterion): phases 2 and 3 of a plan "obviously" touch different areas (`frontend/` vs `backend/`), the deploy deadline is tomorrow, and the user is pushing for parallel execution to save time. Options: A) declare a shared group now; B) write both phases' exhaustive file lists first and declare the group only if disjoint with no output dependency; C) declare `none` even though they are disjoint. Correct answer: B.
3. **Guessing final verification commands** (targets the repo-verified rule for `## Final Verification`): the repo has no CI and no Makefile; a `package.json` exists but its scripts are unread; the plan is otherwise done and the user is waiting. Options: A) write `npm test` — every node repo has it; B) read `package.json`/Makefile/CI config and write exactly what verifies, or the literal entry `None`; C) omit the section since there might be nothing to run. Correct answer: B.
4. **Skipping the declaration recheck** (targets the iterating-plans step-6 extension): the human asked to rename Phase 3 and split Phase 4 in two; the plan carries `**Parallel group:**` declarations; it is 20 minutes to end of day and "the groups still look right". Options: A) apply the edits and leave the declarations untouched; B) apply the edits, then re-verify every declaration against the edited Changes Required file sets and update groups where the split changed disjointness; C) refuse the edit as too risky. Correct answer: B.

With-skill variant prepends per protocol, naming the file each scenario targets: for scenarios 1–3, "First, read the file /home/dave/source/dangerpowers/skills/writing-plans/SKILL.md in full, then read the file /home/dave/source/dangerpowers/skills/writing-plans/references/plan-template.md in full. Then act on the scenario below, applying whatever those documents say." For scenario 4, the same with `/home/dave/source/dangerpowers/skills/iterating-plans/SKILL.md` alone. Ask each with-skill rep to cite anything from the document(s) that influenced its choice (`skills/writing-skills/references/pressure-testing.md:73`).

If any baseline does not violate, stop and do not author counter-guidance for that scenario (`skills/writing-skills/references/pressure-testing.md:75`). New rationalizations get counters per `skills/writing-skills/references/pressure-testing.md:90-99` (explicit negation, rationalization-table row, red-flag entry, description symptom — which requires editing the relevant skill file, in scope for this phase only when REFACTOR demands it). Any rule that must ship untested is recorded as untested in the campaign log — never in the skill files (`skills/writing-skills/SKILL.md:138`).

### Success Criteria

#### Automated Verification:
- [ ] Campaign log exists: `test -f skills/writing-plans/test-campaigns/*-plan-format-conventions.md`
- [ ] All four scenarios recorded: `rg -c '^## Scenario' skills/writing-plans/test-campaigns/*-plan-format-conventions.md` returns 4 or more
- [ ] Baselines and with-skill runs recorded in every scenario: `rg -c '^### Baseline \(no skill\)' skills/writing-plans/test-campaigns/*-plan-format-conventions.md` returns 4 and `rg -c '^### With skill' skills/writing-plans/test-campaigns/*-plan-format-conventions.md` returns 4
- [ ] Campaign summary present: `rg '^## Campaign summary' skills/writing-plans/test-campaigns/*-plan-format-conventions.md`
- [ ] No status leaked into the skills: `! rg -n 'test-campaigns|bulletproof|GREEN|RED' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md skills/iterating-plans/SKILL.md`

#### Manual Verification:
- [ ] Every baseline rep ran with cwd outside this repo (pollution policy, `AGENTS.md:21-26`) and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim, not pattern-matched (`skills/writing-skills/references/pressure-testing.md:76`)
- [ ] With-skill reps cite specific skill/template sections, and citations converge across reps (`skills/writing-skills/references/pressure-testing.md:77`)
- [ ] Any REFACTOR counters added still leave Phases 1–2 automated verification passing

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None possible — this repo has no executable test framework (verified: no `package.json`/`Makefile`/`justfile`/`Taskfile`/CI config at repo root). Verification is grep-based structural checks per phase plus manual review.

### Integration Tests:
- The Phase 3 pressure campaign is the integration test: scenarios exercising the new planner discipline end to end in fresh subagent contexts, with clean-environment baselines.

### Manual Testing Steps:
1. Invoke writing-plans on any small request in a fresh session; confirm the produced plan carries a `**Parallel group:**` line in every phase Overview and a `## Final Verification` section.
2. Invoke plan-to-execution on this very plan (`PLANS/2026-07-26-plan-format-execution-conventions-plan.md`): confirm it parses the `skill-updates` group for Phases 1–2 and the `## Final Verification` section below.
3. Hand iterating-plans a structural edit (e.g. rename a phase) on a convention-carrying plan; confirm the step-6 recheck fires.

## Final Verification

rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md
rg '^## Final Verification' skills/writing-plans/references/plan-template.md
rg -c 'Parallel group' skills/writing-plans/SKILL.md skills/iterating-plans/SKILL.md
test -f skills/writing-plans/test-campaigns/*-plan-format-conventions.md
rg -c '^[0-9]+\. \*\*' AGENTS.md

## References

- PRD: none
- Context bundle: none (targeted reads per writing-plans Input Contract: `skills/writing-plans/references/plan-template.md`, `skills/writing-plans/SKILL.md`, `skills/iterating-plans/SKILL.md`, `skills/plan-to-execution/SKILL.md`, all read fully at planning time)
- Research findings: none
- Key implementation files: `skills/writing-plans/references/plan-template.md:54-58,92-108,111-117` (phase structure, section order, rules), `skills/writing-plans/SKILL.md` (Workflow step 3, Plan Checklist), `skills/iterating-plans/SKILL.md:33-53,91` (rationalizations, red flags, step 6), `skills/plan-to-execution/SKILL.md:17-22` (consumption contract being fed), `PLANS/2026-07-26-plan-to-execution-plan.md:51,59-61` (deferral decision this plan fulfills), `skills/writing-skills/references/pressure-testing.md:68-99,140-166` (campaign protocol)
