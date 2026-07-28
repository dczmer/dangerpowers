This is a repository containing a library of custom skills under the skills/ directory.

Newly created skills should be created under skills/ and NOT as per-project skills that would reside under `.opencode/skills` or `.pi/skills`, for example.

## Operational Rules

- You DO NOT modify README.md. Only humans edit that file, unless the user asks you to make a specific edit.
- You may update AGENTS.md but always get confirmation from the user first. AGENTS.md should contain important information about the project and commands, issues that happen frequently and require trial and error to fix. But the file should be, otherwise, as short and minimal as possible.

## The Planning Pipeline

Skills form a pipeline; each produces one artifact that feeds the next:

1. **prompt-shaping** — confirms scope of a vague request before work starts (optional artifact: `RESEARCH/<date>-<name>-spec.md`)
2. **writing-prds** — `PRDS/<date>-<name>.md`: WHAT and WHY (features only)
3. **researching-codebase** — `RESEARCH/<date>-<name>-research-findings.md`: the codebase as it exists
4. **scouting-context** — `RESEARCH/<date>-<name>-context-bundle.md`: compressed handoff — blast radius, conflicts, constraints
5. **writing-plans** — `PLANS/<date>-<name>-plan.md`: resolved decisions, phased execution; declares per-phase independence (`**Parallel group:**`) and plan-level final verification commands
6. **iterating-plans** — applies human review edits to an existing plan before execution; verifies the plan's facts against the current codebase via sub-agents, and routes back upstream when edits invalidate earlier artifacts
7. **executing-plans** — executes one phase of an approved plan per invocation and reports back status + issues to `PLANS/<date>-<name>-phase-N-report.md`; safe to run as parallel subagents (phases own disjoint file sets; the plan file is read-only in subagent mode)

**prd-to-plan** orchestrates steps 3–5 plus the iterating-plans feedback loop from a single invocation: given a PRD, it drives research, context scouting, and plan writing in order, delegates phases to subagents where safe, and manages user feedback on the plan until the user accepts it as ready for human review.

**plan-to-execution** orchestrates step 7 from a single invocation: given an approved plan, it dispatches one executing-plans subagent per phase, runs plan-declared independent phases in parallel inside isolated git worktrees, checkpoints each phase as a commit, resumes interrupted runs from committed phases, and runs the plan's final test and audit commands — then stops, leaving review, cleanup, and PR creation to the user. Phases declaring `**Execution:** inline` (pressure-test campaigns, test-only execution phases, anything invoking a skill or prompt that dispatches subagents) are never dispatched to subagent executors: the orchestrator runs them inline in the main session, sequentially, only after all preceding phases are merged.

All artifacts are uniquely named (`YYYY-MM-DD-<kebab>`) and committed to source control — `RESEARCH/` is NOT gitignored. Artifacts record provenance in frontmatter (`source_prd`, `source_bundle`, `source_research`) so any step can trace back. Steps 2–4 are skippable when the input they produce already exists or the task is too small to need them.

## Pressure Test Pollution

When running pressure test campaigns (see `skills/writing-skills/references/pressure-testing.md`), watch for two contamination sources in baseline runs:

- **Global or per-project rules** (e.g. a global `AGENTS.md`) bleeding into subagent baselines: this pollutes measurements and must be avoided. If detected, flag it and escalate to the user before trusting baseline results.
- **Skill descriptions of other skills in this repository** visible to subagents: this is fine. These skills ship together, so cross-skill leakage is expected — and baseline reps reaching the right decision because of it is a good outcome, not a measurement error.
