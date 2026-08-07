#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 PROJECT_NAME" >&2
  exit 1
fi
PROJECT_NAME="$1"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not inside a git repository" >&2
  exit 1
fi

for f in flake.nix .envrc .gitignore; do
  if [ -e "$f" ]; then
    echo "error: $f already exists; refusing to overwrite" >&2
    exit 1
  fi
done

SYSTEM="$(nix eval --impure --expr 'builtins.currentSystem' --raw)"

cat > flake.nix <<'EOF'
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
EOF
sed -i "s/PROJECT_NAME/$PROJECT_NAME/" flake.nix

git add flake.nix

if ! nix build ".#devShells.$SYSTEM.default"; then
  echo "error: nix build failed for .#devShells.$SYSTEM.default" >&2
  exit 1
fi

git add flake.lock

printf 'use flake\n' > .envrc
direnv allow

printf '.direnv/\nresult\n' > .gitignore

touch AGENTS.md

echo "bootstrap complete: flake.nix, flake.lock, .envrc, .gitignore, AGENTS.md"
