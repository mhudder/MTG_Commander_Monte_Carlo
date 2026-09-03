#!/usr/bin/env python3
"""
Learning a tutor target policy by randomised experiment.

THE METHOD
----------
Card evaluation asks "is this card good?" and is answered by ablation. A tutor
asks a different question: "what should I fetch, and does the answer depend on
the game state?" That is a policy problem, and it needs a different design.

The trick is to make the sim choose its own target UNIFORMLY AT RANDOM from a
shortlist, then log (game state, target chosen, final outcome) for every
resolution. Because the target is randomised and the state is observed before
the choice, each resolution is a small randomised controlled trial. Comparing
targets WITHIN a state bucket is causal.

Comparing ACROSS state buckets is not: the turn you cast the tutor is not
randomised, and games where you are still casting tutors on turn 10 are
different games. Read down the columns, never across the rows.

    python tutor_policy.py collect     # gather the randomised dataset
    python tutor_policy.py analyse     # per-bucket win rates
    python tutor_policy.py evaluate    # A/B the learned policy vs fixed ones
"""
import json
import sys
from collections import defaultdict

import numpy as np

from edhmc.pending import build_pending
from edhmc.lorehold import simulate as lh_sim
from edhmc.experiment import DEFAULT_CFG

SHORTLIST = ("Arcane Bombardment", "Monument to Endurance", "Land Tax",
             "Smothering Tithe", "Library of Leng", "Sol Ring",
             "Sensei's Divining Top")
LOG = "tutor_log.json"
N_COLLECT = 45000
MIN_CELL = 40


def collect():
    deck, cmd = build_pending("lorehold")
    cfg = dict(DEFAULT_CFG, turns=14, watch=frozenset(),
               tutor_policy="random", tutor_targets=SHORTLIST)
    rows = []
    for j in range(N_COLLECT):
        r = lh_sim(deck, cmd, cfg, 20000 + j)
        for (turn, name, lands, hand, cmdr) in r["tutor_log"]:
            rows.append((name, turn, lands, cmdr, r["won"], r["damage"]))
    json.dump(rows, open(LOG, "w"))
    print(f"{len(rows)} tutor events from {N_COLLECT} games")


def analyse():
    rows = json.load(open(LOG))
    for title, key in (
        ("by TURN CAST", lambda t, l, c: "early T<=6" if t <= 6
         else ("mid T7-9" if t <= 9 else "late T>=10")),
        ("by COMMANDER STATUS", lambda t, l, c: "Lorehold out" if c
         else "no commander"),
    ):
        g = defaultdict(list)
        for name, turn, lands, cmdr, won, dmg in rows:
            g[(key(turn, lands, cmdr), name)].append(won)
        buckets = sorted({k[0] for k in g})
        print(f"\nWIN RATE {title}  (compare DOWN each column, not across)")
        print(f"  {'target':<26}" + "".join(f"{b:>18}" for b in buckets))
        for n in SHORTLIST:
            cells = []
            for b in buckets:
                v = g.get((b, n), [])
                if len(v) < MIN_CELL:
                    cells.append(f"{'--':>18}")
                    continue
                m = np.mean(v)
                se = np.std(v, ddof=1) / np.sqrt(len(v))
                cells.append(f"{m:>12.3f}+-{se:<5.3f}")
            print(f"  {n:<26}" + "".join(cells))


def evaluate(n=14000):
    deck, cmd = build_pending("lorehold")

    def run(policy, order=()):
        cfg = dict(DEFAULT_CFG, turns=14, watch=frozenset(),
                   tutor_targets=SHORTLIST, tutor_policy=policy,
                   tutor_order=order)
        return np.array([lh_sim(deck, cmd, cfg, 60000 + j)["won"]
                         for j in range(n)], float)

    fixed = {f"always {c}": run("fixed", (c,)) for c in
             ("Arcane Bombardment", "Land Tax", "Monument to Endurance")}
    adaptive = run("adaptive")
    print(f"{'tutor policy':<32}{'win rate':>12}")
    for k, v in fixed.items():
        print(f"{k:<32}{v.mean():>12.4f}")
    print(f"{'ADAPTIVE (state-dependent)':<32}{adaptive.mean():>12.4f}")
    for k, v in fixed.items():
        d = adaptive - v
        ci = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
        print(f"  adaptive - ({k}) = {d.mean():+.4f} +-{ci:.4f}")


if __name__ == "__main__":
    {"collect": collect, "analyse": analyse,
     "evaluate": evaluate}[sys.argv[1] if len(sys.argv) > 1 else "analyse"]()
