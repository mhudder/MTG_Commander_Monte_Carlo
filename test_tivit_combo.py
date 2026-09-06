#!/usr/bin/env python3
"""The Deadeye loop's mana economy, pinned as a test.

`deadeye_loop`'s docstring makes a quantitative claim about WHEN the loop pays
for itself. A docstring claiming a mechanism is not evidence of one -- that is
the project's own standing lesson, learned from two deck modules that
documented their errors as deliberate -- so the claim is checked here.

The setup is deliberately artificial: Tivit and Deadeye on the battlefield, a
fixed ten-Treasure pool, and NO LANDS. That isolates the loop's own economy
from the rest of the game, which is the only way to see whether it is
self-sustaining rather than merely spending a good board.

    python test_tivit_combo.py
"""
import sys

from edhmc.decks import tivit_v1
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.tivit import TivitGame, deadeye_loop
from edhmc import voting as V

DECK, CMD = tivit_v1.build()
BY_NAME = {c.name: c for c in DECK}
START = 10


def setup(extras):
    g = TivitGame(DECK, CMD, dict(DEFAULT_CFG, turns=20, watch=frozenset()), 1)
    g.board.append(Permanent(card=CMD, sick=False))
    g.commander_cast = True
    g.board.append(Permanent(card=BY_NAME["Deadeye Navigator"], sick=False))
    for name in extras:
        g.board.append(Permanent(card=BY_NAME[name], sick=False))
    g.tokens["Treasure"] = START
    return g


# (extras, expect_self_sustaining, why)
CASES = [
    ([], False,
     "2 votes x 1 kind = 2, and the activation costs 2. Exactly break even."),
    (["Academy Manufactor"], True,
     "2 votes x 3 kinds = 6 Treasures for 2 mana."),
    (["Ballot Broker"], True,
     "3 votes x 1 kind = 3 Treasures for 2 mana -- an extra vote is enough "
     "ON ITS OWN, without Manufactor."),
    (["Ballot Broker", "Brago's Representative"], True,
     "4 votes x 1 kind = 4."),
    (["Academy Manufactor", "Ballot Broker"], True,
     "3 votes x 3 kinds = 9, the fastest configuration."),
]


def main():
    cap = DEFAULT_CFG.get("combo_cap", 40)
    failures = []
    print(f"Tivit + Deadeye, {START} Treasures, no lands. "
          f"combo_cap={cap}.\n")
    print(f"  {'board':<42}{'votes':>6}{'iters':>7}{'treasure':>10}   verdict")
    for extras, expect, why in CASES:
        g = setup(extras)
        votes = V.my_votes(g)
        deadeye_loop(g)
        iters = g.m["combo_iterations"]
        end = g.tokens["Treasure"]
        sustaining = iters >= cap
        label = "+".join(x.split(",")[0] for x in extras) or "(Tivit alone)"
        ok = sustaining == expect
        verdict = ("self-sustaining" if sustaining else "stops") + \
                  ("" if ok else "   <-- UNEXPECTED")
        print(f"  {label:<42}{votes:>6}{iters:>7}"
              f"{START:>6} ->{end:<4} {verdict}")
        if not ok:
            failures.append((label, expect, sustaining, why))
        if not sustaining and end > START:
            failures.append((label, "no profit when it stops", end, why))

    print()
    for extras, _expect, why in CASES:
        label = "+".join(x.split(",")[0] for x in extras) or "(Tivit alone)"
        print(f"  {label:<42}{why}")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("   ", f)
        return 1
    print("\nOK -- the loop is self-sustaining exactly where the docstring "
          "says, by BOTH routes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
