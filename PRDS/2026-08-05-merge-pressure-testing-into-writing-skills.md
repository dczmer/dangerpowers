---
artifact: prd
date: 2026-08-05
git_commit: 94a7a06099b91b9d8f8291a41a826b76ef45765a
branch: dev/sloptime
request: "help me write a PRD to merge the writing-skills, pressure-testing, and trigger-testing skills. we previously split the writing-skills skill into writing-skills and pressure-testing, then i added a trigger-testing skill designed to go with these. but i think the contents of writing-skills and pressure-testing are too intwined and should become one skill again. we should leave trigger-testing a separate skill for now, but it has similar problems to a lesser extent. many of the rules and instructions in the writing-skills SKILL.md file are about interperting test results and updating the skill according to pressure-test evals, but the actual testing process is completely divorced from this skill. this creates a system where pressure-testing skill has to duplicate the instructions from writing-skills or else the pressure-testing skill is incomplete and the writing-skills skill contains instructions that it cannot use. analyze both skills carefully. we want to merge these skills together without duplication, orphaned instructions, or inconsistency."
status: approved
---

# Merge pressure-testing into writing-skills PRD

## 1. Problem & Context

The repo's skill-authoring guidance was previously split into two skills: `writing-skills` (how to author a skill) and `pressure-testing` (how to run a RED-GREEN-REFACTOR campaign against a discipline skill). A third skill, `trigger-testing`, was added later for description eval campaigns.

The split is broken in both directions:

- The `writing-skills` SKILL.md contains rules about interpreting test results and updating a skill per pressure-test outcomes (form-to-failure matching, rationalization plugging, bulletproofing discipline skills) — but the actual campaign process lives in another skill, so those instructions sit in a file whose reader cannot act on them.
- The `pressure-testing` skill must duplicate or cross-reference `writing-skills` content (e.g. "Match the Form to the Failure") to be complete — so it is either redundant or incomplete.

The result is duplication, orphaned instructions, and inconsistency risk between two files that describe one intertwined process. The user who maintains these skills wants them merged back into one skill. `trigger-testing` has similar coupling problems to a lesser extent, but stays a separate skill for now.

## 2. Goals & Non-Goals

- **Goals:**
  - One skill covers both authoring a skill and pressure-testing it, with no duplicated content, no orphaned instructions, and no inconsistency between the main file and its reference material.
  - Campaign-execution instructions (scenario design, execution protocol, rationalization plugging, results logging) live in an on-demand reference file, not in the always-loaded main skill file.
  - A user can pressure-test any existing skill by asking, without naming or knowing about a second skill.
  - The merge is verified: a pressure-test campaign runs against the merged skill, and a clean-context reviewer confirms the result is coherent.
- **Non-goals:**
  - Merging `trigger-testing` into `writing-skills`, or restructuring `trigger-testing`'s content.
  - Changing the pressure-testing methodology itself (RED-GREEN-REFACTOR, scenario design rules, rep counts) beyond the rewrite needed to consolidate it into one skill.
  - Updating any other skill in the repo.
  - Preserving `pressure-testing`'s historical test-campaign logs or eval sets.

## 3. User Stories & Acceptance Scenarios

### P1: Author a skill end-to-end in one place
- **Independent test:** invoke the merged skill to write a new discipline skill; verify the flow covers authoring and offers pressure testing without loading any other skill.
- **Scenario:** Given a user asks to create a new discipline skill, When the authoring flow finishes, Then the user is asked whether they want to start pressure testing, and answering "no" ends the flow cleanly.

### P1: Pressure-test an existing skill by asking
- **Independent test:** invoke the merged skill with a pressure-test request against an existing skill; verify the campaign begins directly.
- **Scenario:** Given a user says "pressure test the test-skill skill", When the merged skill loads, Then after reading the skill's own main file for context it jumps directly to the pressure-testing campaign instructions and begins the campaign against the named target skill.

### P2: Campaign instructions stay out of the always-loaded file
- **Independent test:** read the merged skill's main file; confirm it contains no campaign-execution instructions.
- **Scenario:** Given the merged skill exists, When an agent loads only its main file, Then every instruction that applies solely to running a pressure-testing campaign is absent from that file and present in the on-demand reference file instead.

### P2: The old standalone skill is gone
- **Independent test:** list the repo's skills; confirm `pressure-testing` no longer exists as a loadable skill.
- **Scenario:** Given the merge is complete, When the repo's skills are enumerated, Then no `pressure-testing` skill, campaign logs, or eval sets remain.

## 4. Requirements

- **FR-001:** Merge `writing-skills` and `pressure-testing` into a single skill named `writing-skills`. `trigger-testing` remains a separate skill.
- **FR-002:** The merged skill's pressure-testing campaign instructions live in the skill's on-demand reference file (`references/pressure-testing.md` within the skill's directory).
- **FR-003:** Instructions that apply only to executing a pressure-testing campaign (scenario design, execution protocol, rationalization plugging, results logging, multi-skill campaigns, done criteria) must not appear in the merged skill's main file.
- **FR-004:** At the end of the skill-authoring flow, the merged skill prompts the user whether they want to start pressure testing, and the user may opt out.
- **FR-005:** The same end-of-flow prompt also offers a trigger eval as an opt-in, replacing the current unconditional "run the trigger-testing skill manually" direction. Both prompts are opt-in; opting out of either ends the flow cleanly.
- **FR-006:** The merged skill's description is updated so that requests to pressure-test an existing skill trigger it. Add a couple of simple trigger phrases for this; do not copy the `pressure-testing` skill's description text.
- **FR-007:** When the merged skill is invoked to pressure-test an existing skill, its workflow jumps directly to the pressure-testing campaign after reading the entirety of the merged skill's main file for context.
- **FR-008:** The `pressure-testing` skill directory is deleted entirely, including its skill definition, its existing test-campaign logs, and its trigger-eval sets.
- **FR-009:** Campaign content is rewritten and tightened during the move (not moved verbatim), resolving duplication with authoring guidance and fixing all cross-references that previously pointed at the standalone `pressure-testing` skill.
- **FR-010:** A pressure-test campaign is performed against the merged `writing-skills` skill itself, and as part of that campaign the merged skill is verified to trigger on phrases like "pressure test the test-skill skill".
- **FR-011:** A subagent with a clean context reviews the completed merged skill for consistency and for soundness of the end-to-end process of writing and/or pressure-testing a skill.
- **FR-012:** The merged result contains no duplicated instructions, no instructions orphaned from the process they belong to, and no contradictory guidance between the main file and the reference file.

## 5. Scope

- **In scope:**
  - Merging `writing-skills` and `pressure-testing` into one skill per FR-001 through FR-009.
  - Deleting the `pressure-testing` skill directory and all its contents.
  - The verification campaign against the merged skill (FR-010) and the clean-context review (FR-011).
  - The opt-in end-of-flow prompts for pressure testing and trigger eval.
- **Out of scope:**
  - Any change to `trigger-testing`'s own content or structure.
  - Merging `trigger-testing` into `writing-skills`.
  - Migrating or preserving `pressure-testing`'s historical campaign logs and eval sets.
  - Changes to any other skill, agent, or repo tooling.

## 6. Assumptions & Constraints

Confirmed with the user during the PRD interview:

- The `pressure-testing` skill directory is deleted entirely — skill definition, test-campaign logs, and trigger-eval sets alike.
- Verification of the merge is a pressure-test campaign only; triggering on the new phrases is verified as part of that campaign. No separate trigger-eval campaign is required for this work.
- Both pressure testing and trigger eval become opt-in end-of-flow prompts in the merged skill.
- The campaign content is rewritten and tightened during the move, not moved verbatim.

## 7. Edge Cases

- **Target skill has no violable rule:** the campaign instructions' existing scope rule (pure-reference skills are not pressure-testable) must survive the merge; invoking a pressure test against such a skill reports that pressure testing does not apply.
- **User opts out of both end-of-flow prompts:** the authoring flow ends cleanly with no campaign started.
- **User invokes the merged skill to pressure-test a skill that does not exist:** the campaign flow must surface this rather than inventing a target. (Behavior: report the target cannot be found.)
- **References to the old `pressure-testing` skill elsewhere:** any cross-references inside the merged skill's own files are fixed per FR-009; references in other skills' files are out of scope.

## 8. Success Criteria

- **SC-001:** Exactly one skill exists where `writing-skills` and `pressure-testing` existed before; enumerating the repo's skills shows `writing-skills` and no `pressure-testing`.
- **SC-002:** Asking to "pressure test the <name> skill" loads the merged `writing-skills` skill and a campaign against the named target begins without the user naming any second skill — demonstrated in the verification campaign log.
- **SC-003:** The merged skill's main file contains no campaign-execution-only instructions, confirmed by the clean-context review.
- **SC-004:** A campaign log exists for the pressure test of the merged `writing-skills` skill, recording that it triggered on phrases like "pressure test the test-skill skill".
- **SC-005:** The clean-context subagent review reports no duplication, no orphaned instructions, and no inconsistencies in the merged skill's writing and pressure-testing process.
- **SC-006:** Both end-of-flow prompts (pressure testing, trigger eval) can be declined and the flow still completes.

## 9. Open Questions

None.
