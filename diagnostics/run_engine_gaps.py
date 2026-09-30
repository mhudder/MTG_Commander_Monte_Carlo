#!/usr/bin/env python3
"""What the three engine gaps of §0z90-§0z92 were worth.

    python -m diagnostics.run_engine_gaps 15000 OUTDIR
    python -m diagnostics.run_engine_gaps --report OUTDIR

Each deck's STAGED list, N paired games at T10 and T20, seeds 5000.., every
arm on the same seeds. The OFF arm of each deck is the engine before this
change (all four knobs off reproduces HEAD bit for bit); each other arm
turns ONE thing on against it, so each row is that piece alone.

  karlov   exquisite_general (every opponent's life loss gains you that
           much) and exquisite_drain_loop (Blood + a "each opponent loses 1"
           card is the infinite loop it is), apart and together
  tivit    tivit_trigger_connects (the trigger needs Tivit to connect)
  rendmaw  trample, and `blocker_toughness` 1 / 2 / 3 -- a judgement about
  azusa    the pod's bodies, said out loud by sweeping it

Every engine module is imported in the parent before the pool forks, so the
files can be edited while this runs.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

MET = ("won", "damage", "exquisite_gains", "drain_loop_wins",
       "tivit_combat_triggers", "lifegain_triggers", "turns_played")
OFF = {"exquisite_general": False, "exquisite_drain_loop": False,
       "tivit_trigger_connects": False, "trample": False}
ARMS = {
    "karlov": {"off": OFF,
               "general": dict(OFF, exquisite_general=True),
               "loop": dict(OFF, exquisite_drain_loop=True),
               "both": dict(OFF, exquisite_general=True,
                            exquisite_drain_loop=True)},
    "tivit": {"off": OFF, "connects": dict(OFF, tivit_trigger_connects=True)},
    "rendmaw": {"off": OFF,
                "t1": dict(OFF, trample=True, blocker_toughness=1),
                "t2": dict(OFF, trample=True),
                "t3": dict(OFF, trample=True, blocker_toughness=3)},
    "azusa": {"off": OFF,
              "t1": dict(OFF, trample=True, blocker_toughness=1),
              "t2": dict(OFF, trample=True),
              "t3": dict(OFF, trample=True, blocker_toughness=3)},
}
LISTS = {d: build_pending(d) for d in ARMS}


def job(a):
    deck, arm, turns, lo, hi = a
    cards, cmd = LISTS[deck]
    cfg = dict(DEFAULT_CFG, turns=turns, **ARMS[deck][arm])
    sim = DECKS[deck].sim
    return [[float(sim(list(cards), cmd, cfg, 5000 + s).get(m, 0) or 0)
             for m in MET] for s in range(lo, hi)]


def load(outdir, deck, arm, t, m="won"):
    return np.load(os.path.join(outdir, f"{deck}_{arm}_T{t}.npy"))[:, MET.index(m)]


def report(outdir):
    for deck, arms in ARMS.items():
        print(deck.upper())
        for arm in arms:
            if arm == "off":
                continue
            cells = []
            for t in (10, 20):
                d = load(outdir, deck, arm, t) - load(outdir, deck, "off", t)
                ci = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
                cells.append(f"T{t} {d.mean():+.4f} ±{ci:.4f}"
                             f"{'*' if abs(d.mean()) > ci else ' '}")
            mech = "  ".join(f"{m} {load(outdir, deck, arm, 20, m).mean():.3f}"
                             for m in MET[2:5]
                             if load(outdir, deck, arm, 20, m).any())
            print(f"  {arm:<9}" + "   ".join(cells) + f"   {mech}")
        base = "  ".join(f"{m} {load(outdir, deck, 'off', 20, m).mean():.3f}"
                         for m in ("won", "damage"))
        print(f"  (off, T20: {base})\n")


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
        sys.exit(0)
    n, outdir = int(sys.argv[1]), sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    ch = 4
    tasks = [(d, a, t, k * n // ch, (k + 1) * n // ch)
             for d, arms in ARMS.items() for a in arms for t in (10, 20)
             for k in range(ch)]
    with Pool(4) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (d, a, t, _, _), r in zip(tasks, res):
        cols.setdefault((d, a, t), []).extend(r)
    for (d, a, t), rows in cols.items():
        np.save(os.path.join(outdir, f"{d}_{a}_T{t}.npy"), np.array(rows, float))
    print("saved", len(cols), "columns to", outdir)
