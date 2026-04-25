# Development Environment and Runtime

## Required Tools

- macOS, Linux, or another Unix-like environment
- Python 3.9 or newer
- `clang`
- `clang++` for the C++ interoperability demo

No third-party Python package is required. The compiler uses the Python standard
library.

## Repository

GitHub repository:

<https://github.com/mostafaamer1234/JAYD-ProgrammingLanguage-Compiler>

Clone:

```bash
git clone https://github.com/mostafaamer1234/JAYD-ProgrammingLanguage-Compiler.git
cd JAYD-ProgrammingLanguage-Compiler
```

## Run the Compiler

Check a source file:

```bash
python3 -m jayd check examples/factorial.jayd
```

Emit LLVM IR:

```bash
python3 -m jayd emit-ir examples/factorial.jayd
```

Build and run:

```bash
mkdir -p build
python3 -m jayd run examples/factorial.jayd -o build/factorial
```

## Runtime

Jayd's runtime is intentionally small. It relies on:

- LLVM IR primitives for arithmetic and control flow
- C `printf` for `print`
- `clang` for native linking
- optional C/C++ object files for `extern func`

## C++ Interop Setup

```bash
mkdir -p build
clang++ -c examples/cpp_square.cpp -o build/cpp_square.o
python3 -m jayd run examples/cpp_interop.jayd -o build/cpp_interop --link build/cpp_square.o
```

Expected output:

```text
81
```

