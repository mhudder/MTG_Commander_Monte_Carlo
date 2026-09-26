#!/usr/bin/env python3
"""Treasures and Pitiless Plunderer (§0z64), commander damage (§0z65), measured.

    python -m diagnostics.run_treasures_cmdr 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_treasures_cmdr --report OUTDIR

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Old behaviour is
restored inside each worker, never in the parent (§0u) -- here it is a knob,
`commander_damage=False`, so there is nothing to patch.

  <deck> / <deck>_off   rule on (the default) / off, for the five decks
                        whose commander attacks (azusa's is a 0/3 and was
                        bit-identical in check_unchanged_decks)
  RP / RK               rendmaw, Pygmy Kavu's slot holding Pitiless
                        Plunderer / a blank -- the candidate row, on
                        candidates.py's victim slot
  R_noaltar / RP_noaltar
                        Ashnod's Altar blanked, without and with the
                        Plunderer: the proposal asked whether the Altar is
                        a bad card or an unfuelled one
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "commander_damage_kills", "opponents_killed",
       "treasures_made", "treasures_spent", "altar_sacrifices")
OFF = {"commander_damage": False}
ARMS = {
    "rendmaw": ("rendmaw", {}, ()),
    "rendmaw_off": ("rendmaw", OFF, ()),
    "lorehold": ("lorehold", {}, ()),
    "lorehold_off": ("lorehold", OFF, ()),
    "karlov": ("karlov", {}, ()),
    "karlov_off": ("karlov", OFF, ()),
    "tivit": ("tivit", {}, ()),
    "tivit_off": ("tivit", OFF, ()),
    "shilgengar": ("shilgengar", {}, ()),
    "shilgengar_off": ("shilgengar", OFF, ()),
    "RP": ("rendmaw", {}, ("plunderer",)),
    "RK": ("rendmaw", {}, ("kavu_blank",)),
    "R_noaltar": ("rendmaw", {}, ("altar_blank",)),
    "RP_noaltar": ("rendmaw", {}, ("plunderer", "altar_blank")),
}


def job(a):
    arm, turns, lo, hi = a
    deck_name, extra, mods = ARMS[arm]
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG, repl_priority
    from edhmc.pending import build_pending
    from edhmc.decks.rendmaw_v12 import PITILESS_PLUNDERER
    from tools.ablation import blank_like
    deck, cmd = build_pending(deck_name)
    deck = list(deck)
    rp = repl_priority(deck)

    def slot(name):
        return next(i for i, c in enumerate(deck) if c.name == name)
    if "plunderer" in mods:
        deck[slot("Pygmy Kavu")] = PITILESS_PLUNDERER
    if "kavu_blank" in mods:
        i = slot("Pygmy Kavu")
        deck[i] = blank_like(deck[i], rp)
    if "altar_blank" in mods:
        i = slot("Ashnod's Altar")
        deck[i] = blank_like(deck[i], rp)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **extra)
    return [[float(R[deck_name].sim(deck, cmd, cfg, 5000 + s).get(m, 0))
             for m in MET] for s in range(lo, hi)]


def paired(outdir, a, b, t, m="won"):
    x = np.load(os.path.join(outdir, f"{a}_T{t}.npy"))[:, MET.index(m)]
    y = np.load(os.path.join(outdir, f"{b}_T{t}.npy"))[:, MET.index(m)]
    d = x - y
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def report(outdir):
    def row(label, a, b, m="won"):
        cells = []
        for t in (10, 20):
            mu, ci = paired(outdir, a, b, t, m)
            sig = "*" if abs(mu) > ci else " "
            cells.append(f"T{t} {mu:+.4f} ±{ci:.4f}{sig}")
        print(f"  {label:<44}" + "   ".join(cells))

    def mean(a, t, m):
        return np.load(os.path.join(outdir, f"{a}_T{t}.npy"))[:, MET.index(m)].mean()

    print("COMMANDER DAMAGE, rule on - rule off (paired, 95% CI; * = outside)")
    for d in ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar"):
        row(f"{d}: won", d, f"{d}_off")
        row(f"{d}: opponents_killed", d, f"{d}_off", "opponents_killed")
        print(f"  {'':<44}commander_damage_kills a game: "
              f"T10 {mean(d, 10, 'commander_damage_kills'):.4f}   "
              f"T20 {mean(d, 20, 'commander_damage_kills'):.4f}")
    print("\nPITILESS PLUNDERER (rendmaw, Pygmy Kavu's slot)")
    row("candidate row: Plunderer - blank", "RP", "RK")
    row("swap: -Pygmy Kavu +Plunderer", "RP", "rendmaw")
    for t in (10, 20):
        print(f"  T{t} treasures made {mean('RP', t, 'treasures_made'):.3f}, "
              f"spent {mean('RP', t, 'treasures_spent'):.3f} a game; "
              f"altar sacrifices {mean('rendmaw', t, 'altar_sacrifices'):.3f} "
              f"-> {mean('RP', t, 'altar_sacrifices'):.3f}")
    print("\nASHNOD'S ALTAR, row = with - blanked")
    row("Altar row, no Plunderer", "rendmaw", "R_noaltar")
    row("Altar row, Plunderer in", "RP", "RP_noaltar")


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
