import os
import shutil
import subprocess
import tempfile
import unittest

from jayd.compiler import Compiler, JaydError, Lexer, Parser


class JaydCompilerTests(unittest.TestCase):
    def compile(self, source):
        return Compiler().compile_source(source)

    def test_lexer_emits_indentation_tokens(self):
        tokens = Lexer("func main() -> int:\n    return 0\n").scan()
        kinds = [t.kind for t in tokens]
        self.assertIn("INDENT", kinds)
        self.assertIn("DEDENT", kinds)
        self.assertIn("FUNC", kinds)

    def test_parser_reads_function(self):
        tokens = Lexer("func main() -> int:\n    return 0\n").scan()
        program = Parser(tokens).parse()
        self.assertEqual(program.declarations[0].name, "main")

    def test_type_inference_and_codegen(self):
        result = self.compile(
            "func main() -> int:\n"
            "    let x = 2 + 3\n"
            "    print(x)\n"
            "    return x\n"
        )
        self.assertIn("define i64 @main", result.llvm_ir)
        self.assertIn("ret i64", result.llvm_ir)

    def test_type_error_is_reported(self):
        with self.assertRaises(JaydError) as cm:
            self.compile(
                "func main() -> int:\n"
                "    let x: int = \"bad\"\n"
                "    return x\n"
            )
        self.assertIn("cannot assign string to int", str(cm.exception))

    def test_generic_identity_typechecks(self):
        self.compile(
            "func identity<T>(value: T) -> T:\n"
            "    return value\n"
            "\n"
            "func main() -> int:\n"
            "    let x = identity(7)\n"
            "    return x\n"
        )

    def test_nullable_accepts_null(self):
        self.compile(
            "func main() -> int:\n"
            "    let name: string? = null\n"
            "    return 0\n"
        )

    def test_use_after_move_is_rejected(self):
        with self.assertRaises(JaydError) as cm:
            self.compile(
                "class Box:\n"
                "    let value: int\n"
                "\n"
                "func main() -> int:\n"
                "    let b = new Box()\n"
                "    let c = move b\n"
                "    print(b)\n"
                "    return 0\n"
            )
        self.assertIn("use of moved binding 'b'", str(cm.exception))

    def test_mutable_alias_is_rejected(self):
        with self.assertRaises(JaydError) as cm:
            self.compile(
                "class Box:\n"
                "    let value: int\n"
                "\n"
                "func main() -> int:\n"
                "    let b = new Box()\n"
                "    let r1 = borrow b\n"
                "    let r2 = borrow mut b\n"
                "    return 0\n"
            )
        self.assertIn("cannot mutably borrow 'b'", str(cm.exception))

    def test_return_local_borrow_is_rejected(self):
        with self.assertRaises(JaydError) as cm:
            self.compile(
                "class Box:\n"
                "    let value: int\n"
                "\n"
                "func leak() -> any:\n"
                "    let b = new Box()\n"
                "    return borrow b\n"
            )
        self.assertIn("cannot return borrow of local binding", str(cm.exception))

    def test_escape_analysis_marks_returned_object_heap(self):
        result = self.compile(
            "class Box:\n"
            "    let value: int\n"
            "\n"
            "func make() -> Box:\n"
            "    let b = new Box()\n"
            "    return b\n"
        )
        self.assertEqual(result.escapes["make"]["b"], "heap")

    def test_file_import_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "mathlib.jayd"), "w", encoding="utf8") as f:
                f.write("func triple(x: int) -> int:\n    return x * 3\n")
            main = os.path.join(td, "main.jayd")
            with open(main, "w", encoding="utf8") as f:
                f.write("import mathlib\n\nfunc main() -> int:\n    return triple(4)\n")
            result = Compiler().compile_file(main)
        self.assertIn("define i64 @triple", result.llvm_ir)

    @unittest.skipUnless(shutil.which("clang"), "clang required")
    def test_native_factorial_runs(self):
        source = (
            "func factorial(n: int) -> int:\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
            "\n"
            "func main() -> int:\n"
            "    print(factorial(5))\n"
            "    return 0\n"
        )
        result = self.compile(source)
        with tempfile.TemporaryDirectory() as td:
            ll = os.path.join(td, "program.ll")
            exe = os.path.join(td, "program")
            with open(ll, "w", encoding="utf8") as f:
                f.write(result.llvm_ir)
            subprocess.check_call(["clang", ll, "-Wno-override-module", "-o", exe])
            output = subprocess.check_output([exe], text=True).strip()
        self.assertEqual(output, "120")

    @unittest.skipUnless(shutil.which("clang") and shutil.which("clang++"), "clang and clang++ required")
    def test_cpp_interop_links_and_runs(self):
        source = "extern func cpp_square(x: int) -> int\n\nfunc main() -> int:\n    print(cpp_square(9))\n    return 0\n"
        result = self.compile(source)
        with tempfile.TemporaryDirectory() as td:
            cpp = os.path.join(td, "square.cpp")
            obj = os.path.join(td, "square.o")
            ll = os.path.join(td, "program.ll")
            exe = os.path.join(td, "program")
            with open(cpp, "w", encoding="utf8") as f:
                f.write('extern "C" long cpp_square(long x) { return x * x; }\n')
            with open(ll, "w", encoding="utf8") as f:
                f.write(result.llvm_ir)
            subprocess.check_call(["clang++", "-c", cpp, "-o", obj])
            subprocess.check_call(["clang", ll, obj, "-Wno-override-module", "-o", exe])
            output = subprocess.check_output([exe], text=True).strip()
        self.assertEqual(output, "81")

    @unittest.skipUnless(shutil.which("clang"), "clang required")
    def test_optimized_build_matches_unoptimized_output(self):
        from jayd.compiler import main

        source = "func sum_to(n: int) -> int:\n    let t = 0\n    let i = 0\n    while i < n:\n        t = t + i\n        i = i + 1\n    return t\n\nfunc main() -> int:\n    print(sum_to(1000))\n    return 0\n"
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "sum.jayd")
            with open(src, "w", encoding="utf8") as f:
                f.write(source)
            outputs = []
            for level in ("0", "2"):
                exe = os.path.join(td, f"sum_O{level}")
                self.assertEqual(main(["build", src, "-o", exe, "-O", level]), 0)
                outputs.append(subprocess.check_output([exe], text=True).strip())
        self.assertEqual(outputs, ["499500", "499500"])


if __name__ == "__main__":
    unittest.main()
