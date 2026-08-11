{
  description = "Run a Python script with nix run";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
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
            nix
            openssh
            terminator
          ];

          runtimePath = pkgs.lib.makeBinPath runtimePackages;

          cveOrchestratorRuntimePackages = runtimePackages ++ (with pkgs; [
            git
          ]) ++ [
            opencodePkgs.opencode
          ];

          cveOrchestratorRuntimePath = pkgs.lib.makeBinPath cveOrchestratorRuntimePackages;

          nixVersions = nix-versions.packages.${system}.default;

          nice-archive = pkgs.writeShellScriptBin "nice-archive" ''
            export PATH=${runtimePath}:$PATH

            exec ${pythonEnv}/bin/python ${self}/nice-archive.py "$@"
          '';

          cve-orchestrator = pkgs.writeShellScriptBin "cve-orchestrator" ''
            export PATH=${cveOrchestratorRuntimePath}:$PATH

            if [ -f "$PWD/cve-orchestrator.py" ]; then
              exec ${pkgs.python312}/bin/python "$PWD/cve-orchestrator.py" "$@"
            fi

            exec ${pkgs.python312}/bin/python ${self}/cve-orchestrator.py "$@"
          '';
        in
        f {
          inherit pkgs opencodePkgs pythonEnv runtimePackages nixVersions nice-archive cve-orchestrator;
        });
    in
    {
      packages = forEachSystem ({ nice-archive, cve-orchestrator, ... }: {
        inherit nice-archive cve-orchestrator;
        default = nice-archive;
      });

      apps = forAllSystems (system: {
        nice-archive = {
          type = "app";
          program = "${self.packages.${system}.nice-archive}/bin/nice-archive";
        };
        cve-orchestrator = {
          type = "app";
          program = "${self.packages.${system}.cve-orchestrator}/bin/cve-orchestrator";
        };
        default = self.apps.${system}.nice-archive;
      });

      devShells = forEachSystem ({ pkgs, opencodePkgs, pythonEnv, runtimePackages, nixVersions, cve-orchestrator, ... }: {
        default = pkgs.mkShell {
          packages = [
            pythonEnv
            nixVersions
            cve-orchestrator
          ] ++ runtimePackages ++ [
            pkgs.git
            opencodePkgs.opencode
          ];

          shellHook = ''
            export NICE_ARCHIVE_ROOT="$PWD"
            export PATH="$PWD:$PATH"
          '';
        };
      });
    };
}
