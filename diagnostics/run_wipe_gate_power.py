#!/usr/bin/env python3
"""Should the wipe gate count BODIES, POWER, or what the wipe COSTS? (§0z106)

    python -m diagnostics.run_wipe_gate_power 15000 > results/wipe_gate_power_20261005.txt

`opponents.should_cast_own_wipe` sweeps when the table's creatures
meaningfully outnumber yours -- counted in bodies. Traced over 3,000 karlov
games, its own wipes fired with 2.7 of its creatures against 9.6 of theirs,
and Karlov himself was one of the 2.7 in 82% of them, carrying 11 counters:
by power the pilot was AHEAD (16.7 against ~9.6) and swept anyway. An
opposing creature here is a body of `p["power"]` (0.65-1.35 by archetype),
which is what chip damage multiplies by, so "power" compares like with like.

Three arms per deck, each deck's staged list, same seeds (5000..), one T20
game per seed with T10 read off it (§0z93):
  count   wipe_gate_measure="count" (the gate as it was)
  power   wipe_gate_measure="power"
  cost    wipe_gate_measure="cost" -- power, counting only YOUR creatures
          the sweeper would kill (none for a one-sided wipe, none that is
          indestructible against a destroy). Added after the first run found
          power costing rendmaw (Massacre Wurm, one-sided, held) and
          shilgengar (Avacyn's grant) at T20
  never   wipe_threshold=1e9 -- no optional own wipe is ever cast; what the
          gate is worth at all, as a reference
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

DECKS_HERE = ("karlov", "lorehold", "rendmaw", "tivit", "shilgengar",
              "trostani")
ARMS = {
    "count": dict(wipe_gate_measure="count"),
    "power": dict(wipe_gate_measure="power"),
    "cost": dict(wipe_gate_measure="cost"),
    "never": dict(wipe_threshold=1e9),
}
KEYS = ("won", "damage", "own_wipes_cast")
CHUNKS = 4


def job(task):
    deck, arm, lo, hi = task
    cards, cmd = build_pending(deck)
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), **ARMS[arm])
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
    tasks = [(d, a, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for d in DECKS_HERE for a in ARMS for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (d, a, _lo, _hi), r in zip(tasks, res):
        cols.setdefault((d, a), []).extend(r)
    print(f"The wipe gate: bodies or power (§0z106). N={n:,} paired, seeds "
          "5000.., staged lists. Each arm minus COUNT; * = CI excludes zero.\n")
    names = ("won T10", "won T20", "damage T20", "own wipes / game")
    for d in DECKS_HERE:
        base = np.array(cols[(d, "count")])
        print(f"{d}  (count: won T20 {base[:, 1].mean():.4f}, "
              f"own wipes {base[:, 3].mean():.3f}/game)")
        for arm in ("power", "cost", "never"):
            b = np.array(cols[(d, arm)])
            cells = []
            for i, name in enumerate(names):
                m, h = ci(b[:, i] - base[:, i])
                cells.append(f"{name} {m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ' '}")
            print(f"    {arm:<6}" + "   ".join(cells))
        print()


if __name__ == "__main__":
    main()
