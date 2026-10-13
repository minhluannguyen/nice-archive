# 3. Design the topology and choose a generator

Decide which boundaries the vulnerability crosses before writing VM files.
Use the fewest machines that preserve its service, network, privilege, and
trust conditions. Give every VM one clear role and keep unaffected helpers
identical in both variants.

| Shape | When it fits |
| --- | --- |
| One VM | A local flaw needs no separate peer. |
| Attacker and target | The trigger crosses a host or privilege boundary. |
| Client and server | A vulnerable client consumes a controlled response, or a vulnerable server handles a client request. |
| Several services | A proxy, relay, identity provider, database, file server, or browser is part of the security path. |

Place a required intermediary on its own VM when its behavior affects the
flaw. For example, a proxy and backend should be separate if they interpret
the same request differently. Co-locate services only when that reflects the
real deployment and cannot change the security result. Write down the path
through the machines and where evidence will be checked.

Choose the generator that can represent that design:

| Need | Choice |
| --- | --- |
| Change only the affected package | `testsGenerator` with `variant = "package"`. |
| Change the target's whole NixOS pin | `testsGenerator` with `variant = "system"`. |
| Boot selected machines with an old kernel under a modern test driver | `oldKernelTestsGenerator`. |
| Apply a custom old-kernel driver change | `oldKernelNixosTest`. |
| Run an environment too old for modern NixOS tests | A documented legacy `default.nix` workflow. |

Start with `testsGenerator` whenever possible. Replace only the affected
machine when old-kernel support is needed; independent helpers can stay on a
modern pin. If a complete manual VM is needed, consult the separate
[standalone VM guide](../standalone-vms.md). The
[library reference](../nice-archive-libs.md) defines generator arguments,
variants, and outputs. For browser, graphical, and multi-service choices, see
[vulnerability-specific reproduction](../vulnerability-specific-reproduction.md).

**Previous:** [Step 2: Research and select software](./02-research-and-sources.md) · **Next:** [Step 4: Write the case entry point](./04-entry-point.md)
