This is a repository containing a library of custom skills under the skills/ directory.

Newly created skills should be created under skills/ and NOT as per-project skills that would reside under `.opencode/skills` or `.pi/skills`, for example.

## Operational Rules

- You DO NOT modify README.md. Only humans edit that file, unless the user asks you to make a specific edit.
- You may update AGENTS.md but always get confirmation from the user first. AGENTS.md should contain important information about the project and commands, issues that happen frequently and require trial and error to fix. But the file should be, otherwise, as short and minimal as possible.
- `.opencode/skills` and `.opencode/agents` are symlinks to the `skills` and `agents` directories in this repository. Never try to commit the symlinks, always commit the real files.

## Pressure Test Pollution

When the user runs test campaigns via the pressure-testing or trigger-testing skills, watch for two contamination sources in baseline runs:

- **Global or per-project rules** (e.g. a global `AGENTS.md`) bleeding into subagent baselines: this pollutes measurements and must be avoided. If detected, flag it and escalate to the user before trusting baseline results.
- **Skill descriptions of other skills in this repository** visible to subagents: this is fine. These skills ship together, so cross-skill leakage is expected — and baseline reps reaching the right decision because of it is a good outcome, not a measurement error.
