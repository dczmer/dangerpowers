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

1. Verify preconditions: `git rev-parse --is-inside-work-tree` and check that none of the bootstrap files (`flake.nix`, `.envrc`, `.gitignore`) already exist. Ignore everything else in the directory.
2. Detect the system architecture: `nix eval --impure --expr 'builtins.currentSystem' --raw` (e.g. `x86_64-linux`, `aarch64-darwin`). Use this value wherever SYSTEM appears below.
3. Write `flake.nix` from the FLAKE TEMPLATE below, substituting PROJECT_NAME.
4. `git add flake.nix` — flakes require files to be in the git index before nix can see them.
5. Verify the shell builds: `nix build .#devShells.SYSTEM.default` and check the exit code is 0. If it fails, diagnose, fix, and retry.
   - If the failure is an invalid/unknown package name in `packages`, run `nix search nixpkgs PACKAGE_NAME` to find the correct attribute name and update the flake.
6. `git add flake.lock` once generated.
7. Create `.envrc` containing `use flake` and run `direnv allow && echo OK` and verify it prints "OK".
8. Create `.gitignore` containing:
   ```
   .direnv/
   result
   ```
9. Create a blank `AGENTS.md`.
10. Prompt the user for a brief description of the project. Write it to `README.md` under a top-level heading (substitute PROJECT_NAME with the actual project name):
    ```md
    # PROJECT_NAME

    <description>
    ```
11. Interview the user for optional extras using the `question` tool. Ask each question below and act on the answers:
    - **Create a default opencode config?** Ask using the `question` tool (Yes/No). If yes, create `.opencode/opencode.jsonc` with these contents:
      ```jsonc
      {
        "$schema": "https://opencode.ai/config.json",
        "permission": {
          "*": "ask"
        }
      }
      ```
    - **Add additional nix packages to the devShell?** Ask using the `question` tool (Yes/No). If yes, ask which packages, then run `nix search nixpkgs PACKAGE_NAME --json` for each requested package to find the correct attribute name, and add it to `packages` in `flake.nix`. If a requested name is ambiguous or returns no results, skip that package and report the failures to the user.
    - **Any initial instructions for AGENTS.md?** Ask using the `question` tool (Yes/No). If no, continue. If yes, ask for the instructions, translate the user's response into agent instructions, and write them to `AGENTS.md`.
12. Run `nix build .#devShells.SYSTEM.default` again and check `git status` — the only new entry from this skill should be the `result` symlink (gitignored). Pre-existing untracked files are expected; leave them alone.
13. Stage only the files created by this skill: `git add flake.nix flake.lock .envrc .gitignore README.md AGENTS.md` (plus `.opencode/opencode.jsonc` if it was created). Do NOT use `git add -A` or `git add .`. Then make the initial commit: `git commit -m "Initial commit: bootstrap nix devshell"`.
14. Report to the user: what was created, build status, and that the dev environment is ready for customization.

## FLAKE TEMPLATE

Substitute PROJECT_NAME. The default packages are already included.

```nix
{
  description = "PROJECT_NAME";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells = {
          default = pkgs.mkShell {
            packages = with pkgs; [
              curl
              wget
              jq
              git
              ripgrep
              gnugrep
              gawkInteractive
              findutils
              gzip
              diffutils
              coreutils
              tree
              file
              gnused
            ];
            shellHook = ''
            '';
          };
        };
      }
    );
}
```
