# OVERVIEW

create a simple skill for bootstrapping a new project called 'project-bootstrap-nix' in a 'skills' directory under the project root.

if the user invokes the skill without arguments, prompt for the PROJECT_NAME

alternatively, they can prompt to use the skill like so:
> create a new project called PROJECT_NAME

our goal is to bootstrap a new project: setup flake.nix with a devshell, build and verify the flake, setup direnv, add required files, configure .gitignore, and then make the initial commit so the new dev environment is bootstrapped for further customization.

# PROCESS

- assume we're inside of a new git repository folder that the user manually created with `git init`.
- make a flake with a default devShell based on the template provided in the "FLAKE TEMPLATE" section of this document
- what packages to include? see the section "DEFAULT PACKAGES" below.
- add the flake to the git repo; git flakes require files be added to git index before the build process can see them
- do a nix build to test the shell definition (e.g. `nix build .#devShells.x86_64-linux.default`) and check the return code is 0
- git add flake.lock once it is generated
- direnv? create .envrc and allow dir
- add .direnv and result to .gitignore
- create README.md, AGENTS.md (blank)
- `nix build` the devShell and look for unexpected changes
- make initial commit


## FLAKE TEMPLATE

variables:
- PROJECT_NAME: the name of the project to use
- PACKAGES_GO_HERE: put the list of packages here

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
                PACKAGES_GO_HERE                
            ];
            shellHook = ''
            
            '';
          };
        };
      }
    );
}


```

## DEFAULT PACKAGES

- curl
- wget
- jq
- git
- ripgrep
- gnugrep
- gawkInteractive
- findutils
- gzip
- diffutils
- coreutils
- tree
- file
- wget
- gnused
