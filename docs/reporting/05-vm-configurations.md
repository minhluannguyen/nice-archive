# 5. Writing VMs configuration

Write a configuration for each distinct VM role. The target VM contains the
affected package, its service and prerequisites, and target-only fixtures.
Attacker or helper VMs contain only the tools and services needed to deliver
the trigger or observe evidence. Keep helper configurations invariant between
the vulnerable and fixed tests.

## Connect a role to its module

In the case entry point, each `VMs` role names its configuration file. A
package variant can pass the two already selected packages into that file:

```nix
VMs.server = {
  configPath = ./vm-server.nix;
  variant = "package";
  extraArgs = {
    inherit vulnerablePackage fixedPackage;
  };
};
```

The package expressions and exact `extraArgs` contract are documented in the
[library reference](../nice-archive-libs.md#vm-configuration-function-shape).
Resolve and verify the packages first, as described in
[step 2](./02-research-and-sources.md).

## Target VM example

The first function receives NICE Archive values such as `isVulnerable` and
`extraArgs`; the second is the NixOS module. Replace the package's executable
name, service arguments, and port with the real target's requirements:

```nix
{ isVulnerable, vulnerablePackage, fixedPackage, ... }:
{ ... }:
let
  targetPackage = if isVulnerable then vulnerablePackage else fixedPackage;
in {
  environment.systemPackages = [ targetPackage ];
  networking.firewall.allowedTCPPorts = [ 8080 ];

  systemd.services.target = {
    wantedBy = [ "multi-user.target" ];
    serviceConfig.ExecStart = "${targetPackage}/bin/target --port 8080";
  };

  environment.etc."nice-archive/variant".text =
    if isVulnerable then "vulnerable\n" else "fixed\n";
  environment.etc."nice-archive/target-secret".text =
    "NICE-CVE-YYYY-NNNN-TARGET-SECRET\n";
}
```

The variant file gives `test.py` an explicit branch selector; the generator
does not create one automatically. The target-only secret is a guest fixture
for an information-disclosure oracle. Use a different case-specific marker
when the security effect is a file write, privilege change, or crash. Make
sure the attacker cannot read the marker through an unrelated channel.

## Attacker VM example

Install a bounded trigger as a guest command and keep its source under the
role that runs it:

```nix
{ ... }:
{ pkgs, ... }:
let
  trigger = pkgs.writeShellScriptBin "run-trigger" ''
    exec ${pkgs.python3}/bin/python3 ${./exploit/attacker/trigger.py} "$@"
  '';
in {
  environment.systemPackages = [ trigger ];
}
```

Mark this VM `variant = "invariant"` in the entry point when its configuration
does not change. Install a separate service, such as a controlled response
server or evidence logger, only when the vulnerability needs that role. For
examples of distinct target, browser, and logger VMs, inspect the
[Bleach XSS configuration](../../cves/cve-2021-23980-bleach-mutation-xss/flake.nix)
and its [target module](../../cves/cve-2021-23980-bleach-mutation-xss/vm-server.nix).

Use guest-only credentials and fixture values. NixOS does not guarantee
executables under `/bin`, `/usr/bin`, or `/usr/local/bin`; use the package's
Nix store path or `/run/current-system/sw/bin/` in guest commands. Keep
standalone-only port forwarding out of test and scenario VMs; see the
[standalone VM guide](../standalone-vms.md) when manual wiring is necessary.

## Check NixOS options against the VM pin

Use `nixos-option` to inspect service settings, and record the queried NixOS
release and revision alongside the result:

```bash
nixos-option system.nixos.release
nixos-option system.nixos.revision
nixos-option services.nginx
nixos-option services.nginx.enable
```

These commands query the selected local configuration, not automatically the
case's VM. Compare that revision with the VM's module-system pin. If they
differ, inspect and evaluate the option at the VM's revision before using it;
a historical package pin alone does not change NixOS module options.

**Previous:** [Step 4: Write the case entry point](./04-entry-point.md) · **Next:** [Step 6: Use scenario mode to test exploitation](./06-scenario-mode.md)
