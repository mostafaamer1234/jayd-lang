# Project Development Methodology, Plan, and Schedule

## Methodology

The project followed an incremental compiler-construction process:

1. Define the language goal and core syntax.
2. Implement a minimal working compiler pipeline.
3. Add semantic analysis and type checking.
4. Add the advanced ownership/lifetime feature.
5. Add LLVM IR generation and native execution.
6. Add examples, tests, and final documentation.

This matches an iterative software engineering model: each milestone produced a
testable artifact.

## Milestones

| Milestone | Deliverable | Status |
| --- | --- | --- |
| Language concept | Jayd proposal and goals | Complete |
| Grammar and lexical model | Indentation-sensitive lexer | Complete |
| Parser and AST | Recursive descent parser | Complete |
| Semantic analyzer | Scopes, symbols, type checking | Complete |
| Memory safety | Ownership and borrow checker | Complete |
| Middle end | Escape analysis and constant folding | Complete |
| Backend | LLVM IR generation | Complete |
| Runtime path | `clang` native compilation and `printf` output | Complete |
| Interop | `extern func` and object linking | Complete |
| Validation | Unit tests and demo scripts | Complete |
| Final packaging | Docs, report, zip, GitHub repo | Complete |

## Effort Estimate

| Task | Estimated Effort |
| --- | --- |
| Language design and examples | 6-8 hours |
| Lexer/parser/AST | 10-12 hours |
| Type checking and scopes | 8-10 hours |
| Ownership checker | 6-8 hours |
| LLVM backend | 10-14 hours |
| Tests and debugging | 6-8 hours |
| Documentation and packaging | 5-7 hours |

## Risk Management

| Risk | Mitigation |
| --- | --- |
| LLVM backend complexity | Limit v0.1 native lowering to core executable subset |
| Too many language features | Parse/check advanced constructs while documenting backend limits |
| Memory safety too complex | Use conservative borrow lifetimes for a teachable implementation |
| Environment differences | Use Python stdlib and system `clang`; document commands |

