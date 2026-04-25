# Jayd Language Whitepaper

## Abstract

Jayd is a compact educational programming language designed to combine Python's
readability with the predictability of systems languages. Jayd uses indentation
for blocks, a small keyword set, static typing with local inference, LLVM IR
generation, and deterministic memory safety based on ownership and borrowing.

The language targets the gap between quick scripting languages and lower-level
native languages. Python is easy to read and write, but CPU-bound programs often
pay interpreter overhead. C++ offers native speed and control, but exposes
manual memory management, pointer hazards, and undefined behavior. Jayd explores
whether a small language can offer readable syntax while still teaching the
compiler ideas behind native execution and memory safety.

## Application Domain

Jayd is intended for small systems-style programs, compiler-course examples,
numerical demos, and educational language-design experiments. Its domain is not
large enterprise application development. Instead, it focuses on:

- readable algorithms
- predictable native execution
- compile-time diagnostics
- safe ownership transfer
- simple interoperability with C/C++ functions

## Innovation

The distinguishing feature is deterministic memory safety without a garbage
collector. Jayd introduces `move`, `borrow`, and `borrow mut` expressions. The
compiler rejects use-after-move, moving while borrowed, conflicting mutable
borrows, and returning borrows of local values.

This is advanced for a small compiler project because it adds a semantic pass
beyond normal type checking. The compiler does not only ask whether expressions
have correct types; it also checks whether values are still valid to use.

## Computational Model

Jayd programs are organized into files containing functions, classes, imports,
and external function declarations. Execution begins at `main`. Function calls
use static signatures. Primitive values compile to LLVM-level values. Heap-like
objects created with `new` are analyzed by escape analysis so the compiler can
decide whether the allocation can remain local or must escape.

## Abstraction Mechanisms

Jayd supports:

- functions
- local bindings
- constants
- classes with single inheritance
- modules mapped to files
- generic function signatures
- external function declarations

These mechanisms are intentionally small but composable. The language prefers
clear, teachable features over a very large standard library.

## Type System

Jayd is statically typed. Function parameters and return values are explicitly
typed. Local variables may be inferred from their initializer. Nullable types use
the `?` suffix, for example `string?`, so nullability is visible in the type.

The compiler rejects:

- assigning a value to an incompatible type
- returning the wrong type
- calling functions with the wrong number or type of arguments
- referring to undefined symbols
- inheriting from an unknown class

## Usability Goals

Jayd's syntax is designed for readability:

```jayd
func factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

The surface language is intentionally Python-like, while the compiler internals
show advanced language implementation concepts: parsing, semantic analysis,
ownership checking, optimization, and LLVM backend generation.

## Implementation Summary

The current translator is implemented in Python. It performs:

1. Lexical analysis with indentation tokens.
2. Parsing into an AST.
3. Semantic analysis and type checking.
4. Ownership and lifetime checking.
5. Escape analysis.
6. Constant-folding optimization.
7. LLVM IR generation.
8. Optional native compilation through `clang`.

## Limitations

Jayd v0.1 is an implemented segment of the full language design. The executable
backend supports the core primitive/function subset. Classes, exception syntax,
ownership operations, imports, and generics are parsed and checked; full
production object layout, exception unwinding, and generic monomorphization are
future work.

