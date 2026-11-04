#!/usr/bin/env python3
"""Re-measure an adopted pilot policy OUT OF SAMPLE (§0z170).

    python -m diagnostics.run_policy_recheck DECK N SEED0 [--chip-sigma=S]

The policies adopted from §0z160-§0z168 were chosen among many arms on seeds
5000.., and the winner of a field is graded by the seeds that picked it. This
plays the adopted defaults ("new") against the pilot before them on seeds
nobody chose with, N paired games at T10 and T20, the staged list
(`build_pending`). Arms per deck are in `ARMS`:

  lorehold  old: `miracle_reserve` 2, `hold_min_value` 3, the float that
            counted Treasures twice (§0z164, §0z166, §0z168)
  karlov    old: every §0z160 switch off and the fixed floor of 10;
            fixed10: the §0z160 dig on the fixed floor (§0z161's clock alone)

`--chip-sigma=S` asks whether the clock floor (§0z161) leans on the pod's chip
being a formula the pilot reads exactly: the pod's ACTUAL swing is the
formula times a mean-1 lognormal(S) factor, one CRN-addressed draw per pod
turn and opponent (`crn_random`, §0z17), while the pilot's prediction
(`predicted_chip`, which passes its creature count explicitly) stays the
mean. Installed in each worker's initializer (§0u). Output: one line per arm,
new minus arm, 95% CI, `*` where it excludes 0.
"""
import importlib
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

ARMS = {
    "lorehold": {"new": {},
                 "old": {"miracle_reserve": 2, "hold_min_value": 3.0,
                         "float_board_only": False}},
    "karlov": {"new": {},
               "old": {"citadel_x0": False, "citadel_skip": False,
                       "citadel_spin": False, "citadel_damn_single": False,
                       "citadel_main_loop": False, "citadel_main2": False,
                       "citadel_pod_instants": False,
                       "citadel_decking_guard": False,
                       "citadel_floor_mode": "fixed"},
               "fixed10": {"citadel_floor_mode": "fixed"}},
}
CHUNK = 250
_D = {}


def _patch_chip(sigma):
    if sigma <= 0:
        return
    from statistics import NormalDist
    from edhmc import opponents as O
    from edhmc.engine import crn_random
    orig, inv = O.chip_amount, NormalDist().inv_cdf

    def noisy(g, opp, share, creatures=None):
        base = orig(g, opp, share, creatures)
        if creatures is not None or base <= 0:
            return base                       # the pilot's read: the mean
        i = next(k for k, o in enumerate(g.opponents) if o is opp)
        u = crn_random(g, f"chipnoise{O.pod_turn(g)}_{i}")
        u = min(max(u, 1e-9), 1 - 1e-9)
        return base * math.exp(sigma * inv(u) - sigma * sigma / 2)
    O.chip_amount = noisy


def _init(deck, sigma):
    _patch_chip(sigma)
    from edhmc.pending import build_pending
    _D["deck"], _D["cmd"] = build_pending(deck)
    _D["sim"] = importlib.import_module(f"edhmc.{deck}").simulate
    _D["name"] = deck


def _job(args):
    arm, turns, lo, hi = args
    from edhmc.experiment import DEFAULT_CFG
    cfg = dict(DEFAULT_CFG, turns=turns, **ARMS[_D["name"]][arm])
    won = [float(_D["sim"](_D["deck"], _D["cmd"], cfg, s).get("won", 0))
           for s in range(lo, hi)]
    return arm, turns, lo, won


def main(argv):
    sigma = 0.0
    for a in list(argv):
        if a.startswith("--chip-sigma="):
            sigma = float(a.split("=", 1)[1])
            argv.remove(a)
    deck, n, s0 = argv[0], int(argv[1]), int(argv[2])
    arms = list(ARMS[deck]) if sigma <= 0 else ["new", "fixed10"]
    jobs = [(a, t, lo, min(lo + CHUNK, s0 + n)) for a in arms
            for t in (10, 20) for lo in range(s0, s0 + n, CHUNK)]
    res, t0 = {}, time.time()
    with Pool(initializer=_init, initargs=(deck, sigma)) as pool:
        for arm, t, lo, won in pool.imap_unordered(_job, jobs):
            res.setdefault((arm, t), {})[lo] = won
    col = {k: np.array(sum((v[lo] for lo in sorted(v)), []))
           for k, v in res.items()}
    print(f"{deck} chip_sigma={sigma} N={n:,} paired, seeds {s0}.., the staged "
          f"list, python {sys.version.split()[0]}, {time.time() - t0:.0f}s")
    for a in arms:
        if a == "new":
            continue
        cells = []
        for t in (10, 20):
            d = col[("new", t)] - col[(a, t)]
            mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            cells.append(f"T{t} P(win) {col[('new', t)].mean():.4f}  new-{a} "
                         f"{mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ' '}")
        print(f"  new - {a:<8} " + "   ".join(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
