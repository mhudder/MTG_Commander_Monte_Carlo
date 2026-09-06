#!/usr/bin/env python3
"""Why each Penance replacement scores what it scores.

The Galvanoth verdict was only credible because the instrumentation said WHY:
"cast in 15.6% of games, on turn 9.8, 0.51 free casts per game it resolves,
0.08 overall." A win-rate number without that is a result nobody can trace to
the card's text, which this project treats as not a result yet.

    python diag_fivedrop.py [--n 6000] [--turns 20]
"""
import sys

import numpy as np

from edhmc.lorehold import simulate as lorehold_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, _swap_many

from edhmc.decks.lorehold_v16 import (GALVANOTH, CALDERA_PYREMAW,
                                      RADIANT_SCROLLWIELDER)

CUT = "Penance"
CANDIDATES = [GALVANOTH, CALDERA_PYREMAW, RADIANT_SCROLLWIELDER]

# The counter that IS the card's mechanism, per candidate.
MECHANISM = {
    "Galvanoth": ("upkeep_free_casts", "free casts off the top"),
    "Caldera Pyremaw": ("pyremaw_damage", "pod damage from its own trigger"),
    "Radiant Scrollwielder": ("scrollwielder_casts", "spells cast from the yard"),
}


def main():
    argv = sys.argv[1:]

    def opt(flag, default):
        return int(argv[argv.index(flag) + 1]) if flag in argv else default

    n, turns = opt("--n", 6000), opt("--turns", 20)
    deck, cmd = build_pending("lorehold", apply_pending=False)

    print(f"n={n:,} games, {turns} turns, pod v3. "
          f"Each candidate swapped in for {CUT}.\n")
    print(f"{'card':<24}{'MV':>3}{'cast%':>8}{'turn':>7}{'resolved%':>11}"
          f"{'mech/game':>11}{'mech/resolve':>14}   mechanism")
    print("-" * 104)

    for card in CANDIDATES:
        cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({card.name}))
        rows = [lorehold_sim(_swap_many(deck, [CUT], [card]), cmd, cfg,
                             1234 + i) for i in range(n)]
        key, label = MECHANISM[card.name]

        cast = np.array([r["cast_test_card"] for r in rows], dtype=float)
        resolved = np.array([r["test_card_resolved"] for r in rows], dtype=float)
        mech = np.array([r[key] for r in rows], dtype=float)
        # test_card_turn is 99 in games where it was never cast
        t = np.array([r["test_card_turn"] for r in rows], dtype=float)
        t = t[t < 99]

        per_resolve = mech.sum() / resolved.sum() if resolved.sum() else 0.0
        print(f"{card.name:<24}{card.mv:>3}{cast.mean() * 100:>7.1f}%"
              f"{(t.mean() if len(t) else float('nan')):>7.1f}"
              f"{resolved.mean() * 100:>10.1f}%"
              f"{mech.mean():>11.2f}{per_resolve:>14.2f}   {label}")

    print("\ncast%      games in which the card was cast at all")
    print("turn       mean turn it was cast, among those games")
    print("resolved%  games where it resolved and was not answered by the pod")
    print("mech/game  the mechanism counter averaged over ALL games")
    print("mech/resolve  ... over only the games where it stuck. This is the "
          "number\n           that says whether the CARD is good; mech/game "
          "says whether the\n           SLOT is, and the two differ by how "
          "often you draw a five-drop.")


if __name__ == "__main__":
    main()
