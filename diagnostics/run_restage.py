#!/usr/bin/env python3
"""Re-measure every staged swap, and the open head-to-heads, on today's engine.

    python -m diagnostics.run_restage 15000 OUTDIR [ARM ...]

Each arm is `build_pending(deck)` with some slots rewritten, run for N games
at T10 and T20 on seeds 5000..; per-seed columns go to OUTDIR/<arm>_T<h>.npy
so any two arms of one deck pair on the seed. A staged swap is measured IN
CONTEXT: its "before" arm is the staged list with only that swap undone, so
the deck's other staged changes are present on both sides.

  K               karlov as staged (-Soulmender +Conqueror, -Swamp +Citadel)
  K_noConq        ... with the Conqueror swap undone (Soulmender back)
  K_noCit         ... with the Citadel swap undone (Swamp back)
  K_bootsConq     the Conqueror in Swiftfoot Boots' slot instead (Soulmender kept)
  T / T_noProc    tivit as staged / with Anointed Procession undone (Plains back)
  A / A_noKaZar   azusa as staged / with Ka-Zar undone (Perilous Forays back)
  L               lorehold as staged
  L_gold_slot     Goldspan Dragon in Caldera Pyremaw's slot
  L_gold_act      -Blasphemous Act +Goldspan Dragon
  L_gold_grv      -Lightning Greaves +Goldspan Dragon
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage")

# (deck, [(name in the staged list, replacement: ("module", name) | ("lh", CONST))])
ARMS = {
    "K": ("karlov", []),
    "K_noConq": ("karlov", [("Bloodthirsty Conqueror", ("module", "Soulmender"))]),
    "K_noCit": ("karlov", [("Bolas's Citadel", ("module", "Swamp"))]),
    "K_bootsConq": ("karlov", [("Bloodthirsty Conqueror", ("module", "Soulmender")),
                               ("Swiftfoot Boots", ("pending", "Bloodthirsty Conqueror"))]),
    "T": ("tivit", []),
    "T_noProc": ("tivit", [("Anointed Procession", ("module", "Plains"))]),
    "A": ("azusa", []),
    "A_noKaZar": ("azusa", [("Ka-Zar of the Savage Land", ("module", "Perilous Forays"))]),
    "L": ("lorehold", []),
    "L_gold_slot": ("lorehold", [("Caldera Pyremaw", ("lh", "GOLDSPAN_DRAGON"))]),
    "L_gold_act": ("lorehold", [("Blasphemous Act", ("lh", "GOLDSPAN_DRAGON"))]),
    "L_gold_grv": ("lorehold", [("Lightning Greaves", ("lh", "GOLDSPAN_DRAGON"))]),
}


def build(arm):
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS as R
    from edhmc.decks import lorehold_v16 as LM
    deck_name, edits = ARMS[arm]
    staged, cmd = build_pending(deck_name)
    module, _ = R[deck_name].build()
    deck = list(staged)
    for out, (src, name) in edits:
        if src == "module":
            card = next(c for c in module if c.name == name)
        elif src == "pending":
            card = next(c for c in staged if c.name == name)
        else:
            card = getattr(LM, name)
        i = next(i for i, c in enumerate(deck) if c.name == out)   # first copy
        deck[i] = card
    names = [c.name for c in deck if not c.is_land]
    assert len(names) == len(set(names)), f"{arm}: singleton violation"
    return deck_name, deck, cmd


def job(a):
    arm, turns, lo, hi = a
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    deck_name, deck, cmd = build(arm)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
    return [[float(R[deck_name].sim(deck, cmd, cfg, 5000 + s).get(m, 0)) for m in MET]
            for s in range(lo, hi)]


if __name__ == "__main__":
    n, outdir = int(sys.argv[1]), sys.argv[2]
    arms = sys.argv[3:] or list(ARMS)
    for a in arms:
        build(a)                       # fail fast on a bad arm
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
