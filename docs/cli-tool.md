# NICE Archive CLI

`nice-archive` lists CVE cases, runs automated tests, opens interactive VM
scenarios, launches standalone VMs, reports line counts, cleans generated
artifacts, and updates flake locks. Run it from the
repository root, where it looks for cases in `./cves/`.

## Run the CLI

On Linux, install [Nix](https://nixos.org/download.html) and enable flakes by
adding this line to `/etc/nix/nix.conf` (see the
[root README](../README.md#requirements)). KVM acceleration is recommended
when running VMs.

```ini
experimental-features = nix-command flakes
```

From the repository root, enter the development environment to get the CLI and
the packages needed to build and run cases:

```bash
nix develop
nice-archive --help
```

For automatic activation when you enter the directory, use `direnv` with
nix-direnv and the repository's `.envrc`. Allow it once:

```bash
cd /path/to/nice-archive
direnv allow
```

Outside the development environment, use `nix run . --` in place of
`nice-archive` when running commands from the repository root:

```bash
nix run . -- list-cves
```

Use `nice-archive <command> --help` to see a command's options. Running
`nice-archive` with no command shows top-level help.

## Command overview

| Command | Function |
| --- | --- |
| `start` | Open an interactive menu. |
| `list-cves` | See which CVE cases are available. |
| `loc-report` (`cve-loc-report`) | Count lines in case VM definitions and tests. |
| `cleanup` | Remove generated files from one case or all cases. |
| `test` | Check the vulnerable or fixed behavior of one case or all cases. |
| `scenario` | Explore a case's virtual machines interactively. |
| `list-vms` | See which virtual machines a case lets you launch individually. |
| `vm` | Launch one of those virtual machines. |
| `update-flakes` (`update`) | Update the saved dependency versions for one case or all cases. |

Commands that take `--case` accept a full case name, a directory path, or a
unique case-insensitive partial name. Commands that require a case prompt you
if it is omitted; `--no-prompt` makes them fail instead. `loc-report` defaults
to the current repository. Use full names in scripts. `--case` and `--all` are
mutually exclusive.

`test` and `scenario` default to `--vulnerable true`. Set it to `false` for the
fixed variant. Both support `--system SYSTEM`, which defaults to
`x86_64-linux` on Linux. Most users can leave this unchanged.

## Find cases and VMs

```bash
nice-archive list-cves
nice-archive list-vms --case cve-2022-24765-git-dubious-ownership
```

`list-cves` prints one case name per line without building it. `list-vms`
evaluates the selected case's standalone VM outputs and errors if there are
none. For legacy `default.nix` cases, it lists attributes beginning with `vm`.

## Report line counts

```bash
nice-archive loc-report
nice-archive loc-report --case cve-2014-0160-heartbleed
nice-archive loc-report /path/to/another/repository
```

With no arguments, `loc-report` scans this repository. It also accepts
`--all` to select every case here, `--case NAME` for one case, or a positional
directory containing CVE cases. It prints each case's VM count and physical
line counts for root-level VM definitions (`vm.nix`, `vm-*.nix`, and
`*-vm.nix`) and tests (`test.py` or `test.nix`), followed by the total number
of cases. Subdirectories inside a case are not counted. The interactive menu
lets you select one case or all cases.

## Clean generated artifacts

```bash
nice-archive cleanup --case cve-2014-0160-heartbleed
nice-archive cleanup --all --no-prompt
```

`cleanup` removes `*.log`, `*.qcow2`, `.nixos-test-history`, and `*result`
symlinks below the selected case directories and reports how many it removed.
Use `--case NAME` for one case or `--all` for every case. Without either, it
opens a case picker; `--no-prompt` instead requires an explicit selection.
The interactive menu offers the same one-case or all-case choices. Save any
logs you need first. Cleanup also runs automatically before `test`, `scenario`,
and `vm`.

## Run tests

```bash
nice-archive test --case cve-2014-0160-heartbleed --vulnerable true
nice-archive test --case cve-2014-0160-heartbleed --vulnerable false
nice-archive test --all --vulnerable true --no-prompt
```

The first two commands test the vulnerable and fixed variants separately.
`--all` runs the chosen variant for every available case, one after another,
and prints a pass/fail summary.

| `test` option | Effect |
| --- | --- |
| `--case NAME` | Choose one case to test. |
| `--all` | Test every available case for the chosen variant. |
| `--vulnerable true\|false` | Test the vulnerable version (default) or the fixed version. |
| `--system SYSTEM` | Choose the operating system and processor architecture to run; the Linux default is `x86_64-linux`. |
| `--refresh` | Recheck source information before a single-case test; all-case tests do this automatically. |
| `--log MODE [FILE]` | Choose whether test output is saved, shown live, or hidden. |
| `--no-prompt` | Show an error if no case was given instead of opening a selection menu. |

`--refresh` applies to cases built from a Nix flake. It refreshes Nix's source
information but does not update the case's saved dependency versions; use
`update-flakes` for that. Tests run the case's automated VM test, including
older cases that use a different test format.

Direct CLI tests default to `--log file`: the full log is saved as
`<case>/test-vulnerable-<true|false>-<system>.log`, and the last 100 lines are
printed. Other choices are:

| Logging option | Effect |
| --- | --- |
| `--log file debug.log` | Save the full log as `<case>/debug.log`; an absolute path is used as given. |
| `--log live` | Stream output; create no test log. |
| `--log none` | Suppress output; create no test log. |

The `start` menu uses `live` for one case and `none` for all cases. A custom
filename is only valid with `--log file`.

## Open a scenario

```bash
nice-archive scenario --case cve-2020-7247-opensmtpd --vulnerable true --popup false
```

`scenario` starts the selected variant's VMs and attaches your terminal to the
interactive Python test driver. It prints SSH commands for the guests so you
can use another terminal to inspect them. Within the driver, VM objects are
named by the case; for a `server` VM, `server.succeed("id")` runs a command in
that guest. Exit with `Ctrl+D` and choose to kill the VMs.

| `scenario` option | Effect |
| --- | --- |
| `--case NAME` | Choose the case to explore. |
| `--vulnerable true\|false` | Start the vulnerable environment (default) or the fixed one. |
| `--system SYSTEM` | Choose the operating system and processor architecture to run. |
| `--popup true\|false` | Open a separate terminal window for each VM (default `true`), or leave them closed. |
| `--no-prompt` | Show an error if no case was given instead of opening a selection menu. |

Popup windows use `terminator`; with `--popup false`, use the printed SSH
commands or the interactive driver to reach each VM.

The CLI serializes scenarios with `./.nice-archive-scenario.lock`. Set
`NICE_ARCHIVE_SCENARIO_LOCK` to another path to change the lock, or to `0` to
disable it. The case must provide an interactive scenario output.

## Launch a standalone VM

```bash
nice-archive vm --case cve-2022-24765-git-dubious-ownership --name server-vulnerable
```

`vm` lists the selected case's standalone outputs, then launches one VM.
`--name` (also `--vm-name`) selects it; without a name, the CLI prompts. With
`--no-prompt`, supply both `--case` and `--name`. A unique case-insensitive
partial VM name also works. The CLI prints `Ctrl+A`, then `X` as the exit
sequence. Use `scenario` when you need the case's full connected VM topology.

## Update flake locks

```bash
nice-archive update-flakes --case cve-2014-0160-heartbleed
nice-archive update-flakes --all --no-prompt
```

`update-flakes`, or its `update` alias, runs `nix flake update` in selected
flake-backed cases. `--all` skips `default.nix`-only cases. This can change
dependency versions and case behavior, so review lockfile changes and rerun
both test variants afterward.

## Side effects and safety

Before each `test`, `scenario`, or `vm` run, the CLI removes generated case
artifacts: `*.log`, `*.qcow2`, `.nixos-test-history`, and `*result` symlinks.
Save any logs you need before starting another run. Flake-backed `test` and
`scenario` also run `git add` on the selected case so Nix can see new files;
review the staged diff afterward.

Tests, scenarios, and VMs run case-defined software. Keep vulnerable targets
and triggers inside the intended VM lab; follow the
[isolation guidance](./reporting-vulnerabilities.md#isolation-gate). For case
outputs and VM design, see the [library reference](./nice-archive-libs.md).
