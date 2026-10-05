#!/usr/bin/env python3
"""Does Bramble Sovereign's priority move still pay WITH the other four? (§0z111)

    python -m diagnostics.run_trostani_bramble 15000 > results/trostani_bramble_20261005.txt

§0z110 adopted five priority moves on a joint run. Trostani's rebuilt table
then read Bramble Sovereign's own row at -0.0095 +-0.0035 at T10 (it was
+0.0027 before): the deck does better at T10 WITHOUT the card it just
promoted. One mechanism fits -- at 10.5 Bramble outranks the other four
raised engines, Seedborn Muse (10) the largest -- so this asks the paired
question directly. Arms on the adopted list: Bramble at 10.5 (as adopted)
and Bramble back at 8.5, everything else as adopted. Seeds 40000.., a block
neither the sweep (1234.., 6234.., 21234..) nor the table (5000..) used,
since the question was chosen by looking at the table.
"""
import dataclasses
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

SEED0 = 40000
CHUNKS = 4
KEYS = ("won", "damage", "tokens_made", "populates")


def deck_for(prio):
    cards, cmd = build_pending("trostani")
    out = [dataclasses.replace(c, priority=prio)
           if c.name == "Bramble Sovereign" else c for c in cards]
    return out, cmd


def job(task):
    prio, lo, hi = task
    cards, cmd = deck_for(prio)
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,))
    rows = []
    for s in range(lo, hi):
        r = DECKS["trostani"].sim(list(cards), cmd, cfg, SEED0 + s)
        rows.append([float(r["at_rounds"][10]["won"])]
                    + [float(r.get(k, 0) or 0) for k in KEYS])
    return rows


def ci(d):
    d = np.asarray(d, float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    n = int(sys.argv[1])
    tasks = [(p, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for p in (10.5, 8.5) for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (prio, _lo, _hi), r in zip(tasks, res):
        cols.setdefault(prio, []).extend(r)
    a, b = np.array(cols[10.5]), np.array(cols[8.5])
    print(f"trostani, adopted list, Bramble Sovereign at 10.5 minus at 8.5. "
          f"N={n:,} paired, seeds {SEED0}.. (§0z111). * = CI excludes zero.\n")
    for i, name in enumerate(("won T10",) + tuple(f"{k} T20" for k in KEYS)):
        m, h = ci(a[:, i] - b[:, i])
        print(f"    {name:<18}{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ''}")


if __name__ == "__main__":
    main()
