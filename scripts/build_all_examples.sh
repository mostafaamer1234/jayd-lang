#!/usr/bin/env bash
set -euo pipefail

mkdir -p build

python3 -m jayd run examples/factorial.jayd -o build/factorial
python3 -m jayd run examples/calculator.jayd -o build/calculator
python3 -m jayd run examples/perf_loop.jayd -o build/perf_loop
python3 -m jayd run examples/classes_and_generics.jayd -o build/classes_and_generics
python3 -m jayd run examples/memory_safety_valid.jayd -o build/memory_safety_valid
python3 -m jayd run examples/module_user.jayd -o build/module_user

clang++ -c examples/cpp_square.cpp -o build/cpp_square.o
python3 -m jayd run examples/cpp_interop.jayd -o build/cpp_interop --link build/cpp_square.o

if python3 -m jayd check examples/memory_safety_invalid.jayd; then
    echo "Expected memory_safety_invalid.jayd to fail, but it passed" >&2
    exit 1
else
    echo "memory_safety_invalid.jayd correctly failed ownership checking"
fi

