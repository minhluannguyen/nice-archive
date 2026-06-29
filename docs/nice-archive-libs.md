# NICE Archive library reference

This document is the technical reference for the reusable library code in
[`src/`](../src/). It focuses on library syntax, exported functions, VM
configuration conventions, and compact examples.

For a step-by-step workflow for creating a full vulnerability report, see
[Reporting a vulnerability with NICE Archive](./reporting-vulnerabilities.md).

## Exports

The library can be used as a flake input:

```nix
inputs = {
  nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  nice-archive-lib.url = "../../src";
};
```

or imported without flakes:

```nix
let
  nice-archive-lib = import ../../src/default.nix;
in
{
  # Use the library exports here.
}
```

It exports:

| Export | Purpose |
| --- | --- |
| `testsGenerator` | Generates vulnerable/fixed NixOS test outputs and optional interactive scenarios. |
| `standaloneVMGenerator` | Generates named standalone QEMU VM outputs under `standaloneVMs`. |
| `oldKernelTestsGenerator` | Generates normal test outputs, then replaces selected machines with old-kernel VM builds. |
| `oldKernelNixosTest` | Low-level compatibility helper used by `oldKernelTestsGenerator`. |

## Generated test outputs

For `system = "x86_64-linux"`, `testsGenerator` and
`oldKernelTestsGenerator` produce:

```text
test-vulnerable-true-x86_64-linux
test-vulnerable-false-x86_64-linux
start-scenario-vulnerable-true-x86_64-linux
start-scenario-vulnerable-false-x86_64-linux
```

The `start-scenario-*` outputs are omitted when
`generateInteractiveTests = false`.

The NICE Archive CLI expects these names first and falls back to legacy
`testVulnerableTrue` / `testVulnerableFalse` outputs only for older cases.

## VM configuration function shape

Every generated VM points to a `configPath`. That file should be a function
returning a NixOS module:

```nix
{ isVulnerable
, isTest ? false
, isScenario ? true
, isGraphics ? false
, isOldKernelVM ? false
, pkgs
, config
, lib
, modulesPath
, ...
}:
{ pkgs, lib, ... }:

{
  environment.systemPackages = [
    pkgs.curl
  ];
}
```

The first function receives NICE Archive metadata. The second function is the
usual NixOS module argument set.

| Argument | Meaning |
| --- | --- |
| `isVulnerable` | `true`, `false`, or `null` for invariant VMs. |
| `isTest` | `true` in NixOS tests, `false` for standalone VMs. |
| `isScenario` | `true` for interactive scenarios and standalone VMs, `false` for automated tests. |
| `isGraphics` | Whether the generated VM should use graphical QEMU output. For tests, it is `false` by default. |
| `isOldKernelVM` | Whether the VM is being generated for old-kernel compatibility. |
| `pkgs`, `config`, `lib`, `modulesPath` | NixOS module context values passed through by the template. |
| `...` | Values provided through `extraArgs`. |

The shared VM template adds a minimal baseline:

- `system.stateVersion = "24.09"`;
- `networking.hostName`;
- Bash and coreutils;
- root password `root` for standalone VMs;
- optional `virtualisation.graphics`; and
- optional `virtualisation.restrictNetwork`.

The current public field is spelled `isRetrictNetwork` in the library. Use
that exact spelling until the API is migrated.

## `testsGenerator`

Use `testsGenerator` for ordinary CVE reproductions where vulnerable and fixed
variants can be represented by package selection or nixpkgs pinning.

### Syntax

```nix
nice-archive-lib.testsGenerator {
  inherit nixpkgs;

  title = "cve-yyyy-nnnn-example";
  caseDir = ./.;
  system = "x86_64-linux";
  testScriptPath = ./test.py;
  generateInteractiveTests = true;
  enableOCR = false;

  VMs = {
    server = {
      configPath = ./vm-server.nix;
      variant = "package";
    };

    attacker = {
      configPath = ./vm-attacker.nix;
      variant = "invariant";
    };
  };
}
```

### Arguments

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `nixpkgs` | Yes | — | Base nixpkgs source or flake input. |
| `title` | Yes | — | Test name prefix. |
| `caseDir` | Yes | — | CVE directory, usually `./.`. |
| `testScriptPath` | Yes | — | Python NixOS test script. |
| `VMs` | No | `{}` | Attribute set of VM definitions. |
| `system` | No | `"x86_64-linux"` | Nix system for generated outputs. |
| `generateInteractiveTests` | No | `true` | Generate `start-scenario-*` outputs. |
| `enableOCR` | No | `false` | Enable OCR support in the NixOS test driver. Required for `wait_for_text` and `check_screen_text`. |

### VM fields

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `configPath` | Yes | — | Path to the VM configuration function. |
| `variant` | No | Inferred | `invariant`, `package`, or `system`. |
| `nixpkgs` | For `system` | — | Vulnerable/fixed nixpkgs pair. |
| `extraArgs` | No | `{}` | Extra values passed to the VM configuration function. |
| `isRetrictNetwork` | No | `true` | Value for `virtualisation.restrictNetwork`. |
| `isGraphics` | No | `false` | Value for `virtualisation.graphics`. |
| `isOldKernelVM` | No | `false` | Imports the old-kernel backdoor service when true. Usually set by `oldKernelTestsGenerator`. |

### Variants

`variant = "invariant"` means the VM is identical in vulnerable and fixed
tests. The VM receives `isVulnerable = null`.

```nix
attacker = {
  configPath = ./vm-attacker.nix;
  variant = "invariant";
};
```

`variant = "package"` means the NixOS system stays on the same nixpkgs input,
but the VM configuration switches packages based on `isVulnerable`.

```nix
client = {
  configPath = ./vm-client.nix;
  variant = "package";
};
```

`variant = "system"` means the full NixOS system is evaluated from different
nixpkgs pins.

```nix
server = {
  configPath = ./vm-server.nix;
  variant = "system";
  nixpkgs = {
    vulnerable = nixpkgs-vulnerable;
    fixed = nixpkgs-fixed;
  };
};
```

All `system` VMs in one generated test must currently share the same
vulnerable/fixed nixpkgs pair. Use `invariant` for helper machines that do not
need system-level pinning.

If `variant` is omitted, the generator infers:

- `system` when the VM definition contains vulnerable/fixed nixpkgs pinning;
- `invariant` otherwise.

Prefer explicit variants in new cases.

### Example with `extraArgs`

```nix
VMs = {
  server = {
    configPath = ./vm-server.nix;
    variant = "package";
    extraArgs = {
      listenPort = 9999;
      plantedMessage = "NICE-Archive-Test";
    };
  };
};
```

The VM can consume those values:

```nix
{ isVulnerable, listenPort, plantedMessage, ... }:
{ pkgs, ... }:

{
  networking.firewall.allowedTCPPorts = [ listenPort ];

  environment.etc."planted-message.txt".text = plantedMessage;
}
```

### Example with OCR and graphics

```nix
nice-archive-lib.testsGenerator {
  inherit nixpkgs;
  title = "graphical-case";
  caseDir = ./.;
  testScriptPath = ./test.py;
  enableOCR = true;

  VMs = {
    desktop = {
      configPath = ./vm-desktop.nix;
      variant = "package";
      isGraphics = true;
    };
  };
}
```

Use OCR assertions from the test script:

```python
import assertion_blocks as ab

desktop.wait_for_x()
ab.check_screen_text(desktop, "Hello, you have been pwned!", timeout=60)
```

## `standaloneVMGenerator`

Use `standaloneVMGenerator` when a case should expose manually runnable VMs in
addition to automated tests.

### Syntax

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

This creates:

```text
standaloneVMs.server-vulnerable
standaloneVMs.server-fixed
```

### Arguments

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `nixpkgs` | Yes | — | Default nixpkgs source for standalone VMs. |
| `caseDir` | Yes | — | CVE directory, usually `./.`. |
| `system` | No | `"x86_64-linux"` | Nix system. |
| `VMs` | No | `[]` | Attribute set of standalone VM definitions. |

### Standalone VM fields

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `configPath` | Yes | — | Path to the VM configuration function. |
| `isVulnerable` | No | `null` | Value passed to the VM configuration. |
| `nixpkgs` | No | Generator `nixpkgs` | Per-VM nixpkgs source. |
| `hostname` | No | VM attribute name | Guest hostname. |
| `extraArgs` | No | `{}` | Extra values passed to the VM configuration function. |
| `isRetrictNetwork` | No | `true` | Value for `virtualisation.restrictNetwork`. |
| `isGraphics` | No | `false` | Value for `virtualisation.graphics`. |
| `isOldKernelVM` | No | `false` | Imports the old-kernel backdoor service when true. |

## Combining tests and standalone VMs

Use Nix attribute-set merging:

```nix
outputs = { nixpkgs, nice-archive-lib, ... }:
  nice-archive-lib.testsGenerator {
    inherit nixpkgs;
    title = "cve-yyyy-nnnn";
    caseDir = ./.;
    testScriptPath = ./test.py;

    VMs.server = {
      configPath = ./vm-server.nix;
      variant = "package";
    };
  }
  //
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
  };
```

## `oldKernelTestsGenerator`

Use `oldKernelTestsGenerator` when the vulnerable or fixed scenario must boot
one or more machines from an older nixpkgs revision, while still keeping the
modern `testsGenerator` output shape.

It first creates normal base outputs, then replaces one selected scenario with
drivers patched by `oldKernelNixosTest`.

### Syntax

```nix
nice-archive-lib.oldKernelTestsGenerator {
  inherit nixpkgs;
  oldKernelNixpkgs = nixpkgs-22_05;

  title = "cve-yyyy-nnnn-old-kernel";
  caseDir = ./.;
  testScriptPath = ./test.py;

  isVulnerable = true;
  oldKernelVMNames = [ "server" ];
  enableOCR = false;

  VMs = {
    server = {
      configPath = ./vm-server.nix;
      variant = "package";
      oldKernelGraphics = false;
      oldKernelRestrictNetwork = null;
    };

    client = {
      configPath = ./vm-client.nix;
      variant = "invariant";
    };
  };
}
```

When `isVulnerable = true`, the old-kernel driver replaces
`test-vulnerable-true-${system}` and, if enabled,
`start-scenario-vulnerable-true-${system}`. Set `isVulnerable = false` when
the fixed scenario should use the old-kernel machines.

### Arguments

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `nixpkgs` | Yes | — | Modern nixpkgs source for base outputs and non-old-kernel scenarios. |
| `oldKernelNixpkgs` | Usually | `null` | Default old nixpkgs source for old-kernel machines. |
| `title` | Yes | — | Test name prefix. |
| `caseDir` | Yes | — | CVE directory. |
| `testScriptPath` | Yes | — | Python NixOS test script. |
| `VMs` | No | `{}` | VM definitions. |
| `system` | No | `"x86_64-linux"` | Nix system. |
| `isVulnerable` | No | `true` | Scenario replaced by old-kernel machines. |
| `oldKernelVMNames` | No | `builtins.attrNames VMs` | VM names to rebuild from old nixpkgs. |
| `generateInteractiveTests` | No | `true` | Generate and patch `start-scenario-*` outputs. |
| `enableOCR` | No | `false` | Enable OCR in the generated test driver. |

### Old-kernel VM fields

These fields are read in addition to the normal `testsGenerator` VM fields:

| Field | Default | Description |
| --- | --- | --- |
| `oldKernelNixpkgs` | Top-level `oldKernelNixpkgs` | Per-VM old nixpkgs source. |
| `oldKernelGraphics` | `isInteractive` | Graphics value for the old-kernel VM build. |
| `oldKernelRestrictNetwork` | `null` | Network restriction value for the old-kernel VM build. |

### LibreOffice-style graphical example

```nix
nice-archive-lib.oldKernelTestsGenerator {
  title = "CVE-2022-32278 (LibreOffice/XFCE graphical RCE)";
  caseDir = ./.;

  inherit nixpkgs;
  oldKernelNixpkgs = nixpkgs-22_05;
  oldKernelVMNames = [ "libreoffice" ];
  enableOCR = true;

  VMs = {
    libreoffice = {
      configPath = ./libreoffice-vm-graphical.nix;
      variant = "package";
      isGraphics = true;
      oldKernelGraphics = true;
      extraArgs = {
        isNFS = true;
      };
    };

    nfsserver = {
      configPath = ./libreoffice-vm-nfs-server.nix;
      variant = "invariant";
      isGraphics = false;
    };
  };

  testScriptPath = ./test.py;
}
```

## `oldKernelNixosTest`

`oldKernelNixosTest` is the low-level helper used by
`oldKernelTestsGenerator`. Use it directly only when the high-level generator
does not fit.

```nix
let
  patchedDriver = nice-archive-lib.oldKernelNixosTest {
    pkgs = pkgsUnstable;
    oldKernelVMs = {
      server = oldServerForTest;
    };
    testBase.driver = baseDriver;
    isInteractive = false;
  };
in
{
  "test-vulnerable-true-x86_64-linux" = patchedDriver;
}
```

| Argument | Description |
| --- | --- |
| `pkgs` | Modern package set used to construct the patched driver derivation. |
| `oldKernelVMs` | Attribute set mapping test node names to old NixOS system evaluations. |
| `testBase` | Attribute set exposing `driver` or `driverInteractive`. |
| `isInteractive` | Selects `testBase.driverInteractive` when true. |

The keys in `oldKernelVMs` must match the machine names in the base test
driver.

## Python assertion blocks

`testsGenerator` and `oldKernelTestsGenerator` add the `assertion_blocks`
Python package to the NixOS test environment.

```python
import assertion_blocks as ab
```

Assertion blocks should be used as the final oracle of a test whenever a helper
matches the vulnerability class. It is fine to use raw `assert` for control
flow or branch checks, but the final proof should usually be an
`assertion_blocks` helper so logs clearly show what security property was
checked.

Available helpers:

| Helper | Purpose |
| --- | --- |
| `check_service_log_contains(machine, check_message, unit, failed_message="")` | Wait for text in a systemd unit journal. |
| `check_root_gid(machine, user)` | Check that a user has root UID and GID. |
| `check_screen_text(machine, text, timeout=60)` | Use OCR to wait for text on the VM screen. Requires `enableOCR = true`. |
| `check_file_exists(machine, file_path, is_existing=True, timeout=90)` | Check that a path exists or remains absent. |
| `check_file_contains(machine, file_path, content, timeout=90)` | Check that a file contains text. |
| `check_file_size_equals(machine, file_path, expected_size, timeout=90)` | Check exact file size in bytes. |
| `check_cpu_usage_high(machine, command, maximum_cpu_time_usage)` | Check that a command exceeds a CPU-time limit. |
| `check_memory_usage_high(machine, command, maximum_memory_usage)` | Check that a command exceeds an address-space limit. |
| `check_exact_execution_time(machine, command, expected_time, repeats=5, tolerance=0.5)` | Check average execution time within a tolerance. |
| `check_core_dump_exists(machine, unit_name="backdoor.service", expected_signal=None, repeats=10, repeat_command="")` | Find a matching systemd core dump. |

### Choosing assertion blocks by attack type

Use existing cases as models:

| Vulnerability or proof type | Preferred assertion blocks | Model cases |
| --- | --- | --- |
| Privilege escalation | `check_root_gid` | Dirty COW, PwnKit, chwoot |
| DoS / infinite loop / CPU exhaustion | `check_cpu_usage_high` | curl WebSocket loop, OpenSSL BN_mod_sqrt |
| Memory exhaustion | `check_memory_usage_high` | Use when the exploit is expected to exceed an address-space limit. |
| File write, overwrite, deletion, or preservation | `check_file_exists`, `check_file_contains`, `check_file_size_equals` | zgrep file write, curl removes wrong file, Heartbleed dump size/content |
| Information disclosure | `check_file_contains`, optionally `check_file_size_equals` | Heartbleed, GitLab secret snippet |
| Service crash or fatal signal | `check_core_dump_exists`, `check_service_log_contains` | sysstat double free, TensorFlow FPE, curl SASL crash |
| Log or request exfiltration | `check_service_log_contains`, `check_file_contains` | Tomcat SSI XSS, Early CCS MITM |
| Graphical/UI proof | `check_screen_text` | LibreOffice graphical RCE |
| Timing side channel or delay proof | `check_exact_execution_time` | WordPress SQLi timing-style test |

### Privilege escalation example

```python
import assertion_blocks as ab

ab.check_root_gid(server, "newuser")
```

### DoS / CPU exhaustion example

Use this style for bugs where the vulnerable command consumes CPU until it is
limited by `prlimit`. The curl WebSocket loop and OpenSSL BN_mod_sqrt tests are
good models.

```python
import assertion_blocks as ab

ab.check_cpu_usage_high(
    client,
    command="start-client",
    maximum_cpu_time_usage="30",
)
```

### File write/delete example

Use both positive and negative assertions when the fixed behavior should
preserve or reject files.

```python
if variant == "vulnerable":
    ab.check_file_contains(server, f"{workdir}/hacked", "NICE-CVE-WRITE")
    ab.check_file_exists(server, f"{workdir}/hacked2")
else:
    assert variant == "fixed", f"Unknown variant marker: {variant}"
    ab.check_file_exists(server, f"{workdir}/hacked2", is_existing=False)
    ab.check_file_contains(server, f"{workdir}/hacked", "protected original")
```

### Information disclosure example

```python
ab.check_file_size_equals(attacker, dump_file, dump_length)
ab.check_file_contains(attacker, dump_file, secret_key)
```

### Crash/core-dump example

```python
ab.check_service_log_contains(
    machine=server,
    unit="sysstatSetup.service",
    check_message="free(): double free detected",
)
ab.check_core_dump_exists(
    machine=server,
    unit_name="sysstatSetup.service",
    expected_signal="ABRT",
)
```

### Graphical/OCR example

```python
libreoffice.wait_for_x()
ab.check_screen_text(
    libreoffice,
    "Hello, you have been pwned!",
    timeout=60,
)
```
