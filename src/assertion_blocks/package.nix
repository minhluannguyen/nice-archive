{ pkgs, pythonPackages ? pkgs.python3Packages }:

let
  # Create proper package structure for setuptools
  # setuptools expects the package directory to be a subdirectory of the source root
  assertion_blocks_src = pkgs.runCommand "assertion-blocks-src" {
    src = ./.;
  } ''
    mkdir -p $out/assertion_blocks
    cp -r $src/* $out/assertion_blocks/
    touch $out/assertion_blocks/py.typed
    mv $out/assertion_blocks/pyproject.toml $out/
    cat > $out/setup.py <<'PY'
    from setuptools import find_packages, setup

    setup(
        name="assertion_blocks",
        version="1.0",
        packages=find_packages(),
        package_data={"assertion_blocks": ["py.typed"]},
    )
    PY
  '';
in
pythonPackages.buildPythonPackage {
  pname = "assertion-blocks";
  version = "1.0";
  src = assertion_blocks_src;
  pyproject = true;
  build-system = [ pythonPackages.setuptools ];
  nativeBuildInputs =
    [ pythonPackages.setuptools ]
    ++ pkgs.lib.optionals (pythonPackages ? wheel) [ pythonPackages.wheel ];
  doCheck = false;
  pythonImportsCheck = [];
}
