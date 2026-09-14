{ pkgs, runtimePackages, opencodePkgs, sourceRoot }:
let
  runtimePath = pkgs.lib.makeBinPath (
    runtimePackages ++ [ pkgs.git opencodePkgs.opencode ]
  );
in
pkgs.writeShellScriptBin "cve-orchestrator" ''
  export PATH=${runtimePath}:$PATH

  if [ -f "$PWD/otool/cve-orchestrator.py" ]; then
    exec ${pkgs.python312}/bin/python "$PWD/otool/cve-orchestrator.py" "$@"
  fi

  exec ${pkgs.python312}/bin/python ${sourceRoot}/otool/cve-orchestrator.py "$@"
''
