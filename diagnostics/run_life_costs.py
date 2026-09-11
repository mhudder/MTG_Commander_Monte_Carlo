#!/usr/bin/env python3
"""What does charging a card's own life cost do? (§0i, queued item 10)

    python -m diagnostics.run_life_costs [n_games]

"Life-loss drawbacks are free in the model" has been a standing finding since
pod v3 made life decide roughly a third of losses. Two cards in committed lists
paid nothing:

    Bitterblossom      rendmaw   "create a 1/1 Faerie, AND YOU LOSE 1 LIFE",
                                 every upkeep from the turn it lands. The
                                 flagged one: +0.0205, Rendmaw's #5 card, on a
                                 drawback it was not paying.
    Phyrexian Arena    karlov    "you draw a card AND YOU LOSE 1 LIFE" -- and
                                 edhmc/shilgengar.py ALREADY charged it for the
                                 identical card. Two engines, one card, two
                                 behaviours: the §0u drift shape.

NOT FIXED AND MEASURED HERE, because the mana model cannot express it:
Talisman of Conviction deals 1 damage to you per COLOURED tap, and `spend()`
taps a source without recording which colour it produced. Charging per tap
would overcharge (it is free for colourless) and charging never is what happens
today. Said out loud rather than guessed at.

Each deck is measured on its own engine, since the two cards are in different
lists and nothing here is shared.
"""
import sys

import numpy as np

from edhmc import engine, karlov
from edhmc.experiment import DEFAULT_CFG, analyse, report
from edhmc.pending import build_pending

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
TURNS = 20

DECKS = {
    "rendmaw (Bitterblossom)": (engine.simulate, "rendmaw"),
    "karlov (Phyrexian Arena)": (karlov.simulate, "karlov"),
}

METRICS = ("won", "lost", "damage", "final_life", "turns_played",
           "cards_drawn")


def run(sim, deck_name, charge):
    deck, cmd = build_pending(deck_name)
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset(),
               charge_life_costs=charge)
    return [sim(deck, cmd, cfg, 92000 + i) for i in range(N)]


def main():
    print(f"LIFE COSTS / §0i — {N:,} paired games, {TURNS} turns, same seeds\n")
    for label, (sim, deck_name) in DECKS.items():
        a = run(sim, deck_name, False)     # free, as before
        b = run(sim, deck_name, True)      # charged
        res = analyse(a, b, metrics=METRICS)
        print(f"\n{'=' * 100}\n{label}\n{'=' * 100}")
        report(a, b, "free", "charged", dict(DEFAULT_CFG, turns=TURNS), res)
        won = next(r for r in res if r.metric == "won")
        life = next(r for r in res if r.metric == "final_life")
        print(f"  WIN RATE, 4dp: {won.mean_a:.4f} -> {won.mean_b:.4f}   "
              f"{won.mean_diff:+.4f}  [{won.ci_low:+.4f}, {won.ci_high:+.4f}]  "
              f"p={won.p_value:.4g}   "
              f"{'SIGNIFICANT' if won.significant else 'inside its bar'}")
        print(f"  final life:    {life.mean_a:.2f} -> {life.mean_b:.2f}   "
              f"{life.mean_diff:+.2f}")
        print(f"  life paid to own cards: "
              f"{np.mean([r.get('life_lost_to_own_cards', 0) for r in b]):.2f}"
              f" a game")


if __name__ == "__main__":
    main()
