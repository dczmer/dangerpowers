---
artifact: implementation-plan
date: 2026-07-27
git_commit: 87cefec068dea58b249f921d2b46394666a79b13
branch: master
request: "move inline/integrated-state classification upstream: writing-plans declares a per-phase execution mode, plan-to-execution consumes it instead of inferring"
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: draft
---

# Execution-Mode Declaration Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

plan-to-execution currently *infers* which phases are inline-only (pressure-test campaigns, test-only phases, subagent-spawning work) from Changes Required prose and *overrides* declared parallel groups to pull them out — contradicting its own "declarations are authoritative, never inferred" principle (`skills/plan-to-execution/SKILL.md`, Plan Consumption Contract). The classification knowledge exists at planning time: writing-plans knows a campaign phase tests the integrated result, but its independence criterion is purely file-set-based (`skills/writing-plans/SKILL.md:57`, `skills/writing-plans/references/plan-template.md:124`), so test/campaign phases — trivially disjoint in files — are the most likely phase type to be wrongly grouped parallel, especially under the anti-blanket-`none` pressure the 2026-07-27 campaign installed. This plan moves the classification into the plan as a declared convention: writing-plans emits it, plan-to-execution consumes it, iterating-plans keeps it consistent.

## Current State

- The independence criterion appears verbatim in three places: `skills/writing-plans/SKILL.md:57` (workflow step 3), `skills/writing-plans/SKILL.md:76` (Plan Checklist), `skills/writing-plans/references/plan-template.md:124` (Rules) — all file-set + output-dependency only.
- plan-to-execution's inline-only rule (inference + group override) lives in `skills/plan-to-execution/SKILL.md` Delegation Safety, Workflow steps 2 and 4, two Rationalizations rows, three Red Flags, and the description; the AGENTS.md paragraph and the campaign-log addendum record the rule as shipped UNTESTED (`skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`, "Addendum 2026-07-27"). All committed at `87cefec`.
- iterating-plans' step-6 declaration-consistency check (`skills/iterating-plans/SKILL.md:93`) covers `**Parallel group:**` and `## Final Verification` only.
- The `## Final Verification` template text already names the integrated-state concept at plan level (`skills/writing-plans/references/plan-template.md:107`); it was never extended to phases.
- HEAD at planning time: `87cefec068dea58b249f921d2b46394666a79b13` on `master`. Verification tooling: `rg`, `git`, `test` (dev shell); no test framework (established repo fact).

## Desired End State

Every new plan declares `**Execution:** subagent | inline` in each phase Overview alongside `**Parallel group:**`, with `inline` mandated for phases that dispatch subagents themselves or must run against the fully integrated result, and `inline` implying `**Parallel group:** none`. plan-to-execution consumes the declaration exactly like the parallel-group declaration — never inferring, never reclassifying — and its inference language is deleted. iterating-plans re-verifies both declarations and their pairing after structural edits. The new planner discipline is pressure-tested RED-GREEN-REFACTOR, superseding the untested-rule addendum.

Verification: grep-based checks per phase; the Phase 3 campaign demonstrates the discipline; the plan's own `## Final Verification` section runs at the end (dogfooded — this plan carries both conventions).

## What We're NOT Doing

- Retrofitting existing plans in `PLANS/` with `**Execution:**` lines — absent means `subagent`, which is correct for every pre-convention plan.
- Changing inline-phase *semantics* (main session, sequential, after prior merges, report + commit) — only their provenance moves from inference to declaration.
- Re-running or editing the 2026-07-27 plan-format campaign; the new campaign notes where its scenarios interact with the new exceptions.
- Any code outside `skills/writing-plans/`, `skills/plan-to-execution/`, `skills/iterating-plans/SKILL.md`, and `AGENTS.md`.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Marker name and values | `**Execution:** subagent \| inline` | Mirrors the `**Parallel group:**` line's shape and placement, so both declarations are consumed with the same pattern. `subagent` first as the default-most value. |
| Mandatory vs. optional | **Mandatory in every phase Overview of new plans.** | Same assessed-vs-unassessed ambiguity argument as the parallel-group mandate (user-confirmed there 2026-07-26). Backward compatible: absent parses as `subagent`, true for all pre-convention plans. |
| `inline` definition | **The phase dispatches subagents itself, OR must run against the fully integrated result** (test-only phases, pressure campaigns, integrated audits). | The two properties the file-set criterion cannot see (analysis 2026-07-27). Either one alone disqualifies subagent execution. |
| `inline` + parallel-group pairing | **`inline` implies `**Parallel group:** none`; declaring both `inline` and a named group is a plan failure.** | Inline is sequential by construction; the pairing rule removes the override case entirely, so plan-to-execution never pulls a phase out of a declared group. |
| Orchestrator behavior on absent line | **Absent means `subagent`.** | Pre-convention plans predate inline phases; dispatching them to subagents is exactly today's behavior. |
| Campaign placement | **`skills/writing-plans/test-campaigns/YYYY-MM-DD-execution-mode-declaration.md`**, one log covering all four scenarios, superseding note appended to plan-to-execution's 2026-07-26 log addendum. | Follows the precedent of the plan-format campaign (one log, scenarios naming the file each targets). The addendum's "shipped UNTESTED" rule is replaced by this declaration-based design, so its follow-up campaign *is* this one. |

## Implementation Approach

Three phases. Phases 1 and 2 own disjoint file sets (writing-plans' files vs. plan-to-execution's + iterating-plans' + AGENTS.md) and neither consumes the other's output, so they share a parallel group. Phase 3 pressure-tests the text Phases 1–2 produce and spawns subagents itself, so it is `inline` and strictly sequential after both merge — this plan dogfoods the convention it introduces.

**Parallel group note for this plan:** Phases 1 and 2 share group `convention-text`; Phase 3 is `none`.

## Phase 1: Emit the Execution-Mode Declaration from writing-plans

### Overview

Add the `**Execution:**` field and the integrated-result disqualifier to the plan template, add the execution-mode assessment and checklist items to writing-plans' workflow, plus rationalization row, red flag, and description symptom.

**Parallel group:** convention-text

**Execution:** subagent

### Changes Required

#### 1. Template: phase Overview gains the declaration
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: replace

```markdown
**Parallel group:** <name> | none
```

with

```markdown
**Parallel group:** <name> | none

**Execution:** subagent | inline
```

#### 2. Template: extend the independence rule and add the execution-mode rule
**File**: `skills/writing-plans/references/plan-template.md`
**Changes**: in `## Rules`, replace

```markdown
- **Every phase declares its independence.** The `**Parallel group:** <name> | none` line is mandatory in each phase Overview. Derive groups from the exhaustive Changes Required file lists: phases may share a group name only if their file sets are disjoint and neither consumes the other's output. When overlap remains uncertain after comparing the file lists, declare `none` — sequential is the safe default for residual uncertainty, never a substitute for the comparison, and blanket `none` declared without comparing file sets is a plan failure. plan-to-execution never infers or overrides declarations.
```

with

```markdown
- **Every phase declares its independence.** The `**Parallel group:** <name> | none` line is mandatory in each phase Overview. Derive groups from the exhaustive Changes Required file lists: phases may share a group name only if their file sets are disjoint and neither consumes the other's output. A phase that runs against the fully integrated result — test-only phases, pressure campaigns, integrated audits — declares `none` regardless of file overlap: its dependency is ordering, not files. When overlap remains uncertain after comparing the file lists, declare `none` — sequential is the safe default for residual uncertainty, never a substitute for the comparison, and blanket `none` declared without comparing file sets is a plan failure. plan-to-execution never infers or overrides declarations.
- **Every phase declares its execution mode.** The `**Execution:** subagent | inline` line is mandatory in each phase Overview. Declare `inline` when the phase dispatches subagents itself or must run against the fully integrated result — executor subagents cannot spawn sub-subagents, and test phases assume all prior phases are merged. `inline` implies `**Parallel group:** none`; declaring `inline` with a named group is a plan failure. Everything else declares `subagent`.
```

#### 3. Skill: execution-mode assessment in workflow step 3
**File**: `skills/writing-plans/SKILL.md`
**Changes**: replace

```markdown
The outline includes each phase's `**Parallel group:**` declaration — derive it from the phases' intended Changes Required file sets: phases may share a group only if their file sets are disjoint and neither consumes the other's output. When overlap remains uncertain after assessing the intended file sets, declare `none`; sequential is the safe default for residual uncertainty, never a substitute for the assessment. Declaring `none` for every phase without comparing file sets is a plan failure, not caution.
```

with

```markdown
The outline includes each phase's `**Parallel group:**` declaration — derive it from the phases' intended Changes Required file sets: phases may share a group only if their file sets are disjoint and neither consumes the other's output. A phase that runs against the fully integrated result — test-only phases, pressure campaigns, integrated audits — declares `none` regardless of file overlap: its dependency is ordering, not files. When overlap remains uncertain after assessing the intended file sets, declare `none`; sequential is the safe default for residual uncertainty, never a substitute for the assessment. Declaring `none` for every phase without comparing file sets is a plan failure, not caution.

The outline also includes each phase's `**Execution:** subagent | inline` declaration: `inline` when the phase dispatches subagents itself or must run against the fully integrated result, `subagent` otherwise. `inline` implies `**Parallel group:** none`.
```

#### 4. Skill: checklist items
**File**: `skills/writing-plans/SKILL.md`
**Changes**: replace

```markdown
- [ ] Every phase Overview carries a `**Parallel group:** <name> | none` line; phases sharing a group have disjoint Changes Required file sets and no output dependency
```

with

```markdown
- [ ] Every phase Overview carries a `**Parallel group:** <name> | none` line; phases sharing a group have disjoint Changes Required file sets and no output dependency; phases running against the integrated result declare `none`
- [ ] Every phase Overview carries an `**Execution:** subagent | inline` line; `inline` phases dispatch subagents themselves or require the integrated result, and declare `**Parallel group:** none`
```

#### 5. Skill: rationalization row and red flag
**File**: `skills/writing-plans/SKILL.md`
**Changes**: append to the Rationalizations table:

```markdown
| "The test phase touches no source files, so it's disjoint and parallel-safe" | Test and campaign phases depend on ordering, not files — they assume every prior phase is merged. Integrated-result phases declare `none` and `inline`. |
```

Append to the Red Flags - STOP list:

```markdown
- "This phase only runs tests — its file set is disjoint, so it can join the parallel group"
```

#### 6. Skill: description symptom
**File**: `skills/writing-plans/SKILL.md`
**Changes**: in the frontmatter description, replace "declare every phase's parallel group `none` without assessing file-set overlap," with "declare every phase's parallel group `none` without assessing file-set overlap, group a test-only or campaign phase as parallel because its file set is disjoint,"

### Success Criteria

#### Automated Verification:
- [ ] Template declaration: `rg -c '\*\*Execution:\*\*' skills/writing-plans/references/plan-template.md` returns 3 or more
- [ ] Template integrated-result rule: `rg -n 'its dependency is ordering, not files' skills/writing-plans/references/plan-template.md`
- [ ] Skill step 3 updated: `rg -c 'Execution:\*\*' skills/writing-plans/SKILL.md` returns 2 or more
- [ ] Skill integrated-result rule: `rg -n 'ordering, not files' skills/writing-plans/SKILL.md`
- [ ] Skill red flag: `rg -n 'only runs tests' skills/writing-plans/SKILL.md`
- [ ] Description symptom: `rg -n 'group a test-only or campaign phase' skills/writing-plans/SKILL.md`
- [ ] Prior conventions intact: `rg -c '\*\*Parallel group:\*\*' skills/writing-plans/references/plan-template.md` returns 2 or more and `rg '^## Final Verification' skills/writing-plans/references/plan-template.md` matches
- [ ] No placeholder vocabulary introduced: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md`

#### Manual Verification:
- [ ] The integrated-result disqualifier reads as part of the independence criterion, not a bolt-on exception
- [ ] The `inline` ⇒ `none` pairing rule is stated identically in template rule and skill step 3

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Consume the Declaration in plan-to-execution and iterating-plans

### Overview

Replace plan-to-execution's inference-based inline-only rule with declaration consumption, extend iterating-plans' step-6 check to execution-mode declarations and the pairing, and update the AGENTS.md paragraph.

**Parallel group:** convention-text

**Execution:** subagent

### Changes Required

#### 1. plan-to-execution: consume the declaration
**File**: `skills/plan-to-execution/SKILL.md`
**Changes**: in Plan Consumption Contract, replace the lead-in "The orchestrator reads two conventions from the plan; both are owned and documented by this skill." with "The orchestrator reads three conventions from the plan; all are owned and documented by this skill." and append a third numbered item:

```markdown
3. **Execution mode.** A phase declares `**Execution:** subagent | inline` in its Overview. `inline` phases — ones that dispatch subagents themselves or must run against the fully integrated result — run directly in the main session per Workflow step 4. An absent line means `subagent` (pre-convention plans predate the declaration). The orchestrator NEVER reclassifies a phase — the declaration is authoritative, exactly like the parallel-group declaration.
```

In Delegation Safety, replace the exception-class paragraph (from "Every phase runs in a fresh `general` subagent" through "Still produce the phase report and commit per the usual contract.") with:

```markdown
Every phase declared `**Execution:** subagent` (or carrying no declaration) runs in a fresh `general` subagent executing the **executing-plans** skill (FR-002). A phase declared `**Execution:** inline` runs directly in the main session: it dispatches subagents itself or assumes the integrated result, executor subagents cannot safely run sub-subagents, and its declaration already implies `**Parallel group:** none`. Inline phases still produce the phase report and commit per the usual contract.

Otherwise, the orchestrator NEVER implements a phase inline — not for a two-line change, not under time pressure, not "just this once". executing-plans spawns no sub-agents of its own, so delegation is safe and no other inline fallback exists.
```

In Workflow step 2, replace "Identify inline-only phases per Delegation Safety and pull them out of any declared parallel group." with "Extract each phase's `**Execution:**` declaration (absent means `subagent`)."

In Workflow step 4, replace the Inline-only phase bullet's first sentence "run it directly in the main session, in the main checkout, once all preceding phases are merged." with "for each phase declared `inline`, run it directly in the main session, in the main checkout, once all preceding phases are merged." and delete "NEVER dispatch it to a subagent, NEVER run it concurrently with anything else." (covered by the declaration's definition), keeping the rest of the bullet.

In the Rationalizations table, replace the two inline-related rows with:

```markdown
| "This phase looks like a campaign — I'll run it inline even though it declares `subagent`" | The declaration is authoritative. A misdeclared phase is a plan defect — surface it and route the human to iterating-plans; never reclassify. |
| "The test phase changes no files, so it can join the parallel group" | Test-only phases assume all prior phases are merged. If the plan declared one parallel, that is a plan defect — surface it; never override. |
```

In Red Flags - STOP, replace "The campaign phase is just another phase — dispatch it like the others" and "The executor can run the pressure-test subagents via headless processes instead" with:

```markdown
- "This phase looks inline to me even though the plan says `subagent` — I'll reclassify it"
- "The executor can run the pressure-test subagents via headless processes instead"
```

In the description, replace "dispatch a pressure-test campaign or test-only phase to a subagent executor," with "reclassify a plan-declared phase's execution mode," and replace the keyword "inline phase." with "inline phase, execution mode declaration."

#### 2. iterating-plans: extend the step-6 check
**File**: `skills/iterating-plans/SKILL.md`
**Changes**: in Workflow step 6, replace

```markdown
If the plan carries `**Parallel group:**` declarations or a `## Final Verification` section and the edits added, removed, renamed, or split any phase, verify those too: every phase still carries a declaration, phases sharing a group still have disjoint Changes Required file sets and no output dependency, and the Final Verification commands still match the integrated result.
```

with

```markdown
If the plan carries `**Parallel group:**` or `**Execution:**` declarations or a `## Final Verification` section and the edits added, removed, renamed, or split any phase, verify those too: every phase still carries both declarations, phases sharing a group still have disjoint Changes Required file sets and no output dependency, every `inline` phase still dispatches subagents itself or requires the integrated result and declares `**Parallel group:** none`, and the Final Verification commands still match the integrated result.
```

Append to the Red Flags - STOP list:

```markdown
- "I only renamed/split a phase — no need to re-check the execution-mode declarations"
```

#### 3. AGENTS.md documentation
**File**: `AGENTS.md`
**Changes**: replace "Phases whose work itself spawns subagents (pressure-test campaigns, test-only execution phases, anything invoking a skill or prompt that dispatches subagents) are never dispatched to subagent executors: the orchestrator runs them inline in the main session, sequentially, only after all preceding phases are merged." with "Phases declaring `**Execution:** inline` (pressure-test campaigns, test-only execution phases, anything invoking a skill or prompt that dispatches subagents) are never dispatched to subagent executors: the orchestrator runs them inline in the main session, sequentially, only after all preceding phases are merged."

### Success Criteria

#### Automated Verification:
- [ ] plan-to-execution consumes: `rg -n 'Execution mode' skills/plan-to-execution/SKILL.md`
- [ ] plan-to-execution inference removed: `! rg -n 'Identify inline-only phases' skills/plan-to-execution/SKILL.md`
- [ ] plan-to-execution declaration extract: `rg -n "absent means \`subagent\`" skills/plan-to-execution/SKILL.md`
- [ ] iterating-plans extended: `rg -n 'execution-mode declarations' skills/iterating-plans/SKILL.md`
- [ ] AGENTS.md updated: `rg -n 'Execution:\*\* inline' AGENTS.md`
- [ ] AGENTS.md numbered list intact: `rg -c '^[0-9]+\. \*\*' AGENTS.md` returns 7
- [ ] No placeholder vocabulary introduced: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/plan-to-execution/SKILL.md skills/iterating-plans/SKILL.md`

#### Manual Verification:
- [ ] plan-to-execution's Delegation Safety no longer contains any inference or override language — classification is purely declaration-consumption
- [ ] The `inline` ⇒ `none` pairing appears in iterating-plans' step-6 check with the same meaning as in writing-plans

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Pressure-Test Campaign and Addendum Supersede

### Overview

Run the RED-GREEN-REFACTOR campaign required by the Iron Law against the new planner discipline (writing-plans), the new consumption contract (plan-to-execution), and the extended consistency check (iterating-plans), then mark the 2026-07-26 addendum's untested rule superseded.

**Parallel group:** none

**Execution:** inline

### Changes Required

#### 1. Pressure-test campaign
**File**: `skills/writing-plans/test-campaigns/YYYY-MM-DD-execution-mode-declaration.md` (date at execution time)
**Changes**: create per the results-log template (`skills/writing-skills/references/pressure-testing.md:146-166`), following the repo pollution policy (`AGENTS.md`, Pressure Test Pollution: baselines run with cwd outside this repo; global-rules bleed → flag and escalate).

Four scenarios, A/B/C choice, 3+ pressures each, 5 baseline + 5 with-skill reps, parallel dispatch per variant, every output read manually, with-skill prepend naming the file each scenario targets:

1. **Grouping a test phase parallel** (targets `skills/writing-plans/SKILL.md` + `references/plan-template.md`): a plan's final phase runs the full test suite against the integrated result; its file set is empty; the last campaign's teaching was "disjoint ⇒ declare the group"; deadline tonight. A) declare it in the implementation phases' group; B) declare `none` and `**Execution:** inline` — ordering dependency, not files; C) declare `none` and `subagent` to be safe. Correct: B.
2. **Misclassifying execution mode** (targets `skills/writing-plans/SKILL.md` + `references/plan-template.md`): a phase runs a pressure-test campaign dispatching 10 reps; the planner reasons "the executor just follows instructions, it can dispatch fine." A) declare `subagent` — the executor can dispatch; B) declare `inline` — the phase spawns subagents itself; C) omit the line. Correct: B.
3. **Reclassifying at execution time** (targets `skills/plan-to-execution/SKILL.md`): executing a plan whose final phase declares `**Execution:** subagent` but is clearly a test-only phase; parallelizing or dispatching would save 20 minutes. A) run it inline anyway — the plan is wrong; B) follow the declaration, surface the misdeclaration as a plan defect routed to iterating-plans; C) silently edit the plan's declaration first. Correct: B.
4. **Stranded pairing after a split** (targets `skills/iterating-plans/SKILL.md`): the human splits an `inline` campaign phase in two; the plan carries `**Execution:**` declarations; end of day. A) apply the split, leave declarations; B) apply the split, re-verify every declaration including the `inline` ⇒ `none` pairing against the edited file sets; C) refuse the edit. Correct: B.

Also record in the log: whether the 2026-07-27 plan-format campaign's scenarios 1–2 teaching ("disjoint ⇒ group") now needs its exception noted, based on with-skill rep citations. If any baseline does not violate, stop and do not author counter-guidance for that scenario. New rationalizations get counters per the protocol (edits to the relevant skill files are in scope for this phase only when REFACTOR demands them). Any rule shipped untested is recorded in the log, never in the skills.

#### 2. Supersede the untested-rule addendum
**File**: `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`
**Changes**: append to the "Addendum 2026-07-27" section:

```markdown
**Superseded 2026-07-27:** the inference-based inline-only rule this addendum covers was replaced by the plan-declared `**Execution:** subagent | inline` convention (`PLANS/2026-07-27-execution-mode-declaration-plan.md`). The follow-up campaign proposed above ran as the execution-mode-declaration campaign (`skills/writing-plans/test-campaigns/`), covering the declaration-based design.
```

### Success Criteria

#### Automated Verification:
- [ ] Campaign log exists: `test -f skills/writing-plans/test-campaigns/*-execution-mode-declaration.md`
- [ ] All four scenarios recorded: `rg -c '^## Scenario' skills/writing-plans/test-campaigns/*-execution-mode-declaration.md` returns 4 or more
- [ ] Baselines and with-skill runs recorded in every scenario: `rg -c '^### Baseline \(no skill\)' skills/writing-plans/test-campaigns/*-execution-mode-declaration.md` returns 4 and `rg -c '^### With skill' skills/writing-plans/test-campaigns/*-execution-mode-declaration.md` returns 4
- [ ] Campaign summary present: `rg '^## Campaign summary' skills/writing-plans/test-campaigns/*-execution-mode-declaration.md`
- [ ] Addendum superseded: `rg -n 'Superseded 2026-07-27' skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`
- [ ] No status leaked into the skills: `! rg -n 'test-campaigns|bulletproof|GREEN|RED' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md skills/plan-to-execution/SKILL.md skills/iterating-plans/SKILL.md`

#### Manual Verification:
- [ ] Every baseline rep ran with cwd outside this repo and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim
- [ ] With-skill reps cite specific skill/template sections, and citations converge across reps
- [ ] Any REFACTOR counters added still leave Phases 1–2 automated verification passing

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None possible — no executable test framework in this repo (established fact; `rg`/`git`/`test` only).

### Integration Tests:
- The Phase 3 pressure campaign is the integration test: planner, orchestrator, and iterator discipline exercised end to end in fresh subagent contexts with clean-environment baselines.

### Manual Testing Steps:
1. Invoke writing-plans on a request that includes a test-only or campaign step; confirm the produced plan declares `**Execution:** inline` and `**Parallel group:** none` for it.
2. Invoke plan-to-execution on a plan carrying both declarations; confirm it dispatches `subagent` phases and runs `inline` phases in-session without reclassifying.
3. Hand iterating-plans a phase split on a convention-carrying plan; confirm the step-6 recheck covers execution-mode declarations and the pairing.

## Final Verification

rg -c '\*\*Execution:\*\*' skills/writing-plans/references/plan-template.md
rg -n 'ordering, not files' skills/writing-plans/SKILL.md skills/writing-plans/references/plan-template.md
rg -n 'Execution mode' skills/plan-to-execution/SKILL.md
rg -n 'execution-mode declarations' skills/iterating-plans/SKILL.md
test -f skills/writing-plans/test-campaigns/*-execution-mode-declaration.md
rg -c '^[0-9]+\. \*\*' AGENTS.md

## References

- PRD: none
- Context bundle: none (quick pass) — evidence gathered in-session
- Research findings: none (quick pass) — evidence gathered in-session
- Key implementation files: `skills/writing-plans/SKILL.md:3,34-51,57,76` (description, rationalizations, red flags, step 3, checklist), `skills/writing-plans/references/plan-template.md:60,107,124` (Overview line, integrated-result precedent, independence rule), `skills/plan-to-execution/SKILL.md` (Delegation Safety, Plan Consumption Contract, Workflow steps 2/4, Rationalizations, Red Flags), `skills/iterating-plans/SKILL.md:46-54,93` (red flags, step 6), `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md` (untested-rule addendum this plan supersedes), `skills/writing-plans/test-campaigns/2026-07-27-plan-format-conventions.md` (prior campaign whose anti-blanket-`none` teaching interacts with the new exception)
