#!/usr/bin/env python3
"""Items 6 and 7: eight cards whose text the engine now plays (§0z84,
§0z85), measured.

    python -m diagnostics.run_floors_batch2 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_floors_batch2 --report OUTDIR

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Each `*_no*` arm sets ONE
knob to its old value; `*_old` sets all of that deck's.

  R_def / R_nohart / R_nofam / R_nowhip / R_noreanim / R_noshig / R_old
        rendmaw: hart_fetch, familiar_text, whip_text (lifelink and
        reanimation), whip_reanimate (reanimation only), shigeki_text
  S_def / S_noherald / S_noshep / S_noemissary / S_old
        shilgengar: herald_text, shepherd_text, emissary_type="none"
  K_def / K_nolurrus    karlov: lurrus_recast
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "cards_drawn", "hart_sacrifices", "familiar_draws",
       "whip_returns", "lifelinked", "shigeki_digs", "shigeki_lands",
       "herald_counters", "shepherd_persists", "shepherd_returns",
       "emissary_prevented_turns", "lurrus_casts")
R_OLD = {"hart_fetch": False, "familiar_text": False, "whip_text": False,
         "shigeki_text": False}
S_OLD = {"herald_text": False, "shepherd_text": False, "emissary_type": "none"}
ARMS = {
    "R_def": ("rendmaw", {}),
    "R_nohart": ("rendmaw", {"hart_fetch": False}),
    "R_nofam": ("rendmaw", {"familiar_text": False}),
    "R_nowhip": ("rendmaw", {"whip_text": False}),
    "R_noreanim": ("rendmaw", {"whip_reanimate": False}),
    "R_noshig": ("rendmaw", {"shigeki_text": False}),
    "R_old": ("rendmaw", R_OLD),
    "S_def": ("shilgengar", {}),
    "S_noherald": ("shilgengar", {"herald_text": False}),
    "S_noshep": ("shilgengar", {"shepherd_text": False}),
    "S_noemissary": ("shilgengar", {"emissary_type": "none"}),
    "S_old": ("shilgengar", S_OLD),
    "K_def": ("karlov", {}),
    "K_nolurrus": ("karlov", {"lurrus_recast": False}),
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

    def means(a, keys):
        print(f"  {a:<11} T20 a game: " + ", ".join(
            f"{k} {col(outdir, a, 20, k).mean():.3f}" for k in keys))

    print("WIN RATE, new default minus the knob's old value (paired, 95% CI)")
    row("rendmaw: Burnished Hart", "R_def", "R_nohart")
    row("rendmaw: Filigree Familiar", "R_def", "R_nofam")
    row("rendmaw: Whip of Erebos (all)", "R_def", "R_nowhip")
    row("rendmaw: Whip's reanimation alone", "R_def", "R_noreanim")
    row("rendmaw: Shigeki", "R_def", "R_noshig")
    row("rendmaw: all four", "R_def", "R_old")
    means("R_def", ("hart_sacrifices", "familiar_draws", "whip_returns",
                    "shigeki_digs", "shigeki_lands"))
    row("shilgengar: Herald of War", "S_def", "S_noherald")
    row("shilgengar: Twilight Shepherd", "S_def", "S_noshep")
    row("shilgengar: Serra's Emissary", "S_def", "S_noemissary")
    row("shilgengar: all three", "S_def", "S_old")
    means("S_def", ("herald_counters", "shepherd_persists", "shepherd_returns",
                    "emissary_prevented_turns"))
    row("karlov: Lurrus", "K_def", "K_nolurrus")
    means("K_def", ("lurrus_casts",))


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
