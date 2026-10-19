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
If scenario mode is unavailable or inappropriate, use the documented
[standalone VM method](../../../standalone-vms.md). State the isolation
boundary before execution. Never fall back to host-side target or trigger
execution.

Translate the observed sequence into `test.py`, then run both complete
variants with `nice-archive test`. Use distinct logs and capture each exit
status. A build success, command exit, or attacker self-report alone does not
prove the oracle. Diagnose an unchanged failure before retrying it again;
stop at the time bound and report what remains unverified. The
[CLI guide](../../../cli-tool.md) is authoritative for supported flags and
interaction. Scenario and test commands stage the case for flake evaluation,
so review the Git index afterward.

## Avoid

When guest SSH or popup access is available, do not rely only on the
test-driver prompt for manual observation. Keep simple triggers visible in
guest commands or small helpers instead of hiding the workflow in one large
script. Point readers to `test.py` for the machine-checkable oracle.
