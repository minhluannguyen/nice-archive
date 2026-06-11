#!/usr/bin/env python3
"""
A reproducible security report generator for cURL vulnerabilities, built with Nix.
Interactive tool to create new report cases, run tests, and manage VMs.
"""

import sys
import subprocess
import json
import re
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
TEMPLATE_DIR = LIBRARY_DIR / "template"

systemStr = "x86_64-linux" if sys.platform.startswith("linux") else "aarch64-darwin" if sys.platform == "darwin" else error(f"Unsupported platform: {sys.platform}")

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

def run_single_test(case_dir: Path, isVulnerable: bool = True):
    """Run test for a single case"""
    case_name = case_dir.name
    info(f"Testing: {case_name}")
    print()
    
    try:
        vulnerable_str = "true" if isVulnerable else "false"
        result = subprocess.run(
            ["nix", "run", f".#test-vulnerable-{vulnerable_str}-{systemStr}"],
            cwd=case_dir,
            # capture_output=True,
            text=True,
        )

        # To handle legacy test output that have not been updated to use the new nice-archive library. Will be removed in the future.
        if result.returncode != 0:
            warning(f"Primary test command failed, retrying with legacy output for {case_name}")
            result = subprocess.run(
                ["nix", "run", f".#testVulnerable{vulnerable_str.capitalize()}"],
                cwd=case_dir,
                # capture_output=True,
                text=True,
            )
        
        if result.returncode == 0:
            success(f"Test passed: {case_name}")
        else:
            warning(f"Test failed: {case_name}")
            print(result.stderr[-500:] if result.stderr else result.stdout[-500:])
    except Exception as e:
        error(f"Error running test: {e}")
    
    print("\nPress Enter to return to menu...")
    input()

def run_all_tests():
    """Run tests for all cases"""
    info("Running all tests...")
    print()
    
    passed = 0
    failed = 0
    
    cases = sorted([d for d in REPORT_DIR.iterdir() if d.is_dir() and (d / "report.yaml").exists()])
    
    for case_dir in cases:
        case_name = case_dir.name
        info(f"Testing: {case_name}")
        
        try:
            test_output = resolve_test_output(case_dir, True)
            result = subprocess.run(
                ["nix", "run", "--refresh", f".#{test_output}"],
                cwd=case_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                success(f"{case_name} passed")
                passed += 1
            else:
                warning(f"{case_name} failed")
                failed += 1
        except Exception as e:
            warning(f"Error running {case_name}: {e}")
            failed += 1
    
    print()
    print(f"{BLUE}═════════════════════════════════════════{NC}")
    print(f"{GREEN}Passed: {passed}{NC}")
    print(f"{RED}Failed: {failed}{NC}")
    print(f"{BLUE}═════════════════════════════════════════{NC}")

    print("\nPress Enter to return to menu...")
    input()

def run_tests():
    """Run tests menu"""
    info("Run report case tests...")
    print()
    
    cases = sorted([d.name for d in REPORT_DIR.iterdir() if d.is_dir() and ((d / "flake.nix") or (d / "default.nix")).exists()])
    
    if not cases:
        error("No report cases with report.yaml found")
    
    cases.extend(["All cases", "Cancel"])

    choice = inquirer.fuzzy(
        message="Select CVE case to test:",
        choices= cases,
        multiselect=True,
        match_exact=False,
    ).execute()

    selected = choice[0] if choice else "Cancel"

    if selected == "Cancel":
        show_main_menu()
        return
    
    if selected == "All cases":
        run_all_tests()
    else:
        case_dir = REPORT_DIR / selected

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
            show_main_menu()
            return

        run_single_test(case_dir, isVulnerable=(choice == "Vulnerable"))
    
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
def start_scenario():
    """Start scenario for a single case"""
    info("Starting scenario for a report case...")
    print()
    
    cases = sorted([d.name for d in REPORT_DIR.iterdir() if d.is_dir() and ((d / "flake.nix") or (d / "default.nix")).exists()])

    if not cases:
        error("No valid reports found")
    
    cases.append("Cancel")

    choice = inquirer.fuzzy(
        message="Select CVE case to test:",
        choices= cases,
        multiselect=True,
        match_exact=False,
    ).execute()
    
    selected = choice[0] if choice else "Cancel"
    
    if selected == "Cancel":
        show_main_menu()
        return
    
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
        show_main_menu()
        return
    
    case_dir = REPORT_DIR / selected
    
    try:
        subprocess.run(["bash", LIBRARY_DIR / "cleanup-script.sh"], capture_output=True)
    except Exception:
        pass
  
    # Extract VM names from flake
    info("Extracting VM names from flake...")
    try:
        subprocess.run(["git", "add", case_dir], cwd=USER_DIR, capture_output=True)

        if choice == "Vulnerable":
            child = pexpect.spawn(
                f"nix run .#start-scenario-vulnerable-true-{systemStr}",
                cwd=str(case_dir),
                encoding="utf-8",
                echo=False
            )
        else:
            child = pexpect.spawn(
                f"nix run .#start-scenario-vulnerable-false-{systemStr}",
                cwd=str(case_dir),
                encoding="utf-8",
                echo=False
            )

        # Log output to our terminal
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

        post_text = read_until_clean(
            child,
            "INTERACTIVE MODE SETUP COMPLETE. READY FOR INTERACTIVE TESTING.",
            timeout=120,
        )

        if len(ssh_commands) == 0:
            raise RuntimeError("Did not find any SSH commands in the output. Maybe there is no VM available?")
        

        terminator_cmds = []
        for name, cmd in ssh_commands.items():
            terminator_cmds.append(f'terminator -T {name} -e "{cmd}"')

        full_cmd = " & ".join(terminator_cmds)

        time.sleep(2)  # Give some time for the child process to set up before launching terminator
        
        subprocess.Popen(
            ["bash", "-c", full_cmd],
            cwd=case_dir,
        )
        
        info(f"{GREEN}To access the machines, use the following SSH commands:{NC}")
        for name, cmd in ssh_commands.items():
            print(f"  - {name}: {cmd}")

        info(f"{RED}To exit the scenario, press Ctrl+D in this terminal and choose 'Yes' to kill the VMs.{NC}")

        child.logfile = None
        child.logfile_read = None
        child.logfile_send = None
        child.interact()


    except Exception as e:
        error(f"Could not start scenario: {e}")
    
    show_main_menu()

def run_standalone_vms():
    """Run standalone VM machines"""
    info("Running standalone VM machines...")
    
    print()
    
    cases = sorted([d.name for d in REPORT_DIR.iterdir() if d.is_dir() and ((d / "flake.nix") or (d / "default.nix")).exists()])

    if not cases:
        error("No valid reports found")
    
    cases.append("Cancel")

    choice = inquirer.fuzzy(
        message="Select CVE case to test:",
        choices= cases,
        multiselect=True,
        match_exact=False,
    ).execute()
    
    selected = choice[0] if choice else "Cancel"
    
    if selected == "Cancel":
        show_main_menu()
        return
    

    print(f"{BLUE}Scanning for available VMs...{NC}")

    case_dir = REPORT_DIR / selected
    try:
        result = subprocess.run(
            ["nix", "eval", "--json", ".#standaloneVMs"],
            cwd=case_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            error(f"Failed to get available VMs: {result.stderr}")
        
        vm_data = json.loads(result.stdout)
        vm_names = list(vm_data.keys())
        if not vm_names:
            error("No standalone VMs found for this case.")
    except Exception as e:
        error(f"Error getting available VMs: {e}")

    choice = questionary.select(
        message="Select a VM to run:",
        choices= vm_names + ["Cancel"],
        qmark="?",
        pointer="→",
    ).ask()

    if choice == "Cancel":
        show_main_menu()
        return
    
    selected_vm = vm_data[choice]
    info(f"Press Ctrl + A + X to exit the VM and return to the menu.")
    info(f"Starting VM: {choice}...")
    try:
        subprocess.run(
            ["nix", "run", f".#standaloneVMs.{choice}"],
            cwd=case_dir,
        )
    except Exception as e:
        error(f"Error starting VM: {e}")

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
    elif choice == "Exit":
        print("Goodbye!")
        sys.exit(0)


def main():
    """Main entry point"""
    if not REPORT_DIR.exists():
        warning(f"Report directory not found, creating: {REPORT_DIR}")
        REPORT_DIR.mkdir(parents=True)
    
    show_main_menu()


if __name__ == "__main__":
    main()

