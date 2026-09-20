#!/usr/bin/env python3
"""Karlov's candidates against the cut §0z35 established: Swiftfoot Boots.

QUEUED ITEM 22 named a cut and left it unattached, because a cut is half a
swap. This is the other half, three paired runs at the project's swap
convention:

  1. THE CUT COMPARISON, and it is the decisive one. Both legs play
     Bloodthirsty Conqueror; the A leg cuts Soulmender (the live staging) and
     the B leg cuts Swiftfoot Boots. POSITIVE = the Boots are the better cut.
     This is the measurement §0z31 asked for without being able to name it:
     the staged cut is MODEL-BLIND, so the staged +0.0254 is a CEILING, and
     the only way to know whether the blind cut flattered the swap is to run
     the same card against a cut whose row IS evidence.

  2. THE SWAP AS IT WOULD BE STAGED ON THE NEW CUT: -Swiftfoot Boots
     +Bloodthirsty Conqueror, measured on the SAME baseline the staged version
     was measured on (Soulmender still in the list). Directly comparable with
     the +0.0259 / +0.0254 in the ledger.

  3. -Swiftfoot Boots +Alhammarret's Archive, against the live staged list.
     The Archive is HELD on the owner's playtest experience and this run does
     not reopen that -- it prices the card against a real cut instead of
     against a blank, which is the number the hold was never given.

BASELINE. `build_pending("karlov")` applies BOTH staged karlov changes
(-Soulmender +Bloodthirsty Conqueror and -Swamp +Bolas's Citadel), so the
Citadel is IN on every leg here, exactly as it was for the staged
measurement. Run 2's baseline restores Soulmender to that list and nothing
else.

    python -m diagnostics.run_karlov_boots        > results/karlov_boots.txt
    python -m diagnostics.run_karlov_boots --n=40 # smoke test
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
OLD_CUT = "Soulmender"
ADD = "Bloodthirsty Conqueror"
HORIZONS = (10, 20)
METRICS = ("won", "damage", "lifegain_triggers", "life_gained",
           "combo_assembled", "protected", "removal_eaten", "stranded_mv")


def module_card(name: str):
    """The Card as the karlov MODULE defines it.

    A staged cut has already left `build_pending`'s list, so restoring one
    means reaching past it into the module -- the same place
    `pending.classify_cut` looks for exactly this reason (§0z31).
    """
    mod, _catalog = CATALOG["karlov"]
    deck, _cmd = mod.build()
    for c in deck:
        if c.name == name:
            return c
    raise KeyError(f"{name} is not in the karlov module")


def legs(label):
    """(A-leg deck, out_names, in_cards, commander) for one of the three runs."""
    _mod, catalog = CATALOG["karlov"]
    staged, cmd = build_pending("karlov")
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    assert any(c.name == ADD for c in staged), f"{ADD} is not staged"
    if label == "cut-comparison":
        # A = the live staging. B moves the Conqueror into the Boots' slot and
        # puts Soulmender back, so both legs play the Conqueror and the only
        # difference is WHICH card paid for it.
        return staged, [ADD, CUT], [module_card(OLD_CUT), catalog[ADD]], cmd
    if label == "conqueror-on-the-new-cut":
        base = _swap_many(staged, [ADD], [module_card(OLD_CUT)])   # pre-swap list
        return base, [CUT], [catalog[ADD]], cmd
    if label == "archive-on-the-new-cut":
        return staged, [CUT], [catalog["Alhammarret's Archive"]], cmd
    raise KeyError(label)


def job(args):
    label, turns, n = args
    base, outs, ins, cmd = legs(label)
    t0 = time.time()
    ra, rb, _cfg = run_ab(base, cmd, outs, ins, n=n, turns=turns,
                          sim=REGISTRY["karlov"].sim)
    rows = analyse(ra, rb, metrics=METRICS)
    return (label, turns, time.time() - t0,
            float(np.mean([r["won"] for r in ra])),
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in rows])


HEADINGS = {
    "cut-comparison":
        f"1. BOTH legs play {ADD}. A cuts {OLD_CUT} (the live staging), "
        f"B cuts {CUT}.\n     POSITIVE = {CUT} is the better cut.",
    "conqueror-on-the-new-cut":
        f"2. -{CUT} +{ADD} on the pre-swap list ({OLD_CUT} restored).\n"
        f"     Compare with the ledger's +0.0259 / +0.0254 on the blind cut.",
    "archive-on-the-new-cut":
        f"3. -{CUT} +Alhammarret's Archive against the live staged list.",
}


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    labels = list(HEADINGS)
    jobs = [(lab, t, n) for lab in labels for t in HORIZONS]
    print(f"karlov, against the cut §0z35 established. N={n:,} paired, same "
          f"seeds both legs, base = build_pending('karlov') (Citadel IN).\n")
    for lab in labels:
        print(f"  {HEADINGS[lab]}")
    print()
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for label, turns, secs, base_won, rows in pool.imap_unordered(job, jobs):
            done[(label, turns)] = rows
            print(f"  {label}  T{turns}  ({secs:.0f}s)   A-leg won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
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
