# NICE Archive Agent Instructions

These instructions apply when the user asks to reproduce a vulnerability, for
example `Reproduce CVE-YYYY-NNNN`. Derive the affected software, versions,
case name, topology, and oracle from the request, repository state, and
authoritative research. Do not reuse assumptions from another CVE.

The objective is an isolated, machine-checkable NICE Archive case that proves
both vulnerable and fixed behavior. This file is the concise normative
contract. Follow the detailed procedures in
[`docs/reporting-vulnerabilities.md`](./docs/reporting-vulnerabilities.md) and
the API reference in
[`docs/nice-archive-libs.md`](./docs/nice-archive-libs.md).

## 1. Safety gates

### Scope and isolation

- Work only in this repository, except for read-only upstream research and
  downloads required by Nix. Use `/tmp` or the case directory for temporary
  artifacts, and preserve all user changes.
- Never execute vulnerable target software, PoCs, malicious inputs, exploit
  triggers, crash tests, or resource-exhaustion tests directly on the host or
  in the coding-agent shell. Never target public systems, or unrelated services.
- Before executing a target or trigger, state the isolation boundary, why it
  fits the vulnerability class, and how the command is known to run inside it.
  Restrict networking and mounts and use only guest fixtures and secrets.
- Prefer NixOS test or standalone VMs. Use a container only for a user-space
  flaw that cannot exercise the host kernel, container runtime, devices, or
  host privileges. Kernel flaws, local privilege escalation, system services,
  destructive tests, and uncertain PoCs require a VM.
- Host port forwarding is allowed only for standalone VMs when their manual
  wiring requires it. Scenario and test VMs must use the lab network, and port
  forwarding never authorizes host-side execution of a target or trigger.
- `nix develop`, `nix-shell`, and Nix build sandboxing are dependency or build
  environments, not execution boundaries for the target or trigger. If the
  lab cannot be established, stop before the trigger and report the blocker.
- Inspect fetched PoCs and historical software before guest execution. Do not
  change global configuration, use destructive Git commands, or modify
  unrelated cases or projects.

The full boundary procedure is documented under
[Isolation gate](./docs/reporting-vulnerabilities.md#isolation-gate).

### Framework suitability

Before implementation, confirm that the affected target and behavior apply to
Linux, can be represented with Nix/NixOS/Linux VMs or a suitable Linux
container, and admit a machine-checkable Linux-side oracle. A Linux attacker
or build host does not make a Windows-, Apple-, Android-, hardware-, firmware-,
or hosted-product-only vulnerability eligible.

If the target is out of scope, do not create or modify a case and do not run a
PoC. Return the CVE, affected target/platform, reason, evidence, and references.

Use the detailed
[Framework suitability gate](./docs/reporting-vulnerabilities.md#framework-suitability-gate)
to resolve uncertain and cross-platform cases.

### Shell and environment record

Before repository exploration, record in working notes:

- the user shell, when exposed, and the command-runner shell as separate
  values;
- a host-sourced UTC start timestamp;
- the runtime-exposed model and agent harness; and
- whether input, output, total-token, and cost telemetry are exposed.

Environment or tool metadata is authoritative for the command runner; `$SHELL`
usually identifies only the login shell. Until the runner is known, use only
direct, non-interactive, single-program invocations—no control operators,
redirection, substitution, variables, globs, aliases, functions, or heredocs.
Afterward, use that shell's syntax or explicitly select a startup-file-free
interpreter. Never launch an interactive/login shell for automation or source
user startup files. Scripts and human-facing commands must name or match their
intended interpreter.

Record an end timestamp after validation. Never guess model identity, tokens,
cost, or elapsed time, search hidden state for telemetry, or treat unavailable
telemetry as a blocker. Use `not available (not exposed by harness)`.

See [Shell execution gate](./docs/reporting-vulnerabilities.md#shell-execution-gate)
for command examples and the complete environment-record procedure.

### Time and progress bounds

Every command must have a finite tool deadline. Enforce these process-level
limits from launch:

| Activity | Maximum runtime |
| --- | --- |
| Ordinary command | 5 minutes |
| VM or service readiness | 5 minutes |
| Complete NixOS test | 30 minutes |
| Complete interactive scenario | 45 minutes |

Run commands that may exceed two minutes as managed sessions. Poll at least
every two minutes and terminate after five continuous minutes without new
meaningful output or a successful bounded health check. Send `TERM` or an
interrupt first, wait at most 30 seconds, then force only the owned process
group if necessary. Collect final output, status, relevant logs, and clean up
owned test-driver or QEMU children. A timeout or forced kill is a failure or
blocker, never proof of fixed behavior.

Use native NixOS test-driver `timeout=` arguments for guest commands and waits
when supported, plus application-level connect/read timeouts. The host-side
process watchdog does not replace guest-side bounds. Detailed monitoring and
termination rules are in
[Bound waits and blocking triggers](./docs/reporting-vulnerabilities.md#bound-waits-and-blocking-triggers).

## 2. Required outcomes

### Research and target selection

- Reconcile the CNA/NVD record with upstream advisories, fixes, release notes,
  regression tests or public PoCs, distribution advisories, and nixpkgs
  history. Prefer primary sources and document conflicts.
- Verify every recorded URL, version range, commit, package attribute,
  nixpkgs revision, and source hash. Prove the selected vulnerable version is
  inside the authoritative affected range; it need not be the last affected
  release. Prove the fixed selection contains the fix.
- Search nixpkgs history before building from source. Prefer, in order:
  historical packages with `variant = "package"`; whole-target-VM pinning with
  `variant = "system"`; old-kernel support; then a Nix package that fetches a
  complete immutable, hash-verified upstream source.
- Never copy, vendor, reconstruct, or reduce affected-product source into the
  case. Case-owned Nix expressions, VM configuration, wrappers, tests, and
  exploit code are allowed. Fetch target patches immutably with verified
  hashes.

See [Package source strategy](./docs/reporting-vulnerabilities.md#package-source-strategy)
for search commands, pinning patterns, and generator selection.

### Case and topology

- Search for the CVE before creating a directory. Audit and complete the same
  case in place; treat existing claims and test results as unverified.
- Use `cves/cve-yyyy-nnnn-short-lowercase-description/`. Keep primary entry
  points, `test.py`, the case README, and VM modules at the root. Put every
  trigger artifact under `exploit/<role>/` and complex packaging-only
  expressions under `package/`; do not create empty placeholders.
- Use the minimum realistic topology while preserving required service,
  network, privilege, and trust boundaries. Give distinct deployment roles
  such as proxies, relays, databases, and identity providers separate VMs when
  that boundary affects the vulnerability. Keep helper machines invariant.
- Use `testsGenerator` unless documented compatibility constraints require
  another generator. Make VM variants explicit.

### Trigger and oracle

- Reuse a supplied/public PoC or upstream regression test when available.
  Preserve attribution and the security-relevant trigger; document every
  meaningful adaptation and safety bound. If none exists, derive only a
  minimal trigger from authoritative vulnerability material.
- Keep `test.py` linear and human-readable, with concise phase comments for
  readiness, trigger execution, evidence collection, and the expected
  vulnerable/fixed oracle. Expectations belong in `test.py`, not exploit code.
- Apply the same bounded trigger to both variants. The vulnerable branch must
  prove the security effect. The fixed branch must prove the effect absent and
  the target healthy enough for comparison.
- Use deterministic, target-unique guest markers and verify evidence at the
  security boundary. Do not rely on command success, exploit self-reporting,
  generic OS content, output-file existence alone, or only attacker-side
  output when the effect occurs on another VM.
- Finish each branch with an applicable `assertion_blocks` helper. If no helper
  fits, use a deterministic direct assertion and explain the exception in the
  case README.

### Documentation and evidence

The case README must be compact, self-contained, source-backed, and follow the
required section order in
[Write the case README](./docs/reporting-vulnerabilities.md#13-write-the-case-readme).
It must record affected/fixed versions, prerequisites, topology and roles,
pins, trigger provenance and modifications, target marker, oracle, verified
manual and automated commands, observed results, limitations, safety notes,
references, and LLM reproduction metadata. Do not cite another case as the
authority for this case. Clearly label anything not run.

Claims require command output or authoritative sources. Never preserve a claim
merely because another agent wrote it.

## 3. Workflow

Before editing, run `git status --short`, preserve unrelated changes, and read:

- [`README.md`](./README.md) and [`docs/README.md`](./docs/README.md);
- the relevant sections of the
  [reporting guide](./docs/reporting-vulnerabilities.md);
- the [library reference](./docs/nice-archive-libs.md); and
- the relevant CLI implementation and a small number of cases selected for
  matching package type, topology, generator, pinning strategy, or oracle.

Then work in this order:

1. Resolve framework suitability and search for an existing case.
2. Research affected/fixed behavior, PoC provenance, Linux applicability, and
   verified package pins.
3. Design the minimum topology, target-unique marker, and two-variant oracle.
4. Implement the flake, VM modules, role-organized trigger, `test.py`, and
   initial README.
5. Evaluate outputs and independently confirm package versions.
6. Start the vulnerable scenario through the NICE Archive CLI and manually
   observe the trigger inside the isolated lab.
7. Repeat the identical manual trigger against the fixed scenario.
8. Encode or refine the observed flow in `test.py`.
9. Run both complete automated variants through `nice-archive test`.
10. Update only verified README results, clean generated artifacts, review the
    Git index, and run `git status --short` again.

Use the NICE Archive CLI from the repository root whenever it supports the
operation. Direct Nix commands are for unsupported operations or diagnosis;
record why they were needed and return to the CLI for final validation. The
`test` and `scenario` commands stage the selected case for Git-backed flake
evaluation, so always inspect the index afterward.

### Subagents

The main agent owns research, isolation choices, package pins, safety limits,
watchdog decisions, documentation, and final claims. A subagent may own a
long-running scenario or test only if the harness immediately exposes a
detached session handle the main agent can poll and terminate. Otherwise, the
main agent must own the managed process and may delegate only bounded work such
as research, log analysis, or individual guest commands.

When that capability gate passes, use a scenario subagent to keep
`nice-archive scenario ... --popup false` alive and report its SSH commands;
use VM-operator subagents for bounded guest health checks, trigger execution,
and evidence collection; and use test-runner subagents for automated variants.
The main agent monitors progress, compares vulnerable/fixed evidence, and
terminates scenarios explicitly. Scenario-lock acquisition is expected output;
it does not serialize automated tests.

See [Subagent orchestration](./docs/reporting-vulnerabilities.md#subagent-orchestration)
for the detailed roles and capability gate.

If blocked, leave the most useful coherent partial implementation. Record the
exact failing command and output, what is and is not verified, and the next
concrete action. Never recast partial work as success.

## 4. Completion checklist

The task is complete only when all applicable items are true:

- the case is discoverable through the NICE Archive CLI;
- authoritative evidence supports the affected range, selected vulnerable
  version, and fix, and evaluated packages match their intended versions;
- the narrowest faithful packaging strategy is used and no affected-product
  source is stored in the case;
- the topology preserves every required security boundary while omitting
  unnecessary machines;
- manual vulnerable and fixed behavior was observed in an isolated lab using
  the same trigger;
- vulnerable and fixed automated tests both ran and passed through the CLI;
- commands, waits, tests, scenarios, and managed-session monitoring obeyed the
  required bounds;
- `test.py` proves the security property with target-unique guest evidence,
  healthy fixed behavior, and applicable assertion blocks;
- exploit artifacts, packaging expressions, and primary files follow the
  documented layout;
- the README follows the required compact structure and contains only verified
  results and accurate provenance, references, safety notes, and metadata;
- unavailable telemetry is identified rather than guessed;
- generated artifacts and unrelated changes are absent from the final change;
  and
- final `git status --short` and index review have been performed.

End with a concise report covering the CVE, case directory, changed files,
generator and topology, vulnerable/fixed versions, trigger and oracle, commands
run, observed results, limitations, safety notes, and references. Do not ask
questions that the repository, documentation, authoritative sources, or
nixpkgs history can answer.
