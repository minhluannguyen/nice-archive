{ isTest, isVulnerable, isScenario ? true, hostName, isRetrictNetwork ? true, configPath, caseDir, extraArgs ? {} }:
{ config, pkgs, lib, modulesPath, ... }:

let
  templateMinimal = (import ./vm-minimal.nix { inherit isTest hostName isRetrictNetwork; }) { inherit pkgs config lib modulesPath; };
  # Handle both absolute paths and relative paths
  defaultConfigPath = if builtins.isPath configPath then
    configPath
  else if builtins.isString configPath then
    caseDir + "/" + configPath
  else
    caseDir + "/" + configPath;
  customConfig = if builtins.pathExists defaultConfigPath then
    import defaultConfigPath ({ inherit isTest isVulnerable isScenario pkgs config lib modulesPath; } // extraArgs)
  else throw "NixOS configuration file ${toString defaultConfigPath} not found.";
in
{
  imports =
    lib.optionals (!isTest) [
      "${modulesPath}/virtualisation/qemu-vm.nix"
    ]
    ++ 
    [
      templateMinimal
      customConfig
    ];
}
