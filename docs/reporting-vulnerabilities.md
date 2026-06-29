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
3. What does the scenario look like, and which machines are involved?
4. How are the machines are configured to reproduce the vulnerability?
4. What action triggers the vulnerability?
5. Which assertion can be used to check the vulnerability of the system?

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
3. Record exploit provenance before copying or adapting exploit code.
4. Search nixpkgs history before building vulnerable software from source.
5. Design the VM topology.
6. Decide which NICE Archive library generator fits.
7. Implement the Nix files.
8. Start the VM scenario or standalone VMs and reproduce the vulnerability manually.
9. Prefer SSH or popup VM windows for manual reproduction.
10. Translate the successful manual workflow into `test.py`.
11. End the automated test with suitable `assertion_blocks` helpers.
12. Run vulnerable and fixed tests.
13. Update the case README with verified human commands and automated assertions.
14. Report exactly what changed and what was verified.

## LLM reproduction contract

When using this framework, an LLM agent should treat the following as hard
requirements:

- Prefer existing nixpkgs packages and historical nixpkgs revisions over
  building vulnerable software from source.
- Use `nix-versions` or Nixpkgs history before deciding that a source build is
  necessary.
- Follow existing case style before inventing a new structure. Heartbleed is a
  good model for historical user-space packages.
- Use the scenario helper plus SSH for manual validation when possible.
- Use standalone VMs for manual validation when the NixOS test driver is not a
  good fit.
- Do not stop after Nix files evaluate; manually reproduce the exploit in a VM.
- Convert the manual workflow into `test.py`.
- End `test.py` with framework assertion blocks whenever one fits.
- Add exploit provenance and human manual reproduction commands to the CVE
  README.
- Point readers to `test.py` as the machine-checkable oracle.

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

### Exploit provenance

Before integrating exploit code, record where it came from and how it was
changed:

- original advisory URL;
- upstream patch or commit, if known;
- exploit source URL, if copied or adapted;
- whether the exploit was copied, modified, simplified, or rewritten;
- why any changes were needed for the NixOS VM environment; and
- any safety limits added for automated testing.

This information belongs in the CVE README, not only in code comments.

### Package source strategy

Before building vulnerable software from source, check whether nixpkgs already
contains the vulnerable and fixed versions.

Useful tools:

- [Nix package versions](https://lazamar.co.uk/nix-versions/)
- [nix-versions](https://github.com/denful/nix-versions)
- Nixpkgs Git history on GitHub

Example:

```bash
nix shell github:denful/nix-versions -c nix-versions --nixhub --all gzip
```

Use this priority order:

1. Prefer an existing nixpkgs package at a historical nixpkgs revision.
2. For normal user-space packages, follow the Heartbleed style: fetch or select
   the historical package inside the VM module, usually with
   `builtins.fetchTarball` and `import`.
3. If the vulnerable component is a system-level component, distribution
   service, kernel, or tightly coupled dependency set, use `variant = "system"`
   or an old-kernel generator.
4. Use `overrideAttrs` when nixpkgs has the package but needs a small source or
   version adjustment.
5. Build from source only after nixpkgs history does not provide a suitable
   package/version.

Keep package-selection logic close to the VM that needs it. Avoid moving
user-space package selection into the top-level `flake.nix` unless the whole
system pin must change.

## 3. Choose the VM topology

Most cases fit one of these shapes (but some exploits need more complex topologies, so feel free to adapt):

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
| Modern test exists, but humans also need direct/manual VMs | Add `standaloneVMGenerator` |
| One or a few VMs must boot an old kernel / old NixOS while the test driver can stay modern | `oldKernelTestsGenerator` |
| You need custom low-level old-kernel patching | `oldKernelNixosTest` |
| The whole reproduction is too old for modern NixOS tests | `default.nix`, `npins`, and standalone/manual VMs |

Most new reports should start with `testsGenerator`.

When using old-kernel support, prioritize replacing only the vulnerable
target. If many machines must be old at the same time, the standalone/manual
path is usually easier to debug and document.

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

The end of the test should be the machine-checkable oracle. Prefer the
framework's assertion blocks for that oracle:

- use raw `assert` only for control flow, variant checks, or values that do not
  fit an assertion helper;
- finish vulnerable and fixed branches with `assertion_blocks` helpers when a
  helper fits; and
- model new tests on existing cases such as Heartbleed, curl-ws-loop, zgrep
  file write, Dirty COW, chwoot, LibreOffice, and GitLab email reset.

For example:

```python
if variant == "vulnerable":
    ab.check_file_contains(server, f"{workdir}/hacked", "NICE-CVE-WRITE")
    ab.check_file_exists(server, f"{workdir}/hacked2")
else:
    assert variant == "fixed", f"Unknown variant marker: {variant}"
    ab.check_file_exists(server, f"{workdir}/hacked2", is_existing=False)
    ab.check_file_contains(server, f"{workdir}/hacked", "protected original")
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

Use assertions to describe the expected security property, not merely that a
command exited. The full helper list and attack-type mapping is in the
[library reference](./nice-archive-libs.md#python-assertion-blocks).

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
nice-archive list-vms --case cve-yyyy-nnnn-short-name
```

Run one:

```bash
nice-archive vm --case cve-yyyy-nnnn-short-name --name server-vulnerable
```

## 9. Use the CLI for testing and debugging

Run CLI commands from the repository root.

List cases:

```bash
nice-archive list-cves
```

Run vulnerable and fixed tests:

```bash
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable true
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable false
```

Save a full log with a custom filename:

```bash
nice-archive test \
  --case cve-yyyy-nnnn-short-name \
  --vulnerable true \
  --log file debug-vulnerable.log
```

Print live output:

```bash
nice-archive test \
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
nice-archive start
```

Start an interactive scenario directly:

```bash
nice-archive scenario \
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
nice-archive scenario \
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
nice-archive scenario --case cve-yyyy-nnnn-short-name --vulnerable true --popup false

# terminal 2: use the printed command
<paste the printed ssh command>
```

Inside the VM, run the exploit exactly as a human researcher would, check logs,
and inspect files. When the manual flow works, translate the commands into
`test.py`.

### Path B: run standalone VMs manually

Use this path when the vulnerability is too old or too awkward for the modern
NixOS test driver, or when the report needs manual VM terminals. This is common
for old Nixpkgs revisions that do not have NixOS Tests or advanced test-driver
features.

Expose standalone VMs with `standaloneVMGenerator`, then list them:

```bash
nice-archive list-vms --case cve-yyyy-nnnn-short-name
```

Start each VM in a separate terminal:

```bash
# terminal 1
nice-archive vm --case cve-yyyy-nnnn-short-name --name server-vulnerable

# terminal 2
nice-archive vm --case cve-yyyy-nnnn-short-name --name attacker
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
   nice-archive list-cves
   nice-archive list-vms --case cve-yyyy-nnnn-short-name
   ```

3. Evaluate or inspect flake outputs if needed.

4. Run the vulnerable test with live logs:

   ```bash
   nice-archive test \
     --case cve-yyyy-nnnn-short-name \
     --vulnerable true \
     --log live
   ```

5. Run the fixed test:

   ```bash
   nice-archive test \
     --case cve-yyyy-nnnn-short-name \
     --vulnerable false \
     --log file
   ```

6. If the test fails, use the scenario helper and inspect VM state.

## 13. Write the case README

Each CVE README should be understandable without reading the implementation.

Recommended structure:

````markdown
# CVE-YYYY-NNNN: short title

## Description

## Overview

- Affected software:
- Impact:
- Vulnerable versions:
- Fixed versions:
- Disclosure date:

## Reproduction design

Explain the VM topology, package-version strategy, and why the chosen generator
fits this CVE.

## Exploit provenance

- Advisory:
- Patch or fixing commit:
- Exploit source:
- Local changes made for this VM:
- Safety limits or simplifications:

## Manual reproduction

Use the scenario helper with SSH or popup VM windows where possible:

```bash
nice-archive scenario --case cve-yyyy-nnnn-short-name --vulnerable true --popup false
```

Then SSH into the printed VM command and run the exploit trigger directly
inside the VM.

If the case uses standalone VMs, show each terminal and port-forwarding step
needed to wire the machines together.

Expected vulnerable result:

Expected fixed result:

## Running automated tests

Show the `nice-archive test` commands for vulnerable and fixed variants.

## Automated oracle

The machine-checkable reproduction is implemented in `test.py`. Summarize the
assertion blocks used there and what security property each one proves.

## Interactive debugging

## Assertions

## References
````

Include exact commands that were verified. Prefer CLI commands first, because
the CLI knows the modern output naming convention and legacy fallback.

Avoid making human reproduction depend on the test-driver Python prompt unless
there is no practical alternative. Prefer scenario SSH or standalone VM shell
commands for README instructions.

## 14. LLM failure modes to avoid

- Do not build vulnerable software from source before checking nixpkgs history.
- Do not skip manual reproduction in a VM.
- Do not use only the test-driver prompt when SSH or popup VM windows are
  available.
- Do not finish `test.py` with only raw Python `assert` statements when an
  assertion block fits.
- Do not check only that an exploit command exits; check the security effect.
- Do not omit exploit provenance.
- Do not leave the case README without human manual reproduction commands.
- Do not bury the automated oracle; point readers to `test.py`.

## 15. Final checklist

Before considering the report done:

- [ ] The vulnerable test demonstrates the exploit or vulnerable behavior.
- [ ] The fixed test demonstrates mitigation or absence of the vulnerable effect.
- [ ] The assertion checks the security property, not just command completion.
- [ ] `test.py` ends with framework assertion blocks where helpers fit.
- [ ] nixpkgs history was checked before building vulnerable software from source.
- [ ] Existing nixpkgs packages are used when suitable versions exist.
- [ ] Exploit provenance is documented.
- [ ] `flake.nix` uses the appropriate generator.
- [ ] VM names are clear and match variables in `test.py`.
- [ ] Any graphical test sets `isGraphics = true` and `enableOCR = true`.
- [ ] The README explains why the chosen generator fits the age and shape of the vulnerability.
- [ ] Manual reproduction steps use scenario SSH, popup VMs, or standalone VMs.
- [ ] Any old-kernel test uses `oldKernelTestsGenerator` unless it needs custom low-level behavior.
- [ ] The case README explains the topology, exploit, assertions, and commands.
- [ ] The case README points to `test.py` as the automated oracle.
- [ ] Generated logs, `result` symlinks, `.qcow2` files, and `.nixos-test-history` are not accidentally committed.

## 16. References

- [NixOS/nixpkgs#47684](https://github.com/NixOS/nixpkgs/pull/47684)
- [NixOS/nixpkgs#225313](https://github.com/NixOS/nixpkgs/pull/225313)
- [NixOS Wiki: Flakes](https://nixos.wiki/wiki/Flakes)

## 17. Handoff note template (for LLM agents)

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
