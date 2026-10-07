#!/usr/bin/env python3
"""Recompute ONE cached ablation row from scratch and compare it exactly.

    python -m tools.repro_row karlov "Mother of Runes"
    python -m tools.repro_row rendmaw "Steel Overseer" --procs=4

The keep and drop legs are played on the tables' seeds at the tables' N and
horizons, and every (mean, CI) cell of every metric is compared with the
committed cache to the last bit. Exit 0 when the row is IDENTICAL.

Written for the §0z119 rebuild, whose legs ran Python 3.13.16 while the
coordinator ran 3.11.15: the two interpreters play about one game in 15,000
differently (Python 3.12 made `sum()` of floats compensated), so a
coordinator on another interpreter cannot verify a leg's table. Run this
under the interpreter you mean to coordinate on; IDENTICAL on a row or two
is the evidence that it reproduces the legs.
"""
import json
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.pending import build_pending

N, HORIZONS = 15000, (10, 20)
_S = {}


def _init(deck_name, card):
    run = AB.Run(deck_name, N, HORIZONS)
    deck, cmd = build_pending(deck_name)
    _S.update(run=run, cmd=cmd, keep=deck, drop=AB.blanked(run, deck, card))


def _part(args):
    which, lo, hi = args
    return args, AB.columns_all(_S["run"], _S[which], _S["cmd"], lo, hi)


def main(argv) -> int:
    procs = next((int(a.split("=")[1]) for a in argv if a.startswith("--procs=")), 4)
    deck_name, card = [a for a in argv if not a.startswith("--")][:2]
    run = AB.Run(deck_name, N, HORIZONS)
    cached = json.load(open(run.cache))[card]
    parts = AB._chunks(N, procs)
    with Pool(procs, initializer=_init, initargs=(deck_name, card)) as pool:
        got = dict(pool.map(_part, [(w, lo, hi) for w in ("keep", "drop")
                                    for lo, hi in parts]))

    def col(which, t):
        return {m: np.concatenate([got[(which, lo, hi)][t][m]
                                   for lo, hi in parts]) for m in run.metrics}
    fresh = {str(t): AB.paired(run, col("keep", t), col("drop", t))
             for t in run.horizons}
    diff = [(t, m) for t in fresh for m in fresh[t]
            if [float(x) for x in fresh[t][m]] != list(cached[t][m])]
    print(f"python {sys.version.split()[0]}, numpy {np.__version__}: "
          f"{deck_name} / {card}: "
          + ("IDENTICAL" if not diff else f"DIFFERENT in {diff}"))
    for t in fresh:
        print(f"  T{t} won  fresh {fresh[t]['won'][0]:+.6f}  "
              f"cached {cached[t]['won'][0]:+.6f}")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
