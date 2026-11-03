#!/usr/bin/env python3
"""`tools.knobs` registers every knob the engines read, in all three shapes.

    python -m tests.test_knob_reads
    python -m tests.test_knob_reads --mutate   # 3 mutations, exact sets

KNOBS.md promises that the absence of a name means the knob does not exist.
Each read shape was once missed: bare `cfg.get` (nine knobs, §0u's era),
`pod_knob` (POD_V4's five, §0z140), and `turn_knob` -- every knob a fork sets
on one turn, from §0z161 until 2026-11-03 (§0z167). Each case checks the
registry against the SOURCE TEXT, not against the tree the tool reads.

CASES
  A every `turn_knob(g, "name", ...)` in edhmc/ is registered
  B every `pod_knob(cfg, "name")` in edhmc/ is registered
  C every `cfg.get("name"` in edhmc/ is registered

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  turn_knob reads are not matched  -> A
  pod_knob reads are not matched   -> B
  cfg.get reads are not matched    -> C

UNMUTATED (§0z15): a name built at run time (`cfg.get(f"...")`) matches
none of the three, in the source grep or the tool; the defaults column is
not checked here.
"""
import re
import sys

import tools.knobs as K

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
SHAPES = {
    "A": re.compile(r"""\bturn_knob\(\s*\w+\s*,\s*["']([a-z0-9_]+)["']"""),
    "B": re.compile(r"""\bpod_knob\(\s*\w+\s*,\s*["']([a-z0-9_]+)["']\s*\)"""),
    "C": re.compile(r"""\bcfg\.get\(\s*["']([a-z0-9_]+)["']"""),
}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def run_cases():
    PASS.clear()
    FAIL.clear()
    reads = K.scan()
    text = ""
    for path in K.engine_sources():
        with open(path, encoding="utf-8") as fh:
            text += fh.read() + "\n"
    labels = {"A": "A every turn_knob read is registered",
              "B": "B every pod_knob read is registered",
              "C": "C every cfg.get read is registered"}
    for key, rx in SHAPES.items():
        named = set(rx.findall(text))
        missing = sorted(n for n in named if n not in reads)
        check(f"{labels[key]} ({len(named)} in the source)", missing[:4], [])
    return set(FAIL)


def main():
    if not MUTATE:
        print("tools.knobs read shapes\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {k: getattr(K, k) for k in
            ("_turn_knob_read", "_pod_knob_read", "_is_cfg_get")}
    muts = {
        "turn_knob reads are not matched":
            ({"A"}, "_turn_knob_read", lambda node: None),
        "pod_knob reads are not matched":
            ({"B"}, "_pod_knob_read", lambda node: None),
        "cfg.get reads are not matched":
            ({"C"}, "_is_cfg_get", lambda node: False),
    }
    bad = 0
    for label, (want, name, val) in muts.items():
        print(f"-- {label}")
        setattr(K, name, val)
        try:
            broke = run_cases()
        finally:
            setattr(K, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
