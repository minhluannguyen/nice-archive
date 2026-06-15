{ nixpkgs,
  title,
  caseDir, 
  system ? "x86_64-linux",
  VMs ? {},
  testScriptPath,
  generateInteractiveTests ? true
}:
let
  pkgs = import nixpkgs { inherit system; };
  lib = pkgs.lib;

  normalizeNixpkgsSource = src:
    if builtins.isAttrs src && src ? outPath then src.outPath
    else if builtins.isAttrs src && src ? path then src.path
    else src;

  sourceKey = src: builtins.toString (normalizeNixpkgsSource src);
  importPkgs = src: import (normalizeNixpkgsSource src) { inherit system; };

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

  getSystemPinning = name: value:
    let
      pinning =
        if value ? nixpkgs && builtins.isAttrs value.nixpkgs then value.nixpkgs
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
          throw "Error: Without the external VM test backend, all 'system' variant VMs must share the same vulnerable and fixed nixpkgs sources.";

  scenarioNixpkgs = isVulnerable:
    normalizeNixpkgsSource (
      if sharedSystemPinning == null then
        nixpkgs
      else if isVulnerable then
        sharedSystemPinning.vulnerable
      else
        sharedSystemPinning.fixed
    );

  scenarioPkgs = isVulnerable: importPkgs (scenarioNixpkgs isVulnerable);
  vulnerablePkgs = scenarioPkgs true;
  fixedPkgs = scenarioPkgs false;
  
  mkTest = import ./test-configs/test-template.nix;

in
  (if generateInteractiveTests then 
    { 
      "start-scenario-vulnerable-true-${system}" = ((mkTest { 
        isInteractive = true;
        isVulnerable = true; 
        inherit title caseDir VMs testScriptPath;
      }) { pkgs = vulnerablePkgs; lib = vulnerablePkgs.lib; }).driverInteractive;

      "start-scenario-vulnerable-false-${system}" = ((mkTest { 
        isInteractive = true;
        isVulnerable = false; 
        inherit title caseDir VMs testScriptPath;
      }) { pkgs = fixedPkgs; lib = fixedPkgs.lib; }).driverInteractive;
    }
  else {}) // 
  {
    "test-vulnerable-true-${system}" = ((mkTest { 
      isInteractive = false;
      isVulnerable = true; 
      inherit title caseDir VMs testScriptPath;
    }) { pkgs = vulnerablePkgs; lib = vulnerablePkgs.lib; }).driver;

    "test-vulnerable-false-${system}" = ((mkTest { 
      isInteractive = false;
      isVulnerable = false; 
      inherit title caseDir VMs testScriptPath;
    }) { pkgs = fixedPkgs; lib = fixedPkgs.lib; }).driver;
  }
