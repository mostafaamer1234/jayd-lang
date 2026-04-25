# Component Developers

This document maps final project components to team responsibility areas.

| Component | Main Files | Responsibility | Assigned Member |
| --- | --- | --- | --- |
| Language design | `docs/whitepaper.md`, `docs/language-spec.md` | Primary syntax, type system, ownership model | Mostafa Amer |
| Language review | `docs/tutorial.md`, `examples/` | Readability feedback and tutorial/example review | Jack Demtshuk |
| Lexer/parser | `jayd/compiler.py` | Tokenization, indentation, recursive descent parsing | Mostafa Amer |
| Semantic analysis | `jayd/compiler.py` | Scopes, symbols, type checking, classes, generics | Mostafa Amer |
| Memory safety | `jayd/compiler.py` | Ownership, borrowing, lifetime diagnostics | Mostafa Amer |
| Architecture review | `docs/translator-architecture.md`, `docs/design-artifacts.md` | Review of compiler phase diagrams and architecture writeup | Terminkeev Andzhur |
| Backend/runtime | `jayd/compiler.py`, `examples/cpp_square.cpp` | LLVM IR, `clang`, external function linking | Mostafa Amer |
| Runtime verification | `scripts/build_all_examples.sh`, `docs/development-environment.md` | Support checking final build/run commands | Vejseli Erand |
| Testing | `tests/test_compiler.py`, `scripts/` | Unit tests, demo validation, expected failures | Mostafa Amer |
| Test review | `examples/`, `docs/test-plan.md` | Support review of expected outputs and negative test cases | Jack Demtshuk, Terminkeev Andzhur, Vejseli Erand |
| Documentation | `README.md`, `docs/` | Final report, tutorial, reference manual | Mostafa Amer |

Suggested coding specialist notes:

- The compiler is intentionally implemented in one file to make final code
  review and code listing easier for a small course project.
- The architecture is still separated by classes, so each compiler phase can be
  explained independently.
