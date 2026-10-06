#!/usr/bin/env python3
"""Eye of Ugin's tutor, Kozilek's cast draw, and azusa's fetch pair (§0z114).

    python -m diagnostics.run_eye_of_ugin 15000 results/eye_of_ugin_20261006.json
    python -m diagnostics.run_eye_of_ugin --report results/eye_of_ugin_20261006.json

The owner asked whether Eye of Ugin's search is used. It was not: the
tutor ("{7}, {T}: Search your library for a colorless creature card") had no
implementation, and Kozilek's "When you cast this spell, draw four cards"
was missing too. Both are now modelled, each behind its own switch
(`eye_tutor`, `kozilek_cast_draw`), and this measures them against the staged
azusa list, the tables' seeds (5000..) and N, one T20 game per seed with T10
read off it (§0z93). Every arm is paired against the BASELINE, which is the
new engine with both on:

  old engine        both switches off: baseline minus this is the correction
  no Eye tutor      `eye_tutor="off"`
  no Kozilek draw   `kozilek_cast_draw=False`
  Eye -> Forest     the land's row on the new engine (§0z112 read it at
                    -0.0109 at T20 with the tutor missing)
  fetch pair        two Forests -> Fabled Passage + Evolving Wilds: the swap
                    the owner chose on 2026-10-06, measured as one change on
                    the engine it will be staged on
  Fabled / Evolving each alone, for the additivity of the pair
"""
import dataclasses
import json
import sys
import time
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.decks import azusa_v1 as AM
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

HORIZONS = (10, 20)
COUNTERS = ("eye_tutors", "kozilek_draws", "fetches_cracked", "cards_drawn",
            "landfall_triggers")
FOREST = "Forest"


def forest_like(deck):
    return dataclasses.replace(next(c for c in deck if c.name == FOREST))


def replace_forests(deck, cards):
    out, cards = list(deck), list(cards)
    for i, c in enumerate(out):
        if cards and c.name == FOREST:
            out[i] = dataclasses.replace(cards.pop(0))
    assert not cards
    return out


def eye_to_forest(deck):
    out = list(deck)
    i = next(i for i, c in enumerate(out) if c.name == "Eye of Ugin")
    out[i] = forest_like(deck)
    return out


ARMS = {
    "old engine": ({"eye_tutor": "off", "kozilek_cast_draw": False}, None),
    "no Eye tutor": ({"eye_tutor": "off"}, None),
    "no Kozilek draw": ({"kozilek_cast_draw": False}, None),
    "Eye of Ugin -> Forest": ({}, eye_to_forest),
    "-2 Forest +Fabled Passage +Evolving Wilds": (
        {}, lambda d: replace_forests(d, [AM.FABLED_PASSAGE,
                                          AM.EVOLVING_WILDS])),
    "-Forest +Fabled Passage": (
        {}, lambda d: replace_forests(d, [AM.FABLED_PASSAGE])),
    "-Forest +Evolving Wilds": (
        {}, lambda d: replace_forests(d, [AM.EVOLVING_WILDS])),
}


def job(task):
    arm, lo, hi = task
    run = AB.Run("azusa", 1, HORIZONS)
    deck, cmd = build_pending("azusa")
    over = {}
    if arm is not None:
        over, transform = ARMS[arm]
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
    out["counters"]["decked"] = float(sum(r.get("loss_route") == 3
                                          for r in rows))
    return task, out


def measure(n, out_path, procs=4):
    parts = AB._chunks(n, procs)
    tasks = [(a, lo, hi) for a in [None] + list(ARMS) for lo, hi in parts]
    got, t0 = {}, time.time()
    with Pool(procs) as pool:
        for i, (task, res) in enumerate(
                pool.imap_unordered(job, tasks, chunksize=1), 1):
            got[task] = res
            print(f"  {i}/{len(tasks)}  {time.time() - t0:.0f}s", flush=True)
    run = AB.Run("azusa", 1, HORIZONS)

    def col(arm, t, m):
        return np.concatenate([np.array(got[(arm, lo, hi)][t][m])
                               for lo, hi in parts])

    def counters(arm):
        keys = got[(arm, *parts[0])]["counters"]
        return {k: sum(got[(arm, lo, hi)]["counters"][k]
                       for lo, hi in parts) / n for k in keys}

    out = {"n": n, "baseline_counters": counters(None), "arms": {}}
    for arm in ARMS:
        cells = {}
        for t in HORIZONS:
            for m in run.metrics:
                x = col(arm, t, m) - col(None, t, m)
                cells[f"{m}{t}"] = [float(x.mean()),
                                    float(1.96 * x.std(ddof=1) / np.sqrt(n))]
        out["arms"][arm] = {"cells": cells, "counters": counters(arm)}
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("saved", out_path)


def report(path):
    d = json.load(open(path))
    print(f"EYE OF UGIN, KOZILEK, AND THE FETCH PAIR (azusa, §0z114). "
          f"N={d['n']:,} paired against the baseline -- the staged list on "
          f"the new engine, Eye tutor and Kozilek draw ON. Each row is ARM "
          f"MINUS BASELINE; * = CI excludes zero.\n")
    b = d["baseline_counters"]
    print("baseline, per game: " + "  ".join(f"{k} {v:.3f}"
                                            for k, v in sorted(b.items())))
    print()
    print(f"  {'arm':<44}{'won T10':>18}{'won T20':>18}{'damage T20':>16}")
    for arm, row in d["arms"].items():
        cells = []
        for key in ("won10", "won20", "damage20"):
            m, ci = row["cells"][key]
            cells.append(f"{m:+.4f} ±{ci:.4f}{'*' if abs(m) > ci else ' '}")
        print(f"  {arm:<44}{cells[0]:>18}{cells[1]:>18}{cells[2]:>16}")
        c = row["counters"]
        print("      " + "  ".join(f"{k} {c[k] - b[k]:+.3f}"
                                   for k in sorted(c) if abs(c[k] - b[k]) > 1e-9))


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        measure(int(sys.argv[1]), sys.argv[2])
