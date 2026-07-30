---
artifact: prd
date: 2026-07-30
git_commit: 5068d47cc65f6f04c56f0cab0e12054b64b91c3d
branch: dev/sloptime
request: i want to create a PRD for a feature that extracts the pressure-testing and trigger-testing processes into their own stand-alone skills.

read the skill file and both reference files completely.

the new pressure-testing skill:
- extract the pressure-testing.md file and convert it into a new skill
- remove the reference file from writing-skills as well as any instructions to automatically running the test.
- writing-skills should instruct the user that the new skill must be tested but do not automatically begin testing; the user will manually invoke the new skill
- should have everything needed to run a pressure test campaign on an individual target skill, or on a list of skills sequentially
- the new skill should be written using the exact process from writing-skills, minus the testing campaigns

the new trigger-testing skill:
- follow the same general process as for the new pressure-testing skill
- writing-skills should remind the user to run the tests, but not launch the new skill directly
- should carry best-practice rules for writing skill descriptions that may exist in the writing-skills SKILL.md and https://agentskills.io/skill-creation/optimizing-descriptions

the existing writing-skills skill:
- no longer launches testing campaigns automatically
- only references to the test campaigns are to mention that it's part of the process and to direct the user to run those tests manually to complete the skill creation process
status: approved
---

# Extract Pressure-Testing and Trigger-Testing into Standalone Skills PRD

## 1. Problem & Context

The skill-creation workflow in this repository's `writing-skills` skill currently bundles three concerns: how to author a skill, how to pressure-test discipline skills, and how to optimize a skill's trigger description. The two testing processes live as reference material inside `writing-skills`, and `writing-skills` instructs the agent to run those testing campaigns automatically as part of creating or editing a skill.

This coupling causes two problems:

1. **Unwanted automatic execution.** Testing campaigns are expensive (dozens of subagent dispatches) and the user wants to decide when to run them, not have them launch as an automatic step of skill authoring.
2. **Reusability.** The testing processes are useful beyond the authoring flow — a user should be able to run a pressure-test or trigger-test campaign against an existing skill, or against a list of skills, without going through skill authoring at all.

The fix is to extract each testing process into its own standalone skill, and reduce `writing-skills` to authoring-only guidance that reminds the user testing is required and directs them to run it manually.

## 2. Goals & Non-Goals

- **Goals:**
  - Two new standalone skills, `pressure-testing` and `trigger-testing`, each self-contained and manually invocable.
  - Both new skills support campaigning a single target skill and a list of skills run sequentially.
  - `writing-skills` no longer auto-launches testing campaigns; it retains the testing mandates and directs the user to run them manually via the new skills.
  - No testing content is lost in the extraction — everything needed to run each campaign type moves with its skill.
  - The `trigger-testing` skill also carries best-practice rules for writing skill descriptions, sourced from the existing `writing-skills` frontmatter guidance and the external description-optimization guidance at agentskills.io.
- **Non-goals:**
  - Testing the two new skills themselves (no self-test campaigns in this effort; deferred to a separate session after creation).
  - Changing the substance of the testing processes (RED-GREEN-REFACTOR protocol, eval-set design, harness mechanics, log formats) beyond what extraction requires.
  - Changing any skill other than `writing-skills` and the two new skills.
  - Automating or scheduling test campaign execution.

## 3. User Stories & Acceptance Scenarios

### P1: Standalone pressure-testing skill
- **Independent test:** invoke only the new pressure-testing skill against an existing skill and complete a campaign end-to-end without reading `writing-skills`.
- **Scenario:** Given a skill with discipline rules that has never been pressure-tested, When the user manually invokes the pressure-testing skill naming that target skill, Then the agent designs scenarios, runs baseline and with-skill campaigns per the established protocol, and writes a results log — without consulting `writing-skills`.

### P2: Standalone trigger-testing skill
- **Independent test:** invoke only the new trigger-testing skill against an existing skill and complete an eval campaign end-to-end without reading `writing-skills`.
- **Scenario:** Given a skill with an unoptimized description, When the user manually invokes the trigger-testing skill naming that target skill, Then the agent builds the eval set, runs the optimization loop and sanity check, and writes a trigger results log — without consulting `writing-skills`.

### P3: Sequential multi-skill campaigns
- **Independent test:** pass a list of skills to either new skill and observe each skill campaigned in turn.
- **Scenario:** Given a list of three target skills, When the user invokes the pressure-testing skill (or trigger-testing skill) with that list, Then campaigns run sequentially, one skill at a time, each producing its own results log.

### P4: Writing-skills no longer auto-tests
- **Independent test:** author a new skill via `writing-skills` and observe no test campaign launches.
- **Scenario:** Given a user creating a new skill with `writing-skills`, When the authoring checklist reaches the testing items, Then the agent tells the user the skill must be pressure-tested and/or trigger-tested and names the skill(s) to run manually — and does not begin any campaign itself.

### P5: No content lost in extraction
- **Independent test:** diff the union of the new skills' content against the removed reference material; every operational rule is accounted for.
- **Scenario:** Given the extraction is complete, When the new skills' content is compared against the material removed from `writing-skills`, Then every scenario-design rule, execution-protocol step, eval-design rule, harness mechanic, contamination rule, done criterion, and log format from the original material is present in exactly one of the new skills (or intentionally retained in `writing-skills` as an authoring rule).

## 4. Requirements

- **FR-001:** A new `pressure-testing` skill must exist, created using the `writing-skills` authoring process (minus its testing campaigns, per the user's instruction that self-testing is deferred).
- **FR-002:** The `pressure-testing` skill must contain everything needed to run a pressure-test campaign on a single named target skill: scope rules, RED-GREEN-REFACTOR protocol, scenario design, execution protocol, micro-tests, rationalization plugging, meta-testing, done criteria, common mistakes, and the results-log format.
- **FR-003:** The `pressure-testing` skill must support campaigning a list of skills sequentially, one at a time.
- **FR-004:** A new `trigger-testing` skill must exist, created using the `writing-skills` authoring process minus testing campaigns.
- **FR-005:** The `trigger-testing` skill must contain everything needed to run a trigger-eval campaign on a single named target skill: scope, eval query design, train/validation split, the optimization loop, harness mechanics, contamination rules, multi-skill campaign handling, done criteria, common mistakes, and the results-log format.
- **FR-006:** The `trigger-testing` skill must support campaigning a list of skills sequentially, one at a time.
- **FR-007:** The `trigger-testing` skill must carry best-practice rules for writing skill descriptions, incorporating the description guidance currently in `writing-skills` (frontmatter description rules) and the external description-optimization guidance at https://agentskills.io/skill-creation/optimizing-descriptions.
- **FR-008:** The pressure-testing reference material must be removed from `writing-skills` once extracted.
- **FR-009:** The trigger-optimization reference material must be removed from `writing-skills` once extracted.
- **FR-010:** `writing-skills` must no longer contain any instruction that automatically begins or launches a testing campaign.
- **FR-011:** `writing-skills` must retain the testing mandates (the Iron Law requiring a failing baseline before a discipline rule, and the Trigger Eval Rule requiring a passing eval set before a description ships) unchanged in force.
- **FR-012:** Where `writing-skills` references testing, it must state that testing is part of the skill-creation process and direct the user to run the appropriate standalone skill manually to complete the process.
- **FR-013:** `writing-skills` checklist items covering testing must be rewritten so they direct the user to manual testing rather than instructing the agent to perform campaign steps.
- **FR-014:** No testing-process content may be lost: content removed from `writing-skills` must be accounted for in the new skills (or explicitly retained as authoring guidance, such as the description-writing rules whose primary home remains `writing-skills`).

## 5. Scope

- **In scope:**
  - Creating the `pressure-testing` and `trigger-testing` skills in this repository's skills library.
  - Extracting the pressure-testing and trigger-optimization reference material from `writing-skills` into those skills.
  - Revising `writing-skills` so it retains testing mandates but never auto-runs campaigns, instead directing the user to invoke the new skills manually.
  - Moving description-writing best practices into `trigger-testing` (including content from the external agentskills.io guidance).
  - Single-skill and sequential list-based campaign support in both new skills.
- **Out of scope:**
  - Pressure-testing or trigger-testing the two new skills themselves (deferred to a separate session).
  - Any change to the testing methodologies themselves.
  - Changes to other skills in the repository.
  - Where description-writing guidance should primarily live if it appears in both places (that is a planning decision; the requirement is only that `trigger-testing` carries it).

## 6. Assumptions & Constraints

- The user confirmed the two new skills are **not** self-tested in this effort; testing them happens in a separate session after creation. (Confirmed 2026-07-30.)
- The user confirmed `trigger-testing` mirrors `pressure-testing`'s sequential list support. (Confirmed 2026-07-30.)
- The user confirmed `writing-skills` keeps the Iron Law and Trigger Eval Rule at full force, redirecting execution to manual invocation of the new skills. (Confirmed 2026-07-30.)
- The new skills live in this repository's skills library per the repo's AGENTS.md direction.
- Constraint: extraction must not break `writing-skills`' own validity or internal consistency — no dangling references to removed material.

## 7. Edge Cases

- **Authoring a pure-reference skill:** `writing-skills` currently exempts pure-reference skills from pressure testing but not from trigger evals; the revised guidance must preserve that distinction when directing the user to manual testing.
- **Authoring a skill with no discipline rules:** the manual-testing direction must still cover trigger testing, since it applies to every skill.
- **Editing an existing skill vs. creating a new one:** the manual-testing reminder applies to both, as the current mandates do.
- **Duplicated description guidance:** description best practices may reasonably appear in both `writing-skills` (authoring) and `trigger-testing` (optimization); the requirement is that `trigger-testing` carries them, not that they be deduplicated.
- **Untested-rule recording:** the existing convention that untested rules/descriptions are recorded as untested in the campaign log (never in the skill itself) must remain expressible in the new skills' log guidance.

## 8. Success Criteria

- **SC-001:** A user can run a complete pressure-test campaign on any single skill by invoking only the `pressure-testing` skill, with no reference to `writing-skills` needed.
- **SC-002:** A user can run a complete trigger-eval campaign on any single skill by invoking only the `trigger-testing` skill, with no reference to `writing-skills` needed.
- **SC-003:** Both new skills accept a list of skills and campaign them sequentially, producing one results log per target skill.
- **SC-004:** A full skill-authoring run via `writing-skills` completes without any test campaign being launched, while still telling the user testing is required and naming the skills to run.
- **SC-005:** Every operational rule present in the extracted reference material is found in the new skills (or intentionally retained in `writing-skills`); nothing is silently dropped.
- **SC-006:** All three skills (`writing-skills`, `pressure-testing`, `trigger-testing`) pass the repository's skill validation.
- **SC-007:** `writing-skills` contains no instruction that triggers automatic campaign execution; its only testing references state that testing is part of the process and direct manual invocation.

## 9. Open Questions

None.
