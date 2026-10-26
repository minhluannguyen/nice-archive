{
  description = "Run a Python script with nix run";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
    nixpkgs-opencode.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    nix-versions.url = "github:denful/nix-versions";
  };

  outputs = { self, nixpkgs, nixpkgs-opencode, nix-versions }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems = nixpkgs.lib.genAttrs systems;
      forEachSystem = f: forAllSystems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
          opencodePkgs = import nixpkgs-opencode {
            inherit system;
          };

          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            jinja2
            pyyaml
            pexpect
            ruamel-yaml
            questionary
            inquirerpy
          ]);

          runtimePackages = with pkgs; [
            git
            nix
            openssh
            terminator
            xterm
          ];

          runtimePath = pkgs.lib.makeBinPath runtimePackages;

          nixVersions = nix-versions.packages.${system}.default;

          nice-archive = pkgs.writeShellScriptBin "nice-archive" ''
            export PATH=${runtimePath}:$PATH

            exec ${pythonEnv}/bin/python ${self}/nice-archive.py "$@"
          '';

        in
        f {
          inherit pkgs opencodePkgs pythonEnv runtimePackages nixVersions nice-archive;
        });
    in
    {
      packages = forEachSystem ({ nice-archive, ... }: {
        inherit nice-archive;
        default = nice-archive;
      });

      apps = forAllSystems (system: {
        nice-archive = {
          type = "app";
          program = "${self.packages.${system}.nice-archive}/bin/nice-archive";
        };
        default = self.apps.${system}.nice-archive;
      });

      devShells = forEachSystem ({ pkgs, opencodePkgs, pythonEnv, runtimePackages, nixVersions, ... }: {
        default = pkgs.mkShell {
          packages = [
            pythonEnv
            nixVersions
          ] ++ runtimePackages ++ [
            pkgs.git
            opencodePkgs.opencode
          ];

          shellHook = ''
            export NICE_ARCHIVE_ROOT="$PWD"
            export PATH="$PWD:$PATH"
          '';
        };

        docs = pkgs.mkShell {
          packages = [ pkgs.hugo pkgs.git ];
        };
      });
    };
}
