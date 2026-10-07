#!/usr/bin/env python3
"""What §0z117's five fixes are worth, each against the engine with it.

    python -m diagnostics.run_top_five 15000 results/top_five_20261007.json
    python -m diagnostics.run_top_five --report results/top_five_20261007.json

N paired games on the staged lists, the tables' seeds (5000..), one T20 game
per seed with T10 read off it (§0z93). Each arm turns ONE fix off and is
ARM MINUS THE NEW ENGINE: a positive number is what the missing text had
been flattering the deck by, a negative one what the fix is worth to it.

  rendmaw     Biotransference blank (`biotransference_text=False`)
  lorehold    discards never paid (`discard_text=False`)
  tivit       Coercive Portal a creature wipe that stays (`portal_text=False`)
  shilgengar  Kokusho vanilla (`kokusho_text=False`); and the OLD hand tags
              (Avacyn and Angel of Suffering not Angels, Bishop of Wings no
              Cleric), rebuilt into the list -- the tags have no switch
"""
import dataclasses
import json
import sys
import time
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

HORIZONS = (10, 20)
OLD_TAGS = {"Avacyn, Angel of Hope": frozenset(),
            "Angel of Suffering": frozenset(),
            "Bishop of Wings": frozenset()}


def old_tags(deck):
    return [dataclasses.replace(c, tags=(c.tags - {"angel", "cleric"})
                                | OLD_TAGS[c.name])
            if c.name in OLD_TAGS else c for c in deck]


ARMS = [
    ("rendmaw", "Biotransference off", {"biotransference_text": False}, None),
    ("lorehold", "discards off", {"discard_text": False}, None),
    ("tivit", "Portal text off", {"portal_text": False}, None),
    ("shilgengar", "Kokusho off", {"kokusho_text": False}, None),
    ("shilgengar", "old hand tags", {}, old_tags),
]
COUNTERS = ("biotransference_necrons", "rendmaw_triggers", "spell_discards",
            "portal_carnage", "portal_tokens_destroyed", "kokusho_drain",
            "blood_made", "own_wipes_cast", "life_lost_to_own_cards")


def job(task):
    deck_name, arm, lo, hi = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd = build_pending(deck_name)
    over = {}
    if arm is not None:
        _, _, over, transform = ARMS[arm]
        if transform is not None:
            deck = transform(deck)
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
    decks = sorted({a[0] for a in ARMS})
    tasks = [(d, None, lo, hi) for d in decks for lo, hi in parts]
    tasks += [(a[0], i, lo, hi) for i, a in enumerate(ARMS)
              for lo, hi in parts]
    got, t0 = {}, time.time()
    with Pool(procs) as pool:
        for i, (task, res) in enumerate(
                pool.imap_unordered(job, tasks, chunksize=1), 1):
            got[task] = res
            if i % 4 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)}  {time.time() - t0:.0f}s",
                      flush=True)
    out = {"n": n, "arms": []}
    for i, (d, label, over, _) in enumerate(ARMS):
        run = AB.Run(d, 1, HORIZONS)

        def col(arm, t, m):
            return np.concatenate([np.array(got[(d, arm, lo, hi)][t][m])
                                   for lo, hi in parts])

        def counters(arm):
            return {k: sum(got[(d, arm, lo, hi)]["counters"][k]
                           for lo, hi in parts) / n for k in COUNTERS}
        cells = {}
        for t in HORIZONS:
            for m in run.metrics:
                x = col(i, t, m) - col(None, t, m)
                cells[f"{m}{t}"] = [float(x.mean()), float(
                    1.96 * x.std(ddof=1) / np.sqrt(n))]
        out["arms"].append({"deck": d, "arm": label, "cells": cells,
                            "new": counters(None), "off": counters(i)})
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("saved", out_path)


def report(path):
    d = json.load(open(path))
    print(f"§0z116's TOP FIVE, FIXED (§0z117). N={d['n']:,} paired, staged "
          f"lists; each row turns ONE fix off: ARM MINUS THE NEW ENGINE "
          f"(* = CI excludes zero).\n")
    print(f"  {'deck':<11}{'arm':<22}{'won T10':>18}{'won T20':>18}"
          f"{'damage T20':>18}")
    for a in d["arms"]:
        cells = []
        for key in ("won10", "won20", "damage20"):
            m, ci = a["cells"][key]
            cells.append(f"{m:+.4f} ±{ci:.4f}{'*' if abs(m) > ci else ' '}")
        print(f"  {a['deck']:<11}{a['arm']:<22}" + "".join(
            f"{c:>18}" for c in cells))
        moved = {k: (a["new"][k], a["off"][k]) for k in a["new"]
                 if abs(a["new"][k] - a["off"][k]) > 1e-9}
        print("      per game, new -> off: " + "  ".join(
            f"{k} {v[0]:.2f}->{v[1]:.2f}" for k, v in moved.items()))


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        measure(int(sys.argv[1]), sys.argv[2])
