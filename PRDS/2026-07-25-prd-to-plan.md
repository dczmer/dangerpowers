---
artifact: prd
date: 2026-07-25
git_commit: e70aebac8416adba54f7adaac7c54c6b2c961eb7
branch: master
request: "create a prd to describe requirements for a new skill. this skill will be a planning and preparation skill orchestrator. it will guide the user and agent through: 1. input: PRD document and optional user prompt with additional instructions 2. using the researching-codebase skill to map out relevant parts of the codebase and design architecture 3. transitioning to the scouting-codebase skill and producing a context bundle for planning. this should be able to run in a subagent to avoid polluting the orchestrator's context window. 4. transitioning to the writing-plans skill to write the plan file 5. presenting the plan to the user and working together to iterate on the plan until the user accepts (accepts the plan report is ready for human review, not setting the 'status' of the plan document)."
status: draft
---

# prd-to-plan Skill PRD

## 1. Problem & Context

This repository maintains a pipeline of skills — researching-codebase, scouting-context, writing-plans, iterating-plans — each producing one artifact that feeds the next. Today a user (or agent) must invoke each skill manually, remember the correct order, know which artifacts already exist, and keep track of which skill consumes which output. Running these skills inline in a single conversation also fills the orchestrating context window with research and scouting detail that is only needed transiently, degrading the quality of later planning work.

The prd-to-plan skill orchestrates this pipeline: given a PRD, it drives research, context scouting, and plan writing in the correct order, delegates heavy phases to subagents to keep its own context clean, and manages the user feedback loop on the resulting plan.

## 2. Goals & Non-Goals

- **Goals:**
  - Guide user and agent from an existing PRD to an accepted, human-review-ready plan through a single skill invocation.
  - Keep the orchestrator's context window small by delegating artifact-producing phases to subagents.
  - Reuse the existing pipeline skills unchanged rather than duplicating their logic.
  - Handle pre-existing research/context artifacts gracefully with user confirmation.
  - Manage plan iteration through user feedback until the user accepts the plan as ready for human review.
- **Non-goals:**
  - Writing or revising the PRD itself; the PRD is an input.
  - Executing the plan (executing-plans territory) or any code changes.
  - Setting the plan document's status field or replacing human review; user acceptance here means only "ready for human review."
  - Modifying the underlying pipeline skills' behavior.
  - Running pipeline phases in parallel; the pipeline is strictly sequential.

## 3. User Stories & Acceptance Scenarios

### P1: Full pipeline run from a PRD
- **Independent test:** Invoke the skill with a PRD and no existing artifacts; verify a plan file is produced and presented.
- **Scenario:** Given a PRD document exists, When the user invokes the skill with that PRD, Then the skill produces research findings, a context bundle, and a plan in that order, and presents the plan to the user.

### P2: Context isolation via subagents
- **Independent test:** Run the pipeline and inspect the orchestrator's context; verify phase detail lives in subagents.
- **Scenario:** Given the pipeline is running, When an artifact-producing phase executes, Then that phase runs in a subagent (where safe) and the orchestrator's context retains only artifact paths and phase status, not phase content.

### P3: Plan iteration loop
- **Independent test:** After a plan is presented, give feedback and verify the plan is revised via iterating-plans and re-presented.
- **Scenario:** Given a plan has been presented, When the user provides feedback, Then the skill applies the feedback via the iterating-plans skill and re-presents the revised plan, repeating until the user accepts.

### P4: Existing artifact handling
- **Independent test:** Invoke with a research-findings artifact already present; verify the user is asked before reuse or regeneration.
- **Scenario:** Given an upstream artifact for this PRD already exists, When the pipeline reaches that phase, Then the skill asks the user whether to reuse the existing artifact or regenerate it.

### P5: Optional user instructions
- **Independent test:** Invoke with a PRD plus additional instructions; verify the instructions reach each phase.
- **Scenario:** Given the user supplies additional instructions alongside the PRD, When each phase runs, Then those instructions are conveyed to that phase's skill invocation.

## 4. Requirements

- **FR-001:** The skill accepts two inputs: a PRD document and an optional free-text user prompt containing additional instructions.
- **FR-002:** The skill drives the pipeline in fixed order: researching-codebase, then scouting-context, then writing-plans.
- **FR-003:** Each artifact-producing phase runs in a subagent so that phase detail does not enter the orchestrator's context window, subject to FR-004.
- **FR-004:** Before delegating a phase to a subagent, the skill verifies delegation is safe — in particular, if the phase's skill itself spawns subagents and nested subagents are unsupported, that phase runs inline in the orchestrator instead.
- **FR-005:** After each phase, the skill verifies the expected artifact was produced before transitioning to the next phase; on failure it surfaces the problem to the user rather than proceeding silently.
- **FR-006:** When an upstream artifact for this PRD already exists, the skill asks the user whether to reuse it or regenerate it before running that phase.
- **FR-007:** The optional user instructions are passed through to every phase's skill invocation.
- **FR-008:** After writing-plans completes, the skill presents the plan to the user for review.
- **FR-009:** When the user gives feedback on the plan, the skill applies it by invoking the iterating-plans skill, then re-presents the revised plan; this loop repeats until the user accepts.
- **FR-010:** User acceptance concludes the skill; it does not set the plan document's status field and does not trigger execution.
- **FR-011:** The orchestrator's retained context per phase is limited to artifact paths and phase outcomes.

## 5. Scope

- **In scope:** orchestration of researching-codebase, scouting-context, writing-plans, and iterating-plans; subagent delegation with safety checks; existing-artifact prompts; the user feedback/acceptance loop on the plan.
- **Out of scope:** PRD authoring, prompt-shaping, plan execution, changes to the pipeline skills themselves, parallel phase execution.

## 6. Assumptions & Constraints

- The pipeline is strictly sequential; each phase's artifact feeds the next (confirmed by the user via the pipeline description).
- Plan revision during the feedback loop goes through the iterating-plans skill, not direct edits by the orchestrator (user-confirmed).
- All phases should run in subagents, but subagent-nesting safety must be verified first because at least one pipeline skill spawns its own subagents (user-confirmed concern).
- Pre-existing artifacts are handled by asking the user each time, never by silent reuse or silent regeneration (user-confirmed).
- The skill's name is prd-to-plan (user-confirmed).

## 7. Edge Cases

- **PRD input missing or not a PRD:** the skill stops and tells the user a PRD is required rather than proceeding.
- **A phase fails or produces no artifact:** the skill reports the failure and the phase at which it occurred, and does not advance.
- **Nested subagents unsupported:** the affected phase runs inline, and the skill notes the fallback to the user.
- **User rejects the plan repeatedly:** the iteration loop continues; there is no maximum-attempts cutoff imposed by the skill.
- **User supplies instructions conflicting with the PRD:** the skill surfaces the conflict to the user rather than silently choosing one.

## 8. Success Criteria

- **SC-001:** A user can go from an existing PRD to an accepted plan through one skill invocation without manually invoking any pipeline skill.
- **SC-002:** After a full run, the orchestrator's context contains no research findings or context-bundle content — only artifact paths and phase outcomes.
- **SC-003:** Every pipeline phase transition is preceded by verification that the previous phase's artifact exists.
- **SC-004:** Plan feedback from the user is reflected in a revised plan via iterating-plans without the user invoking that skill directly.
- **SC-005:** No phase runs silently over a pre-existing artifact; the user is asked first in every such case.

## 9. Open Questions

None.
