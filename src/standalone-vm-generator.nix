{ 
  nixpkgs,
  caseDir, 
  system ? "x86_64-linux",
  VMs ? []
}:
let
  pkgs = import nixpkgs { inherit system; };
  lib = pkgs.lib;
  
  mkStandaloneVm = import ./vm-configs/make-standalone-vm.nix;

  mkVMs = name: value:
  let
    configPath = if value ? configPath then value.configPath else throw "Each VM must have a configPath defined";
    isVulnerable = if value ? isVulnerable then value.isVulnerable else null;
    isRetrictNetwork = if value ? isRetrictNetwork then value.isRetrictNetwork else true;
    isGraphics = if value ? isGraphics then value.isGraphics else false;
    isOldKernelVM = if value ? isOldKernelVM then value.isOldKernelVM else false;
    vmNixpkgs = if value ? nixpkgs then value.nixpkgs else nixpkgs;
    vmExtraArgs = if value ? extraArgs then value.extraArgs else {};

    nodeValueTemplate = isVulnerable: vmNixpkgs: (mkStandaloneVm {
      configPath = ./vm-configs/vm-template-instance.nix;
      nixpkgs = vmNixpkgs;
      extraArgs = { 
        isTest = false;
        hostName = if value ? hostname then value.hostname else name;
        inherit caseDir isVulnerable configPath isRetrictNetwork isGraphics isOldKernelVM;
        extraArgs = vmExtraArgs;
      };
      inherit system;
    });
  in
    [{
      name = name;
      value = (nodeValueTemplate isVulnerable vmNixpkgs).vm;
    }];
in
{
  standaloneVMs = (lib.listToAttrs (builtins.concatLists (lib.mapAttrsToList (mkVMs) VMs)));
}
