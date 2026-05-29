{
    check-service-log-contains = { machine, check_message, unit, failed_message ? "" }: ''
        print("ASSERTION BLOCK: check_service_log_contains")
        def check_service_log_contains(machine, check_message, unit, failed_message=""):
            failed_msg_display = f"Error checking journalctl logs for unit {unit}: {failed_message}" if failed_message else f"Failed to find \'{check_message}\' in the output"

            stdout = ${machine}.wait_until_succeeds(f"journalctl -u {unit} --no-pager | grep \"{check_message}\" -A 10 -B 10 --color", timeout=60)
            print(stdout)
            assert f"{check_message}" in stdout, failed_msg_display

        check_service_log_contains(${machine}, "${check_message}", "${unit}", "${failed_message}")
    '';

    check-root-gid = { machine, user }: ''
        print("ASSERTION BLOCK: check_root_gid")
        def check_root_gid(machine, user):
            stdout = machine.succeed(f"su - {user} -c 'id'")
            print(stdout)
            assert (f"uid=0({user})" in stdout or "uid=0(root)" in stdout) and "gid=0(root)" in stdout, f"User {user} does not have root privileges"

        check_root_gid(${machine}, "${user}")
    '';

    check-file-exists = { machine, file_path, timeout ? 90 }: ''
        print("ASSERTION BLOCK: check_file_exists")

        def check_file_exists(machine, file_path, timeout):
            import inspect
            
            sig = inspect.signature(machine.wait_for_file)
            if "timeout" in sig.parameters:
                machine.wait_for_file(file_path, timeout)
                machine.wait_for_file(f"{file_path}", timeout)
            else:
                print("Warning: wait_for_file does not support timeout parameter in this tester version.")
                machine.wait_for_file(file_path)
                machine.wait_for_file(f"{file_path}")

        check_file_exists(${machine}, "${file_path}", ${toString timeout})
    '';

    check-file-contains = { machine, file_path, content, timeout ? 90 }: ''
        print("ASSERTION BLOCK: check_file_contains")

        def check_file_contains(machine, file_path, content, timeout):
            import inspect

            sig = inspect.signature(machine.wait_for_file)
            if "timeout" in sig.parameters:
                machine.wait_for_file(file_path, timeout)
            else:
                print("Warning: wait_for_file does not support timeout parameter in this tester version.")
                machine.wait_for_file(file_path)

            stdout = machine.succeed(f"cat {file_path}")
            print(stdout)
            assert f"{content}" in stdout, f"File {file_path} does not contain expected content: {content}"

        check_file_contains(${machine}, "${file_path}", "${content}", ${toString timeout})
    '';

    check-file-size-equals = { machine, file_path, expected_size, timeout ? 90 }: ''
        print("ASSERTION BLOCK: check_file_size_equals")

        def check_file_size_equals(machine, file_path, expected_size, timeout):
            import inspect

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

        check_file_size_equals(${machine}, "${file_path}", ${toString expected_size}, ${toString timeout})
    '';

    check-cpu-usage-high = { machine, command, maximum_cpu_time_usage }: ''
        print("ASSERTION BLOCK: check_cpu_usage_high")
        def check_cpu_usage_high(machine, command, maximum_cpu_time_usage):
            res = machine.execute("prlimit --cpu=" + maximum_cpu_time_usage + " " + command)
            print(res)
            assert res[0] in (152, 137), f"Maximum CPU time usage might not exceeded, unexpected status {res[0]}: {res[1]}"

        check_cpu_usage_high(${machine}, "${command}", "${toString maximum_cpu_time_usage}")
    '';

    check-exact-execution-time = { machine, command, expected_time, repeats ? 5, tolerance ? 0.5 }: ''
        print("ASSERTION BLOCK: check_exact_execution_time")

        def check_exact_execution_time(machine, command, expected_time, repeats, tolerance):
            import time
            
            times = []
            for _ in range(repeats):
                start_time = time.time()
                machine.succeed(command)
                end_time = time.time()
                times.append(end_time - start_time)

            avg_time = sum(times) / len(times)
            print(f"Average execution time: {avg_time} seconds")
            assert abs(avg_time - expected_time) <= tolerance, f"Execution time {avg_time} not within expected range of {expected_time} ± {tolerance} seconds"

        check_exact_execution_time(${machine}, f"${command}", ${toString expected_time}, ${toString repeats}, ${toString tolerance})
    '';

    check-core-dump-exists = { machine, unit_name, expected_signal}: ''
        print("ASSERTION BLOCK: check_core_dump_exists")

        def check_core_dump_exists(machine, unit_name, expected_signal):
            import json

            list_coredumpctl = machine.execute("coredumpctl list --no-pager --no-legend  --json=short")
            print(list_coredumpctl[1])
            coredump_items = json.loads(list_coredumpctl[1])

            assert len(coredump_items) != 0, "No core dumps found on the machine"
            
            expected_signal_str = str(expected_signal).strip()
            pid = None
            dumped_info = None
            for item in coredump_items:
                if "pid" in item:
                    pid = item["pid"]
                    dumped_info = machine.execute(f"coredumpctl info {pid} --no-pager 2>/dev/null | head")

                    if f"Unit: {unit_name}" in dumped_info[1] and (f"Signal: {expected_signal_str}" in dumped_info[1] or f"({expected_signal_str})" in dumped_info[1]):
                        break
                    else:
                        pid = None

            assert pid is not None, f"No core dumps found on the machine for unit {unit_name} with signal {expected_signal_str}"
            signal_info = dumped_info[1].split("Signal:")[1].split("\n")[0].strip()
            print(f"Core dump found for unit {unit_name} with signal {signal_info}")

        check_core_dump_exists(${machine}, "${unit_name}", ${builtins.toJSON expected_signal})
    '';
}