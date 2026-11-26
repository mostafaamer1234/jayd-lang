# Jayd

**Live playground: [jayd-lang.vercel.app](https://jayd-lang.vercel.app)**. The real compiler runs in the browser through Pyodide: edit code and see type and borrow errors, stack-or-heap decisions, and the generated LLVM IR.

Jayd is an educational compiler project for CMPSC 470. It implements a Python-readable,
statically typed language with a classic compiler pipeline:

- indentation-aware lexer
- recursive descent parser
- AST and semantic analysis
- type inference for local bindings
- generic function signatures
- class declarations with single inheritance checks
- ownership and borrow checking
- escape analysis
- constant-folding optimization
- LLVM IR generation
- optional native executable generation through `clang`

The standout feature is deterministic memory safety without garbage collection. Jayd
uses a conservative ownership checker with `move`, `borrow`, and `borrow mut`
expressions, then reports whether `new` allocations can stay on the stack or must
escape to the heap.

## Quick Start

```bash
mkdir -p build
python3 -m jayd check examples/factorial.jayd
python3 -m jayd emit-ir examples/factorial.jayd
python3 -m jayd build examples/factorial.jayd -o build/factorial
./build/factorial
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

Or:

```bash
scripts/run_tests.sh
scripts/build_all_examples.sh
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
