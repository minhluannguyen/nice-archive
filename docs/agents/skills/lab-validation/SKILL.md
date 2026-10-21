---
name: lab-validation
description: Manually and automatically validate both NICE Archive variants in isolated guests with bounded processes and target-side evidence.
---

# Validate in the lab

Apply [runtime safety](../agent-runtime/SKILL.md). Read
[scenario mode](../../../reporting/06-scenario-mode.md),
[test writing](../../../reporting/07-test.md), and
[test verification](../../../reporting/08-verify-test.md). Confirm evaluated
outputs and target versions before starting the trigger.

Use `nice-archive scenario` for vulnerable manual observation, then repeat
the identical guest trigger in the fixed scenario. Use the printed guest SSH
commands or bounded test-driver methods. Confirm the vulnerable security
effect where it occurs and the fixed absence plus normal target operation.
Each scenario call has a 10-minute ceiling. The first call starts one
40-minute manual-validation budget across variants; stop manual work at that
deadline and record missing observations. For a shared CLI clock across calls,
set `NICE_ARCHIVE_PHASE_BUDGET_FILE` to a fresh path for this attempt before
the first scenario and keep the path unchanged.

Use `--popup false --log file <variant-log> --status-file <variant-status.json>`
for a managed scenario. Read `ssh_verified` before using a guest SSH command.
The bounded `scenario> ` proxy accepts one-line test-driver Python; finish
each call with `:quit` and wait for the process to exit. Give each variant
distinct log and status files. The [CLI guide](../../../cli-tool.md#open-a-scenario)
defines the prompts and response markers.

If scenario mode is unavailable or inappropriate, use the documented
[standalone VM method](../../../standalone-vms.md). State the isolation
boundary before execution. Never fall back to host-side target or trigger
execution.

Run `nice-archive begin-test-phase` before writing or refining `test.py` after
manual validation. The 40-minute test budget includes writing, both complete
variants, and fixes; an in-flight test must stop by the shorter of its
30-minute bound and the remaining phase time. Translate the observed sequence
into `test.py`, then run both variants with `nice-archive test`. Use distinct
logs and capture each exit
status. A build success, command exit, or attacker self-report alone does not
prove the oracle. After two identical failures, diagnose and change the
approach before another retry;
stop at the time bound and report what remains unverified. The
[CLI guide](../../../cli-tool.md) is authoritative for supported flags and
interaction. Scenario and test commands stage the case for flake evaluation,
so review the Git index afterward.

## Avoid

When guest SSH or popup access is available, do not rely only on the
test-driver prompt for manual observation. Keep simple triggers visible in
guest commands or small helpers instead of hiding the workflow in one large
script. Point readers to `test.py` for the machine-checkable oracle.
