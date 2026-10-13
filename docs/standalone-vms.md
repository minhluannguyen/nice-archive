# Standalone VMs for manual reproduction

Standalone VMs are an optional alternative when a case needs separate guest
terminals or an old environment cannot run a modern NixOS test driver. Use
the interactive [scenario workflow](./reporting/06-scenario-mode.md)
when it supports the required lab. Keep automated tests as the primary oracle
when they are available.

## Define the machines

Use `standaloneVMGenerator` alongside `testsGenerator` if both workflows are
needed. Define vulnerable and fixed machines explicitly:

```nix
nice-archive-lib.standaloneVMGenerator {
  inherit nixpkgs;
  caseDir = ./.;
  VMs = {
    server-vulnerable = {
      configPath = ./vm-server.nix;
      isVulnerable = true;
      hostname = "server";
    };
    server-fixed = {
      configPath = ./vm-server.nix;
      isVulnerable = false;
      hostname = "server";
    };
  };
}
```

The [library reference](./nice-archive-libs.md#standalonevmgenerator)
defines the complete function and how to combine it with test outputs.
The [Git dubious ownership case](../cves/cve-2022-24765-git-dubious-ownership/flake.nix)
shows both generators in one case.

## Start and connect

```bash
nice-archive list-vms --case cve-yyyy-nnnn-short-name
nice-archive vm --case cve-yyyy-nnnn-short-name --name server-vulnerable
```

Run separate role VMs in separate terminals. If they need manual addresses,
service startup, or host port forwarding, record those commands and ports in
the case README. Host forwarding is allowed only for standalone VM wiring;
it does not authorize running the target or trigger on the host. The
[CLI guide](./cli-tool.md#launch-a-standalone-vm) covers available options.
