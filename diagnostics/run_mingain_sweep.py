#!/usr/bin/env python3
"""Finishes the shilgengar_ult_min_gain question from run_reserve_sweep.py:
raising it above the default (1) was monotonically worse (2: -0.0045, 3:
-0.0121, 5: -0.0233), which is the trend that says test BELOW it too.

    python run_mingain_sweep.py [--n=15000] [--procs=N]
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import shilgengar_v1
from edhmc.experiment import DEFAULT_CFG
from edhmc import shilgengar as S

DECK, CMD = shilgengar_v1.build()
OBS = ("won", "damage", "shilgengar_ults", "shilgengar_reanimated",
       "blood_made", "blood_spent", "angels_fed", "creatures_sacrificed")

_W = {}


def _init(flags, turns):
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)


def _one(seed):
    r = S.simulate(DECK, CMD, _W["cfg"], seed)
    return [r[m] for m in OBS]


def observe(flags, n, turns, procs):
    with Pool(procs, initializer=_init, initargs=(flags, turns)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    turns = 20

    a = observe({"shilgengar_ult_min_gain": 1}, n, turns, procs)
    print(f"  {'min_gain':<10}{'win rate':>22}{'ults':>18}{'reanimated':>18}")
    for v in (0, -2):
        b = observe({"shilgengar_ult_min_gain": v}, n, turns, procs)
        for i, m in enumerate(OBS):
            pass
        won = b[:, 0] - a[:, 0]
        ults = b[:, 2] - a[:, 2]
        reanim = b[:, 3] - a[:, 3]
        hw = 1.96 * won.std(ddof=1) / np.sqrt(n)
        star = "*" if abs(won.mean()) > hw else " "
        print(f"  {v:<10}{won.mean():>+10.4f} +-{hw:<8.4f}{star}"
              f"{ults.mean():>+9.3f}{reanim.mean():>+18.3f}")


if __name__ == "__main__":
    main()
