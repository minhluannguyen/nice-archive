"""
Assertion blocks for NixOS test framework.

This module provides helper functions for NixOS test assertions.
These functions assume they're running within a NixOS test environment
where machine objects have methods like succeed(), execute(), wait_for_file(), etc.
"""

import inspect
import json
import time


def check_service_log_contains(machine, check_message, unit, failed_message=""):
    """Check if a service's journalctl log contains a specific message."""
    print("ASSERTION BLOCK: check_service_log_contains")
    failed_msg_display = (
        f"Error checking journalctl logs for unit {unit}: {failed_message}"
        if failed_message
        else f"Failed to find '{check_message}' in the output"
    )

    stdout = machine.wait_until_succeeds(
        f'journalctl -u {unit} --no-pager | grep "{check_message}" -A 10 -B 10 --color',
        timeout=60
    )
    print(stdout)
    assert f"{check_message}" in stdout, failed_msg_display


def check_root_gid(machine, user):
    """Check if a user has root privileges."""
    print("ASSERTION BLOCK: check_root_gid")
    stdout = machine.succeed(f"su - {user} -c 'id'")
    print(stdout)
    assert (
        (f"uid=0({user})" in stdout or "uid=0(root)" in stdout)
        and "gid=0(root)" in stdout
    ), f"User {user} does not have root privileges"


def check_file_exists(machine, file_path, is_existing=True, timeout=90):
    """Check if a file exists or doesn't exist."""
    print(
        f"ASSERTION BLOCK: check_file_exists (expecting file to be "
        f"{'present' if is_existing else 'absent'})"
    )

    if is_existing:
        sig = inspect.signature(machine.wait_for_file)
        if "timeout" in sig.parameters:
            machine.wait_for_file(file_path, timeout)
        else:
            print("Warning: wait_for_file does not support timeout parameter in this tester version.")
            machine.wait_for_file(file_path)
    else:
        machine.wait_until_succeeds(f"test ! -e {file_path}", timeout=timeout)


def check_file_contains(machine, file_path, content, timeout=90):
    """Check if a file contains specific content."""
    print("ASSERTION BLOCK: check_file_contains")

    sig = inspect.signature(machine.wait_for_file)
    if "timeout" in sig.parameters:
        machine.wait_for_file(file_path, timeout)
    else:
        print("Warning: wait_for_file does not support timeout parameter in this tester version.")
        machine.wait_for_file(file_path)

    stdout = machine.succeed(f"cat {file_path}")
    print(stdout)
    assert f"{content}" in stdout, f"File {file_path} does not contain expected content: {content}"


def check_file_size_equals(machine, file_path, expected_size, timeout=90):
    """Check if a file has the expected size in bytes."""
    print("ASSERTION BLOCK: check_file_size_equals")

    sig = inspect.signature(machine.wait_for_file)
    if "timeout" in sig.parameters:
        machine.wait_for_file(file_path, timeout)
    else:
        print("Warning: wait_for_file does not support timeout parameter in this tester version.")
        machine.wait_for_file(file_path)

    stdout = machine.succeed(f"stat -c%s {file_path}")
    print(stdout)
    actual_size = int(stdout.strip())
    assert actual_size == expected_size, f"File size of {file_path} is {actual_size}, expected {expected_size}"


def check_cpu_usage_high(machine, command, maximum_cpu_time_usage):
    """Check if a command exceeds maximum CPU time usage."""
    print("ASSERTION BLOCK: check_cpu_usage_high")
    res = machine.execute("prlimit --cpu=" + maximum_cpu_time_usage + " " + command)
    print(res)
    assert res[0] in (152, 137), f"Maximum CPU time usage might not exceeded, unexpected status {res[0]}: {res[1]}"


def check_memory_usage_high(machine, command, maximum_memory_usage):
    """Check if a command exceeds maximum memory usage."""
    print("ASSERTION BLOCK: check_memory_usage_high")
    res = machine.execute("prlimit --as=" + maximum_memory_usage + " " + command)
    print(res)
    assert res[0] in (27, 139), f"Maximum memory usage might not exceeded, unexpected status {res[0]}: {res[1]}"


def check_exact_execution_time(machine, command, expected_time, repeats=5, tolerance=0.5):
    """Check if a command executes within expected time frame."""
    print("ASSERTION BLOCK: check_exact_execution_time")

    times = []
    for _ in range(repeats):
        start_time = time.time()
        machine.succeed(command)
        end_time = time.time()
        times.append(end_time - start_time)

    avg_time = sum(times) / len(times)
    print(f"Average execution time: {avg_time} seconds")
    assert (
        abs(avg_time - expected_time) <= tolerance
    ), f"Execution time {avg_time} not within expected range of {expected_time} ± {tolerance} seconds"


def check_core_dump_exists(
    machine, unit_name="backdoor.service", expected_signal=None, repeats=10, repeat_command=""
):
    """Check if a core dump exists for a specific unit with expected signal."""
    print("ASSERTION BLOCK: check_core_dump_exists")

    def _check_core_dump_exists_internal(machine, unit_name, expected_signal, repeats, repeat_command):
        list_coredumpctl = machine.execute("coredumpctl list --no-pager --no-legend  --json=short")
        print(list_coredumpctl[1])
        if list_coredumpctl[0] != 0:
            raise AssertionError(f"Error executing coredumpctl: {list_coredumpctl[1]}")
        coredump_items = json.loads(list_coredumpctl[1])

        assert len(coredump_items) != 0, "No core dumps found on the machine"

        expected_signal_str = str(expected_signal).strip()
        pid = None
        dumped_info = None
        for item in coredump_items:
            if "pid" in item:
                pid = item["pid"]
                dumped_info = machine.execute(f"coredumpctl info {pid} --no-pager 2>/dev/null | head -n 20")
                print(dumped_info[1])
                if f"Unit: {unit_name}" in dumped_info[1] and (
                    f"Signal: {expected_signal_str}" in dumped_info[1]
                    or f"({expected_signal_str})" in dumped_info[1]
                ):
                    break
                else:
                    pid = None

        assert (
            pid is not None
        ), f"No core dumps found on the machine for unit {unit_name} with signal {expected_signal_str}"
        signal_info = dumped_info[1].split("Signal:")[1].split("\n")[0].strip()
        print(f"Core dump found for unit {unit_name} with signal {signal_info}")

        return True

    def _wait_for_core_dump(machine, unit_name, expected_signal, repeats, repeat_command):
        if repeat_command:
            print(f"Initial command to trigger the core dump: {repeat_command}")
            machine.execute(repeat_command)
            for attempt in range(repeats):
                try:
                    print(f"Checking for core dump, attempt {attempt + 1}/{repeats}...")
                    _check_core_dump_exists_internal(machine, unit_name, expected_signal, repeats, repeat_command)
                    return
                except AssertionError as e:
                    print(str(e))
                    if repeat_command:
                        print(f"Executing repeat command: {repeat_command}")
                        machine.execute(repeat_command)
                    time.sleep(5)
        else:
            _check_core_dump_exists_internal(machine, unit_name, expected_signal, repeats, repeat_command)
            return
        assert (
            False
        ), f"Core dump with signal {expected_signal} for unit {unit_name} not found after {repeats} attempts"

    _wait_for_core_dump(machine, unit_name, expected_signal, repeats, repeat_command)
