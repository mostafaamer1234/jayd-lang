"""Benchmark Jayd native executables against CPython on the same programs.

    python3 bench/run_bench.py            # prints a markdown table
    python3 bench/run_bench.py --runs 5

Each benchmark exists twice: <name>.jayd and an equivalent <name>.py. The Jayd
program is compiled at -O0 and -O2; outputs must match CPython exactly or the
benchmark fails.
"""

from __future__ import annotations

import argparse
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = Path(__file__).resolve().parent
PROGRAMS = ["fib", "loop"]


def timed(cmd: list[str], runs: int) -> tuple[float, str]:
    times, out = [], ""
    for _ in range(runs):
        start = time.perf_counter()
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        times.append(time.perf_counter() - start)
    return statistics.median(times), out


def build(name: str, opt: int, workdir: Path) -> Path:
    exe = workdir / f"{name}_O{opt}"
    subprocess.run(
        [sys.executable, "-m", "jayd", "build", str(BENCH / f"{name}.jayd"), "-o", str(exe), "-O", str(opt)],
        check=True, cwd=ROOT, capture_output=True,
    )
    return exe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for name in PROGRAMS:
            py_t, py_out = timed([sys.executable, str(BENCH / f"{name}.py")], args.runs)
            o0_t, o0_out = timed([str(build(name, 0, work))], args.runs)
            o2_t, o2_out = timed([str(build(name, 2, work))], args.runs)
            if not (py_out == o0_out == o2_out):
                print(f"output mismatch for {name}: python={py_out} O0={o0_out} O2={o2_out}", file=sys.stderr)
                return 1
            rows.append((name, py_t, o0_t, o2_t))

    print(f"Machine: {platform.machine()} / {platform.system()} / Python {platform.python_version()}, median of {args.runs} runs\n")
    print("| Benchmark | CPython | Jayd -O0 | Jayd -O2 | Speedup (-O2 vs CPython) |")
    print("|---|---|---|---|---|")
    for name, py_t, o0_t, o2_t in rows:
        print(f"| {name} | {py_t * 1000:.0f} ms | {o0_t * 1000:.0f} ms | {o2_t * 1000:.0f} ms | {py_t / o2_t:.0f}x |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
