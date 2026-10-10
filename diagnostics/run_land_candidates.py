#!/usr/bin/env python3
"""Land CANDIDATES against the basic they would replace (§0z113).

    python -m diagnostics.run_land_candidates 15000 results/land_candidates_20261006.json
    python -m diagnostics.run_land_candidates --report results/land_candidates_20261006.json

The land ablation (§0z112, `run_land_ablation`) asked what the lands IN each
list are worth over a basic. This asks the same question of lands NOT in the
lists: each candidate replaces one copy of the basic `run_land_ablation.
basic_for` would pick for it -- the basic of the colour it makes that the
deck's spells want most, or the deck's most common basic for a land that
makes none of its colours (every colourless land here). Same harness as the
ablation: the staged list, the tables' seeds (5000..) and N, one T20 game per
seed with T10 read off it (§0z93).

THE NUMBER IS candidate minus basic, paired. It is a CANDIDATE ROW in the
add-card sense: value over the basic it displaced, which is exactly the swap
a land candidate proposes -- a land is cut for a land.

Each arm also records the card's MECHANISM COUNTER over the same games (the
add-card rule: a counter that fires zero times is unmistakable where a
win rate 0.03 too low is not), and every deck carries a NOOP arm -- a basic
replaced by a fresh copy of itself -- which must change nothing.

KNOB ARMS. Two candidates rest on a policy threshold, said out loud and
measured at a second setting: Command Beacon's `beacon_min_tax` (4, and 2)
and Treasure Vault's `vault_min_treasures` (4, and 2). The baseline holds
neither card, so the knob is inert in it and the same baseline serves.
"""
import dataclasses
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from diagnostics.run_land_ablation import basic_for, swap
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.decks import (azusa_v1, karlov_v2, lorehold_v17, rendmaw_v12,
                         shilgengar_v1, tivit_v1)
from tools.candidates import filler_land

HORIZONS = (10, 20)
COUNTERS = ("tomb_damage", "cradle_mana", "land_lifegain", "beacon_used",
            "beacon_tax_saved", "vault_activations", "vault_x",
            "fetches_cracked", "myriad_cracked", "field_zombies",
            "lifegain_triggers", "life_gained", "life_lost_to_own_cards")

# THE THREE TRUE FETCHES ARE ONE CARD TO THIS ENGINE: the same `L()` fields
# and script, and the 1 life each pays is not charged (a ceiling, §0z113). So
# the games are identical -- the smoke run printed three equal rows -- and
# Verdant Catacombs is measured for all three.
SAME_AS = {"Misty Rainforest": "Verdant Catacombs",
           "Prismatic Vista": "Verdant Catacombs"}

# (deck, card, cfg overrides, label)
ARMS = [(d, c, {}, c.name) for d, mod in (
            ("rendmaw", rendmaw_v12), ("lorehold", lorehold_v17),
            ("karlov", karlov_v2), ("tivit", tivit_v1),
            ("shilgengar", shilgengar_v1), ("azusa", azusa_v1))
        for c in mod.LAND_CANDIDATES if c.name not in SAME_AS]
ARMS += [("lorehold", lorehold_v17.COMMAND_BEACON, {"beacon_min_tax": 2},
          "Command Beacon @ beacon_min_tax=2"),
         ("tivit", tivit_v1.TREASURE_VAULT, {"vault_min_treasures": 2},
          "Treasure Vault @ vault_min_treasures=2")]
DECKS = sorted({a[0] for a in ARMS})


def arm_deck(deck_name, arm):
    deck, cmd = build_pending(deck_name)
    if arm is None:
        return deck, cmd, {}
    if arm == "noop":
        basic = filler_land(deck)
        return swap(deck, basic.name, dataclasses.replace(basic)), cmd, {}
    _, card, over, _ = ARMS[arm]
    basic = basic_for(deck, card)
    return swap(deck, basic.name, dataclasses.replace(card)), cmd, over


def job(task):
    deck_name, arm, lo, hi = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd, over = arm_deck(deck_name, arm)
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
    arms = {d: [None, "noop"] + [i for i, a in enumerate(ARMS) if a[0] == d]
            for d in DECKS}
    tasks = [(d, a, lo, hi) for d in DECKS for a in arms[d]
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
        deck, _ = build_pending(d)

        def col(arm, t, m):
            return np.concatenate([np.array(got[(d, arm, lo, hi)][t][m])
                                   for lo, hi in parts])

        def counters(arm):
            return {k: sum(got[(d, arm, lo, hi)]["counters"][k]
                           for lo, hi in parts) / n for k in COUNTERS}

        def cell(arm):
            res = {}
            for t in HORIZONS:
                for m in run.metrics:
                    x = col(arm, t, m) - col(None, t, m)
                    res[f"{m}{t}"] = [float(x.mean()),
                                      float(1.96 * x.std(ddof=1) / np.sqrt(n))]
            return res

        base = counters(None)
        rows = {}
        for a in arms[d][2:]:
            _, card, over, label = ARMS[a]
            c = counters(a)
            rows[label] = {
                "basic": basic_for(deck, card).name,
                "knobs": over,
                "cells": cell(a),
                "counters": {k: round(c[k] - base[k], 4) for k in COUNTERS
                             if abs(c[k] - base[k]) > 1e-9},
            }
        out["decks"][d] = {
            "rows": rows,
            "noop_changed": int(sum(np.any(col(None, t, m) != col("noop", t, m))
                                    for t in HORIZONS for m in run.metrics)),
        }
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("saved", out_path)


def report(path):
    data = json.load(open(path))
    n = data["n"]
    print(f"LAND CANDIDATES, N={n:,} paired, seeds 5000.., staged lists "
          f"(§0z113). Each candidate in place of the basic it would replace; "
          f"win rate, candidate minus basic; * = CI excludes zero. Counters "
          f"are per game, candidate minus basic.\n")
    for d, res in data["decks"].items():
        print(f"{d.upper()}   NOOP changed {res['noop_changed']} metric "
              f"columns (must be 0)")
        print(f"  {'candidate':<42}{'for':<10}{'won T10':>18}{'won T20':>18}")
        for label, row in sorted(res["rows"].items(),
                                 key=lambda kv: -kv[1]["cells"]["won20"][0]):
            cells = []
            for t in HORIZONS:
                m, ci = row["cells"][f"won{t}"]
                star = "*" if abs(m) > ci else " "
                cells.append(f"{m:+.4f} ±{ci:.4f}{star}")
            print(f"  {label:<42}{row['basic']:<10}{cells[0]:>18}{cells[1]:>18}")
            if row["counters"]:
                print("      " + "  ".join(f"{k} {v:+.3f}" for k, v in
                                          sorted(row["counters"].items())))
        print()


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        measure(int(sys.argv[1]), sys.argv[2])
