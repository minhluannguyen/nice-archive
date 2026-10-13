# 6. Use scenario mode to test exploitation

Manually run the security-relevant trigger before writing the automated test.
Establish the VM or container boundary first and confirm that the target and
trigger commands run inside it. Use only lab fixtures and secrets; do not aim
at unrelated services or public systems.

## Use the NICE Archive CLI

Run CLI commands from the repository root. Confirm that the case is
discoverable before starting its lab:

```bash
nice-archive list-cves
```

The CLI can start scenarios, run both test variants, list standalone VMs,
and update flake locks. Its [guide](../cli-tool.md) explains command options,
logging, and exit status. `scenario` and `test` stage the selected case for
Git-backed flake evaluation, so inspect the Git index afterward. Use direct
Nix commands only for operations the CLI does not support or for diagnosis.

## Use an interactive scenario

The scenario command starts the VMs for one variant and attaches an
interactive NixOS test-driver session:

```bash
nice-archive scenario --case cve-yyyy-nnnn-short-name --vulnerable true --popup false
```

You can also use the interactive version of the CLI to start the scenario mode.

Once ready, it prints SSH commands for each guest. Keep the scenario terminal
open and use a printed SSH command from another terminal, or use the named VM
objects in the test-driver prompt for bounded checks. Exit the driver with
`Ctrl+D` and choose to stop the VMs. The [CLI guide](../cli-tool.md#open-a-scenario)
explains popup windows, locking, and command options.

## Observe the security effect

1. Confirm the target package and required services are ready.
2. Run the bounded trigger from the correct role VM.
3. Collect evidence where the security effect occurs: target file, process,
   privilege, service state, log, or original target-only secret.
4. Start the fixed scenario with `--vulnerable false` and repeat the identical
   trigger.
5. Confirm that the effect is absent and the fixed target remains healthy.

Keep the sequence simple enough to translate into the automated test in the
[next step](./07-test.md). Record exact guest commands and observations for the
case README. If the scenario is unavailable, follow the separate
[standalone VM guide](../standalone-vms.md) and document the manual network
wiring. Scenario and automated-test VMs use their lab network; host port
forwarding is only for standalone VM wiring.

An exploit hang, VM timeout, or killed process is a failed or blocked run,
not proof that the fixed version is safe. Collect diagnostics and repeat
only after the cause is understood. Additional browser, graphical, kernel,
and multi-service patterns are in
[vulnerability-specific reproduction](../vulnerability-specific-reproduction.md).

**Previous:** [Step 5: Writing VMs configuration](./05-vm-configurations.md) · **Next:** [Step 7: Write the automated test](./07-test.md)
