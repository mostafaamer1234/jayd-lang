# Component Developers

This document maps final project components to team responsibility areas. Update
the assigned member names before Canvas submission.

| Component | Main Files | Responsibility | Assigned Member |
| --- | --- | --- | --- |
| Language design | `docs/whitepaper.md`, `docs/language-spec.md` | Syntax, type system, ownership model | TODO |
| Lexer/parser | `jayd/compiler.py` | Tokenization, indentation, recursive descent parsing | TODO |
| Semantic analysis | `jayd/compiler.py` | Scopes, symbols, type checking, classes, generics | TODO |
| Memory safety | `jayd/compiler.py` | Ownership, borrowing, lifetime diagnostics | TODO |
| Backend/runtime | `jayd/compiler.py`, `examples/cpp_square.cpp` | LLVM IR, `clang`, external function linking | TODO |
| Testing | `tests/test_compiler.py`, `scripts/` | Unit tests, demo validation, expected failures | TODO |
| Documentation | `README.md`, `docs/` | Final report, tutorial, reference manual | TODO |

Suggested coding specialist notes:

- The compiler is intentionally implemented in one file to make final code
  review and code listing easier for a small course project.
- The architecture is still separated by classes, so each compiler phase can be
  explained independently.

