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
            ];
            shellHook = ''
            '';
          };
        };
      }
    );
}
