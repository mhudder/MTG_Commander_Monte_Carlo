#!/usr/bin/env python3
"""What §0z118's eight fixes (§0z116 items 6-13) are worth, each against the
engine with it.

    python -m diagnostics.run_oracle_batch 15000 results/oracle_batch_20261007.json
    python -m diagnostics.run_oracle_batch --report results/oracle_batch_20261007.json

N paired games on the staged lists, the tables' seeds (5000..), one T20 game
per seed with T10 read off it (§0z93). Each arm turns fixes OFF and is
ARM MINUS THE NEW ENGINE: a positive number is what the missing text had
been flattering the deck by, a negative one what the fix is worth to it.
"all off" turns every one of the deck's switches off at once.

  protect_events  6   protection answers the events its text answers;
                      Mother of Runes is a {T} ability on the battlefield
  damn_overload   7   Damn is a wrath only at {2}{W}{W}
  kambal_batch    8   Kambal drains once per batch of tokens
  vigor_counters  9   Primal Vigor doubles +1/+1 counters in rendmaw
  own_wipe_scope  10  Culling Ritual, Ondu Inversion, Ultima, Promise of
                      Loyalty destroy what their text says
  giada_text      11  Giada's counters on every Angel that enters
  overseer_taps   12  Steel Overseer taps to activate
  gsz_shuffle     13  Green Sun's Zenith shuffles into the library
  mother_home     --  NOT a fix: when the pilot keeps Mother of Runes home
                      from combat so her {T} shroud is up -- "needed" (the
                      default) against "always" and "never"
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
KNOBS = {
    "rendmaw": ("protect_events", "vigor_counters", "own_wipe_scope",
                "overseer_taps"),
    "lorehold": ("protect_events", "own_wipe_scope"),
    "karlov": ("protect_events", "damn_overload"),
    "tivit": ("damn_overload", "kambal_batch", "own_wipe_scope"),
    "shilgengar": ("protect_events", "damn_overload", "giada_text"),
    "azusa": ("gsz_shuffle",),
}
ARMS = []
for _d, _ks in KNOBS.items():
    for _k in _ks:
        ARMS.append((_d, f"{_k} off", {_k: False}))
    if len(_ks) > 1:
        ARMS.append((_d, "all off", {k: False for k in _ks}))
# NOT a fix: the pilot's policy the {T} rule made live (CLAUDE.md, §0z42's
# lesson) -- Mother of Runes attacks, and is tapped for the pod's round.
# Each deck's default ("never" in karlov, "needed" in lorehold) is the
# baseline; the other two are the arms.
for _d, _modes in (("karlov", ("always", "needed")),
                   ("lorehold", ("always", "never"))):
    for _m in _modes:
        ARMS.append((_d, f"mother_home {_m}", {"mother_home": _m}))
COUNTERS = ("protected", "protected_indestructible", "removal_eaten",
            "wipes_suffered", "own_wipes_cast", "citadel_wipe_held",
            "kambal_triggers", "token_drain", "overseer_activations",
            "culling_mana", "culling_mana_spent", "turns_ended",
            "giada_counters", "gsz_shuffled", "own_wipe_survivors")


def job(task):
    deck_name, arm, lo, hi = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd = build_pending(deck_name)
    over = ARMS[arm][2] if arm is not None else {}
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
    for i, (d, label, over) in enumerate(ARMS):
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
    print(f"§0z116's ITEMS 6-13, FIXED (§0z118). N={d['n']:,} paired, staged "
          f"lists; each row turns fixes off: ARM MINUS THE NEW ENGINE "
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
