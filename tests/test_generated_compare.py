#!/usr/bin/env python3
"""What `tools._generated.comparable` masks, and what it must keep comparing.

    python -m tests.test_generated_compare
    python -m tests.test_generated_compare --mutate   # 2 mutations, exact sets

`check_docs` calls a generated doc current when `comparable(file)` equals
`comparable(fresh render)`. Two git-state facts are printed in STATUS.md and
must be masked, or committing the doc makes it stale by its own test: the ref
in the provenance line, and each ablation table's last-commit date with its
"(uncommitted edits)" flag. c72377e was committed red on the second.

CASES
  A  two docs that differ only in the provenance ref compare equal
  B  two table rows that differ only in date and dirty flag compare equal
  C  NEIGHBOUR: a table row whose noise floor moved still compares unequal
  D  NEIGHBOUR: a cache fingerprint (hex, like a ref) still compares unequal
  E  NEIGHBOUR: a table row whose row counts moved still compares unequal

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the date mask matches nothing (the bug)            -> B
  the date mask swallows the whole table row         -> C, E

UNMUTATED (§0z15): A and D pin the provenance mask, which neither mutation
touches.
"""
import re
import sys

import tools._generated as G

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

ROW = ("| lorehold | `ablation_lorehold.txt` | 15,000 | 10, 20 | ±0.0031 "
       "| 42/11/12 = 65 | {date} |")
FP = "| rendmaw | `{fp}` | `08632e094e2bf826` | **CURRENT** | 1 |"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def same(a, b):
    return G.comparable(a) == G.comparable(b)


def run_cases():
    PASS.clear()
    FAIL.clear()
    check("A provenance refs differ only",
          same("Derived at `1dcdd28`. x\n", "Derived at `c72377e`. x\n"), True)
    check("B table rows differ only in date and dirty flag",
          same(ROW.format(date="2026-10-08 *(uncommitted edits)*"),
               ROW.format(date="2026-10-11")), True)
    check("C NEIGHBOUR: a moved noise floor is still caught",
          same(ROW.format(date="2026-10-11"),
               ROW.format(date="2026-10-11").replace("±0.0031", "±0.0044")),
          False)
    check("D NEIGHBOUR: a moved cache fingerprint is still caught",
          same(FP.format(fp="e5748a9fd75c3bcc"), FP.format(fp="9b97a9669068b7ba")),
          False)
    check("E NEIGHBOUR: moved row counts are still caught",
          same(ROW.format(date="2026-10-11"),
               ROW.format(date="2026-10-11").replace("42/11/12 = 65",
                                                     "43/11/11 = 65")),
          False)
    return set(FAIL)


MUTATIONS = {
    "the date mask matches nothing (the bug)":
        (re.compile(r"(?!x)x()"), {"B"}),
    "the date mask swallows the whole table row":
        (re.compile(r"^(\| \w+ \| `ablation_\w+\.txt` \|).*\|$", re.M),
         {"C", "E"}),
}


def main() -> int:
    if not MUTATE:
        print("comparable() masks git state and nothing else\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    real, good = G._TABLE_DATE, 0
    for label, (pattern, want) in MUTATIONS.items():
        G._TABLE_DATE = pattern
        try:
            broke = run_cases()
        finally:
            G._TABLE_DATE = real
        ok = broke == want
        good += ok
        print(f"   {label}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    n = len(MUTATIONS)
    print(f"{good} passed, {n - good} failed ({n} mutations, exact sets)")
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
