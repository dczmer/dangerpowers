---
name: prd-to-plan
description: Use when a PRD exists in PRDS/ and an implementation plan is needed, to drive research, context scouting, and plan writing through a single invocation; also use when tempted to invoke the pipeline skills manually one by one, keep research or scouting detail in the orchestrating context window, reuse a pre-existing artifact without asking, advance past a phase that produced no artifact, or edit a plan directly instead of routing feedback through iterating-plans. Keywords: PRD to plan, orchestrate pipeline, plan from PRD, research then plan, context bundle, pipeline orchestrator, subagent delegation.
---

# Skill: prd-to-plan

This skill orchestrates the planning pipeline: **researching-codebase** → **scouting-context** → **writing-plans**, plus the **iterating-plans** feedback loop. It produces no phase artifacts itself — the pipeline skills produce them. This skill owns sequencing, delegation, verification gates, and all user interaction.

## Input Contract

Two inputs (FR-001):

1. **Path to a PRD document** (required). If it is missing or is not a PRD, stop and tell the user a PRD is required. Do not proceed on a guessed or implied document.
2. **Optional free-text user instructions.** Convey these verbatim to every phase's skill invocation (FR-007). If the instructions conflict with the PRD, surface the conflict to the user and wait for a resolution — never silently pick one side.

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

## Workflow

1. Validate the PRD input. Record the optional instructions. Surface any PRD/instruction conflict to the user before doing anything else.
2. Derive the expected artifact path for each phase from the naming conventions: `RESEARCH/YYYY-MM-DD-<kebab>-research-findings.md`, `RESEARCH/YYYY-MM-DD-<kebab>-context-bundle.md`, `PLANS/YYYY-MM-DD-<kebab>-plan.md`.
3. For each phase in fixed order — researching-codebase, then scouting-context, then writing-plans (FR-002): if that phase's artifact for this PRD already exists, use the `question` tool to ask whether to reuse or regenerate it **before** running the phase (FR-006). Never reuse silently. Never regenerate silently.
4. Run or dispatch the phase per Delegation Safety. If a delegated phase returns questions (e.g. writing-plans' phase-outline buy-in), ask the user via the `question` tool and resume the phase with the answers. The orchestrator mediates all user interaction; subagents never ask directly.
5. After each phase, verify the expected artifact file exists at the derived path before transitioning (FR-005). On failure, report the failure and the phase at which it occurred, and do not advance.
6. When writing-plans completes, present the plan location to the user for review (FR-008).
7. Feedback loop (FR-009): when the user gives feedback, invoke the **iterating-plans** skill (inline per Delegation Safety; its confirm-before-editing questions go to the user through the orchestrator), then re-present the revised plan. Repeat until the user accepts. There is no maximum-attempts cutoff.
8. User acceptance concludes the skill. Do not set the plan document's `status` field. Do not trigger execution (FR-010).

## Context Discipline

The orchestrator retains per phase only the artifact path and the phase outcome (FR-011). It does not read research-findings or context-bundle content into its own context — that detail belongs to the subagents and to the pipeline skills that consume those artifacts.

### Red Flags - STOP

- "I'll skim the research findings to summarize for the user"
- "I'll keep the bundle content handy for the planning phase"
- "The artifact exists so I'll reuse it without asking"
- "The phase mostly worked so I'll advance anyway"
- "These three edits are small; I'll just fix the plan myself"

## Boundary

This skill ends at user acceptance of the plan as ready for human review. It does not execute the plan, does not set plan `status`, does not edit the PRD, does not modify the pipeline skills, and never runs phases in parallel.
