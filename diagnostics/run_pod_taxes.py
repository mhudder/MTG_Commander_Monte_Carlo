#!/usr/bin/env python3
"""§0z246 (queue item 52, part A): your tax cards read the pod's mana.

    python -m diagnostics.run_pod_taxes            # the tables' seeds
    python -m diagnostics.run_pod_taxes --fresh    # seeds 20000..34999
    python -m diagnostics.run_pod_taxes tivit      # one deck

Each deck's baseline and the rows of its tax cards (keep minus the
median-priority blank, `tools.ablation`'s own `play` and `blanked`, on
`build_pending()`'s list) with the four switches OFF -- the engine before
-- and ON, ON THE SAME SEEDS, so each change is paired per seed and
carries its own CI.

On the tables' seeds the OFF leg must reproduce the rebuilt caches (§0z35)
for lorehold, shilgengar and azusa, whose engines have not moved since;
tivit's off leg is §0z245's ON leg (baseline 0.5477, Tempting Contract
+0.0077), its cache being SUSPECT since. The switches are set by rebinding
`tools.ablation.DEFAULT_CFG` inside each job, which `play` reads per call
(§0u).
"""
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

N, HORIZONS = 15000, (10, 20)
KNOBS = ("rhystic_from_pod", "tithe_from_pod", "monologue_from_pod",
         "minds_eye_from_pod")
RULES = {"off": dict(DEFAULT_CFG, **{k: False for k in KNOBS}),
         "on": dict(DEFAULT_CFG, **{k: True for k in KNOBS})}
CARDS = {"tivit": ["Rhystic Study", "Monologue Tax"],
         "lorehold": ["Smothering Tithe"],
         "shilgengar": ["Smothering Tithe"],
         "azusa": ["Mind's Eye"]}


def job(args):
    deck_name, rule, card, lo, hi = args
    AB.DEFAULT_CFG = RULES[rule]
    run = AB.Run(deck_name, N, HORIZONS)
    deck, cmd = build_pending(deck_name)
    if card is not None:
        deck = AB.blanked(run, deck, card)
    return args, AB.play(run, deck, cmd, range(lo, hi))


def ci(x):
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def main(argv):
    lo0 = 15000 if "--fresh" in argv else 0          # seeds 5000 + i
    decks = [a for a in argv if a in CARDS] or list(CARDS)
    chunks = [(lo0 + i * N // 8, lo0 + (i + 1) * N // 8) for i in range(8)]
    jobs = [(d, r, c, lo, hi) for d in decks for r in RULES
            for c in [None] + CARDS[d] for lo, hi in chunks]
    with Pool(4) as pool:
        got = dict(pool.imap_unordered(job, jobs))

    def col(d, rule, card, t):
        return np.concatenate([got[(d, rule, card, lo, hi)][t]["won"]
                               for lo, hi in chunks])

    print(f"seeds {5000 + lo0}..{5000 + lo0 + N - 1}, N={N:,} paired; "
          "the four switches off -> on; +- is 95%")
    for d in decks:
        print(d)
        for t in HORIZONS:
            b = {r: col(d, r, None, t) for r in RULES}
            ch = b["on"] - b["off"]
            print(f"  baseline T{t}: off {b['off'].mean():.4f}  on "
                  f"{b['on'].mean():.4f}  change {ch.mean():+.4f}"
                  f"+-{ci(ch):.4f}")
        for c in CARDS[d]:
            line = f"  {c:18s}"
            for t in HORIZONS:
                r = {x: col(d, x, None, t) - col(d, x, c, t) for x in RULES}
                ch = r["on"] - r["off"]
                line += (f" | T{t} off {r['off'].mean():+.4f}"
                         f"+-{ci(r['off']):.4f} on {r['on'].mean():+.4f}"
                         f"+-{ci(r['on']):.4f} change {ch.mean():+.4f}"
                         f"+-{ci(ch):.4f}")
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
