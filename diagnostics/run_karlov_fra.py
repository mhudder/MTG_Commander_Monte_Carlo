#!/usr/bin/env python3
"""The two Reality Fracture cards imported into karlov, measured two ways.

PREVIEW TEXT: Reality Fracture releases 2026-10-02 and this was fetched on
2026-09-20, so every number here is a claim with a date on it.

  vs SWIFTFOOT BOOTS   the real swap, against the cut §0z35 established and
                       §0z36 measured. This is the number a staging rests on.
  vs BLOODTHIRSTY CONQUEROR IN THE BOOTS' SLOT
                       the ranking. §0z36 measured `-Swiftfoot Boots
                       +Bloodthirsty Conqueror` at +0.0401 ±0.0037, so the
                       Boots are ONE SLOT that the Conqueror already wants.
                       A new card is only worth that slot if it beats the
                       Conqueror in it, and a shared baseline cannot say
                       (§0c) -- this can, because both legs put a card in the
                       same slot on the same seeds.

BASELINE. `build_pending("karlov")` applies both staged changes, so the
Conqueror is already IN the list in Soulmender's slot. The 'ref' runs
therefore restore Soulmender first and put the Conqueror in the Boots' slot
instead, which is exactly the leg §0z36's run 2 measured -- so its +0.0401 is
the number these rows are differences from.

    python -m diagnostics.run_karlov_fra > results/karlov_fra.txt
    python -m diagnostics.run_karlov_fra --n=40      # smoke test
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
REF = "Bloodthirsty Conqueror"
CARDS = ("Liliana the Faultless", "Edgar, Ancient Bloodlord")
HORIZONS = (10, 20)
METRICS = ("won", "damage", "lifegain_triggers", "life_gained",
           "karlov_counters", "combo_assembled", "wipes_suffered",
           "liliana_triggers", "edgar_triggers", "stranded_mv")


def module_card(name):
    mod, _ = CATALOG["karlov"]
    return next(c for c in mod.build()[0] if c.name == name)


def legs(card, against):
    _mod, catalog = CATALOG["karlov"]
    staged, cmd = build_pending("karlov")
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    if against == "cut":
        return staged, CUT, catalog[card], cmd
    # Put the list into §0z36's run-2 shape: Soulmender back, Conqueror in the
    # Boots' slot. The B leg then swaps the Conqueror for the candidate.
    base = _swap_many(staged, [REF, CUT],
                      [module_card(OLD_CUT), catalog[REF]])
    return base, REF, catalog[card], cmd


def job(args):
    card, against, turns, n = args
    base, out_name, in_card, cmd = legs(card, against)
    t0 = time.time()
    ra, rb, _cfg = run_ab(base, cmd, out_name, in_card, n=n, turns=turns,
                          sim=REGISTRY["karlov"].sim)
    return (card, against, turns, time.time() - t0,
            float(np.mean([r["won"] for r in ra])),
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in analyse(ra, rb, metrics=METRICS)])


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    jobs = [(c, a, t, n) for c in CARDS for a in ("cut", "ref")
            for t in HORIZONS]
    print(f"karlov x Reality Fracture. N={n:,} paired, same seeds both legs.\n"
          f"  'cut' = -{CUT} +card, the real swap.\n"
          f"  'ref' = {REF} -> card in the {CUT} slot; positive means the "
          f"candidate beats the card already queued for it.\n")
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for card, against, turns, secs, base_won, rows in pool.imap_unordered(job, jobs):
            done[(card, against, turns)] = rows
            print(f"  {card}  vs {against}  T{turns}  ({secs:.0f}s)   "
                  f"A-leg won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                if metric in ("liliana_triggers", "edgar_triggers") \
                        and abs(diff) < 1e-9:
                    continue
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()

    print("=" * 78)
    print("SUMMARY: win rate, paired")
    print("=" * 78)
    print(f"{'card':<26}{'against':<22}{'win T10':>18}{'win T20':>18}")
    for card in CARDS:
        for against in ("cut", "ref"):
            cells = []
            for t in HORIZONS:
                rows = done.get((card, against, t))
                if rows is None:
                    cells.append("      (not run)")
                    continue
                _m, diff, lo, hi, sig = rows[0]
                cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}"
                             f"{' *' if sig else '  '}")
            label = f"-{CUT}" if against == "cut" else f"vs {REF}"
            print(f"{card:<26}{label:<22}{cells[0]:>18}{cells[1]:>18}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
