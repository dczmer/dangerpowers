---
artifact: prd
date: 2026-07-31
git_commit: 72416a8169ab650a341b4e82e63a03f52bf5591a
branch: dev/sloptime
request: |
  write a PRD to implement a new trigger-testing harness.

  the current testing process is implemented as a skill and a read-only agent. we target a set of test phrases and fire them against the loaded skill descriptions. the agent is supposed to report if it loaded the skill or not, without executing a full workflow. but this doesn't work well in practice, becasue either the full skill workflow starts or because the skill doesn't load and the agent starts trying to analyze the codebase or interview the user for more info. this causes the subagents to hang or to reach their step limit without reporting whether they loaded the skill or not.

  requirements for the new process:
  - bootstrap a temporary workspace directory and run the evals from that dir, so they only ever see 'stubs' of the skills under test, never the bodies.
  - this solution should fit into the existing trigger-testing skill and replace the current test harness and commands to something like `trigger-test.sh [--model MODEL] SCENARIO_TEXT`.
  - start by creating a tempfs directory for testing (TESTDIR)
  - create a .agents under $TESTDIR directory with skills/ and agents/ subdirectories
  - copy the skills and agents from a SOURCEDIR (example ./opencode in this project repo)
  - STUB the skill files - they should only have the yaml front-matter and no body that could begin executing a workflow
  - the test command should be like the following:
    opencode run --dir "$TEMPDIR" --agent trigger-evaluator --format json --model $MODEL "$SCENARIO"
  - model is only needed if specified by optional parameter; if not provided, omit this argument
  - if the scenario text is passed directly as a string argument to the command, it should use a `<<'EOF'` heredoc to avoid escaping and quoting issues.
  - if the scenario text is saved to a file, it needs to be under $TEMPDIR so that opencode will open it and not reject it as an external directory
  - detect if the skill loaded from the json output. if the agent reaches its step limit or times out without printing the skill tool invocation, the assume the trigger failed.
  - look for a message with type=tool, tool=skill, state.input.name=SKILL_NAME, or a message type=text, part.text="Skill loaded: SKILL_NAME"
  - detect and surface conflicts with other skills: if multiple skills are loaded or the wrong skill is loaded, then we may have to rework the descriptions of multiple skills if they are too similar to trigger the intended skill consistently.
status: approved
---

# Isolated Trigger-Testing Harness PRD

## 1. Problem & Context

Trigger-testing evaluates whether a skill's description causes the agent to load that skill for a given scenario phrase. The current process dispatches a read-only evaluator agent against the real skills library and asks it to report whether it loaded the target skill without executing the skill's workflow.

This fails in practice in both directions:

1. **The workflow starts.** When the skill loads, its body instructs the evaluator to begin the full workflow, so the eval never produces a clean loaded/not-loaded answer.
2. **The eval derails.** When the skill does not load, the evaluator falls back to analyzing the codebase or interviewing the user, hangs, or hits its step limit without reporting an outcome.

The root cause is that the evaluator sees real skill bodies in a real working directory. The fix is to run each eval in an isolated temporary workspace where skills exist only as frontmatter stubs — descriptions are present to trigger on, but there is no body to execute and no codebase to analyze — and to detect the outcome mechanically from the eval run's structured output.

## 2. Goals & Non-Goals

- **Goals:**
  - A single command that runs one scenario phrase against the skill library and reports whether the target skill loaded.
  - Eval runs happen in an isolated temporary workspace containing only stubbed skills (frontmatter only) and the evaluator agent, never skill bodies or a real codebase.
  - The temporary workspace is set up once when a campaign starts and reused for every eval in that campaign; a new workspace is never created per eval.
  - Outcome detection is mechanical: parse the run's structured output for a skill-load signal; a step limit or timeout without that signal counts as a failed trigger.
  - Conflicting triggers (wrong skill loaded, or multiple skills loaded) are detected and surfaced so descriptions can be reworked.
  - The new harness replaces the current harness and commands inside the existing `trigger-testing` skill.
  - An optional model selection, omitted entirely when not specified.
- **Non-goals:**
  - Changing the trigger-testing methodology: eval-set design, train/validation splits, optimization loop, done criteria.
  - Batch or multi-scenario execution (the invoking skill loops over the eval set itself).
  - Distinguishing timeout/step-limit failures from clean no-loads in the reported outcome.
  - Automatically rewriting conflicting skill descriptions; the harness only surfaces conflicts.
  - Changes to the evaluator agent's role beyond what isolation requires.
  - Pressure-testing harness changes.

## 3. User Stories & Acceptance Scenarios

### P1: Isolated single-scenario eval
- **Independent test:** run the harness once against one scenario phrase and receive a loaded/not-loaded verdict without any skill workflow executing.
- **Scenario:** Given a target skill and a scenario phrase, When the user runs the harness command with that phrase, Then the eval executes in a temporary workspace where the target skill exists only as a frontmatter stub, and the harness reports whether the skill loaded — with no workflow steps executed and no codebase analysis or user interview attempted.

### P2: Mechanical outcome detection
- **Independent test:** run scenarios known to trigger and known not to trigger the target skill; each verdict matches expectation without human inspection of the transcript.
- **Scenario:** Given a scenario phrase that should trigger the target skill, When the harness runs it and the evaluator loads the skill, Then the harness reports "loaded"; and Given a phrase that should not trigger it, When the evaluator finishes or exhausts its steps without loading the skill, Then the harness reports "not loaded".

### P3: Conflict surfacing
- **Independent test:** run a scenario that triggers the wrong skill or multiple skills; the conflict appears in the harness output.
- **Scenario:** Given a scenario phrase intended for skill A but whose wording also matches skill B, When the harness runs the eval and skill B (or both A and B) loads, Then the harness reports which skill(s) actually loaded so the user knows the descriptions must be reworked.

### P4: Optional model selection
- **Independent test:** run the harness with and without the model option; both invocations succeed, and the model argument is absent from the underlying eval invocation when not specified.
- **Scenario:** Given the harness command, When the user passes a model option, Then the eval runs against that model; and When the user omits it, Then the eval runs with the default model and no model argument is passed.

### P5: Replacement of the existing harness
- **Independent test:** follow the updated `trigger-testing` skill end-to-end; every eval it runs goes through the new harness and no old harness command remains.
- **Scenario:** Given the updated `trigger-testing` skill, When a user runs a trigger-eval campaign, Then all eval executions use the new isolated harness and the skill contains no references to the previous harness process.

## 4. Requirements

- **FR-001:** The harness must be invocable as a single command accepting one scenario text plus an optional model selector.
- **FR-002:** A temporary workspace directory must be created once when a trigger-test campaign starts, isolated from the real repository, and reused for every eval in that campaign; a campaign must never create a new workspace per eval.
- **FR-003:** The temporary workspace must contain the evaluator agent and stubbed versions of the skills under test, where each stub consists of the skill's frontmatter only — no body content that could start a workflow.
- **FR-004:** The stub set must be derived from a configurable source directory containing the real skills and agents.
- **FR-005:** The harness must accept the scenario text either directly as an argument or via a file; file-based input must reside inside the temporary workspace so the eval runtime accepts it, and argument-based input must be passed without quoting or escaping hazards.
- **FR-006:** When a model is specified, the eval must run against that model; when omitted, no model argument may be passed.
- **FR-007:** The harness must determine the outcome by parsing the eval run's structured output for a skill-load signal naming the target skill.
- **FR-008:** If the eval run ends, times out, or reaches its step limit without a skill-load signal for the target skill, the harness must report the trigger as failed.
- **FR-009:** The harness must detect and surface which skill(s) actually loaded, including cases where the wrong skill or multiple skills loaded.
- **FR-010:** The temporary workspace must be cleaned up automatically when the campaign ends.
- **FR-011:** The `trigger-testing` skill must be updated to use this harness for all eval executions, replacing the current harness and its commands.
- **FR-012:** The harness must report a binary loaded/not-loaded verdict for the target skill; timeouts and step-limit exhaustion are not distinguished from clean no-loads in the verdict.

## 5. Scope

- **In scope:**
  - A new single-scenario trigger-test command implementing isolated, stub-based eval execution.
  - Stub generation (frontmatter-only copies) from a source skills/agents directory.
  - Mechanical outcome detection from structured eval output, including conflict surfacing.
  - Optional model selection.
  - Automatic temporary-workspace lifecycle: one workspace created at campaign start, reused across all evals in the campaign, cleaned up at campaign end.
  - Updating the `trigger-testing` skill to replace the current harness and commands with the new one.
- **Out of scope:**
  - Eval-set design, train/validation splits, optimization-loop logic, and other trigger-testing methodology.
  - Batch/multi-scenario execution in a single command invocation.
  - Three-way outcome classification (loaded / not-loaded / indeterminate).
  - Automated description rewrites in response to detected conflicts.
  - Preserving the temporary workspace for post-run debugging.

## 6. Assumptions & Constraints

- The user confirmed the harness runs one scenario per invocation; the invoking skill iterates over the eval set. (Confirmed 2026-07-31.)
- The user confirmed a binary loaded/not-loaded verdict, with timeout/step-limit counting as failed. (Confirmed 2026-07-31.)
- The user confirmed conflicts are detected and surfaced, not treated as automatic eval failures. (Confirmed 2026-07-31.)
- The user confirmed the temporary workspace is cleaned up automatically after each run. (Confirmed 2026-07-31.)
- Constraint: the harness must fit into the existing `trigger-testing` skill as a replacement for its current harness, not a new standalone skill.

## 7. Edge Cases

- **Scenario text with quotes, backticks, or shell metacharacters:** must be passed to the eval runtime intact, without escaping or quoting corruption.
- **Scenario supplied as a file:** the file must be placed inside the temporary workspace so the eval runtime does not reject it as external.
- **No model specified:** the model argument must be omitted entirely, not passed empty.
- **Evaluator loads the target skill plus additional skills:** reported as loaded, with the extra loads surfaced as a conflict.
- **Evaluator loads a different skill than the target:** reported as not loaded, with the actually-loaded skill surfaced as a conflict.
- **Evaluator never invokes any skill (derailment, hang, step limit):** reported as not loaded.
- **Source directory missing or malformed skills:** the harness must fail loudly rather than run against a partial stub set.
- **Many evals in one campaign:** all evals share the single campaign workspace; reusing it must not change any eval's outcome relative to running it alone.

## 8. Success Criteria

- **SC-001:** Running one command with a scenario phrase produces a loaded/not-loaded verdict for the target skill with no manual transcript inspection.
- **SC-002:** No eval run executes any step of a skill's workflow, because eval runs never have access to skill bodies.
- **SC-003:** No eval run derails into codebase analysis or user interviews, because eval runs happen in an isolated workspace without a real codebase.
- **SC-004:** A scenario known to trigger the target skill is reported loaded; a scenario known not to trigger it is reported not loaded.
- **SC-005:** Runs that load the wrong skill or multiple skills visibly report which skills loaded.
- **SC-006:** The `trigger-testing` skill's full campaign flow executes entirely through the new harness, with no remaining references to the old harness.
- **SC-007:** A campaign creates exactly one temporary workspace regardless of how many evals it runs, and after the campaign ends no temporary workspace artifacts remain.

## 9. Open Questions

None.
