#!/usr/bin/env python3
"""What is queued item 13 worth? Shilgengar's Treasures, spent as mana.

    python -m diagnostics.run_shilgengar_treasures [n_games]

Until 2026-09-10 `self.treasures` was a counter that ONLY Revel in Riches read.
Pitiless Plunderer, Smothering Tithe, Black Market Connections and Wayfarer's
Bauble all made Treasures and nothing ever spent one, so three of this deck's
mana sources produced no mana — and `ult_reserve()` held three mana back
through every main phase for an ultimate the Treasures could often have paid
for, which is a cost §0t measured and attributed to the reserve policy.

TWO LEGS, because the item makes two claims and they are separable:

  A  BASELINE      Treasures are inert; the reserve is always 3 when the
                   ultimate line is live.
  B  SPENDABLE     `pay()` spends Treasures after real mana, everywhere; and
                   `ult_reserve()` returns 0 when the Treasures alone already
                   cover the ultimate.

THE METRIC TO WATCH IS NOT WIN RATE FIRST. `treasures_spent` says whether the
mechanism fires at all, and `shilgengar_ults` says whether the reserve change
reached the ability it was for. A win rate that moves while those do not would
mean something else changed.
"""
import sys

import numpy as np

from edhmc import shilgengar as SH
from edhmc.experiment import DEFAULT_CFG, analyse, report
from edhmc.pending import build_pending

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
TURNS = 20

METRICS = ("won", "damage", "treasures_made", "treasures_spent",
           "shilgengar_ults", "blood_made", "mana_spent", "cards_drawn",
           "final_board_power")


def run(treasures_as_mana):
    deck, cmd = build_pending("shilgengar")
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset(),
               treasures_as_mana=treasures_as_mana)
    return [SH.simulate(deck, cmd, cfg, 91000 + i) for i in range(N)]


def main():
    print(f"SHILGENGAR TREASURES / ITEM 13 — {N:,} paired games, {TURNS} "
          f"turns, same seeds\n")
    a, b = run(False), run(True)

    print(f"{'leg':<28}{'win rate':>10}{'made':>8}{'spent':>8}{'ults':>8}"
          f"{'mana':>9}")
    for name, rows in (("A inert (baseline)", a), ("B spendable", b)):
        print(f"{name:<28}"
              f"{np.mean([x['won'] for x in rows]):>10.4f}"
              f"{np.mean([x['treasures_made'] for x in rows]):>8.2f}"
              f"{np.mean([x['treasures_spent'] for x in rows]):>8.2f}"
              f"{np.mean([x['shilgengar_ults'] for x in rows]):>8.3f}"
              f"{np.mean([x['mana_spent'] for x in rows]):>9.1f}")

    res = analyse(a, b, metrics=METRICS)
    print()
    report(a, b, "A inert", "B spendable", dict(DEFAULT_CFG, turns=TURNS), res)

    # Win rate to four places, because this deck's effects live in the third
    # and the report's two-decimal column cannot show one.
    won = next(r for r in res if r.metric == "won")
    print(f"\n  WIN RATE, 4dp: {won.mean_a:.4f} -> {won.mean_b:.4f}   "
          f"{won.mean_diff:+.4f}  [{won.ci_low:+.4f}, {won.ci_high:+.4f}]  "
          f"p={won.p_value:.4g}   {'SIGNIFICANT' if won.significant else 'inside its bar'}")


if __name__ == "__main__":
    main()
