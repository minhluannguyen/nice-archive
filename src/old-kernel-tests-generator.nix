{
  nixpkgs,
  oldKernelNixpkgs ? null,
  title,
  caseDir,
  system ? "x86_64-linux",
  VMs ? {},
  testScriptPath,
  isVulnerable ? true,
  oldKernelVMNames ? builtins.attrNames VMs,
  generateInteractiveTests ? true
}:

let
  pkgs = import nixpkgs { inherit system; };
  lib = pkgs.lib;

  testsGenerator = import ./tests-generator.nix;
  oldKernelNixosTest = import ./test-configs/nixos-test-old-kernel.nix;

  scenario = if isVulnerable then "true" else "false";
  testOutputName = "test-vulnerable-${scenario}-${system}";
  interactiveOutputName = "start-scenario-vulnerable-${scenario}-${system}";

  normalizeNixpkgsSource = src:
    if builtins.isAttrs src && src ? outPath then src.outPath
    else if builtins.isAttrs src && src ? path then src.path
    else src;

  getVM = name:
    if builtins.hasAttr name VMs then VMs.${name}
    else throw "Error: old-kernel VM '${name}' is not defined in VMs.";

  getConfigPath = name: value:
    if value ? configPath then value.configPath
    else throw "Error: VM '${name}' must define 'configPath'.";

  getVariant = value:
    if value ? variant then value.variant
    else if value ? nixpkgs then "system"
    else "invariant";

  getOldKernelNixpkgs = name: value:
    let
      source =
        if value ? oldKernelNixpkgs then value.oldKernelNixpkgs
        else oldKernelNixpkgs;
    in
      if source != null then normalizeNixpkgsSource source
      else throw "Error: No old-kernel nixpkgs source was provided for VM '${name}'.";

  baseVMs = lib.mapAttrs
    (_: value:
      builtins.removeAttrs value [ "oldKernelNixpkgs" "oldKernelRestrictNetwork" ]
      // { isOldKernelVM = false; })
    VMs;

  baseOutputs = testsGenerator {
    inherit
      nixpkgs
      title
      caseDir
      system
      testScriptPath
      generateInteractiveTests
      ;
    VMs = baseVMs;
  };

  mkOldKernelVM = isInteractive: name:
    let
      value = getVM name;
      oldNixpkgs = getOldKernelNixpkgs name value;
      variant = getVariant value;
      vmIsVulnerable =
        if variant == "invariant" then null
        else isVulnerable;
    in
      import "${oldNixpkgs}/nixos" {
        configuration = import ./vm-configs/vm-template-instance.nix {
          isTest = true;
          hostName = value.hostname or name;
          isVulnerable = vmIsVulnerable;
          isScenario = isInteractive;
          isGraphics = isInteractive;
          isOldKernelVM = true;
          isRetrictNetwork = value.oldKernelRestrictNetwork or null;
          configPath = getConfigPath name value;
          inherit caseDir;
          extraArgs = value.extraArgs or {};
        };
        inherit system;
      };

  mkOldKernelVMs = isInteractive:
    lib.genAttrs oldKernelVMNames (mkOldKernelVM isInteractive);

  testDriver = oldKernelNixosTest {
    inherit pkgs;
    oldKernelVMs = mkOldKernelVMs false;
    testBase.driver = baseOutputs.${testOutputName};
    isInteractive = false;
  };

  interactiveDriver = oldKernelNixosTest {
    inherit pkgs;
    oldKernelVMs = mkOldKernelVMs true;
    testBase.driverInteractive = baseOutputs.${interactiveOutputName};
    isInteractive = true;
  };
in

baseOutputs
// {
  ${testOutputName} = testDriver;
}
// lib.optionalAttrs generateInteractiveTests {
  ${interactiveOutputName} = interactiveDriver;
}
