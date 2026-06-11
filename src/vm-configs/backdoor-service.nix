{ pkgs, ... }:

let 
    qemu-common = {
        qemuSerialDevice = "ttyS0";
    };
in 
{
    boot.kernelParams = [
        "console=${qemu-common.qemuSerialDevice}"
        "console=tty0"
        # Panic if an error occurs in stage 1 (rather than waiting for
        # user intervention).
        "panic=1"
        "boot.panic_on_fail"
        # Using acpi_pm as a clock source causes the guest clock to
        # slow down under high host load.  This is usually a bad
        # thing, but for VM tests it should provide a bit more
        # determinism (e.g. if the VM runs at lower speed, then
        # timeouts in the VM should also be delayed).
        "clocksource=acpi_pm"
    ];

    boot.consoleLogLevel = 7;

    systemd.services.backdoor = {
        description = "Backdoor root shell";
        wantedBy = [ "multi-user.target" ];
        requires = [
        "dev-hvc0.device"
        "dev-${qemu-common.qemuSerialDevice}.device"
        ];
        after = [
        "dev-hvc0.device"
        "dev-${qemu-common.qemuSerialDevice}.device"
        ];
        script = ''
        export USER=root
        export HOME=/root
        export DISPLAY=:0.0

        # Determine if this script is ran with nounset
        strict="false"
        if set -o | grep --quiet --perl-regexp "nounset\s+on"; then
            strict="true"
        fi

        if [[ -e /etc/profile ]]; then
            # TODO: Currently shell profiles are not checked at build time,
            # so we need to unset stricter options to source them
            set +o nounset
            # shellcheck disable=SC1091
            source /etc/profile
            [ "$strict" = "true" ] && set -o nounset
        fi

        # Don't use a pager when executing backdoor
        # actions. Because we use a tty, commands like systemctl
        # or nix-store get confused into thinking they're running
        # interactively.
        export PAGER=

        cd /tmp
        exec < /dev/hvc0 > /dev/hvc0
        while ! exec 2> /dev/${qemu-common.qemuSerialDevice}; do sleep 0.1; done
        echo "connecting to host..." >&2
        stty -F /dev/hvc0 raw -echo # prevent nl -> cr/nl conversion
        # The following line is essential since it signals to
        # the test driver that the shell is ready.
        # See: the connect method in the Machine class.
        echo "Spawning backdoor root shell..."
        # Passing the terminal device makes bash run non-interactively.
        # Otherwise we get errors on the terminal because bash tries to
        # setup things like job control.
        # Note: calling bash explicitly here instead of sh makes sure that
        # we can also run non-NixOS guests during tests. This, however, is
        # mostly futureproofing as the test instrumentation is still very
        # tightly coupled to NixOS.
        PS1="" exec ${pkgs.coreutils}/bin/env bash --norc /dev/hvc0
        '';
        serviceConfig.KillSignal = "SIGHUP";
    };

    systemd.services."serial-getty@${qemu-common.qemuSerialDevice}".enable = false;
    systemd.services."serial-getty@hvc0".enable = false;

    services.journald.extraConfig = ''
        ForwardToConsole=yes
        TTYPath=/dev/${qemu-common.qemuSerialDevice}
        MaxLevelConsole=debug
    '';

    networking.usePredictableInterfaceNames = false;
}