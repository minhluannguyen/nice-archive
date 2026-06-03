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


def _collect_flake_outputs(node, outputs=None, current_name=None):
    if outputs is None:
        outputs = set()

    if not isinstance(node, dict):
        return outputs

    if "type" in node:
        if current_name is not None:
            outputs.add(current_name)
        return outputs

    for key, value in node.items():
        if key in {"packages", "apps", "checks", "legacyPackages"} and isinstance(value, dict):
            _collect_flake_outputs(value, outputs, current_name)
        elif isinstance(value, dict):
            _collect_flake_outputs(value, outputs, key)

    return outputs


def resolve_test_output(case_dir: Path, isVulnerable: bool) -> str:
    legacy = f"testVulnerable{'True' if isVulnerable else 'False'}"

    result = subprocess.run(
        ["nix", "flake", "show", "--json"],
        cwd=case_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and result.stdout.strip():
        try:
            available_outputs = _collect_flake_outputs(json.loads(result.stdout))
            if legacy in available_outputs:
                return legacy
        except Exception:
            pass

    return preferred

def run_single_test(case_dir: Path, isVulnerable: bool = True):
    """Run test for a single case"""
    case_name = case_dir.name
    info(f"Testing: {case_name}")
    print()
    
    try:
        test_output = resolve_test_output(case_dir, isVulnerable)

        if isVulnerable:
            result = subprocess.run(
                ["nix", "run", f".#{test_output}"],
                cwd=case_dir,
                # capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                ["nix", "run", f".#{test_output}"],
                cwd=case_dir,
                # capture_output=True,
                text=True
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
            "Run tests",
            "Exit"
        ],
        qmark="?",
        pointer="→",
    ).ask()
    
    if choice == "Run tests":
        run_tests()
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

