#!/usr/bin/env python3
"""Rendmaw's sacrifice outlets paying their costs (§0z70) and Time Sieve's
real-artifact fuel (§0z71), measured.

    python -m diagnostics.run_outlets_sieve 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_outlets_sieve --report OUTDIR

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Both changes are knobs,
so no worker patches anything (§0u).

  R_end / R_main / R_free
                        rendmaw: outlets pay, at the end step (the default,
                        §0z73) / pay, inside `activations` before the main
                        phase (what §0z70 first measured, as R_pay) / free
  T_combo / T_cap / T_never
                        tivit, sieve_real_fuel "combo" (default) / "cap" /
                        "never" (every table before §0z71)
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "cards_drawn", "village_rites_cast", "chef_activations",
       "backwoods_activations", "sieve_activations", "sieve_real_fuel",
       "extra_turns")
ARMS = {
    "R_end": ("rendmaw", {}),
    "R_main": ("rendmaw", {"sac_outlets_timing": "main"}),
    "R_free": ("rendmaw", {"sac_outlets_pay": False}),
    "T_combo": ("tivit", {}),
    "T_cap": ("tivit", {"sieve_real_fuel": "cap"}),
    "T_never": ("tivit", {"sieve_real_fuel": "never"}),
}


def job(a):
    arm, turns, lo, hi = a
    deck_name, extra = ARMS[arm]
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    deck, cmd = build_pending(deck_name)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **extra)
    return [[float(R[deck_name].sim(list(deck), cmd, cfg, 5000 + s).get(m, 0)
                   or 0) for m in MET] for s in range(lo, hi)]


def col(outdir, arm, t, m):
    return np.load(os.path.join(outdir, f"{arm}_T{t}.npy"))[:, MET.index(m)]


def report(outdir):
    def row(label, a, b, m="won"):
        cells = []
        for t in (10, 20):
            d = col(outdir, a, t, m) - col(outdir, b, t, m)
            mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            cells.append(f"T{t} {mu:+.4f} ±{ci:.4f}{'*' if abs(mu) > ci else ' '}")
        print(f"  {label:<40}" + "   ".join(cells))

    def means(a, keys):
        return ", ".join(f"{k} {col(outdir, a, 20, k).mean():.3f}" for k in keys)

    print("RENDMAW'S OUTLETS PAY (paired, 95% CI; * = outside)")
    row("won: pay at end step - free", "R_end", "R_free")
    row("won: pay before main - free", "R_main", "R_free")
    row("won: end step - before main", "R_end", "R_main")
    row("cards_drawn: end step - free", "R_end", "R_free", "cards_drawn")
    for a in ("R_end", "R_main", "R_free"):
        print(f"  {a:<8} T20 a game: " + means(a, ("village_rites_cast",
              "chef_activations", "backwoods_activations")))
    print("\nTIME SIEVE'S REAL FUEL")
    row("won: combo - never", "T_combo", "T_never")
    row("won: cap - never", "T_cap", "T_never")
    row("won: combo - cap", "T_combo", "T_cap")
    for a in ("T_never", "T_combo", "T_cap"):
        print(f"  {a:<8} T20 a game: " + means(a, ("sieve_activations",
              "sieve_real_fuel", "extra_turns")))


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
        sys.exit(0)
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
