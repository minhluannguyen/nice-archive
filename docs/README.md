# NICE Archive documentation

This directory contains the project documentation for working with NICE
Archive as a reproducible vulnerability-reporting framework.

## Start here

- [NICE Archive library reference](./nice-archive-libs.md)  
  Use this when you need exact library syntax, exported functions, VM fields,
  generated outputs, and assertion helper signatures.

- [Reporting a vulnerability with NICE Archive](./reporting-vulnerabilities.md)  
  This is the detailed implementation playbook behind the concise
  repository-level `AGENTS.md` contract. Use it for VM design, flake structure,
  tests, CLI commands, interactive debugging, and handoff checklists.

- [CVE OpenCode batch orchestrator](./CVE_ORCHESTRATOR_README.md)
  Use this when running unattended multi-CVE OpenCode experiments and collecting
  batch-level result metadata.

## Suggested reading order

1. Read the root [README](../README.md) for setup and CLI basics.
2. Follow [Reporting a vulnerability with NICE Archive](./reporting-vulnerabilities.md).
3. Check [NICE Archive library reference](./nice-archive-libs.md) when you need
   exact generator or VM-field syntax.
4. Read the repository-level [`AGENTS.md`](../AGENTS.md) when delegating a case
   to a coding agent.

## Documentation map

| Document | Audience | Contents |
| --- | --- | --- |
| [Root README](../README.md) | New users | Setup, CLI usage, interactive helper usage, direct Nix outputs, cleanup. |
| [Library reference](./nice-archive-libs.md) | Contributors and agents editing library-backed cases | `testsGenerator`, `standaloneVMGenerator`, `oldKernelTestsGenerator`, VM fields, assertions. |
| [Vulnerability reporting guide](./reporting-vulnerabilities.md) | Humans and LLM agents building CVE reports | End-to-end technical workflow and checklists. |
| [CVE OpenCode batch orchestrator](./CVE_ORCHESTRATOR_README.md) | Experiment runners | Batch OpenCode worktree orchestration, result files, live output, and OpenRouter metadata. |
