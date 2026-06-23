{ isTest, hostName, isRetrictNetwork ? true, isGraphics }:
{ pkgs, lib, ... }:

let
  
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
// lib.optionalAttrs (isGraphics != null) {
  virtualisation.graphics = isGraphics;
}
// lib.optionalAttrs (isRetrictNetwork != null) {
  virtualisation.restrictNetwork = isRetrictNetwork;
}
