#!/usr/bin/env python3
"""Why Time Sieve's priority move flipped sign between horizons (queued item
18, §0z44), and what the two §0z86 fixes do to it.

    python -m diagnostics.run_sieve_horizon 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_sieve_horizon --report OUTDIR

§0z44 found Time Sieve 9 -> 11 at −0.0043 ±0.0022 (T10) and +0.0121 ±0.0039
(T20), and GUESSED the cause: extra turns counted against the horizon. The
guess was never tested, and the investigation found a second mechanism the
guess missed -- the pod's kill clock read `g.turn`, which an extra turn
advances, so every extra turn brought each opponent's kill a round closer.

Arms, tivit's staged list, N games at T10 and T20, seeds 5000..:

  P9_old  / P11_old   Sieve at priority 9 / 11, the engine BEFORE §0z86
                      (pod_clock_rounds=False, horizon_counts="turns")
  P9_clk  / P11_clk   the pod clock in rounds, the horizon still in turns
  P9_new  / P11_new   both fixes (the §0z86 defaults)
"""
import dataclasses
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "extra_turns", "extra_turns_taken", "sieve_activations",
       "turns_played", "pod_rounds", "test_card_turn")
OLD = {"pod_clock_rounds": False, "horizon_counts": "turns"}
CLK = {"pod_clock_rounds": True, "horizon_counts": "turns"}
NEW = {}
ARMS = {f"P{p}_{tag}": (p, cfg) for p in (9, 11)
        for tag, cfg in (("old", OLD), ("clk", CLK), ("new", NEW))}


def job(a):
    arm, turns, lo, hi = a
    prio, extra = ARMS[arm]
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    deck, cmd = build_pending("tivit")
    deck = [dataclasses.replace(c, priority=prio) if c.name == "Time Sieve"
            else c for c in deck]
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({"Time Sieve"}),
               **extra)
    return [[float(R["tivit"].sim(list(deck), cmd, cfg, 5000 + s).get(m, 0)
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
        print(f"  {label:<46}" + "   ".join(cells))

    print("TIME SIEVE 9 -> 11 (win rate, paired, 95% CI)")
    row("the old engine (§0z44's flip)", "P11_old", "P9_old")
    row("pod clock in rounds", "P11_clk", "P9_clk")
    row("pod clock AND horizon in rounds (§0z86)", "P11_new", "P9_new")
    print("\nTHE FIXES THEMSELVES, at Sieve's current priority 9")
    row("pod clock in rounds - old", "P9_clk", "P9_old")
    row("horizon in rounds, given the clock", "P9_new", "P9_clk")
    row("both - old", "P9_new", "P9_old")
    print("\nMECHANISM, a game")
    for a in ARMS:
        for t in (10, 20):
            cast = col(outdir, a, t, "test_card_turn")
            cast = cast[cast < 99]
            print(f"  {a:<8} T{t}: extra turns {col(outdir, a, t, 'extra_turns_taken').mean():.3f}"
                  f"  Sieve activations {col(outdir, a, t, 'sieve_activations').mean():.3f}"
                  f"  pod rounds {col(outdir, a, t, 'pod_rounds').mean():.2f}"
                  f"  Sieve cast on turn {cast.mean() if len(cast) else float('nan'):.2f}"
                  f" ({len(cast)} games)")


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
