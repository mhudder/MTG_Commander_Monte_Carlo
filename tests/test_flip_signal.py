#!/usr/bin/env python3
"""§0z24 — `FLIP` is gated on significance, and no longer eats "unmeasured".

    python -m tests.test_flip_signal
    python -m tests.test_flip_signal --mutate   # 3 mutations, exact sets

THE DEFECT. `ablation.py` classified a row and then overrode it with FLIP
whenever `np.sign()` of the raw damage point estimate disagreed between
horizons -- no significance test. A card whose damage was statistically zero
has a coin-flip sign, so it was labelled FLIP whenever the coins disagreed:
the strongest-sounding label, on the rows with the least evidence, replacing
the one label (`--`) that says "unmeasured, do not rank".

THE FIX, as §0z24 specified it: FLIP only when damage is SIGNIFICANT at every
horizon and the signs disagree. A gate, not a removal. On the committed
tables it moved 20 FLIP rows to 4, changed NO number in any row, and kept
The Great Henge, shilgengar's Damn and Wrath of God, and Mechanized
Production -- each significant at both horizons with opposite signs.

CASES, each a synthetic row so the rule is tested, not a table:
  A  significant at both horizons, opposite signs      -> FLIP
  B  significant at both horizons, SAME sign           -> its own label
  C  significant only at T10, signs disagree -- a cost that FADES rather than
     reverses (tivit's Damn: -1.46 +-0.18 then +0.08 +-0.22) -> not FLIP
  D  inside its bar at both, signs disagree (the Biotransference case)  -> --
  E  a single horizon can never FLIP
  F  win significant, damage noise with a flipped sign (Primal Vigor)   -> win,
     so the override no longer eats a real win label

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the significance gate is removed (the old rule)   -> C, D and F
  the gate asks for ANY significant horizon, not all -> C
  FLIP is removed entirely                          -> A
"""
import sys

import numpy as np

import tools.ablation as AB

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
HZ = ["10", "20"]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def row(d10, d20, won):
    return {"10": {"damage": d10, "won": won}, "20": {"damage": d20, "won": won}}


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    check("A significant both horizons, opposite signs -> FLIP",
          AB.signal(row((-1.0, 0.2), (+0.8, 0.2), (0.005, 0.002)), HZ), "FLIP")
    check("B significant both horizons, same sign -> its own label",
          AB.signal(row((-1.0, 0.2), (-0.8, 0.2), (0.005, 0.002)), HZ), "both")
    check("C significant only at T10 (a cost that fades) -> not FLIP",
          AB.signal(row((-1.46, 0.18), (+0.08, 0.22), (0.0070, 0.0034)), HZ),
          "win")
    check("D inside its bar at both, signs disagree -> --",
          AB.signal(row((-0.001, 0.02), (+0.001, 0.04), (0.0005, 0.001)), HZ),
          "--")
    one = {"20": {"damage": (-1.0, 0.2), "won": (0.005, 0.002)}}
    check("E a single horizon can never FLIP", AB.signal(one, ["20"]), "both")
    check("F win significant, damage noise flipped -> win",
          AB.signal(row((-0.03, 0.05), (+0.06, 0.09), (0.0075, 0.0022)), HZ),
          "win")
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z24 -- FLIP is gated on significance\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = AB.flips
    sign = lambda res, hz: len({np.sign(res[h]["damage"][0]) for h in hz}) > 1
    muts = {
        "the significance gate is removed (the old rule)":
            (lambda res, hz: len(hz) > 1 and sign(res, hz), {"C", "D", "F"}),
        "the gate asks for ANY significant horizon, not all":
            (lambda res, hz: len(hz) > 1 and sign(res, hz) and any(
                abs(res[h]["damage"][0]) > res[h]["damage"][1] for h in hz), {"C"}),
        "FLIP is removed entirely":
            (lambda res, hz: False, {"A"}),
    }
    bad = 0
    for label, (fn, want) in muts.items():
        print(f"-- {label}")
        AB.flips = fn
        try:
            broke = run_cases()
        finally:
            AB.flips = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected {sorted(want)}"
              f"  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed ({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
