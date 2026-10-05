#!/usr/bin/env python3
"""What asking the wipe gate at EVERY optional cast site is worth (§0z104).

    python -m diagnostics.run_wipe_gate 15000 > results/wipe_gate_20261005.txt

`opponents.should_cast_own_wipe` -- sweep only when the table's creatures
meaningfully outnumber yours -- was asked in the main phase alone. Lorehold
cast its own wipes by miracle, Arcane Bombardment, discover, Apex, Jeska's
Will, Goliath and Galvanoth without asking, and karlov's Bolas's Citadel dug
them off the top without asking: 34% of lorehold's own wipes and 9% of
karlov's resolved with the gate closed, on a board the pilot was winning.
`wipe_gate_all_casts` is the fix; False is the old engine. Each deck's staged
list, both arms on the same seeds (5000..), one T20 game per seed with T10
read off it (§0z93).
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

DECKS_HERE = ("lorehold", "karlov")
KEYS = ("won", "damage", "own_wipes_cast")
CHUNKS = 4


def job(task):
    deck, on, lo, hi = task
    cards, cmd = build_pending(deck)
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               wipe_gate_all_casts=on)
    rows = []
    for s in range(lo, hi):
        r = DECKS[deck].sim(list(cards), cmd, cfg, 5000 + s)
        rows.append([float(r["at_rounds"][10]["won"])]
                    + [float(r.get(k, 0) or 0) for k in KEYS])
    return rows


def ci(d):
    d = np.asarray(d, float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    n = int(sys.argv[1])
    tasks = [(d, on, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for d in DECKS_HERE for on in (False, True) for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        res = p.map(job, tasks)
    cols = {}
    for (d, on, _lo, _hi), r in zip(tasks, res):
        cols.setdefault((d, on), []).extend(r)
    print(f"The wipe gate at every optional cast site (§0z104). N={n:,} paired, "
          "seeds 5000.., staged lists. ON minus OFF; * = CI excludes zero.\n")
    names = ("won T10", "won T20", "damage T20", "own wipes / game")
    for d in DECKS_HERE:
        a = np.array(cols[(d, False)]); b = np.array(cols[(d, True)])
        print(f"{d}  (old engine: won T20 {a[:, 1].mean():.4f}, "
              f"own wipes {a[:, 3].mean():.3f}/game)")
        for i, name in enumerate(names):
            m, h = ci(b[:, i] - a[:, i])
            print(f"    {name:<18}{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ''}")
        print()


if __name__ == "__main__":
    main()
