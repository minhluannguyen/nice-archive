#!/bin/bash
set -euo pipefail

DIR="./cves"

find "$DIR" -type f -name "*.qcow2" -delete
find "$DIR" -type l -name "*result" -delete
find "$DIR" -type f -name ".nixos-test-history" -delete