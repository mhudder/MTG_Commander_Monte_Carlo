#!/usr/bin/env python3
"""The two Reality Fracture cards imported into azusa, measured two ways.

PREVIEW TEXT: Reality Fracture releases 2026-10-02 and this was fetched on
2026-09-20, so every number here is a claim with a date on it.

Each card is run BOTH ways, because the two answer different questions and the
project has confused them before (§0c):

  vs YAVIMAYA ELDER   the real swap. What the deck gains by playing this card
                      instead of the cut §0z35 named. This is the number a
                      staging rests on.
  vs TRAVELING CHOCOBO IN YAVIMAYA'S SLOT
                      the ranking. Same slot, same seeds, so this is directly
                      comparable with every row of results/azusa_slot.txt --
                      the backlog's fourteen cards measured against the same
                      reference. A candidate row could not be compared with
                      those; this can.

    python -m diagnostics.run_azusa_fra > results/azusa_fra.txt
    python -m diagnostics.run_azusa_fra --n=40      # smoke test
"""
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.experiment import run_ab, analyse, _swap_many

N = 15000
CUT = "Yavimaya Elder"
REF = "Traveling Chocobo"
CARDS = ("Verdant Kraken", "Simulacrum Shaper")
HORIZONS = (10, 20)
METRICS = ("won", "damage", "landfall_triggers", "lands_played", "cards_drawn",
           "final_life", "stranded_mv", "kraken_tokens", "shaper_lands",
           "shaper_draws", "tokens_made")


def legs(card, against):
    _mod, catalog = CATALOG["azusa"]
    staged, cmd = build_pending("azusa")
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    if against == "cut":
        return staged, CUT, catalog[card], cmd
    base = _swap_many(staged, [CUT], [catalog[REF]])
    return base, REF, catalog[card], cmd


def job(args):
    card, against, turns, n = args
    base, out_name, in_card, cmd = legs(card, against)
    t0 = time.time()
    ra, rb, _cfg = run_ab(base, cmd, out_name, in_card, n=n, turns=turns,
                          sim=REGISTRY["azusa"].sim)
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
    print(f"azusa x Reality Fracture. N={n:,} paired, same seeds both legs, "
          f"base = build_pending('azusa').")
    print(f"  'cut' = -{CUT} +card, the real swap.")
    print(f"  'ref' = {REF} -> card in {CUT}'s slot, comparable with "
          f"results/azusa_slot.txt.\n")
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for card, against, turns, secs, base_won, rows in pool.imap_unordered(job, jobs):
            done[(card, against, turns)] = rows
            print(f"  {card}  vs {against}  T{turns}  ({secs:.0f}s)   "
                  f"A-leg won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                if metric in ("kraken_tokens", "shaper_lands", "shaper_draws") \
                        and abs(diff) < 1e-9:
                    continue          # the other card's counter, always 0
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()

    print("=" * 78)
    print("SUMMARY: win rate, paired")
    print("=" * 78)
    print(f"{'card':<22}{'against':<10}{'win T10':>20}{'win T20':>20}")
    for card in CARDS:
        for against in ("cut", "ref"):
            cells = []
            for t in HORIZONS:
                rows = done.get((card, against, t))
                if rows is None:
                    cells.append("       (not run)")
                    continue
                _m, diff, lo, hi, sig = rows[0]
                cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}"
                             f"{' *' if sig else '  '}")
            label = f"-{CUT}" if against == "cut" else f"vs {REF}"
            print(f"{card:<22}{label:<10}{cells[0]:>20}{cells[1]:>20}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
