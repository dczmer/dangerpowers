---
name: project-bootstrap-nix
description: Use when bootstrapping a new project in a fresh git repository — creates a flake.nix devShell, verifies it builds, sets up direnv and .gitignore, adds README/AGENTS stubs, and makes the initial commit. Trigger phrases include "bootstrap a new project", "create a new project called NAME".
---

# Project Bootstrap (Nix)

Bootstrap a new project with a Nix flake devShell, direnv, and an initial commit.

## Preconditions

- The current directory is a git repository the user created with `git init`.
- If any of `flake.nix`, `.envrc`, or `.gitignore` already exist, STOP and tell the user — this skill is for empty repos only.
- If the user did not supply a project name (e.g. "create a new project called my-app"), ask for PROJECT_NAME before proceeding.

## Steps

1. Verify preconditions: `git rev-parse --is-inside-work-tree` and check the repo has no existing bootstrap files.
2. Detect the system architecture: `nix eval --impure --expr 'builtins.currentSystem' --raw` (e.g. `x86_64-linux`, `aarch64-darwin`). Use this value wherever SYSTEM appears below.
3. Write `flake.nix` from the FLAKE TEMPLATE below, substituting PROJECT_NAME.
4. `git add flake.nix` — flakes require files to be in the git index before nix can see them.
5. Verify the shell builds: `nix build .#devShells.SYSTEM.default` and check the exit code is 0. If it fails, diagnose, fix, and retry.
   - If the failure is an invalid/unknown package name in `packages`, run `nix search nixpkgs PACKAGE_NAME` to find the correct attribute name and update the flake.
6. `git add flake.lock` once generated.
7. Create `.envrc` containing `use flake` and run `direnv allow`.
8. Create `.gitignore` containing:
   ```
   .direnv/
   result
   ```
9. Create blank `README.md` and `AGENTS.md`.
10. Run `nix build .#devShells.SYSTEM.default` again and check `git status` for unexpected changes (only the `result` symlink should appear, and it is gitignored).
11. `git add -A` and make the initial commit: `git commit -m "Initial commit: bootstrap nix devshell"`.
12. Report to the user: what was created, build status, and that the dev environment is ready for customization.

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
