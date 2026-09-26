#!/usr/bin/env python3
"""Menace (§0z61) and the pod's reaction to a known win (§0z62), measured.

    python -m diagnostics.run_menace_approach 15000 OUTDIR [ARM ...]

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Old behaviour is
restored inside each worker, never in the parent (§0u):

  R / R_nomenace      rendmaw; `menace_of` always False in the second
  L_off               lorehold with NO reaction: `known_win` can never be set
  L_f0 / L_f05 / L    known_win_focus 0 (the counterspell half only), 0.5,
                      and the default 1.0
  L_noappr            Approach blanked -- the row's other arm at every focus,
                      since without Approach nothing sets `known_win`
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "approach_wins", "approach_returned")
ARMS = {
    "R": ("rendmaw", {}, None),
    "R_nomenace": ("rendmaw", {}, "nomenace"),
    "L_off": ("lorehold", {}, "noreact"),
    "L_f0": ("lorehold", {"known_win_focus": 0.0}, None),
    "L_f05": ("lorehold", {"known_win_focus": 0.5}, None),
    "L": ("lorehold", {}, None),
    "L_noappr": ("lorehold", {}, "blank"),
}


def job(a):
    arm, turns, lo, hi = a
    deck_name, extra, mode = ARMS[arm]
    import edhmc.opponents as OPP
    import edhmc.lorehold as L
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG, repl_priority
    from edhmc.pending import build_pending
    from tools.ablation import blank_like
    if mode == "nomenace":
        OPP.menace_of = lambda g, p: False
    if mode == "noreact":
        L.LoreholdGame.known_win = property(lambda self: None,
                                            lambda self, v: None)
    deck, cmd = build_pending(deck_name)
    deck = list(deck)
    if mode == "blank":
        i = next(i for i, c in enumerate(deck)
                 if c.name == "Approach of the Second Sun")
        deck[i] = blank_like(deck[i], repl_priority(deck))
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **extra)
    return [[float(R[deck_name].sim(deck, cmd, cfg, 5000 + s).get(m, 0))
             for m in MET] for s in range(lo, hi)]


if __name__ == "__main__":
    n, outdir = int(sys.argv[1]), sys.argv[2]
    arms = sys.argv[3:] or list(ARMS)
    os.makedirs(outdir, exist_ok=True)
    CH = 8
    tasks = [(a, t, k * n // CH, (k + 1) * n // CH)
             for a in arms for t in (10, 20) for k in range(CH)]
    with Pool(4, maxtasksperchild=1) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (a, t, _, _), r in zip(tasks, res):
        cols.setdefault((a, t), []).extend(r)
    for (a, t), rows in cols.items():
        np.save(os.path.join(outdir, f"{a}_T{t}.npy"), np.array(rows, float))
    print("saved", len(cols), "columns to", outdir)
