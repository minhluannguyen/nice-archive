---
name: prompt-interaction
description: Control a genuinely interactive NICE Archive CLI or guest SSH prompt with bounded expect or pexpect operations.
---

# Prompt interaction

Use non-interactive CLI flags and guest commands when available. Use
`pexpect` (Python) or `expect` (Tcl) only when a command genuinely requires
a TTY or a prompt response. Declare the script interpreter and spawn the
specific CLI or guest SSH command; never spawn a vulnerable target or trigger
on the host.

Set a finite timeout for spawn, each prompt match, each read, and shutdown.
Match a known prompt or EOF before sending the next response. On an unexpected
prompt or timeout, capture a bounded diagnostic tail, interrupt the owned
process, and report failure. Do not wait for a shell prompt indefinitely.

For manual labs, keep `nice-archive scenario` in a managed session and run
guest commands through its test-driver methods or the printed guest SSH
command. The [CLI guide](../../../cli-tool.md#open-a-scenario) defines its
actual prompts and exit sequence; do not assume runner-specific PTY controls
are NICE Archive CLI flags.
