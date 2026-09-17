"""Run every pinned test module and fail if any of them fails.

    python -m tests            # every tests/test_*.py, plain mode
    python -m tests --mutate   # the mutation mode of every module that has one
    python -m tests -k henge   # only modules whose name contains the substring

WHY THIS EXISTS. Each test module was runnable on its own and honest about its
exit code, and nothing ran them: no runner, no CI, no line in the closing
protocol. A test that pins The Great Henge's draw failed for three commits
while the card it pinned was being reported as measured. A test that is not
run does not exist.

Each module runs in its OWN SUBPROCESS, for two reasons. The modules mutate
engine module attributes in `--mutate` mode and restore them in `finally`,
which is fine in isolation and not something to trust across thirteen modules
in one interpreter. And a module's `--mutate` flag is read from `sys.argv`,
so importing a test module is not the same as running it.

TWO SIGNALS, CROSS-CHECKED. The exit code is the verdict. The "N passed, M
failed" line each module prints is read as well, and a module that prints
failures and exits 0 is reported as a failure OF THE MODULE: an exit code that
disagrees with the module's own tally is the one way this runner could be
fooled, so it refuses to be.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

TALLY = re.compile(r"(\d+) passed, (\d+) failed")
HERE = os.path.dirname(os.path.abspath(__file__))


def modules(substr: str = "") -> list[str]:
    out = []
    for f in sorted(os.listdir(HERE)):
        if f.startswith("test_") and f.endswith(".py") and substr in f:
            out.append(f"tests.{f[:-3]}")
    return out


def run(module: str, mutate: bool) -> tuple[bool, str]:
    """(ok, one-line summary). Prints the module's own output on failure."""
    args = [sys.executable, "-m", module] + (["--mutate"] if mutate else [])
    t0 = time.time()
    proc = subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    secs = time.time() - t0
    text = proc.stdout + proc.stderr
    m = None
    for m in TALLY.finditer(text):
        pass                                  # keep the LAST tally line
    tally = f"{m.group(1)} passed, {m.group(2)} failed" if m else "no tally"
    printed_fail = bool(m and int(m.group(2)) > 0)
    ok = proc.returncode == 0 and not printed_fail
    if proc.returncode == 0 and printed_fail:
        tally += "  ** printed failures but exited 0 -- the module's exit code is dishonest **"
    if not ok:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return ok, f"{tally}  ({secs:.0f}s, exit {proc.returncode})"


def main() -> int:
    args = sys.argv[1:]
    mutate = "--mutate" in args
    substr = ""
    if "-k" in args:
        substr = args[args.index("-k") + 1]
    mods = modules(substr)
    if mutate:
        # Only the modules that implement --mutate; the others would run their
        # plain mode and report success for a question nobody asked.
        mods = [m for m in mods
                if "--mutate" in open(os.path.join(HERE, m.split(".")[1] + ".py"),
                                      encoding="utf-8").read()]
    if not mods:
        print("no test modules matched")
        return 2
    print(f"running {len(mods)} test module(s){' in --mutate mode' if mutate else ''}\n")
    failed = []
    for mod in mods:
        ok, summary = run(mod, mutate)
        print(f"  [{'ok  ' if ok else 'FAIL'}] {mod:<36} {summary}")
        if not ok:
            failed.append(mod)
    print()
    if failed:
        print(f"{len(failed)} of {len(mods)} test module(s) FAILED: "
              + ", ".join(failed))
        return 1
    print(f"all {len(mods)} test module(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
