# NICE Archive documentation

This directory contains the project documentation for working with NICE
Archive as a reproducible vulnerability-reporting framework.

## Start here

- [Reporting a vulnerability with NICE Archive](./reporting-vulnerabilities.md):
  how to report a CVE with NICE Archive.

- [Building upstream and third-party packages](./reporting/upstream-and-third-party-builds.md):
  Nix packaging examples for targets absent from nixpkgs and case-owned triggers.

- [Reviewing new CVE recipes](./REVIEWING.md): checklist and labels for pull
  requests that add a recipe.

- [NICE Archive CLI guide](./cli-tool.md): instructions and how to use the `nice-archive` command-line tool.

- [NICE Archive library documentation](./nice-archive-libs.md): the detailed documentation for the `nice-archive-lib`, including the helper functions, and assertions for writing vulnerability recipes.

- [Vulnerability-specific reproduction](./vulnerability-specific-reproduction.md):
  guidance and note for specific vulnerability classes (Remote code execution, XSS, DoS, etc) reproductions.

- [Standalone VMs for manual reproduction](./standalone-vms.md): optional
  manually launched VMs when the interactive scenario does not fit.

- [Agent guides](./agents/reproducer.md): start at
  [AGENTS.md](../AGENTS.md), then choose the
  [reproducer](./agents/reproducer.md) or
  [evaluator](./agents/evaluator.md) role. Focused `SKILL.md` files under
  [agent skills](./agents/skills/) contain the shared gates and role workflows.

- [CVE OpenCode batch orchestrator](./CVE_ORCHESTRATOR_README.md)
  Use this when running unattended multi-CVE OpenCode experiments and collecting
  batch-level result metadata.
