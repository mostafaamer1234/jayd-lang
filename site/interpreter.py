"""Tree-walking interpreter for checked Jayd programs.

Native code needs clang, which a browser does not have, so the web playground runs programs
with this interpreter after the real compiler has accepted them (lexing, parsing, type checking,
ownership and escape analysis). It follows the LLVM backend's semantics: 64-bit wrapping integer
arithmetic, `/` and `%` truncating toward zero, and `print` formatting like the backend's printf
calls (`%ld`, `%f`, `%s`, booleans as 1/0).

    from jayd.compiler import Compiler
    from jayd.interpreter import run
    output = run(Compiler().compile_source(src).program)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

try:  # package import, or a flat copy next to compiler.py (the web playground)
    from .compiler import (AssignStmt, Binary, BorrowExpr, Call, ClassDecl, ExprStmt, ForStmt, FuncDecl, IfStmt, JaydError, LetStmt,
                           Literal, Member, MoveExpr, NewExpr, Program, ReturnStmt, ThrowStmt, TryCatchStmt, Unary, Var, WhileStmt)
except ImportError:  # pragma: no cover
    from jayd_compiler import (AssignStmt, Binary, BorrowExpr, Call, ClassDecl, ExprStmt, ForStmt, FuncDecl, IfStmt, JaydError,  # type: ignore
                               LetStmt, Literal, Member, MoveExpr, NewExpr, Program, ReturnStmt, ThrowStmt, TryCatchStmt, Unary, Var, WhileStmt)

INT_MIN, INT_MAX = -(2**63), 2**63 - 1
DEFAULTS = {"int": 0, "float": 0.0, "bool": False, "string": ""}


class _Return(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class _Thrown(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class Limit(JaydError):
    pass


def _wrap(n: int) -> int:
    return (n - INT_MIN) % 2**64 + INT_MIN


def _tdiv(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return "%f" % v
    if v is None:
        return "(null)"
    if isinstance(v, dict):
        return f"<{v.get('__class__', 'object')}>"
    return str(v)


class Interpreter:
    def __init__(self, program: Program, max_steps: int = 5_000_000, max_depth: int = 400, max_output: int = 2000) -> None:
        self.funcs: Dict[str, FuncDecl] = {}
        self.classes: Dict[str, ClassDecl] = {}
        for d in program.declarations:
            if isinstance(d, FuncDecl):
                self.funcs[d.name] = d
            elif isinstance(d, ClassDecl):
                self.classes[d.name] = d
        self.output: List[str] = []
        self.steps, self.depth = 0, 0
        self.max_steps, self.max_depth, self.max_output = max_steps, max_depth, max_output

    # ---- helpers ----
    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise Limit(f"stopped after {self.max_steps:,} steps (possible infinite loop)")

    def _fields(self, name: str) -> List[Any]:
        cls = self.classes[name]
        inherited = self._fields(cls.base) if cls.base and cls.base in self.classes else []
        return inherited + list(cls.fields)

    # ---- running ----
    def run(self, entry: str = "main") -> Dict[str, Any]:
        if entry not in self.funcs:
            raise JaydError(f"no '{entry}' function to run")
        result = self.call(entry, [])
        return {"output": self.output, "exit_code": result if isinstance(result, int) else 0, "steps": self.steps}

    def call(self, name: str, args: List[Any]) -> Any:
        fn = self.funcs.get(name)
        if fn is None:
            raise JaydError(f"function '{name}' has no body to run (extern functions need a native build)")
        self.depth += 1
        if self.depth > self.max_depth:
            raise Limit(f"recursion deeper than {self.max_depth} calls")
        env = {p.name: v for p, v in zip(fn.params, args)}
        try:
            self.block(fn.body, env)
            return None
        except _Return as r:
            return r.value
        finally:
            self.depth -= 1

    def block(self, body: List[Any], env: Dict[str, Any]) -> None:
        for stmt in body:
            self.stmt(stmt, env)

    def stmt(self, s: Any, env: Dict[str, Any]) -> None:
        self._tick()
        if isinstance(s, LetStmt):
            env[s.name] = self.expr(s.value, env)
        elif isinstance(s, AssignStmt):
            env[s.name] = self.expr(s.value, env)
        elif isinstance(s, ReturnStmt):
            raise _Return(None if s.value is None else self.expr(s.value, env))
        elif isinstance(s, ExprStmt):
            self.expr(s.expr, env)
        elif isinstance(s, IfStmt):
            self.block(s.then_body if self.expr(s.condition, env) else s.else_body, env)
        elif isinstance(s, WhileStmt):
            while self.expr(s.condition, env):
                self._tick()
                self.block(s.body, env)
        elif isinstance(s, ForStmt):
            it = self.expr(s.iterable, env)
            seq = range(it) if isinstance(it, int) and not isinstance(it, bool) else it if isinstance(it, str) else None
            if seq is None:
                raise JaydError(f"line {s.token.line}: cannot loop over {_fmt(it)}")
            for item in seq:
                self._tick()
                env[s.name] = item
                self.block(s.body, env)
        elif isinstance(s, ThrowStmt):
            raise _Thrown(self.expr(s.value, env))
        elif isinstance(s, TryCatchStmt):
            try:
                self.block(s.try_body, env)
            except _Thrown as t:
                env[s.error_name] = _fmt(t.value)
                self.block(s.catch_body, env)
        else:
            raise JaydError(f"cannot run statement {type(s).__name__}")

    def expr(self, e: Any, env: Dict[str, Any]) -> Any:
        if isinstance(e, Literal):
            return e.value
        if isinstance(e, Var):
            if e.name not in env:
                raise JaydError(f"line {e.token.line}: '{e.name}' has no value")
            return env[e.name]
        if isinstance(e, (MoveExpr, BorrowExpr)):
            return env[e.name]
        if isinstance(e, Unary):
            v = self.expr(e.expr, env)
            if e.op == "-":
                return -v if isinstance(v, float) else _wrap(-v)
            return not v
        if isinstance(e, Binary):
            if e.op == "and":
                return bool(self.expr(e.left, env)) and bool(self.expr(e.right, env))
            if e.op == "or":
                return bool(self.expr(e.left, env)) or bool(self.expr(e.right, env))
            a, b = self.expr(e.left, env), self.expr(e.right, env)
            return self._binary(e, a, b)
        if isinstance(e, Call):
            if isinstance(e.callee, Var) and e.callee.name == "print":
                if len(self.output) < self.max_output:
                    self.output.append(_fmt(self.expr(e.args[0], env)))
                return None
            if not isinstance(e.callee, Var):
                raise JaydError(f"line {e.token.line}: only named functions can be called")
            return self.call(e.callee.name, [self.expr(a, env) for a in e.args])
        if isinstance(e, NewExpr):
            obj: Dict[str, Any] = {"__class__": e.class_name}
            fields = self._fields(e.class_name) if e.class_name in self.classes else []
            for f in fields:
                obj[f.name] = None if f.type.nullable else DEFAULTS.get(f.type.name)
            for f, a in zip(fields, e.args):
                obj[f.name] = self.expr(a, env)
            return obj
        if isinstance(e, Member):
            obj = self.expr(e.obj, env)
            if not isinstance(obj, dict):
                raise JaydError(f"line {e.token.line}: null has no member '{e.name}'")
            return obj.get(e.name)
        raise JaydError(f"cannot run expression {type(e).__name__}")

    def _binary(self, e: Any, a: Any, b: Any) -> Any:
        op = e.op
        if op in ("==", "!="):
            return (a == b) == (op == "==")
        if op in ("<", "<=", ">", ">="):
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        if isinstance(a, str) or isinstance(b, str):
            if op == "+":
                return _fmt(a) + _fmt(b) if not (isinstance(a, str) and isinstance(b, str)) else a + b
            raise JaydError(f"line {e.token.line}: '{op}' does not work on strings")
        if isinstance(a, float) or isinstance(b, float):
            if op == "/" and b == 0:
                return math.copysign(math.inf, a) if a else math.nan
            if op == "%":
                return math.fmod(a, b) if b else math.nan
            return {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b else math.nan}[op]
        if op in ("/", "%") and b == 0:
            raise JaydError(f"line {e.token.line}: integer division by zero")
        if op == "/":
            return _wrap(_tdiv(a, b))
        if op == "%":
            return _wrap(a - _tdiv(a, b) * b)
        return _wrap({"+": a + b, "-": a - b, "*": a * b}[op])


def run(program: Program, entry: str = "main", **limits: Any) -> Dict[str, Any]:
    return Interpreter(program, **limits).run(entry)
