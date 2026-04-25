# Conclusions and Postmortem

## Final Result

Jayd successfully demonstrates an innovative little language and an implemented
translator. The project includes a real compiler pipeline, testable examples,
native LLVM-backed execution, and a distinctive memory safety feature.

## What Worked Well

- Python-inspired syntax made example programs readable.
- The compiler architecture separated phases cleanly enough to explain in a
  final presentation.
- LLVM IR generation made the project more advanced than a simple interpreter.
- Ownership and borrowing gave the language a unique identity.
- Automated tests made regressions easy to catch.

## Challenges

- Full production compiler features are large in scope.
- Generic lowering and class object layout are complex topics.
- LLVM IR is strict, so type mismatches in generated IR must be found quickly.
- Memory safety checking requires more than normal type checking.

## Tradeoffs

The implementation prioritizes a strong compiler-course demonstration over a
production-ready language. The v0.1 backend lowers the primitive executable
subset fully. Other features are parsed and checked so the language design is
visible, but some are left as documented future work.

## Lessons Learned

- A language feature is not just syntax; it affects parsing, typing, runtime,
  diagnostics, tests, and documentation.
- Compiler phases make a large problem easier to manage.
- Error messages are part of language usability.
- A small language can still show advanced ideas if it has one strong feature.

## Future Work

Future development should focus on:

- complete object layout for classes
- method dispatch
- arrays and collections
- full generic monomorphization
- richer borrow lifetimes
- exceptions lowered to runtime behavior
- more optimization passes

