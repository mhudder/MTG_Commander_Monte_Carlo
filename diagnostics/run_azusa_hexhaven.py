#!/usr/bin/env python3
"""§0z249: Hexhaven Invigorator into each of four azusa slots, one paired run.

    python -m diagnostics.run_azusa_hexhaven 15000 \\
        > results/azusa_hexhaven_slots_20261122.txt

The owner, 2026-11-22: "Of the following cards in Azusa, which one was the
weakest?" (Greensleeves, Ka-Zar, Mole Man, Mossborn Hydra, Springheart,
Traveling Chocobo), then "Run them, please also run hexhaven invigorator. I
would like to replace the weakest card with it." The table (§0e) cannot rank
the bottom four -- Ka-Zar, Springheart Nantuko, Greensleeves and Traveling
Chocobo, within one noise floor of each other -- so this run does.

Five lists on the same seeds (5000..): the staged list, and the list with
Hexhaven Invigorator in each cut's EXACT position (`_swap_many`, so common
random numbers cancel the other 98 cards). Each leg minus the base is that
SWAP's number, the decision itself. Any two legs differ ONLY in which card
Hexhaven replaced, so leg X minus leg Y is "cut Y" against "cut X" with the
same replacement -- the head-to-head of the two cards, measured, not
inferred from two rows that share a baseline (the comparison §0e forbids).
One T20 game per list per seed, T10 read off it (§0z93).
"""
import sys
from itertools import combinations
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.registry import DECKS as REGISTRY

NEW = "Hexhaven Invigorator"
CUTS = ("Ka-Zar of the Savage Land", "Springheart Nantuko",
        "Greensleeves, Maro-Sorcerer", "Traveling Chocobo")
KEYS = ("won", "damage", "landfall_triggers", "lands_played", "cards_drawn",
        "hexhaven_triggers", "hexhaven_damage", "hexhaven_lands")
CHUNKS = 4


def legs():
    base, cmd = build_pending("azusa")
    cat = CATALOG["azusa"][1]
    out = {"base": base}
    for cut in CUTS:
        assert any(c.name == cut for c in base), f"{cut!r} is not in the list"
        out[cut] = _swap_many(base, [cut], [cat[NEW]])
    return out, cmd


def job(task):
    lo, hi = task
    decks, cmd = legs()
    sim = REGISTRY["azusa"].sim
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), watch=frozenset())
    out = {k: [] for k in decks}
    for s in range(lo, hi):
        for leg, deck in decks.items():
            r = sim(list(deck), cmd, cfg, 5000 + s)
            row = {f"{m}20": float(r.get(m, 0) or 0) for m in KEYS}
            row["won10"] = float(r["at_rounds"][10]["won"])
            out[leg].append(row)
    return out


def ci(d):
    d = np.asarray(d, float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    n = int(sys.argv[1])
    tasks = [(k * n // CHUNKS, (k + 1) * n // CHUNKS) for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        parts = p.map(job, tasks)
    rows = {leg: sum((part[leg] for part in parts), []) for leg in parts[0]}

    def col(leg, key):
        return np.array([r[key] for r in rows[leg]])

    def line(x, y, keys):
        for key in keys:
            m, h = ci(col(y, key) - col(x, key))
            print(f"      {key:<22}{m:+.4f} ±{h:.4f}"
                  f"{'*' if abs(m) > h else ''}")

    print(f"azusa: {NEW} into four slots. N={n:,} paired, seeds 5000.., "
          f"base = build_pending('azusa'), the new card in each cut's exact "
          f"position.\n* = the 95% CI excludes zero.\n")
    print("THE SWAPS (leg minus base; positive = the swap wins more):")
    for cut in CUTS:
        print(f"  -{cut} +{NEW}")
        line("base", cut, ("won10", "won20", "damage20",
                           "landfall_triggers20", "lands_played20"))
    print("\nTHE CUTS HEAD TO HEAD (leg Y minus leg X = keep X's card, cut "
          "Y's, against keep Y's, cut X's;\npositive = X's card is the "
          "WEAKER of the two -- cutting it costs less):")
    for x, y in combinations(CUTS, 2):
        print(f"  {x}  vs  {y}")
        line(y, x, ("won10", "won20"))
    print(f"\n  {NEW}'s own counters, T20, means per game:")
    for cut in CUTS:
        own = "  ".join(f"{k} {col(cut, k + '20').mean():.3f}"
                        for k in ("hexhaven_triggers", "hexhaven_damage",
                                  "hexhaven_lands"))
        print(f"      in {cut}'s slot: {own}")
    print(f"\n  base win rate: T10 {col('base', 'won10').mean():.4f}, "
          f"T20 {col('base', 'won20').mean():.4f}")


if __name__ == "__main__":
    main()
