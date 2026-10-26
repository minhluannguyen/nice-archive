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
| `oldKernelNixosTest` | Low-level compatibility helper used by `oldKernelTestsGenerator`. Can be used directly without the `nice-archive-lib`. |

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
| `system` | No | `"x86_64-linux"` | Nix system for generated outputs. Supported values are `"x86_64-linux"` and `"aarch64-linux"`. |
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

#### Variants

There are three supported VM variants:

`variant = "invariant"` means the VM is identical in vulnerable and fixed
tests, usually for helper VMs (do not contain the affected package). The VM receives `isVulnerable = null`.

```nix
attacker = {
  configPath = ./vm-attacker.nix;
  variant = "invariant";
};
```

`variant = "package"` means the NixOS system stays on the same nixpkgs input,
but the VM configuration switches packages based on `isVulnerable`. Imagine you want to install an old vulnerable version of a package in your current "modern"  system. This is sufficient for most software, which does not depend too heavily on the kernel or other system-level components.

```nix
client = {
  configPath = ./vm-client.nix;
  variant = "package";
};
```

`variant = "system"` means the full NixOS system is evaluated from different
nixpkgs pins. For software that is tightly coupled to the OS and would break if the old version of the package is installed on a modern system. This option will take a snapshot of the nixpkgs repository at the time of the vulnerability and use that to build the whole NixOS VM. It's like traveling back in time.

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

#### Historical package pin inside a VM

For a `package` variant, select a verified historical nixpkgs revision inside
the affected VM module while leaving the surrounding NixOS system on its
normal pin. Replace the placeholder commits, hashes, and package attribute
with values independently verified for the CVE:

```nix
{ isVulnerable, ... }:
{ pkgs, ... }:
let
  pin = if isVulnerable then {
    rev = "<vulnerable-nixpkgs-commit>";
    hash = "<verified-archive-hash>";
  } else {
    rev = "<fixed-nixpkgs-commit>";
    hash = "<verified-archive-hash>";
  };
  historical = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/${pin.rev}.tar.gz";
    sha256 = pin.hash;
  }) { system = pkgs.stdenv.hostPlatform.system; };
in {
  environment.systemPackages = [ historical.openssl ];
}
```

For this example, `openssl` stands for the affected package attribute. Verify
the archive hash with `nix-prefetch-url <url> --unpack` and confirm the
evaluated package version before running the case. See the
[source-selection workflow](./reporting/02-research-and-sources.md) for the
decision order.

#### Example with `extraArgs`

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

#### Example with OCR and graphics

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

`testsGenerator` already provides interactive scenarios and guest access. Add
`standaloneVMGenerator` only when a failed scenario attempt or verified
compatibility constraint shows that scenario mode cannot run the required lab.
Record that reason in the case README.

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

When standalone outputs are needed alongside tests, use Nix attribute-set
merging:

```nix
outputs = { nixpkgs, nice-archive-lib, ... }:
  nice-archive-lib.testsGenerator {
    inherit nixpkgs;
    title = "cve-yyyy-nnnn";
    caseDir = ./.;
    testScriptPath = ./test.py;
    generateInteractiveTests = true;

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

Here, a NixOS version 22.05 is used to build the `server` machine.

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

#### Old-kernel VM fields

These fields are read in addition to the normal `testsGenerator` VM fields:

| Field | Default | Description |
| --- | --- | --- |
| `oldKernelNixpkgs` | Top-level `oldKernelNixpkgs` | Per-VM old nixpkgs source. |
| `oldKernelGraphics` | `isGraphics`, otherwise `false` | Graphics value for the old-kernel VM build; `null` defers to the historical NixOS default. |
| `oldKernelRestrictNetwork` | `null` | Network restriction value for the old-kernel VM build. |

Old-kernel guests default to headless output. Set `oldKernelGraphics = true`
for a graphical guest. Interactive scenarios replace `-nographic` with
`-display none` for headless old guests, preserving the test driver's serial
and monitor connections. Automated tests keep their existing display rewrite.
Modern helper VM launch scripts are copied unchanged.

Interactive old-kernel guests receive a socket-activated SSH listener on
vsock port 22 with an ephemeral host key. The wrapper preserves the base
driver's vsock CID; it does not expose a guest TCP port. The historical guest
needs virtio-vsock and systemd support for `ListenStream=vsock::22`; the host
needs `/dev/vhost-vsock` and the base driver's `systemd-ssh-proxy` setup.
Check the scenario status file's `ssh_verified` result before using an SSH
command. `--popup false` controls terminal windows, not QEMU graphics.

See [CVE-2022-32278](../cves/cve-2022-32278-graphical-libreoffice-rce/flake.nix) for a complete example of an old-kernel test case.

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

Interactive replacements need a guest SSH listener on vsock port 22. The
wrapper expects `export startScripts` and each replaced interactive launch
script to contain a `vhost-vsock-pci` device. The high-level generator
installs the guest listener automatically.

## NixOS test-driver methods

The generated test exposes each VM by its configured name. Common methods are
listed below; the [official NixOS test-driver reference](https://nixos.org/manual/nixos/stable/#ssec-machine-objects)
defines their exact behavior and supported timeout parameters.

| Method | Use |
| --- | --- |
| `start_all()` | Boot all machines. |
| `<vm>.start()` | Boot one machine. |
| `<vm>.wait_for_unit("name.service", timeout=seconds)` | Wait for a systemd unit. |
| `<vm>.wait_for_open_port(port, timeout=seconds)` | Wait for a listening TCP port. |
| `<vm>.succeed("command", timeout=seconds)` | Run a command that must succeed. |
| `<vm>.fail("command", timeout=seconds)` | Run a command that must fail. |
| `<vm>.execute("command", timeout=seconds)` | Inspect `(status, output)` without requiring a particular exit status. |
| `<vm>.wait_until_succeeds("command", timeout=seconds)` | Retry a command until success or timeout. |
| `<vm>.wait_for_file("/path", timeout=seconds)` | Wait for a guest file. |
| `<vm>.wait_for_x()` | Wait for X11 in a graphical test. |
| `<vm>.wait_for_text("text")` | OCR screen text when `enableOCR = true`. |
| `<vm>.copy_from_host("src", "dst")` | Copy a host file into the VM. |
| `<vm>.copy_from_vm("src", "dst")` | Copy a VM file back to the host. |

Use native `timeout=` arguments when supported, as well as application-level
connect and read timeouts for network triggers.

## Python assertion blocks

```python
import assertion_blocks as ab
```

Assertion blocks should be used as the final validation of a test whenever a helper
matches the vulnerability class. It is fine to use raw `assert` for control
flow or branch checks, but the final proof should usually be an
`assertion_blocks` helper so logs clearly show what security property was
checked.

Available helpers:

| Helper | Purpose |
| --- | --- |
| `check_service_log_contains(machine, check_message, unit, failed_message="", timeout=60)` | Wait for text in a systemd unit journal. |
| `check_root_privileges(machine, user, timeout=90)` | Check that a user has root UID and GID. |
| `check_screen_text(machine, text, timeout=60)` | Use OCR to wait for text on the VM screen. Requires `enableOCR = true`. |
| `check_file_exists(machine, file_path, is_existing=True, timeout=90)` | Check that a path exists or remains absent. |
| `check_file_contains(machine, file_path, content, timeout=90, is_existing=True)` | Check that an existing file contains or omits text. |
| `check_file_size_equals(machine, file_path, expected_size, timeout=90)` | Check exact file size in bytes. |
| `check_cpu_usage_high(machine, command, maximum_cpu_time_usage, timeout=90)` | Check that a command exceeds a CPU-time limit. |
| `check_memory_usage_high(machine, command, maximum_memory_usage, timeout=90)` | Check that a command exceeds an address-space limit. |
| `check_exact_execution_time(machine, command, expected_time, repeats=5, tolerance=0.5, timeout=90)` | Check average execution time within a tolerance. |
| `check_core_dump_exists(machine, unit_name="backdoor.service", expected_signal=None, repeats=10, repeat_command="", timeout=90)` | Find a matching systemd core dump. |

For `check_file_contains`, `is_existing` describes whether the content should
be present. The file itself must exist in both modes. Each helper passes its
`timeout` to the underlying NixOS test-driver operation; the LLM workflow's
hard command and test limits still apply independently.

### Choosing assertion blocks by attack type

Use existing cases as models:

| Vulnerability or proof type | Preferred assertion blocks | Model cases |
| --- | --- | --- |
| Privilege escalation | `check_root_privileges` | Dirty COW, PwnKit, chwoot |
| DoS / infinite loop / CPU exhaustion | `check_cpu_usage_high` | curl WebSocket loop, OpenSSL BN_mod_sqrt |
| Memory exhaustion | `check_memory_usage_high` | Use when the exploit is expected to exceed an address-space limit. |
| File write, overwrite, deletion, preservation, RCE evidence | `check_file_exists`, `check_file_contains`, `check_file_size_equals` | zgrep file write, curl removes wrong file, Heartbleed dump size/content |
| Information disclosure | `check_file_contains`, optionally `check_file_size_equals` | Heartbleed, GitLab secret snippet |
| Service crash or fatal signal | `check_core_dump_exists`, `check_service_log_contains` | sysstat double free, TensorFlow FPE, curl SASL crash |
| Log or request exfiltration | `check_service_log_contains`, `check_file_contains` | Early CCS MITM |
| Browser-executed XSS | Drive a real browser programmatically in headless/non-graphical mode unless visible UI behavior is required; then assert a browser-caused effect with `check_service_log_contains`, `check_file_contains`, or, for genuinely graphical cases, `check_screen_text` | Bleach mutation XSS, Tomcat SSI XSS |
| Graphical/UI proof | `check_screen_text` | LibreOffice graphical RCE |
| Timing side channel or delay proof | `check_exact_execution_time` | WordPress SQLi timing-style test |

### Privilege escalation example

```python
import assertion_blocks as ab

ab.check_root_privileges(server, "newuser", timeout=90)
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
    timeout=90,
)
```

### File write/delete example

Use both positive and negative assertions when the fixed behavior should
preserve or reject files.

```python
# The VM configuration plants this marker from isVulnerable.
variant = server.succeed(
    "cat /etc/nice-archive/cve-yyyy-nnnn-variant",
    timeout=10,
).strip()
if variant == "vulnerable":
    ab.check_file_exists(
        server, "/tmp/cve-xxxx-pwned", is_existing=True, timeout=90
    )
    ab.check_file_contains(
        server, "/etc/passwd", "super-secret-flag-injected", timeout=90
    )
else:
    assert variant == "fixed", f"Unknown variant marker: {variant}"
    ab.check_file_exists(
        server, "/tmp/cve-xxxx-pwned", is_existing=False, timeout=90
    )
    ab.check_file_contains(
        server,
        "/etc/passwd",
        "super-secret-flag-injected",
        is_existing=False,
        timeout=90,
    )
```

### Information disclosure example

```python
ab.check_file_size_equals(attacker, dump_file, dump_length, timeout=90)
ab.check_file_contains(attacker, dump_file, secret_key, timeout=90)
```

### Crash/core-dump example

```python
ab.check_service_log_contains(
    machine=server,
    unit="sysstatSetup.service",
    check_message="free(): double free detected",
    timeout=60,
)
ab.check_core_dump_exists(
    machine=server,
    unit_name="sysstatSetup.service",
    expected_signal="ABRT",
    timeout=90,
)
```

### Graphical/OCR example

```python
libreoffice.wait_for_x(timeout=90)
ab.check_screen_text(
    libreoffice,
    "Hello, you have been pwned!",
    timeout=60,
)
```
