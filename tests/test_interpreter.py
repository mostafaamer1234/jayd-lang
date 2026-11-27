import unittest
from pathlib import Path

from jayd.compiler import Compiler
from jayd.interpreter import Limit, run


def out(src):
    return run(Compiler().compile_source(src).program)["output"]


class JaydInterpreterTests(unittest.TestCase):
    def test_factorial_prints_like_printf(self):
        src = "func factorial(n: int) -> int:\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nfunc main() -> int:\n    print(factorial(5))\n    print(2.5)\n    print(\"hi\")\n    print(3 > 2)\n    return 0\n"
        self.assertEqual(out(src), ["120", "2.500000", "hi", "1"])

    def test_integer_division_truncates_toward_zero_like_sdiv(self):
        src = "func main() -> int:\n    print(-7 / 2)\n    print(-7 % 2)\n    print(7 / -2)\n    return 0\n"
        self.assertEqual(out(src), ["-3", "-1", "-3"])

    def test_division_matches_whether_or_not_constants_are_folded(self):
        src = "func div(a: int, b: int) -> int:\n    return a / b\n\nfunc rem(a: int, b: int) -> int:\n    return a % b\n\nfunc main() -> int:\n    print(div(-7, 2))\n    print(rem(-7, 2))\n    return 0\n"
        self.assertEqual(out(src), ["-3", "-1"])

    def test_folded_integer_division_stays_an_integer_in_the_ir(self):
        ir = Compiler().compile_source("func main() -> int:\n    print(-7 / 2)\n    return 0\n").llvm_ir
        self.assertIn("i64 -3", ir)
        self.assertNotIn("@.fmt.float", ir.split("@printf(ptr", 1)[-1].split("\n", 1)[0])

    def test_loops_and_objects(self):
        src = (
            "class Box:\n    let size: int\n\nfunc main() -> int:\n    let b = new Box()\n"
            "    let total = 0\n    let i = 0\n    while i < 5:\n        total = total + i\n        i = i + 1\n    print(total)\n    return 0\n"
        )
        self.assertEqual(out(src), ["10"])

    def test_infinite_loop_is_stopped(self):
        src = "func main() -> int:\n    let i = 0\n    while i < 1:\n        i = i * 1\n    return 0\n"
        with self.assertRaises(Limit):
            run(Compiler().compile_source(src).program, max_steps=10_000)

    def test_examples_run(self):
        examples = Path(__file__).resolve().parent.parent / "examples"
        for name in ["factorial.jayd", "perf_loop.jayd", "memory_safety_valid.jayd", "classes_and_generics.jayd"]:
            with self.subTest(name=name):
                program = Compiler().compile_file(str(examples / name)).program
                result = run(program, max_steps=200_000_000)
                self.assertIsInstance(result["output"], list)


if __name__ == "__main__":
    unittest.main()
