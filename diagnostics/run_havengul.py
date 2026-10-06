#!/usr/bin/env python3
"""Havengul Laboratory: what its timing and its colours were costing (§0z112).

    python -m diagnostics.run_havengul 15000 > results/havengul_20261006.txt

The land ablation measured Havengul Laboratory at -0.0581 +-0.0042 against a
Swamp at T20 -- the largest land row in any deck, for a card that is a land
with an activation. Two faults, both against the oracle text: its
"{4}, {T}: Investigate" ran in the UPKEEP (four of every turn's mana before
the main phase, and no {T}), and it was defined as tapping for {B} or {C}
where the Laboratory face taps for {C} only.

Three arms on tivit's staged list, paired, seeds 5000.., one T20 game per
seed with T10 read off it (§0z93):
  old      havengul_at="upkeep", produces B or C (every table before §0z112)
  timing   havengul_at="end",    produces B or C
  fixed    havengul_at="end",    produces C       (the engine as it is now)
"""
import dataclasses
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

NAME = "Havengul Laboratory // Havengul Mystery"
ARMS = {"old": ("upkeep", "BC"), "timing": ("end", "BC"), "fixed": ("end", "C")}
KEYS = ("won", "damage", "cards_drawn", "mana_spent", "havengul_clues")
CHUNKS = 4


def job(task):
    arm, lo, hi = task
    at, colours = ARMS[arm]
    cards, cmd = build_pending("tivit")
    cards = [dataclasses.replace(c, produces=frozenset(colours))
             if c.name == NAME else c for c in cards]
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), havengul_at=at)
    rows = []
    for s in range(lo, hi):
        r = DECKS["tivit"].sim(list(cards), cmd, cfg, 5000 + s)
        rows.append([float(r["at_rounds"][10]["won"])]
                    + [float(r.get(k, 0) or 0) for k in KEYS])
    return rows


def ci(d):
    d = np.asarray(d, float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    n = int(sys.argv[1])
    tasks = [(a, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for a in ARMS for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (a, _lo, _hi), r in zip(tasks, res):
        cols.setdefault(a, []).extend(r)
    print(f"Havengul Laboratory's timing and colours (§0z112). tivit, N={n:,} "
          f"paired, seeds 5000.., staged list. * = CI excludes zero.\n")
    names = ("won T10",) + tuple(f"{k} T20" for k in KEYS)
    base = np.array(cols["old"])
    print(f"old: won T20 {base[:, 1].mean():.4f}")
    for arm in ("timing", "fixed"):
        b = np.array(cols[arm])
        print(f"\n{arm} minus old")
        for i, name in enumerate(names):
            m, h = ci(b[:, i] - base[:, i])
            print(f"    {name:<22}{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ''}")
    b, a = np.array(cols["fixed"]), np.array(cols["timing"])
    m, h = ci(b[:, 1] - a[:, 1])
    print(f"\nfixed minus timing (the colour alone), won T20: {m:+.4f} ±{h:.4f}")


if __name__ == "__main__":
    main()
