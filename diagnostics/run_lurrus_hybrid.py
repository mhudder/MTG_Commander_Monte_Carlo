#!/usr/bin/env python3
"""Lurrus's hybrid pips, paid and counted (§0z52), paired on karlov.

    python -m diagnostics.run_lurrus_hybrid 15000

"old" restores the flattened {1}{W}{B} and the devotion count that read the
printed cost only (patched inside each worker); "new" is the engine as it is.
"""
import sys, dataclasses, numpy as np
from multiprocessing import Pool
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15000; MET = ("won", "damage", "lifegain_triggers")
def job(a):
    arm, turns, lo, hi = a
    import edhmc.karlov as K
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    deck, cmd = build_pending("karlov")
    if arm == "old":
        K.devotion_white = lambda g: sum(p.card.cost.get("W", 0) for p in g.board)
        deck = [dataclasses.replace(c, alt_costs=()) if c.name.startswith("Lurrus") else c
                for c in deck]
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
    out = {m: [] for m in MET}
    for s in range(lo, hi):
        r = R["karlov"].sim(deck, cmd, cfg, 5000 + s)
        for m in MET: out[m].append(float(r.get(m, 0)))
    return out
if __name__ == "__main__":
    CH = 8; tasks, keys = [], []
    for arm in ("new", "old"):
        for t in (10, 20):
            for k in range(CH):
                tasks.append((arm, t, k*N//CH, (k+1)*N//CH)); keys.append((arm, t))
    with Pool(4, maxtasksperchild=1) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for k, r in zip(keys, res):
        d = cols.setdefault(k, {m: [] for m in MET})
        for m in MET: d[m] += r[m]
    for t in (10, 20):
        s = ""
        for m in MET:
            x = np.array(cols[("new", t)][m]) - np.array(cols[("old", t)][m])
            s += f"  {m} {x.mean():+.4f} +-{1.96*x.std(ddof=1)/np.sqrt(len(x)):.4f}"
        print(f"Lurrus hybrid + devotion (new - old) T{t}{s}   changed games {np.mean(np.array(cols[('new',t)]['damage'])!=np.array(cols[('old',t)]['damage'])):.4f}")
