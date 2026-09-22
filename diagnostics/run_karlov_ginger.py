#!/usr/bin/env python3
"""Ginger, Queen of Sweets against the cut item 22 established, and against
the card that already wants that slot.

THE CANDIDATE ROW IS +0.0059 +-0.0027 (results/candidates_karlov3.txt) and
P(deploy) is 0.156 -- a {6} lands in one game in six, which is the Bolas's
Citadel shape (14.4%). A row that small needs its MECHANISM read before it
means anything, so this prints the counters beside the objective.

Two runs, both paired on the same seeds:

  1. THE REAL SWAP: -Swiftfoot Boots +Ginger, against the live staged list.
     Directly comparable with §0z36's two measurements on the same cut --
     Bloodthirsty Conqueror +0.0401 +-0.0037 and Alhammarret's Archive
     +0.0168 +-0.0030 at T20.

  2. THE DIRECT RANKING, which §0c says a common baseline cannot give: the
     Conqueror in the A leg and Ginger in the SAME slot of the B leg, so the
     difference is paired rather than inferred. POSITIVE = Ginger is better.

BASELINE. `build_pending("karlov")` applies both staged karlov changes, so
the Citadel and the Conqueror are IN on run 1's legs, exactly as they were
for §0z36.

    python -m diagnostics.run_karlov_ginger        > results/karlov_ginger.txt
    python -m diagnostics.run_karlov_ginger --n=40 # smoke test
"""
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.experiment import run_ab, analyse, _swap_many

N = 15000
CUT = "Swiftfoot Boots"
ADD = "Ginger, Queen of Sweets"
RIVAL = "Bloodthirsty Conqueror"
HORIZONS = (10, 20)
METRICS = ("won", "damage", "lifegain_triggers", "life_gained", "cards_drawn",
           "gingerbrutes_made", "gingerbrute_sacs", "monarch_turns",
           "monarch_draws", "monarch_lost", "stranded_mv")


def legs(label):
    _mod, catalog = CATALOG["karlov"]
    staged, cmd = build_pending("karlov")
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    if label == "real-swap":
        return staged, [CUT], [catalog[ADD]], cmd
    if label == "vs-the-rival":
        # THE SAME SLOT, which is the only comparison §0c allows between two
        # cards. The first version of this leg passed outs=[CUT, RIVAL] against
        # the staged list, which already HOLDS the Conqueror -- it swapped the
        # Boots for a second copy of him and then swapped one of the two away.
        # It reported +0.0169 and meant nothing.
        #
        # Built the way §0z36 built the Conqueror's own +0.0401: restore
        # Soulmender in his place to get the PRE-SWAP list, put him in the
        # Boots' slot, and then the one paired difference is who occupies that
        # slot. POSITIVE = Ginger.
        assert any(c.name == RIVAL for c in staged), f"{RIVAL} is not staged"
        pre = _swap_many(staged, [RIVAL], [module_card("Soulmender")])
        a_leg = _swap_many(pre, [CUT], [catalog[RIVAL]])
        return a_leg, [RIVAL], [catalog[ADD]], cmd
    raise KeyError(label)


def module_card(name: str):
    """The Card as the karlov MODULE defines it -- a staged cut has already
    left `build_pending`'s list, so restoring one reaches past it (§0z31)."""
    mod, _catalog = CATALOG["karlov"]
    deck, _cmd = mod.build()
    for c in deck:
        if c.name == name:
            return c
    raise KeyError(f"{name} is not in the karlov module")


def job(args):
    label, turns, n = args
    base, outs, ins, cmd = legs(label)
    t0 = time.time()
    ra, rb, _cfg = run_ab(base, cmd, outs, ins, n=n, turns=turns,
                          sim=REGISTRY["karlov"].sim)
    rows = analyse(ra, rb, metrics=METRICS)
    # Conditional on the card actually resolving: P(deploy) is 0.156, so the
    # unconditional counters are mostly zeros and say little about the card.
    dep = [r for r in rb if float(r.get("gingerbrutes_made", 0)) > 0
           or float(r.get("monarch_gained", 0)) > 0]
    cond = {k: (float(np.mean([r.get(k, 0) for r in dep])) if dep else 0.0)
            for k in ("gingerbrutes_made", "gingerbrute_sacs", "monarch_turns",
                      "monarch_draws")}
    return (label, turns, time.time() - t0,
            float(np.mean([r["won"] for r in ra])), len(dep) / max(1, len(rb)),
            cond,
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in rows])


HEADINGS = {
    "real-swap":
        f"1. -{CUT} +{ADD}, the real swap against the live staged list.\n"
        f"     Compare: {RIVAL} +0.0401 and Alhammarret's Archive +0.0168 "
        f"on this same cut (§0z36).",
    "vs-the-rival":
        f"2. {RIVAL} -> {ADD} in the {CUT} slot, on the PRE-SWAP list "
        f"(Soulmender restored),\n     built as §0z36 built the Conqueror's "
        f"+0.0401. POSITIVE = {ADD} is the better card for that slot.",
}


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    labels = list(HEADINGS)
    jobs = [(lab, t, n) for lab in labels for t in HORIZONS]
    print(f"karlov x Ginger, Queen of Sweets. N={n:,} paired, same seeds both "
          f"legs, base = build_pending('karlov').\n")
    for lab in labels:
        print(f"  {HEADINGS[lab]}")
    print()
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for label, turns, secs, base_won, pdep, cond, rows in \
                pool.imap_unordered(job, jobs):
            done[(label, turns)] = rows
            print(f"  {label}  T{turns}  ({secs:.0f}s)   A-leg won {base_won:.4f}"
                  f"   P(Ginger resolves) {pdep:.3f}")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print(f"    CONDITIONAL on resolving: "
                  + "  ".join(f"{k}={v:.2f}" for k, v in cond.items()))
            print()
            sys.stdout.flush()

    print("=" * 78)
    print("SUMMARY: win rate, paired")
    print("=" * 78)
    print(f"{'run':<34}{'win T10':>20}{'win T20':>20}")
    for lab in labels:
        cells = []
        for t in HORIZONS:
            rows = done.get((lab, t))
            if rows is None:
                cells.append("       (not run)")
                continue
            _m, diff, lo, hi, sig = rows[0]
            cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}{' *' if sig else '  '}")
        print(f"{lab:<34}{cells[0]:>20}{cells[1]:>20}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
