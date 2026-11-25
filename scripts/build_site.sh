#!/usr/bin/env bash
# Copies the compiler into site/ so the playground runs the same code as the CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
cp jayd/compiler.py site/compiler.py
echo "site/compiler.py updated"
