## New Skill Placement

Unless explicitly stated by the user, newly created skills should be created under skills/ and NOT as per-project skills that would reside under `.opencode/skills` or `.pi/skills`, for example.

## Operational Rules

- You DO NOT modify README.md. Only humans edit that file, unless the user asks you to make a specific edit.
- You may update AGENTS.md but always get confirmation from the user first. AGENTS.md should contain important information about the project and commands, issues that happen frequently and require trial and error to fix. But the file should be, otherwise, as short and minimal as possible.
- Skills live under the `skills` directory below the project root. When told to load, use, or test a skill, use the Glob tool to look under `./skills` instead of inventing plausible-sounding paths or searching the system.

## Auditing Python / shell

Configs live in pyproject.toml (`[tool.black]`, `[tool.ruff]`, line-length 79) and `.flake8`; bare invocations from the repo root just work:

- `uv run flake8 <files>` — catches pycodestyle indentation rules (E1xx) ruff lacks
- `uv run ruff check <files>` — lint (E/W/F/I/DTZ/PLW/EXE); overlaps flake8 but not a superset, so run both
- `uv run black <files>` (format) / `uv run black --check <files>` (audit)
- `uv run pyright <paths>` — type check
- `shellcheck <files>` — shell scripts

## Mermaid diagrams

To validate or render mermaid diagrams (e.g. in SKILL.md files), use the installed `mermaidx` Python library;

## Project Layout

```
dangerpowers/
├── skills/                    # library of custom opencode skills (one dir per skill)
│   └── */                     # each skill contains:
│       ├── SKILL.md           # skill definition/instructions
│       ├── scripts/           # helper scripts (some skills)
│       ├── references/        # reference docs (some skills)
│       └── agents/            # supporting agent configs/schemas (some skills)
├── skills-workspace/          # per-skill test artifacts (e.g. trigger-tests/queries.json);
                               # trigger-test campaign dirs (campaign-YYYY-MM-DD[-N]/) are persistent and committed
├── tools/test-harness/      # shared headless eval-harness scripts for the
│                            # trigger/retrieval/shape/pressure testing skills (evaluator.py,
│                            # strategies.py, workspace-manager.sh, test_evaluator.py)
├── docs/                      # documentation and deep-dives (index: docs/README.md)
├── agents/                    # custom opencode agent definitions (*.md)
├── plugins/                   # opencode plugin (opencode-plugin.ts) registering skills/ + agents/ via config hook
├── .opencode/                 # opencode config
├── .worktrees/                # git worktrees used by plan execution
├── AGENTS.md                  # repo operational rules for agents
├── README.md                  # docs
├── package.json / node_modules # Node deps for plugins/ (yaml, @opencode-ai/plugin)
├── tsconfig.json              # TypeScript config (npm run typecheck)
├── flake.nix / flake.lock / .envrc  # Nix dev environment
└── pyproject.toml / uv.lock / .venv # Python environment (skill development tooling)
```
