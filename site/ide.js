// Jayd Playground: the real compiler (compiler.py) checks the program in Pyodide, then
// interpreter.py runs it. Both are copied from jayd/ by scripts/build_site.sh.
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const EXAMPLES = {
    "factorial.jayd": `func factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

func main() -> int:
    let i = 1
    while i <= 10:
        print(factorial(i))
        i = i + 1
    return 0
`,
    "fizzbuzz.jayd": `func main() -> int:
    let i = 1
    while i <= 15:
        if i % 15 == 0:
            print("FizzBuzz")
        else:
            if i % 3 == 0:
                print("Fizz")
            else:
                if i % 5 == 0:
                    print("Buzz")
                else:
                    print(i)
        i = i + 1
    return 0
`,
    "primes.jayd": `func is_prime(n: int) -> bool:
    if n < 2:
        return false
    let d = 2
    while d * d <= n:
        if n % d == 0:
            return false
        d = d + 1
    return true

func main() -> int:
    let n = 2
    let found = 0
    while found < 20:
        if is_prime(n):
            print(n)
            found = found + 1
        n = n + 1
    return 0
`,
    "stack_or_heap.jayd": `class Buffer:
    let size: int

func make() -> Buffer:
    let kept = new Buffer()
    let scratch = new Buffer()
    return kept

func main() -> int:
    let b = make()
    print("open the Memory tab")
    return 0
`,
    "borrow_error.jayd": `class Buffer:
    let size: int

func main() -> int:
    let buffer = new Buffer()
    let view = borrow buffer
    let owned = move buffer
    return 0
`,
    "generics.jayd": `func identity<T>(value: T) -> T:
    return value

func main() -> int:
    let number = identity(42)
    let ratio = identity(2.5)
    let maybe_name: string? = null
    print(number)
    print(ratio)
    return 0
`,
  };
  const KW = /\b(func|let|return|if|else|while|for|in|class|new|borrow|move|import|extern|throw|try|catch|and|or|not|true|false|null|mut)\b/;
  let py = null, current = "factorial.jayd", checkTimer = null;

  // ---------- editor ----------
  const src = $("src");
  function highlight(text, errLines = new Set()) {
    const lines = text.split("\n");
    const tok = /(#.*$)|("(?:[^"\\]|\\.)*")|\b(\d+(?:\.\d+)?)\b|\b(int|float|bool|string|void)\b|\b(func|let|return|if|else|while|for|in|class|new|borrow|move|import|extern|throw|try|catch|and|or|not|true|false|null|mut)\b|\b([a-zA-Z_]\w*)(?=\s*\()/g;
    return lines.map((line, i) => {
      let out = "", last = 0, m;
      tok.lastIndex = 0;
      while ((m = tok.exec(line))) {
        out += esc(line.slice(last, m.index));
        const cls = m[1] ? "c" : m[2] ? "s" : m[3] ? "n" : m[4] ? "t" : m[5] ? "k" : "f";
        out += `<span class="${cls}">${esc(m[0])}</span>`;
        last = m.index + m[0].length;
      }
      out += esc(line.slice(last));
      return errLines.has(i + 1) ? `<span class="errline">${out || " "}</span>` : out;
    }).join("\n") + "\n";
  }
  let errLines = new Set();
  function paint() {
    $("hl").innerHTML = highlight(src.value, errLines);
    const n = src.value.split("\n").length;
    $("gutter").innerHTML = Array.from({ length: n }, (_, i) => (errLines.has(i + 1) ? `<span class="bad">${i + 1}</span>` : i + 1)).join("\n");
    src.style.height = "auto";
    src.style.height = Math.max(src.scrollHeight, src.parentElement.clientHeight) + "px";
    src.style.width = "auto";
  }
  function caret() {
    const before = src.value.slice(0, src.selectionStart).split("\n");
    $("st-pos").textContent = `Ln ${before.length}, Col ${before[before.length - 1].length + 1}`;
  }

  // ---------- panels ----------
  function show(p) {
    document.querySelectorAll(".ptabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.p === p)));
    ["out", "problems", "ir", "mem"].forEach((k) => ($(`p-${k}`).hidden = k !== p));
  }
  const irHtml = (ir) => esc(ir).split("\n").map((l) => (l.trim().startsWith(";") ? `<span class="c">${l}</span>` : l.replace(/\b(define|declare|call|ret|alloca|load|store|br|icmp|fcmp|add|sub|mul|sdiv|srem|phi|getelementptr|private|constant|global)\b/g, '<span class="k">$1</span>'))).join("\n");
  function memHtml(escapes) {
    const fns = Object.entries(escapes || {}).filter(([, v]) => Object.keys(v).length);
    if (!fns.length) return '<p class="none">No objects are created with new, so nothing to place.</p>';
    return fns.map(([fn, vars]) => `<div class="memfn"><h4>${esc(fn)}()</h4>${Object.entries(vars).map(([v, w]) => `<div class="memrow"><span>${esc(v)}</span><span class="pill ${w}">${w === "heap" ? "heap · escapes" : "stack · stays local"}</span></div>`).join("")}</div>`).join("");
  }
  function parseErrors(msg) {
    return String(msg).split("\n").filter(Boolean).map((l) => {
      const m = l.match(/^(\w+) error at (\d+):(\d+): (.*)$/);
      return m ? { phase: m[1], line: +m[2], col: +m[3], msg: m[4] } : { phase: "error", line: 0, col: 0, msg: l };
    });
  }
  function setProblems(list) {
    errLines = new Set(list.map((p) => p.line).filter(Boolean));
    $("pcount").textContent = list.length;
    $("pcount").classList.toggle("bad", list.length > 0);
    $("p-problems").innerHTML = list.length ? list.map((p) => `<div class="prob" data-line="${p.line}"><b>${esc(p.phase)}</b><span>${p.line ? `${p.line}:${p.col} ` : ""}${esc(p.msg)}</span></div>`).join("") : '<p class="none">No problems. Types, ownership and borrows all check out.</p>';
    $("st-check").textContent = list.length ? `✕ ${list.length} problem${list.length > 1 ? "s" : ""}` : "✓ Checks passed";
    document.querySelector(".statusbar").classList.toggle("err", list.length > 0);
    paint();
  }

  // ---------- compiler ----------
  function call(fn) {
    py.globals.set("SRC", src.value);
    return JSON.parse(py.runPython(`${fn}(SRC)`));
  }
  function check() {
    if (!py) return;
    const r = call("check");
    setProblems(r.ok ? [] : parseErrors(r.error));
    if (r.ok) { $("p-ir").innerHTML = irHtml(r.ir); $("p-mem").innerHTML = memHtml(r.escapes); }
    return r;
  }
  function run() {
    if (!py) return;
    const r = call("execute");
    const out = $("p-out");
    if (r.stage === "compile") {
      setProblems(parseErrors(r.error));
      out.innerHTML = `<span class="errline">Compilation failed. See Problems.</span>`;
      show("problems");
      return;
    }
    setProblems([]);
    $("p-ir").innerHTML = irHtml(r.ir); $("p-mem").innerHTML = memHtml(r.escapes);
    const lines = r.output.map(esc).join("\n");
    out.innerHTML = `<span class="meta">$ jayd run ${esc(current)}   (checked in ${r.compile_ms} ms)</span>\n${lines}${lines ? "\n" : ""}` +
      (r.stage === "run" ? `<span class="errline">runtime error: ${esc(r.error)}</span>` : `<span class="okline">exited with code ${r.exit_code} · ${r.steps.toLocaleString()} steps · ${r.run_ms} ms</span>`);
    show("out");
  }

  function load(name, text) {
    current = name;
    $("tab-name").textContent = name;
    src.value = text ?? EXAMPLES[name];
    $("dirty").hidden = true;
    document.querySelectorAll("#files button").forEach((b) => b.setAttribute("aria-current", String(b.dataset.f === name)));
    paint();
    if (py) { run(); if (name === "stack_or_heap.jayd") show("mem"); }
  }

  $("files").innerHTML = Object.keys(EXAMPLES).map((n) => `<li><button type="button" data-f="${n}">${n}</button></li>`).join("");
  $("files").addEventListener("click", (e) => { const b = e.target.closest("[data-f]"); if (b) load(b.dataset.f); });
  document.querySelector(".ptabs").addEventListener("click", (e) => { const b = e.target.closest("[data-p]"); if (b) show(b.dataset.p); });
  $("p-problems").addEventListener("click", (e) => {
    const p = e.target.closest("[data-line]"); if (!p || !+p.dataset.line) return;
    const lines = src.value.split("\n"), pos = lines.slice(0, +p.dataset.line - 1).join("\n").length + (+p.dataset.line > 1 ? 1 : 0);
    src.focus(); src.setSelectionRange(pos, pos + lines[+p.dataset.line - 1].length); caret();
  });
  src.addEventListener("input", () => { $("dirty").hidden = false; paint(); clearTimeout(checkTimer); checkTimer = setTimeout(check, 300); });
  src.addEventListener("keyup", caret); src.addEventListener("click", caret);
  src.addEventListener("keydown", (e) => {
    if (e.key === "Tab") { e.preventDefault(); document.execCommand("insertText", false, "    "); }
    else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); run(); }
    else if (e.key === "Enter") {
      const line = src.value.slice(0, src.selectionStart).split("\n").pop();
      const indent = line.match(/^\s*/)[0] + (line.trim().endsWith(":") ? "    " : "");
      e.preventDefault(); document.execCommand("insertText", false, "\n" + indent);
    }
  });
  $("run").addEventListener("click", run);
  $("share").addEventListener("click", async () => {
    const enc = btoa(unescape(encodeURIComponent(src.value))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    const url = `${location.origin}${location.pathname}#code=${enc}`;
    history.replaceState(null, "", `#code=${enc}`);
    try { await navigator.clipboard.writeText(url); $("share").textContent = "Link copied"; } catch (_) { $("share").textContent = "Link in address bar"; }
    setTimeout(() => ($("share").textContent = "Share"), 1800);
  });
  window.addEventListener("resize", paint);

  const shared = location.hash.startsWith("#code=") ? (() => { try { return decodeURIComponent(escape(atob(location.hash.slice(6).replace(/-/g, "+").replace(/_/g, "/")))); } catch (_) { return null; } })() : null;
  load(shared ? "shared.jayd" : "factorial.jayd", shared || undefined);

  (async () => {
    try {
      const [pyodide, comp, interp] = await Promise.all([loadPyodide(), fetch("compiler.py").then((r) => r.text()), fetch("interpreter.py").then((r) => r.text())]);
      pyodide.FS.writeFile("/home/pyodide/jayd_compiler.py", comp);
      pyodide.FS.writeFile("/home/pyodide/jayd_interpreter.py", interp);
      pyodide.runPython(`
import json, time
from jayd_compiler import Compiler
from jayd_interpreter import run as interpret

def check(src):
    try:
        r = Compiler().compile_source(src, "main.jayd")
        return json.dumps({"ok": True, "ir": r.llvm_ir, "escapes": r.escapes})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})

def execute(src):
    t0 = time.perf_counter()
    try:
        r = Compiler().compile_source(src, "main.jayd")
    except Exception as e:
        return json.dumps({"stage": "compile", "error": str(e)})
    t1 = time.perf_counter()
    base = {"ir": r.llvm_ir, "escapes": r.escapes, "compile_ms": round((t1 - t0) * 1000)}
    try:
        res = interpret(r.program, max_steps=3_000_000)
        return json.dumps({**base, "stage": "done", **res, "run_ms": round((time.perf_counter() - t1) * 1000)})
    except Exception as e:
        return json.dumps({**base, "stage": "run", "output": [], "error": str(e)})
`);
      py = pyodide;
      $("run").disabled = false;
      $("run-label").textContent = "Run";
      run();
      if (current === "stack_or_heap.jayd") show("mem");
    } catch (err) {
      $("p-out").innerHTML = `<span class="errline">Could not start the compiler: ${esc(err.message)}</span>`;
      $("st-check").textContent = "Compiler unavailable";
    }
  })();
})();
