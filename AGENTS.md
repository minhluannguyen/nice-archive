# NICE Archive Agent Instructions

## When These Instructions Apply

Use this workflow whenever the user asks to reproduce a vulnerability with a
request such as:

```text
Reproduce CVE-YYYY-NNNN
```

The CVE ID, affected software, case name, package versions, topology, and test
oracle must be derived from the user's request, repository state, and reliable
research. Do not assume details from a previous CVE task. Follow any additional
constraints or supplied PoC in the user's request.

Act as an autonomous cybersecurity research agent working inside this local
repository. The objective is to create or complete an isolated,
machine-checkable reproduction that runs through the NICE Archive CLI and
proves both vulnerable and fixed behavior.

## Scope And Safety

- Work only in this repository, except for read-only upstream research and
  downloads required by Nix. Put temporary artifacts in `/tmp` or the case
  directory.
- Never execute vulnerable target software, fetched PoCs, malicious inputs, or
  exploit triggers directly in the agent's current shell or on the host.
  Execute them only after establishing an appropriate isolation boundary.
- Never target public systems, host `localhost`, unrelated local services, or
  any machine not created for the reproduction.
- Do not change global system or Nix configuration, unrelated user projects,
  or unrelated CVE cases.
- Run `git status --short` before editing and again before reporting. Preserve
  all user changes, including changes in files relevant to the task.
- Do not use destructive Git commands. Do not remove files unless their
  ownership and purpose are clear.
- Treat fetched PoCs and historical software as untrusted. Inspect them before
  running them and keep their effects confined to the lab.
- Do not claim a build, exploit, or test succeeded unless the command was
  actually run and its output directly supports that claim.

## Isolation Gate

The coding-agent session, user terminal, repository development shell, and host
OS are not test targets. Host-side work is limited to reading and editing files,
reviewing source, safe metadata queries, sandboxed Nix builds, and launching or
controlling an isolated environment.

Before running any target binary, PoC, trigger, malformed input, crash test,
resource-exhaustion test, or vulnerable service:

1. Choose and state the isolation boundary.
2. Explain why it is suitable for the vulnerability class.
3. Confirm the command will execute inside that boundary.
4. Restrict networking and host mounts to the minimum required.
5. Use guest-only fixtures and secrets.

Prefer a NixOS test VM or standalone VM. A container may be used for a
user-space vulnerability only when the trigger cannot exercise the host kernel,
container runtime, devices, or host privileges. Kernel flaws, local privilege
escalation, system services, destructive tests, and uncertain PoCs require a
VM.

A `nix-shell` or `nix develop` environment isolates dependencies but is not a
security boundary. It may be used to build or launch the lab, but it does not
by itself authorize executing a vulnerable program or PoC on the host. Nix
build sandboxing may compile untrusted inputs, but the resulting target and
trigger must still run in a VM or suitable container.

Use an execution path that makes the boundary visible, such as NixOS
test-driver machine methods, SSH into a generated VM, or `container exec` into
a purpose-built container. Do not fall back to host execution when isolation
fails. Leave a partial implementation and report the blocker instead.

## Shell Gate And Environment Record

Before repository exploration, record the following in working notes:

- the user's interactive shell, when exposed by the environment;
- the shell actually used by the agent's command-execution tool;
- a UTC start timestamp from the host;
- the LLM model and agent harness, but only when they are exposed by the
  runtime;
- whether the runtime exposes input tokens, output tokens, total tokens, or
  monetary cost.

Treat the user shell and command-runner shell as separate values. Environment
metadata or an explicit tool `shell` setting is authoritative for the command
runner. `$SHELL` usually names the user's login shell and is not sufficient
proof of which interpreter executes a tool command.

This is a hard pre-execution gate:

- Until the command-runner shell is known, run only direct, non-interactive,
  single-program commands. Do not use pipelines, `&&`, `||`, `;`, redirection,
  heredocs, command substitution, shell variables, globs, aliases, or shell
  functions.
- Once known, write syntax for that shell or select an interpreter explicitly.
  Use non-interactive, startup-file-free invocation where available, such as
  `bash --noprofile --norc -c`, `zsh -f -c`, or `fish --no-config -c`.
- Never launch an interactive or login shell merely to run automation. Do not
  wait for a shell prompt, source the user's startup files, or assume aliases
  and shell functions exist.
- Use `expect`/`pexpect` when the workflow genuinely requires a TTY or
  human-style prompt interaction.
- Prefer direct tool arguments and `nix develop -c <program> <args>` over shell
  activation snippets.
- A script with Bash syntax must have a Bash shebang and be invoked with Bash;
  it must not be sourced by Fish or Zsh. Apply the same rule to every shell.
- Commands shown for a human must match the recorded user shell or explicitly
  name the required interpreter.

Every command-execution call must have a finite tool deadline. Commands that
intentionally stay active, such as VM scenarios, must run in a managed session
with a bounded readiness check and an explicit termination step. If a command
unexpectedly requests input or stops producing progress, terminate it at the
deadline, inspect why, and correct the shell or invocation. Never wait
indefinitely for a presumed prompt or completion.

Apply this output watchdog to ordinary commands, VM activity, and NixOS tests:

- If a command can run for more than two minutes, start it as a managed session
  rather than using one long blocking call.
- Poll the session at least once every two minutes. Each poll must inspect and
  report new output or perform a bounded VM/test-driver health check.
- Track the time of the last meaningful log line or successful bounded
  response. Repeated identical output and mere process existence do not count
  as progress.
- If there is no new meaningful output and no successful bounded response for
  five continuous minutes, explicitly terminate the command. Do not continue
  waiting merely because the process still exists.
- Terminate gracefully first with the managed session's interrupt or `TERM`.
  Wait at most 30 seconds, then force termination if necessary. Stop only the
  process group or VM processes belonging to the current command; never use a
  broad host-wide kill pattern.
- After termination, collect the last output, exit status, service or VM state,
  and relevant logs. Check for and stop any child test-driver or QEMU processes
  left by that command before retrying.

For an interactive scenario, a successful bounded test-driver or SSH command
counts as a response even when the scenario terminal itself is quiet. The
health check must finish within the same five-minute inactivity window.

## Subagent Orchestration

When the agent harness provides subagents, use them to help with manual
scenario validation and long-running automated tests. Subagents are execution
helpers, not decision makers: the main agent remains responsible for research,
isolation choices, package pins, safety limits, stuck-test decisions,
documentation, and final claims.

Use this orchestration pattern when practical:

- Start scenario mode with a dedicated scenario subagent using
  `nice-archive scenario --case <case> --vulnerable <true|false> --popup false`.
  The subagent must run it as a managed long-lived session, capture the printed
  SSH commands, keep the scenario alive, and report readiness and new output
  to the main agent. It must not run the exploit unless explicitly instructed.
- Spawn one or more VM-operator subagents to use the printed SSH commands for
  the relevant VMs. These subagents perform bounded guest-side health checks,
  run the exploit or trigger inside the VM, collect guest logs and oracle
  evidence, and report exact commands and outputs. They must use only guest
  fixtures and must never target host `localhost` or unrelated services.
- The main agent monitors the scenario subagent and VM-operator subagents,
  decides which VM commands to run next, records the manual vulnerable and
  fixed observations, and explicitly terminates the scenario when done.
- Attempt scenario mode before falling back to standalone VMs, unless the case
  generator does not expose interactive scenarios or repository documentation
  shows that standalone VMs are required.

For automated validation, spawn a test-runner subagent for each long-running
`nice-archive test` command when subagents are available. The subagent runs the
test in a managed session and reports progress, but the main agent applies the
output watchdog and decides whether the test is stuck. If the watchdog
threshold is reached, the main agent instructs the subagent to interrupt or
terminate the test, or terminates the managed session itself if the subagent
cannot.

Record an end timestamp after validation so elapsed wall-clock time can be
calculated. Never estimate token counts or billing data from context length or
elapsed time. If the runtime does not expose a metadata value, record it as
`not available (not exposed by harness)` rather than guessing.

Usage telemetry is best-effort documentation, not a completion gate. Agent
environments such as IDE chat integrations may expose no per-task token counts,
model identifier, or billing data to the agent. Do not search hidden files,
query unrelated APIs, approximate tokens from text length, or allocate a
subscription price to one run. Continue the reproduction and record the reason
the value is unavailable.

## Required Discovery

Do read-only discovery before implementation. Read at least:

```text
README.md
docs/README.md
docs/reporting-vulnerabilities.md
docs/nice-archive-libs.md
nice-archive.py
```

Inspect a small number of relevant working cases under `cves/`. Select them by
shared package type, network topology, historical nixpkgs strategy, generator,
or test oracle rather than reading every case.

Search for an existing case containing the requested CVE ID before creating a
directory. If one exists and represents the same vulnerability, audit and
complete it in place. Treat previous agent work as unverified until its
research claims, package pins, manual reproduction, and automated tests have
been checked. Create a distinct directory only when an existing matching ID is
demonstrably unrelated, and explain the naming decision.

Before changing code, understand:

- case naming and directory organization;
- `flake.nix` structure and generated output names;
- `nice-archive-lib.testsGenerator` and the other supported generators;
- package, system, and invariant VM variants;
- vulnerable and fixed package selection;
- NixOS test node names and their relationship to `test.py` variables;
- assertion helpers from `assertion_blocks`;
- CLI behavior for tests, scenarios, standalone VMs, lock updates, logging,
  and automatic staging of case files.

Repository documentation is authoritative for framework conventions. Existing
case code is an example, not proof that a pattern is current or correct.

## Vulnerability Research

Research the requested CVE before implementation. NVD is a starting point, not
the sole source. Prefer primary and authoritative sources, and record exact
URLs in the case README.

Consult and reconcile, where available:

- the NVD or CNA record;
- the upstream advisory and security notice;
- fixing commits, patches, and regression tests;
- upstream release notes;
- a public PoC or exploit with clear provenance;
- distribution advisories;
- nixpkgs history for usable vulnerable and fixed packages.

Determine and document:

- affected software and exact affected version range;
- fixed version or commit;
- vulnerability class and root cause;
- configuration and runtime prerequisites;
- Linux and NixOS applicability;
- available PoCs or upstream regression tests;
- expected vulnerable and fixed behavior;
- a reproducible Nix/NixOS packaging strategy.

Verify every URL, commit hash, version range, nixpkgs revision, package
attribute, and source hash before recording it. If sources conflict, describe
the conflict and favor upstream evidence. Never fabricate missing facts.

## Packaging Strategy

Use `nix-versions`, nixpkgs history, and existing case patterns before deciding
to build vulnerable software from source. Prefer historical nixpkgs packages
when they provide the required versions.

Use this priority order unless the target requires a documented exception:

1. Select existing vulnerable and fixed user-space packages from historical
   nixpkgs revisions.
2. Use a package override for a small source or version adjustment.
3. Use `variant = "system"` or an old-kernel generator for system components,
   kernels, distribution services, or tightly coupled dependency sets.
4. Build from source only after nixpkgs history cannot provide a suitable
   package.

For every vulnerable and fixed pin:

- prove the selected package evaluates to the intended version;
- use full immutable revisions in final source URLs when practical;
- verify source hashes rather than copying unexplained values;
- keep package selection near the VM that needs it for package variants;
- keep helper machines invariant unless they genuinely require another pin;
- make vulnerable and fixed environments differ only where necessary.

Use `nice-archive-lib.testsGenerator` unless the framework documentation or a
demonstrated compatibility issue requires another generator. Explain any
deviation in the case README.

## Case Design

Use the naming convention:

```text
cves/cve-yyyy-nnnn-short-lowercase-description/
```

A typical case contains:

```text
flake.nix
test.py
vm-server.nix
vm-attacker.nix
exploit/
readme.md
flake.lock
```

Adapt the file set and topology to the vulnerability. Common topologies are a
single target VM, client/server, attacker/server, or a multi-service network.
Use the smallest topology that faithfully models the real preconditions and
keeps the trigger isolated.

Make VM roles explicit. Use `variant = "package"` when only the selected
package changes, `variant = "system"` when the machine's nixpkgs pin must
change, and `variant = "invariant"` for machines shared by both scenarios.

## Exploit And Oracle

Reuse a supplied or publicly available PoC or upstream regression test whenever
one exists. It may be modified, reduced, or wrapped to run deterministically in
the NixOS lab. Preserve the original security-relevant trigger unless a change
is required and documented.

If no usable PoC exists, a minimal trigger may be derived directly from the
CVE description, upstream advisory, patch, or regression test. Do not invent a
new exploit technique or write an unrelated PoC from scratch. Document the
authoritative artifact from which each trigger step was derived.

Keep final exploit code under the case's `exploit/` directory. Record:

- original source and author when available;
- whether it was copied, adapted, simplified, or rewritten;
- every meaningful local change and why it was required;
- safety limits added for automation.

Exploit code should perform the trigger. Variant-specific expectations belong
in `test.py`.

The oracle must independently prove the security property. Strong examples
include:

- known guest-only content disclosed across a path boundary;
- a marker file created with otherwise unavailable privileges;
- a controlled privilege-boundary crossing verified by UID and GID;
- an expected crash, signal, or core dump;
- a measurable resource-exhaustion condition;
- a service log containing a specific security-relevant event;
- an upstream regression test that fails before the fix and passes after it.

Do not treat any of these as sufficient by themselves:

- the exploit process exited successfully;
- the exploit printed `success`;
- an output file merely exists;
- a request returned some non-error status;
- the fixed exploit returned a nonzero status.

The vulnerable branch must prove the documented effect. The fixed branch must
apply the same trigger, prove the effect is absent, and verify that the target
remained healthy enough for the comparison to be meaningful.

Use `assertion_blocks` for the final security oracle in each branch whenever a
suitable helper exists. Raw Python assertions may support control flow and
health checks but must not replace an applicable assertion block. If no helper
fits, explain why in the case README and implement a deterministic direct
assertion.

Use only guest fixtures and guest files for the oracle. Do not read or modify
host secrets.

## Validation Workflow

Work from cheap checks to expensive VM runs:

1. Inspect repository state, documentation, similar cases, and any existing
   target case.
2. Complete source research and choose verified package pins.
3. Implement the flake, VM modules, trigger, and initial documentation.
4. Evaluate flake outputs and confirm package versions.
5. Start the vulnerable scenario with a scenario subagent when available, or
   use standalone VMs only when scenario mode is unavailable or inappropriate.
6. Use VM-operator subagents, printed SSH commands, popup VM, or test-driver
   shell to check target health and run the trigger manually inside the lab.
7. Repeat the manual trigger against the fixed scenario.
8. Encode the verified workflow in `test.py`.
9. Run the complete vulnerable automated test, preferably through a
   test-runner subagent while the main agent monitors for stuck execution.
10. Run the complete fixed automated test the same way.
11. Update the README with verified commands and observations.
12. Clean or ignore generated artifacts and inspect `git status --short`.

All waits and potentially blocking triggers must have explicit finite
deadlines. This is especially important for the fixed variant, where a blocked
exploit can otherwise wait forever and be mistaken for successful mitigation.

- Give network clients connect and read timeouts.
- Put a bounded `timeout` around untrusted exploit commands and commands that
  may hang on the fixed version.
- Pass explicit timeouts to test-driver polling and wait helpers when the API
  supports them.
- Bound custom loops by elapsed time or attempt count and fail with diagnostic
  output when the limit is reached.
- Give host-side builds and test runs a finite but realistic deadline. Account
  for first-time Nix downloads and builds rather than choosing an arbitrarily
  short limit.
- On timeout, collect useful service status, journal, process, or network
  diagnostics and report the timeout. Never report a timeout as a passing
  fixed result by itself.

Run commands from the repository root, normally inside `nix develop`:

```bash
nice-archive list-cves
nice-archive scenario --case cve-yyyy-nnnn-short-name --vulnerable true --popup false
nice-archive scenario --case cve-yyyy-nnnn-short-name --vulnerable false --popup false
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable true --log live
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable false --log live
```

Outside the development shell, use `nix run . -- <command arguments>`. Prefer
the CLI over guessing generated Nix output names. Be aware that `test` and
`scenario` stage the selected case with `git add` so Git-backed flakes can see
new files; always review the index afterward.

Do not stop after successful evaluation or build. A case is not reproduced
until the trigger has been observed manually in the VM and both automated
variants have been run, unless an external blocker makes that impossible.

## Case Documentation

Keep the case `readme.md` self-contained and source-backed. It must cover:

- description, affected and fixed versions, impact, and root cause;
- required configuration and chosen VM topology;
- generator and package selection strategy;
- advisory, patch, release, PoC, distribution, and nixpkgs references;
- exploit provenance, modifications, and safety limits;
- exact manual reproduction commands and observed behavior;
- vulnerable and fixed CLI test commands;
- the `test.py` oracle and what each assertion proves;
- verified limitations or environmental caveats;
- a reproduction metadata section completed after validation.

The reproduction metadata section must state that the case was reproduced by
an LLM agent and record:

- LLM model identifier;
- agent or coding harness;
- reproduction date;
- command shell used;
- UTC start and end timestamps and elapsed wall-clock time;
- input, output, and total token counts when exposed;
- monetary cost, currency, and calculation source when exposed or calculated
  from known token counts and dated model pricing;
- telemetry source, such as runtime, UI, user-provided, calculated, or not
  exposed by the harness.

Use `not available (not exposed by harness)` for any value the runtime does not
expose. For example, a GitHub Copilot Chat run may identify the harness while
leaving the exact model, per-run tokens, and cost unavailable to the agent.
If cost is calculated rather than reported by the platform, label it as an
estimate and record the pricing source and date. A subscription price is not a
per-run cost. Do not infer or fabricate model identity, tokens, cost, or elapsed
time, and do not treat unavailable telemetry as a reproduction blocker.

Do not preserve a claim solely because a previous agent wrote it. Correct or
qualify anything unsupported by sources or command output.

## Completion Criteria

The task is complete only when all applicable items are true:

- the case is discoverable through the NICE Archive CLI;
- package versions and pins are independently verified;
- manual vulnerable behavior was observed in an isolated VM;
- manual fixed behavior was observed using the same trigger;
- vulnerable and fixed automated tests both ran and passed;
- `test.py` checks the security effect with applicable assertion blocks;
- the README records accurate provenance, commands, results, and references;
- the README records LLM reproduction metadata with unavailable values clearly
  identified;
- no unrelated files or generated VM artifacts are included in the change.

If blocked, leave the most useful coherent partial implementation possible.
Record the exact failing command, relevant output, what has and has not been
verified, and the next concrete action. Do not recast a partial result as
success.

## Final Report

End the work with a concise report containing these fields:

```text
CVE:
Case directory:
Files added/changed:
Generator used:
VM topology:
Vulnerable version:
Fixed version:
PoC or trigger:
Oracle:
Commands run:
Results observed:
Known limitations:
Safety notes:
References:
```

Do not ask questions that can be answered by the repository, its documentation,
existing cases, upstream sources, or nixpkgs history.
