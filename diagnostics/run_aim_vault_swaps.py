#!/usr/bin/env python3
"""Aiming the commander (§0z67), Treasure Vault (§0z68), the owner's 0.8
known-win focus, and the two stagings the owner approved -- measured.

    python -m diagnostics.run_aim_vault_swaps 15000 OUTDIR [ARM ...]
    python -m diagnostics.run_aim_vault_swaps --report OUTDIR

N games per arm at T10 and T20, seeds 5000.., `build_pending()`; per-seed
columns saved so arms of one deck pair on the seed. Everything old is a knob
here, so no worker patches anything (§0u).

  <deck>_A   commander_aim=off, commander_block_aware=False  (§0z65 as built)
  <deck>_B   aim off, the defender knows 104.3j
  <deck>_C   aim "lethal", aware                            (the new defaults)
  <deck>_D   aim "focus", aware
             for rendmaw, lorehold, karlov, tivit, shilgengar
  R_v0 / R_v2 / R_v6   rendmaw's Vault never cracked / threshold 2 / 6
                       (rendmaw_C is threshold 4)
  L_f10      lorehold at known_win_focus 1.0 (lorehold_C is the owner's 0.8)
  L_gold     lorehold, -Blasphemous Act +Goldspan Dragon, on the C engine
  S_lyra     shilgengar, -Vampiric Rites +Lyra, Archangel of Dawn, on C
  L_gold_B / S_lyra_B   the same two swaps on B (commander not aimed)

THE C AND D ARMS WERE RUN TWICE. The first "lethal" aimed the commander at a
defender who then blocked it (§0z67); the rerun, after the fix, replaces
them and everything paired with them. The A, B and Vault-threshold arms did
not change and were not rerun.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "commander_damage_kills", "opponents_killed",
       "commander_aimed", "vault_activations", "treasures_made")
A = {"commander_aim": "off", "commander_block_aware": False}
B = {"commander_aim": "off", "commander_block_aware": True}
C = {"commander_aim": "lethal", "commander_block_aware": True}
D = {"commander_aim": "focus", "commander_block_aware": True}
DECKS5 = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar")
ARMS = {}
for _d in DECKS5:
    for _k, _cfg in (("A", A), ("B", B), ("C", C), ("D", D)):
        ARMS[f"{_d}_{_k}"] = (_d, _cfg, None)
ARMS.update({
    "R_v0": ("rendmaw", dict(C, vault_min_treasures=999), None),
    "R_v2": ("rendmaw", dict(C, vault_min_treasures=2), None),
    "R_v6": ("rendmaw", dict(C, vault_min_treasures=6), None),
    "L_f10": ("lorehold", dict(C, known_win_focus=1.0), None),
    "L_gold": ("lorehold", C, ("Blasphemous Act", "Goldspan Dragon")),
    "S_lyra": ("shilgengar", C, ("Vampiric Rites",
                                 "Lyra, Archangel of Dawn")),
    # The same swaps with the commander NOT aimed, so whichever default the
    # aim measurement picks has its swap measured on it.
    "L_gold_B": ("lorehold", B, ("Blasphemous Act", "Goldspan Dragon")),
    "S_lyra_B": ("shilgengar", B, ("Vampiric Rites",
                                   "Lyra, Archangel of Dawn")),
})


def job(a):
    arm, turns, lo, hi = a
    deck_name, extra, swap = ARMS[arm]
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import DECKS as CATALOG, build_pending
    deck, cmd = build_pending(deck_name)
    deck = list(deck)
    if swap:
        out, add = swap
        i = next(k for k, c in enumerate(deck) if c.name == out)
        deck[i] = CATALOG[deck_name][1][add]
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **extra)
    return [[float(R[deck_name].sim(deck, cmd, cfg, 5000 + s).get(m, 0) or 0)
             for m in MET] for s in range(lo, hi)]


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

    def mean(a, m, t=20):
        return col(outdir, a, t, m).mean()

    print("COMMANDER: each step against the one before (paired, 95% CI; "
          "* = outside)")
    for d in DECKS5:
        print(f" {d}")
        row("B-A  the defender knows 104.3j", f"{d}_B", f"{d}_A")
        row("C-B  aim lethal", f"{d}_C", f"{d}_B")
        row("D-C  aim focus instead", f"{d}_D", f"{d}_C")
        row("C-A  the new defaults, all told", f"{d}_C", f"{d}_A")
        print(f"  {'':<46}cmdr kills a game T20: A {mean(d + '_A', 'commander_damage_kills'):.3f}"
              f"  B {mean(d + '_B', 'commander_damage_kills'):.3f}"
              f"  C {mean(d + '_C', 'commander_damage_kills'):.3f}"
              f"  D {mean(d + '_D', 'commander_damage_kills'):.3f}")
    print("\nTREASURE VAULT (rendmaw, on C)")
    row("threshold 4 (default) - never", "rendmaw_C", "R_v0")
    row("threshold 2 - never", "R_v2", "R_v0")
    row("threshold 6 - never", "R_v6", "R_v0")
    for a in ("R_v2", "rendmaw_C", "R_v6"):
        print(f"  {a:<12} activations a game T20 {mean(a, 'vault_activations'):.3f}, "
              f"treasures {mean(a, 'treasures_made'):.3f}")
    print("\nKNOWN-WIN FOCUS (lorehold, on C)")
    row("0.8 (owner) - 1.0", "lorehold_C", "L_f10")
    print("\nTHE TWO APPROVED SWAPS, on C")
    row("lorehold -Blasphemous Act +Goldspan", "L_gold", "lorehold_C")
    row("shilgengar -Vampiric Rites +Lyra", "S_lyra", "shilgengar_C")
    if os.path.exists(os.path.join(outdir, "L_gold_B_T10.npy")):
        print("\nTHE SAME SWAPS, commander not aimed (on B)")
        row("lorehold -Blasphemous Act +Goldspan", "L_gold_B", "lorehold_B")
        row("shilgengar -Vampiric Rites +Lyra", "S_lyra_B", "shilgengar_B")


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
