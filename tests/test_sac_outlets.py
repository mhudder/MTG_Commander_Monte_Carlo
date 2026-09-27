#!/usr/bin/env python3
"""Rendmaw's sacrifice outlets pay their costs (§0z70).

    python -m tests.test_sac_outlets
    python -m tests.test_sac_outlets --mutate   # 4 mutations, exact sets

    Village Rites   {B} Instant. As an additional cost to cast this spell,
                    sacrifice a creature. Draw two cards.
    Dockside Chef   {1}{B}, Sacrifice an artifact or creature: Draw a card.
    Grim Backwoods  Land. {T}: Add {C}. {2}{B}{G}, {T}, Sacrifice a creature:
                    Draw a card.                 (Scryfall, verified 2026-09-27)

WHAT WAS WRONG. Village Rites and Dockside Chef checked that the activation
pool was non-empty and spent none of it -- free in this model -- and Village
Rites never reached the graveyard. Grim Backwoods was named in a comment as
"the same shape" and implemented nowhere. `engine.pay_from` is the one rule
now: `can_pay`, `spend` (which taps lands and sacrifices Treasures), and the
used units popped so the next ability cannot reuse them.

CASES
  A  Village Rites with a Swamp and a token: cast, the Swamp tapped, the card
     in the graveyard, two cards drawn, the token gone
  B  with only a Forest: not cast
  C  with no land and one Treasure: cast, the Treasure spent
  D  Dockside Chef with a Swamp and a Forest: activated, both tapped, one card
  E  with a Swamp alone: not activated
  F  Grim Backwoods with Swamp, Forest and two Wastes: activated, the Backwoods
     and all four lands tapped, one card
  G  with Swamp, Forest and ONE Waste: not activated -- its own {C} is part
     of the cost -- and left untapped
  H  `sac_outlets_pay=False`: the old free Village Rites (cast off a Forest)
     and no Grim Backwoods at all
  I  TIMING (§0z73), default "end": `activations` alone leaves Village
     Rites in hand; the end step casts it
  J  `sac_outlets_timing="main"`: `activations` casts it
  K  `main_phase` never casts Village Rites -- it would resolve as a blank.
     The first end-step measurement counted ZERO Rites cast a game: the
     main phase had already spent it.

  Cases A-G drive a whole turn's outlets: `activations`, then
  `end_step_outlets` -- which is where they run by default since §0z73.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pay_from ignores the cost (pays nothing, always succeeds) -> A, B, C, D, E, F, G
  the Backwoods may pay with its own mana                    -> F, G
  the outlets always run early (timing ignored)              -> I
  main_phase may cast Village Rites                          -> K
      (F: predicted, not certain -- whether a Waste is left untapped depends
      on how `can_pay` breaks a tie between three colourless units)

UNMUTATED (§0z15): the graveyard in A and the knob gate in H are inline
with no seam; H is the neighbour that proves the old behaviour is still
reachable.
"""
import random
import sys

import edhmc.engine as EN
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = RM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return next(c for c in DECK if c.name == name)


def land(name, colour):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({colour}))


def token():
    return EN.Permanent(card=EN.Card(name="Saproling token",
                                     types=frozenset({"Creature"}),
                                     power=1, toughness=1),
                        sick=False, is_token=True)


def game(*perms, hand=(), treasures=0, **cfg):
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, turns=20, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = list(hand), []
    g.library = [EN.Card(name=f"F{i}", types=frozenset({"Sorcery"}),
                         cost={"gen": 9}) for i in range(20)]
    g.treasures = treasures
    g.turn = 6
    for p in perms:
        g.board.append(p if isinstance(p, EN.Permanent)
                       else EN.Permanent(card=p, sick=False))
    return g


def turn(g):
    EN.activations(g)
    EN.end_step_outlets(g)


def lands_tapped(g, name):
    return [p.tapped for p in g.board if p.card.name == name]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    rites = card("Village Rites")
    g = game(land("Swamp", "B"), token(), hand=[rites])
    turn(g)
    check("A Rites: cast, Swamp tapped, graveyard, +2 cards, token gone",
          (lands_tapped(g, "Swamp"), rites in g.graveyard, len(g.hand),
           any(p.is_token for p in g.board)), ([True], True, 2, False))
    g = game(land("Forest", "G"), token(), hand=[rites])
    turn(g)
    check("B Rites with only a Forest: not cast", rites in g.hand, True)
    g = game(token(), hand=[rites], treasures=1)
    turn(g)
    check("C Rites off a Treasure: cast, Treasure spent",
          (rites in g.graveyard, g.treasures), (True, 0))
    g = game(card("Dockside Chef"), land("Swamp", "B"), land("Forest", "G"),
             token())
    turn(g)
    check("D Chef with Swamp + Forest: both tapped, one card",
          (lands_tapped(g, "Swamp") + lands_tapped(g, "Forest"), len(g.hand)),
          ([True, True], 1))
    g = game(card("Dockside Chef"), land("Swamp", "B"), token())
    turn(g)
    check("E Chef with a Swamp alone: not activated", len(g.hand), 0)
    bw = card("Grim Backwoods")
    g = game(bw, land("Swamp", "B"), land("Forest", "G"), land("Wastes", "C"),
             land("Wastes", "C"), token())
    turn(g)
    check("F Backwoods + four lands: activated, all tapped, one card",
          (lands_tapped(g, "Grim Backwoods"),
           lands_tapped(g, "Swamp") + lands_tapped(g, "Forest")
           + lands_tapped(g, "Wastes"), len(g.hand)),
          ([True], [True] * 4, 1))
    g = game(bw, land("Swamp", "B"), land("Forest", "G"), land("Wastes", "C"),
             token())
    turn(g)
    check("G Backwoods + three lands: not activated, untapped",
          (len(g.hand), lands_tapped(g, "Grim Backwoods")), (0, [False]))
    g = game(land("Forest", "G"), token(), hand=[rites], sac_outlets_pay=False)
    turn(g)
    g2 = game(bw, land("Swamp", "B"), land("Forest", "G"), land("Wastes", "C"),
              land("Wastes", "C"), token(), sac_outlets_pay=False)
    turn(g2)
    check("H knob off: free Rites off a Forest, no Backwoods",
          (rites in g.hand, g2.m["backwoods_activations"]), (False, 0))
    g = game(land("Swamp", "B"), token(), hand=[rites])
    EN.activations(g)
    early = rites in g.hand
    EN.end_step_outlets(g)
    check("I default timing: not in activations, cast at the end step",
          (early, rites in g.graveyard), (True, True))
    g = game(land("Swamp", "B"), token(), hand=[rites],
             sac_outlets_timing="main")
    EN.activations(g)
    check("J timing main: cast inside activations", rites in g.graveyard, True)
    g = game(land("Swamp", "B"), hand=[rites])
    g.commander_cast = True
    EN.main_phase(g)
    check("K main_phase does not cast Village Rites", rites in g.hand, True)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Rendmaw's sacrifice outlets pay their costs\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(EN, n) for n in ("pay_from", "backwoods_pool",
                                        "outlets_early", "main_phase_may_cast")}
    muts = {
        "pay_from ignores the cost":
            ({"A", "B", "C", "D", "E", "F", "G"}, "pay_from",
             lambda g, units, cost: True),
        "the Backwoods may pay with its own mana":
            ({"F", "G"}, "backwoods_pool", lambda units, land: units),
        "the outlets always run early":
            ({"I"}, "outlets_early", lambda g: True),
        "main_phase may cast Village Rites":
            ({"K"}, "main_phase_may_cast", lambda g, c: True),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(EN, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(EN, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
