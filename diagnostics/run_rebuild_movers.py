#!/usr/bin/env python3
"""Item 50's rebuild: were the biggest movers real? (§0z244, §0z170)

    python -m diagnostics.run_rebuild_movers            # fresh seeds 20000..34999
    python -m diagnostics.run_rebuild_movers --tables   # the tables' seeds: the check

For each card, its ablation row -- keep minus the median-priority blank, on
`build_pending()`'s list, through `tools.ablation`'s own `play` and
`blanked` -- under the pod before item 50 (`POD_PRE_ITEM50`) and the pod
after (`DEFAULT_CFG`), ON THE SAME SEEDS, so the change in the row is paired
per seed and carries its own CI. The movers were picked as the largest of
379 table rows, so the seeds that picked them grade them (§0z170): the
fresh run is the measurement.

`--tables` plays one card on the tables' seeds (5000..19999), and must
reproduce BOTH tables: the old-pod row is the table at `120cc9a`, the
new-pod row the rebuilt cache (§0z35). It did: Biotransference T20 +0.0059
/ +0.0101 and baseline 0.3361 / 0.3393, both to the table's digits.

The pod is chosen by rebinding `tools.ablation.DEFAULT_CFG` inside each
job: `play` reads the module global per call, and each job sets it before
playing, so a fresh worker cannot miss it (§0u).
"""
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG, POD_PRE_ITEM50
from edhmc.pending import build_pending

N = 15000
HORIZONS = (10, 20)
PODS = {"old": dict(DEFAULT_CFG, **POD_PRE_ITEM50), "new": dict(DEFAULT_CFG)}
# The largest T20 movers of §0z244, two to five a deck (shilgengar's were
# the smallest and are left out).
MOVERS = {
    "lorehold": ["Storm-Kiln Artist", "Emeria's Call", "Ultima", "Storm Herd"],
    "tivit": ["Orzhov Signet", "Path to Exile", "Idyllic Tutor",
              "Tyrant's Choice", "Damn"],
    "rendmaw": ["Biotransference", "Heroic Intervention"],
    "azusa": ["Ancient Greenwarden"],
    "karlov": ["Voice of the Blessed"],
}
CHECK = {"rendmaw": ["Biotransference"]}


def job(args):
    deck_name, pod, card, lo, hi = args
    AB.DEFAULT_CFG = PODS[pod]
    run = AB.Run(deck_name, N, HORIZONS)
    deck, cmd = build_pending(deck_name)
    if card is not None:
        deck = AB.blanked(run, deck, card)
    return args, AB.play(run, deck, cmd, range(lo, hi))


def ci(x):
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def main(argv):
    tables = "--tables" in argv
    lo0 = 0 if tables else 15000                # seeds 5000 + i
    cards = CHECK if tables else MOVERS
    chunks = [(lo0 + i * N // 8, lo0 + (i + 1) * N // 8) for i in range(8)]
    jobs = [(d, pod, c, lo, hi) for d, cs in cards.items() for pod in PODS
            for c in [None] + cs for lo, hi in chunks]
    with Pool(4) as pool:
        got = dict(pool.imap_unordered(job, jobs))

    def col(d, pod, c, t):
        return np.concatenate([got[(d, pod, c, lo, hi)][t]["won"]
                               for lo, hi in chunks])

    print(f"seeds {5000 + lo0}..{5000 + lo0 + N - 1}, N={N:,} paired; "
          "row = keep - blank; change = new-pod row - old-pod row, paired "
          "per seed; +- is 95%")
    for d, cs in cards.items():
        for c in cs:
            line = f"{d:9s} {c:24s}"
            for t in HORIZONS:
                r = {p: col(d, p, None, t) - col(d, p, c, t) for p in PODS}
                ch = r["new"] - r["old"]
                line += (f" | T{t} old {r['old'].mean():+.4f}+-{ci(r['old']):.4f}"
                         f" new {r['new'].mean():+.4f}+-{ci(r['new']):.4f}"
                         f" change {ch.mean():+.4f}+-{ci(ch):.4f}")
            print(line, flush=True)
    for d in cards:
        b = {p: col(d, p, None, 20).mean() for p in PODS}
        print(f"baseline T20 {d}: old {b['old']:.4f} new {b['new']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
