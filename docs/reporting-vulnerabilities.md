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

1. Record the user shell and command-runner shell separately, plus UTC start
   time, model, harness, and which usage metadata the runtime exposes.
2. Do read-only discovery first and search for an existing matching case.
3. Create a dedicated working directory for this CVE before
   implementation, unless the user explicitly asks to do otherwise. 
4. Identify vulnerable and fixed versions.
5. Record exploit provenance before copying or adapting exploit code.
6. Search nixpkgs history before building vulnerable software from source.
7. Design the VM topology and target-unique oracle markers.
8. Decide which NICE Archive library generator fits.
9. Implement the Nix files.
10. Start the VM scenario with a scenario subagent only when the capability
    gate passes; otherwise, the main agent owns the managed scenario. Use
    standalone VMs only when scenario mode is unavailable or inappropriate.
11. Use VM-operator subagents with SSH, popup VM windows, or the test-driver
    shell for manual reproduction.
12. Translate the successful manual workflow into `test.py`.
13. End the automated test with suitable `assertion_blocks` helpers.
14. Run vulnerable and fixed tests with finite timeouts, preferably through
    test-runner subagents while the main agent monitors progress.
15. Update the case README with verified commands, assertions, and LLM
    reproduction metadata.
16. Report exactly what changed and what was verified.

## LLM reproduction contract

When using this framework, an LLM agent should treat the following as hard
requirements:

- Prefer existing nixpkgs packages and historical nixpkgs revisions over
  building vulnerable software from source.
- Use `nix-versions` or Nixpkgs history before deciding that a source build is
  necessary.
- Create one dedicated Git branch per CVE case before implementation, and do
  not combine unrelated CVE work on one branch.
- Treat shell detection as a pre-execution gate. Do not run shell-dependent or
  compound commands until the command runner's interpreter is known.
- Give every command-execution call a finite deadline and never wait
  indefinitely for a prompt or a command that stopped making progress.
- Never execute vulnerable software, PoCs, malicious inputs, or exploit
  triggers in the coding-agent session or directly on the host.
- Establish and state a suitable VM or container boundary before running a
  trigger. Do not fall back to host execution if isolation fails.
- Follow existing case style before inventing a new structure. Heartbleed is a
  good model for historical user-space packages.
- Use the scenario helper plus SSH for manual validation when possible.
- When the subagent capability gate passes, use a scenario subagent to keep
  scenario mode running and VM-operator subagents to SSH into generated VMs and
  simulate the exploit from inside the lab. Otherwise, the main agent owns the
  managed scenario.
- Use standalone VMs for manual validation when the NixOS test driver is not a
  good fit.
- Do not stop after Nix files evaluate; manually reproduce the exploit in a VM.
- Reuse and adapt an existing PoC when available. If none exists, derive a
  minimal trigger from authoritative CVE material instead of inventing an
  independent exploit from scratch.
- Convert the manual workflow into `test.py`.
- Plant target-unique flags, credentials, users, tokens, or records for the
  oracle.
- End `test.py` with framework assertion blocks whenever one fits.
- Bound VM waits, network operations, exploit processes, and fixed-variant
  checks with finite timeouts.
- Add exploit provenance and human manual reproduction commands to the CVE
  README.
- Point readers to `test.py` as the machine-checkable oracle.
- Record model, harness, shell, elapsed time, token usage, and cost in the case
  README. Use `not available (not exposed by harness)` rather than estimating
  values the runtime does not expose; unavailable telemetry is not a blocker.

### Shell execution gate

The user's interactive shell and the interpreter used by an agent's command
tool may differ. Record both. Environment or tool metadata is authoritative for
the command runner; `$SHELL` commonly reports the login shell and does not prove
which interpreter will parse a command.

Until the runner is known, use only direct, non-interactive, single-program
invocations. Avoid pipelines, control operators, redirection, heredocs,
substitution, variables, globs, aliases, and functions. Once known, use syntax
for that interpreter or select one explicitly without startup files, such as
`bash --noprofile --norc -c`, `zsh -f -c`, or `fish --no-config -c`.

Do not launch interactive or login shells for automation, source user startup
files, or wait for a shell prompt. A script must declare and use its intended
interpreter. Human reproduction commands must match the recorded user shell or
name the interpreter explicitly.

Use `expect`/`pexpect` when the workflow genuinely requires a TTY or
human-style prompt interaction.

Every command tool call needs a finite deadline. Long-lived VM scenarios need
a managed session, bounded readiness checks, and explicit termination. If a
command unexpectedly requests input or stops progressing, terminate it at the
deadline and diagnose the shell or invocation.

Enforce these hard wall-clock limits from process launch:

| Activity | Maximum runtime |
| --- | --- |
| Ordinary command | 5 minutes |
| VM or service readiness | 5 minutes |
| Complete NixOS test, including build and execution | 30 minutes |
| Complete interactive scenario, including startup, validation, and cleanup | 45 minutes |

Set both the command tool deadline and a process-level watchdog where
available. Do not extend a running deadline or restart merely to reset it.
Timeout status `124`, forced termination, or expiration of any limit is a
failure or blocker, not a passing fixed result.

Poll managed sessions at least every two minutes. Track meaningful new output
or a successful bounded VM/test-driver response. If neither occurs for five
continuous minutes, terminate the command even when its overall hard limit has
not expired. Enforce the inactivity cutoff independently: poll at or before two
and four minutes, then check at five minutes rather than waiting for a
six-minute poll. Repeated identical output and mere process existence are not
progress.

### Subagent orchestration

When an LLM agent has a subagent facility, use it to split long-running VM
operations from orchestration. Subagents are execution helpers; the main agent
still owns research, safety decisions, the watchdog, test termination
decisions, documentation, and final claims.

Subagent availability alone is insufficient. A subagent may own a scenario or
test only when it immediately returns a detached session handle that the main
agent can poll and terminate independently. If the call is synchronous,
non-cancellable, or hides the process handle, the main agent must own the
managed command. Use subagents only for bounded finite work in that mode; never
block the main agent waiting for a subagent whose scenario requires manual
termination.

For manual validation, use this pattern when practical:

1. Start `nice-archive scenario --case <case> --vulnerable <true|false>
   --popup false` in a dedicated scenario subagent. The subagent should keep
   the scenario running as a managed session, capture the printed SSH commands,
   and report readiness plus new output. Apply the 45-minute process-level
   deadline from launch.
2. Spawn one or more VM-operator subagents to connect with the printed SSH
   commands. They should run bounded guest-side health checks, execute the
   trigger inside the VM, collect logs and oracle evidence, and report exact
   commands and outputs.
3. Keep the main agent as the orchestrator. It decides what each VM operator
   should try next, compares vulnerable and fixed observations, tracks the
   watchdog, and tells the scenario subagent when to terminate the VMs.

Attempt scenario mode before falling back to standalone VMs unless the case
does not expose interactive scenarios or the target is known to require
standalone VMs. VM-operator subagents must use only guest fixtures and must
never target host `localhost`, unrelated local services, or public systems.

For automated validation, spawn a test-runner subagent for each long-running
`nice-archive test` command only when the capability gate passes. The subagent
reports progress from the managed test session, but the main agent decides
whether the test is stuck under the two-minute polling and five-minute
inactivity watchdog. If the watchdog fires, the main agent instructs the
subagent to interrupt or terminate the test, or terminates the managed session
itself. Otherwise, the main agent owns the managed test command. Apply the
30-minute process-level deadline from launch.

### Isolation gate

The repository development shell and coding-agent session are part of the host,
not part of the vulnerability lab. Host work is limited to source review, file
editing, safe metadata queries, sandboxed Nix builds, and starting or
controlling isolated environments.

Before executing target software, a PoC, malformed input, crash test, or
resource-exhaustion trigger, state the selected boundary and confirm the
command runs inside it. Prefer NixOS test or standalone VMs. Containers are
appropriate only for user-space flaws that cannot affect the host kernel,
container runtime, devices, or host privileges. Kernel bugs, local privilege
escalation, system services, destructive tests, resource exhaustion, and
uncertain PoCs require a VM.

`nix-shell` and `nix develop` isolate dependencies but are not security
boundaries. They can build or launch a lab; they do not make host execution of
a vulnerable program or PoC safe. Use test-driver machine methods, SSH into a
generated VM, or an explicit container execution command. Restrict networking
and mounts, use guest-only fixtures, and never target host `localhost`. If the
lab cannot start, report the blocker instead of falling back to the host.

## 1. Create a case directory

Before implementation, create a dedicated working directory for the CVE case. The default location is under `cves/` with a name that follows the convention:

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

### Unique markers and lab credentials

Design the oracle around evidence that is unique to this target VM and this
CVE case.

Good marker patterns include:

- a flag file with a case-specific value, such as
  `NICE-CVE-YYYY-NNNN-SERVER-FLAG`;
- a special target-only user with a flag-style GECOS field, password, or home
  directory marker;
- a footprint left by the attacker, e.g., a file, a line in root-owned files (`/etc/passwd`), a newly created root-owned account, etc., that will be asserted on by the victim machine after the exploit runs;
- an admin account whose username and password are unique to the case and can
  later be used by the attacker to prove credential disclosure;
- a database row, API token, email, session cookie, or service-side secret that
  was intentionally planted from the start of the VM and can be used to prove disclosure; or
- a root-owned marker file or account created only when a privilege boundary is
  crossed.

Keep these markers deterministic and guest-only. They are test fixtures, not
real secrets. Document where each marker is planted, why it proves the security
property, and how the fixed branch proves the marker is absent while the target
stays healthy.

### Exploit provenance

Before integrating exploit code, record where it came from and how it was
changed:

- original advisory URL;
- upstream patch or commit, if known;
- exploit source URL, if copied or adapted;
- whether the exploit was copied, modified, simplified, rewritten in place, or
  used as the basis for a new recipe-local `exploit/<helper>`;
- why any changes were needed for the NixOS VM environment; and
- any safety limits added for automated testing.

This information belongs in the CVE README, not only in code comments.

Keep final exploit code under the case's `exploit/` directory. Reuse a supplied
or public PoC whenever one is available. It is fine to modify, simplify, wrap,
or rewrite that PoC when the original does not fit the VM environment or test
oracle, provided the source and changes are documented.

If no suitable PoC is available, derive a minimal trigger directly from the
CVE description, upstream advisory, fixing patch, or regression test. Do not
invent a new exploit technique or write an unrelated PoC from scratch. Record
the authoritative artifact from which the local helper was derived and make VM
modules reference the final recipe-local path, such as
`./exploit/trigger.py`.

The exploit source code should only handle practical or realistic inputs. Branching for tests should be avoided; test logic belongs in `test.py` instead. For example, if the exploit is expected to crash or fail on a fixed version, the exploit should not catch the crash and print "failed" or "success"; that must be handled by the test script.

Keep exploit workflows easy to inspect. When the exploit steps are small enough
to resemble what a human would run manually, prefer small single-purpose
helpers under `exploit/`, or simple commands directly in `test.py`, over one
large "do everything" script. Use a larger script when the task is genuinely
heavy, such as authentication request/response flows, input processing,
protocol setup, or other complex mechanics.

The README manual reproduction should mirror the same human-readable sequence.
`test.py` should orchestrate the sequence and own vulnerable/fixed expectations
and pass/fail decisions.

### Package source strategy

Before building vulnerable software from source, check whether nixpkgs already
contains the vulnerable and fixed versions. Prefer
[nixpkgs-multiverse](https://github.com/fzakaria/nixpkgs-multiverse), then use
`nix-versions` as a fallback. Multiverse can query its index by exact version,
date, release tag, or commit without first evaluating every nixpkgs revision:

```bash
# Exact version and its revision range.
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query when curl 7.83.0

# Package version at a date, and release-tag provenance.
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query at 2022-03-15 python3
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query rev 24.11

# Nested Python and kernel package sets at immutable revision labels.
nix eval --raw 'github:fzakaria/nixpkgs-multiverse#2018-01-01-f59a0f7f1a6d.python3Packages.requests.version'
nix eval --raw 'github:fzakaria/nixpkgs-multiverse#2022-03-14-73ad5f9e147c.linuxPackages.kernel.version'

# Fallback search using nix-versions.
nix-versions 'bin/curl@7.83'
```

The multiverse index covers top-level attributes. Select a revision before
evaluating nested sets such as `python3Packages` or `linuxPackages`. Release
tags move as backports arrive, so record and pin the resolved full commit in a
case. If multiverse has no suitable result, `nix-versions` searches these
sources:

- [Nixpkgs History](https://history.nix-packages.com)
- [NixHub](https://nixhub.io)
- [Lazamar](https://lazamar.co.uk/nix-versions/)

See the multiverse [Nix API](https://github.com/fzakaria/nixpkgs-multiverse/blob/main/docs/nix-api.md)
and [`mvs` CLI](https://github.com/fzakaria/nixpkgs-multiverse/blob/main/docs/cli.md),
or run `nix-versions --help` for fallback usage.

The vulnerable package can be any version that authoritative evidence confirms
is affected; it does not have to be the last affected release. When several
affected versions are viable, select one already present in nixpkgs and
compatible with package-level pinning. Do not build a specific boundary release
from source merely because it is the newest affected version.

Never copy, transcribe, extract, vendor, or reconstruct affected-product source
into the case directory. This includes full source snapshots, individual
upstream source files, copied functions, and reduced local reimplementations of
the vulnerable code. Obtain the target from an immutable nixpkgs revision or
make Nix fetch a complete, hash-verified release, tag, or commit from the
original upstream project and build it in the sandbox. Nix may unpack that
fetched source during the build. Case-owned Nix expressions, VM configuration,
wrappers, tests, and exploit/trigger code remain appropriate. Fetch any needed
upstream or nixpkgs target patch by immutable URL and verified hash rather than
copying its source hunks into the case.

Use this priority order:

1. Use existing vulnerable and fixed packages from historical nixpkgs
   revisions with `variant = "package"`. Keep the surrounding NixOS system on
   the current pin and select the historical package inside the target VM
   configuration, for example:

```nix
let 
  opensslTarballInfo = if isVulnerable then 
  {
    # 1.0.1f - vulnerable
    url = "https://github.com/NixOS/nixpkgs/archive/ab6453c483e406b07c63503bca5038838c187ecf.tar.gz";
    sha256 = "sha256:0zfkymyg0l5ihnyj1nlm14fs7z109ah6hbid7l0i3f0g80s1pbq2";
  } else 
  {
    # 1.0.1g - not vulnerable
    url = "https://github.com/NixOS/nixpkgs/archive/caa9007e847102d013203b547d1ce67bcd77e89a.tar.gz";
    sha256 = "sha256:0byrsw6pmqci2vb6b98w02vpc8k09kj4xl2qlm3myxfsyxpq553r";
  };

  opensslPkgs = (import (builtins.fetchTarball {
    url = opensslTarballInfo.url;
    sha256 = opensslTarballInfo.sha256;
  }) { system = "x86_64-linux"; }).openssl;
in
{
  environment.systemPackages = with pkgs; [
    opensslPkgs
  ];
}
```
The commit hashes found through nixpkgs history can be used to update the `url`
line in the example. Calculate the archive hash with
`nix-prefetch-url <url> --unpack`; alternatively, use the expected hash printed
by a failed Nix build and then rerun with the verified value. See
[Heartbleed](../cves/cve-2014-0160-heartbleed/) for a working example.

2. If package-level pinning cannot represent a system component or its tightly
   coupled dependencies, pin the whole target VM with `variant = "system"`.
   See [chwoot](../cves/cve-2025-32463-chwoot/) for a working example.
3. If whole-system pinning cannot provide the necessary old kernel or old NixOS
   environment while retaining a modern test driver, use
   `oldKernelTestsGenerator`. Use `oldKernelNixosTest` only for required custom
   low-level behavior.
4. Only if no suitable vulnerable or fixed package is available through the
   applicable nixpkgs strategies above, define a package or use `overrideAttrs`
   to fetch and build the complete original upstream source. See
   [CVE-2013-0249](../cves/cve-2013-0249-curl-sasl-buffer-overflow/) for a
   source-build example.

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

Choose the minimum realistic topology. Preserve every service, network,
privilege, and trust boundary that is a precondition of the vulnerability, but
do not add machines that have no independent role.

- Run a required intermediary on its own VM when it represents a distinct
  deployment role. A reverse proxy, gateway, or load balancer should be on a
  proxy VM separate from the backend server.
- Apply the same separation to required mail relays, databases, identity
  providers, DNS servers, file servers, and protocol intermediaries when the
  exploit depends on traffic or trust crossing that boundary.
- Co-locate services only when that is a realistic deployment and separation
  cannot change the security behavior. Explain intentional co-location.
- Every VM must have a stated role. Removing one should either violate a
  documented precondition or reduce isolation; otherwise, omit it.
- Keep invariant infrastructure and communication paths identical in the
  vulnerable and fixed scenarios.

Document the path through the topology, for example
`attacker -> proxy -> backend`, and state what security-relevant processing
occurs at each boundary.

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

### Example: Server VM pattern

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

### Example: Attacker VM pattern

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

#### Important notes:

- Keep the exploit code under `./exploit/` in the case directory.
- If PoC code is copied or adapted, reference the original source using comments and the recipe README.
- Note that the file path system of NixOS is not the same as a conventional Linux FHS. Packages are installed in the Nix store, and `/bin`, `/usr/bin`, and `/usr/local/bin` may not exist or may not contain the expected binaries. If these binaries are installed, there will be symlinks to the Nix store paths from `/run/current-system/sw/bin/`. So if you need to run a binary from a package, use the Nix store path or the symlink in `/run/current-system/sw/bin/` instead of assuming it is in `/bin` or `/usr/bin`. See [CVE-2020-7247](../cves/cve-2020-7247-opensmtpd/exploit) for an example of a case that uses the symlink path to run a binary (`touch`).

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
attacker.succeed("timeout 30s run-exploit http://server:8080")

ab.check_file_contains(attacker, "/tmp/result.txt", "Pwned!")
```

The end of the test should be the machine-checkable oracle. Prefer the
framework's assertion blocks for that oracle:

- use raw `assert` only for control flow, variant checks, or values that do not
  fit an assertion helper;
- assert target-unique marker evidence, not generic machine behavior. For
  example, a path traversal that reads `/etc/passwd` should check for a
  case-specific target user or marker line instead of only `root:`;
- cross-check evidence at the boundary where the security effect occurs. For
  RCE against a server, check the unauthorized file, process, user, log, or
  privilege change on the server. For data theft from a server, compare the
  attacker's output with the original target-only value planted on the server;
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

Some important points:
- The test is also a list of steps for a human to reproduce the exploit manually. Keep the test
  readable and understandable, don't use overly complex Python constructs.
- The test should handle both vulnerable and fixed variants.

### Bound waits and blocking triggers

Every wait, polling loop, network operation, and trigger that may block must
have a finite deadline. Fixed variants need particular care: an exploit that
hangs after the fix is not by itself proof that the vulnerability is blocked.

Use explicit test-driver timeouts where supported and wrap potentially hanging
guest commands with `timeout`:

```python
server.wait_for_unit("vulnerable-service.service", timeout=120)
server.wait_for_open_port(8080, timeout=60)

status, output = attacker.execute(
    "timeout --signal=TERM 30s run-exploit http://server:8080"
)
assert status != 124, f"exploit timed out instead of producing a result: {output}"
```

Also set connect and read timeouts inside network PoCs. Bound custom retry loops
by elapsed time or attempt count. VM and service readiness must fail after five
minutes. Complete CLI-driven NixOS tests, including initial downloads and
builds, must fail after 30 minutes. Interactive scenarios must terminate after
45 minutes. The two-minute polling and five-minute inactivity cutoff still
apply and may terminate an operation earlier. On timeout, collect diagnostics
and fail clearly; never count a timeout alone as a passing fixed result.

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

Use the NICE Archive CLI whenever it supports the operation. Use it for case
discovery, flake updates, scenarios, standalone VMs, and vulnerable/fixed
tests. Do not replace supported CLI operations with guessed flake attributes,
direct QEMU commands, or ad hoc containers.

Run CLI commands from the repository root. Outside the development shell, use
`nix run . --` followed by the same NICE Archive arguments. Direct `nix build`,
`nix run`, or `nix eval` is allowed only when no CLI operation fits or when
diagnosing a CLI/generated-output failure. Record the reason and perform final
vulnerable/fixed validation through `nice-archive test`.

List cases:

```bash
nice-archive list-cves
```

Run vulnerable and fixed tests:

```bash
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable true
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable false
```

For LLM agents, use a test-runner subagent only when it returns a detached,
cancellable session handle. Otherwise, the main agent must own the managed
test command. Poll at least every two minutes, apply the five-minute inactivity
cutoff, and enforce the 30-minute total test limit.

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

For LLM agents with subagents, run terminal 1 in a scenario subagent and use
VM-operator subagents for terminal 2 and any additional attacker, client, or
server sessions. The main agent should keep the printed SSH commands, decide
which VM each operator should enter, compare the evidence they report, and
terminate the scenario after both vulnerable and fixed observations are
recorded.

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

Each CVE README must be compact and understandable without reading the
implementation. Existing cases may guide implementation, but the resulting
README must not name, cite, compare itself with, or claim to be modeled after
another CVE case. Describe the case using its own evidence and authoritative
external sources.

Use this required structure and section order:

````markdown
# CVE-YYYY-NNNN: short title

## Summary

| Field | Value |
| --- | --- |
| CVE | `CVE-YYYY-NNNN` |
| Software | `<name>` |
| Vulnerable version | `<version or commit>` |
| Fixed version | `<version or commit>` |
| Vulnerability class | `<class or CWE>` |
| Preconditions | `<required configuration or access>` |
| Impact | `<security effect>` |

## Root cause

At most two short paragraphs describing the flawed behavior and the fix.

## Reproduction

| Field | Value |
| --- | --- |
| Generator | `<NICE Archive generator>` |
| Topology | `<each VM, service role, and communication path>` |
| Package selection | `<pins and variants>` |
| Trigger | `<PoC or regression trigger>` |
| Target marker | `<target-unique guest evidence>` |
| Oracle | `<assertion and security property>` |

## Run and results

```text
<verified manual command>
<vulnerable automated test command>
<fixed automated test command>
```

| Variant | Expected | Observed | Status |
| --- | --- | --- | --- |
| Vulnerable | `<effect>` | `<actual observation>` | `<pass/fail/not run>` |
| Fixed | `<effect absent and service healthy>` | `<actual observation>` | `<pass/fail/not run>` |

## Provenance

| Item | Source or local change |
| --- | --- |
| Advisory | `<URL>` |
| Fix or patch | `<URL/commit>` |
| Release notes | `<URL>` |
| PoC or regression test | `<URL and author>` |
| Local modifications | `<concise changes>` |
| Nixpkgs sources | `<revisions and package versions>` |

## Limitations and safety

- `<verified limitation, safety boundary, or None known>`

## Reproduction metadata

| Field | Value |
| --- | --- |
| Reproduced by | LLM agent |
| Model | `<runtime value or not available with reason>` |
| Agent/harness | `<tool and version or not available with reason>` |
| Date | `<YYYY-MM-DD>` |
| Command shell | `<bash, zsh, fish, or other>` |
| Start time | `<UTC timestamp or not available with reason>` |
| End time | `<UTC timestamp or not available with reason>` |
| Elapsed time | `<measured duration or not available with reason>` |
| Input tokens | `<runtime value or not available with reason>` |
| Output tokens | `<runtime value or not available with reason>` |
| Total tokens | `<runtime value or not available with reason>` |
| Cost | `<platform value, sourced estimate, or not available with reason>` |
| Telemetry source | `<runtime, UI, user-provided, calculated, or not exposed>` |

## References
````

Keep the strict form compact:

- use one table for summary, reproduction, results, provenance, and metadata;
- keep root cause to two short paragraphs;
- include commands once and include only commands actually verified, marking
  unexecuted commands as `not run`;
- use `None known` instead of filler when no limitation is known;
- deduplicate references and include only sources directly relevant to this
  CVE;
- do not add separate `Description`, `Overview`, `Assertions`, or `Interactive
  debugging` sections when the required tables already contain that material;
- do not include comparisons, implementation ancestry, or links to other CVE
  example cases.

Include exact commands that were verified. Prefer CLI commands first, because
the CLI knows the modern output naming convention and legacy fallback.

Avoid making human reproduction depend on the test-driver Python prompt unless
there is no practical alternative. Prefer scenario SSH or standalone VM shell
commands for README instructions.

Complete `Reproduction metadata` after validation. It must state that the case
was reproduced by an LLM agent and identify the exact model and harness when
the runtime exposes them. Record start and end timestamps so elapsed time is
measured rather than guessed.

Token counts and cost often are not visible to the agent. Use `not available`
with a reason such as `not exposed by harness` for unavailable fields. IDE chat
integrations, including some GitHub Copilot Chat configurations, may identify
the harness but expose no exact model, per-task token counts, or billing data to
the agent. Missing telemetry does not block completion.

Never infer tokens from context size or text length. A subscription price is
not a per-run cost. If cost is calculated from known token counts, label it as
an estimate and cite the model pricing source, currency, and pricing date. Do
not inspect hidden files, query unrelated services, or fabricate metadata to
make the section look complete.

## 14. LLM failure modes to avoid

- Do not build vulnerable software from source before checking nixpkgs history.
- Do not invent an independent PoC when supplied, public, or upstream trigger
  material can be reused or adapted.
- Do not skip manual reproduction in a VM.
- Do not use only the test-driver prompt when SSH or popup VM windows are
  available.
- Do not finish `test.py` with only raw Python `assert` statements when an
  assertion block fits.
- Do not check only that an exploit command exits; check the security effect.
- Do not assert only generic OS or service behavior. Plant and check a
  target-unique flag, credential, user, token, or record.
- Do not hide simple exploit workflows inside one large script when small
  helpers or `test.py` commands would make the manual sequence clearer.
- Do not put vulnerable/fixed expectations or the final oracle inside exploit
  scripts.
- Do not rely only on attacker-side output for effects that should be visible
  on the target VM.
- Do not omit exploit provenance.
- Do not leave the case README without human manual reproduction commands.
- Do not bury the automated oracle; point readers to `test.py`.
- Do not leave waits, network calls, exploit processes, or fixed checks
  unbounded.
- Do not guess the model, tokens, cost, shell, or elapsed time in reproduction
  metadata.

## 15. Final checklist

Before considering the report done:

- [ ] The vulnerable test demonstrates the exploit or vulnerable behavior.
- [ ] The fixed test demonstrates mitigation or absence of the vulnerable effect.
- [ ] The assertion checks the security property, not just command completion.
- [ ] The oracle uses target-unique guest markers rather than only generic
      machine behavior.
- [ ] Multi-VM oracles cross-check attacker output against the original
      target-side marker or check the unauthorized effect on the target VM.
- [ ] Simple exploit workflows are split into clear helper commands or
      `test.py` steps; complex scripts are used only where they make the
      exploit mechanics clearer.
- [ ] `test.py` ends with framework assertion blocks where helpers fit.
- [ ] nixpkgs history was checked before building vulnerable software from source.
- [ ] Existing nixpkgs packages are used when suitable versions exist.
- [ ] The chosen vulnerable version is proven affected; it is not required to
      be the last affected version.
- [ ] Package pinning was preferred over whole-system pinning, and
      whole-system pinning was preferred over old-kernel support when each
      earlier option could faithfully represent the target.
- [ ] No affected-product source files, functions, snippets, or reduced
      reimplementations are stored in the case; source-build fallbacks fetch
      complete hash-verified original upstream source through Nix.
- [ ] Exploit provenance is documented.
- [ ] Existing PoC or regression-test material was reused or adapted when
      available; any derived trigger cites its authoritative basis.
- [ ] `flake.nix` uses the appropriate generator.
- [ ] VM names are clear and match variables in `test.py`.
- [ ] The topology is the minimum realistic model: required service and trust
      boundaries use separate VMs, while unnecessary helper VMs are omitted.
- [ ] Required intermediaries such as proxies are not co-located with the
      backend unless that deployment is realistic and the choice is explained.
- [ ] Any graphical test sets `isGraphics = true` and `enableOCR = true`.
- [ ] The README explains why the chosen generator fits the age and shape of the vulnerability.
- [ ] Manual reproduction steps use scenario SSH, popup VMs, or standalone VMs.
- [ ] Any old-kernel test uses `oldKernelTestsGenerator` unless it needs custom low-level behavior.
- [ ] The case README explains the topology, exploit, assertions, and commands.
- [ ] The case README points to `test.py` as the automated oracle.
- [ ] The case README follows the required compact section order without
      duplicate sections or unnecessary implementation narrative.
- [ ] The case README does not name, cite, or compare itself with another CVE
      example case.
- [ ] Each CVE is isolated on its own working directory.
- [ ] Potentially blocking operations and fixed-variant checks have finite
      timeouts.
- [ ] Ordinary commands, readiness checks, complete tests, and scenarios obey
      the 5/5/30/45-minute hard limits.
- [ ] Managed sessions are polled at least every two minutes and terminated
      after five minutes without meaningful output or a bounded response.
- [ ] Final scenarios, standalone VMs, flake updates, and vulnerable/fixed
      tests use the NICE Archive CLI whenever it supports the operation.
- [ ] A subagent owns a long-running process only when the main agent receives
      a detached session handle it can poll and terminate independently.
- [ ] The case README contains LLM model, harness, shell, elapsed time, token,
      and cost metadata, using `not available` with a reason for unexposed
      values.
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
