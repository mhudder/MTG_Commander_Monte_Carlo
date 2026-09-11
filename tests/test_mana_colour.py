#!/usr/bin/env python3
"""Pin colour-correct payment: the engine taps what it proved it could tap.

    python -m tests.test_mana_colour
    python -m tests.test_mana_colour --mutate

WHY THIS EXISTS. `can_pay` has always chosen a colour-correct assignment and
returned the exact indices it chose; `spend` read only their COUNT and tapped
that many permanents cheapest-to-lose first. So the engine proved one payment
and made another, and which land ended up tapped was decided by the order the
lands happened to be played. §0z8.

Three properties are pinned here, and the third is the one that makes the first
two worth having:

  1. The assignment is HONOURED -- the permanents tapped are the ones chosen.
  2. Generic is paid from the MOST PLENTIFUL colour, so a lone source of a
     colour is not spent on a generic cost while a spare of another colour
     sits untapped.
  3. BOARD ORDER DOES NOT MATTER. The same position with the lands played in a
     different order gives the same answer. That is the invariant the old code
     broke, and it is the one a future change is most likely to break again.

And one property that must NOT be lost: lands are still tapped before mana
creatures, so a dork can attack (`tap_reluctance`).

`--mutate` restores the count-based rule and asserts the colour cases fail.
"""
import random
import sys

from edhmc.engine import (Game, Card, Permanent, can_pay, available_mana,
                          spend, ManaUnits)
from edhmc.experiment import DEFAULT_CFG
import edhmc.engine as EN

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(name, produces):
    return Card(name=name, types=frozenset({"Land"}), is_land=True,
                produces=frozenset(produces))


def dork(name, colors):
    return Card(name=name, types=frozenset({"Creature"}), power=2, toughness=2,
                mana_ability=(1, frozenset(colors)))


def game(perms, hand=()):
    g = Game([], Card(name="cmd", types=frozenset({"Creature"})),
             dict(DEFAULT_CFG, turns=20, watch=frozenset()),
             random.Random(1), 1)
    for c in perms:
        g.board.append(Permanent(card=c, tapped=False, sick=False))
    g.hand = list(hand)
    return g


def untapped(g):
    return sorted(p.card.name for p in g.board if not p.tapped)


def main():
    if MUTATE:
        # The pre-2026-09-11 rule: tap by COUNT, cheapest-to-lose first,
        # ignoring which units can_pay actually assigned.
        def count_based(g, pay_idx, units):
            n = len(pay_idx)
            g.m["mana_spent"] += n
            sources = [p for p in g.board
                       if not p.tapped and (p.card.is_land or p.card.mana_ability)]
            sources.sort(key=lambda p: EN.tap_reluctance(g, p))
            left = n
            for p in sources:
                if left <= 0:
                    break
                p.tapped = True
                left -= 1
        EN.spend = count_based
        print("MUTATED: spend taps by count again\n")
    else:
        EN.spend = EN.__dict__["spend"]

    sp = EN.spend

    # 1. A lone {W} source survives a generic cost when a spare {R} exists.
    g = game([land("Plains", "W"), land("Mountain", "R"), land("Mountain", "R")])
    units = available_mana(g)
    sp(g, can_pay({"gen": 2}, units), units)
    check("paying {2} keeps the only Plains and taps two Mountains",
          untapped(g), ["Plains"])

    # 2. THE SAME POSITION, LANDS PLAYED IN A DIFFERENT ORDER. This is the
    # invariant: board order is not a game rule.
    g2 = game([land("Mountain", "R"), land("Plains", "W"), land("Mountain", "R")])
    units2 = available_mana(g2)
    sp(g2, can_pay({"gen": 2}, units2), units2)
    check("...and board order does not change that", untapped(g2), ["Plains"])

    # 3. A coloured pip still takes the source that can pay it.
    g = game([land("Plains", "W"), land("Mountain", "R"), land("Mountain", "R")])
    units = available_mana(g)
    sp(g, can_pay({"gen": 1, "R": 1}, units), units)
    check("paying {1}{R} with a white card in hand is not checked here; "
          "the R pip must come from a Mountain",
          any(p.card.name == "Mountain" and p.tapped for p in g.board), True)

    # 4. THE HAND BREAKS A TRUE TIE. One Plains, two Mountains, paying {1}{R}
    # leaves one of each -- scarcity cannot choose, so the cards in hand do.
    white = Card(name="white card", types=frozenset({"Creature"}),
                 cost={"gen": 1, "W": 1}, power=2, toughness=2)
    kept = {}
    for label, hand in (("no white card", []), ("a white card", [white])):
        g = game([land("Plains", "W"), land("Mountain", "R"),
                  land("Mountain", "R")], hand)
        units = available_mana(g)
        sp(g, can_pay({"gen": 1, "R": 1}, units), units)
        kept[label] = "Plains" in untapped(g)
    check("a white card in hand is what keeps the Plains on a true tie",
          (kept["no white card"], kept["a white card"]), (False, True))

    # 5. THE TAP ORDER SURVIVES. A land is spent before a mana creature, so the
    # dork can still attack -- the policy `spend` used to own and `can_pay`
    # now enforces through tap_reluctance.
    g = game([land("Forest", "G"), dork("Llanowar Elves", "G")])
    units = available_mana(g)
    sp(g, can_pay({"gen": 1}, units), units)
    check("a land is tapped before a mana creature", untapped(g),
          ["Llanowar Elves"])

    # 6. Duals are saved for last: with a dual and two basics, a generic cost
    # should not burn the dual.
    g = game([land("Sacred Foundry", "RW"), land("Plains", "W"),
              land("Mountain", "R")])
    units = available_mana(g)
    sp(g, can_pay({"gen": 1}, units), units)
    check("a generic cost does not burn the dual",
          "Sacred Foundry" in untapped(g), True)

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        # FOUR, not the two predicted. Writing this list wrong first time is
        # the mutation check earning its keep, and the two extra failures are
        # the interesting ones:
        #
        #   BOARD ORDER genuinely decided the answer under the old rule --
        #   this case was written expecting the mutant to agree by luck, and
        #   it does not. Reversing the order reverses which land survives.
        #   THE DUAL WAS BURNED TOO. `can_pay` has always saved duals for
        #   last, and the old `spend` then tapped the first land in board
        #   order anyway -- so the one piece of colour reasoning the codebase
        #   already had was being discarded as well.
        expected = {
            "paying {2} keeps the only Plains and taps two Mountains",
            "...and board order does not change that",
            "a white card in hand is what keeps the Plains on a true tie",
            "a generic cost does not burn the dual",
        }
        actual = set(FAIL)
        if actual == expected:
            print("  MUTATION CHECK OK -- exactly the four cases that depend "
                  "on the fix failed. The two that did NOT are the tap order "
                  "(lands before dorks) and the coloured pip itself, which "
                  "the old rule got right and this change preserves.")
            return 0
        print(f"  MUTATION CHECK FAILED\n    expected {sorted(expected)}\n"
              f"    actual   {sorted(actual)}")
        return 1
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
