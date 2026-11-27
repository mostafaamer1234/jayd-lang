#!/usr/bin/env bash
# Copies the compiler and interpreter into site/ so the playground runs the same code as the CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
cp jayd/compiler.py site/compiler.py
cp jayd/interpreter.py site/interpreter.py
echo "site/compiler.py and site/interpreter.py updated"
