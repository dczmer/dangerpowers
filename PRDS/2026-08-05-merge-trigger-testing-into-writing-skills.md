---
artifact: prd
date: 2026-08-05
git_commit: ee02e96e9db3e03f8abb96754577eccfc3173395
branch: dev/sloptime
request: "help me write a prd to integrate the trigger-testing skill into the writing-skills skill. the writing-skills skill optionally triggers a trigger testing campaign by loading the trigger-testing skill directly. but trigger-testing should be implemented as a reference file, like the pressure-testing campaign, and only loaded if/when the user chooses to run the trigger test. requirements: trigger-testing merged into writing-skills; trigger-testing directory and previous test evals or campaign artifacts are deleted. trigger-testing reference file only loads if the user chooses to start a campaign. look for duplication between the skills. if the content belongs in SKILL.md (authoring) then it should only live there. if the content belongs in trigger-testing.md (campaigns) then it should only live there. if it is important to both phases, then it should live in SKILL.md and the reference file should point back to it. resolve any orphaned or conflicting rules in both files. the user should be able to invoke trigger-testing an existing skill directly, like we do with the pressure-testing campaign currently. it should read the whole SKILL.md into context and jump to the trigger-testing part. a pressure-test campaign has been run over the updated skill to verify it picks up requests for trigger tests. a final step should be to review the skill and reference files for duplication, inconsistency, rules in the wrong places/files, cohesion between the skill and reference file workflows, orphaned rules, etc. it should use a subagent with a clean context to do this analysis."
status: approved
---

# Merge trigger-testing into writing-skills PRD

## 1. Problem & Context

The repo previously split skill-authoring guidance across three skills: `writing-skills` (how to author a skill), `pressure-testing` (RED-GREEN-REFACTOR campaigns against discipline rules), and `trigger-testing` (description eval campaigns). A recent merge folded `pressure-testing` back into `writing-skills` as an on-demand reference file. `trigger-testing` remains a standalone skill with the same coupling problems:

- The `writing-skills` main file contains description-authoring rules (imperative opener, WHAT + WHEN, no workflow summary, YAML safety, trigger terms woven into prose) that `trigger-testing` also states — duplicated guidance that can drift.
- The `writing-skills` main file directs the reader to load the `trigger-testing` skill for trigger evals, so part of its documented workflow lives in a second skill the reader must know to invoke.
- The `trigger-testing` skill carries campaign-only content (eval query design, harness protocol, optimization loop, contamination rules) in an always-loaded main file, and cross-references `writing-skills` for authoring rules it depends on.

The maintainer wants `trigger-testing` folded into `writing-skills` exactly the way `pressure-testing` was: campaign instructions in an on-demand reference file, authoring rules in the main file, no duplication, no orphaned or conflicting rules.

## 2. Goals & Non-Goals

- **Goals:**
  - One skill covers authoring a skill, pressure-testing it, and trigger-testing its description, with no duplicated content, no orphaned instructions, and no inconsistency between the main file and its reference files.
  - Trigger-campaign instructions (eval query design, train/validation split, optimization loop, harness protocol, contamination rules, results logging) live in an on-demand reference file loaded only when a campaign runs.
  - A user can trigger-test any existing skill's description by asking, without naming or knowing about a second skill.
  - The campaign tooling the trigger-test harness depends on survives the merge and remains under the merged skill's ownership.
  - The merge is verified: a pressure-test campaign runs against the merged skill's new discipline rules, and a clean-context reviewer confirms the result is coherent.
- **Non-goals:**
  - Running a trigger-eval campaign against the merged skill's updated description — that verification is deferred to a later session.
  - Changing the trigger-testing methodology itself (eval set sizes, split ratios, rep counts, pass criteria) beyond the rewrite needed to consolidate it into one skill.
  - Updating any other skill in the repo.
  - Preserving `trigger-testing`'s historical campaign logs or eval sets.

## 3. User Stories & Acceptance Scenarios

### P1: Author a skill end-to-end in one place
- **Independent test:** invoke the merged skill to write a new skill; verify the flow covers authoring and offers a trigger eval without loading any other skill.
- **Scenario:** Given a user asks to create a new skill, When the authoring flow finishes, Then the user is asked whether they want to run a trigger eval, and answering "no" ends the flow cleanly.

### P1: Trigger-test an existing skill by asking
- **Independent test:** invoke the merged skill with a trigger-test request against an existing skill; verify the campaign begins directly.
- **Scenario:** Given a user says "trigger test the test-skill skill", When the merged skill loads, Then after reading the skill's own main file for context it jumps directly to the trigger-testing campaign instructions and begins the campaign against the named target skill.

### P2: Campaign instructions stay out of the always-loaded file
- **Independent test:** read the merged skill's main file; confirm it contains no trigger-campaign-execution instructions.
- **Scenario:** Given the merged skill exists, When an agent loads only its main file, Then every instruction that applies solely to running a trigger-testing campaign is absent from that file and present in the on-demand reference file instead.

### P2: The old standalone skill is gone
- **Independent test:** list the repo's skills; confirm `trigger-testing` no longer exists as a loadable skill.
- **Scenario:** Given the merge is complete, When the repo's skills are enumerated, Then no `trigger-testing` skill, campaign logs, or eval sets remain.

## 4. Requirements

- **FR-001:** Merge `trigger-testing` into `writing-skills` as a single skill named `writing-skills`, mirroring the structure used for the pressure-testing merge.
- **FR-002:** The merged skill's trigger-testing campaign instructions live in the skill's on-demand reference file (a `trigger-testing` reference within the skill's references directory), loaded only when a campaign runs — through the direct-invocation branch or the opt-in end-of-flow prompt.
- **FR-003:** Instructions that apply only to executing a trigger-testing campaign (eval query design, train/validation split, optimization loop, harness protocol, contamination rules, multi-skill campaigns, done criteria, results logging) must not appear in the merged skill's main file.
- **FR-004:** Description-authoring rules (imperative opener, WHAT + WHEN, no workflow summary, YAML safety, trigger terms woven into prose, length limit) live only in the merged skill's main file. Where campaign content depends on those rules, the reference file points back to the main file rather than restating them. Content important to both phases lives in the main file; campaign-only content lives only in the reference file.
- **FR-005:** The end-of-flow opt-in prompt offering a trigger eval is preserved, but on "yes" it loads the trigger-testing reference file within the merged skill instead of invoking a separate skill.
- **FR-006:** The merged skill's description and invocation branch are updated so that requests to trigger-test an existing skill (e.g. "trigger test the <name> skill") load the merged skill, which reads its entire main file for context and then jumps directly to the trigger-testing campaign instructions — mirroring the existing pressure-testing invocation branch, including the cannot-find-target behavior.
- **FR-007:** The description boundary clause that currently distinguishes pressure-testing requests from "trigger-testing's description evals" is rewritten, since both campaign types now live in one skill; the description must route both request types to the merged skill.
- **FR-008:** The campaign tooling the trigger-test harness depends on (the eval-runner tooling and the dedicated evaluator agent definition) is preserved and relocated under the merged skill's ownership; all references to its old location are fixed.
- **FR-009:** The `trigger-testing` skill directory is deleted entirely, including its skill definition, its test-campaign logs, and its trigger-eval sets. Eval sets and campaign logs belonging to other skills (stored in those skills' own directories) are untouched.
- **FR-010:** Campaign content is rewritten and tightened during the move (not moved verbatim), resolving duplication with authoring guidance, resolving any orphaned or conflicting rules across both files, and fixing all cross-references that previously pointed at the standalone `trigger-testing` skill.
- **FR-011:** A pressure-test campaign is performed against the merged `writing-skills` skill covering any new or edited discipline rules introduced by the merge.
- **FR-012:** A final review of the merged skill and both reference files is performed by a subagent with a clean context, checking for duplication, inconsistency, rules in the wrong file, cohesion between the main-file workflow and the reference-file workflows, and orphaned rules.

## 5. Scope

- **In scope:**
  - Merging `trigger-testing` into `writing-skills` per FR-001 through FR-010.
  - Deleting the `trigger-testing` skill directory and all its contents.
  - Relocating and re-pointing the trigger-test harness tooling and evaluator agent.
  - The pressure-test verification campaign against the merged skill (FR-011) and the clean-context final review (FR-012).
- **Out of scope:**
  - A trigger-eval campaign against the merged skill's new description (deferred to a later session).
  - Migrating or preserving `trigger-testing`'s historical campaign logs and eval sets.
  - Changes to any other skill's content; references to `trigger-testing` in other skills' files or in historical plans are not rewritten (they describe past states).
  - Changes to the pressure-testing reference file beyond what deduplication and consistency require.

## 6. Assumptions & Constraints

Confirmed with the user during the PRD interview:

- The harness tooling (eval-runner and evaluator agent) is kept and relocated under the merged skill's ownership; only the standalone skill, its evals, and its campaign logs are deleted.
- Verification is a pressure-test campaign covering new discipline rules only; the trigger eval of the updated description is explicitly deferred to a later session.
- The phrase "trigger test the <name> skill" remains a direct invocation route into the merged skill, mirroring how pressure-testing invocation works today.

## 7. Edge Cases

- **User invokes the merged skill to trigger-test a skill that does not exist:** the invocation branch must report that the target cannot be found, same as the pressure-testing branch — never invent a target.
- **User declines the trigger-eval end-of-flow prompt:** the authoring flow ends cleanly with no campaign started, and any untested description is reported as untested.
- **Description boundary between campaign types:** with both campaigns in one skill, a request like "test the X skill" is ambiguous; the merged skill's workflow must resolve which campaign applies (discipline rules vs. description routing) rather than picking one silently.
- **References to the old `trigger-testing` skill elsewhere:** cross-references inside the merged skill's own files are fixed per FR-010; references in other skills' files or historical plans are out of scope.
- **Pure-reference skills:** the existing rule that trigger evals apply to every skill (including pure reference) must survive the merge intact.

## 8. Success Criteria

- **SC-001:** Exactly one skill exists where `writing-skills` and `trigger-testing` existed before; enumerating the repo's skills shows `writing-skills` and no `trigger-testing`.
- **SC-002:** Asking to "trigger test the <name> skill" loads the merged `writing-skills` skill and a campaign against the named target begins without the user naming any second skill.
- **SC-003:** The merged skill's main file contains no trigger-campaign-execution instructions, and the reference file contains no restated description-authoring rules, confirmed by the clean-context review.
- **SC-004:** A campaign log exists for the pressure test of the merged `writing-skills` skill covering the new discipline rules introduced by the merge.
- **SC-005:** The clean-context subagent review reports no duplication, no orphaned or conflicting rules, no rules in the wrong file, and coherent cohesion between the main-file workflow and both reference-file workflows.
- **SC-006:** The trigger-eval end-of-flow prompt can be declined and the authoring flow still completes.
- **SC-007:** The relocated harness tooling remains functional — a trigger-test campaign can still be executed end-to-end after the merge.

## 9. Open Questions

None.
