{
  description = "NICE Archive's Library for reproducing CVEs";

  outputs = { self }:
  {
    standaloneVMGenerator = import ./standalone-vm-generator.nix;
    testsGenerator = import ./tests-generator.nix;
    oldKernelTestGenerator = import ./old-kernel-test-generator.nix;
  };
}
