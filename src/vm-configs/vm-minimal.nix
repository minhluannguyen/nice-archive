{ isTest, hostName, isRetrictNetwork ? true }:
{ pkgs, lib, ... }:

let
  
in
{
  system.stateVersion = "24.09";

  virtualisation.graphics = false;

  virtualisation.restrictNetwork = isRetrictNetwork;

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
