{ isTest, isVulnerable, isScenario ? true, hostName, isGraphics ? false, isOldKernelVM ? false, isRetrictNetwork ? true, configPath, caseDir, extraArgs ? {} }:
{ config, pkgs, lib, modulesPath, ... }:

let
  templateMinimal = import ./vm-minimal.nix {
    inherit isTest hostName isRetrictNetwork isGraphics;
  };
  # Handle both absolute paths and relative paths
  defaultConfigPath = if builtins.isPath configPath then
    configPath
  else if builtins.isString configPath then
    caseDir + "/" + configPath
  else
    caseDir + "/" + configPath;
  customConfig = if builtins.pathExists defaultConfigPath then
    import defaultConfigPath ({ inherit isTest isVulnerable isScenario isGraphics isOldKernelVM pkgs config lib modulesPath; } // extraArgs)
  else throw "NixOS configuration file ${toString defaultConfigPath} not found.";
  # Interactive lab access for historical guests that predate the NixOS test
  # framework's SSH generator. Keep it in this tracked template so Git-backed
  # case flakes always include it when the library has uncommitted changes.
  sshBackdoorConfig = { config, pkgs, lib, ... }:
    let
      hostKey = "/run/nice-archive-ssh/ssh_host_ed25519_key";
      sshConfig = pkgs.writeText "nice-archive-sshd_config" ''
        HostKey ${hostKey}
        UsePAM no
        PermitRootLogin yes
        PermitEmptyPasswords yes
        PasswordAuthentication yes
        AllowUsers root
        UseDNS no
        AuthorizedKeysFile /etc/ssh/authorized_keys.d/%u .ssh/authorized_keys
        Subsystem sftp internal-sftp
      '';
    in {
      boot.kernelModules = [ "vmw_vsock_virtio_transport" ];

      # Match the interactive test framework's passwordless lab root. Explicit
      # case credentials still take precedence over this default.
      users.users.root.initialHashedPassword = lib.mkOverride 900 "";
      users.users.sshd = {
        isSystemUser = true;
        group = "sshd";
        description = "SSH privilege separation user";
      };
      users.groups.sshd = {};

      systemd.services.nice-archive-ssh-keygen = {
        description = "Generate an ephemeral SSH host key for the interactive lab";
        wantedBy = [ "multi-user.target" ];
        before = [ "multi-user.target" ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
          RuntimeDirectory = "nice-archive-ssh";
          RuntimeDirectoryMode = "0700";
        };
        script = ''
          ${pkgs.openssh}/bin/ssh-keygen -q -t ed25519 -N "" -f ${hostKey}
        '';
      };

      systemd.sockets.nice-archive-ssh = {
        description = "Interactive lab SSH over vsock";
        wantedBy = [ "sockets.target" ];
        socketConfig = {
          ListenStream = "vsock::22";
          Accept = true;
        };
      };

      systemd.services."nice-archive-ssh@" = {
        description = "Interactive lab SSH connection";
        environment.LD_LIBRARY_PATH = config.system.nssModules.path;
        serviceConfig = {
          # Historical OpenSSH can exit 255 after a normal disconnect.
          ExecStart = "-${pkgs.openssh}/bin/sshd -i -e -f ${sshConfig}";
          StandardInput = "socket";
          StandardError = "journal";
          KillMode = "process";
        };
      };
    };
in
{
  imports =
    lib.optionals isOldKernelVM [
      ./backdoor-service.nix
    ]
    ++
    lib.optionals (isOldKernelVM && isTest && isScenario) [
      sshBackdoorConfig
    ]
    ++
    lib.optionals (!isTest || isOldKernelVM) [
      "${modulesPath}/virtualisation/qemu-vm.nix"
    ]
    ++ 
    [
      templateMinimal
      customConfig
    ];
}
