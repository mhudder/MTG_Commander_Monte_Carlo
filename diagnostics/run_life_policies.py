#!/usr/bin/env python3
"""What the changes of §0z97 are worth: the crown no longer ends the pod's
chip round, and two of trostani's life floors move on the owner's call.

    python -m diagnostics.run_life_policies 15000 OUTDIR
    python -m diagnostics.run_life_policies --report OUTDIR

N paired games per arm at T10 and T20, seeds 5000.., every arm on the same
seeds. T10 is read off the T20 game (`snapshot_rounds`, §0z93), which is the
same game by construction.

TROSTANI, the staged list. `old` is the engine before this change. Each
other arm moves one thing from it, or a cap on top of the owner's floor:
  lib20        Sylvan Library keeps a card down to 20 life, not 25
  procNN       Processor floor 12 (not 20), paying at most NN (99 = all of it
               above the floor), Library at 20 -- the cap the owner left open
               is the one number swept here

THE CROWN, every deck. No staged list holds a card that grants the monarch,
so the fix cannot move a table; it is measured where it bites, with the
crown granted on round 5 (`monarch_start_turn`, §0z39), fixed against the old
`break`.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

MET = ("won", "damage", "final_life", "processor_life_paid",
       "processor_tokens", "library_kept", "library_life_paid",
       "monarch_lost", "monarch_draws")
OLD = {"processor_life": 8, "processor_floor": 20, "library_life_floor": 25,
       "crown_loss_ends_chip": True}
NEW_LIB = dict(OLD, library_life_floor=20)
CAPS = (8, 12, 16, 24, 99)
ARMS = {("trostani", "old"): OLD, ("trostani", "lib20"): NEW_LIB}
for cap in CAPS:
    ARMS[("trostani", f"proc{cap}")] = dict(NEW_LIB, processor_floor=12,
                                            processor_life=cap)
for d in DECKS:
    ARMS[(d, "crown_old")] = {"monarch_start_turn": 5,
                              "crown_loss_ends_chip": True}
    ARMS[(d, "crown_fix")] = {"monarch_start_turn": 5,
                              "crown_loss_ends_chip": False}
LISTS = {d: build_pending(d) for d in DECKS}


def job(a):
    deck, arm, lo, hi = a
    cards, cmd = LISTS[deck]
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               **ARMS[(deck, arm)])
    sim = DECKS[deck].sim
    rows10, rows20 = [], []
    for s in range(lo, hi):
        out = sim(list(cards), cmd, cfg, 5000 + s)
        rows20.append([float(out.get(m, 0) or 0) for m in MET])
        t10 = out["at_rounds"][10]
        rows10.append([float(t10.get(m, 0) or 0) for m in MET])
    return rows10, rows20


def load(outdir, deck, arm, t, m="won"):
    a = np.load(os.path.join(outdir, f"{deck}_{arm}_T{t}.npy"))
    return a[:, MET.index(m)]


def cell(outdir, deck, arm, base, t):
    d = load(outdir, deck, arm, t) - load(outdir, deck, base, t)
    ci = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
    return f"T{t} {d.mean():+.4f} ±{ci:.4f}{'*' if abs(d.mean()) > ci else ' '}"


def report(outdir):
    print("TROSTANI -- against `old` (Processor 8 above 20, Library 25)")
    for (deck, arm) in ARMS:
        if deck != "trostani" or arm == "old" or arm.startswith("crown"):
            continue
        mech = "  ".join(
            f"{m} {load(outdir, deck, arm, 20, m).mean():.2f}"
            for m in ("processor_life_paid", "processor_tokens",
                      "library_kept"))
        print(f"  {arm:<8} {cell(outdir, deck, arm, 'old', 10)}   "
              f"{cell(outdir, deck, arm, 'old', 20)}   {mech}")
    print("  old      " + "  ".join(
        f"{m} {load(outdir, 'trostani', 'old', 20, m).mean():.2f}"
        for m in ("won", "processor_life_paid", "processor_tokens",
                  "library_kept")))
    print("\n  caps against each other, paired (the Library at 20 in both):")
    for cap in CAPS:
        if cap == 8:
            continue
        print(f"  proc{cap:<3}- proc8   "
              f"{cell(outdir, 'trostani', f'proc{cap}', 'proc8', 10)}   "
              f"{cell(outdir, 'trostani', f'proc{cap}', 'proc8', 20)}")
    print("\nTHE CROWN -- fixed against the old `break`, crown on round 5")
    for deck in DECKS:
        lost = load(outdir, deck, "crown_fix", 20, "monarch_lost").mean()
        dmg = (load(outdir, deck, "crown_fix", 20, "final_life")
               - load(outdir, deck, "crown_old", 20, "final_life")).mean()
        print(f"  {deck:<11}{cell(outdir, deck, 'crown_fix', 'crown_old', 10)}"
              f"   {cell(outdir, deck, 'crown_fix', 'crown_old', 20)}"
              f"   crowns lost {lost:.3f}   final_life {dmg:+.2f}")


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
        sys.exit(0)
    n, outdir = int(sys.argv[1]), sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    ch = 4
    tasks = [(d, a, k * n // ch, (k + 1) * n // ch)
             for (d, a) in ARMS for k in range(ch)]
    with Pool(4) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for (d, a, _, _), (r10, r20) in zip(tasks, res):
        cols.setdefault((d, a, 10), []).extend(r10)
        cols.setdefault((d, a, 20), []).extend(r20)
    for (d, a, t), rows in cols.items():
        np.save(os.path.join(outdir, f"{d}_{a}_T{t}.npy"),
                np.array(rows, float))
    print("saved", len(cols), "columns to", outdir)
