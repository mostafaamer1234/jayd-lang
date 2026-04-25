# Test Plan, Test Scripts, and Suites

## Test Strategy

The test plan validates both normal compiler behavior and expected compiler
failures. The suite uses Python `unittest` so it can run without external
dependencies.

## Automated Test Suite

Primary test file:

- `tests/test_compiler.py`

Run:

```bash
python3 -m unittest discover -s tests
```

Convenience script:

```bash
scripts/run_tests.sh
```

## Example Build Script

```bash
scripts/build_all_examples.sh
```

This validates runnable examples and confirms the intentional memory safety
failure is rejected.

## Test Categories

| Category | What Is Tested |
| --- | --- |
| Lexer | Keywords, indentation tokens, function source |
| Parser | Function declarations and AST structure |
| Type checker | Inference, invalid assignments, nullable values |
| Generics | Generic identity function type checking |
| Classes | Class declarations and class return analysis |
| Ownership | Use-after-move, mutable aliasing, returning local borrow |
| Escape analysis | Stack vs heap classification |
| Imports | File-based module resolution |
| Code generation | LLVM IR for functions and returns |
| Native execution | `clang` builds and runs factorial |
| C++ interop | Links a C++ object and calls `cpp_square` |

## Manual Test Commands

```bash
python3 -m jayd run examples/factorial.jayd -o build/factorial
python3 -m jayd run examples/calculator.jayd -o build/calculator
python3 -m jayd run examples/perf_loop.jayd -o build/perf_loop
python3 -m jayd run examples/classes_and_generics.jayd -o build/classes_and_generics
python3 -m jayd run examples/module_user.jayd -o build/module_user
python3 -m jayd check examples/memory_safety_invalid.jayd
```

Expected outputs:

| Program | Expected Result |
| --- | --- |
| `factorial.jayd` | `120` |
| `calculator.jayd` | `45` |
| `perf_loop.jayd` | `4999950000` |
| `classes_and_generics.jayd` | `42` |
| `module_user.jayd` | `21` |
| `memory_safety_invalid.jayd` | ownership compile-time error |

