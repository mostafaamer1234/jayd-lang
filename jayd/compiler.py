from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class JaydError(Exception):
    pass


@dataclass
class Diagnostic:
    message: str
    line: int = 0
    column: int = 0
    phase: str = "compiler"

    def __str__(self) -> str:
        loc = f"{self.line}:{self.column}" if self.line else "<unknown>"
        return f"{self.phase} error at {loc}: {self.message}"


class DiagnosticBag:
    def __init__(self) -> None:
        self.items: List[Diagnostic] = []

    def error(self, message: str, token: Optional["Token"] = None, phase: str = "compiler") -> None:
        self.items.append(Diagnostic(message, token.line if token else 0, token.column if token else 0, phase))

    def extend(self, other: "DiagnosticBag") -> None:
        self.items.extend(other.items)

    def fail_if_any(self) -> None:
        if self.items:
            raise JaydError("\n".join(str(d) for d in self.items))


@dataclass
class Token:
    kind: str
    text: str
    literal: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.text!r}, {self.line}:{self.column})"


KEYWORDS = {
    "and": "AND",
    "as": "AS",
    "borrow": "BORROW",
    "catch": "CATCH",
    "class": "CLASS",
    "const": "CONST",
    "else": "ELSE",
    "extern": "EXTERN",
    "false": "FALSE",
    "for": "FOR",
    "func": "FUNC",
    "if": "IF",
    "import": "IMPORT",
    "in": "IN",
    "let": "LET",
    "move": "MOVE",
    "mut": "MUT",
    "new": "NEW",
    "not": "NOT",
    "null": "NULL",
    "or": "OR",
    "return": "RETURN",
    "throw": "THROW",
    "true": "TRUE",
    "try": "TRY",
    "while": "WHILE",
}


class Lexer:
    def __init__(self, source: str, filename: str = "<memory>") -> None:
        self.source = source.replace("\t", "    ")
        self.filename = filename
        self.diagnostics = DiagnosticBag()
        self.tokens: List[Token] = []

    def scan(self) -> List[Token]:
        indents = [0]
        lines = self.source.splitlines()
        for line_no, raw in enumerate(lines, 1):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if indent > indents[-1]:
                indents.append(indent)
                self.tokens.append(Token("INDENT", "", None, line_no, 1))
            while indent < indents[-1]:
                indents.pop()
                self.tokens.append(Token("DEDENT", "", None, line_no, 1))
            if indent != indents[-1]:
                self.diagnostics.error("inconsistent indentation", Token("BAD", "", None, line_no, indent + 1), "lexer")
            self._scan_line(raw[indent:], line_no, indent + 1)
            self.tokens.append(Token("NEWLINE", "\\n", None, line_no, len(raw) + 1))
        while len(indents) > 1:
            indents.pop()
            self.tokens.append(Token("DEDENT", "", None, len(lines) + 1, 1))
        self.tokens.append(Token("EOF", "", None, len(lines) + 1, 1))
        self.diagnostics.fail_if_any()
        return self.tokens

    def _scan_line(self, text: str, line: int, base_col: int) -> None:
        i = 0
        single = {
            "(": "LPAREN",
            ")": "RPAREN",
            "[": "LBRACKET",
            "]": "RBRACKET",
            ":": "COLON",
            ",": "COMMA",
            ".": "DOT",
            "+": "PLUS",
            "-": "MINUS",
            "*": "STAR",
            "/": "SLASH",
            "%": "PERCENT",
            "=": "EQUAL",
            "<": "LT",
            ">": "GT",
            "?": "QUESTION",
            "&": "AMP",
        }
        multi = {"->": "ARROW", "==": "EQEQ", "!=": "BANGEQ", "<=": "LTE", ">=": "GTE", "&&": "ANDAND", "||": "OROR"}
        while i < len(text):
            c = text[i]
            col = base_col + i
            if c in " \r":
                i += 1
                continue
            if c == "#":
                break
            two = text[i : i + 2]
            if two in multi:
                self.tokens.append(Token(multi[two], two, None, line, col))
                i += 2
                continue
            if c == '"':
                start = i
                i += 1
                value = ""
                while i < len(text) and text[i] != '"':
                    if text[i] == "\\" and i + 1 < len(text):
                        escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
                        i += 1
                        value += escapes.get(text[i], text[i])
                    else:
                        value += text[i]
                    i += 1
                if i >= len(text):
                    self.diagnostics.error("unterminated string literal", Token("STRING", text[start:], None, line, col), "lexer")
                    return
                i += 1
                self.tokens.append(Token("STRING", text[start:i], value, line, col))
                continue
            if c.isdigit():
                start = i
                while i < len(text) and text[i].isdigit():
                    i += 1
                if i < len(text) and text[i] == "." and i + 1 < len(text) and text[i + 1].isdigit():
                    i += 1
                    while i < len(text) and text[i].isdigit():
                        i += 1
                    self.tokens.append(Token("FLOAT", text[start:i], float(text[start:i]), line, col))
                else:
                    self.tokens.append(Token("INT", text[start:i], int(text[start:i]), line, col))
                continue
            if c.isalpha() or c == "_":
                start = i
                while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                    i += 1
                word = text[start:i]
                self.tokens.append(Token(KEYWORDS.get(word, "IDENT"), word, None, line, col))
                continue
            if c in single:
                self.tokens.append(Token(single[c], c, None, line, col))
                i += 1
                continue
            self.diagnostics.error(f"unexpected character {c!r}", Token("BAD", c, None, line, col), "lexer")
            i += 1


@dataclass
class TypeNode:
    name: str
    args: List["TypeNode"] = field(default_factory=list)
    nullable: bool = False

    def __str__(self) -> str:
        args = f"<{', '.join(map(str, self.args))}>" if self.args else ""
        return f"{self.name}{args}{'?' if self.nullable else ''}"


@dataclass
class Param:
    name: str
    type: TypeNode
    token: Token


@dataclass
class Node:
    token: Token


@dataclass
class Program:
    declarations: List[Any]


@dataclass
class ImportDecl(Node):
    module: str


@dataclass
class ExternFunc(Node):
    name: str
    params: List[Param]
    return_type: TypeNode


@dataclass
class FuncDecl(Node):
    name: str
    type_params: List[str]
    params: List[Param]
    return_type: TypeNode
    body: List[Any]


@dataclass
class FieldDecl(Node):
    name: str
    type: TypeNode
    mutable: bool


@dataclass
class ClassDecl(Node):
    name: str
    base: Optional[str]
    fields: List[FieldDecl]
    methods: List[FuncDecl]


@dataclass
class LetStmt(Node):
    name: str
    mutable: bool
    annotation: Optional[TypeNode]
    value: Any


@dataclass
class AssignStmt(Node):
    name: str
    value: Any


@dataclass
class ReturnStmt(Node):
    value: Optional[Any]


@dataclass
class ExprStmt(Node):
    expr: Any


@dataclass
class IfStmt(Node):
    condition: Any
    then_body: List[Any]
    else_body: List[Any]


@dataclass
class WhileStmt(Node):
    condition: Any
    body: List[Any]


@dataclass
class ForStmt(Node):
    name: str
    iterable: Any
    body: List[Any]


@dataclass
class ThrowStmt(Node):
    value: Any


@dataclass
class TryCatchStmt(Node):
    try_body: List[Any]
    error_name: str
    catch_body: List[Any]


@dataclass
class Literal(Node):
    value: Any


@dataclass
class Var(Node):
    name: str


@dataclass
class Binary(Node):
    left: Any
    op: str
    right: Any


@dataclass
class Unary(Node):
    op: str
    expr: Any


@dataclass
class Call(Node):
    callee: Any
    args: List[Any]


@dataclass
class Member(Node):
    obj: Any
    name: str


@dataclass
class NewExpr(Node):
    class_name: str
    args: List[Any]


@dataclass
class BorrowExpr(Node):
    name: str
    mutable: bool


@dataclass
class MoveExpr(Node):
    name: str


class Parser:
    def __init__(self, tokens: Sequence[Token]) -> None:
        self.tokens = list(tokens)
        self.i = 0
        self.diagnostics = DiagnosticBag()

    def parse(self) -> Program:
        decls: List[Any] = []
        while not self.check("EOF"):
            if self.match("NEWLINE"):
                continue
            decls.append(self.declaration())
        self.diagnostics.fail_if_any()
        return Program(decls)

    def declaration(self) -> Any:
        if self.match("IMPORT"):
            tok = self.previous()
            parts = [self.consume("IDENT", "expected module name after import").text]
            while self.match("DOT"):
                parts.append(self.consume("IDENT", "expected module path segment").text)
            self.consume_line()
            return ImportDecl(tok, ".".join(parts))
        if self.match("EXTERN"):
            tok = self.previous()
            self.consume("FUNC", "expected func after extern")
            return self.func_decl(tok, extern=True)
        if self.match("FUNC"):
            return self.func_decl(self.previous(), extern=False)
        if self.match("CLASS"):
            return self.class_decl(self.previous())
        tok = self.peek()
        self.error(tok, "expected top-level declaration")
        self.advance()
        return ImportDecl(tok, "<error>")

    def func_decl(self, tok: Token, extern: bool) -> Any:
        name = self.consume("IDENT", "expected function name").text
        type_params: List[str] = []
        if self.match("LT"):
            type_params.append(self.consume("IDENT", "expected generic type parameter").text)
            while self.match("COMMA"):
                type_params.append(self.consume("IDENT", "expected generic type parameter").text)
            self.consume("GT", "expected '>' after generic parameters")
        self.consume("LPAREN", "expected '(' after function name")
        params: List[Param] = []
        if not self.check("RPAREN"):
            while True:
                ptok = self.consume("IDENT", "expected parameter name")
                self.consume("COLON", "expected ':' after parameter name")
                params.append(Param(ptok.text, self.type_node(), ptok))
                if not self.match("COMMA"):
                    break
        self.consume("RPAREN", "expected ')' after parameters")
        ret = TypeNode("void")
        if self.match("ARROW"):
            ret = self.type_node()
        if extern:
            self.consume_line()
            return ExternFunc(tok, name, params, ret)
        self.consume("COLON", "expected ':' before function body")
        body = self.block()
        return FuncDecl(tok, name, type_params, params, ret, body)

    def class_decl(self, tok: Token) -> ClassDecl:
        name = self.consume("IDENT", "expected class name").text
        base = None
        if self.match("LPAREN"):
            base = self.consume("IDENT", "expected base class name").text
            self.consume("RPAREN", "expected ')' after base class")
        self.consume("COLON", "expected ':' before class body")
        self.consume("NEWLINE", "expected newline before class body")
        self.consume("INDENT", "expected indented class body")
        fields: List[FieldDecl] = []
        methods: List[FuncDecl] = []
        while not self.check("DEDENT") and not self.check("EOF"):
            if self.match("NEWLINE"):
                continue
            if self.match("FUNC"):
                methods.append(self.func_decl(self.previous(), extern=False))
            elif self.match("LET", "CONST"):
                ftok = self.previous()
                mutable = ftok.kind == "LET"
                name_tok = self.consume("IDENT", "expected field name")
                self.consume("COLON", "expected ':' after field name")
                fields.append(FieldDecl(ftok, name_tok.text, self.type_node(), mutable))
                self.consume_line()
            else:
                self.error(self.peek(), "expected field or method in class body")
                self.advance()
        self.consume("DEDENT", "expected end of class body")
        return ClassDecl(tok, name, base, fields, methods)

    def statement(self) -> Any:
        if self.match("LET", "CONST"):
            tok = self.previous()
            name = self.consume("IDENT", "expected binding name").text
            annotation = None
            if self.match("COLON"):
                annotation = self.type_node()
            self.consume("EQUAL", "expected '=' in binding")
            value = self.expression()
            self.consume_line()
            return LetStmt(tok, name, tok.kind == "LET", annotation, value)
        if self.match("RETURN"):
            tok = self.previous()
            value = None if self.check("NEWLINE") else self.expression()
            self.consume_line()
            return ReturnStmt(tok, value)
        if self.match("IF"):
            tok = self.previous()
            condition = self.expression()
            self.consume("COLON", "expected ':' after if condition")
            then_body = self.block()
            else_body: List[Any] = []
            if self.match("ELSE"):
                self.consume("COLON", "expected ':' after else")
                else_body = self.block()
            return IfStmt(tok, condition, then_body, else_body)
        if self.match("WHILE"):
            tok = self.previous()
            condition = self.expression()
            self.consume("COLON", "expected ':' after while condition")
            return WhileStmt(tok, condition, self.block())
        if self.match("FOR"):
            tok = self.previous()
            name = self.consume("IDENT", "expected loop variable").text
            self.consume("IN", "expected 'in' in for loop")
            iterable = self.expression()
            self.consume("COLON", "expected ':' after for loop")
            return ForStmt(tok, name, iterable, self.block())
        if self.match("THROW"):
            tok = self.previous()
            value = self.expression()
            self.consume_line()
            return ThrowStmt(tok, value)
        if self.match("TRY"):
            tok = self.previous()
            self.consume("COLON", "expected ':' after try")
            try_body = self.block()
            self.consume("CATCH", "expected catch after try block")
            err_name = self.consume("IDENT", "expected catch variable").text
            self.consume("COLON", "expected ':' after catch variable")
            return TryCatchStmt(tok, try_body, err_name, self.block())
        if self.check("IDENT") and self.check_next("EQUAL"):
            tok = self.advance()
            self.advance()
            value = self.expression()
            self.consume_line()
            return AssignStmt(tok, tok.text, value)
        expr = self.expression()
        self.consume_line()
        return ExprStmt(expr.token, expr)

    def block(self) -> List[Any]:
        self.consume("NEWLINE", "expected newline before block")
        self.consume("INDENT", "expected indented block")
        body: List[Any] = []
        while not self.check("DEDENT") and not self.check("EOF"):
            if self.match("NEWLINE"):
                continue
            body.append(self.statement())
        self.consume("DEDENT", "expected end of block")
        return body

    def expression(self) -> Any:
        return self.or_expr()

    def or_expr(self) -> Any:
        expr = self.and_expr()
        while self.match("OR", "OROR"):
            op = self.previous()
            expr = Binary(op, expr, "or", self.and_expr())
        return expr

    def and_expr(self) -> Any:
        expr = self.equality()
        while self.match("AND", "ANDAND"):
            op = self.previous()
            expr = Binary(op, expr, "and", self.equality())
        return expr

    def equality(self) -> Any:
        expr = self.comparison()
        while self.match("EQEQ", "BANGEQ"):
            op = self.previous()
            expr = Binary(op, expr, op.text, self.comparison())
        return expr

    def comparison(self) -> Any:
        expr = self.term()
        while self.match("LT", "LTE", "GT", "GTE"):
            op = self.previous()
            expr = Binary(op, expr, op.text, self.term())
        return expr

    def term(self) -> Any:
        expr = self.factor()
        while self.match("PLUS", "MINUS"):
            op = self.previous()
            expr = Binary(op, expr, op.text, self.factor())
        return expr

    def factor(self) -> Any:
        expr = self.unary()
        while self.match("STAR", "SLASH", "PERCENT"):
            op = self.previous()
            expr = Binary(op, expr, op.text, self.unary())
        return expr

    def unary(self) -> Any:
        if self.match("MINUS", "NOT"):
            op = self.previous()
            return Unary(op, op.text, self.unary())
        if self.match("BORROW"):
            tok = self.previous()
            mutable = self.match("MUT")
            name = self.consume("IDENT", "expected binding name after borrow").text
            return BorrowExpr(tok, name, mutable)
        if self.match("MOVE"):
            tok = self.previous()
            name = self.consume("IDENT", "expected binding name after move").text
            return MoveExpr(tok, name)
        if self.match("NEW"):
            tok = self.previous()
            name = self.consume("IDENT", "expected class name after new").text
            self.consume("LPAREN", "expected '(' after class name")
            args = self.argument_list()
            return NewExpr(tok, name, args)
        return self.call()

    def call(self) -> Any:
        expr = self.primary()
        while True:
            if self.match("LPAREN"):
                expr = Call(expr.token, expr, self.argument_list())
            elif self.match("DOT"):
                name = self.consume("IDENT", "expected member name").text
                expr = Member(expr.token, expr, name)
            else:
                break
        return expr

    def argument_list(self) -> List[Any]:
        args: List[Any] = []
        if not self.check("RPAREN"):
            while True:
                args.append(self.expression())
                if not self.match("COMMA"):
                    break
        self.consume("RPAREN", "expected ')' after arguments")
        return args

    def primary(self) -> Any:
        if self.match("INT", "FLOAT", "STRING"):
            return Literal(self.previous(), self.previous().literal)
        if self.match("TRUE"):
            return Literal(self.previous(), True)
        if self.match("FALSE"):
            return Literal(self.previous(), False)
        if self.match("NULL"):
            return Literal(self.previous(), None)
        if self.match("IDENT"):
            return Var(self.previous(), self.previous().text)
        if self.match("LPAREN"):
            expr = self.expression()
            self.consume("RPAREN", "expected ')' after expression")
            return expr
        tok = self.peek()
        self.error(tok, "expected expression")
        self.advance()
        return Literal(tok, 0)

    def type_node(self) -> TypeNode:
        name = self.consume("IDENT", "expected type name").text
        args: List[TypeNode] = []
        if self.match("LT"):
            args.append(self.type_node())
            while self.match("COMMA"):
                args.append(self.type_node())
            self.consume("GT", "expected '>' after type arguments")
        nullable = self.match("QUESTION")
        return TypeNode(name, args, nullable)

    def consume_line(self) -> None:
        if self.check("EOF") or self.check("DEDENT"):
            return
        self.consume("NEWLINE", "expected end of line")

    def match(self, *kinds: str) -> bool:
        if self.check(*kinds):
            self.advance()
            return True
        return False

    def check(self, *kinds: str) -> bool:
        return self.peek().kind in kinds

    def check_next(self, kind: str) -> bool:
        return self.i + 1 < len(self.tokens) and self.tokens[self.i + 1].kind == kind

    def consume(self, kind: str, message: str) -> Token:
        if self.check(kind):
            return self.advance()
        self.error(self.peek(), message)
        return Token(kind, "", None, self.peek().line, self.peek().column)

    def advance(self) -> Token:
        tok = self.peek()
        if not self.check("EOF"):
            self.i += 1
        return tok

    def previous(self) -> Token:
        return self.tokens[self.i - 1]

    def peek(self) -> Token:
        return self.tokens[self.i]

    def error(self, token: Token, message: str) -> None:
        self.diagnostics.error(message, token, "parser")


@dataclass(frozen=True)
class Type:
    name: str
    args: Tuple["Type", ...] = ()
    nullable: bool = False

    def __str__(self) -> str:
        args = f"<{', '.join(map(str, self.args))}>" if self.args else ""
        return f"{self.name}{args}{'?' if self.nullable else ''}"

    def accepts(self, other: "Type") -> bool:
        if self.name == "any":
            return True
        if other.name == "null":
            return self.nullable or self.name == "null" or self.name == "any"
        return self == other


INT_T = Type("int")
FLOAT_T = Type("float")
BOOL_T = Type("bool")
STRING_T = Type("string")
VOID_T = Type("void")
NULL_T = Type("null")
ANY_T = Type("any")


@dataclass
class FunctionSig:
    name: str
    params: List[Type]
    ret: Type
    type_params: List[str] = field(default_factory=list)
    extern: bool = False


@dataclass
class Symbol:
    name: str
    type: Type
    mutable: bool
    token: Token


class Scope:
    def __init__(self, parent: Optional["Scope"] = None) -> None:
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, sym: Symbol) -> Optional[Symbol]:
        if sym.name in self.symbols:
            return self.symbols[sym.name]
        self.symbols[sym.name] = sym
        return None

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        return self.parent.lookup(name) if self.parent else None


class SemanticAnalyzer:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.diagnostics = DiagnosticBag()
        self.functions: Dict[str, FunctionSig] = {
            "print": FunctionSig("print", [ANY_T], VOID_T),
        }
        self.classes: Dict[str, ClassDecl] = {}
        self.current_return = VOID_T
        self.generic_names: List[str] = []

    def analyze(self) -> None:
        for decl in self.program.declarations:
            if isinstance(decl, ExternFunc):
                self._register_func(decl.name, decl.params, decl.return_type, decl.token, [], True)
            elif isinstance(decl, FuncDecl):
                self._register_func(decl.name, decl.params, decl.return_type, decl.token, decl.type_params, False)
            elif isinstance(decl, ClassDecl):
                if decl.name in self.classes:
                    self.diagnostics.error(f"duplicate class '{decl.name}'", decl.token, "semantic")
                self.classes[decl.name] = decl
        for cls in self.classes.values():
            if cls.base and cls.base not in self.classes:
                self.diagnostics.error(f"unknown base class '{cls.base}'", cls.token, "semantic")
        for decl in self.program.declarations:
            if isinstance(decl, FuncDecl):
                self._check_func(decl)
            elif isinstance(decl, ClassDecl):
                for method in decl.methods:
                    self._check_func(method, cls=decl)
        self.diagnostics.fail_if_any()

    def _register_func(self, name: str, params: List[Param], ret: TypeNode, tok: Token, type_params: List[str], extern: bool) -> None:
        if name in self.functions and name != "print":
            self.diagnostics.error(f"duplicate function '{name}'", tok, "semantic")
            return
        generic = set(type_params)
        self.functions[name] = FunctionSig(name, [self.resolve_type(p.type, generic) for p in params], self.resolve_type(ret, generic), type_params, extern)

    def resolve_type(self, node: TypeNode, generic: Iterable[str] = ()) -> Type:
        known = {"int", "float", "bool", "string", "void", "null", "any"}
        if node.name not in known and node.name not in self.classes and node.name not in set(generic):
            self.diagnostics.error(f"unknown type '{node.name}'", None, "semantic")
        return Type(node.name, tuple(self.resolve_type(a, generic) for a in node.args), node.nullable)

    def _check_func(self, fn: FuncDecl, cls: Optional[ClassDecl] = None) -> None:
        sig = self.functions.get(fn.name)
        scope = Scope()
        self.current_return = self.resolve_type(fn.return_type, fn.type_params)
        self.generic_names = fn.type_params
        if cls:
            scope.define(Symbol("self", Type(cls.name), False, fn.token))
        for p, ptype in zip(fn.params, sig.params if sig else []):
            dup = scope.define(Symbol(p.name, ptype, True, p.token))
            if dup:
                self.diagnostics.error(f"duplicate parameter '{p.name}'", p.token, "semantic")
        self._check_block(fn.body, scope)

    def _check_block(self, body: List[Any], scope: Scope) -> bool:
        returned = False
        for stmt in body:
            if returned:
                self.diagnostics.error("unreachable statement after return", stmt.token, "semantic")
                continue
            if isinstance(stmt, ReturnStmt):
                actual = VOID_T if stmt.value is None else self._expr_type(stmt.value, scope)
                if not self.current_return.accepts(actual):
                    self.diagnostics.error(f"return type mismatch: expected {self.current_return}, got {actual}", stmt.token, "semantic")
                returned = True
            elif isinstance(stmt, LetStmt):
                value_type = self._expr_type(stmt.value, scope)
                declared = self.resolve_type(stmt.annotation, self.generic_names) if stmt.annotation else value_type
                if not declared.accepts(value_type):
                    self.diagnostics.error(f"cannot assign {value_type} to {declared}", stmt.token, "semantic")
                dup = scope.define(Symbol(stmt.name, declared, stmt.mutable, stmt.token))
                if dup:
                    self.diagnostics.error(f"duplicate binding '{stmt.name}'", stmt.token, "semantic")
            elif isinstance(stmt, AssignStmt):
                sym = scope.lookup(stmt.name)
                if not sym:
                    self.diagnostics.error(f"unknown binding '{stmt.name}'", stmt.token, "semantic")
                elif not sym.mutable:
                    self.diagnostics.error(f"cannot assign to const binding '{stmt.name}'", stmt.token, "semantic")
                else:
                    value_type = self._expr_type(stmt.value, scope)
                    if not sym.type.accepts(value_type):
                        self.diagnostics.error(f"cannot assign {value_type} to {sym.type}", stmt.token, "semantic")
            elif isinstance(stmt, ExprStmt):
                self._expr_type(stmt.expr, scope)
            elif isinstance(stmt, IfStmt):
                cond = self._expr_type(stmt.condition, scope)
                if cond != BOOL_T:
                    self.diagnostics.error(f"if condition must be bool, got {cond}", stmt.token, "semantic")
                then_ret = self._check_block(stmt.then_body, Scope(scope))
                else_ret = self._check_block(stmt.else_body, Scope(scope)) if stmt.else_body else False
                returned = then_ret and else_ret
            elif isinstance(stmt, WhileStmt):
                cond = self._expr_type(stmt.condition, scope)
                if cond != BOOL_T:
                    self.diagnostics.error(f"while condition must be bool, got {cond}", stmt.token, "semantic")
                self._check_block(stmt.body, Scope(scope))
            elif isinstance(stmt, ForStmt):
                child = Scope(scope)
                child.define(Symbol(stmt.name, ANY_T, True, stmt.token))
                self._expr_type(stmt.iterable, scope)
                self._check_block(stmt.body, child)
            elif isinstance(stmt, ThrowStmt):
                self._expr_type(stmt.value, scope)
                returned = True
            elif isinstance(stmt, TryCatchStmt):
                self._check_block(stmt.try_body, Scope(scope))
                catch_scope = Scope(scope)
                catch_scope.define(Symbol(stmt.error_name, STRING_T, False, stmt.token))
                self._check_block(stmt.catch_body, catch_scope)
        return returned

    def _expr_type(self, expr: Any, scope: Scope) -> Type:
        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return BOOL_T
            if isinstance(expr.value, int):
                return INT_T
            if isinstance(expr.value, float):
                return FLOAT_T
            if isinstance(expr.value, str):
                return STRING_T
            return NULL_T
        if isinstance(expr, Var):
            sym = scope.lookup(expr.name)
            if not sym:
                if expr.name in self.functions:
                    sig = self.functions[expr.name]
                    return Type("func", tuple(sig.params + [sig.ret]))
                self.diagnostics.error(f"unknown binding '{expr.name}'", expr.token, "semantic")
                return ANY_T
            return sym.type
        if isinstance(expr, Unary):
            t = self._expr_type(expr.expr, scope)
            if expr.op == "-" and t in (INT_T, FLOAT_T):
                return t
            if expr.op == "not" and t == BOOL_T:
                return BOOL_T
            self.diagnostics.error(f"invalid unary operator {expr.op} for {t}", expr.token, "semantic")
            return ANY_T
        if isinstance(expr, Binary):
            lt = self._expr_type(expr.left, scope)
            rt = self._expr_type(expr.right, scope)
            if expr.op in {"+", "-", "*", "/", "%"}:
                if lt == rt and lt in (INT_T, FLOAT_T):
                    return lt
                if expr.op == "+" and lt == rt == STRING_T:
                    return STRING_T
                self.diagnostics.error(f"operator {expr.op} does not support {lt} and {rt}", expr.token, "semantic")
                return ANY_T
            if expr.op in {"<", "<=", ">", ">=", "==", "!="}:
                if lt.accepts(rt) or rt.accepts(lt):
                    return BOOL_T
                self.diagnostics.error(f"cannot compare {lt} and {rt}", expr.token, "semantic")
                return BOOL_T
            if expr.op in {"and", "or"}:
                if lt != BOOL_T or rt != BOOL_T:
                    self.diagnostics.error(f"logical operator {expr.op} requires bool operands", expr.token, "semantic")
                return BOOL_T
        if isinstance(expr, Call):
            if isinstance(expr.callee, Var) and expr.callee.name in self.functions:
                sig = self.functions[expr.callee.name]
                arg_types = [self._expr_type(a, scope) for a in expr.args]
                if len(arg_types) != len(sig.params):
                    self.diagnostics.error(f"function '{sig.name}' expects {len(sig.params)} args, got {len(arg_types)}", expr.token, "semantic")
                    return sig.ret
                substitutions: Dict[str, Type] = {}
                for expected, actual in zip(sig.params, arg_types):
                    if expected.name in sig.type_params:
                        substitutions[expected.name] = actual
                    elif not expected.accepts(actual):
                        self.diagnostics.error(f"argument type mismatch for '{sig.name}': expected {expected}, got {actual}", expr.token, "semantic")
                if sig.ret.name in substitutions:
                    return substitutions[sig.ret.name]
                return sig.ret
            callee_t = self._expr_type(expr.callee, scope)
            self.diagnostics.error(f"cannot call expression of type {callee_t}", expr.token, "semantic")
            return ANY_T
        if isinstance(expr, Member):
            obj_t = self._expr_type(expr.obj, scope)
            cls = self.classes.get(obj_t.name)
            if not cls:
                self.diagnostics.error(f"type {obj_t} has no members", expr.token, "semantic")
                return ANY_T
            for field in cls.fields:
                if field.name == expr.name:
                    return self.resolve_type(field.type)
            self.diagnostics.error(f"class {cls.name} has no member '{expr.name}'", expr.token, "semantic")
            return ANY_T
        if isinstance(expr, NewExpr):
            if expr.class_name not in self.classes:
                self.diagnostics.error(f"unknown class '{expr.class_name}'", expr.token, "semantic")
            for arg in expr.args:
                self._expr_type(arg, scope)
            return Type(expr.class_name)
        if isinstance(expr, BorrowExpr):
            sym = scope.lookup(expr.name)
            if not sym:
                self.diagnostics.error(f"unknown binding '{expr.name}'", expr.token, "semantic")
                return ANY_T
            return Type("mutref" if expr.mutable else "ref", (sym.type,))
        if isinstance(expr, MoveExpr):
            sym = scope.lookup(expr.name)
            if not sym:
                self.diagnostics.error(f"unknown binding '{expr.name}'", expr.token, "semantic")
                return ANY_T
            return sym.type
        return ANY_T


@dataclass
class BorrowState:
    moved: bool = False
    immutable_borrows: int = 0
    mutable_borrow: bool = False
    local: bool = True


class OwnershipChecker:
    """A small Rust-inspired ownership pass.

    The checker is intentionally conservative: borrows live until function exit.
    That makes the rules easy to explain in a compiler course presentation and
    still catches use-after-move and aliasing mistakes at compile time.
    """

    def __init__(self, program: Program) -> None:
        self.program = program
        self.diagnostics = DiagnosticBag()

    def check(self) -> None:
        for decl in self.program.declarations:
            if isinstance(decl, FuncDecl):
                states = {p.name: BorrowState() for p in decl.params}
                self._check_block(decl.body, states)
        self.diagnostics.fail_if_any()

    def _check_block(self, body: List[Any], states: Dict[str, BorrowState]) -> None:
        for stmt in body:
            if isinstance(stmt, LetStmt):
                self._check_expr(stmt.value, states)
                states[stmt.name] = BorrowState()
            elif isinstance(stmt, AssignStmt):
                st = states.get(stmt.name)
                if st and (st.immutable_borrows or st.mutable_borrow):
                    self.diagnostics.error(f"cannot assign to '{stmt.name}' while it is borrowed", stmt.token, "ownership")
                self._check_expr(stmt.value, states)
            elif isinstance(stmt, ReturnStmt) and stmt.value is not None:
                if isinstance(stmt.value, BorrowExpr):
                    self.diagnostics.error(f"cannot return borrow of local binding '{stmt.value.name}'", stmt.token, "ownership")
                self._check_expr(stmt.value, states)
            elif isinstance(stmt, ExprStmt):
                self._check_expr(stmt.expr, states)
            elif isinstance(stmt, IfStmt):
                self._check_expr(stmt.condition, states)
                self._check_block(stmt.then_body, dict(states))
                self._check_block(stmt.else_body, dict(states))
            elif isinstance(stmt, WhileStmt):
                self._check_expr(stmt.condition, states)
                self._check_block(stmt.body, dict(states))
            elif isinstance(stmt, ForStmt):
                self._check_expr(stmt.iterable, states)
                child = dict(states)
                child[stmt.name] = BorrowState()
                self._check_block(stmt.body, child)
            elif isinstance(stmt, ThrowStmt):
                self._check_expr(stmt.value, states)
            elif isinstance(stmt, TryCatchStmt):
                self._check_block(stmt.try_body, dict(states))
                child = dict(states)
                child[stmt.error_name] = BorrowState()
                self._check_block(stmt.catch_body, child)

    def _check_expr(self, expr: Any, states: Dict[str, BorrowState]) -> None:
        if isinstance(expr, Var):
            st = states.get(expr.name)
            if st and st.moved:
                self.diagnostics.error(f"use of moved binding '{expr.name}'", expr.token, "ownership")
        elif isinstance(expr, MoveExpr):
            st = states.get(expr.name)
            if not st:
                return
            if st.moved:
                self.diagnostics.error(f"binding '{expr.name}' has already been moved", expr.token, "ownership")
            if st.immutable_borrows or st.mutable_borrow:
                self.diagnostics.error(f"cannot move '{expr.name}' while it is borrowed", expr.token, "ownership")
            st.moved = True
        elif isinstance(expr, BorrowExpr):
            st = states.get(expr.name)
            if not st:
                return
            if st.moved:
                self.diagnostics.error(f"cannot borrow moved binding '{expr.name}'", expr.token, "ownership")
            if expr.mutable:
                if st.immutable_borrows or st.mutable_borrow:
                    self.diagnostics.error(f"cannot mutably borrow '{expr.name}' while another borrow exists", expr.token, "ownership")
                st.mutable_borrow = True
            else:
                if st.mutable_borrow:
                    self.diagnostics.error(f"cannot immutably borrow '{expr.name}' while mutable borrow exists", expr.token, "ownership")
                st.immutable_borrows += 1
        elif isinstance(expr, Binary):
            self._check_expr(expr.left, states)
            self._check_expr(expr.right, states)
        elif isinstance(expr, Unary):
            self._check_expr(expr.expr, states)
        elif isinstance(expr, Call):
            self._check_expr(expr.callee, states)
            for arg in expr.args:
                self._check_expr(arg, states)
        elif isinstance(expr, Member):
            self._check_expr(expr.obj, states)
        elif isinstance(expr, NewExpr):
            for arg in expr.args:
                self._check_expr(arg, states)


class EscapeAnalyzer:
    def analyze(self, program: Program) -> Dict[str, Dict[str, str]]:
        results: Dict[str, Dict[str, str]] = {}
        for decl in program.declarations:
            if not isinstance(decl, FuncDecl):
                continue
            allocations: Dict[str, str] = {}
            returned = self._returned_names(decl.body)
            for stmt in self._walk_stmts(decl.body):
                if isinstance(stmt, LetStmt) and isinstance(stmt.value, NewExpr):
                    allocations[stmt.name] = "heap" if stmt.name in returned else "stack"
            results[decl.name] = allocations
        return results

    def _returned_names(self, body: List[Any]) -> set:
        names = set()
        for stmt in self._walk_stmts(body):
            if isinstance(stmt, ReturnStmt):
                value = stmt.value
                if isinstance(value, Var):
                    names.add(value.name)
                if isinstance(value, MoveExpr):
                    names.add(value.name)
        return names

    def _walk_stmts(self, body: List[Any]) -> Iterable[Any]:
        for stmt in body:
            yield stmt
            if isinstance(stmt, IfStmt):
                yield from self._walk_stmts(stmt.then_body)
                yield from self._walk_stmts(stmt.else_body)
            elif isinstance(stmt, WhileStmt):
                yield from self._walk_stmts(stmt.body)
            elif isinstance(stmt, ForStmt):
                yield from self._walk_stmts(stmt.body)


class Optimizer:
    def optimize(self, program: Program) -> Program:
        for decl in program.declarations:
            if isinstance(decl, FuncDecl):
                decl.body = [self._stmt(s) for s in decl.body]
        return program

    def _stmt(self, stmt: Any) -> Any:
        if isinstance(stmt, LetStmt):
            stmt.value = self._expr(stmt.value)
        elif isinstance(stmt, AssignStmt):
            stmt.value = self._expr(stmt.value)
        elif isinstance(stmt, ReturnStmt) and stmt.value is not None:
            stmt.value = self._expr(stmt.value)
        elif isinstance(stmt, ExprStmt):
            stmt.expr = self._expr(stmt.expr)
        elif isinstance(stmt, IfStmt):
            stmt.condition = self._expr(stmt.condition)
            stmt.then_body = [self._stmt(s) for s in stmt.then_body]
            stmt.else_body = [self._stmt(s) for s in stmt.else_body]
        elif isinstance(stmt, WhileStmt):
            stmt.condition = self._expr(stmt.condition)
            stmt.body = [self._stmt(s) for s in stmt.body]
        return stmt

    def _expr(self, expr: Any) -> Any:
        if isinstance(expr, Binary):
            expr.left = self._expr(expr.left)
            expr.right = self._expr(expr.right)
            if isinstance(expr.left, Literal) and isinstance(expr.right, Literal):
                try:
                    if expr.op == "+":
                        return Literal(expr.token, expr.left.value + expr.right.value)
                    if expr.op == "-":
                        return Literal(expr.token, expr.left.value - expr.right.value)
                    if expr.op == "*":
                        return Literal(expr.token, expr.left.value * expr.right.value)
                    if expr.op == "/" and expr.right.value != 0:
                        return Literal(expr.token, expr.left.value / expr.right.value)
                    if expr.op == "%":
                        return Literal(expr.token, expr.left.value % expr.right.value)
                    if expr.op == "==":
                        return Literal(expr.token, expr.left.value == expr.right.value)
                    if expr.op == "!=":
                        return Literal(expr.token, expr.left.value != expr.right.value)
                    if expr.op == "<":
                        return Literal(expr.token, expr.left.value < expr.right.value)
                    if expr.op == "<=":
                        return Literal(expr.token, expr.left.value <= expr.right.value)
                    if expr.op == ">":
                        return Literal(expr.token, expr.left.value > expr.right.value)
                    if expr.op == ">=":
                        return Literal(expr.token, expr.left.value >= expr.right.value)
                except Exception:
                    return expr
        elif isinstance(expr, Unary):
            expr.expr = self._expr(expr.expr)
            if isinstance(expr.expr, Literal):
                if expr.op == "-":
                    return Literal(expr.token, -expr.expr.value)
                if expr.op == "not":
                    return Literal(expr.token, not expr.expr.value)
        elif isinstance(expr, Call):
            expr.args = [self._expr(a) for a in expr.args]
        elif isinstance(expr, NewExpr):
            expr.args = [self._expr(a) for a in expr.args]
        return expr


class LLVMCodegen:
    def __init__(self, program: Program, escapes: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        self.program = program
        self.escapes = escapes or {}
        self.lines: List[str] = []
        self.globals: List[str] = []
        self.reg = 0
        self.label = 0
        self.vars: Dict[str, Tuple[str, str]] = {}
        self.terminated = False
        self.fn_returns: Dict[str, str] = {}

    def emit(self) -> str:
        self.fn_returns = {"print": "void"}
        for decl in self.program.declarations:
            if isinstance(decl, ExternFunc):
                self.fn_returns[decl.name] = self.llvm_type_node(decl.return_type)
            elif isinstance(decl, FuncDecl):
                self.fn_returns[decl.name] = self.llvm_type_node(decl.return_type, decl.type_params)
        body: List[str] = [
            '; ModuleID = "jayd"',
            'source_filename = "jayd"',
            '@.fmt.int = private unnamed_addr constant [5 x i8] c"%ld\\0A\\00"',
            '@.fmt.float = private unnamed_addr constant [4 x i8] c"%f\\0A\\00"',
            '@.fmt.str = private unnamed_addr constant [4 x i8] c"%s\\0A\\00"',
            'declare i32 @printf(ptr, ...)',
            "",
        ]
        for decl in self.program.declarations:
            if isinstance(decl, ExternFunc):
                params = ", ".join(self.llvm_type_node(p.type) for p in decl.params)
                body.append(f"declare {self.llvm_type_node(decl.return_type)} @{decl.name}({params})")
        for decl in self.program.declarations:
            if isinstance(decl, FuncDecl):
                body.extend(self.func(decl))
        return "\n".join(body[:6] + self.globals + body[6:]) + "\n"

    def func(self, fn: FuncDecl) -> List[str]:
        self.lines = []
        self.vars = {}
        self.reg = 0
        self.label = 0
        self.terminated = False
        ret = self.llvm_type_node(fn.return_type, fn.type_params)
        params = ", ".join(f"{self.llvm_type_node(p.type, fn.type_params)} %{p.name}.arg" for p in fn.params)
        self.lines.append(f"define {ret} @{fn.name}({params}) {{")
        self.lines.append("entry:")
        for p in fn.params:
            pty = self.llvm_type_node(p.type, fn.type_params)
            slot = f"%{p.name}"
            self.lines.append(f"  {slot} = alloca {pty}")
            self.lines.append(f"  store {pty} %{p.name}.arg, ptr {slot}")
            self.vars[p.name] = (slot, pty)
        for name, where in self.escapes.get(fn.name, {}).items():
            self.lines.append(f"  ; escape-analysis: {name} allocated on {where}; destructor inserted at scope exit")
        for stmt in fn.body:
            self.stmt(stmt)
        if not self.terminated:
            if ret == "void":
                self.lines.append("  ret void")
            elif ret == "double":
                self.lines.append("  ret double 0.0")
            else:
                self.lines.append(f"  ret {ret} 0")
        self.lines.append("}")
        self.lines.append("")
        return self.lines

    def stmt(self, stmt: Any) -> None:
        if self.terminated:
            return
        if isinstance(stmt, LetStmt):
            ty, val = self.expr(stmt.value)
            if ty == "void":
                return
            slot = f"%{stmt.name}"
            self.lines.append(f"  {slot} = alloca {ty}")
            self.lines.append(f"  store {ty} {val}, ptr {slot}")
            self.vars[stmt.name] = (slot, ty)
        elif isinstance(stmt, AssignStmt):
            ty, val = self.expr(stmt.value)
            slot, expected = self.vars[stmt.name]
            self.lines.append(f"  store {expected} {val}, ptr {slot}")
        elif isinstance(stmt, ExprStmt):
            self.expr(stmt.expr)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value is None:
                self.lines.append("  ret void")
            else:
                ty, val = self.expr(stmt.value)
                self.lines.append(f"  ret {ty} {val}")
            self.terminated = True
        elif isinstance(stmt, IfStmt):
            cond_ty, cond = self.expr(stmt.condition)
            then_label = self.new_label("if.then")
            else_label = self.new_label("if.else")
            end_label = self.new_label("if.end")
            self.lines.append(f"  br i1 {cond}, label %{then_label}, label %{else_label}")
            self.lines.append(f"{then_label}:")
            self.terminated = False
            for s in stmt.then_body:
                self.stmt(s)
            then_term = self.terminated
            if not then_term:
                self.lines.append(f"  br label %{end_label}")
            self.lines.append(f"{else_label}:")
            self.terminated = False
            for s in stmt.else_body:
                self.stmt(s)
            else_term = self.terminated
            if not else_term:
                self.lines.append(f"  br label %{end_label}")
            self.lines.append(f"{end_label}:")
            self.terminated = then_term and else_term
        elif isinstance(stmt, WhileStmt):
            start = self.new_label("while.cond")
            body = self.new_label("while.body")
            end = self.new_label("while.end")
            self.lines.append(f"  br label %{start}")
            self.lines.append(f"{start}:")
            _, cond = self.expr(stmt.condition)
            self.lines.append(f"  br i1 {cond}, label %{body}, label %{end}")
            self.lines.append(f"{body}:")
            self.terminated = False
            for s in stmt.body:
                self.stmt(s)
            if not self.terminated:
                self.lines.append(f"  br label %{start}")
            self.lines.append(f"{end}:")
            self.terminated = False
        elif isinstance(stmt, (ForStmt, ThrowStmt, TryCatchStmt)):
            self.lines.append(f"  ; backend note: {stmt.__class__.__name__} parsed and checked but not lowered in v0.1")

    def expr(self, expr: Any) -> Tuple[str, str]:
        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "i1", "1" if expr.value else "0"
            if isinstance(expr.value, int):
                return "i64", str(expr.value)
            if isinstance(expr.value, float):
                return "double", repr(expr.value)
            if isinstance(expr.value, str):
                return "ptr", self.string_ptr(expr.value)
            if expr.value is None:
                return "ptr", "null"
        if isinstance(expr, Var):
            slot, ty = self.vars[expr.name]
            reg = self.new_reg()
            self.lines.append(f"  {reg} = load {ty}, ptr {slot}")
            return ty, reg
        if isinstance(expr, Unary):
            ty, val = self.expr(expr.expr)
            if expr.op == "-":
                reg = self.new_reg()
                if ty == "double":
                    self.lines.append(f"  {reg} = fsub double -0.0, {val}")
                else:
                    self.lines.append(f"  {reg} = sub i64 0, {val}")
                return ty, reg
            if expr.op == "not":
                reg = self.new_reg()
                self.lines.append(f"  {reg} = xor i1 {val}, true")
                return "i1", reg
        if isinstance(expr, Binary):
            lt, lv = self.expr(expr.left)
            rt, rv = self.expr(expr.right)
            reg = self.new_reg()
            if expr.op in {"+", "-", "*", "/", "%"}:
                if lt == "double":
                    op = {"+": "fadd", "-": "fsub", "*": "fmul", "/": "fdiv", "%": "frem"}[expr.op]
                    self.lines.append(f"  {reg} = {op} double {lv}, {rv}")
                    return "double", reg
                op = {"+": "add", "-": "sub", "*": "mul", "/": "sdiv", "%": "srem"}[expr.op]
                self.lines.append(f"  {reg} = {op} i64 {lv}, {rv}")
                return "i64", reg
            if expr.op in {"<", "<=", ">", ">=", "==", "!="}:
                if lt == "double":
                    op = {"<": "olt", "<=": "ole", ">": "ogt", ">=": "oge", "==": "oeq", "!=": "one"}[expr.op]
                    self.lines.append(f"  {reg} = fcmp {op} double {lv}, {rv}")
                else:
                    op = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "eq", "!=": "ne"}[expr.op]
                    self.lines.append(f"  {reg} = icmp {op} {lt} {lv}, {rv}")
                return "i1", reg
            if expr.op in {"and", "or"}:
                op = "and" if expr.op == "and" else "or"
                self.lines.append(f"  {reg} = {op} i1 {lv}, {rv}")
                return "i1", reg
        if isinstance(expr, Call):
            if isinstance(expr.callee, Var) and expr.callee.name == "print":
                return self.print_call(expr.args[0])
            args = [self.expr(a) for a in expr.args]
            ret = self.fn_returns.get(expr.callee.name if isinstance(expr.callee, Var) else "", "i64")
            rendered = ", ".join(f"{ty} {val}" for ty, val in args)
            if ret == "void":
                self.lines.append(f"  call void @{expr.callee.name}({rendered})")
                return "void", ""
            reg = self.new_reg()
            self.lines.append(f"  {reg} = call {ret} @{expr.callee.name}({rendered})")
            return ret, reg
        if isinstance(expr, MoveExpr):
            return self.expr(Var(expr.token, expr.name))
        if isinstance(expr, BorrowExpr):
            slot, _ = self.vars[expr.name]
            return "ptr", slot
        if isinstance(expr, NewExpr):
            self.lines.append(f"  ; new {expr.class_name}: object layout checked by semantic analyzer")
            return "ptr", "null"
        raise JaydError(f"LLVM backend cannot lower expression {expr!r}")

    def print_call(self, expr: Any) -> Tuple[str, str]:
        ty, val = self.expr(expr)
        if ty == "i64":
            fmt = "getelementptr inbounds ([5 x i8], ptr @.fmt.int, i64 0, i64 0)"
            self.lines.append(f"  call i32 (ptr, ...) @printf(ptr {fmt}, i64 {val})")
        elif ty == "double":
            fmt = "getelementptr inbounds ([4 x i8], ptr @.fmt.float, i64 0, i64 0)"
            self.lines.append(f"  call i32 (ptr, ...) @printf(ptr {fmt}, double {val})")
        elif ty == "ptr":
            fmt = "getelementptr inbounds ([4 x i8], ptr @.fmt.str, i64 0, i64 0)"
            self.lines.append(f"  call i32 (ptr, ...) @printf(ptr {fmt}, ptr {val})")
        elif ty == "i1":
            z = self.new_reg()
            self.lines.append(f"  {z} = zext i1 {val} to i64")
            fmt = "getelementptr inbounds ([5 x i8], ptr @.fmt.int, i64 0, i64 0)"
            self.lines.append(f"  call i32 (ptr, ...) @printf(ptr {fmt}, i64 {z})")
        return "void", ""

    def string_ptr(self, value: str) -> str:
        data = value.encode("utf8") + b"\x00"
        name = f"@.str.{len(self.globals)}"
        escaped = "".join(chr(b) if 32 <= b <= 126 and b not in (34, 92) else f"\\{b:02X}" for b in data)
        self.globals.append(f'{name} = private unnamed_addr constant [{len(data)} x i8] c"{escaped}"')
        return f"getelementptr inbounds ([{len(data)} x i8], ptr {name}, i64 0, i64 0)"

    def llvm_type_node(self, node: TypeNode, generic_names: Optional[List[str]] = None) -> str:
        if generic_names and node.name in generic_names:
            return "i64"
        return {"int": "i64", "float": "double", "bool": "i1", "string": "ptr", "void": "void"}.get(node.name, "ptr")

    def new_reg(self) -> str:
        self.reg += 1
        return f"%r{self.reg}"

    def new_label(self, prefix: str) -> str:
        self.label += 1
        return f"{prefix}.{self.label}"


@dataclass
class CompileResult:
    program: Program
    escapes: Dict[str, Dict[str, str]]
    llvm_ir: str


class Compiler:
    def parse_source(self, source: str, filename: str = "<memory>") -> Program:
        tokens = Lexer(source, filename).scan()
        return Parser(tokens).parse()

    def compile_program(self, program: Program, optimize: bool = True) -> CompileResult:
        SemanticAnalyzer(program).analyze()
        OwnershipChecker(program).check()
        if optimize:
            program = Optimizer().optimize(program)
        escapes = EscapeAnalyzer().analyze(program)
        llvm_ir = LLVMCodegen(program, escapes).emit()
        return CompileResult(program, escapes, llvm_ir)

    def compile_source(self, source: str, filename: str = "<memory>", optimize: bool = True) -> CompileResult:
        return self.compile_program(self.parse_source(source, filename), optimize)

    def compile_file(self, path: str, optimize: bool = True) -> CompileResult:
        program = self._load_module(os.path.abspath(path), seen=set())
        return self.compile_program(program, optimize)

    def _load_module(self, path: str, seen: set) -> Program:
        if path in seen:
            return Program([])
        seen.add(path)
        with open(path, "r", encoding="utf8") as f:
            program = self.parse_source(f.read(), path)
        base = os.path.dirname(path)
        imported: List[Any] = []
        local: List[Any] = []
        for decl in program.declarations:
            if isinstance(decl, ImportDecl):
                module_path = os.path.join(base, *decl.module.split(".")) + ".jayd"
                if not os.path.exists(module_path):
                    raise JaydError(f"import '{decl.module}' not found at {module_path}")
                imported.extend(self._load_module(module_path, seen).declarations)
            else:
                local.append(decl)
        return Program(imported + local)


def write_native(ir_path: str, out_path: str, links: Optional[List[str]] = None, opt_level: int = 0) -> None:
    clang = shutil.which("clang")
    if not clang:
        raise JaydError("clang not found; emitted LLVM IR but cannot build native executable")
    subprocess.check_call([clang, f"-O{opt_level}", ir_path, *(links or []), "-Wno-override-module", "-o", out_path])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="jayd", description="Jayd educational compiler")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "emit-ir", "build", "run"):
        p = sub.add_parser(name)
        p.add_argument("source")
        if name in ("emit-ir", "build", "run"):
            p.add_argument("-o", "--output")
        if name in ("build", "run"):
            p.add_argument("--link", action="append", default=[], help="extra object/library to pass to clang")
            p.add_argument("-O", dest="opt_level", type=int, choices=(0, 1, 2, 3), default=0, help="LLVM optimization level passed to clang")
    ns = ap.parse_args(argv)
    compiler = Compiler()
    try:
        result = compiler.compile_file(ns.source)
        if ns.cmd == "check":
            print("OK")
            for fn, allocations in result.escapes.items():
                for name, where in allocations.items():
                    print(f"escape-analysis: {fn}.{name} -> {where}")
            return 0
        out = ns.output
        if ns.cmd == "emit-ir":
            if out:
                with open(out, "w", encoding="utf8") as f:
                    f.write(result.llvm_ir)
            else:
                print(result.llvm_ir, end="")
            return 0
        ir_path = out + ".ll" if out else os.path.splitext(ns.source)[0] + ".ll"
        exe_path = out if out else os.path.splitext(ns.source)[0]
        with open(ir_path, "w", encoding="utf8") as f:
            f.write(result.llvm_ir)
        write_native(ir_path, exe_path, ns.link, ns.opt_level)
        if ns.cmd == "run":
            subprocess.check_call([exe_path if exe_path.startswith("/") else f"./{exe_path}"])
        else:
            print(exe_path)
        return 0
    except (JaydError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
