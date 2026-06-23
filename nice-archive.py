#!/usr/bin/env python3
"""
A reproducible security report generator for cURL vulnerabilities, built with Nix.
Interactive tool to create new report cases, run tests, and manage VMs.
"""

import sys
import subprocess
import json
import re
import argparse
import shlex
from pathlib import Path
import time
import pexpect
from InquirerPy import inquirer
import questionary

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Directories
USER_DIR = Path.cwd()
REPORT_DIR = USER_DIR / "cves"

LIBRARY_DIR = Path(__file__).parent

if sys.platform.startswith("linux"):
    systemStr = "x86_64-linux"
elif sys.platform == "darwin":
    systemStr = "aarch64-darwin"
else:
    print(f"{RED}❌{NC} Unsupported platform: {sys.platform}", file=sys.stderr)
    sys.exit(1)

def info(msg: str):
    """Print info message"""
    print(f"{BLUE}ℹ️{NC} {msg}")


def success(msg: str):
    """Print success message"""
    print(f"{GREEN}✅{NC} {msg}")


def error(msg: str):
    """Print error message and exit"""
    print(f"{RED}❌{NC} {msg}", file=sys.stderr)
    sys.exit(1)


def warning(msg: str):
    """Print warning message"""
    print(f"{YELLOW}⚠️{NC} {msg}")

ALL_CASES = "__all_cases__"
DEFAULT_TEST_LOG_TAIL_LINES = 100
LOG_LIVE = "live"
LOG_FILE = "file"
LOG_NONE = "none"
LOG_MODES = {LOG_LIVE, LOG_FILE, LOG_NONE}

def wait_for_enter():
    """Pause when returning to the interactive menu."""
    try:
        input("\nPress Enter to return to menu...")
    except EOFError:
        pass

def has_nix_entry(case_dir: Path) -> bool:
    """Return whether a case has a flake.nix or default.nix entry point."""
    return (case_dir / "flake.nix").exists() or (case_dir / "default.nix").exists()

def list_case_dirs(require_nix_entry: bool = False) -> list[Path]:
    """List report case directories."""
    if not REPORT_DIR.exists():
        return []

    cases = [d for d in REPORT_DIR.iterdir() if d.is_dir()]

    if require_nix_entry:
        cases = [d for d in cases if has_nix_entry(d)]

    return sorted(cases)

def resolve_case(case: str, require_nix_entry: bool = False) -> Path:
    """Resolve a case name or path to a case directory."""
    candidate = Path(case).expanduser()

    if not candidate.is_absolute():
        report_candidate = REPORT_DIR / case
        if report_candidate.exists():
            candidate = report_candidate

    if candidate.exists():
        if not candidate.is_dir():
            error(f"Case path is not a directory: {candidate}")
        if require_nix_entry and not has_nix_entry(candidate):
            error(f"No flake.nix or default.nix found in case directory: {candidate}")
        return candidate

    cases = list_case_dirs(require_nix_entry=require_nix_entry)
    exact_matches = [d for d in cases if d.name == case]
    casefold_matches = [d for d in cases if d.name.casefold() == case.casefold()]
    partial_matches = [d for d in cases if case.casefold() in d.name.casefold()]

    matches = exact_matches or casefold_matches or partial_matches

    if not matches:
        error(f"Could not find case: {case}")

    if len(matches) > 1:
        names = ", ".join(d.name for d in matches)
        error(f"Case name is ambiguous: {case}. Matches: {names}")

    return matches[0]

def resolve_named_choice(name: str, choices: list[str], label: str) -> str:
    """Resolve an exact, case-insensitive, or unique partial name."""
    if name in choices:
        return name

    casefold_matches = [choice for choice in choices if choice.casefold() == name.casefold()]
    partial_matches = [choice for choice in choices if name.casefold() in choice.casefold()]
    matches = casefold_matches or partial_matches

    if not matches:
        error(f"Could not find {label}: {name}")

    if len(matches) > 1:
        error(f"{label.capitalize()} name is ambiguous: {name}. Matches: {', '.join(matches)}")

    return matches[0]

def prompt_case(message: str, include_all: bool = False, require_nix_entry: bool = False) -> Path | str | None:
    """Prompt for a case, optionally including an all-cases choice."""
    cases = [d.name for d in list_case_dirs(require_nix_entry=require_nix_entry)]

    if not cases:
        error("No valid report cases found")

    choices = cases[:]
    if include_all:
        choices.append("All cases")
    choices.append("Cancel")

    selected = inquirer.fuzzy(
        message=message,
        choices=choices,
        multiselect=True,
        match_exact=False,
    ).execute()

    selected_case = selected[0] if selected else "Cancel"

    if selected_case == "Cancel":
        return None

    if selected_case == "All cases":
        return ALL_CASES

    return resolve_case(selected_case, require_nix_entry=require_nix_entry)

def prompt_vulnerability() -> bool | None:
    """Prompt for vulnerable or non-vulnerable scenario."""
    choice = questionary.select(
        message="Vulnerable or non-vulnerable scenario?",
        choices=[
            "Vulnerable",
            "Non-Vulnerable",
            "Cancel"
        ],
        qmark="?",
        pointer="→",
        default="Vulnerable"
    ).ask()

    if choice == "Cancel":
        return None

    return choice == "Vulnerable"

def get_start_point(case_dir: Path) -> str:
    """Return the Nix entry point type for a case."""
    if (case_dir / "flake.nix").exists():
        return "flake"
    if (case_dir / "default.nix").exists():
        return "default"
    error("No flake.nix or default.nix found in case directory")

def print_command_tail(result: subprocess.CompletedProcess):
    """Print the useful tail of a captured failed command."""
    output = result.stderr or result.stdout or ""
    if output:
        print_log_tail(output)

def test_log_path(
    case_dir: Path,
    isVulnerable: bool,
    system: str,
    filename: str | None = None,
) -> Path:
    """Return the path where a test log should be saved."""
    if filename:
        path = Path(filename).expanduser()
        return path if path.is_absolute() else case_dir / path

    vulnerable_str = "true" if isVulnerable else "false"
    safe_system = system.replace("/", "-")
    return case_dir / f"test-vulnerable-{vulnerable_str}-{safe_system}.log"

def format_command(command: list[str | Path]) -> str:
    """Return a shell-readable command string for logs."""
    return shlex.join(str(part) for part in command)

def append_command_log(log_parts: list[str], command: list[str | Path], result: subprocess.CompletedProcess):
    """Append a command and its combined output to the full test log."""
    log_parts.append(f"$ {format_command(command)}\n")
    log_parts.append(result.stdout or "")
    if log_parts[-1] and not log_parts[-1].endswith("\n"):
        log_parts.append("\n")
    log_parts.append(f"[exit code: {result.returncode}]\n")

def run_logged_command(
    command: list[str | Path],
    cwd: Path,
    log_parts: list[str],
    log_mode: str,
) -> subprocess.CompletedProcess:
    """Run a command using the selected logging mode."""
    info(f"Running command: {format_command(command)}")

    if log_mode == LOG_LIVE:
        return subprocess.run(
            command,
            cwd=cwd,
        )

    if log_mode == LOG_NONE:
        return subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    append_command_log(log_parts, command, result)
    return result

def save_test_log(log_path: Path, log_text: str):
    """Persist the full captured test log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(log_text, encoding="utf-8")

def tail_lines(output: str, line_count: int = DEFAULT_TEST_LOG_TAIL_LINES) -> str:
    """Return the last line_count lines from output."""
    lines = output.splitlines()
    if len(lines) <= line_count:
        return output

    tail = "\n".join(lines[-line_count:])
    if output.endswith("\n"):
        tail += "\n"
    return tail

def print_log_tail(log_text: str):
    """Print the configured tail of a captured log."""
    output = tail_lines(log_text)
    if output:
        print(output, end="" if output.endswith("\n") else "\n")

def clean_output(case_dir: Path):
    """Clean previous test outputs"""
    try:
        subprocess.run(["bash", LIBRARY_DIR / "cleanup-script.sh", str(case_dir)], cwd=LIBRARY_DIR, capture_output=True)
    except Exception as e:
        warning(f"Error during cleanup: {e}")

def git_add_case(case_dir: Path):
    """Add a case directory to git."""
    try:
        subprocess.run(["git", "add", str(case_dir)], cwd=USER_DIR, capture_output=True)
    except Exception as e:
        warning(f"Error adding case to git: {e}")

def run_single_test(
    case_dir: Path,
    isVulnerable: bool = True,
    pause: bool = False,
    refresh: bool = False,
    log_mode: str = LOG_FILE,
    log_file: str | None = None,
    system: str = systemStr,
) -> bool:
    """Run test for a single case"""
    if log_mode not in LOG_MODES:
        raise ValueError(f"Unsupported test log mode: {log_mode}")
    if log_mode != LOG_FILE and log_file is not None:
        raise ValueError("A custom log filename requires file logging mode")

    case_name = case_dir.name
    info(f"Testing: {case_name}")
    print()

    info("Cleaning previous test outputs...")
    clean_output(case_dir)

    start_point = get_start_point(case_dir)
    
    vulnerable_str = "true" if isVulnerable else "false"
    log_path = test_log_path(case_dir, isVulnerable, system, filename=log_file)
    log_parts: list[str] = []

    try:
        refresh_args = ["--refresh"] if refresh else []

        if start_point == "flake":
            git_add_case(case_dir)
            command = ["nix", "run", *refresh_args, f".#test-vulnerable-{vulnerable_str}-{system}"]
            result = run_logged_command(
                command,
                cwd=case_dir,
                log_parts=log_parts,
                log_mode=log_mode,
            )

            # To handle legacy test output that have not been updated to use the new nice-archive library. Will be removed in the future.
            if result.returncode != 0:
                retry_message = f"Primary test command failed, retrying with legacy output for {case_name}"
                warning(retry_message)
                if log_mode == LOG_FILE:
                    log_parts.append(f"\n# {retry_message}\n")
                command = ["nix", "run", *refresh_args, f".#testVulnerable{vulnerable_str.capitalize()}"]
                result = run_logged_command(
                    command,
                    cwd=case_dir,
                    log_parts=log_parts,
                    log_mode=log_mode,
                )
        else:
            command = ["nix-build", "default.nix", "-A", f"testVulnerable{vulnerable_str.capitalize()}"]
            result = run_logged_command(
                command,
                cwd=case_dir,
                log_parts=log_parts,
                log_mode=log_mode,
            )

            if result.returncode == 0:
                command = ["./result/bin/nixos-test-driver"]
                result = run_logged_command(
                    command,
                    cwd=case_dir,
                    log_parts=log_parts,
                    log_mode=log_mode,
                )

        log_text = "".join(log_parts)
        if log_mode == LOG_FILE:
            save_test_log(log_path, log_text)
            info(f"Test log saved to: {log_path}")

        if result.returncode == 0:
            success(f"Test passed: {case_name}")
            passed = True
        else:
            warning(f"Test failed: {case_name}")
            passed = False

        if log_mode == LOG_FILE and log_text:
            info(f"Printing last {DEFAULT_TEST_LOG_TAIL_LINES} lines of test output:")
            print_log_tail(log_text)
    except Exception as e:
        if log_mode == LOG_FILE and log_parts:
            try:
                save_test_log(log_path, "".join(log_parts))
                warning(f"Partial test log saved to: {log_path}")
            except Exception as log_error:
                warning(f"Could not save partial test log: {log_error}")
        error(f"Error running test: {e}")
    
    if pause:
        wait_for_enter()

    return passed

def run_all_tests(
    isVulnerable: bool = True,
    pause: bool = False,
    refresh: bool = True,
    log_mode: str = LOG_FILE,
    log_file: str | None = None,
    system: str = systemStr,
) -> bool:
    """Run tests for all cases"""
    info("Running all tests...")
    print()
    
    passed = 0
    failed = 0
    
    cases = list_case_dirs(require_nix_entry=True)
    
    for case_dir in cases:
        if run_single_test(
            case_dir,
            isVulnerable=isVulnerable,
            pause=False,
            refresh=refresh,
            log_mode=log_mode,
            log_file=log_file,
            system=system,
        ):
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"{BLUE}═════════════════════════════════════════{NC}")
    print(f"{GREEN}Passed: {passed}{NC}")
    print(f"{RED}Failed: {failed}{NC}")
    print(f"{BLUE}═════════════════════════════════════════{NC}")

    if pause:
        wait_for_enter()

    return failed == 0

def run_tests():
    """Run tests menu"""
    info("Run report case tests...")
    print()
    
    selected = prompt_case(
        message="Select CVE case to test:",
        include_all=True,
        require_nix_entry=True,
    )

    if selected is None:
        show_main_menu()
        return

    is_vulnerable = prompt_vulnerability()
    
    if is_vulnerable is None:
        show_main_menu()
        return

    if selected == ALL_CASES:
        run_all_tests(
            isVulnerable=is_vulnerable,
            pause=True,
            log_mode=LOG_NONE,
        )
    else:
        run_single_test(
            selected,
            isVulnerable=is_vulnerable,
            pause=True,
            log_mode=LOG_LIVE,
        )

    show_main_menu()

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

def strip_ansi(s: str) -> str:
    s = ANSI_RE.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s

def read_until_clean(child, needle: str, timeout: float = 120.0) -> str:
    deadline = time.time() + timeout
    raw_parts = []
    clean_buf = ""

    while time.time() < deadline:
        try:
            chunk = child.read_nonblocking(size=4096, timeout=1)
        except pexpect.TIMEOUT:
            continue

        raw_parts.append(chunk)
        clean_buf += strip_ansi(chunk)

        if needle in clean_buf:
            return clean_buf

    raise TimeoutError(f"Did not see cleaned text: {needle!r}")

# Start interactive scenario section
def start_scenario_case(
    case_dir: Path,
    isVulnerable: bool = True,
    system: str = systemStr,
    popup: bool = True,
) -> bool:
    """Start scenario for a single case."""
    info("Starting scenario for a report case...")
    print()

    try:
        clean_output(case_dir)
    except Exception:
        pass

    info("Extracting VM names from flake...")
    try:
        subprocess.run(["git", "add", str(case_dir)], cwd=USER_DIR, capture_output=True)

        vulnerable_str = "true" if isVulnerable else "false"
        child = pexpect.spawn(
            f"nix run .#start-scenario-vulnerable-{vulnerable_str}-{system}",
            cwd=str(case_dir),
            encoding="utf-8",
            echo=False
        )

        # Log output to our terminal until the interactive setup finishes.
        child.logfile_read = sys.stdout

        clean_text = read_until_clean(
            child,
            "additionally exposed symbols:",
            timeout=120,
        )

        ssh_commands = dict(re.findall(
            r"^\s*([A-Za-z0-9._-]+):\s+(ssh\b[^\r\n]+)$",
            clean_text,
            re.MULTILINE,
        ))

        child.sendline("test_script()")

        read_until_clean(
            child,
            "INTERACTIVE MODE SETUP COMPLETE. READY FOR INTERACTIVE TESTING.",
            timeout=120,
        )

        if len(ssh_commands) == 0:
            raise RuntimeError("Did not find any SSH commands in the output. Maybe there is no VM available?")

        time.sleep(2)  # Give the child process time to settle before launching terminals.

        if popup:
            for name, cmd in ssh_commands.items():
                try:
                    subprocess.Popen(
                        ["terminator", "-T", name, "-e", cmd],
                        cwd=case_dir,
                    )
                except FileNotFoundError:
                    warning("terminator is not available; use the SSH commands below manually.")
                    break

        info(f"{GREEN}To access the machines, use the following SSH commands:{NC}")
        for name, cmd in ssh_commands.items():
            print(f"  - {name}: {cmd}")

        info(f"{RED}To exit the scenario, press Ctrl+D in this terminal and choose 'Yes' to kill the VMs.{NC}")

        child.logfile = None
        child.logfile_read = None
        child.logfile_send = None
        child.interact()
        return True

    except Exception as e:
        error(f"Could not start scenario: {e}")

def start_scenario():
    """Start scenario for a single case from the interactive menu."""
    selected = prompt_case(
        message="Select CVE case to start:",
        require_nix_entry=True,
    )

    if selected is None:
        show_main_menu()
        return

    is_vulnerable = prompt_vulnerability()

    if is_vulnerable is None:
        show_main_menu()
        return

    start_scenario_case(selected, isVulnerable=is_vulnerable)
    show_main_menu()

def get_standalone_vm_data(case_dir: Path) -> dict:
    """Return standalone VM metadata for a case."""
    print(f"{BLUE}Scanning for available VMs...{NC}")

    if (case_dir / "flake.nix").exists():
        result = subprocess.run(
            ["nix", "eval", "--json", ".#standaloneVMs", "--apply", "builtins.attrNames"],
            cwd=case_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            vm_names = json.loads(result.stdout)
            if not vm_names:
                error("No standalone VMs found for this case.")
            return {
                "kind": "flake-standalone",
                "names": vm_names,
            }

        if not (case_dir / "default.nix").exists():
            error(f"Failed to get available VMs: {result.stderr}")

    if (case_dir / "default.nix").exists():
        try:
            result = subprocess.run(
                ["nix-instantiate", "--eval", "--json", "--expr", "builtins.attrNames (import ./default.nix)"],
                cwd=case_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error(f"Failed to get available VMs: {result.stderr}")

            vm_names = [
                name for name in json.loads(result.stdout)
                if name.startswith("vm")
            ]

            if not vm_names:
                error("No standalone VMs found for this case.")

            return {
                "kind": "default-nix",
                "names": vm_names,
            }
        except Exception as e:
            error(f"Error getting available VMs: {e}")

    error("No flake.nix or default.nix found in case directory")

def prompt_standalone_vm(vm_names: list[str]) -> str | None:
    """Prompt for a standalone VM name."""
    choice = questionary.select(
        message="Select a VM to run:",
        choices=vm_names + ["Cancel"],
        qmark="?",
        pointer="→",
    ).ask()

    if choice == "Cancel":
        return None

    return choice

def run_standalone_vm(case_dir: Path, vm_name: str | None = None, allow_prompt: bool = True) -> bool:
    """Run one standalone VM."""
    info("Running standalone VM machine...")
    print()

    info("Cleaning previous VM outputs...")
    clean_output(case_dir)

    vm_data = get_standalone_vm_data(case_dir)
    vm_names = vm_data["names"]

    if vm_name is None:
        if not allow_prompt:
            error("--name is required when running a VM without prompts")
        vm_name = prompt_standalone_vm(vm_names)

    if vm_name is None:
        return False

    selected_vm = resolve_named_choice(vm_name, vm_names, "VM")

    info("Press Ctrl + A + X to exit the VM and return to the menu.")
    info(f"Starting VM: {selected_vm}...")
    try:
        if vm_data["kind"] == "flake-standalone":
            result = subprocess.run(
                ["nix", "run", f".#standaloneVMs.{selected_vm}"],
                cwd=case_dir,
            )
        else:
            result = subprocess.run(
                ["nix-build", "default.nix", "-A", selected_vm],
                cwd=case_dir,
            )

            if result.returncode != 0:
                return False

            run_scripts = sorted((case_dir / "result" / "bin").glob("run-*-vm"))
            if not run_scripts:
                error("No VM launcher found under result/bin after nix-build")

            result = subprocess.run(
                [str(run_scripts[0])],
                cwd=case_dir,
            )

        return result.returncode == 0
    except Exception as e:
        error(f"Error starting VM: {e}")

def run_standalone_vms():
    """Run standalone VM machines from the interactive menu."""
    selected = prompt_case(
        message="Select CVE case to test:",
        require_nix_entry=True,
    )

    if selected is None:
        show_main_menu()
        return

    run_standalone_vm(selected)
    show_main_menu()

def update_flake_case(case_dir: Path) -> bool:
    """Update nix flake for a single case"""
    info(f"Updating nix flake for: {case_dir.name}")
    print()
    
    try:
        result = subprocess.run(
            ["nix", "flake", "update"],
            cwd=case_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            success(f"Flake updated successfully: {case_dir.name}")
            return True
        else:
            warning(f"Failed to update flake: {case_dir.name}")
            print_command_tail(result)
            return False
    except Exception as e:
        error(f"Error updating flake: {e}")
    

def update_all_flakes(pause: bool = False) -> bool:
    """Update nix flakes for all cases"""
    info("Updating nix flakes for all cases...")
    print()
    
    cases = list_case_dirs(require_nix_entry=True)
    failed = 0
    
    for case_dir in cases:
        if not update_flake_case(case_dir):
            failed += 1
    
    if pause:
        wait_for_enter()

    return failed == 0

def update_flakes():
    """Update nix flakes for existing cases"""
    info("Updating nix flakes for existing cases...")
    print()
    
    selected = prompt_case(
        message="Select CVE case to test:",
        include_all=True,
        require_nix_entry=True,
    )
    
    if selected is None:
        show_main_menu()
        return
    
    if selected == ALL_CASES:
        update_all_flakes(pause=True)
    else:
        update_flake_case(selected)
    show_main_menu()

def show_main_menu():
    """Display main menu"""

# ASCII art generated with https://asciiart.website/figlet.php and snowflake from https://ascii.co.uk/art/snow
    print(r"""
   .      .                                                                                             .      .   
   _\/  \/_    ███╗   ██╗██╗ ██████╗███████╗     █████╗ ██████╗  ██████╗██╗  ██╗██╗██╗   ██╗███████╗    _\/  \/_   
    _\/\/_     ████╗  ██║██║██╔════╝██╔════╝    ██╔══██╗██╔══██╗██╔════╝██║  ██║██║██║   ██║██╔════╝     _\/\/_    
_\_\_\/\/_/_/_ ██╔██╗ ██║██║██║     █████╗      ███████║██████╔╝██║     ███████║██║██║   ██║█████╗   _\_\_\/\/_/_/_
 / /_/\/\_\ \  ██║╚██╗██║██║██║     ██╔══╝      ██╔══██║██╔══██╗██║     ██╔══██║██║╚██╗ ██╔╝██╔══╝    / /_/\/\_\ \ 
    _/\/\_     ██║ ╚████║██║╚██████╗███████╗    ██║  ██║██║  ██║╚██████╗██║  ██║██║ ╚████╔╝ ███████╗     _/\/\_    
    /\  /\     ╚═╝  ╚═══╝╚═╝ ╚═════╝╚══════╝    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝     /\  /\    
   '      '                                                                                             '      '   
    """)

    choice = questionary.select(
        message="What would you like to do?",
        choices=[
            "Start interactive scenario",
            "Run tests",
            "Run standalone VM machines",
            "Update flakes for CVE cases",
            "Exit"
        ],
        qmark="?",
        pointer="→",
    ).ask()
    
    if choice == "Start interactive scenario":
        start_scenario()
    elif choice == "Run tests":
        run_tests()
    elif choice == "Run standalone VM machines":
        run_standalone_vms()
    elif choice == "Update flakes for CVE cases":
        update_flakes()
    elif choice == "Exit":
        print("Goodbye!")
        sys.exit(0)

def parse_bool(value: str) -> bool:
    """Parse a command-line boolean value."""
    normalized = value.strip().casefold()

    if normalized in {"true", "t", "yes", "y", "1"}:
        return True

    if normalized in {"false", "f", "no", "n", "0"}:
        return False

    raise argparse.ArgumentTypeError("expected true or false")

class TestLogAction(argparse.Action):
    """Parse --log MODE [FILE]."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: list[str],
        option_string: str | None = None,
    ):
        mode = values[0].casefold()

        if mode not in LOG_MODES:
            parser.error("--log mode must be one of: live, file, none")

        if mode == LOG_FILE:
            if len(values) > 2:
                parser.error("--log file accepts at most one filename")
            filename = values[1] if len(values) == 2 else None
        else:
            if len(values) != 1:
                parser.error(f"--log {mode} does not accept a filename")
            filename = None

        setattr(namespace, self.dest, (mode, filename))

class TestHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Format the optional test log filename clearly."""

    def _format_args(self, action: argparse.Action, default_metavar: str) -> str:
        if isinstance(action, TestLogAction):
            return "MODE [FILE]"
        return super()._format_args(action, default_metavar)

def add_case_args(parser: argparse.ArgumentParser, include_all: bool = False):
    """Add case selection options to a command parser."""
    parser.add_argument(
        "--case",
        dest="case_name",
        help="case name or path, for example cve-2016-5195-dirty-cow",
    )

    if include_all:
        parser.add_argument(
            "--all",
            action="store_true",
            help="apply the command to all valid CVE cases",
        )
    else:
        parser.set_defaults(all=False)

def add_vulnerability_arg(parser: argparse.ArgumentParser):
    """Add vulnerable/non-vulnerable selection to a command parser."""
    parser.add_argument(
        "--vulnerable",
        type=parse_bool,
        default=True,
        metavar="{true,false}",
        help="run the vulnerable variant: true or false (default: true)",
    )

def add_system_arg(parser: argparse.ArgumentParser):
    """Add Nix system selection to a command parser."""
    parser.add_argument(
        "--system",
        default=systemStr,
        help=f"Nix system tag to use for generated outputs (default: {systemStr})",
    )

def add_no_prompt_arg(parser: argparse.ArgumentParser):
    """Add the no-prompt option to a command parser."""
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="fail instead of asking interactively for missing arguments",
    )

def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="nice-archive",
        description="CLI tool for managing reproducible NICE Archive security reports.",
    )

    commands = parser.add_subparsers(dest="command", metavar="command")

    start_parser = commands.add_parser(
        "start",
        help="open the interactive menu",
        description="Open the interactive NICE Archive menu.",
    )
    start_parser.set_defaults(action="start", print_help_when_empty=False)

    list_cves_parser = commands.add_parser(
        "list-cves",
        help="list available CVE cases",
        description="List valid CVE case directories.",
    )
    list_cves_parser.set_defaults(action="list_cves", print_help_when_empty=False)

    test_parser = commands.add_parser(
        "test",
        help="run CVE tests",
        description="Run one CVE test or all CVE tests.",
        formatter_class=TestHelpFormatter,
        epilog="""logging modes:
  --log live              print test output live; do not create a log file
  --log file              save the full log using the default per-case name
  --log file NAME         save the full log as NAME inside each case directory
  --log none              suppress test output and do not create a log file

CLI test runs default to "--log file". In the interactive menu, single-case
tests use live logging and all-case runs suppress test output.""",
    )
    add_case_args(test_parser, include_all=True)
    add_vulnerability_arg(test_parser)
    add_system_arg(test_parser)
    add_no_prompt_arg(test_parser)
    test_parser.add_argument(
        "--refresh",
        action="store_true",
        help="pass --refresh to nix run",
    )
    test_parser.add_argument(
        "--log",
        nargs="+",
        action=TestLogAction,
        default=(LOG_FILE, None),
        dest="test_log",
        metavar="MODE [FILE]",
        help=(
            "test logging mode: live, file [FILE], or none "
            "(default: file with an automatic per-case filename)"
        ),
    )
    test_parser.set_defaults(action="test", print_help_when_empty=True, command_parser=test_parser)

    scenario_parser = commands.add_parser(
        "scenario",
        help="start an interactive CVE scenario",
        description="Start a CVE scenario and attach to the interactive test driver.",
    )
    add_case_args(scenario_parser)
    add_vulnerability_arg(scenario_parser)
    add_system_arg(scenario_parser)
    add_no_prompt_arg(scenario_parser)
    scenario_parser.add_argument(
        "--popup",
        type=parse_bool,
        default=True,
        metavar="{true,false}",
        help="open terminator SSH windows after VMs are ready: true or false (default: true)",
    )
    scenario_parser.set_defaults(action="scenario", print_help_when_empty=True, command_parser=scenario_parser)

    vm_parser = commands.add_parser(
        "vm",
        help="run a standalone VM",
        description="Run a standalone VM for a CVE case.",
    )
    add_case_args(vm_parser)
    add_no_prompt_arg(vm_parser)
    vm_parser.add_argument(
        "--name",
        "--vm-name",
        dest="vm_name",
        help="standalone VM name to run",
    )
    vm_parser.set_defaults(action="vm", print_help_when_empty=True, command_parser=vm_parser)

    list_vms_parser = commands.add_parser(
        "list-vms",
        help="list standalone VMs for a CVE case",
        description="List standalone VM outputs for a CVE case.",
    )
    add_case_args(list_vms_parser)
    add_no_prompt_arg(list_vms_parser)
    list_vms_parser.set_defaults(action="list_vms", print_help_when_empty=True, command_parser=list_vms_parser)

    update_parser = commands.add_parser(
        "update-flakes",
        aliases=["update"],
        help="update flake.lock files",
        description="Update flake.lock for one CVE case or all CVE cases.",
    )
    add_case_args(update_parser, include_all=True)
    add_no_prompt_arg(update_parser)
    update_parser.set_defaults(action="update_flakes", print_help_when_empty=True, command_parser=update_parser)

    return parser

def has_cli_action(args: argparse.Namespace) -> bool:
    """Return whether a CLI action flag was selected."""
    return getattr(args, "action", None) is not None

def cli_vulnerability(args: argparse.Namespace) -> bool:
    """Return the selected vulnerability variant, defaulting to vulnerable."""
    return getattr(args, "vulnerable", True)

def cli_case(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    message: str,
    include_all: bool = False,
    require_nix_entry: bool = True,
) -> Path | str:
    """Resolve a case from CLI args, prompting only when needed."""
    case_name = getattr(args, "case_name", None)
    all_cases = getattr(args, "all", False)
    no_prompt = getattr(args, "no_prompt", False)

    if case_name and all_cases:
        parser.error("--case and --all cannot be used together")

    if all_cases:
        if include_all:
            return ALL_CASES
        parser.error("--all is not valid for this action")

    if case_name:
        return resolve_case(case_name, require_nix_entry=require_nix_entry)

    if no_prompt:
        parser.error("--case is required for this action")

    selected = prompt_case(
        message=message,
        include_all=include_all,
        require_nix_entry=require_nix_entry,
    )

    if selected is None:
        sys.exit(0)

    return selected

def list_cases() -> bool:
    """Print valid CVE case names."""
    for case_dir in list_case_dirs(require_nix_entry=True):
        print(case_dir.name)
    return True

def list_standalone_vms(case_dir: Path) -> bool:
    """Print standalone VM names for a case."""
    vm_data = get_standalone_vm_data(case_dir)
    for vm_name in vm_data["names"]:
        print(vm_name)
    return True

def run_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> bool:
    """Run a non-menu command-line action."""
    action = getattr(args, "action", None)

    if action == "start":
        show_main_menu()
        return True

    if action == "list_cves":
        return list_cases()

    if action == "list_vms":
        case_dir = cli_case(
            args,
            parser,
            message="Select CVE case to inspect:",
            require_nix_entry=True,
        )
        return list_standalone_vms(case_dir)

    if action == "scenario":
        case_dir = cli_case(
            args,
            parser,
            message="Select CVE case to start:",
            require_nix_entry=True,
        )
        return start_scenario_case(
            case_dir,
            isVulnerable=cli_vulnerability(args),
            system=args.system,
            popup=args.popup,
        )

    if action == "test":
        log_mode, log_file = args.test_log
        selected = cli_case(
            args,
            parser,
            message="Select CVE case to test:",
            include_all=True,
            require_nix_entry=True,
        )

        if selected == ALL_CASES:
            return run_all_tests(
                isVulnerable=cli_vulnerability(args),
                refresh=True,
                log_mode=log_mode,
                log_file=log_file,
                system=args.system,
            )

        return run_single_test(
            selected,
            isVulnerable=cli_vulnerability(args),
            refresh=args.refresh,
            log_mode=log_mode,
            log_file=log_file,
            system=args.system,
        )

    if action == "vm":
        case_dir = cli_case(
            args,
            parser,
            message="Select CVE case to test:",
            require_nix_entry=True,
        )
        return run_standalone_vm(
            case_dir,
            vm_name=args.vm_name,
            allow_prompt=not args.no_prompt,
        )

    if action == "update_flakes":
        selected = cli_case(
            args,
            parser,
            message="Select CVE case to update:",
            include_all=True,
            require_nix_entry=True,
        )

        if selected == ALL_CASES:
            return update_all_flakes()

        return update_flake_case(selected)

    parser.error("choose a command such as start, test, scenario, vm, update-flakes, list-cves, or list-vms")

def main(argv: list[str] | None = None):
    """Main entry point"""
    cli_args = sys.argv[1:] if argv is None else argv

    if not REPORT_DIR.exists():
        warning(f"Report directory not found, creating: {REPORT_DIR}")
        REPORT_DIR.mkdir(parents=True)

    parser = build_parser()
    args = parser.parse_args(cli_args)

    if not has_cli_action(args):
        parser.print_help()
        return

    if len(cli_args) == 1 and getattr(args, "print_help_when_empty", False):
        args.command_parser.print_help()
        return

    ok = run_cli(args, parser)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
