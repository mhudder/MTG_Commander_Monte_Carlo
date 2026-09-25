#!/usr/bin/env python3
"""The 2026-09-25 second batch of text fixes, measured (§0z54-§0z58).

    python -m diagnostics.run_batch_0z54 15000 OUTDIR [ARM ...]

Every arm runs N games at T10 and T20 on seeds 5000.., `build_pending()`,
and saves per-seed metric columns to OUTDIR/<arm>_T<h>.npy, so any two arms
-- or the same arm run from a worktree at another commit -- pair on the seed.
Old behaviour is restored per worker, never in the parent (§0u):

  L            lorehold as it is
  L_oldappr    Approach of the Second Sun as it was: no return, any two casts win
  L_noappr     Approach blanked (its row)       L_noarch  The Dawning Archaic blanked
  K            karlov as it is
  K_oldnecro   Necropotence renamed so no rule sees it, and `draw2` again
  K_nonecro    Necropotence blanked             K_floor10 / K_floor30 / K_hand5
  K_oldoffer   Benevolent Offering as a flat 4 life
  K_nooffer    Benevolent Offering blanked
  R            rendmaw as it is (doll_policy "nest", doll_sac_at 3)
  R_attack     doll_policy "attack" -- the Doll's old behaviour, in effect
  R_sac2 / R_sac4 / R_sac5                      R_nodoll  Twitching Doll blanked
"""
import dataclasses
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "cards_drawn", "approach_wins", "archaic_casts",
       "necro_cards", "offering_spirits", "doll_sacrifices", "doll_spiders",
       "final_life", "mv_cheated")

ARMS = {
    "L": {"deck": "lorehold"},
    "L_oldappr": {"deck": "lorehold", "old_approach": True},
    "L_noappr": {"deck": "lorehold", "blank": "Approach of the Second Sun"},
    "L_noarch": {"deck": "lorehold", "blank": "The Dawning Archaic"},
    "K": {"deck": "karlov"},
    "K_oldnecro": {"deck": "karlov", "old_necro": True},
    "K_nonecro": {"deck": "karlov", "blank": "Necropotence"},
    "K_floor10": {"deck": "karlov", "cfg": {"necro_life_floor": 10}},
    "K_floor30": {"deck": "karlov", "cfg": {"necro_life_floor": 30}},
    "K_hand5": {"deck": "karlov", "cfg": {"necro_hand_target": 5}},
    "K_oldoffer": {"deck": "karlov", "old_offer": True},
    "K_nooffer": {"deck": "karlov", "blank": "Benevolent Offering"},
    "R": {"deck": "rendmaw"},
    "R_attack": {"deck": "rendmaw", "cfg": {"doll_policy": "attack"}},
    "R_sac2": {"deck": "rendmaw", "cfg": {"doll_sac_at": 2}},
    "R_sac4": {"deck": "rendmaw", "cfg": {"doll_sac_at": 4}},
    "R_sac5": {"deck": "rendmaw", "cfg": {"doll_sac_at": 5}},
    "R_nodoll": {"deck": "rendmaw", "blank": "Twitching Doll"},
}


def build(spec):
    from edhmc.pending import build_pending
    from edhmc.experiment import repl_priority
    from tools.ablation import blank_like
    deck, cmd = build_pending(spec["deck"])
    deck = list(deck)
    if "blank" in spec:
        i = next(i for i, c in enumerate(deck) if c.name == spec["blank"])
        deck[i] = blank_like(deck[i], repl_priority(deck))
    if spec.get("old_necro"):
        deck = [dataclasses.replace(c, name="Necropotence (as draw2)",
                                    script="draw2")
                if c.name == "Necropotence" else c for c in deck]
    if spec.get("old_offer"):
        deck = [dataclasses.replace(c, script=None, lifegain=4.0)
                if c.name == "Benevolent Offering" else c for c in deck]
    return deck, cmd


def job(a):
    arm, turns, lo, hi = a
    spec = ARMS[arm]
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    if spec.get("old_approach"):
        import edhmc.lorehold as L

        def old(g, card, is_copy, was_cast, from_hand):
            if is_copy:
                return
            g.m["approach_casts"] += 1
            if g.m["approach_casts"] >= 2:
                g.result = "win"
        L.approach_resolves = old
    deck, cmd = build(spec)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **spec.get("cfg", {}))
    out = []
    for s in range(lo, hi):
        r = R[spec["deck"]].sim(deck, cmd, cfg, 5000 + s)
        out.append([float(r.get(m, 0)) for m in MET])
    return out


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
