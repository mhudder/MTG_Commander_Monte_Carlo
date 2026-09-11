#!/usr/bin/env python3
"""What is queued item 16 worth? Token copies that re-trigger the host's ETB.

    python -m diagnostics.run_springheart_etb [n_games]

THREE CHANGES SHIP TOGETHER AND THEY DO NOT POINT THE SAME WAY, so they are
measured apart. Reporting their sum as one number would hide that two of them
are corrections that COST the deck value:

  A  BASELINE       the pre-2026-09-10 engine: a token copy is a bare body.
  B  +copy ETB      the copy re-triggers the host's ETB (item 16 proper).
                    Adds value.
  C  +legend rule   a token copy of a LEGENDARY host dies on arrival, keeping
                    only its ETB. Takes value away -- and it is a correction,
                    not a nerf: the old engine kept an illegal second copy of
                    a legend on the battlefield, and `count()`-based landfall
                    payoffs doubled off it (§0z1).
  D  +re-rank       the host list is re-ordered for a world where copies have
                    ETBs, and Greensleeves -- legendary, and valuable only for
                    a LANDFALL trigger her copy now never lives to see -- is
                    dropped from it.

D is the whole change. A->D is what the azusa table needs regenerating for.

CFG KNOBS, NOT MONKEYPATCHES. §0u: Windows spawns fresh interpreters for
worker processes and a patch installed in the parent never reaches them. This
harness is single-process and would survive either way, which is exactly why
the habit matters -- the next one might not be.
"""
import sys

import numpy as np

from edhmc import azusa as AZ
from edhmc.experiment import DEFAULT_CFG, analyse, report
from edhmc.pending import build_pending

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
TURNS = 20

# The host order as it stood before the re-rank, so leg C measures the engine
# change alone and leg D adds the policy on top of it.
OLD_HOSTS = ("Scute Swarm", "Lotus Cobra", "Tireless Provisioner",
             "Rampaging Baloths", "Greensleeves, Maro-Sorcerer",
             "Avenger of Zendikar", "Courser of Kruphix", "Tireless Tracker")

LEGS = {
    "A baseline (copy is a bare body)":
        dict(copy_etb=False, copy_legend_rule=False,
             springheart_hosts=OLD_HOSTS),
    "B + copy ETB":
        dict(copy_etb=True, copy_legend_rule=False,
             springheart_hosts=OLD_HOSTS),
    "C + legend rule":
        dict(copy_etb=True, copy_legend_rule=True,
             springheart_hosts=OLD_HOSTS),
    "D + re-ranked hosts (SHIPPED)":
        dict(copy_etb=True, copy_legend_rule=True, springheart_hosts=None),
}

METRICS = ("won", "damage", "cards_drawn", "landfall_triggers", "tokens_made",
           "springheart_copies", "springheart_etbs", "springheart_legend_dies",
           "final_board_power")


def run(extra):
    deck, cmd = build_pending("azusa")
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset(), **extra)
    # Same seeds in every leg: the only thing that differs is the cfg, so the
    # paired difference is the change and nothing else.
    return [AZ.simulate(deck, cmd, cfg, 90000 + i) for i in range(N)]


def main():
    print(f"SPRINGHEART / ITEM 16 — {N:,} paired games, {TURNS} turns, "
          f"same seeds in every leg\n")
    rows = {name: run(cfg) for name, cfg in LEGS.items()}
    names = list(LEGS)

    print(f"{'leg':<34}{'win rate':>10}{'damage':>10}{'copies':>9}"
          f"{'ETBs':>8}{'legend':>8}{'tokens':>10}")
    for name in names:
        r = rows[name]
        print(f"{name:<34}"
              f"{np.mean([x['won'] for x in r]):>10.4f}"
              f"{np.mean([x['damage'] for x in r]):>10.2f}"
              f"{np.mean([x['springheart_copies'] for x in r]):>9.2f}"
              f"{np.mean([x['springheart_etbs'] for x in r]):>8.2f}"
              f"{np.mean([x['springheart_legend_dies'] for x in r]):>8.2f}"
              f"{np.mean([x['tokens_made'] for x in r]):>10.1f}")

    # Each step against the one before it, and the whole change against the
    # baseline -- the steps are what explains the total, and the total is what
    # the table needs regenerating for.
    steps = [(names[0], names[1]), (names[1], names[2]),
             (names[2], names[3]), (names[0], names[3])]
    for a, b in steps:
        print()
        report(rows[a], rows[b], a, b,
               dict(DEFAULT_CFG, turns=TURNS),
               analyse(rows[a], rows[b], metrics=METRICS))

    # WIN RATE TO FOUR PLACES. `report` prints two, and every effect in this
    # comparison lives in the third and fourth -- a table of "+0.00" four
    # times over is not a result, it is a formatting accident.
    print(f"\n{'=' * 100}\nWIN RATE, 4dp\n{'=' * 100}")
    for a, b in steps:
        w = next(r for r in analyse(rows[a], rows[b], metrics=("won",))
                 if r.metric == "won")
        print(f"  {a:<34} -> {b:<34} {w.mean_diff:+.4f} "
              f"[{w.ci_low:+.4f}, {w.ci_high:+.4f}] p={w.p_value:<10.3g}"
              f"{'  SIGNIFICANT' if w.significant else '  inside its bar'}")


if __name__ == "__main__":
    main()
