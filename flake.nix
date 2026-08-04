{
  description = "dangerpowers";
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
              uv
              shellcheck
              shunit2
            ];
            shellHook = ''
              [[ -d .venv ]] || uv venv .venv
              source .venv/bin/activate
              which agentskills || $(uv sync && uv python install)

              echo ">> NOTE: Add ~/.local/bin to \$PATH to discover executables."
            '';
          };
        };
      }
    );
}
