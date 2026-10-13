# Reporting a vulnerability with NICE Archive

This is the entry point for building a reproducible, machine-checkable CVE
case. Follow the steps in order for a new case; revisit individual pages when
repairing an existing one. The case should demonstrate the security effect in
the vulnerable variant and its absence in a healthy fixed variant.

## Workflow

| Step | Document | Outcome |
| --- | --- | --- |
| 1 | [Create or find the case](./reporting/01-create-case.md) | A correctly named, scoped case directory. |
| 2 | [Research and select software](./reporting/02-research-and-sources.md) | Proven affected/fixed selections and trigger provenance. |
| 3 | [Design the topology and choose a generator](./reporting/03-design.md) | The minimum faithful VM roles and a compatible test strategy. |
| 4 | [Write the case entry point](./reporting/04-entry-point.md) | Pinned flake or documented legacy entry point. |
| 5 | [Writing VMs configuration](./reporting/05-vm-configurations.md) | Target, helper, and attacker machines with guest fixtures. |
| 6 | [Use scenario mode to test exploitation](./reporting/06-scenario-mode.md) | Observe the vulnerable and fixed behavior in interactive guest labs. |
| 7 | [Write the automated test](./reporting/07-test.md) | Encode the observed trigger and target-specific assertions. |
| 8 | [Verify test correctness](./reporting/08-verify-test.md) | Both automated variants prove the intended security property. |
| 9 | [Write the case README](./reporting/09-case-readme.md) | A concise, source-backed account of actual results. |

