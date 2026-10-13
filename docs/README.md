# NICE Archive documentation

This directory contains the project documentation for working with NICE
Archive as a reproducible vulnerability-reporting framework.

## Start here

- [Reporting a vulnerability with NICE Archive](./reporting-vulnerabilities.md):
  how to report a CVE with NICE Archive.

- [NICE Archive CLI guide](./cli-tool.md): instructions and how to use the `nice-archive` command-line tool.

- [NICE Archive library documentation](./nice-archive-libs.md): the detailed documentation for the `nice-archive-lib`, including the helper functions, and assertions for writing vulnerability recipes.

- [Vulnerability-specific reproduction](./vulnerability-specific-reproduction.md):
  guidance and note for specific vulnerability classes (Remote code execution, XSS, DoS, etc) reproductions.

- [Standalone VMs for manual reproduction](./standalone-vms.md): optional
  manually launched VMs when the interactive scenario does not fit.

- [Temporary agent instructions](./tmp-agent.md): agent and LLM procedures
  moved out of the reporting workflow pending a later revision.

- [CVE OpenCode batch orchestrator](./CVE_ORCHESTRATOR_README.md)
  Use this when running unattended multi-CVE OpenCode experiments and collecting
  batch-level result metadata.
