#!/usr/bin/env python3
"""Karlov's counter reserve (§0z155): `karlov_exile_keep` at 0 (the
default), 6 and 12, paired on the staged list, seeds 5000.., T10 from the
T20 game -- `run_oracle_remainder`'s design, so keep=0 reproduces that
runner's "all" arm exactly.

    python -m diagnostics.run_karlov_exile_keep 15000
"""
import sys
from multiprocessing import Pool
import numpy as np
CH = 8
KEEPS = (0, 6, 12)
def job(a):
    keep, lo, hi = a
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    cards, cmd = build_pending("karlov")
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), karlov_exile_keep=keep)
    rows = []
    for s in range(lo, hi):
        out = R["karlov"].sim(list(cards), cmd, cfg, 5000 + s)
        rows.append([float(out["at_rounds"][10].get("won", 0) or 0), float(out.get("won", 0) or 0),
                     float(out.get("karlov_exiles", 0))])
    return rows
if __name__ == "__main__":
    N = int(sys.argv[1])
    tasks = [(k, c * N // CH, (c + 1) * N // CH) for k in KEEPS for c in range(CH)]
    with Pool(4, maxtasksperchild=1) as p:
        res = [r.get(timeout=3600) for r in [p.apply_async(job, (t,)) for t in tasks]]
    cols = {}
    for (k, _, _), r in zip(tasks, res):
        cols.setdefault(k, []).extend(r)
    a = {k: np.array(v) for k, v in cols.items()}
    for k in KEEPS:
        print(f"keep={k:2d}: exiles/game {a[k][:,2].mean():.3f}  won T10 {a[k][:,0].mean():.4f}  T20 {a[k][:,1].mean():.4f}")
    for k in KEEPS[1:]:
        cells = []
        for j in (0, 1):
            d = a[k][:, j] - a[0][:, j]
            mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            cells.append(f"{mu:+.4f} ±{ci:.4f}{'*' if abs(mu) > ci else ' '}")
        print(f"keep={k} minus keep=0:  T10 {cells[0]}   T20 {cells[1]}")
