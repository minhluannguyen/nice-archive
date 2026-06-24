{ isTest, hostName, isRetrictNetwork ? true, isGraphics }:
{ pkgs, lib, ... }:

let
  virtualisationOptions =
    lib.optionalAttrs (isGraphics != null) {
      graphics = lib.mkForce isGraphics;
    }
    // lib.optionalAttrs (isRetrictNetwork != null) {
      restrictNetwork = isRetrictNetwork;
    };
in
{
  system.stateVersion = "24.09";

  networking.hostName = hostName;

  environment.systemPackages = with pkgs; [
    bashInteractive
    coreutils
  ];

  users.users.root = {
    isSystemUser = true;
    password = if !isTest then "root" else null;
  };
}
// lib.optionalAttrs (virtualisationOptions != {}) {
  virtualisation = virtualisationOptions;
}
