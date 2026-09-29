#!/usr/bin/env python3
"""Death triggers looking back (§0z76), shilgengar's routed lifegain and
finality counters (§0z75), Goldspan's targeted Treasure and the Treasure
Vault held back (§0z77), measured.

    python -m diagnostics.run_lookback_finality 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_lookback_finality --report OUTDIR

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Every change is a knob,
so no worker patches anything (§0u). The one change with NO knob -- Voldaren
Bloodcaster's name, which had never matched the card -- is in every
shilgengar arm, the "old" one included, so `S_old` is not the old table.

  R_def / R_nolook / R_vnever / R_valways / R_old
        rendmaw: defaults / death_lookback off / vault_hold "never" /
        vault_hold "always" / both off (the engine before this batch)
  K_def / K_nolook          karlov
  A_def / A_nolook          azusa (Titania)
  S_def / S_nolook / S_noroute / S_nofin / S_old
        shilgengar: defaults / look-back off / gain_life_routed off /
        finality_exiles off / all three off
  L_def / L_notarget        lorehold, goldspan_targeted on / off
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "cards_drawn", "drain_damage", "treasures_made",
       "vault_activations", "blood_made", "lifegain_triggers",
       "finality_exiled", "goldspan_target_treasures", "opponents_killed")
OFF = {"death_lookback": False}
ARMS = {
    "R_def": ("rendmaw", {}),
    "R_nolook": ("rendmaw", OFF),
    "R_vnever": ("rendmaw", {"vault_hold": "never"}),
    "R_valways": ("rendmaw", {"vault_hold": "always"}),
    "R_old": ("rendmaw", dict(OFF, vault_hold="never")),
    "K_def": ("karlov", {}),
    "K_nolook": ("karlov", OFF),
    "A_def": ("azusa", {}),
    "A_nolook": ("azusa", OFF),
    "S_def": ("shilgengar", {}),
    "S_nolook": ("shilgengar", OFF),
    "S_noroute": ("shilgengar", {"gain_life_routed": False}),
    "S_nofin": ("shilgengar", {"finality_exiles": False}),
    "S_old": ("shilgengar", dict(OFF, gain_life_routed=False,
                                 finality_exiles=False)),
    "L_def": ("lorehold", {}),
    "L_notarget": ("lorehold", {"goldspan_targeted": False}),
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

    def means(arms, keys):
        for a in arms:
            print(f"  {a:<11} T20 a game: " + ", ".join(
                f"{k} {col(outdir, a, 20, k).mean():.3f}" for k in keys))

    print("DEATH LOOK-BACK (paired, 95% CI; * = outside)")
    for d, keys in (("R", ("drain_damage", "treasures_made")),
                    ("K", ("damage",)), ("A", ("damage",)),
                    ("S", ("cards_drawn", "blood_made"))):
        row(f"won: {d} look-back - live board", f"{d}_def", f"{d}_nolook")
        means((f"{d}_def", f"{d}_nolook"), keys)
    print("\nRENDMAW'S VAULT HOLD")
    row("won: doubler - never", "R_def", "R_vnever")
    row("won: always - never", "R_valways", "R_vnever")
    row("won: doubler - always", "R_def", "R_valways")
    row("won: this batch - before it", "R_def", "R_old")
    means(("R_def", "R_vnever", "R_valways"),
          ("vault_activations", "treasures_made"))
    print("\nSHILGENGAR")
    row("won: routed - direct", "S_def", "S_noroute")
    row("won: finality exiles - dies", "S_def", "S_nofin")
    row("won: this batch - before it", "S_def", "S_old")
    means(("S_def", "S_noroute", "S_nofin", "S_old"),
          ("lifegain_triggers", "finality_exiled", "blood_made"))
    print("\nLOREHOLD'S GOLDSPAN")
    row("won: targeted Treasure - none", "L_def", "L_notarget")
    means(("L_def", "L_notarget"),
          ("goldspan_target_treasures", "treasures_made"))


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
