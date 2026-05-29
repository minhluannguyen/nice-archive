## NICE Framework implementation

### Overview

This repository contains a collection of **reproducible NixOS virtual machines and NixOS integration tests** for CVEs. Each CVE is organized in its own folder under `cves/` and contains the Nix expressions needed to rebuild the environments used in the experiments. Consult the individual CVE README files for specific instructions on how to build and run the VMs and tests.

### Repo layout

- `cves/`: one folder per CVE
- `cleanup-script.sh`: deletes generated `*.qcow2` disk images and `result` symlinks under `cves/`

### Requirements

- [Nix package manager](https://nixos.org/download.html)
- Flakes enabled
- QEMU available on the host; KVM acceleration recommended

Enable flakes by adding the following lines to `/etc/nix/nix.conf`:

```
experimental-features = nix-command flakes
```

See upstream docs: https://wiki.nixos.org/wiki/Flakes

### Build & usage (reproducing experiments)

Each CVE directory typically contains a `flake.nix` exposing one or more outputs. Output names vary per CVE, so first inspect the available outputs.

#### 1) Inspect flake outputs

```bash
cd cves/<cve-directory>
nix flake show
```

Common outputs:

- `vm` (or `vmServer`, `vmClient`, …): build a runnable NixOS VM image
- `testVulnerableTrue` / `testVulnerableFalse`: build an integration test closure

#### 2) Build and run a standalone VM

If the flake provides `vm`:

```bash
cd cves/<cve-directory>
nix build .#vm
ls -la result/bin
./result/bin/run-*-vm
```

If the CVE exposes multiple VMs (e.g. `vmServer` / `vmClient`), build that output and run the corresponding `result/bin/run-…` launcher.
For CVEs that do not use flakes, refer to their individual README files for instructions.

Note: Flake requires to be a git repository, and files need to be tracked by git to be included in the build. 

#### 3) Build and run a NixOS integration test

If the flake provides a test output (commonly `testVulnerableTrue`):

```bash
cd cves/<cve-directory>
nix build .#testVulnerableTrue.driver
./result/bin/nixos-test-driver
# or 
nix build .#testVulnerableTrue -L
```

The test driver boots the VM(s) listed under `nodes = { ... }` in the `*test*.nix` file and then executes the Python `testScript`.

#### Interactive mode (recommended for debugging)

To start an interactive test driver session, build and run:
```bash
cd cves/<cve-directory>
nix build .#testVulnerableTrue.driverInteractive
./result/bin/nixos-test-driver --interactive
```
This starts an interactive Python REPL that has the node objects (e.g. `server`, `client`, `attacker`) already created and wired up. This means the test framework **automatically builds and bootstraps the VMs** for you—no need to manually run individual `run-*-vm` scripts.

Common interactive workflow:

- Boot all nodes: `start_all()`
- Wait for a unit: `<node>.wait_for_unit("multi-user.target")`
- Run a command in a node: `<node>.succeed("id")` (or `.fail(...)`)
- Inspect logs: `<node>.succeed("journalctl -u <unit> --no-pager")`

#### QEMU GUI popup vs headless (graphics toggle)

Whether QEMU windows pop up is controlled by the node VM configuration (usually in a `*-vm*.nix` file) via `virtualisation.graphics`:

- `virtualisation.graphics = true;` (or leaving it at the default) may open a QEMU display window for the node.
- `virtualisation.graphics = false;` forces headless mode; you interact via the test driver interface (serial console / command execution).

If you prefer debugging inside a visible VM window, set `virtualisation.graphics = true;` for the node(s). If you’re running in CI or want fully automated runs, or want to keep things in the terminal, keep it `false`.

### End-to-end example: CVE-2014-0160 (Heartbleed)

```bash
cd cves/cve-2014-0160-heartbleed

# Vulnerable configuration
nix build .#testVulnerableTrue
./result/bin/nixos-test-driver

# Non-vulnerable configuration
nix build .#testVulnerableFalse
./result/bin/nixos-test-driver

# Optional: standalone VM
nix build .#vm
ls -la result/bin
./result/bin/run-*-vm
```

### Cleaning up generated artifacts

Some runs create `result` symlinks and/or QEMU disk images (`*.qcow2`) under `cves/`.

```bash
./cleanup-script.sh
```

### Troubleshooting

- **“flake … does not provide attribute …”**
  Run `nix flake show` inside the CVE directory and use one of the outputs shown there (many CVEs use `testVulnerableTrue` rather than a generic `test`).

- **Port-forward conflicts / privileged ports**
  Some VMs forward privileged ports (e.g. 23). If that conflicts on your host, edit the relevant `*-vm*.nix` and change `virtualisation.forwardPorts` to a higher host port (e.g. 2323) or use `sudo`.

- **“Git tree is dirty” warnings**
  Expected when local changes exist; it doesn’t impact reproducibility.

### References

- [Nix Manual](https://nixos.org/manual/nix/)
- [nixos-generators](https://github.com/nix-community/nixos-generators)