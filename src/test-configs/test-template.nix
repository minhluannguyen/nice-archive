{ title, isInteractive, isVulnerable, caseDir, VMs, testScriptPath, enableOCR ? false }:
{ pkgs, lib, ... }:

let 
  testSystem =
    if pkgs ? system then pkgs.system
    else pkgs.stdenv.hostPlatform.system;

  normalizeNixpkgsSource = src:
    if builtins.isAttrs src && src ? outPath then src.outPath
    else if builtins.isAttrs src && src ? path then src.path
    else src;

  sourceKey = src: builtins.toString (normalizeNixpkgsSource src);

  getNodeVariant = name: value:
    let
      explicitVariant = value.variant or null;
      hasNixpkgsPinning = 
        value ? nixpkgs
        && builtins.isAttrs value.nixpkgs
        && ((value.nixpkgs ? vulnerable) || (value.nixpkgs ? fixed));
      inferredVariant =
        if hasNixpkgsPinning then "system"
        else "invariant";
    in
      if explicitVariant == null then
        inferredVariant
      else if builtins.elem explicitVariant [ "invariant" "package" "system" ] then
        explicitVariant
      else
        throw "Error: VM '${name}' has unsupported variant '${explicitVariant}'. Expected one of: invariant, package, system.";

  getConfigPath = name: value:
    if value ? configPath then value.configPath
    else throw "Error: VM '${name}' must define 'configPath'.";

  getSystemPinning = name: value:
    let
      pinning =
        if value ? nixpkgs then value.nixpkgs
        else null;

      vulnerable =
        if pinning == null then null
        else if pinning ? vulnerable then pinning.vulnerable
        else null;

      fixed =
        if pinning == null then null
        else if pinning ? fixed then pinning.fixed
        else null;
    in
      if vulnerable != null && fixed != null then
        {
          inherit vulnerable fixed;
        }
      else
        throw "Error: VM '${name}' uses variant = \"system\" but does not provide nixpkgs pins for both vulnerable and fixed scenarios.";

  hasSystemVariant =
    lib.any
      (name: getNodeVariant name VMs.${name} == "system")
      (lib.attrNames VMs);

  systemVariantPins =
    lib.mapAttrsToList
      (name: value: getSystemPinning name value)
      (lib.filterAttrs (name: value: getNodeVariant name value == "system") VMs);

  sharedSystemPinning =
    if systemVariantPins == [] then
      null
    else
      let
        firstPinning = builtins.head systemVariantPins;
        allPinningMatch = lib.all (pinning:
          sourceKey pinning.vulnerable == sourceKey firstPinning.vulnerable
          && sourceKey pinning.fixed == sourceKey firstPinning.fixed
        ) systemVariantPins;
      in
        if allPinningMatch then
          firstPinning
        else
          throw "Error: All 'system' variant VMs must share the same vulnerable and fixed nixpkgs sources.";

  testNixpkgs =
    if sharedSystemPinning == null then
      null
    else if isVulnerable then
      sharedSystemPinning.vulnerable
    else
      sharedSystemPinning.fixed;

  testPkg =
    if testNixpkgs == null then
      pkgs
    else
      import (normalizeNixpkgsSource testNixpkgs) { system = testSystem; };

  nodes = (lib.mapAttrs (name: value: 
    let
      variant = getNodeVariant name value;
      isRetrictNetwork = if value ? isRetrictNetwork then value.isRetrictNetwork else true;
      isGraphics = if value ? isGraphics then value.isGraphics else false;
      isOldKernelVM = if value ? isOldKernelVM then value.isOldKernelVM else false;
      extraArgs = if value ? extraArgs then value.extraArgs else {};
    in
      (import ../vm-configs/vm-template-instance.nix { 
        isTest = true; 
        hostName = name; 
        isVulnerable = if variant == "invariant" then null else isVulnerable;
        isScenario = isInteractive;
        configPath = getConfigPath name value; 
        inherit caseDir isRetrictNetwork isGraphics isOldKernelVM extraArgs;
      })
  ) VMs);

  defaultInteractiveVMWaitBlock = (lib.concatStringsSep "\n" (lib.mapAttrsToList (name: value: ''
    ${name}.wait_for_unit("multi-user.target")
  '') VMs));
  interactiveTestScript = lib.concatStringsSep "\n" ([
    "start_all()"
    defaultInteractiveVMWaitBlock
    "print(\"INTERACTIVE MODE SETUP COMPLETE. READY FOR INTERACTIVE TESTING.\")" 
  ]);

  testScript = if isInteractive then interactiveTestScript else (builtins.readFile testScriptPath);

  assertionBlocksPkg = ps: import ../assertion_blocks/package.nix {
    pkgs = testPkg;
    pythonPackages = ps;
  };
in
  testPkg.testers.runNixOSTest ({
    name = "${title}-${if isVulnerable then "vulnerable" else "non-vulnerable"}-test";
    nodes = nodes;

    extraPythonPackages = ps: [ (assertionBlocksPkg ps) ];

    testScript = testScript;
  } // testPkg.lib.optionalAttrs enableOCR {
    enableOCR = true;
  } // testPkg.lib.optionalAttrs (isInteractive) {
    interactive.sshBackdoor.enable = true;
  })
