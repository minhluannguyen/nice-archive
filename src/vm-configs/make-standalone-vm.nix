{ configPath, extraArgs ? {}, nixpkgs, system ? "x86_64-linux" }:

let
  mkVm = import "${nixpkgs}/nixos" {
    configuration = import configPath (extraArgs // { isTest = false; });
    inherit system;
  };
in
{
    vm = mkVm.vm;
}