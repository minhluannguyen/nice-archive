{ pkgs, oldKernelVMs, testBase, isInteractive ? false, ... }:
let
  mkPair = name: drv:
    "[${name}]=\"${drv.vm}/bin/run-${name}-vm\"";
  arrBody = pkgs.lib.concatStringsSep "\n  " (pkgs.lib.mapAttrsToList mkPair oldKernelVMs);
  graphicsBody = pkgs.lib.concatStringsSep "\n  " (pkgs.lib.mapAttrsToList
    (name: drv: "[${name}]=${if drv.config.virtualisation.graphics then "true" else "false"}")
    oldKernelVMs);

in
pkgs.runCommand "nixos-old-kernel-test" { 
  meta.mainProgram = "nixos-test-driver";
 } ''
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
  declare -A oldGraphics=(
    ${graphicsBody}
  )

  # Process every VM script in the list
  for orig in $startScripts; do
    base=$(basename "$orig")             # e.g. run-nfsserver-vm
    machine=$(echo "$base" | sed -E 's/^run-(.*)-vm$/\1/')

    # Pick the old-kernel run script that matches this machine
    # (fall back to the original if none supplied)

    if [[ -n "''${oldVM[$machine]:-}" ]]; then
        src="''${oldVM[$machine]}"
    else
        src="$orig"
    fi

    dst="$outBin/$base"
    cp "$src" "$dst"
    chmod +xw "$dst"

    # Keep invariant modern helpers intact, including graphics and SSH wiring.
    if [[ -z "''${oldVM[$machine]:-}" ]]; then
      newScripts+=("$dst")
      idx=$((idx + 1))
      continue
    fi

    # Use the base driver's QEMU binary and user-network settings, while
    # retaining the historical guest's kernel, initrd and disk arguments.
    execLine=$(sed -n 's/.*\(exec.*\)/\1/p'  "$orig")
    netLine=$(sed  -n 's/.*\(-net nic.*\)/\1/p' "$orig")

    # Escape slashes so we can feed the lines to sed safely.
    escExec=$(printf '%s\n' "$execLine" | sed 's:[\\/&]:\\&:g')
    escNet=$(printf  '%s\n' "$netLine"  | sed 's:[\\/&]:\\&:g')

    # The driver supplies serial and monitor connections itself. Disable only
    # the display, without -nographic's implicit serial/monitor redirection.
    if [[ "''${oldGraphics[$machine]}" == false ]]; then
      sed -i "s/-nographic/-display none/g" "$dst"
    else
      sed -i "s/-nographic//g" "$dst"
    fi
    sed -i "s#^exec.*#''${escExec}#" "$dst"
    sed -i "s#-net nic.*#''${escNet}#" "$dst"

    ${pkgs.lib.optionalString isInteractive ''
      # Preserve the exact CID advertised by the copied driver; it depends on
      # the full node list, including helpers that were not replaced.
      vsockLine=$(grep -E '^[[:space:]]*-device vhost-vsock-pci,guest-cid=[0-9]+' "$orig")
      if [[ -z "$vsockLine" ]]; then
        echo "Missing base-driver vsock device for $machine" >&2
        exit 1
      fi
      if grep -q 'vhost-vsock-pci' "$dst"; then
        echo "Old VM $machine already defines a vsock device" >&2
        exit 1
      fi
      # Insert before QEMU_OPTS so the copied continuation line stays valid.
      printf '%s\n' "$vsockLine" > vsock-line
      sed -i '/\$QEMU_OPTS/e cat vsock-line' "$dst"
    ''}

    # Add virtio-net for this VM when the base script does not already carry
    # the test VLAN. Multi-node tests already have this wiring in their
    # generated run scripts.
    if ! grep -q 'netdev=vlan1' "$dst"; then
      sed -i "s|\\(\$QEMU_OPTS\\)|-device virtio-net-pci,netdev=vlan1,mac=52:54:00:12:01:0''${idx} -netdev vde,id=vlan1,sock=\"\$QEMU_VDE_SOCKET_1\" \\1|" "$dst"
    fi

    newScripts+=("$dst")
    idx=$((idx + 1))

    echo $dst >&2
  done

  # 3. Re-inject the rewritten list into the driver
  printf -v joined '%s ' "''${newScripts[@]}"
  sed -i "s#^export startScripts=.*#export startScripts=\"''${joined% }\"#" "$driverPath"

  echo "Patched driver and VM scripts written to $out" >&2
''
