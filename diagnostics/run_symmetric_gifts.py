#!/usr/bin/env python3
"""§0z245: Tempting Contract's and Master of Ceremonies' Treasures for the pod.

    python -m diagnostics.run_symmetric_gifts           # the tables' seeds
    python -m diagnostics.run_symmetric_gifts --fresh   # seeds 20000..34999

Tivit's baseline and the two cards' ablation rows (keep minus the
median-priority blank, `tools.ablation`'s own `play` and `blanked`, on
`build_pending()`'s list) with `pod_gifts_symmetric` off -- the engine
before the fix -- and on, ON THE SAME SEEDS, so each change is paired per
seed and carries its own CI.

On the tables' seeds the OFF leg must reproduce tivit's rebuilt cache to
its digits (§0z35): baseline 0.5499, Tempting Contract +0.0091, Master of
Ceremonies +0.0190 at T20. The knob is set by rebinding
`tools.ablation.DEFAULT_CFG` inside each job, which `play` reads per call
(§0u).
"""
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

DECK, N, HORIZONS = "tivit", 15000, (10, 20)
CARDS = ["Tempting Contract", "Master of Ceremonies"]
RULES = {"off": dict(DEFAULT_CFG, pod_gifts_symmetric=False),
         "on": dict(DEFAULT_CFG, pod_gifts_symmetric=True)}


def job(args):
    rule, card, lo, hi = args
    AB.DEFAULT_CFG = RULES[rule]
    run = AB.Run(DECK, N, HORIZONS)
    deck, cmd = build_pending(DECK)
    if card is not None:
        deck = AB.blanked(run, deck, card)
    return args, AB.play(run, deck, cmd, range(lo, hi))


def ci(x):
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def main(argv):
    lo0 = 15000 if "--fresh" in argv else 0          # seeds 5000 + i
    chunks = [(lo0 + i * N // 8, lo0 + (i + 1) * N // 8) for i in range(8)]
    jobs = [(r, c, lo, hi) for r in RULES for c in [None] + CARDS
            for lo, hi in chunks]
    with Pool(4) as pool:
        got = dict(pool.imap_unordered(job, jobs))

    def col(rule, card, t, m="won"):
        return np.concatenate([got[(rule, card, lo, hi)][t][m]
                               for lo, hi in chunks])

    print(f"{DECK}, seeds {5000 + lo0}..{5000 + lo0 + N - 1}, N={N:,} "
          "paired; pod_gifts_symmetric off -> on; +- is 95%")
    for t in HORIZONS:
        b = {r: col(r, None, t) for r in RULES}
        d = b["on"] - b["off"]
        print(f"  baseline T{t}: off {b['off'].mean():.4f}  on "
              f"{b['on'].mean():.4f}  change {d.mean():+.4f}+-{ci(d):.4f}")
    for c in CARDS:
        line = f"  {c:22s}"
        for t in HORIZONS:
            r = {x: col(x, None, t) - col(x, c, t) for x in RULES}
            d = r["on"] - r["off"]
            line += (f" | T{t} off {r['off'].mean():+.4f}+-{ci(r['off']):.4f}"
                     f" on {r['on'].mean():+.4f}+-{ci(r['on']):.4f}"
                     f" change {d.mean():+.4f}+-{ci(d):.4f}")
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
