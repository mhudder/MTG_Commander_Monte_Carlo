#!/usr/bin/env python3
"""Every azusa candidate, measured IN ONE SLOT against one reference card.

WHY THIS SHAPE AND NOT FIFTEEN SWAPS. §0c: candidate rows share a baseline,
so they have overlapping CIs by construction and cannot be ranked against
each other -- which is why fifteen azusa cards sat in `MEASURED` with nothing
decided. §0z35 showed the way out: put one card in the A leg and another in
the SAME SLOT of the B leg, and the difference is PAIRED on the same seeds.

So this runs every candidate against ONE FIXED REFERENCE in Yavimaya Elder's
slot -- Traveling Chocobo, whose own swap value is measured (+0.0265 +-0.0042
at T20, §0z35). Each row is `candidate - Chocobo`, paired. Read it two ways:

  * as a RANKING: every candidate is compared with the same card in the same
    slot on the same seeds, so these rows ARE comparable with each other in a
    way fifteen candidate rows are not.
  * as a SWAP VALUE: add Chocobo's own +0.0265 to get what
    `-Yavimaya Elder +candidate` is worth. That sum's bar is wider than the
    paired bar printed here -- the paired number is the decision-grade one.

THE REFERENCE IS NOT A BASELINE. A candidate at -0.02 here is not a bad card;
it is a card that loses this slot to the Chocobo. Nothing below is evidence
about a card in any other slot.

WATCH THE LAND COUNT. Yavimaya Elder is a CREATURE, so a land candidate
(War Room, Castle Garenbrig) takes the deck to 37 lands, and CLAUDE.md's
standing note applies: a land change is the kind of change this harness
flatters. Those two rows are marked.

    python -m diagnostics.run_azusa_slot            > results/azusa_slot.txt
    python -m diagnostics.run_azusa_slot --n=40     # smoke test, minutes
"""
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import DECKS as CATALOG, MEASURED, build_pending
from edhmc.experiment import run_ab, analyse, _swap_many

N = 15000
CUT = "Yavimaya Elder"
REF = "Traveling Chocobo"
HORIZONS = (10, 20)
METRICS = ("won", "damage", "landfall_triggers", "lands_played",
           "cards_drawn", "final_life", "stranded_mv")

# Ordered by the candidate row each card already has, best first, so the
# decision-relevant comparisons land first if the run is interrupted.
ORDER = [
    "Guardian Project", "Nissa, Resurgent Animist", "The Great Henge",
    "Nissa, Who Shakes the World", "Return of the Wildspeaker",
    "Awaken the Woods", "Sapling Nursery", "Zendikar's Roil",
    "Expedition Map", "Zuran Orb", "Archdruid's Charm",
    "Finale of Devastation", "War Room", "Castle Garenbrig",
]


def candidates() -> list[str]:
    """The MEASURED azusa cards, in ORDER, minus the reference itself.

    Derived from the ledger rather than typed out (§0q): a card measured and
    added to `MEASURED` after this file was written must not silently drop out
    of the comparison, so an unknown name raises instead of being skipped.
    """
    have = [c.card for c in MEASURED if c.deck == "azusa"]
    missing = [c for c in have if c not in ORDER and c != REF]
    if missing:
        raise SystemExit(f"MEASURED azusa cards not in ORDER: {missing}")
    return [c for c in ORDER if c in have]


def job(args):
    name, turns, n = args
    mod, catalog = CATALOG["azusa"]
    staged, cmd = build_pending("azusa")
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    base = _swap_many(staged, [CUT], [catalog[REF]])      # reference in the slot
    t0 = time.time()
    ra, rb, _cfg = run_ab(base, cmd, REF, catalog[name], n=n, turns=turns,
                          sim=REGISTRY["azusa"].sim)
    rows = analyse(ra, rb, metrics=METRICS)
    return (name, turns, time.time() - t0,
            float(np.mean([r["won"] for r in ra])),
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in rows])


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    names = candidates()
    jobs = [(name, t, n) for name in names for t in HORIZONS]
    print(f"azusa: every candidate against {REF} in {CUT}'s slot. "
          f"N={n:,} paired, same seeds both legs, base = build_pending('azusa').")
    print(f"POSITIVE = the candidate beats {REF} in that slot. "
          f"{len(names)} cards, {len(jobs)} runs, {procs} procs.\n")
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for name, turns, secs, base_won, rows in pool.imap_unordered(job, jobs):
            done[(name, turns)] = rows
            print(f"  {name}  T{turns}  ({secs:.0f}s)   "
                  f"A-leg ({REF}) won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()

    print("=" * 78)
    print(f"RANKING: win rate against {REF} in the same slot, paired.")
    print("=" * 78)
    print(f"{'card':<32}{'win T10':>20}{'win T20':>20}")
    for name in names:
        cells = []
        for t in HORIZONS:
            rows = done.get((name, t))
            if rows is None:
                cells.append("       (not run)")
                continue
            _m, diff, lo, hi, sig = rows[0]
            cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}{' *' if sig else '  '}")
        print(f"{name:<32}{cells[0]:>20}{cells[1]:>20}")
    print(f"\n{REF} is the reference and sits at 0.0000 by construction; its "
          f"own swap value is +0.0265 +-0.0042 at T20 (§0z35).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
