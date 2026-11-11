#!/usr/bin/env python3
"""The baseline's own win rate travels from the ablation run to STATUS.md
(queue item 41's carried half, §0z195).

    python -m tests.test_baseline_record
    python -m tests.test_baseline_record --mutate   # 3 mutations, exact sets

`ablation_stream` yields (BASELINE_KEY, `baseline_record`) once the baseline
is measured; `main` keeps it in the cache; `render_table` prints a BASELINE
line in the header when the cache has it; `tools.status` reads that line into
its tables table; `cache_manifest` leaves the key out of its card count.

CASES
  A  a real run (karlov, N=30, T10+T20, one process) yields BASELINE_KEY
     first, and its "won" per horizon equals the mean of the baseline's own
     columns, played separately by `columns_all`
  B  `render_table` prints the BASELINE line from a cache that has the key,
     with the last horizon's number, and none from one that does not
  C  `tools.status`'s RE_BASE reads B's header back to the last horizon's
     win rate
  D  `cache_manifest`'s literal for the key is `ablation.BASELINE_KEY`

MUTATIONS, WRITTEN BEFORE THE FIRST RUN, exact sets:
  `baseline_record` returns {} (nothing recorded)         -> A
  `ablation.BASELINE_KEY` renamed (render looks elsewhere) -> B, C, D
  `status.RE_BASE` never matches                          -> C

UNMUTATED (§0z15): the run's own `main` loop (that it stores the key and
skips the save print) -- read, not executed here; a rebuild exercises it.
"""
import json
import re
import sys

import numpy as np

import tools.ablation as AB
import tools.status as ST
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
_REAL = {"rec": AB.baseline_record, "key": AB.BASELINE_KEY, "re": ST.RE_BASE}


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"\n        {detail}"))


def run_cases():
    del PASS[:], FAIL[:]
    run = AB.Run("karlov", 30, (10, 20))
    deck, cmd = build_pending("karlov")
    card = next(c.name for c in deck if not c.is_land)
    stream = AB.ablation_stream(run, [card], 1)
    first = next(stream)
    stream.close()
    direct = AB.columns_all(run, deck, cmd, 0, run.n)
    want = {str(t): float(np.mean(direct[t]["won"])) for t in run.horizons}
    got = first[1].get("won") if first[0] == AB.BASELINE_KEY else None
    check("A the run yields the baseline first, equal to its own columns",
          got == want, f"first={first[0]!r} got={got} want={want}")

    with open(run.__class__("karlov", 15000, (10, 20)).cache) as fh:
        results = json.load(fh)
    results.pop("(baseline)", None)
    nonlands = [c.name for c in deck if not c.is_land]
    partly = AB.partly_for("karlov", deck)
    big = AB.Run("karlov", 15000, (10, 20))
    plain = AB.render_table(big, results, nonlands, partly)
    with_key = dict(results, **{"(baseline)": {"won": {"10": 0.3111,
                                                        "20": 0.5432}}})
    shown = AB.render_table(big, with_key, nonlands, partly)
    check("B the header prints the baseline only when the cache has it",
          "BASELINE:" not in plain and "0.5432 at T20" in shown,
          "missing or spurious BASELINE line")
    m = ST.RE_BASE.search(shown)
    check("C status reads the last horizon's baseline back",
          bool(m) and m.group(1) == "0.5432", f"match={m and m.group(1)}")
    src = open("tools/cache_manifest.py", encoding="utf-8").read()
    lit = re.search(r'k != "([^"]+)"', src)
    check("D the manifest's key literal is ablation.BASELINE_KEY",
          bool(lit) and lit.group(1) == AB.BASELINE_KEY,
          f"{lit and lit.group(1)!r} vs {AB.BASELINE_KEY!r}")
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The baseline record, run -> cache -> table -> STATUS\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    muts = {
        "baseline_record returns {}": ({"A"}, "rec", lambda b: {}),
        "BASELINE_KEY renamed": ({"B", "C", "D"}, "key", "(elsewhere)"),
        "RE_BASE never matches": ({"C"}, "re", re.compile(r"(?!x)x")),
    }
    bad = 0
    for label, (want, what, val) in muts.items():
        print(f"-- {label}")
        if what == "rec":
            AB.baseline_record = val
        elif what == "key":
            AB.BASELINE_KEY = val
        else:
            ST.RE_BASE = val
        try:
            broke = run_cases()
        finally:
            AB.baseline_record, AB.BASELINE_KEY = _REAL["rec"], _REAL["key"]
            ST.RE_BASE = _REAL["re"]
        ok = broke == want
        bad += not ok
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
