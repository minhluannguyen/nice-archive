#!/bin/bash
set -euo pipefail

DIR="$1"

find "$DIR" -type f -name "*.qcow2" -delete
find "$DIR" -type l -name "*result" -delete
find "$DIR" -type f -name ".nixos-test-history" -delete
find "$DIR" -type f -name "*.log" -delete