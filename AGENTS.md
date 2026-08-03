This is a repository containing a library of custom skills under the skills/ directory.

Newly created skills should be created under skills/ and NOT as per-project skills that would reside under `.opencode/skills` or `.pi/skills`, for example.

## Operational Rules

- You DO NOT modify README.md. Only humans edit that file, unless the user asks you to make a specific edit.
- You may update AGENTS.md but always get confirmation from the user first. AGENTS.md should contain important information about the project and commands, issues that happen frequently and require trial and error to fix. But the file should be, otherwise, as short and minimal as possible.
- `.opencode/skills` and `.opencode/agents` are symlinks to the `skills` and `agents` directories in this repository. Never try to commit the symlinks, always commit the real files.
- Skills live under the `skills` directory below the project root. When told to load, use, or test a skill, use the Glob too to look under `./skills` instead of inventing plausible-sounding paths or searching the system.

## Project Layout

```
dangerpowers/
├── skills/                    # library of custom opencode skills (one dir per skill)
│   └── */                     # each skill contains:
│       ├── SKILL.md           # skill definition/instructions
│       ├── scripts/           # helper scripts (some skills)
│       ├── references/        # reference docs (some skills)
│       ├── test-campaigns/    # pressure-test campaign data (some skills)
│       └── trigger-evals/     # trigger-eval scenarios (some skills)
├── agents/                    # custom opencode agent definitions (*.md)
├── PRDS/                      # product requirements documents
├── RESEARCH/                  # research findings + context bundles feeding plans
├── PLANS/                     # implementation plans + phase execution reports
├── .opencode/                 # opencode config; skills/ and agents/ inside are symlinks to the top-level dirs
├── .worktrees/                # git worktrees used by plan execution
├── AGENTS.md                  # repo operational rules for agents
├── README.md / NOTES.md / EXAMPLE_AGENT_RULES.md  # docs
├── flake.nix / flake.lock / .envrc  # Nix dev environment
└── pyproject.toml / uv.lock / .venv # Python environment (skill tooling)
```
