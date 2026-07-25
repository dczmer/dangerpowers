This is a repository containing a library of custom skills under the skills/ directory.

Newly created skills should be created under skills/ and NOT as per-project skills that would reside under `.opencode/skills` or `.pi/skills`, for example.

## The Planning Pipeline

Skills form a pipeline; each produces one artifact that feeds the next:

1. **prompt-shaping** — confirms scope of a vague request before work starts (optional artifact: `RESEARCH/<date>-<name>-spec.md`)
2. **writing-prds** — `PRDS/<date>-<name>.md`: WHAT and WHY (features only)
3. **researching-codebase** — `RESEARCH/<date>-<name>-research-findings.md`: the codebase as it exists
4. **scouting-context** — `RESEARCH/<date>-<name>-context-bundle.md`: compressed handoff — blast radius, conflicts, constraints
5. **writing-plans** — `PLANS/<date>-<name>-plan.md`: resolved decisions, phased execution
6. **iterating-plans** — applies human review edits to an existing plan before execution; verifies the plan's facts against the current codebase via sub-agents, and routes back upstream when edits invalidate earlier artifacts
7. **executing-plans** — executes one phase of an approved plan per invocation and reports back status + issues to `PLANS/<date>-<name>-phase-N-report.md`; safe to run as parallel subagents (phases own disjoint file sets; the plan file is read-only in subagent mode)

**prd-to-plan** orchestrates steps 3–5 plus the iterating-plans feedback loop from a single invocation: given a PRD, it drives research, context scouting, and plan writing in order, delegates phases to subagents where safe, and manages user feedback on the plan until the user accepts it as ready for human review.

All artifacts are uniquely named (`YYYY-MM-DD-<kebab>`) and committed to source control — `RESEARCH/` is NOT gitignored. Artifacts record provenance in frontmatter (`source_prd`, `source_bundle`, `source_research`) so any step can trace back. Steps 2–4 are skippable when the input they produce already exists or the task is too small to need them.

## Pressure Test Pollution

When running pressure test campaigns (see `skills/writing-skills/references/pressure-testing.md`), watch for two contamination sources in baseline runs:

- **Global or per-project rules** (e.g. a global `AGENTS.md`) bleeding into subagent baselines: this pollutes measurements and must be avoided. If detected, flag it and escalate to the user before trusting baseline results.
- **Skill descriptions of other skills in this repository** visible to subagents: this is fine. These skills ship together, so cross-skill leakage is expected — and baseline reps reaching the right decision because of it is a good outcome, not a measurement error.
