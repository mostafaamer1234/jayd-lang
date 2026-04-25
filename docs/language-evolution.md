# Language Evolution

## Initial Idea

Jayd began as a proposed language that would feel close to Python while
compiling to native code. The first design emphasized readability, static
typing, deterministic memory behavior, and C++ compatibility.

## Current Implemented Version

The implemented v0.1 compiler includes:

- indentation-based syntax
- functions
- local variables and constants
- static type checking
- generic function signatures
- classes with single inheritance validation
- file-based imports
- ownership and borrow checking
- escape analysis
- LLVM IR emission
- native execution through `clang`
- external function linking

## Design Decisions

The team kept the language small enough to implement but advanced enough to show
real compiler knowledge. The biggest design decision was to prioritize memory
safety as the unique feature rather than building a large standard library.

## Future Evolution

Planned future versions could add:

- full object layout and method dispatch in LLVM
- generic monomorphization for all supported types
- better borrow lifetimes using control-flow regions
- arrays and standard containers
- pattern matching
- explicit error types
- lightweight threads and message passing
- compile-time race detection

