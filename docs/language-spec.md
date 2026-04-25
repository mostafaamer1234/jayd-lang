# Jayd Language Spec

## Design Goal

Jayd is designed to sit between Python and C++: readable syntax, static checking,
native compilation, and deterministic memory safety.

## Syntax

- Blocks are indentation-based.
- Top-level declarations are `import`, `extern func`, `func`, and `class`.
- Statements include `let`, `const`, assignment, `if`, `else`, `while`, `for`,
  `return`, `try`, `catch`, and `throw`.
- Expressions include literals, variables, calls, arithmetic, comparison,
  `new`, `move`, `borrow`, and `borrow mut`.

## Types

Primitive types:

- `int`
- `float`
- `bool`
- `string`
- `null`
- `void`

Jayd supports nullable spelling such as `string?`, class types, and generic
function signatures such as:

```jayd
func identity<T>(value: T) -> T:
    return value
```

## Ownership Model

The v0.1 checker is intentionally conservative for clarity:

- `move x` transfers ownership and makes `x` unusable afterward.
- `borrow x` creates an immutable borrow.
- `borrow mut x` creates an exclusive mutable borrow.
- A mutable borrow cannot coexist with any other borrow.
- A moved value cannot be used or borrowed.
- A borrowed value cannot be moved.
- Returning a borrow of a local binding is rejected.

Borrows currently live until the end of the function. This is stricter than a
production language, but it demonstrates lifetime checking clearly.

## Backend

The compiler emits LLVM IR for the core executable subset: primitive values,
functions, recursion, calls, arithmetic, comparisons, `if`, `while`, bindings,
assignment, and `print`.

Imports are resolved from sibling `.jayd` files using the module path. For
example, `import math.util` loads `math/util.jayd` relative to the importing
file.

`extern func` declarations lower to LLVM declarations. The CLI accepts
`--link path/to/object.o` for linking C/C++ objects into a final executable.

Advanced constructs such as classes, ownership operations, exception syntax, and
for-loops are parsed and checked. The LLVM backend emits explanatory comments for
constructs that are not lowered in v0.1.
