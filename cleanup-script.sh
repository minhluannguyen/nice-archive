#!/bin/bash
set -euo pipefail

DIR="$1"
KEEP_LOGS="${2:-}"

find "$DIR" -type f -name "*.qcow2" -delete
find "$DIR" -type l -name "*result" -delete
find "$DIR" -type f -name ".nixos-test-history" -delete
if [[ "$KEEP_LOGS" != "--keep-logs" ]]; then
  find "$DIR" -type f -name "*.log" ! -name "scenario-*.log" -delete
fi
