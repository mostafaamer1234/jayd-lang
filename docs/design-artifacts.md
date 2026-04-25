# Design Artifacts

## Compiler Class Diagram

```mermaid
classDiagram
    class Compiler {
        +compile_file(path)
        +compile_source(source)
        +compile_program(program)
    }
    class Lexer {
        +scan()
    }
    class Parser {
        +parse()
    }
    class SemanticAnalyzer {
        +analyze()
    }
    class OwnershipChecker {
        +check()
    }
    class EscapeAnalyzer {
        +analyze(program)
    }
    class Optimizer {
        +optimize(program)
    }
    class LLVMCodegen {
        +emit()
    }
    Compiler --> Lexer
    Compiler --> Parser
    Compiler --> SemanticAnalyzer
    Compiler --> OwnershipChecker
    Compiler --> Optimizer
    Compiler --> EscapeAnalyzer
    Compiler --> LLVMCodegen
```

## AST Overview

```mermaid
flowchart TD
    Program --> ImportDecl
    Program --> ExternFunc
    Program --> FuncDecl
    Program --> ClassDecl
    FuncDecl --> Statements
    ClassDecl --> FieldDecl
    ClassDecl --> Methods
    Statements --> LetStmt
    Statements --> AssignStmt
    Statements --> IfStmt
    Statements --> WhileStmt
    Statements --> ReturnStmt
    Statements --> ExprStmt
    ExprStmt --> Expressions
    Expressions --> Literal
    Expressions --> Var
    Expressions --> Binary
    Expressions --> Unary
    Expressions --> Call
    Expressions --> NewExpr
    Expressions --> BorrowExpr
    Expressions --> MoveExpr
```

## Ownership Checking Flow

```mermaid
flowchart TD
    A["Start function"] --> B["Create state for parameters"]
    B --> C["Visit statements in order"]
    C --> D{"Expression kind"}
    D -->|move x| E["Reject if moved or borrowed; mark moved"]
    D -->|borrow x| F["Reject if mutable borrow exists; add immutable borrow"]
    D -->|borrow mut x| G["Reject if any borrow exists; add mutable borrow"]
    D -->|use x| H["Reject if moved"]
    D -->|return borrow x| I["Reject local borrow escape"]
    E --> C
    F --> C
    G --> C
    H --> C
    I --> C
```

## Translator Pseudocode

```text
compile_file(path):
    source = read(path)
    imported_programs = resolve_imports(source)
    tokens = lex(source)
    ast = parse(tokens)
    merged_ast = imported_programs + ast
    semantic_analyze(merged_ast)
    ownership_check(merged_ast)
    optimized_ast = constant_fold(merged_ast)
    escape_info = analyze_escapes(optimized_ast)
    llvm_ir = generate_llvm(optimized_ast, escape_info)
    return llvm_ir
```

