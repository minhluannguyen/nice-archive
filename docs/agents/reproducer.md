# Reproducer agent

Use this role when asked to reproduce or repair one CVE case. The result is an
isolated, machine-checkable case that proves the security effect on a
vulnerable selection and its absence on a healthy fixed selection. Derive the
target, versions, topology, and oracle from this CVE's sources; do not reuse
another case's assumptions.

After the [shared runtime gate](./skills/agent-runtime/SKILL.md), work through
these skills in order:

1. [Research and design](./skills/cve-research/SKILL.md): eligibility, existing
   case, authoritative evidence, package pins, topology, and oracle.
2. [Build the case](./skills/case-implementation/SKILL.md): files, packaging,
   VM roles, trigger artifacts, and initial test.
3. [Validate in the lab](./skills/lab-validation/SKILL.md): evaluate packages,
   manually observe both variants, then run both automated tests.
4. [Report evidence](./skills/case-reporting/SKILL.md): README, metadata,
   cleanup, index review, and handoff.

Read the relevant step of the [technical reporting workflow](../reporting-vulnerabilities.md)
when performing it. Start every scenario with `nice-archive scenario` and
every automated validation with `nice-archive test` from the repository root.
Direct Nix is for unsupported work or diagnosis; give it finite tool and
process deadlines, record why it was needed, and return to the CLI for final
validation.

If blocked, leave a coherent partial case. Give the exact failed command and
output, distinguish verified from unverified work, and name the next concrete
action. Never turn a timeout, failed build, or unrun variant into a pass.
