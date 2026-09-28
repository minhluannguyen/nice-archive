#!/usr/bin/env python3
"""Copy selected CVE recipes from an experiment results directory."""

import argparse
import re
import shutil
import sys
from pathlib import Path


DESTINATION = Path(__file__).resolve().parent / "cves-llm"
CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cve_file", type=Path, help="text file with one CVE ID per line")
    parser.add_argument("root_dir", type=Path, help="directory containing CVE result directories")
    args = parser.parse_args()

    if not args.cve_file.is_file():
        parser.error(f"CVE file does not exist: {args.cve_file}")
    if not args.root_dir.is_dir():
        parser.error(f"root directory does not exist: {args.root_dir}")

    failed = False
    seen = set()
    for line_number, line in enumerate(args.cve_file.read_text(encoding="utf-8").splitlines(), 1):
        cve = line.strip().upper()
        if not cve or cve.startswith("#"):
            continue
        if not CVE_PATTERN.fullmatch(cve):
            print(f"Line {line_number}: invalid CVE ID: {line.strip()}", file=sys.stderr)
            failed = True
            continue
        if cve in seen:
            continue
        seen.add(cve)

        recipe_dir = args.root_dir / cve / "recipe"
        matches = sorted(
            path for path in recipe_dir.glob(f"{cve.lower()}-*") if path.is_dir()
        )
        if len(matches) != 1:
            print(f"{cve}: expected one recipe directory in {recipe_dir}, found {len(matches)}", file=sys.stderr)
            failed = True
            continue

        source = matches[0]
        destination = DESTINATION / source.name
        if destination.exists():
            print(f"Skipped existing: {destination}")
            continue
        DESTINATION.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, symlinks=True)
        print(f"Copied: {source} -> {destination}")

    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
