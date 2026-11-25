# Jayd

![CI](https://github.com/mostafaamer1234/jayd-lang/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![LLVM](https://img.shields.io/badge/backend-LLVM%20IR-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Jayd is a statically typed language that reads like Python and compiles to **LLVM IR** and native executables. It gets **deterministic memory safety without a garbage collector** from compile-time ownership and borrow checking, plus escape analysis that decides whether each allocation can stay on the stack.

The compiler is written in pure Python with no dependencies (`clang` is only needed for native builds). It was built as a 4-person team project for CMPSC 470 at Penn State; I was the project manager and lead system architect, implemented the lexer, parser, semantic analysis and LLVM backend, and led testing (see [docs/team.md](docs/team.md)).

### Compiler pipeline

```
source.jayd ─▶ indentation-aware lexer ─▶ recursive-descent parser ─▶ AST
            ─▶ semantic analysis + type inference + generics + class/inheritance checks
            ─▶ ownership / borrow checker ─▶ escape analysis ─▶ constant folding
            ─▶ LLVM IR ─▶ clang (-O0..-O3) ─▶ native executable
```

## Performance

`bench/run_bench.py` compiles each benchmark with Jayd at `-O0` and `-O2`, runs the equivalent CPython program, and **fails if the outputs differ**:

| Benchmark | CPython 3.13 | Jayd -O0 | Jayd -O2 | Speedup (-O2 vs CPython) |
|---|---|---|---|---|
| `fib(32)`, recursive calls | 146 ms | 12 ms | 6 ms | 24x |
| 50M-iteration arithmetic loop | 2049 ms | 34 ms | 18 ms | 117x |

*Apple Silicon (arm64), macOS, median of 3 runs. CI re-runs the benchmarks on Linux and macOS for every PR. At `-O2` LLVM simplifies the loop heavily, so that number mostly shows what a typed, compiled pipeline unlocks compared with an interpreter.*

## Quick Start

```bash
mkdir -p build
python3 -m jayd check examples/factorial.jayd
python3 -m jayd emit-ir examples/factorial.jayd
python3 -m jayd build examples/factorial.jayd -o build/factorial      # add -O2 for optimized output
./build/factorial
```

Install as a command (`jayd ...`):

```bash
pip install .
jayd run examples/factorial.jayd -o build/factorial -O2
```

Run tests and benchmarks:

```bash
python3 -m unittest discover -s tests
```

Or:

```bash
scripts/run_tests.sh
scripts/build_all_examples.sh
python3 bench/run_bench.py
```

Build the C++ interop demo:

```bash
clang++ -c examples/cpp_square.cpp -o /tmp/cpp_square.o
python3 -m jayd run examples/cpp_interop.jayd -o /tmp/jayd_cpp --link /tmp/cpp_square.o
```

## Language Sample

```jayd
func factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

func main() -> int:
    let value = factorial(5)
    print(value)
    return 0
```

## Memory Safety Sample

```jayd
class Buffer:
    let size: int

func invalid() -> int:
    let b = new Buffer()
    let view = borrow b
    let owned = move b   # compile-time ownership error
    return 0
```

## Final Project Deliverables

The final report package is organized under [docs](docs):

- [Final project report index](docs/final-project-report.md)
- [Language whitepaper](docs/whitepaper.md)
- [Language specification](docs/language-spec.md)
- [Tutorial](docs/tutorial.md)
- [Reference manual](docs/reference-manual.md)
- [Development plan](docs/development-plan.md)
- [Translator architecture](docs/translator-architecture.md)
- [Test plan](docs/test-plan.md)
- [Design artifacts](docs/design-artifacts.md)
- [Postmortem conclusions](docs/conclusions.md)
- [Submission checklist](docs/submission-checklist.md)
