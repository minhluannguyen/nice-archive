{ nixpkgs, 
  nixpkgsVM ? nixpkgs,
  caseDir, 
  system ? "x86_64-linux",
  customVMs ? []
}:
let
  pkgs = import nixpkgs { inherit system; };
  lib = pkgs.lib;

  # Test configuration
  # mkTest = import ./test-template.nix;
  
  mkStandaloneVm = import ./vm-configs/make-standalone-vm.nix;

  mkVMs = node:
    let
      configPath = node.configPath;
      supportsVulnerable = 
        let
          # Read the file as raw text to check parameter names
          fileContent = builtins.readFile configPath;
          # Simple check: does the file contain "isVulnerable" in parameter list
          hasParam = builtins.match ".*isVulnerable.*" fileContent != null;
        in
          hasParam;
      mkVMName = name: isVulnerable:
        if supportsVulnerable then
          if isVulnerable then
            "vm_${name}_vulnerable_true_${system}"
          else
            "vm_${name}_vulnerable_false_${system}"
        else
          "vm_${name}_${system}";

      nodeValueTemplate = (mkStandaloneVm {
          configPath = ./vm-configs/vm-template-instance.nix;
          extraArgs = { 
            isTest = false;
            hostName = node.name;
            configPath = node.configPath;
            isRetrictNetwork = if node ? isRetrictNetwork then node.isRetrictNetwork else true;
            inherit caseDir; 
          };
          nixpkgs = nixpkgsVM;
          inherit system;
        });
    in
      if supportsVulnerable then
        [
          {
            name = mkVMName node.name true;
            value = nodeValueTemplate.vmVulnerableTrue;
          }
          {
            name = mkVMName node.name false;
            value = nodeValueTemplate.vmVulnerableFalse;
          }
        ]
      else
        [
          {
            name = "vm_${node.name}";
            value = nodeValueTemplate;
          }
        ];
in
((builtins.listToAttrs (builtins.concatLists (map mkVMs customVMs))))
