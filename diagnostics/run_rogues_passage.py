#!/usr/bin/env python3
"""What Rogue's Passage's activation is worth (§0z107).

    python -m diagnostics.run_rogues_passage 15000 > results/rogues_passage_20261005.txt

"{4}, {T}: Target creature can't be blocked this turn." Until §0z107 it
was a colourless land in both lists that run it; `rogues_passage=False`
restores that. Each deck's staged list, both arms on the same seeds
(5000..), one T20 game per seed with T10 read off it (§0z93). ON minus OFF.

`tivit_combat_triggers` is the commander's "deals combat damage to a player"
half -- the thing §0z91 made the Passage matter for.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

DECKS_HERE = ("karlov", "tivit")
KEYS = ("won", "damage", "passage_activations", "combat_damage",
        "tivit_combat_triggers")
CHUNKS = 4


def job(task):
    deck, on, lo, hi = task
    cards, cmd = build_pending(deck)
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               rogues_passage=on)
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
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (d, on, _lo, _hi), r in zip(tasks, res):
        cols.setdefault((d, on), []).extend(r)
    print(f"Rogue's Passage's activation (§0z107). N={n:,} paired, seeds "
          "5000.., staged lists. ON minus OFF; * = CI excludes zero.\n")
    names = ("won T10",) + tuple(f"{k} T20" for k in KEYS)
    for d in DECKS_HERE:
        a = np.array(cols[(d, False)]); b = np.array(cols[(d, True)])
        print(f"{d}  (off: won T20 {a[:, 1].mean():.4f}; on: "
              f"{b[:, 3].mean():.3f} activations/game)")
        for i, name in enumerate(names):
            m, h = ci(b[:, i] - a[:, i])
            print(f"    {name:<30}{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ''}")
        print()


if __name__ == "__main__":
    main()
