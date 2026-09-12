#!/usr/bin/env python3
"""Pin the two cheap closures from the KNOWN_ISSUES review: §0i and §0f.

    python -m tests.test_lorehold_0f_0i
    python -m tests.test_lorehold_0f_0i --mutate

1. TALISMAN OF CONVICTION IS CHARGED (§0i).
   "{T}: Add {C}.  {T}: Add {R} or {W}. This artifact deals 1 damage to you."
   Charged only when `can_pay` assigned it to an {R} or {W} PIP; a Talisman
   spent on a generic cost was tapped for {C} and is free. §0i called this
   infeasible because "`spend()` does not record which colour a source
   produced" -- true of the count-based payment, and untrue since §0z8, which
   made both the owner and the assignment available at every payment site.
   `engine.pip_assignment` reads the pip off `can_pay`'s existing return value
   rather than making a second copy of its choice.

2. BORROWED KNOWLEDGE DISCARDS (§0f).
   "Choose one - * Discard your hand, then draw cards equal to the number of
   cards in target opponent's hand. * Discard your hand, then draw cards equal
   to the number of cards discarded this way." Mode 2, because mode 1 has no
   opponent hand to count (§4).

   NOTE WHAT §0f GETS WRONG: it prescribes reusing the `wheel` script. A wheel
   draws a flat 7 and this draws only what it discarded, so `wheel` would
   OVERSTATE the card. The case below pins the difference.

`--mutate` restores `charge_life_costs=False` and
`borrowed_knowledge_discard=False` and asserts exactly the dependent cases
fail.
"""
import random
import sys

import edhmc.lorehold as L
from edhmc.engine import Card, Permanent, pip_assignment, coloured_tap_life
from edhmc.decks.lorehold_v16 import build
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
MUT = {"charge_life_costs": False, "borrowed_knowledge_discard": False,
       "apex_ten_mana": False, "mother_lode_discover": False}
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


DECK, CMD = build()
TALISMAN = [c for c in DECK if c.name == "Talisman of Conviction"][0]
BORROWED = [c for c in DECK if c.name == "Borrowed Knowledge"][0]
APEX = [c for c in DECK if c.name == "Apex of Power"][0]
LODE = [c for c in DECK if c.name == "Hit the Mother Lode"][0]


def game(**extra):
    cfg = dict(DEFAULT_CFG, **(MUT if MUTATE else {}), **extra)
    g = L.LoreholdGame(list(DECK), CMD, cfg, 1)
    g.hand = []
    g.board = L.Board()
    return g


def mountain():
    return Card(name="Mountain", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"R"}))


def put(g, card, tapped=False):
    g.board.append(Permanent(card=card, tapped=tapped, sick=False))


# ---------------------------------------------------------------------------
# 1. Talisman of Conviction
# ---------------------------------------------------------------------------

def pay_and_measure(cost, extra_lands=0):
    """Pay `cost` off a Talisman plus `extra_lands` Mountains; return life lost."""
    g = game()
    put(g, TALISMAN)
    for _ in range(extra_lands):
        put(g, mountain())
    before = g.your_life
    units = L.mana_units(g)
    paid = L.pay(g, cost, units)
    assert paid is not None, f"could not pay {cost}"
    return round(before - g.your_life, 3)


def test_talisman():
    print("\nTalisman of Conviction: 1 damage for a COLOURED tap only")
    # {R} with nothing else on the board: the Talisman must make the R.
    check("paying {R} off the Talisman alone costs 1 life",
          pay_and_measure({"R": 1}), 1.0)
    check("paying {W} off the Talisman alone costs 1 life",
          pay_and_measure({"W": 1}), 1.0)
    # Generic: a pilot taps it for {C}, which is the painless mode.
    check("paying {1} off the Talisman alone is FREE ({C} mode)",
          pay_and_measure({"gen": 1}), 0.0)
    # A colourless pip is the {C} mode too.
    check("paying {C} off the Talisman alone is FREE",
          pay_and_measure({"C": 1}), 0.0)
    # With a Mountain available, can_pay should prefer the Mountain for the
    # R pip -- it is the more constrained source -- so nothing is paid.
    check("with a Mountain on board, {R} comes off the LAND and costs nothing",
          pay_and_measure({"R": 1}, extra_lands=1), 0.0)
    # ...and the Talisman then covers the generic, still for free.
    check("{1}{R} taps the Mountain for the pip and the Talisman for {C}",
          pay_and_measure({"gen": 1, "R": 1}, extra_lands=1), 0.0)


def test_pip_assignment_is_positional():
    """The decoder, on its own: coloured pips first, generic falls off."""
    print("\n`pip_assignment` recovers the pip from can_pay's return value")
    check("{W}{R} + {2} decodes to the two pips and drops the generic",
          pip_assignment({"W": 1, "R": 1, "gen": 2}, [10, 11, 12, 13]),
          [(10, "W"), (11, "R")])
    check("a pure generic cost decodes to nothing",
          pip_assignment({"gen": 3}, [4, 5, 6]), [])
    check("COLORS order is W,U,B,R,G,C, not cost-dict order",
          [p for _, p in pip_assignment({"R": 1, "W": 1}, [0, 1])],
          ["W", "R"])


def test_pool_without_owners_is_safe():
    """A caller-built pool has no permanents behind it and must not crash."""
    print("\na pool with no owners degrades to zero, not to an exception")
    g = game()
    check("coloured_tap_life on a plain list returns 0.0",
          coloured_tap_life(g, {"R": 1}, [0], [frozenset({"R"})]), 0.0)


# ---------------------------------------------------------------------------
# 2. Borrowed Knowledge
# ---------------------------------------------------------------------------

def cast_borrowed(hand_size):
    """Resolve Borrowed Knowledge with `hand_size` other cards in hand."""
    g = game()
    filler = [Card(name=f"filler{i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1}) for i in range(hand_size)]
    g.hand = list(filler)
    yard_before = len(g.graveyard)
    lib_before = len(g.library)
    L.apply_spell_effects(g, BORROWED)
    return dict(hand=len(g.hand),
                binned=len(g.graveyard) - yard_before,
                drawn=lib_before - len(g.library))


def test_borrowed_knowledge():
    print("\nBorrowed Knowledge: discard N, draw N")
    r = cast_borrowed(4)
    check("a hand of 4 is binned", r["binned"], 4)
    check("...and exactly 4 are drawn back (NET ZERO, unlike a wheel)",
          r["drawn"], 4)
    check("...leaving a hand of 4", r["hand"], 4)

    r0 = cast_borrowed(0)
    check("an empty hand discards nothing and draws nothing",
          (r0["binned"], r0["drawn"]), (0, 0))

    # THE POINT OF THE FIX, and what §0f's `wheel` prescription would break.
    r7 = cast_borrowed(1)
    check("a hand of 1 draws 1, NOT the 7 the `wheel` script would give",
          r7["drawn"], 1)


def test_the_graveyard_is_the_point():
    """`draw2` put nothing in the yard; this deck eats the yard."""
    print("\nthe half `draw2` never modelled: cards reaching the graveyard")
    r = cast_borrowed(5)
    check("5 cards reach the graveyard for Bombardment/Mastery/Archaic",
          r["binned"], 5)


def test_apex_of_power():
    """"Exile the top seven... If this spell was cast FROM YOUR HAND, add ten
    mana of any one color." It was `draw4`: four cards and no mana."""
    print("\nApex of Power: seven exiled, ten mana of one colour")
    g = game()
    lib = len(g.library)
    L.apply_spell_effects(g, APEX)
    check("it exiles seven off the top", lib - len(g.library) >= 7, True)
    check("...and adds ten mana", g.m.get("apex_mana_made", 0), 10)
    check("the colour is ONE colour, not a wildcard", g.apex_color in ("R", "W"), True)
    check("it casts from among the exiled seven",
          g.m.get("apex_casts", 0) > 0, True)
    check("uncast cards stay EXILED, not drawn (hand is untouched)",
          len(g.hand), 0)

    # "If this spell was cast from your hand" -- a copy exiles and gets nothing.
    gc = game()
    L.apply_spell_effects(gc, APEX, is_copy=True)
    check("a COPY exiles seven and gets NO mana",
          (gc.m.get("apex_exiled", 0), gc.m.get("apex_mana_made", 0)), (7, 0))


def test_mother_lode():
    """"Discover 10 ... create a number of TAPPED Treasure tokens equal to
    the difference." It was a flat 5, untapped."""
    print("\nHit the Mother Lode: Discover 10, and the Treasures enter tapped")
    g = game()
    L.apply_spell_effects(g, LODE)
    mv = g.m.get("discover_mv", 0)
    check("it free-casts a nonland of mana value <= 10",
          g.m.get("discover_casts", 0), 1)
    check("Treasures = 10 - that card's mana value",
          g.tapped_treasures, int(10 - mv))
    check("...and they are TAPPED, so they are not mana this turn",
          g.treasures, 0)
    # The merge itself, not the end-of-turn balance: once untapped they are
    # ordinary Treasures and the turn is free to spend them, which is the
    # whole point of the delay.
    check("the tapped pile is non-empty before the untap step",
          g.tapped_treasures > 0, True)
    L.take_turn(g)
    check("the untap step moves them into the real Treasure pile",
          g.tapped_treasures, 0)


def main():
    print(__doc__.split("\n\n")[0])
    if MUTATE:
        print("\nMUTATION RUN: charge_life_costs=False, "
              "borrowed_knowledge_discard=False\n")
    test_talisman()
    test_pip_assignment_is_positional()
    test_pool_without_owners_is_safe()
    test_borrowed_knowledge()
    test_the_graveyard_is_the_point()
    test_apex_of_power()
    test_mother_lode()

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        # EIGHT, not the seven predicted, and the extra one is the sharpest
        # case in the file. "An empty hand discards nothing and draws nothing"
        # was written expecting the mutant to agree by luck; it does not,
        # because `draw2` drew two cards REGARDLESS OF HAND SIZE. The old
        # script was not a weak approximation of this card, it was a different
        # card -- one that draws off an empty hand, which is the one board
        # state where Borrowed Knowledge does literally nothing.
        #
        # Everything else that passes under the mutant passes for a reason:
        # `pip_assignment` is pure decoding and reads no cfg, the owner-less
        # pool already returned 0.0, and the FREE Talisman cases were free
        # under both rules -- which is the fix's whole claim, that it charges
        # the coloured tap and nothing else.
        expected = {
            "paying {R} off the Talisman alone costs 1 life",
            "paying {W} off the Talisman alone costs 1 life",
            "a hand of 4 is binned",
            "...and exactly 4 are drawn back (NET ZERO, unlike a wheel)",
            "...leaving a hand of 4",
            "an empty hand discards nothing and draws nothing",
            "a hand of 1 draws 1, NOT the 7 the `wheel` script would give",
            "5 cards reach the graveyard for Bombardment/Mastery/Archaic",
            # Apex: `draw4` exiles nothing, adds no mana, casts nothing, and
            # puts four cards in HAND -- so every one of these reverses.
            "it exiles seven off the top",
            "...and adds ten mana",
            "it casts from among the exiled seven",
            "uncast cards stay EXILED, not drawn (hand is untouched)",
            "a COPY exiles seven and gets NO mana",
            # Mother Lode: the flat 5 Treasures discovers nothing and enters
            # UNTAPPED, so the tapped pile stays empty.
            "it free-casts a nonland of mana value <= 10",
            "Treasures = 10 - that card's mana value",
            "...and they are TAPPED, so they are not mana this turn",
            "the tapped pile is non-empty before the untap step",
        }
        actual = set(FAIL)
        if actual == expected:
            print("  MUTATION CHECK OK -- exactly the 17 cases that read the "
                  "four knobs failed, including the one this list got wrong "
                  "first time: `draw2` drew two cards off an EMPTY hand, "
                  "where the real card draws none. Three stayed passing on "
                  "purpose: the Talisman's FREE cases were free under both "
                  "rules (the fix charges the coloured tap and nothing else), "
                  "`pip_assignment` reads no cfg at all, and Apex's colour is "
                  "a single colour either way because `apex_color` defaults "
                  "to R.")
            return 0
        print(f"  MUTATION CHECK FAILED\n"
              f"    only in expected: {sorted(expected - actual)}\n"
              f"    only in actual:   {sorted(actual - expected)}")
        return 1
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
