# Jayd Reference Manual

## File Extension

Jayd source files use `.jayd`.

## Program Entry Point

Execution begins at:

```jayd
func main() -> int:
    return 0
```

## Keywords

| Keyword | Syntax | Meaning |
| --- | --- | --- |
| `func` | `func name(params) -> type:` | Defines a function |
| `extern` | `extern func name(params) -> type` | Declares a C/C++ ABI function |
| `class` | `class Name:` | Declares a class |
| `import` | `import module_name` | Loads a sibling `.jayd` file |
| `let` | `let x = expr` | Mutable local binding |
| `const` | `const x = expr` | Immutable local binding |
| `if` | `if condition:` | Conditional branch |
| `else` | `else:` | Alternative branch |
| `while` | `while condition:` | Loop while condition is true |
| `for` | `for x in expr:` | Parsed and checked loop form |
| `return` | `return expr` | Returns from a function |
| `try` | `try:` | Parsed exception block |
| `catch` | `catch err:` | Parsed exception handler |
| `throw` | `throw expr` | Parsed throw statement |
| `new` | `new ClassName()` | Creates a class instance for analysis |
| `move` | `move x` | Transfers ownership of `x` |
| `borrow` | `borrow x` | Creates an immutable borrow |
| `mut` | `borrow mut x` | Creates a mutable borrow |
| `true` | `true` | Boolean literal |
| `false` | `false` | Boolean literal |
| `null` | `null` | Null literal |
| `and` | `a and b` | Boolean conjunction |
| `or` | `a or b` | Boolean disjunction |
| `not` | `not a` | Boolean negation |

## Primitive Types

| Type | Meaning | LLVM Lowering |
| --- | --- | --- |
| `int` | 64-bit integer | `i64` |
| `float` | 64-bit floating point | `double` |
| `bool` | Boolean | `i1` |
| `string` | UTF-8 string pointer | `ptr` |
| `void` | No return value | `void` |
| `null` | Null value | `ptr null` |

Nullable types use `?`:

```jayd
let name: string? = null
```

## Functions

```jayd
func add(a: int, b: int) -> int:
    return a + b
```

Function parameters and return types must be explicit.

## Generic Function Signatures

```jayd
func identity<T>(value: T) -> T:
    return value
```

The semantic analyzer checks generic calls. The v0.1 LLVM backend supports the
primitive integer generic demonstration used in the examples.

## Classes

```jayd
class Shape:
    let name: string

class Circle(Shape):
    let radius: float
```

Class inheritance is single inheritance. The compiler rejects unknown base
classes and unknown member access.

## Imports

```jayd
import module_math
```

This loads `module_math.jayd` relative to the importing file.

## Operators

| Operators | Meaning |
| --- | --- |
| `+ - * / %` | Arithmetic |
| `< <= > >= == !=` | Comparison |
| `and or not` | Boolean logic |
| `=` | Assignment |

## Built-in Function

```jayd
print(value)
```

Prints `int`, `float`, `bool`, or `string` values.

## Compiler Commands

```bash
python3 -m jayd check file.jayd
python3 -m jayd emit-ir file.jayd
python3 -m jayd build file.jayd -o output
python3 -m jayd run file.jayd -o output
```

