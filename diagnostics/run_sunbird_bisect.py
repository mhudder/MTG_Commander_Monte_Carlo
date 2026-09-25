#!/usr/bin/env python3
"""Where did Sunbird's Invocation's decline happen? (queued 0b-i, §0z59)

Run INSIDE a worktree at the commit to measure, by absolute path, so that
commit's engine is the one imported:

    git worktree add ../edhmc_at <commit>
    (cd ../edhmc_at && python /path/to/diagnostics/run_sunbird_bisect.py \
        30000 /tmp/<commit>.npy 4)

Legs A (lorehold_v16 as printed) and S (-Scroll Rack +Sunbird's Invocation)
at T20, N paired games, seeds 5000.., the cfg `run_lorehold_pair` uses --
so its first commit reproduces the 2026-09-09 figure (+0.0152 +-0.0028), and
it did. Saves per-seed `won` for both legs. SAME SEEDS AT EVERY COMMIT, so
the per-seed S-A differences of two commits pair: a step between commits
has its own interval, not two independent ones. results/sunbird_bisect.txt
is the table over 22 commits.
"""
import os, sys
sys.path.insert(0, os.getcwd())
import numpy as np
from multiprocessing import Pool
N, OUT, PROCS = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
_W = {}
def _init():
    from edhmc.decks import lorehold_v16 as MOD
    from edhmc.lorehold import simulate
    from edhmc.experiment import DEFAULT_CFG, _swap_many
    deck, cmd = MOD.build()
    s_deck = _swap_many(deck, ["Scroll Rack"], [MOD.SUNBIRDS_INVOCATION])
    _W.update(sim=simulate, A=(deck, cmd), S=(s_deck, cmd),
              cfg=dict(DEFAULT_CFG, turns=20,
                       watch=frozenset({"Caldera Pyremaw", "Sunbird's Invocation"})))
def _one(seed):
    a = _W["sim"](*_W["A"], _W["cfg"], seed)["won"]
    s = _W["sim"](*_W["S"], _W["cfg"], seed)["won"]
    return a, s
if __name__ == "__main__":
    with Pool(PROCS, initializer=_init) as p:
        rows = p.map(_one, range(5000, 5000 + N), chunksize=64)
    np.save(OUT, np.array(rows, float))
    a = np.array(rows, float); d = a[:, 1] - a[:, 0]
    print(f"{OUT}: S-A {d.mean():+.4f} +-{1.96*d.std(ddof=1)/np.sqrt(len(d)):.4f}")
