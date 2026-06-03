{
  description = "Run a Python script with nix run";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };

          packagedPython = pkgs.python312.withPackages (ps: with ps; [
            jinja2
            pyyaml
            pexpect
            ruamel-yaml
            questionary
            inquirerpy
          ]);

          nice-archive = pkgs.writeShellScriptBin "nice-archive" ''
            export PATH=${pkgs.nix}/bin:${pkgs.terminator}/bin:${pkgs.openssh}/bin:$PATH
            
            exec ${packagedPython}/bin/python ${self}/nice-archive.py "$@"
          '';
        in
        {
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
    };
}