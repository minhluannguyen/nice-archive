# NICE Archive

NICE Archive is a collection of reproducible NixOS virtual machines and NixOS
integration tests for CVE reproductions. Each CVE case lives under
[`cves/`](./cves/) and contains the Nix, VM, exploit, and test files needed to
rebuild the experiment.

The project also includes a small CLI, `nice-archive`, and reusable library
generators under [`src/`](./src/) for creating consistent vulnerable/fixed
test scenarios.

## Repository layout

```text
.
├── cves/                  # One directory per CVE reproduction
├── docs/                  # Project documentation
├── src/                   # NICE Archive Nix libraries and Python assertions
├── nice-archive.py        # CLI implementation
├── nice-archive           # Local wrapper for the CLI
├── cleanup-script.sh      # Removes generated VM/test artifacts
├── cve-loc-report.sh      # Helper script for rough CVE size reports
└── flake.nix              # Development shell and CLI app
```

Start with [`docs/README.md`](./docs/README.md) for the documentation table of
contents.

## Requirements

- [Nix](https://nixos.org/download.html)
- Nix flakes enabled
- QEMU available on the host
- KVM acceleration recommended for practical VM performance
- Optional: [direnv](https://direnv.net/) with nix-direnv

Enable flakes in `/etc/nix/nix.conf`:

```text
experimental-features = nix-command flakes
```

## Development shell

Enter the project shell:

```bash
nix develop
```

The shell provides the Python dependencies and runtime tools used by the CLI.

With direnv:

```bash
cd /path/to/nice-archive
direnv allow
```

After that, entering the repository loads the same environment automatically.

## CLI quick start

Run CLI commands from the repository root.

With the development shell active:

```bash
nice-archive list-cves
```

Without entering the shell:

```bash
nix run . -- list-cves
```

The examples below use `nice-archive`. If you are outside the development
shell, replace `nice-archive` with `nix run . --`.

### List CVE cases

```bash
nice-archive list-cves
```

### Run automated tests

Run one vulnerable test:

```bash
nice-archive test \
  --case cve-2025-32463-chwoot \
  --vulnerable true
```

Run the fixed/non-vulnerable variant:

```bash
nice-archive test \
  --case cve-2025-32463-chwoot \
  --vulnerable false
```

Run all vulnerable or fixed tests:

```bash
nice-archive test --all --vulnerable true
nice-archive test --all --vulnerable false
```

By default, CLI test runs save the full log in the case directory and print
only the last 100 lines.

Logging modes:

```bash
# Save the full log with the default generated filename.
nice-archive test --case cve-2025-32463-chwoot --log file

# Save the full log using a custom filename inside the case directory.
nice-archive test --case cve-2025-32463-chwoot --log file debug.log

# Print the Nix/test output live and do not create a log file.
nice-archive test --case cve-2025-32463-chwoot --log live

# Suppress test output and do not create a log file.
nice-archive test --case cve-2025-32463-chwoot --log none
```

Add `--refresh` to pass `--refresh` to `nix run`.

### List and run standalone VMs

Some cases expose manually runnable VMs through `standaloneVMs`.

```bash
nice-archive list-vms --case cve-2025-32463-chwoot
nice-archive vm --case cve-2025-32463-chwoot --name server
```

Use `--no-prompt` in scripts to fail instead of opening interactive prompts
when required values are missing.

### Update flake locks

```bash
nice-archive update-flakes --case cve-2025-32463-chwoot
nice-archive update-flakes --all
```

## Interactive helper

The interactive helper can be started with `nice-archive start`;

### Menu helper

```bash
nice-archive start

   .      .                                                                                             .      .   
   _\/  \/_    ███╗   ██╗██╗ ██████╗███████╗     █████╗ ██████╗  ██████╗██╗  ██╗██╗██╗   ██╗███████╗    _\/  \/_   
    _\/\/_     ████╗  ██║██║██╔════╝██╔════╝    ██╔══██╗██╔══██╗██╔════╝██║  ██║██║██║   ██║██╔════╝     _\/\/_    
_\_\_\/\/_/_/_ ██╔██╗ ██║██║██║     █████╗      ███████║██████╔╝██║     ███████║██║██║   ██║█████╗   _\_\_\/\/_/_/_
 / /_/\/\_\ \  ██║╚██╗██║██║██║     ██╔══╝      ██╔══██║██╔══██╗██║     ██╔══██║██║╚██╗ ██╔╝██╔══╝    / /_/\/\_\ \ 
    _/\/\_     ██║ ╚████║██║╚██████╗███████╗    ██║  ██║██║  ██║╚██████╗██║  ██║██║ ╚████╔╝ ███████╗     _/\/\_    
    /\  /\     ╚═╝  ╚═══╝╚═╝ ╚═════╝╚══════╝    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝     /\  /\    
   '      '                                                                                             '      '   
    
? What would you like to do? (Use arrow keys)
 → Start interactive scenario
   Run tests
   Run standalone VM machines
   Update flakes for CVE cases
   Exit

```

The menu lets you select a CVE case and then:

- start an interactive scenario;
- run tests;
- run standalone VMs; or
- update flake locks.

### Scenario helper

The scenario helper is the preferred debugging interface for multi-VM tests:

```bash
nice-archive scenario \
  --case cve-2025-32463-chwoot \
  --vulnerable true \
  --popup false
```

This will run the interactive mode of the NixOS test driver and automatically start the VMs. After the VMs are running, some VM windows will be opened for the user to interact with the VMs.

The user can also interact with the VMs through the test driver terminal. Some common commands are:

```python
start_all()
server.wait_for_unit("multi-user.target")
server.succeed("id")
server.succeed("journalctl -u <unit> --no-pager")
```

Exit the scenario with `Ctrl+D` in the scenario terminal and choose to kill the
VMs.

Note: the `test` and `scenario` commands run `git add <case-dir>` before
invoking flake outputs so that newly created files are visible to Nix's
Git-backed flake evaluation. Review `git status` before committing.

## Direct Nix usage

The CLI is recommended because it knows the modern output names and legacy
fallbacks. Direct Nix commands are still useful when debugging a case.

Modern library-backed cases expose outputs like:

```bash
cd cves/<case>

nix run .#test-vulnerable-true-x86_64-linux
nix run .#test-vulnerable-false-x86_64-linux
nix run .#start-scenario-vulnerable-true-x86_64-linux
nix run .#standaloneVMs.<vm-name>
```

Some older cases still expose legacy names such as:

```bash
nix run .#testVulnerableTrue
nix run .#testVulnerableFalse
```

If an output name fails, inspect the case's `flake.nix` or use the CLI first.

## Documentation

- [Documentation index](./docs/README.md)
- [NICE Archive library reference](./docs/nice-archive-libs.md)
- [Reporting a vulnerability with NICE Archive](./docs/reporting-vulnerabilities.md)

The library reference documents `testsGenerator`, `standaloneVMGenerator`,
`oldKernelTestsGenerator`, graphical/OCR flags, old-kernel compatibility, and
Python assertion helpers.

The reporting guide is the recommended workflow for adding or updating a CVE
case.

## Cleaning generated artifacts

Test and VM runs can create `result` symlinks, `*.qcow2` disk images, and
`.nixos-test-history` files.

Clean all CVE cases:

```bash
./cleanup-script.sh cves
```

Clean one case:

```bash
./cleanup-script.sh cves/cve-2025-32463-chwoot
```

## Troubleshooting

### `flake ... does not provide attribute ...`

The case may use modern generated names, legacy names, or standalone nested
outputs. Prefer the CLI first:

```bash
nice-archive test --case <case> --vulnerable true
nice-archive list-vms --case <case>
```

### New files are missing from Nix evaluation

Nix flakes sourced from Git only include files visible to Git. Add new case
files to the index or use the CLI commands that stage the selected case before
running tests and scenarios.

### Port conflicts

Some VMs forward host ports. If a port is already in use, edit the relevant
`vm-*.nix` file and change `virtualisation.forwardPorts`.

### GUI or OCR tests fail

Graphical tests normally need:

- `isGraphics = true` on the graphical VM; and
- `enableOCR = true` in the generator when using OCR assertions.

See the library reference for details.