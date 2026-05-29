{pkgs, oldKernelVM, test, machine_name, ...}:

pkgs.runCommand "nixos-old-kernel-test" { } 
''
    machinePath=$out/bin/run-${machine_name}-vm
    driverPath=$out/bin/nixos-test-driver

    mkdir -p $out/bin
    cp ${oldKernelVM.vm}/bin/run-*-vm $machinePath
    cp ${test.driver}/bin/nixos-test-driver $driverPath

    chmod +xw $machinePath
    chmod +xw $driverPath
    
    startScriptPath=$(grep '^export startScripts=' $driverPath | sed -E "s/export startScripts=['\"]([^'\"]*)['\"]/\\1/")
    execPath=$(sed -n 's/.*\(exec.*\)/\1/p' "$startScriptPath")
    netPath=$(sed -n 's/.*\(-net nic.*\)/\1/p' "$startScriptPath")

    escapedExecPath=$(printf '%s\n' "$execPath" | sed 's/[\/&]/\\&/g')
    escapedNetPath=$(printf '%s\n' "$netPath" | sed 's/[\/&]/\\&/g')

    sed -i "s#^export startScripts=.*#export startScripts=\"$machinePath\"#" $driverPath

    sed -i 's/-nographic//g' $machinePath
    sed -i "s/^exec.*/$escapedExecPath/" $machinePath
    sed -i "s/-net nic.*/$escapedNetPath/" $machinePath

    sed -i "s/\(\$QEMU_OPTS\)/-device virtio-net-pci,netdev=vlan1,mac=52:54:00:12:01:01 -netdev vde,id=vlan1,sock=\"\$QEMU_VDE_SOCKET_1\" \1/" $machinePath

    echo "Output stored in: $out" >&2
    
    #$out/bin/nixos-test-driver
''