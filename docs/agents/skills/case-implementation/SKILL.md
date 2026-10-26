---
name: case-implementation
description: Implement a researched NICE Archive case with correct files, VM roles, trigger provenance, and an initial two-variant test.
---

# Build the case

Follow the [case layout](../../../reporting/01-create-case.md),
[entry point](../../../reporting/04-entry-point.md), and
[VM configuration](../../../reporting/05-vm-configurations.md) guides. Use
`testsGenerator` unless a documented compatibility constraint requires
another generator. Make variants explicit and independently check the package
versions after evaluation.

Keep `flake.nix`, `test.py`, the README, and VM modules at the case root. Put
all payloads and trigger helpers under `exploit/<role>/`; use `package/` only
for complex packaging expressions. Create no empty placeholders and store no
affected-product source in the case. Fetch target patches immutably with
verified hashes.

Use the [test guide](../../../reporting/07-test.md) for a linear `test.py`:
readiness, bounded trigger, evidence collection, and vulnerable/fixed oracle.
Keep expectations in `test.py`, use the same trigger in both branches, plant a
target-unique marker, and finish each branch with an applicable
`assertion_blocks` helper. If none fits, use a deterministic direct assertion
and explain it in the README. Claims from an existing case are unverified
until checked.
