---
name: subagent-orchestration
description: Delegate long-running NICE Archive scenarios and tests only when the main agent can poll and terminate their detached sessions.
---

# Subagent orchestration

The main agent retains research, isolation, package pins, deadlines, watchdog
decisions, documentation, and final claims. Delegate a long-running scenario
or test only if the harness immediately returns a detached session handle
that the main agent can poll and terminate. A synchronous or hidden process
stays with the main agent; bounded research, log analysis, or guest commands
may still be delegated when authorized.

When the gate passes, use a scenario subagent for
`nice-archive scenario --case <case> --vulnerable <true|false> --popup false`.
It reports the handle, readiness, and printed guest SSH commands. Use VM
operator subagents for bounded health checks, triggers, and target evidence
inside the lab. The main agent monitors progress and tells the scenario
subagent when to stop the VMs. Repeat for the fixed variant under the same
trigger. Scenario-lock acquisition is expected; it does not serialize tests.

Use test-runner subagents for the two `nice-archive test` variants only under
the same handle gate. The main agent polls each run and decides when the
inactivity or hard deadline requires termination. Apply the shared
[clock rules](../agent-runtime/SKILL.md#deadlines-and-progress) from launch;
an agent report without exit status and guest evidence is not a test result.
