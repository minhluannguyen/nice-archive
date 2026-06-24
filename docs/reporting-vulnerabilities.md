# Reporting a vulnerability with NICE Archive

This guide explains how to use NICE Archive as a framework for producing a
reproducible vulnerability report. It is intentionally step-by-step and
explicit so that both humans and LLM coding agents can follow it without
guessing project conventions.

For the library API itself, see
[NICE Archive library reference](./nice-archive-libs.md).

## Goal of a NICE Archive report

A good report case should answer five questions:

1. What vulnerability is being reproduced?
2. Which software and versions are vulnerable or fixed?
3. What virtual machines are needed to demonstrate the vulnerability?
4. What action proves exploitation or mitigation?
5. What automated assertion verifies the result?

The expected output is a directory under [`cves/`](../cves/) with:

```text
cves/cve-yyyy-nnnn-short-name/
├── flake.nix
├── test.py
├── vm-server.nix
├── vm-attacker.nix
├── exploit/
└── readme.md
```

Some reports may need fewer files, and graphical or old-kernel reports may
need more.

## Agent-friendly workflow

If you are an LLM agent working on a new report, follow this order:

1. Do read-only discovery first.
2. Identify vulnerable and fixed versions.
3. Design the VM topology.
4. Decide which NICE Archive library generator fits.
5. Implement the Nix files.
6. Implement the automated tests.
7. Use the CLI tool to start VMs and reproduce the vulnerability.
8. Run vulnerable and fixed tests.
9. Update the case README with verified commands and assertions.
10. Report exactly what changed and what was verified.

## 1. Create a case directory

Use the directory shape:

```bash
mkdir -p cves/cve-yyyy-nnnn-short-name/exploit
```

Naming convention:

```text
cve-<year>-<number>-<short-lowercase-description>
```

Examples:

```text
cve-2014-0160-heartbleed
cve-2023-7028-gitlab-email
cve-2025-32463-chwoot
```

Keep the name stable. It becomes the value passed to the CLI with
`--case`.

## 2. Collect vulnerability facts

Before writing code, capture the minimum facts needed for reproducibility:

| Fact | Example |
| --- | --- |
| CVE ID | `CVE-2025-32463` |
| Affected software | `sudo` |
| Vulnerable version or commit | `1.9.14` to before `1.9.17p1` |
| Fixed version or commit | `1.9.17p1` or a nixpkgs commit containing it |
| Vulnerability class | local privilege escalation |
| Exploit precondition | local unprivileged user |
| Success condition | attacker gets root shell or root-owned file |
| Fixed behavior | exploit fails or sensitive output is absent |

For each report, decide what the automated test should prove:

- vulnerable case: the exploit succeeds;
- fixed case: the exploit fails or the vulnerable effect is absent.

For finding the Nixpkgs commit that contains the vulnerable or fixed version, use tools like:
- [Nix package version](https://lazamar.co.uk/nix-versions/)
- [nix-versions](https://github.com/denful/nix-versions)
- Or, search the Nixpkgs Git history on GitHub for the package name and version.

## 3. Choose the VM topology

Most cases fit one of these shapes:

| Topology | Use when | Common nodes |
| --- | --- | --- |
| Single VM | Local privilege escalation, parser crash, local DoS | `server` |
| Client/server | Vulnerable client contacts controlled server, or vulnerable server receives traffic | `client`, `server` |
| Attacker/server | Exploit code should be isolated from target | `attacker`, `server` |
| Multi-service | Mail, database, proxy, NFS, LDAP, or browser workflow is needed | `attacker`, `server`, `mailserver`, `proxy`, etc. |
| Graphical | The exploit requires X11, LibreOffice, browser UI, or OCR | `desktop`, `server` |

Use clear node names because those names become Python variables in `test.py`.

## 4. Choose the generator

Generator choice is not only a style preference. It follows the history of
NixOS testing and the age of the vulnerable environment.

The NixOS Tests framework was proposed very early in NixOS history, around
2010, but early implementations were primitive and old Nixpkgs revisions often
do not contain the modern test APIs that NICE Archive uses today. Nixpkgs
gained `pkgs.nixosTests` through
[NixOS/nixpkgs#47684](https://github.com/NixOS/nixpkgs/pull/47684), and the
current `pkgs.testers.runNixOSTest` interface came later through
[NixOS/nixpkgs#225313](https://github.com/NixOS/nixpkgs/pull/225313).

The practical consequence is:

- use the modern generator when the vulnerable/fixed environments can be
  expressed with current NixOS test machinery;
- use old-kernel support when only selected machines must boot an old NixOS or
  old kernel;
- use standalone VMs when the environment is too old or too special for the
  modern NixOS test driver; and
- keep old components as narrow as possible, ideally only the vulnerable target
  machine.

Use this decision table:

| Situation | Generator |
| --- | --- |
| Normal package-level vulnerability | `testsGenerator` |
| Vulnerable/fixed full system must come from different nixpkgs pins | `testsGenerator` with `variant = "system"` |
| When `testsGenerator` is not suitable | Try `standaloneVMGenerator` |
| One or a few VMs must boot an old kernel / old NixOS while the test driver can stay modern | `oldKernelTestsGenerator` |
| You need custom low-level old-kernel patching | `oldKernelNixosTest` |
| The whole reproduction is too old for modern NixOS tests | `default.nix`, `npins`, and standalone/manual VMs |

Most new reports should start with `testsGenerator`.

When using old-kernel support, prioritize replacing the
vulnerable target. If there are multiple machines, recommend using the standalone/manual path for the machines.

## 5. Write `flake.nix`

Start with this template:

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

      VMs = {
        server = {
          configPath = ./vm-server.nix;
          variant = "package";
        };
      };
    };
}
```

The generated outputs are:

```text
test-vulnerable-true-x86_64-linux
test-vulnerable-false-x86_64-linux
start-scenario-vulnerable-true-x86_64-linux
start-scenario-vulnerable-false-x86_64-linux
```

### When to use flakes

Use `flake.nix` for new NICE Archive cases when the case can be evaluated with
modern Nix. Flakes provide a standard lock-file based way to pin dependencies
and expose outputs for `nix run`, `nix build`, and the NICE Archive CLI.

Flakes are a Nix 2.4-era feature introduced on 2021-11-01; see the
[NixOS Wiki page on Flakes](https://nixos.wiki/wiki/Flakes). They are the
right default for modern cases and for cases that can reference old nixpkgs
inputs from a modern flake.

Do not force flakes when the target environment predates flake-era Nix/Nixpkgs
support so much that the case needs older pinning and evaluation machinery.
For those cases, use `default.nix` with a pinning tool such as `npins`, as in
the Dirty COW-style legacy case. This is especially relevant for old kernels
or old NixOS releases where the modern NixOS test framework did not yet exist
or did not have the features needed by the reproduction.

Also remember the Git behavior of flakes: files must be visible to Git before
Nix copies the flake source into the store. The Flakes wiki calls this out
explicitly. The NICE Archive CLI stages the selected case before flake-based
test/scenario runs, but you should still review `git status`.

### Package variant

Use `variant = "package"` when the VM file can choose vulnerable or fixed
software with `isVulnerable`.

```nix
server = {
  configPath = ./vm-server.nix;
  variant = "package";
};
```

### System variant

Use `variant = "system"` when the entire NixOS system must be evaluated from
different nixpkgs revisions:

```nix
inputs = {
  nixpkgs-vulnerable.url = "github:NixOS/nixpkgs/<vulnerable-commit>";
  nixpkgs-fixed.url = "github:NixOS/nixpkgs/nixos-unstable";
  nice-archive-lib.url = "../../src";
};

outputs = { nixpkgs-vulnerable, nixpkgs-fixed, nice-archive-lib, ... }:
  nice-archive-lib.testsGenerator {
    nixpkgs = nixpkgs-fixed;
    title = "cve-yyyy-nnnn-short-name";
    caseDir = ./.;
    testScriptPath = ./test.py;

    VMs.server = {
      configPath = ./vm-server.nix;
      variant = "system";
      nixpkgs = {
        vulnerable = nixpkgs-vulnerable;
        fixed = nixpkgs-fixed;
      };
    };
  };
```

### Graphical or OCR case

Set `isGraphics = true` on the graphical node and `enableOCR = true` on the
generator:

```nix
nice-archive-lib.testsGenerator {
  inherit nixpkgs;
  title = "graphical-cve";
  caseDir = ./.;
  testScriptPath = ./test.py;
  enableOCR = true;

  VMs.desktop = {
    configPath = ./vm-desktop.nix;
    variant = "package";
    isGraphics = true;
  };
}
```

### Old-kernel case

Use `oldKernelTestsGenerator` when the vulnerable VM must run from an old
nixpkgs revision:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-old.url = "github:NixOS/nixpkgs/<old-commit>";
    nice-archive-lib.url = "../../src";
  };

  outputs = { nixpkgs, nixpkgs-old, nice-archive-lib, ... }:
    nice-archive-lib.oldKernelTestsGenerator {
      inherit nixpkgs;
      oldKernelNixpkgs = nixpkgs-old;

      title = "cve-yyyy-nnnn-old-kernel";
      caseDir = ./.;
      testScriptPath = ./test.py;
      oldKernelVMNames = [ "server" ];

      VMs.server = {
        configPath = ./vm-server.nix;
        variant = "package";
      };
    };
}
```

## 6. Write VM modules

Each VM module receives NICE Archive metadata first, then NixOS module
arguments:

```nix
{ isVulnerable, isTest ? false, isScenario ? true, ... }:
{ pkgs, lib, ... }:

let
  package =
    if isVulnerable then
      pkgs.vulnerablePackage
    else
      pkgs.fixedPackage;
in
{
  environment.systemPackages = [ package ];
}
```

The package names above are placeholders. In a real report, use one of these
patterns:

- select packages from different nixpkgs pins;
- override package version and source with `overrideAttrs`;
- copy exploit files into the VM with `pkgs.runCommand`;
- create helper scripts with `pkgs.writeShellScriptBin` or
  `pkgs.writeScriptBin`; or
- configure systemd services for vulnerable servers.

### Server VM pattern

```nix
{ isVulnerable, listenPort ? 8080, ... }:
{ pkgs, ... }:

let
  app = pkgs.writeShellScriptBin "vulnerable-service" ''
    exec ${pkgs.python3}/bin/python3 ${./exploit/server.py} --port ${toString listenPort}
  '';
in
{
  networking.firewall.allowedTCPPorts = [ listenPort ];

  environment.systemPackages = [ app ];

  systemd.services.vulnerable-service = {
    wantedBy = [ "multi-user.target" ];
    path = [ app ];
    script = ''
      vulnerable-service
    '';
  };
}
```

### Attacker VM pattern

```nix
{ ... }:
{ pkgs, ... }:

let
  exploit = pkgs.runCommand "exploit-files" {} ''
    mkdir -p "$out"
    cp -r ${./exploit} "$out/exploit"
  '';
in
{
  environment.systemPackages = [
    exploit
    pkgs.curl
    pkgs.python3
  ];
}
```

## 7. Write `test.py`

The generated NixOS test exposes each VM using the name from `VMs`.

Basic structure:

```python
# pyright: reportUndefinedVariable=false

import assertion_blocks as ab

start_all()

server.wait_for_unit("multi-user.target")
server.wait_for_unit("vulnerable-service.service")
server.wait_for_open_port(8080)

attacker.wait_for_unit("multi-user.target")
attacker.succeed("run-exploit http://server:8080")

ab.check_file_contains(attacker, "/tmp/result.txt", "Pwned!")
```

Useful NixOS test-driver methods include:

| Method | Use |
| --- | --- |
| `start_all()` | Boot all machines. |
| `<vm>.start()` | Boot one machine. |
| `<vm>.wait_for_unit("name.service")` | Wait for a systemd unit. |
| `<vm>.wait_for_open_port(port)` | Wait for a listening TCP port. |
| `<vm>.succeed("command")` | Run a command that must exit 0. |
| `<vm>.fail("command")` | Run a command that must fail. |
| `<vm>.execute("command")` | Run a command and inspect `(status, output)`. |
| `<vm>.wait_until_succeeds("command", timeout)` | Retry until command succeeds. |
| `<vm>.wait_for_file("/path")` | Wait for a file to appear. |
| `<vm>.wait_for_x()` | Wait for X11 in graphical tests. |
| `<vm>.wait_for_text("text")` | OCR screen text when `enableOCR = true`. |
| `<vm>.copy_from_host("src", "dst")` | Copy a host file into the VM during a test. |
| `<vm>.copy_from_vm("src", "dst")` | Copy a VM file back to the host during a test. |

Use assertions to describe the expected security property. The full helper list
is in the [library reference](./nice-archive-libs.md#python-assertion-blocks).

```python
ab.check_file_exists(server, "/tmp/important.txt")
ab.check_file_contains(attacker, "/tmp/leak.txt", "secret")
ab.check_root_gid(server, "newuser")
ab.check_screen_text(desktop, "Hello, you have been pwned!", timeout=60)
```

## 8. Add standalone VMs when useful

Standalone VMs are for manual reproduction and debugging. Add them only when a
human benefits from opening a machine outside the test driver or the test driver is not compatible with the vulnerable environment.

```nix
nice-archive-lib.testsGenerator {
  # Put the testsGenerator arguments from the earlier examples here.
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
}
```

List them from the repository root:

```bash
nix run . -- list-vms --case cve-yyyy-nnnn-short-name
```

Run one:

```bash
nix run . -- vm --case cve-yyyy-nnnn-short-name --name server-vulnerable
```

## 9. Use the CLI for testing and debugging

Run CLI commands from the repository root.

List cases:

```bash
nix run . -- list-cves
```

Run vulnerable and fixed tests:

```bash
nix run . -- test --case cve-yyyy-nnnn-short-name --vulnerable true
nix run . -- test --case cve-yyyy-nnnn-short-name --vulnerable false
```

Save a full log with a custom filename:

```bash
nix run . -- test \
  --case cve-yyyy-nnnn-short-name \
  --vulnerable true \
  --log file debug-vulnerable.log
```

Print live output:

```bash
nix run . -- test \
  --case cve-yyyy-nnnn-short-name \
  --vulnerable true \
  --log live
```

The CLI runs `git add <case-dir>` before flake-based tests and scenarios so
that new case files are visible to Nix's Git-backed flake evaluation. Review
`git status` before committing.

## 10. Use the interactive helper

The interactive helper is useful when an automated test fails or when you need
to explore a VM manually.

Start the guided menu:

```bash
nix run . -- start
```

Start an interactive scenario directly:

```bash
nix run . -- scenario \
  --case cve-yyyy-nnnn-short-name \
  --vulnerable true \
  --popup false
```

What the scenario command does:

1. cleans previous generated VM artifacts for the case;
2. builds and starts the generated `start-scenario-*` test driver;
3. waits until the NixOS test driver exposes SSH backdoors;
4. runs the interactive setup block generated by the library;
5. prints SSH commands for each VM; and
6. optionally opens `terminator` windows when `--popup true`.

Inside the interactive test-driver session, useful commands are:

```python
start_all()
server.wait_for_unit("multi-user.target")
server.succeed("id")
server.succeed("journalctl -u vulnerable-service --no-pager")
```

Exit with `Ctrl+D` in the scenario terminal and choose to kill the VMs.

## 11. Debug and reproduce on real VMs

Automated tests are the final proof, but most vulnerability reports are easier
to build if you can reproduce the exploit manually in real VMs first.

There are three supported debugging paths.

### Path A: start a scenario, then SSH into the machines

Use this path for modern library-backed cases. It is the easiest path when
`start-scenario-*` outputs exist.

```bash
nix run . -- scenario \
  --case cve-yyyy-nnnn-short-name \
  --vulnerable true \
  --popup false
```

The CLI prints SSH commands after the test driver is ready, for example:

```text
ℹ️ To access the machines, use the following SSH commands:
  - attacker: ssh -o User=root vsock-mux//run/user/1000/tmpc4pekkyh/attacker_host.socket
  - client: ssh -o User=root vsock-mux//run/user/1000/tmpc4pekkyh/client_host.socket
  - server: ssh -o User=root vsock-mux//run/user/1000/tmpc4pekkyh/server_host.socket
ℹ️ To exit the scenario, press Ctrl+D in this terminal and choose 'Yes' to kill the VMs.

```

Open another terminal, paste the SSH command for the target VM, and reproduce
the exploit manually:

```bash
# terminal 1: scenario remains running
nix run . -- scenario --case cve-yyyy-nnnn-short-name --vulnerable true --popup false

# terminal 2: use the printed command
<paste the printed ssh command>
```

Inside the VM, you can run the exploit, check logs, and inspect files. When the manual flow works, translate the commands into `test.py`.

### Path B: run standalone VMs manually

Use this path when the vulnerability is too old or too awkward for the modern
NixOS test driver, or when the report needs manual VM terminals. This is common
for old Nixpkgs revisions that do not have NixOS Tests or advanced test-driver
features.

Expose standalone VMs with `standaloneVMGenerator`, then list them:

```bash
nix run . -- list-vms --case cve-yyyy-nnnn-short-name
```

Start each VM in a separate terminal:

```bash
# terminal 1
nix run . -- vm --case cve-yyyy-nnnn-short-name --name server-vulnerable

# terminal 2
nix run . -- vm --case cve-yyyy-nnnn-short-name --name attacker
```

For standalone VMs, you must wire the reproduction environment yourself. That
usually means one or more of:

- adding `virtualisation.forwardPorts` in the VM config;
- using host ports to connect the attacker and target;
- configuring static service addresses in `/etc/hosts`;
- starting services manually inside the guests; and
- keeping several terminal windows open at the same time.

Document the manual wiring in the case README so another user can reproduce
the exploit without reading the Nix code.

### Path C: use old-kernel VM support

Use this path when the vulnerability is specifically tied to an old Linux
kernel or an old NixOS VM, but the overall test can still be controlled by a
modern test driver.

Prefer replacing only the vulnerable target VM:

```nix
nice-archive-lib.oldKernelTestsGenerator {
  inherit nixpkgs;
  oldKernelNixpkgs = nixpkgs-old;
  oldKernelVMNames = [ "server" ];

  title = "cve-yyyy-nnnn-old-kernel";
  caseDir = ./.;
  testScriptPath = ./test.py;

  VMs.server = {
    configPath = ./vm-server.nix;
    variant = "package";
  };
}
```

Keep helper machines modern unless they must also be old. This reduces boot
fragility, network wiring problems, and evaluation failures.

## 12. Verify in cheap-to-expensive order

Recommended order:

1. Check file presence:

   ```bash
   rg --files cves/cve-yyyy-nnnn-short-name
   ```

2. Check CLI discovery:

   ```bash
   nix run . -- list-cves
   nix run . -- list-vms --case cve-yyyy-nnnn-short-name
   ```

3. Evaluate or inspect flake outputs if needed.

4. Run the vulnerable test with live logs:

   ```bash
   nix run . -- test \
     --case cve-yyyy-nnnn-short-name \
     --vulnerable true \
     --log live
   ```

5. Run the fixed test:

   ```bash
   nix run . -- test \
     --case cve-yyyy-nnnn-short-name \
     --vulnerable false \
     --log file
   ```

6. If the test fails, use the scenario helper and inspect VM state.

## 13. Write the case README

Each CVE README should be understandable without reading the implementation.

Recommended structure:

```markdown
# CVE-YYYY-NNNN: short title

## Description

## Overview

- Affected software:
- Impact:
- Vulnerable versions:
- Fixed versions:
- Disclosure date:

## Reproduction design

## Running automated tests

## Interactive debugging

## Assertions

## References
```

Include exact commands that were verified. Prefer CLI commands first, because
the CLI knows the modern output naming convention and legacy fallback.

## 14. Final checklist

Before considering the report done:

- [ ] The vulnerable test demonstrates the exploit or vulnerable behavior.
- [ ] The fixed test demonstrates mitigation or absence of the vulnerable effect.
- [ ] The assertion checks the security property, not just command completion.
- [ ] `flake.nix` uses the appropriate generator.
- [ ] VM names are clear and match variables in `test.py`.
- [ ] Any graphical test sets `isGraphics = true` and `enableOCR = true`.
- [ ] The README explains why the chosen generator fits the age and shape of the vulnerability.
- [ ] Manual reproduction steps are documented when standalone VMs or SSH scenarios are needed.
- [ ] Any old-kernel test uses `oldKernelTestsGenerator` unless it needs custom low-level behavior.
- [ ] The case README explains the topology, exploit, assertions, and commands.
- [ ] Generated logs, `result` symlinks, `.qcow2` files, and `.nixos-test-history` are not accidentally committed.

## 15. References

- [NixOS/nixpkgs#47684](https://github.com/NixOS/nixpkgs/pull/47684)
- [NixOS/nixpkgs#225313](https://github.com/NixOS/nixpkgs/pull/225313)
- [NixOS Wiki: Flakes](https://nixos.wiki/wiki/Flakes)

## 16. Handoff note template (for LLM agents)

When handing off a report, summarize:

```text
Implemented:
- Files added/changed:
- Generator used:
- VM topology:
- Vulnerable version:
- Fixed version:

Verified:
- Command:
- Result:
- Log file:

Known limitations:
- <list limitations, or write "none">
```
