{
  description = "NICE Archive's Library for reproducing CVEs";

  outputs = { self }:
  {
    standaloneVMGenerator = import ./standalone-vm-generator.nix;
    testsGenerator = import ./tests-generator.nix;
    oldKernelNixosTest = import ./test-configs/nixos-test-old-kernel.nix;
  };
}
