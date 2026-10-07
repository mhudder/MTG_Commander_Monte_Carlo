#!/usr/bin/env python3
"""Is the commander's shroud worth anything to karlov? (§0z118)

    python -m diagnostics.run_karlov_shroud 15000 > results/karlov_shroud_20261007.txt

N paired games on the staged list, the tables' seeds (5000..), one T20 game
per seed with T10 read off it. ARM MINUS THE SHIPPED ENGINE:

  no shroud                     `shroud_sources=()`: Swiftfoot Boots,
                                Lightning Greaves, Whispersilk Cloak and
                                Mother of Runes shroud nothing
  Mother home, no other shroud  only Mother shrouds, and she never attacks

Written because §0z118's Mother of Runes arms said keeping her home to
shroud the commander COST karlov: with the commander an illegal target the
pod's spot removal takes the next-biggest threat, and in this deck that is
an engine piece worth more than a three-mana commander recast.
"""
import sys

import numpy as np
from multiprocessing import Pool

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

ARMS = {"base": {},
        "no shroud": {"shroud_sources": ()},
        "Mother home, no other shroud": {
            "mother_home": "always", "shroud_sources": ("Mother of Runes",)}}


def job(task):
    arm, lo, hi = task
    run = AB.Run("karlov", 1, (10, 20))
    deck, cmd = build_pending("karlov")
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset(),
               snapshot_rounds=(10,), **ARMS[arm])
    rows = [run.sim(list(deck), cmd, cfg, 5000 + i) for i in range(lo, hi)]
    return task, ([float(r["won"]) for r in rows],
                  [float(r["at_rounds"][10]["won"]) for r in rows],
                  sum(float(r.get("removal_eaten", 0)) for r in rows))


def main(n, procs=4):
    parts = AB._chunks(n, procs)
    with Pool(procs) as pool:
        got = dict(pool.map(job, [(a, lo, hi) for a in ARMS
                                  for lo, hi in parts]))

    def col(arm, k):
        return np.concatenate([np.array(got[(arm, lo, hi)][k])
                               for lo, hi in parts])

    def eaten(arm):
        return sum(got[(arm, lo, hi)][2] for lo, hi in parts) / n
    print(f"KARLOV: IS THE COMMANDER'S SHROUD WORTH ANYTHING? N={n:,} paired, "
          f"ARM MINUS THE SHIPPED ENGINE\n")
    for arm in ARMS:
        if arm == "base":
            continue
        for k, h in ((1, "T10"), (0, "T20")):
            x = col(arm, k) - col("base", k)
            print(f"  {arm:<30}{h} {x.mean():+.4f} "
                  f"±{1.96 * x.std(ddof=1) / np.sqrt(n):.4f}")
        print(f"     removal_eaten a game {eaten(arm):.3f}, shipped "
              f"{eaten('base'):.3f}")


if __name__ == "__main__":
    main(int(sys.argv[1]))
