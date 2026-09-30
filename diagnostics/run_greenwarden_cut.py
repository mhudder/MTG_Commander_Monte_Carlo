#!/usr/bin/env python3
"""Ancient Greenwarden's cut, moved from Sylvan Awakening to Oblivion Stone
by the owner (2026-09-30, §0z88).

    python -m diagnostics.run_greenwarden_cut 15000

The list is identical either way except for ONE slot, so the paired
difference is the decision itself:

    A  Oblivion Stone in the slot   (the list as committed 2026-09-10)
    B  Sylvan Awakening in the slot (the list after this change)

Oblivion Stone is KNOWN_BLIND in azusa -- a fate-counter wipe the engine
does not play -- so it scores as a {3} artifact that does nothing, and B
measures Sylvan Awakening against that. §0z36: a blind cut can flatter a
swap OR cost it, and this run cannot see what the Stone does at a real
table. Sylvan Awakening is fully modelled (land animation, §0s).

Every engine module is imported in the PARENT before the pool forks, so the
workers run this code even if the deck module is edited while it runs.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks.azusa_v1 import C
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

MET = ("won", "damage", "landfall_triggers", "cards_drawn", "removal_eaten")
SYLVAN = C("Sylvan Awakening", "Sorcery", {"gen": 2, "G": 1}, priority=7,
           threat=6.5, script="sylvan_awakening")
DECK, CMD = build_pending("azusa")
A = list(DECK)
B = [SYLVAN if c.name == "Oblivion Stone" else c for c in DECK]
assert sum(c.name == "Oblivion Stone" for c in A) == 1
assert sum(c.name == "Sylvan Awakening" for c in B) == 1 and len(A) == len(B)
SIM = DECKS["azusa"].sim


def job(a):
    arm, turns, lo, hi = a
    deck = A if arm == "A" else B
    cfg = dict(DEFAULT_CFG, turns=turns)
    return [[float(SIM(list(deck), CMD, cfg, 5000 + s).get(m, 0) or 0)
             for m in MET] for s in range(lo, hi)]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    ch = 8
    tasks = [(arm, t, k * n // ch, (k + 1) * n // ch)
             for t in (10, 20) for arm in ("A", "B") for k in range(ch)]
    with Pool(4) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (arm, t, _, _), r in zip(tasks, res):
        cols.setdefault((arm, t), []).extend(r)
    print(f"azusa staged list, N={n:,} paired, seeds 5000..{5000 + n - 1}")
    print("B - A: Sylvan Awakening in Oblivion Stone's slot\n")
    for t in (10, 20):
        a, b = np.array(cols[("A", t)]), np.array(cols[("B", t)])
        print(f"T{t}")
        for i, m in enumerate(MET):
            d = b[:, i] - a[:, i]
            ci = 1.96 * d.std(ddof=1) / np.sqrt(n)
            star = "*" if abs(d.mean()) > ci else " "
            print(f"  {m:<20}{a[:, i].mean():>10.4f} -> {b[:, i].mean():>10.4f}"
                  f"   {d.mean():+.4f} ±{ci:.4f}{star}")


if __name__ == "__main__":
    main()
