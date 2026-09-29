#!/usr/bin/env python3
"""The finality-aware ultimate (§0z82) and five floors closed (§0z83), measured.

    python -m diagnostics.run_floors_batch 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_floors_batch --report OUTDIR

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Every change is a knob,
so no worker patches anything (§0u). Each `*_no*` arm switches ONE knob to
its old value; `*_old` switches all of that deck's.

  S_def / S_noaware             shilgengar, finality_aware_ult
  T_def / T_nosaga              tivit, saga_chapters
  L_def / L_nodrc / L_nomonk / L_old
                                lorehold, drc_delirium_pt, pinnacle_monk_etb
  R_def / R_noelder / R_nosolemn / R_nogloom / R_old
                                rendmaw, elder_fetch, solemn_text,
                                gloomshrieker_text
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "cards_drawn", "finality_exiled", "cards_fed",
       "shilgengar_ults", "saga_votes", "votes_cast", "monk_returns",
       "basics_fetched", "elder_sacrifices", "solemn_death_draws",
       "gloomshrieker_returns", "drain_damage")
ARMS = {
    "S_def": ("shilgengar", {}),
    "S_noaware": ("shilgengar", {"finality_aware_ult": False}),
    "T_def": ("tivit", {}),
    "T_nosaga": ("tivit", {"saga_chapters": False}),
    "L_def": ("lorehold", {}),
    "L_nodrc": ("lorehold", {"drc_delirium_pt": False}),
    "L_nomonk": ("lorehold", {"pinnacle_monk_etb": False}),
    "L_old": ("lorehold", {"drc_delirium_pt": False, "pinnacle_monk_etb": False}),
    "R_def": ("rendmaw", {}),
    "R_noelder": ("rendmaw", {"elder_fetch": False}),
    "R_nosolemn": ("rendmaw", {"solemn_text": False}),
    "R_nogloom": ("rendmaw", {"gloomshrieker_text": False}),
    "R_old": ("rendmaw", {"elder_fetch": False, "solemn_text": False,
                          "gloomshrieker_text": False}),
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
        print(f"  {label:<44}" + "   ".join(cells))

    def means(arms, keys):
        for a in arms:
            print(f"  {a:<11} T20 a game: " + ", ".join(
                f"{k} {col(outdir, a, 20, k).mean():.3f}" for k in keys))

    print("WIN RATE, new default minus the knob's old value (paired, 95% CI)")
    row("shilgengar: finality-aware ultimate", "S_def", "S_noaware")
    means(("S_def", "S_noaware"), ("cards_fed", "shilgengar_ults", "finality_exiled"))
    row("tivit: saga chapters", "T_def", "T_nosaga")
    means(("T_def", "T_nosaga"), ("saga_votes", "votes_cast"))
    row("lorehold: Channeler's +2/+2", "L_def", "L_nodrc")
    row("lorehold: Pinnacle Monk's ETB", "L_def", "L_nomonk")
    row("lorehold: both", "L_def", "L_old")
    means(("L_def",), ("monk_returns",))
    row("rendmaw: Sakura-Tribe Elder", "R_def", "R_noelder")
    row("rendmaw: Solemn Simulacrum", "R_def", "R_nosolemn")
    row("rendmaw: Gloomshrieker", "R_def", "R_nogloom")
    row("rendmaw: all three", "R_def", "R_old")
    means(("R_def", "R_old"), ("basics_fetched", "elder_sacrifices",
                               "solemn_death_draws", "gloomshrieker_returns",
                               "drain_damage"))


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
