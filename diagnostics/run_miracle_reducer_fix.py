#!/usr/bin/env python3
"""Ruby Medallion and Longshot, Rebel Bowman were missing from the miracle
cost math -- three separate partial copies of "the miracle discount" had
drifted apart. This is the paired before/after measurement.

    python run_miracle_reducer_fix.py [--n=15000] [--procs=N]
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import lorehold_v16
from edhmc.experiment import DEFAULT_CFG
from edhmc import lorehold as L

DECK, CMD = lorehold_v16.build()

OBS = ("won", "mv_cheated", "miracles_cast", "damage", "spells_cast",
       "settop_placed", "settop_miracled", "leng_to_top", "leng_miracled",
       "mana_floated", "stranded_mv", "turns_played")

_W = {}

# OLD monkeypatches the three drifted partial implementations back in, so the
# fix can be measured as a paired flip (same seeds, same deck, only the
# miracle-cost math differs) rather than argued from the diff.
#
# APPLIED INSIDE EACH WORKER'S _init, not in the parent process: Windows'
# multiprocessing has no fork, so Pool workers are spawned as fresh
# interpreters that re-import edhmc.lorehold from scratch. A monkeypatch made
# in the parent before creating the Pool never reaches them -- the first cut
# of this script patched the parent only and printed an exact +0.0000 on
# every metric, which is what "the patch never ran" looks like, not what "no
# effect" looks like.
def _install_old():
    def old_reduction(g, card):
        red = 1 if g.has("Artist's Talent") else 0
        red += 1 if (g.has("Ruby Medallion") and card.cost.get("R", 0) > 0) else 0
        return red   # no Longshot
    L.miracle_reduction = old_reduction

    def old_need(g, card=None):
        need = 0 if g.has("Molecule Man") else 2
        if g.has("Artist's Talent"):
            need = max(0, need - 1)
        return need   # card-blind always, no Medallion/Longshot ever
    L.miracle_need = old_need

    def old_value(g, card):
        if card.is_land:
            return -1.0
        if g.has("Molecule Man"):
            return float(card.mv)
        if "Instant" in card.types or "Sorcery" in card.types:
            return float(card.mv) - 2.0
        if card.miracle_cost:
            return float(card.mv) - sum(card.miracle_cost.values())
        return -1.0
    L.miracle_value = old_value


def _init(flags, turns, variant):
    if variant == "old":
        _install_old()
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)


def _one(seed):
    r = L.simulate(DECK, CMD, _W["cfg"], seed)
    return [r[m] for m in OBS]


def observe(variant, flags, n, turns, procs):
    with Pool(procs, initializer=_init,
              initargs=(flags, turns, variant)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    turns = 20

    a = observe("old", {}, n, turns, procs)
    b = observe("new", {}, n, turns, procs)

    print("=" * 78)
    print(f"Ruby Medallion + Longshot in the miracle cost. N = {n:,}, T{turns}.")
    print("=" * 78)
    print("  OLD = the three drifted partial implementations (Medallion applied")
    print("  only in the real payment, Longshot nowhere, miracle_need/_value")
    print("  card-blind). NEW = one shared miracle_reduction(), all three")
    print("  reducers, card-specific where a card is known.\n")
    for i, m in enumerate(OBS):
        d = b[:, i] - a[:, i]
        hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
        star = " *" if abs(d.mean()) > hw else "  "
        print(f"  {m:<18}{a[:, i].mean():>10.4f} ->{b[:, i].mean():>10.4f}"
              f"   {d.mean():>+9.4f} +-{hw:<8.4f}{star}")


if __name__ == "__main__":
    main()
