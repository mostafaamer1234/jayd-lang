# Jayd Tutorial

## Installing and Running

Requirements:

- Python 3.9 or newer
- `clang` for native executable generation
- `clang++` for the C++ interop demo

From the project root:

```bash
python3 -m jayd check examples/factorial.jayd
python3 -m jayd run examples/factorial.jayd -o build/factorial
```

## Exercise 1: Write a Function

Create `hello_math.jayd`:

```jayd
func square(x: int) -> int:
    return x * x

func main() -> int:
    let value = square(9)
    print(value)
    return 0
```

Run it:

```bash
python3 -m jayd run hello_math.jayd -o build/hello_math
```

Expected output:

```text
81
```

## Variables and Types

Jayd supports mutable `let` and immutable `const` bindings:

```jayd
func main() -> int:
    let x = 5
    const y = 10
    x = x + y
    print(x)
    return 0
```

Local variable types can be inferred. You can also write them explicitly:

```jayd
let count: int = 12
let name: string? = null
```

## Control Flow

```jayd
func sum_to(n: int) -> int:
    let total = 0
    let i = 0
    while i < n:
        total = total + i
        i = i + 1
    return total
```

## Classes

Class declarations are checked by the compiler:

```jayd
class Shape:
    let name: string

class Circle(Shape):
    let radius: float
```

## Generics

Jayd supports generic function signatures:

```jayd
func identity<T>(value: T) -> T:
    return value

func main() -> int:
    let x = identity(42)
    print(x)
    return 0
```

## Memory Safety

Jayd rejects invalid ownership patterns:

```jayd
class Buffer:
    let size: int

func main() -> int:
    let buffer = new Buffer()
    let view = borrow buffer
    let owned = move buffer
    return 0
```

Run:

```bash
python3 -m jayd check examples/memory_safety_invalid.jayd
```

Expected diagnostic:

```text
ownership error at 7:17: cannot move 'buffer' while it is borrowed
```

## C++ Interoperability

`examples/cpp_interop.jayd` declares an external function:

```jayd
extern func cpp_square(x: int) -> int
```

Build and run:

```bash
clang++ -c examples/cpp_square.cpp -o build/cpp_square.o
python3 -m jayd run examples/cpp_interop.jayd -o build/cpp_interop --link build/cpp_square.o
```

Expected output:

```text
81
```

