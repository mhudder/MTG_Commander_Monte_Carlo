#!/usr/bin/env python3
"""What do the 2026-09-10 Azusa candidates actually DO, per game?

The win rates for these seven live in `results/candidates_azusa_batch3_T20.txt`.
A win rate is not an explanation, and this project's standing rule is that a
number nobody can trace to a card's text is not a result yet -- so this prints
the MECHANISM COUNTERS beside each card: how often it resolves, on what turn,
and how many times the thing the card says happens happened.

That ordering matters more here than usual. Four of the seven have a dynamic
cost or a restricted pool, so the first question about each of them is not "is
it good" but "does it ever get cast", and a cost bug looks exactly like a bad
card in a win-rate table. The Great Henge at its printed {7}{G}{G} would resolve
in a handful of games and score like a bad nine-drop; The Great Henge at its
real cost is a three- or four-drop. One counter separates those two worlds.

    python -m diagnostics.diag_azusa_batch3 [n_games]

Reads the same staged list, victim slot and seeds as tools/candidates.py, so
the rows here and the rows there describe the same games.
"""
import sys

import numpy as np

from edhmc.azusa import simulate as azusa_sim
from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.pending import build_pending
from edhmc.decks import azusa_v1 as M
from tools.candidates import blank_like, filler_land
from edhmc.experiment import repl_priority

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
TURNS = 20
VICTIM = "Sylvan Library"        # see tools/candidates.py DECKS["azusa3"]

# What to print for each card, and it is deliberately per-card rather than one
# shared block: the whole point is to name the mechanism the card claims.
COUNTERS = {
    "The Great Henge": ("henge_draws", "henge_life", "cards_drawn"),
    "Sapling Nursery": ("tokens_made", "landfall_triggers",
                        "final_board_power"),
    "Nissa, Who Shakes the World": ("pw_activations", "pw_ultimates",
                                    "mana_spent", "landfall_triggers"),
    "Return of the Wildspeaker": ("wildspeaker_asked", "wildspeaker_draws",
                                  "wildspeaker_pumps", "cards_drawn"),
    "Finale of Devastation": ("finale_from_yard", "final_board_power",
                              "mana_spent"),
    "War Room": ("war_room_draws", "cards_drawn", "final_life"),
    "Castle Garenbrig": ("castle_activations", "castle_mana_spent",
                         "mana_spent"),
}


def run(cand):
    deck, cmd = build_pending("azusa")
    blank = blank_like(cand, repl_priority(deck), deck)
    a = _swap_many(deck, [VICTIM], [blank])
    b = _swap_many(deck, [VICTIM], [cand])
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset({cand.name}))
    # The same seeds candidates.py uses, so these rows and those rows are the
    # same games and can be read against each other.
    ra = [azusa_sim(a, cmd, cfg, 80000 + j) for j in range(N)]
    rb = [azusa_sim(b, cmd, cfg, 80000 + j) for j in range(N)]
    return ra, rb


def mean(rows, key):
    return float(np.mean([r.get(key, 0.0) for r in rows]))


def main():
    print(f"AZUSA batch 3 -- mechanism counters, {N:,} paired games, "
          f"{TURNS} turns")
    print(f"victim slot: {VICTIM}   (land candidates are measured against a "
          f"{filler_land(build_pending('azusa')[0]).name})\n")
    for cand in M.BATCH3_CANDIDATES:
        ra, rb = run(cand)
        deployed = mean(rb, "cast_test_card")
        turn = [r["test_card_turn"] for r in rb if r["test_card_turn"] < 99]
        answered = mean(rb, "test_card_answered")
        print(f"  {cand.name}  (MV {cand.mv})")
        print(f"      resolves in {deployed:6.1%} of games"
              + (f", first on turn {np.mean(turn):.1f}" if turn else "")
              + (f", answered {answered:.1%}" if answered else ""))
        for key in COUNTERS.get(cand.name, ()):
            a, b = mean(ra, key), mean(rb, key)
            # THE CONDITIONAL FIGURE IS A PAIRED DIFFERENCE ON THE SAME GAMES,
            # not a B-side level. A level would be unreadable here: the games
            # where a seven-drop resolves are the LONG games, which score
            # higher on every counter in the table whether or not the card did
            # anything, so "tokens_made is 137 when Sapling Nursery resolves"
            # says more about game length than about Sapling Nursery.
            # Restricting to those games and differencing B-A within them is
            # the same trick `experiment.analyse_conditional` uses, and the
            # unconditional column stays beside it because that -- not this --
            # is what the win rate is built from (§0p, where a conditional
            # number was quoted as if it were unconditional).
            live = [i for i in range(len(rb)) if rb[i]["cast_test_card"]]
            cond = (float(np.mean([rb[i].get(key, 0.0) - ra[i].get(key, 0.0)
                                   for i in live])) if live else 0.0)
            print(f"      {key:<22}{a:>9.2f} -> {b:>9.2f}   "
                  f"{b - a:>+8.2f}   (when it resolves: {cond:>+8.2f})")
        print()


if __name__ == "__main__":
    main()
