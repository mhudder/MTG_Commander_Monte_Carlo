#!/usr/bin/env python3
"""What §0z115's land rules are worth to each deck, by group.

    python -m diagnostics.run_land_fidelity 15000 results/land_fidelity_20261006.json
    python -m diagnostics.run_land_fidelity --report results/land_fidelity_20261006.json

Every rule §0z115 added has a switch; each arm turns one GROUP of them off
and is paired against the new engine (all on), on the staged lists, the
tables' seeds (5000..) and N, one T20 game per seed with T10 read off it
(§0z93). ARM MINUS BASELINE, so a negative number is what the group is
worth to the deck in the direction it moved:

  all off       every switch below: the pre-§0z115 engine, save one data
                fix that has no switch (Nykthos is now a {C} land, azusa)
  G1 off        the lands the model got WRONG: Temple of the False God and
                Tainted Field (`land_only_if`), Nykthos's devotion,
                Eldrazi Temple, Vault of the Archangel's cost (`vault_paid`
                False is karlov's old FREE lifelink -- and for shilgengar,
                which never modelled the Vault, it is a free Vault, not
                the old engine)
  G2 off        life and entry: enters-tapped conditions and the shocks'
                life, painland and horizon-land life, fetches, karoo bounce
  G3 off        the utility lands' abilities: Mikokoro and Geier Reach,
                Castle Locthwain, Castle Ardenvale, High Market and
                Phyrexian Tower, Petrified Field, Crystal Vein
  shock needed  NOT a group: the shocklands' policy, `shock_pay="needed"`
                against the default "floor" -- the pilot question the
                shocks' new cost makes live (CLAUDE.md, §0z42's lesson)
"""
import json
import sys
import time
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

HORIZONS = (10, 20)
DECKS = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
G1 = {"land_only_if": False, "nykthos_devotion": False,
      "eldrazi_temple": False, "vault_paid": False}
G2 = {"land_etb_rules": False, "painland_life": False, "land_fetch": False,
      "karoo_bounce": False}
G3 = {"draw_lands": False, "locthwain": False, "castle_ardenvale": False,
      "high_market": False, "land_outlets": False, "petrified_field": False,
      "crystal_vein": False}
ARMS = {"all off": {**G1, **G2, **G3}, "G1 off": G1, "G2 off": G2,
        "G3 off": G3, "shock needed": {"shock_pay": "needed"}}
COUNTERS = ("shock_life", "painland_life", "fetch_life", "karoo_bounces",
            "fetches_cracked", "lands_entered_tapped_by_rule",
            "archangel_vault_activations", "nykthos_activations",
            "crystal_vein_sacs", "petrified_returns", "locthwain_draws",
            "high_market_sacs", "land_outlet_sacs", "ardenvale_tokens",
            "draw_land_activations", "draw_land_windows",
            "life_lost_to_own_cards")


def job(task):
    deck_name, arm, lo, hi = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd = build_pending(deck_name)
    over = ARMS[arm] if arm else {}
    top = max(HORIZONS)
    rest = tuple(t for t in HORIZONS if t != top)
    cfg = dict(DEFAULT_CFG, turns=top, watch=frozenset(),
               snapshot_rounds=rest, **over)
    rows = [run.sim(list(deck), cmd, cfg, 5000 + i) for i in range(lo, hi)]
    out = {top: {m: [float(r[m]) for r in rows] for m in run.metrics}}
    for t in rest:
        out[t] = {m: [float(r["at_rounds"][t][m]) for r in rows]
                  for m in run.metrics}
    out["counters"] = {k: float(sum(float(r.get(k, 0) or 0) for r in rows))
                       for k in COUNTERS}
    return task, out


def measure(n, out_path, procs=4):
    parts = AB._chunks(n, procs)
    tasks = [(d, a, lo, hi) for d in DECKS for a in [None] + list(ARMS)
             for lo, hi in parts]
    got, t0 = {}, time.time()
    with Pool(procs) as pool:
        for i, (task, res) in enumerate(
                pool.imap_unordered(job, tasks, chunksize=1), 1):
            got[task] = res
            if i % 8 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)}  {time.time() - t0:.0f}s",
                      flush=True)
    out = {"n": n, "decks": {}}
    for d in DECKS:
        run = AB.Run(d, 1, HORIZONS)

        def col(arm, t, m):
            return np.concatenate([np.array(got[(d, arm, lo, hi)][t][m])
                                   for lo, hi in parts])

        def counters(arm):
            return {k: sum(got[(d, arm, lo, hi)]["counters"][k]
                           for lo, hi in parts) / n for k in COUNTERS}
        res = {"baseline_counters": counters(None), "arms": {}}
        for arm in ARMS:
            cells = {}
            for t in HORIZONS:
                for m in run.metrics:
                    x = col(arm, t, m) - col(None, t, m)
                    cells[f"{m}{t}"] = [float(x.mean()), float(
                        1.96 * x.std(ddof=1) / np.sqrt(n))]
            res["arms"][arm] = {"cells": cells, "counters": counters(arm)}
        out["decks"][d] = res
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("saved", out_path)


def report(path):
    d = json.load(open(path))
    print(f"LAND FIDELITY (§0z115), N={d['n']:,} paired, staged lists, seeds "
          f"5000... Each arm turns a group of the new rules OFF; the row is "
          f"ARM MINUS THE NEW ENGINE (* = CI excludes zero).\n")
    for deck, res in d["decks"].items():
        b = res["baseline_counters"]
        print(f"{deck.upper()}   per game, new engine: " + "  ".join(
            f"{k} {v:.2f}" for k, v in b.items() if v))
        for arm, row in res["arms"].items():
            cells = []
            for key in ("won10", "won20", "damage20"):
                m, ci = row["cells"][key]
                cells.append(f"{m:+.4f} ±{ci:.4f}{'*' if abs(m) > ci else ' '}")
            print(f"  {arm:<14}{cells[0]:>18}{cells[1]:>18}{cells[2]:>18}")
        print()


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        measure(int(sys.argv[1]), sys.argv[2])
