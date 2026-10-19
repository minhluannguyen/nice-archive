---
name: agent-runtime
description: Apply shared shell, eligibility, isolation, and process bounds before reproducing or evaluating a NICE Archive CVE.
---

# Agent runtime and safety

## First record

Before repository exploration, record the user shell when exposed, the actual
command-runner interpreter, a host-sourced UTC start timestamp, runtime-exposed
model and harness, and whether input, output, total-token, and cost telemetry
are exposed. Tool metadata, not `$SHELL`, identifies the runner. Until known,
run only direct, non-interactive, single-program commands. Then use its syntax
or explicitly select a startup-file-free interpreter. Never launch a login or
interactive shell for automation or source startup files. Record UTC end time
after validation; use `not available (not exposed by harness)` for unavailable
telemetry rather than estimating it.

Until the runner is known, avoid pipelines, redirection, substitutions,
variables, globs, aliases, functions, and heredocs. Scripts and human-facing
commands must name or match their interpreter. For a real TTY prompt, use the
[prompt-interaction skill](../prompt-interaction/SKILL.md).

Run `git status --short` before editing. Preserve unrelated changes; do not
switch branches or use destructive Git operations unless the task requires it.
Work within the assigned repository or worktree and `/tmp` for temporary
artifacts. Read-only upstream research and Nix downloads are allowed. Do not
change global configuration or unrelated cases.

## Suitability gate

Before case implementation or trigger execution, verify that the affected
target and behavior apply to Linux, that a Linux VM or suitable container can
represent the required configuration, and that a deterministic Linux-side
oracle is possible. A Linux attacker or build host does not make a
Windows-, Apple-, Android-, firmware-, hardware-, or hosted-product-only flaw
eligible. If out of scope, make no case changes and run no PoC; report CVE,
affected target/platform, reason, evidence, and references.

## Isolation gate

Host work is limited to source review, file editing, safe metadata queries,
sandboxed builds, and starting or controlling the isolated lab.
Never execute vulnerable software, PoCs, malformed inputs, crash tests, or
resource-exhaustion triggers in the host coding shell. Before execution, state
the boundary, why it fits the flaw, and how the command runs inside it. Prefer
NixOS test or standalone VMs. A container is suitable only for a user-space
flaw that cannot reach the host kernel, runtime, devices, or privileges.
Kernel flaws, local privilege escalation, system services, destructive tests,
resource exhaustion, and uncertain PoCs require a VM. Restrict networking and
mounts, use guest-only fixtures and secrets, and never target public or
unrelated services. Host port forwarding is permitted only when manually
wiring standalone VMs; scenario and test VMs use the lab network. Never aim a
guest trigger at host `localhost`. Port forwarding does not authorize
host-side execution of a target or trigger.

`nix develop`, `nix-shell`, and Nix build sandboxes do not isolate target or
trigger execution. Inspect fetched PoCs and historical software before guest
execution. If the lab cannot be established, stop before the trigger.

## Deadlines and progress

Give each command a finite tool deadline and a process-level bound from
launch:

| Activity | Maximum runtime |
| --- | --- |
| Ordinary command | 5 minutes |
| VM or service readiness | 5 minutes |
| Complete NixOS test | 30 minutes |
| Complete interactive scenario | 45 minutes |

Use guest `timeout=` where supported and application connect/read timeouts.
Runner-specific budgets may be shorter.

Start each clock at process launch, including build, boot, execution, and
shutdown. Do not extend a running deadline or restart work to reset its
clock. Reserve termination grace inside the applicable limit.

Run operations likely to exceed two minutes as managed sessions. Poll at least
every two minutes; after five continuous minutes without meaningful new output
or a successful bounded health check, terminate the owned operation. Send
TERM or interrupt first, wait at most 30 seconds, then force only the owned
process group if needed. Collect status and relevant logs; clean up owned VM
children. A timeout or forced kill is a failure or blocker, never proof of
fixed behavior. See [test time bounds](../../../reporting/07-test.md) for
guest-level details.

Check inactivity by two minutes, four minutes, and five minutes after the
last meaningful progress. Repeated identical output and mere process
existence are not progress. Exit status `124` is a timeout, not a pass.

## Optional subagents

The main agent owns safety, pins, watchdog decisions, documentation, and final
claims. A subagent may own a scenario or test only when it immediately gives
the main agent a detached handle the main agent can poll and terminate.
Otherwise, the main agent owns the managed process; delegate only bounded
research, log analysis, or guest commands when delegation is authorized. Use
the [subagent orchestration skill](../subagent-orchestration/SKILL.md) when
delegating a scenario or test.
