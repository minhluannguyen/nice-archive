{ pkgs, oldKernelVMs, testBase, isInteractive ? false, ... }:
let
  mkPair = name: drv:
    "[${name}]=\"${drv.vm}/bin/run-${name}-vm\"";
  arrBody = pkgs.lib.concatStringsSep "\n  " (pkgs.lib.mapAttrsToList mkPair oldKernelVMs);

in
pkgs.runCommand "nixos-old-kernel-test" { } ''
  outBin=$out/bin
  mkdir -p "$outBin"

  driverPath=$outBin/nixos-test-driver
  cp ${if isInteractive then testBase.driverInteractive else testBase.driver}/bin/nixos-test-driver "$driverPath"
  chmod +xw "$driverPath"

  startScripts=$(grep '^export startScripts=' "$driverPath" | sed -E "s/export startScripts=['\"]([^'\"]*)['\"]/\\1/")

  declare -a newScripts
  idx=1

  declare -A oldVM=(
    ${arrBody}
  )

  # Process every VM script in the list
  for orig in $startScripts; do
    base=$(basename "$orig")             # e.g. run-nfsserver-vm
    machine=$(echo "$base" | sed -E 's/^run-(.*)-vm$/\1/')

    # Pick the old-kernel run script that matches this machine
    # (fall back to the original if none supplied)

    if [[ -n "''${oldVM[$machine]}" ]]; then
        src="''${oldVM[$machine]}"
    else
        src="$orig"
    fi

    dst="$outBin/$base"
    cp "$src" "$dst"
    chmod +xw "$dst"

    # Copy the 'exec …’ and '-net nic …’ lines from the ORIGINAL script,
    # because they contain the right disk image paths, etc.
    execLine=$(sed -n 's/.*\(exec.*\)/\1/p'  "$orig")
    netLine=$(sed  -n 's/.*\(-net nic.*\)/\1/p' "$orig")

    # Escape slashes so we can feed the lines to sed safely.
    escExec=$(printf '%s\n' "$execLine" | sed 's:[\\/&]:\\&:g')
    escNet=$(printf  '%s\n' "$netLine"  | sed 's:[\\/&]:\\&:g')

    sed -i "s/-nographic//g" "$dst"
    sed -i "s#^exec.*#''${escExec}#" "$dst"
    sed -i "s#-net nic.*#''${escNet}#" "$dst"

    # Add virtio-net for this VM - socket name follows the loop index.
    sed -i "s|\\(\$QEMU_OPTS\\)|-device virtio-net-pci,netdev=vlan1,mac=52:54:00:12:01:0''${idx} -netdev vde,id=vlan1,sock=\"\$QEMU_VDE_SOCKET_1\" \\1|" "$dst"

    newScripts+=("$dst")
    idx=$((idx + 1))

    echo $dst >&2
  done

  # 3. Re-inject the rewritten list into the driver
  printf -v joined '%s ' "''${newScripts[@]}"
  sed -i "s#^export startScripts=.*#export startScripts=\"''${joined% }\"#" "$driverPath"

  echo "Patched driver and VM scripts written to $out" >&2
''