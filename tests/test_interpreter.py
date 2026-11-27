from __future__ import annotations

import pytest

from jayd.compiler import Compiler
from jayd.interpreter import Limit, run


def out(src: str) -> list[str]:
    return run(Compiler().compile_source(src).program)["output"]


def test_factorial_prints_like_printf():
    src = "func factorial(n: int) -> int:\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nfunc main() -> int:\n    print(factorial(5))\n    print(2.5)\n    print(\"hi\")\n    print(3 > 2)\n    return 0\n"
    assert out(src) == ["120", "2.500000", "hi", "1"]


def test_integer_division_truncates_toward_zero_like_sdiv():
    src = "func main() -> int:\n    print(-7 / 2)\n    print(-7 % 2)\n    print(7 / -2)\n    return 0\n"
    assert out(src) == ["-3", "-1", "-3"]


def test_division_matches_whether_or_not_constants_are_folded():
    src = "func div(a: int, b: int) -> int:\n    return a / b\n\nfunc rem(a: int, b: int) -> int:\n    return a % b\n\nfunc main() -> int:\n    print(div(-7, 2))\n    print(rem(-7, 2))\n    return 0\n"
    assert out(src) == ["-3", "-1"]


def test_folded_integer_division_stays_an_integer_in_the_ir():
    ir = Compiler().compile_source("func main() -> int:\n    print(-7 / 2)\n    return 0\n").llvm_ir
    assert "i64 -3" in ir and "@.fmt.float" not in ir.split("@printf(ptr", 1)[-1].split("\n", 1)[0]


def test_loops_and_objects():
    src = (
        "class Box:\n    let size: int\n\nfunc main() -> int:\n    let b = new Box()\n"
        "    let total = 0\n    let i = 0\n    while i < 5:\n        total = total + i\n        i = i + 1\n    print(total)\n    return 0\n"
    )
    assert out(src) == ["10"]


def test_infinite_loop_is_stopped():
    src = "func main() -> int:\n    let i = 0\n    while i < 1:\n        i = i * 1\n    return 0\n"
    with pytest.raises(Limit):
        run(Compiler().compile_source(src).program, max_steps=10_000)


@pytest.mark.parametrize("name", ["factorial.jayd", "perf_loop.jayd", "memory_safety_valid.jayd", "classes_and_generics.jayd"])
def test_examples_run(name):
    from pathlib import Path

    program = Compiler().compile_file(str(Path(__file__).resolve().parent.parent / "examples" / name)).program
    result = run(program, max_steps=200_000_000)
    assert isinstance(result["output"], list)
