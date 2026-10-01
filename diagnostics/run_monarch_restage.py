#!/usr/bin/env python3
"""The two monarch cards' real swaps, restated after §0z97.

    python -m diagnostics.run_monarch_restage 15000 > results/monarch_restage_20261001.txt

Losing the crown used to `break` the pod's chip-damage loop, so every
opponent seated after the one who took it dealt nothing that round. That
undercharged exactly the games in which you had been the monarch, so both
cards that grant it were measured high. Each swap is run twice on the same
seeds -- the old loop (`crown_loss_ends_chip=True`, which reproduces the
engine the ledger's number came from) and the fixed one -- so the restated
number and the size of the correction come out of one run.

  lorehold  -Lightning Greaves +Chief Magistrate of Mercadia  (SIMULATED)
  karlov    -Swiftfoot Boots   +Ginger, Queen of Sweets       (MEASURED)

Base lists are `build_pending`, as when the ledger's numbers were taken.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import run_ab
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.registry import DECKS as REGISTRY

SWAPS = (("lorehold", "Lightning Greaves", "Chief Magistrate of Mercadia"),
         ("karlov", "Swiftfoot Boots", "Ginger, Queen of Sweets"))
ARMS = {"old": {"crown_loss_ends_chip": True},
        "fixed": {"crown_loss_ends_chip": False}}
CHUNKS = 4


def job(a):
    deck, cut, add, arm, turns, lo, hi = a
    base, cmd = build_pending(deck)
    card = CATALOG[deck][1][add]
    ra, rb, _ = run_ab(base, cmd, cut, card, n=hi - lo, cfg=ARMS[arm],
                       base_seed=1234 + lo, turns=turns,
                       sim=REGISTRY[deck].sim)
    return [(float(x["won"]), float(y["won"]),
             float(y.get("monarch_turns", 0)), float(y.get("monarch_lost", 0)))
            for x, y in zip(ra, rb)]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    tasks = [(d, c, a, arm, t, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for d, c, a in SWAPS for arm in ARMS for t in (10, 20)
             for k in range(CHUNKS)]
    with Pool(4) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (d, _c, _a, arm, t, _lo, _hi), rows in zip(tasks, res):
        cols.setdefault((d, arm, t), []).extend(rows)
    print(f"Monarch swaps restated after §0z97. N={n:,} paired per cell, "
          "seeds 1234.., both arms on the same seeds.\n")
    for d, c, a in SWAPS:
        print(f"{d}: -{c} +{a}")
        for t in (10, 20):
            arr = {arm: np.array(cols[(d, arm, t)]) for arm in ARMS}
            cells = []
            for arm in ARMS:
                diff = arr[arm][:, 1] - arr[arm][:, 0]
                ci = 1.96 * diff.std(ddof=1) / np.sqrt(len(diff))
                cells.append(f"{arm} {diff.mean():+.4f} ±{ci:.4f}"
                             f"{'*' if abs(diff.mean()) > ci else ' '}")
            # The correction itself, paired: the B leg's win under each arm.
            corr = arr["fixed"][:, 1] - arr["old"][:, 1]
            corr -= arr["fixed"][:, 0] - arr["old"][:, 0]
            ci = 1.96 * corr.std(ddof=1) / np.sqrt(len(corr))
            mt = arr["fixed"][:, 2].mean()
            print(f"  T{t}  " + "   ".join(cells)
                  + f"   fix moved the swap {corr.mean():+.4f} ±{ci:.4f}"
                  + f"   monarch turns {mt:.2f}")
        print()


if __name__ == "__main__":
    main()
