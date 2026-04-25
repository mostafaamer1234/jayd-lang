# Code Listing

The full source listing is included in the submitted project folder. The most
important files are:

```text
jayd/__main__.py
jayd/cli.py
jayd/compiler.py
tests/test_compiler.py
examples/factorial.jayd
examples/calculator.jayd
examples/perf_loop.jayd
examples/classes_and_generics.jayd
examples/memory_safety_valid.jayd
examples/memory_safety_invalid.jayd
examples/cpp_interop.jayd
examples/cpp_square.cpp
examples/module_math.jayd
examples/module_user.jayd
```

## Main Compiler File

`jayd/compiler.py` contains the implementation of:

- diagnostics
- lexer
- AST node classes
- parser
- type system
- semantic analyzer
- ownership checker
- escape analyzer
- optimizer
- LLVM IR code generator
- command-line interface

Because the complete file is long, it is submitted as source code rather than
duplicated in this report. This keeps the report readable while still satisfying
the code listing requirement through the included project source.

