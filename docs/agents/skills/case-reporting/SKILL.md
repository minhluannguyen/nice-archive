---
name: case-reporting
description: Write a source-backed NICE Archive case README and evidence handoff from actually observed manual and automated results.
---

# Report verified evidence

Follow the exact section order and fields in
[the case README guide](../../../reporting/09-case-readme.md). Give affected
and fixed versions, acquisition source and pins, prerequisites, VM roles,
trigger provenance and adaptations, target marker, oracle, manual commands,
automated commands, actual results, limitations, safety notes, and references.
For multi-VM cases, include a compact VM diagram with numbered trigger and
evidence arrows. Label unrun steps explicitly; cite authoritative sources or
command output for claims. Do not cite another case as this case's authority.

For an LLM reproduction, record the user shell and runner shell separately,
UTC start/end and measured elapsed time, model and harness if exposed, and
input/output/total tokens and cost only when exposed. Use `not available (not
exposed by harness)` for missing fields; never infer usage from context size
or subscription price. Use the README guide's metadata field names.

Clean generated case artifacts without deleting user files. Review the Git
index, run final `git status --short`, and report the case path, changed files,
generator and topology, versions, trigger and oracle, commands and outcomes,
limitations, safety boundary, and references. Keep partial results explicit.
