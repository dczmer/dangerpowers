---
name: project-bootstrap-nix
description: Use when bootstrapping a new project in a fresh git repository — creates a flake.nix devShell, verifies it builds, sets up direnv and .gitignore, adds README/AGENTS stubs, and makes the initial commit. Trigger phrases include "bootstrap a new project", "create a new project called NAME".
---

# Project Bootstrap (Nix)

Bootstrap a new project with a Nix flake devShell, direnv, and an initial commit.

## Preconditions

- The current directory is a git repository the user created with `git init`.
- If any of `flake.nix`, `.envrc`, or `.gitignore` already exist, STOP and tell the user — these files must not be overwritten.
- Other files or directories may exist in the repo. Ignore them entirely: do not read, modify, stage, or commit them. Leave them untracked and untouched.
- If the user did not supply a project name (e.g. "create a new project called my-app"), ask for PROJECT_NAME before proceeding.

## Steps

1. Run the bootstrap script from this skill's directory, substituting PROJECT_NAME:
   ```bash
   skills/project-bootstrap-nix/scripts/bootstrap.sh "PROJECT_NAME"
   ```
   It verifies the preconditions, writes `flake.nix`/`flake.lock`/`.envrc`/`.gitignore`/`AGENTS.md`, stages `flake.nix` and `flake.lock`, and verifies the devShell builds. If it exits non-zero, read its error output, fix the problem, and re-run it (it is safe to re-run only if the failing step did not create a bootstrap file — otherwise fix manually and continue).
2. Prompt the user for a brief description of the project. Write it to `README.md` under a top-level heading (substitute PROJECT_NAME with the actual project name):
   ```md
   # PROJECT_NAME

   <description>
   ```
3. Interview the user for optional extras using the `question` tool. Ask each question below and act on the answers:
    - **Create a default opencode config?** Ask using the `question` tool (Yes/No). If yes, create `.opencode/opencode.jsonc` with these contents:
      ```jsonc
      {
        "$schema": "https://opencode.ai/config.json",
        "permission": {
          "*": "ask"
        }
      }
      ```
    - **Add additional nix packages to the devShell?** Ask using the `question` tool (Yes/No). If yes, ask which packages. For each requested package, first try an exact match: `nix eval nixpkgs#PACKAGE_NAME.meta.description --raw 2>&1` — if it succeeds, the attribute name is valid. If it fails, fall back to `nix search nixpkgs PACKAGE_NAME --json` to find the correct attribute name. Add validated packages to `packages` in `flake.nix`. If a requested name is ambiguous or returns no results, skip that package and report the failures to the user.
    - **Any initial instructions for AGENTS.md?** Ask using the `question` tool (Yes/No). If no, continue. If yes, ask for the instructions, translate the user's response into agent instructions, and write them to `AGENTS.md`.
4. Rebuild the devShell to validate any added packages: `nix build .#devShells.$(nix eval --impure --expr 'builtins.currentSystem' --raw).default`.
5. Stage only the files created by this skill: `git add flake.nix flake.lock .envrc .gitignore README.md AGENTS.md` (plus `.opencode/opencode.jsonc` if it was created). Do NOT use `git add -A` or `git add .`. Then make the initial commit: `git commit -m "Initial commit: bootstrap nix devshell"`.
6. Report to the user: what was created, build status, any unexpected or untracked files or folders, and that the dev environment is ready for customization.
