# 1. Create or find the case

First confirm the affected behavior applies to Linux, can run in a suitable
isolated Linux lab, and admits a machine-checkable Linux-side oracle. If it
does not, do not create a case. Search `cves/` before creating a directory.
Complete an existing case in place and verify its current claims rather than
assuming they are correct.

Name a new directory `cves/cve-yyyy-nnnn-short-lowercase-description/`. The
directory name is the `--case` value used by the CLI. Keep `flake.nix` (or a
legacy `default.nix`), `test.py`, the case README, and VM configuration files
at the case root. Put trigger artifacts under `exploit/<role>/`, where the role
is the VM that consumes them. Use `package/` only for complex packaging
expressions. Create directories when they are needed, not as placeholders.

For example, a two-role case might start as:

```text
cves/cve-yyyy-nnnn-short-name/
├── flake.nix
├── vm-server.nix
├── vm-attacker.nix
├── test.py
├── README.md
└── exploit/attacker/trigger.py
```

**Previous:** [Workflow overview](../reporting-vulnerabilities.md) · **Next:** [Step 2: Research and select software](./02-research-and-sources.md)
