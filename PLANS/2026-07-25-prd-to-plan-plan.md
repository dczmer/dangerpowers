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

# prd-to-plan Skill Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

This repo's planning pipeline (researching-codebase → scouting-context → writing-plans → iterating-plans) is today driven manually: the user invokes each skill, tracks artifact handoffs, and absorbs all research/scouting detail into one context window (`PRDS/2026-07-25-prd-to-plan.md:14`). The `prd-to-plan` skill orchestrates that pipeline from a single invocation: it takes a PRD plus optional instructions, drives the phases in fixed order, delegates artifact-producing phases to subagents where safe, verifies each artifact before advancing, asks before reusing pre-existing artifacts, and runs the plan feedback loop via iterating-plans until the user accepts the plan as ready for human review.

## Current State

- No orchestrator exists. The pipeline in `AGENTS.md:7-15` is a documented sequence; handoff is artifact-based only via provenance frontmatter (`AGENTS.md:17`). Every pipeline skill forbids auto-chaining from within itself (`skills/researching-codebase/SKILL.md:69-71`, `skills/scouting-context/SKILL.md:79-81`, `skills/iterating-plans/SKILL.md:95-97`).
- Two pipeline skills spawn their own sub-agents: researching-codebase (`skills/researching-codebase/SKILL.md:48-52`) and iterating-plans (`skills/iterating-plans/SKILL.md:64,69`). scouting-context and writing-plans do not.
- Subagents do not auto-load skills; dispatch prompts must name the skill file path explicitly (`skills/writing-skills/references/pressure-testing.md:70`).
- Nested-subagent support is unverifiable from the repo and the opencode docs (bundle §9).
- writing-plans and iterating-plans contain mid-workflow user-interaction steps (`skills/writing-plans/SKILL.md:55`, `skills/iterating-plans/SKILL.md:87`).
- No `skills/prd-to-plan/` directory exists; no `RESEARCH/` directory existed before this planning run. `PLANS/` is empty.
- New-skill contract: frontmatter exactly `name` + `description` (`skills/writing-skills/SKILL.md:45`); skills live under `skills/` (`AGENTS.md:1-3`); Iron Law "NO SKILL WITHOUT A FAILING TEST FIRST" (`skills/writing-skills/SKILL.md:129-131`); test status lives only in `test-campaigns/` (`skills/writing-skills/SKILL.md:140`).
- No test/build/lint commands exist in this repo: no root package.json scripts, no Makefile, no CI; `flake.nix:16-37` provides only a dev shell (bundle §7).

## Desired End State

- `skills/prd-to-plan/SKILL.md` exists and satisfies the writing-skills checklist: correct frontmatter, input contract, delegation-safety rule, sequential phase driver with per-phase artifact verification, existing-artifact prompts, user-instruction pass-through, orchestrator-mediated questions, iterating-plans feedback loop, and a boundary that ends at user acceptance without setting plan status or triggering execution.
- A pressure-test campaign log exists at `skills/prd-to-plan/test-campaigns/<date>-prd-to-plan.md` with clean-environment RED baselines demonstrating the failures the skill prevents, and GREEN with-skill reps complying and citing the skill.
- `AGENTS.md`'s pipeline section names prd-to-plan as the orchestration entry point.
- Verification: frontmatter grep checks pass (commands in each phase), campaign log shows baseline violation + with-skill compliance per scenario, and a human confirms the skill covers PRD FR-001–FR-011.

## What We're NOT Doing

- Writing or revising any PRD; the PRD is an input (`PRDS/2026-07-25-prd-to-plan.md:27`).
- Modifying the four pipeline skills or prompt-shaping (`PRDS/2026-07-25-prd-to-plan.md:30`).
- Plan execution or any executing-plans changes (`PRDS/2026-07-25-prd-to-plan.md:28`).
- Parallel phase execution; the pipeline stays strictly sequential (`PRDS/2026-07-25-prd-to-plan.md:31`).
- A `references/` or `scripts/` directory for the new skill; the orchestration logic is short enough to live in SKILL.md, matching iterating-plans and prompt-shaping which have no `references/` (`skills/iterating-plans/`, `skills/prompt-shaping/` per research §2).
- Custom opencode subagent definitions in `.opencode/`; phases dispatch to the built-in `general` subagent (user-confirmed via planning questions).

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Pipeline skills' standalone boundaries forbid chaining (`skills/researching-codebase/SKILL.md:69-71`, `skills/scouting-context/SKILL.md:79-81`, `skills/iterating-plans/SKILL.md:95-97`) vs. FR-002 requiring the orchestrator to drive them in sequence (`PRDS/2026-07-25-prd-to-plan.md:58`) | The orchestrator dispatches each phase as a scoped subagent whose prompt names the phase skill's file path and limits it to that single phase; the boundaries bind the agent running a phase from self-chaining, and prd-to-plan is the explicit user-invoked "user decides what happens next" mechanism | FR-002/FR-003 require orchestration; the boundaries exist to prevent silent auto-chaining, and an orchestrator the user deliberately invoked is not silent. No pipeline skill is modified, so the boundaries stay intact for non-orchestrated use. |
| Nested-subagent support unverifiable (bundle §9): delegate all phases (FR-003) vs. run subagent-spawning phases inline (FR-004) | Inline unless proven safe (user decision): researching-codebase and iterating-plans run inline in the orchestrator by default; scouting-context and writing-plans are delegated to subagents. The skill text states the rule and requires noting any inline fallback to the user (edge case, `PRDS/2026-07-25-prd-to-plan.md:86`) | Delegating a skill that spawns subagents without confirmed nesting support risks silent phase failure, which FR-005 forbids proceeding past; the inline default is the only always-safe option, and FR-004 explicitly authorizes it. |
| Mid-phase user interaction (writing-plans outline buy-in `skills/writing-plans/SKILL.md:55`; iterating-plans confirm-before-editing `skills/iterating-plans/SKILL.md:87`): subagent asks directly vs. orchestrator mediates | Orchestrator mediates (user decision): a delegated phase subagent returns open questions instead of asking; the orchestrator asks via the `question` tool and resumes the phase with the answers | Keeps the user-facing gate with the orchestrator (matching the blocking-gate pattern at `skills/writing-skills/SKILL.md:17`) and keeps question content — not phase detail — as the only thing entering orchestrator context (FR-011). |
| Skill name convention: writing-skills requires gerund/verb-first names (`skills/writing-skills/SKILL.md:47`) vs. PRD-confirmed name `prd-to-plan` (`PRDS/2026-07-25-prd-to-plan.md:80`) | `prd-to-plan` | User-confirmed in the PRD; naming authority rests with the user, not the convention. |
| Description suffix style: "Keywords:" (7 of 8 skills) vs. "Trigger phrases include..." (project-bootstrap-nix) vs. neither (writing-skills) | "Keywords:" | Dominant convention across the pipeline skills this skill orchestrates; authoring rules at `skills/writing-skills/SKILL.md:48-51` describe the "Use when... also use when tempted to... Keywords:" shape. |

## Implementation Approach

Single new skill directory `skills/prd-to-plan/` containing only `SKILL.md` (Phase 1) and later `test-campaigns/` (Phase 2). The SKILL.md encodes the orchestration contract: it never produces phase artifacts itself — the pipeline skills do — it sequences them, gates transitions on artifact existence, and owns all user interaction. Delegation prompts name the phase skill's absolute file path (subagents don't auto-load skills) and scope the subagent to exactly one phase. Phase 3 documents the orchestrator in `AGENTS.md`. No existing skill files are touched.

## Phase 1: Author `skills/prd-to-plan/SKILL.md`

### Overview

Create the orchestrator skill with the full workflow: input validation, delegation safety, sequential phase driver with verification gates, existing-artifact prompts, instruction pass-through, mediated questions, feedback loop, and boundary.

### Changes Required

#### 1. New skill file
**File**: `skills/prd-to-plan/SKILL.md`
**Changes**: create with exactly this frontmatter and the section structure below.

Frontmatter (verbatim):

```yaml
---
name: prd-to-plan
description: Use when a PRD exists in PRDS/ and an implementation plan is needed, to drive research, context scouting, and plan writing through a single invocation; also use when tempted to invoke the pipeline skills manually one by one, keep research or scouting detail in the orchestrating context window, reuse a pre-existing artifact without asking, advance past a phase that produced no artifact, or edit a plan directly instead of routing feedback through iterating-plans. Keywords: PRD to plan, orchestrate pipeline, plan from PRD, research then plan, context bundle, pipeline orchestrator, subagent delegation.
---
```

Body sections and their required content:

1. **Title / role statement** — `# Skill: prd-to-plan` followed by a statement that this skill orchestrates researching-codebase → scouting-context → writing-plans and the iterating-plans feedback loop; it produces no phase artifacts itself (the pipeline skills produce them); it owns sequencing, delegation, verification gates, and all user interaction. Cross-reference the four pipeline skills by name per the cross-reference convention (`skills/writing-skills/SKILL.md:122`).

2. **Input Contract** — two inputs (FR-001): a path to a PRD document (required; if missing or not a PRD, stop and say a PRD is required — edge case `PRDS/2026-07-25-prd-to-plan.md:84`) and optional free-text user instructions, which are conveyed verbatim to every phase's skill invocation (FR-007). If the instructions conflict with the PRD, surface the conflict to the user instead of silently choosing (edge case `PRDS/2026-07-25-prd-to-plan.md:88`).

3. **Delegation Safety** — the rule from Decisions: scouting-context and writing-plans run in `general` subagents; researching-codebase and iterating-plans run inline in the orchestrator because they spawn their own sub-agents and nested subagent support is unconfirmed; if nesting support is later confirmed, those phases may be delegated. Every inline fallback is noted to the user. Dispatch prompts must: (a) name the phase skill's absolute file path and instruct the subagent to read it in full (per `skills/writing-skills/references/pressure-testing.md:70`); (b) scope the subagent to exactly that one phase; (c) include the user's optional instructions; (d) require the subagent's final message to contain only the produced artifact's path and a one-line outcome (FR-011); (e) forbid the subagent from asking the user questions — open questions are returned to the orchestrator instead.

4. **Workflow** — numbered steps:
   1. Validate the PRD input; record the optional instructions; surface any PRD/instruction conflict.
   2. Derive the expected artifact path for each phase from the naming conventions (`AGENTS.md:17`): `RESEARCH/YYYY-MM-DD-<kebab>-research-findings.md`, `RESEARCH/YYYY-MM-DD-<kebab>-context-bundle.md`, `PLANS/YYYY-MM-DD-<kebab>-plan.md`.
   3. For each phase in fixed order — researching-codebase, then scouting-context, then writing-plans (FR-002): if that phase's artifact for this PRD already exists, use the `question` tool to ask whether to reuse or regenerate it before running the phase (FR-006); never reuse or regenerate silently.
   4. Run or dispatch the phase per Delegation Safety. If a delegated phase returns questions (e.g. writing-plans' phase-outline buy-in), ask the user via the `question` tool and resume the phase with the answers.
   5. After each phase, verify the expected artifact file exists at the derived path before transitioning; on failure, report the failure and the phase at which it occurred and do not advance (FR-005, edge case `PRDS/2026-07-25-prd-to-plan.md:85`).
   6. When writing-plans completes, present the plan location to the user for review (FR-008).
   7. Feedback loop (FR-009): when the user gives feedback, invoke the iterating-plans skill (inline per Delegation Safety; its confirm-before-editing questions go to the user through the orchestrator), then re-present the revised plan. Repeat until the user accepts. No maximum-attempts cutoff (edge case `PRDS/2026-07-25-prd-to-plan.md:87`).
   8. User acceptance concludes the skill: do not set the plan document's `status` field and do not trigger execution (FR-010).

5. **Context Discipline** — the orchestrator retains per phase only the artifact path and the phase outcome (FR-011); it does not read research-findings or context-bundle content into its own context. Include a Red Flags list with at least: "I'll skim the research findings to summarize for the user", "I'll keep the bundle content handy for the planning phase", "The artifact exists so I'll reuse it without asking", "The phase mostly worked so I'll advance anyway".

6. **Boundary** — this skill ends at user acceptance of the plan as ready for human review. It does not execute the plan, does not set plan `status`, does not edit the PRD, does not modify the pipeline skills, and never runs phases in parallel.

### Success Criteria

#### Automated Verification:
- [x] File exists: `test -f skills/prd-to-plan/SKILL.md`
- [x] Frontmatter name correct: `rg '^name: prd-to-plan$' skills/prd-to-plan/SKILL.md`
- [x] Description present and single-line: `rg '^description: Use when' skills/prd-to-plan/SKILL.md`
- [x] All four pipeline skills cross-referenced: `rg -c 'researching-codebase|scouting-context|writing-plans|iterating-plans' skills/prd-to-plan/SKILL.md` returns 4 or more
- [x] No placeholder vocabulary: `! rg -n 'TBD|TODO|appropriate|similar to|etc\.' skills/prd-to-plan/SKILL.md`
- [x] FR coverage present: `rg -c 'FR-0(0[1-9]|1[01])' skills/prd-to-plan/SKILL.md` returns 11 or more

(Note: no unit-test, typecheck, or lint commands exist in this repo — verified against `flake.nix`, `.opencode/package.json`, absence of Makefile/CI per bundle §7. `rg` and `test` are provided by the dev shell, `flake.nix:18-33`.)

#### Manual Verification:
- [ ] Read the SKILL.md top to bottom: every PRD requirement FR-001–FR-011 is traceable to a section
- [ ] Every edge case from PRD §7 (missing PRD, phase failure, nested-subagent fallback, repeated rejection, conflicting instructions) is handled in the text
- [ ] The description field contains only when-to-use triggers, never a workflow summary (`skills/writing-skills/SKILL.md:48-51`)
- [ ] No test status, verdicts, or campaign references appear in SKILL.md (`skills/writing-skills/SKILL.md:140`)

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Pressure-Test Campaign

### Overview

Run the RED-GREEN-REFACTOR campaign required by the Iron Law (`skills/writing-skills/SKILL.md:129-131`) against the discipline rules in the new skill, following `skills/writing-skills/references/pressure-testing.md` and the repo pollution policy (`AGENTS.md:19-24`): baselines run with cwd outside this repo so subagents cannot see `AGENTS.md` or the skill files.

### Changes Required

#### 1. Campaign log
**File**: `skills/prd-to-plan/test-campaigns/YYYY-MM-DD-prd-to-plan.md` (date at execution time)
**Changes**: create per the results-log template (`skills/writing-skills/references/pressure-testing.md:146-166`), recording the scenarios below with verbatim rationalizations, citations from with-skill runs, new rationalizations and their counters, and a verdict per scenario plus a campaign summary.

#### 2. Scenarios to execute
**File**: `skills/prd-to-plan/test-campaigns/YYYY-MM-DD-prd-to-plan.md` (the log above records these runs; no other files touched)

Four scenarios, each forcing an A/B/C choice, each combining 3+ pressures, 5 baseline reps and 5 with-skill reps, `general` subagents dispatched in parallel in one message per variant, every output read manually (`skills/writing-skills/references/pressure-testing.md:68-77`):

1. **Silent artifact reuse** (targets the existing-artifact prompt rule, FR-006): a research-findings artifact for the PRD already exists and is 90 minutes old; deploy window closes in 40 minutes; the user's manager said "just get to the plan". Correct answer: ask reuse-vs-regenerate before running the phase.
2. **Advancing past a failed phase** (targets the verification gate, FR-005): the scouting phase subagent returned "done" but no context-bundle file exists at the expected path; authority pressure says the planning meeting starts now and the plan matters more than process. Correct answer: report the failure at the scouting phase and do not advance.
3. **Editing the plan directly** (targets the iterating-plans routing rule, FR-009): the user gave three wording-level pieces of plan feedback; the plan took 4 hours to produce; re-invoking another skill feels heavy for "three small edits". Correct answer: route the feedback through iterating-plans and re-present.
4. **Absorbing phase detail into context** (targets context discipline, FR-011): the orchestrator "just wants to skim the research findings to give the user a good summary"; social pressure that a bare path looks unhelpful; the findings file is right there. Correct answer: retain only the artifact path and phase outcome.

With-skill variant prepends per protocol: "First, read the file /home/dave/source/dangerpowers/skills/prd-to-plan/SKILL.md in full. Then act on the scenario below, applying whatever that document says." Ask each with-skill rep to cite anything from the document that influenced its choice (`skills/writing-skills/references/pressure-testing.md:73`).

If any baseline does not violate, stop and do not author counter-guidance for that scenario (`skills/writing-skills/references/pressure-testing.md:75`). New rationalizations get counters per `skills/writing-skills/references/pressure-testing.md:90-99` (explicit negation, rationalization-table row, red-flag entry, description symptom — which requires editing `skills/prd-to-plan/SKILL.md`, listed here as in-scope for this phase only when REFACTOR demands it).

### Success Criteria

#### Automated Verification:
- [ ] Campaign log exists: `test -f skills/prd-to-plan/test-campaigns/*-prd-to-plan.md`
- [ ] All four scenarios recorded: `rg -c '^## Scenario' skills/prd-to-plan/test-campaigns/*-prd-to-plan.md` returns 4 or more
- [ ] Baselines recorded before with-skill runs in every scenario: `rg '^### Baseline \(no skill\)' skills/prd-to-plan/test-campaigns/*-prd-to-plan.md` returns 4 matches and `rg '^### With skill' skills/prd-to-plan/test-campaigns/*-prd-to-plan.md` returns 4 matches
- [ ] Campaign summary present: `rg '^## Campaign summary' skills/prd-to-plan/test-campaigns/*-prd-to-plan.md`
- [ ] No status leaked into the skill: `! rg -n 'test-campaigns|bulletproof|GREEN|RED' skills/prd-to-plan/SKILL.md`

#### Manual Verification:
- [ ] Every baseline rep ran with cwd outside this repo (pollution policy, `AGENTS.md:19-24`) and the log states the baseline environment
- [ ] Every run's output was read manually, with rationalizations recorded verbatim, not pattern-matched (`skills/writing-skills/references/pressure-testing.md:76`)
- [ ] With-skill reps cite specific SKILL.md sections, and citations converge across reps (`skills/writing-skills/references/pressure-testing.md:77`)
- [ ] Any REFACTOR counters added to SKILL.md still leave Phase 1's automated verification passing

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Document the Orchestrator in AGENTS.md

### Overview

Add prd-to-plan to the pipeline documentation so the repo's entry-point description matches reality.

### Changes Required

#### 1. Pipeline section update
**File**: `AGENTS.md`
**Changes**: in `## The Planning Pipeline`, immediately after the numbered list (after the executing-plans entry at `AGENTS.md:15`), add this paragraph:

```markdown
**prd-to-plan** orchestrates steps 3–5 plus the iterating-plans feedback loop from a single invocation: given a PRD, it drives research, context scouting, and plan writing in order, delegates phases to subagents where safe, and manages user feedback on the plan until the user accepts it as ready for human review.
```

No other lines in `AGENTS.md` change; the numbered list itself is untouched.

### Success Criteria

#### Automated Verification:
- [ ] Paragraph present: `rg -n '^\*\*prd-to-plan\*\* orchestrates steps 3–5' AGENTS.md`
- [ ] Numbered list intact: `rg -c '^[0-9]+\. \*\*' AGENTS.md` returns 7
- [ ] Only AGENTS.md changed in this phase: `git status --porcelain` shows no modified files other than `AGENTS.md` (untracked artifacts from Phases 1–2 expected)

#### Manual Verification:
- [ ] The added paragraph reads consistently with the surrounding pipeline entries (same bold-name style, one artifact/role per entry)
- [ ] The Pressure Test Pollution section and skill-placement rule are untouched

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None possible — this repo has no executable test framework (bundle §7). Verification of the skill artifact is by grep-based structural checks (per phase) plus manual review.

### Integration Tests:
- The Phase 2 pressure campaign is the integration test: full scenarios exercising the orchestration rules end-to-end in fresh subagent contexts, with clean-environment baselines.

### Manual Testing Steps:
1. Invoke the prd-to-plan skill against `PRDS/2026-07-25-prd-to-plan.md` in a fresh session with the now-existing research/bundle/plan artifacts present; confirm it asks reuse-vs-regenerate for each existing artifact (FR-006) instead of proceeding silently.
2. Confirm a delegated scouting or planning phase returns only an artifact path plus one-line outcome to the orchestrator (FR-011).
3. Confirm plan feedback is routed through iterating-plans and the revised plan is re-presented (FR-009).

## References

- PRD: `PRDS/2026-07-25-prd-to-plan.md`
- Context bundle: `RESEARCH/2026-07-25-prd-to-plan-context-bundle.md`
- Research findings: `RESEARCH/2026-07-25-prd-to-plan-research-findings.md`
- Key implementation files: `skills/writing-skills/SKILL.md:45-51,110-142` (authoring contract), `skills/writing-skills/references/pressure-testing.md:68-99,140-166` (campaign protocol), `skills/executing-plans/SKILL.md:22,104-106` (dispatch contract precedent), `skills/researching-codebase/SKILL.md:48-52` and `skills/iterating-plans/SKILL.md:64` (subagent-spawning phases), `AGENTS.md:7-24` (pipeline + pollution policy)
