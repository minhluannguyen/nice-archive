## Goal of a NICE Archive report

A good report case should answer six questions:

1. What vulnerability is being reproduced?
2. Which software and versions are vulnerable or fixed?
3. What does the scenario look like, and which machines are involved?
4. How are the machines configured to reproduce the vulnerability?
5. What action triggers the vulnerability?
6. Which assertion checks the vulnerability of the system?

The expected output is a directory under [`cves/`](../cves/) with:

```text
cves/cve-yyyy-nnnn-short-name/
├── flake.nix
├── default.nix              # only when required by the selected workflow
├── README.md
├── test.py
├── vm-server.nix
├── vm-attacker.nix
├── exploit/
│   ├── attacker/
│   └── server/
├── package/                 # only for complex packaging expressions
└── flake.lock
```

Some reports may need fewer files, and graphical or old-kernel reports may
need more. Keep primary entry points, the case README, `test.py`, and VM
configuration files in the case root. `default.nix` is optional for modern
flake-backed cases. Preserve an existing legacy `readme.md` filename when
completing a case unless a rename is explicitly in scope.

Put every exploit script, payload, helper service, malformed fixture, and
other trigger artifact below `exploit/<role>/`, where `<role>` is the VM or
execution environment that consumes it, such as `attacker`, `server`, or
`client`. Use `exploit/shared/` only for artifacts genuinely consumed by
several roles. If target packaging needs a large or multi-file expression,
place packaging-only files under `package/` or `package/<target>/` and import
them from the root entry point. The `package/` directory must not contain
copied affected-product source. Do not create empty placeholder directories.
## Agent-friendly workflow

If you are an LLM agent working on a new report, follow this order:

1. Record the user shell and command-runner shell separately, plus UTC start
   time, model, harness, and which usage metadata the runtime exposes.
2. Do read-only discovery, resolve framework suitability, and search for an
   existing matching case.
3. Work only in the case directory or in the worktree assigned by the
   orchestrator. Do not create or switch Git branches unless the user or
   orchestration workflow explicitly requires it.
4. Research vulnerable/fixed behavior, record exploit provenance, and select
   verified package pins before considering a source build.
5. Design the minimum topology, target-unique marker, two-variant oracle, and
   appropriate generator.
6. Implement the Nix files, role-organized trigger, initial `test.py`, and
   initial README.
7. Evaluate the generated outputs and independently confirm package versions.
8. Start the vulnerable VM scenario with a scenario subagent only when the
   capability gate passes; otherwise, the main agent owns the managed scenario.
   Use standalone VMs only when scenario mode is unavailable or inappropriate.
9. Use VM-operator subagents with SSH, popup VM windows, or the test-driver
   shell to reproduce the vulnerable behavior manually.
10. Repeat the identical manual trigger against the fixed scenario.
11. Refine `test.py` from the observed workflow and end each branch with a
    suitable `assertion_blocks` helper.
12. Run vulnerable and fixed tests with finite timeouts, preferably through
    test-runner subagents while the main agent monitors progress.
13. Update the case README with verified commands, assertions, and LLM
    reproduction metadata.
14. Report exactly what changed and what was verified.

## LLM reproduction contract

When using this framework, an LLM agent should treat the following as hard
requirements:

- Prefer existing nixpkgs packages and historical nixpkgs revisions over
  building vulnerable software from source.
- Use `nix-versions` or Nixpkgs history before deciding that a source build is
  necessary.
- Keep each CVE's changes isolated to its case directory or assigned worktree.
  Do not create or switch Git branches unless the user or orchestration
  workflow explicitly requires it.
- Treat shell detection as a pre-execution gate. Do not run shell-dependent or
  compound commands until the command runner's interpreter is known.
- Give every command-execution call a finite deadline and never wait
  indefinitely for a prompt or a command that stopped making progress.
- Never execute vulnerable software, PoCs, malicious inputs, or exploit
  triggers in the coding-agent session or directly on the host.
- Establish and state a suitable VM or container boundary before running a
  trigger. Do not fall back to host execution if isolation fails.
- Follow the documented case layout. Existing cases can demonstrate APIs and
  packaging patterns, but legacy layouts are not authoritative for new cases.
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

Host port forwarding is allowed only for standalone VMs when their manual
wiring requires it. Scenario and automated-test VMs must communicate over the
lab network. Forwarding does not authorize host-side target or trigger
execution.

### Framework suitability gate

Resolve platform eligibility before creating or modifying a case, adapting a
PoC, choosing package pins, or starting a lab. A vulnerability fits NICE
Archive only when all of the following are true:

- the vulnerable target runs on Linux;
- the affected behavior and its required configuration apply to the Linux
  build;
- vulnerable and fixed behavior can reasonably be represented with Nix,
  NixOS, Linux VMs, or a suitable Linux container; and
- a deterministic, machine-checkable Linux-side oracle is possible.

For cross-platform software, verify from authoritative evidence that the Linux
build is affected by the same flaw. A Linux attacker, client, build host, or
diagnostic utility does not make a non-Linux target eligible.

Reject Windows-only components, Apple- or Android-specific behavior, hardware,
firmware, microcode, BIOS/UEFI, flaws requiring physical equipment, and hosted
products with no reproducible affected Linux package. When applicability is
uncertain, perform only enough read-only research to resolve it; do not begin
implementation while it remains unresolved.

For an out-of-scope request, stop before creating a case or running a target or
PoC and return:

```text
CVE:
Framework eligibility: out of scope
Affected target/platform:
Reason:
Evidence:
References:
```

Do not leave a partial case for a CVE rejected by this gate. Suggest an
alternative Linux vulnerability only when the user asks for one.

## LLM reproduction metadata

Complete `Reproduction metadata` in the case README after validation. Identify
whether the case was reproduced by a human researcher or an LLM agent. For an
LLM reproduction, identify the exact model and harness when the runtime exposes
them, and record start and end timestamps so elapsed time is measured rather
than guessed.

Record these fields:

- **Reproduced by:** `<human researcher>` or `<LLM agent>`
- **Date:** `<YYYY-MM-DD>`
- **Model:** `<runtime value or not available with reason>`
- **Agent/harness:** `<tool and version or not available with reason>`
- **User shell:** `<bash, zsh, fish, other, or not exposed>`
- **Command-runner shell:** `<actual interpreter used by the command tool>`
- **Start time:** `<UTC timestamp or not available with reason>`
- **End time:** `<UTC timestamp or not available with reason>`
- **Elapsed time:** `<measured duration or not available with reason>`
- **Input tokens:** `<runtime value or not available with reason>`
- **Output tokens:** `<runtime value or not available with reason>`
- **Total tokens:** `<runtime value or not available with reason>`
- **Cost:** `<platform value, sourced estimate, or not available with reason>`
- **Telemetry source:** `<runtime, UI, user-provided, calculated, or not exposed>`

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

## LLM failure modes to avoid

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

## Handoff note template

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

Keep the diagram faithful to the actual machines and `test.py`. Number arrows
in trigger and evidence order, label meaningful protocols or ports, and
explain each numbered action below the diagram. A simple one-VM case may use
prose instead. Keep results brief; do not paste full logs or turn an unrun
validation into a pass. A justification explains a choice but does not waive
isolation or validation requirements.
