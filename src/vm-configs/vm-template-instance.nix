{ isTest, isVulnerable, isScenario ? true, hostName, isGraphics ? false, isOldKernelVM ? false, isRetrictNetwork ? true, configPath, caseDir, extraArgs ? {} }:
{ config, pkgs, lib, modulesPath, ... }:

let
  templateMinimal = import ./vm-minimal.nix {
    inherit isTest hostName isRetrictNetwork isGraphics;
  };
  # Handle both absolute paths and relative paths
  defaultConfigPath = if builtins.isPath configPath then
    configPath
  else if builtins.isString configPath then
    caseDir + "/" + configPath
  else
    caseDir + "/" + configPath;
  customConfig = if builtins.pathExists defaultConfigPath then
    import defaultConfigPath ({ inherit isTest isVulnerable isScenario isGraphics isOldKernelVM pkgs config lib modulesPath; } // extraArgs)
  else throw "NixOS configuration file ${toString defaultConfigPath} not found.";
in
{
  imports =
    lib.optionals isOldKernelVM [
      ./backdoor-service.nix
    ]
    ++
    lib.optionals (!isTest) [
      "${modulesPath}/virtualisation/qemu-vm.nix"
    ]
    ++ 
    [
      templateMinimal
      customConfig
    ];
}
