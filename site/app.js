// Runs the real Jayd compiler (jayd/compiler.py, copied by scripts/build_site.sh) in Pyodide.
const EXAMPLES = {
  "Factorial": `func factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

func main() -> int:
    let value = factorial(5)
    print(value)
    return 0
`,
  "Stack or heap": `class Buffer:
    let size: int

func make() -> Buffer:
    let kept = new Buffer()
    let scratch = new Buffer()
    return kept

func main() -> int:
    let b = make()
    print(1)
    return 0
`,
  "Borrow error": `class Buffer:
    let size: int

func main() -> int:
    let buffer = new Buffer()
    let view = borrow buffer
    let owned = move buffer
    return 0
`,
  "Generics": `class Shape:
    let name: string

class Circle(Shape):
    let radius: float

func identity<T>(value: T) -> T:
    return value

func main() -> int:
    let number = identity(42)
    let maybe_name: string? = null
    print(number)
    return 0
`,
  "Loop": `func sum_to(n: int) -> int:
    let total = 0
    let i = 0
    while i < n:
        total = total + i
        i = i + 1
    return total

func main() -> int:
    print(sum_to(1000))
    return 0
`,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
let py = null, timer = null;

function highlight(ir) {
  return esc(ir).split("\n").map((line) => {
    if (line.trim().startsWith(";")) return `<span class="c">${line}</span>`;
    return line.replace(/\b(define|declare|call|ret|alloca|load|store|br|icmp|add|sub|mul|sdiv|phi|getelementptr|private|constant|global)\b/g, '<span class="k">$1</span>');
  }).join("\n");
}

function renderMemory(escapes) {
  const fns = Object.entries(escapes);
  const objects = fns.filter(([, vars]) => Object.keys(vars).length);
  if (!objects.length) {
    $("mem").innerHTML = `<p class="q-small">No objects are allocated with <code>new</code> in this program.</p>`;
    return;
  }
  $("mem").innerHTML = objects.map(([fn, vars]) => `<div class="mem-fn"><h4>${esc(fn)}()</h4>${
    Object.entries(vars).map(([v, where]) => `<div class="mem-row"><code>${esc(v)}</code><span class="pill ${where}">${where === "heap" ? "Heap · escapes" : "Stack · stays local"}</span></div>`).join("")
  }</div>`).join("");
}

function compile() {
  if (!py) return;
  const t0 = performance.now();
  py.globals.set("SRC", $("src").value);
  const res = JSON.parse(py.runPython("run(SRC)"));
  $("timing").textContent = `${Math.round(performance.now() - t0)} ms`;
  const status = $("status");
  if (res.ok) {
    status.className = "status ok";
    status.textContent = `Compiled. ${res.ir.split("\n").length} lines of LLVM IR.`;
    $("ir").innerHTML = highlight(res.ir);
    renderMemory(res.escapes);
  } else {
    status.className = "status err";
    status.textContent = res.error;
    $("ir").innerHTML = "";
    $("mem").innerHTML = "";
  }
}

function setView(view) {
  document.querySelectorAll("#views button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === view)));
  $("ir").hidden = view !== "ir";
  $("mem").hidden = view !== "mem";
}

function load(name) {
  document.querySelectorAll("#examples button").forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === name)));
  $("src").value = EXAMPLES[name];
  setView(name === "Stack or heap" ? "mem" : "ir");
  compile();
}

$("examples").innerHTML = Object.keys(EXAMPLES).map((n) => `<button aria-pressed="false">${n}</button>`).join("");
document.querySelectorAll("#examples button").forEach((b) => b.addEventListener("click", () => load(b.textContent)));
document.querySelectorAll("#views button").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
$("src").value = EXAMPLES["Factorial"];
$("src").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(compile, 350); });
$("src").addEventListener("keydown", (e) => {
  if (e.key === "Tab") { e.preventDefault(); document.execCommand("insertText", false, "    "); }
});
$("run").addEventListener("click", compile);

(async () => {
  try {
    const [pyodide, source] = await Promise.all([loadPyodide(), fetch("compiler.py").then((r) => r.text())]);
    pyodide.FS.writeFile("/home/pyodide/jayd_compiler.py", source);
    pyodide.runPython(`
import json
from jayd_compiler import Compiler

def run(src):
    try:
        r = Compiler().compile_source(src, "source.jayd")
        return json.dumps({"ok": True, "ir": r.llvm_ir, "escapes": r.escapes})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})
`);
    py = pyodide;
    $("run").disabled = false;
    $("run").textContent = "Compile";
    load("Factorial");
  } catch (err) {
    $("status").className = "status err";
    $("status").textContent = `Could not start the in-browser compiler: ${err.message}`;
  }
})();
