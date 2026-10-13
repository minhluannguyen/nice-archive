# 4. Write the case entry point

Use a `flake.nix` for cases that can be evaluated with modern Nix. Pin inputs
in `flake.lock`, include the local NICE Archive library, and pass the case
directory, test script, and named VMs to the selected generator. For example:

```nix
{
  description = "Reproduction environment for CVE-YYYY-NNNN";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nice-archive-lib.url = "../../src";
  };
  outputs = { nixpkgs, nice-archive-lib, ... }:
    nice-archive-lib.testsGenerator {
      inherit nixpkgs;
      title = "cve-yyyy-nnnn-short-name";
      caseDir = ./.;
      testScriptPath = ./test.py;
      VMs.server = {
        configPath = ./vm-server.nix;
        variant = "package";
      };
    };
}
```

This is a starting shape, not a source of version pins. Select and verify
versions through [step 2](./02-research-and-sources.md). The
[library reference](../nice-archive-libs.md#testsgenerator) gives the exact
function signature and output names.

For old cases that cannot use flake-era Nix, use a pinned `default.nix`
workflow and document why. Flake evaluation reads Git-visible files; the CLI
stages a selected case before flake-based tests and scenarios. Review the Git
index after those commands. See the [CLI guide](../cli-tool.md) for command
behavior.

**Previous:** [Step 3: Design the topology and choose a generator](./03-design.md) · **Next:** [Step 5: Writing VMs configuration](./05-vm-configurations.md)
