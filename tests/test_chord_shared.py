#!/usr/bin/env python3
"""§0z213: Chord of Calling is one rule in every deck -- convoke and an X
chosen for its target (`engine.convoke_pool`, `engine.x_plan`), as trostani
played it, now azusa's too.

    python -m tests.test_chord_shared
    python -m tests.test_chord_shared --mutate   # 4 mutations, exact sets

    "Convoke. Search your library for a creature card with mana value X or
    less, put it onto the battlefield, then shuffle."  ({X}{G}{G}{G})

Azusa's old rule (`chord_convoke=False`) cast it at a fixed {4}{G}{G}{G}
with no convoke and took the biggest creature of mana value 4 or less
(§0z197 A7, §0z209 item 8). Trostani's methods are the shared functions
now; that they did not change is the identity check's, not this test's.

Each case builds an azusa game with an empty battlefield and sets the
lands, the creatures and the library by hand.

CASES
  A  before combat, convoke offers only the SICK creatures: two sick, one
     not, and a sick Dryad Arbor (a land) -- two units
  B  after combat, every untapped creature but the land: a tapped one is
     not offered -- three units
  C  three Forests and four convoking creatures (seven mana): of
     Craterhoof (11), Avenger (10) and Eternal Witness (6), the Witness
  D  three Forests and eight (eleven): Craterhoof, priority 9
  E  a target below `tutor_floor` (Quirion Ranger, 4) is never planned
  F  the cast: Chord in hand, three Forests, three sick creatures, Augur of
     Autumn the library's creature -- Augur enters, the three creatures
     are tapped, `chord_convoked` 3, `chord_x` 3, the Chord in the graveyard
  G  NEIGHBOUR: `chord_convoke=False` is the old rule -- seven Forests and
     Augur and Oracle of Mul Daya in the library: Oracle, the biggest of
     mana value 4, and no creature tapped

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  chord_convoke=False everywhere                 -> F
  convoke offers the untapped non-sick ones before combat -> A
  convoke_pool without the land guard            -> A, B
  tutor_floor 0                                  -> E

UNMUTATED (§0z15): G is the switch's neighbour. C and D are the X choice,
which the shared function moved without changing; their own mutation would
be a different ranking, which is a policy question measured on its own
(§0z213), not a defect this test should call a failure.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.azusa import AzusaGame
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.commander_cast = True
    g.bonus_mana = []
    return g


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def forest(g):
    return Permanent(card=take(g, "Forest"), sick=False)


def token(sick=True, tapped=False):
    card = Card(name="Insect token", types=frozenset({"Creature"}),
                power=1, toughness=1)
    return Permanent(card=card, sick=sick, tapped=tapped, is_token=True)


def board(g, forests=0, creatures=()):
    for _ in range(forests):
        g.board.append(forest(g))
    for p in creatures:
        g.board.append(p)


def library(g, names):
    g.library[:] = [take(g, n) for n in names]


def extra(g, units, precombat):
    return len(AZ.convoke_pool(g, units, precombat)) - len(units)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh()
    arbor = Permanent(card=take(g, "Dryad Arbor"), sick=True)
    board(g, 3, [token(), token(), token(sick=False), arbor])
    check("A before combat: the two sick creatures, not the land",
          extra(g, g.available_mana(), True), 2)

    g = fresh()
    arbor = Permanent(card=take(g, "Dryad Arbor"), sick=True)
    board(g, 3, [token(), token(), token(sick=False), token(tapped=True),
                 arbor])
    check("B after combat: every untapped creature but the land",
          extra(g, g.available_mana(), False), 3)

    g = fresh()
    chord = take(g, "Chord of Calling")
    board(g, 3, [token() for _ in range(4)])
    library(g, ["Sol Ring", "Eternal Witness", "Avenger of Zendikar",
                "Craterhoof Behemoth"])
    plan = AZ.x_plan(g, chord, AZ.convoke_pool(g, g.available_mana(), True))
    check("C seven mana: the Witness, X 3",
          (plan[0].name, plan[1]), ("Eternal Witness", {"G": 3, "gen": 3}))

    g = fresh()
    chord = take(g, "Chord of Calling")
    board(g, 3, [token() for _ in range(8)])
    library(g, ["Sol Ring", "Eternal Witness", "Avenger of Zendikar",
                "Craterhoof Behemoth"])
    plan = AZ.x_plan(g, chord, AZ.convoke_pool(g, g.available_mana(), True))
    check("D eleven mana: Craterhoof", plan[0].name, "Craterhoof Behemoth")

    g = fresh()
    chord = take(g, "Chord of Calling")
    board(g, 3, [token() for _ in range(8)])
    library(g, ["Sol Ring", "Quirion Ranger"])
    check("E below tutor_floor: no plan",
          AZ.x_plan(g, chord, AZ.convoke_pool(g, g.available_mana(), True)),
          None)

    g = fresh()
    g.hand[:] = [take(g, "Chord of Calling")]
    bodies = [token() for _ in range(3)]
    board(g, 3, bodies)
    library(g, ["Sol Ring", "Augur of Autumn"])
    g.main_phase()
    check("F the cast: Augur enters, three creatures convoked, X 3",
          ("Augur of Autumn" in [p.card.name for p in g.board],
           [p.tapped for p in bodies], g.m["chord_convoked"],
           g.m["chord_x"], [c.name for c in g.graveyard]),
          (True, [True, True, True], 3, 3, ["Chord of Calling"]))

    g = fresh(chord_convoke=False)
    g.hand[:] = [take(g, "Chord of Calling")]
    bodies = [token() for _ in range(3)]
    board(g, 7, bodies)
    library(g, ["Sol Ring", "Augur of Autumn", "Oracle of Mul Daya"])
    g.main_phase()
    check("G chord_convoke=False: Oracle (mana value 4), nobody convoked",
          ("Oracle of Mul Daya" in [p.card.name for p in g.board],
           [p.tapped for p in bodies]),
          (True, [False, False, False]))
    return set(FAIL)


def _no_sick_rule(g, units, precombat):
    return EN.convoke_pool(g, units, False)


def _no_land_guard(g, units, precombat):
    extra_, owners = [], []
    for p in g.board:
        if p.tapped or not OPP.is_creature_now(g, p):
            continue
        if p.card.mana_ability or p.card is g.commander:
            continue
        if precombat and not p.sick:
            continue
        extra_.append(frozenset(EN.colours_of(p.card) | {"C"}))
        owners.append(p)
    return EN.ManaUnits(list(units) + extra_, units.owners + owners,
                        units.weights + [(9, 0, 0)] * len(extra_),
                        units.legacy, units.surplus)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z213: Chord of Calling, one rule\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "chord_convoke=False everywhere":
            ({"F"}, None, {"chord_convoke": False}),
        "convoke offers the non-sick ones before combat":
            ({"A"}, _no_sick_rule, {}),
        "convoke_pool without the land guard":
            ({"A", "B"}, _no_land_guard, {}),
        "tutor_floor 0":
            ({"E"}, None, {"tutor_floor": 0}),
    }
    bad = 0
    for label, (want, fn, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real = AZ.convoke_pool
        if fn is not None:
            AZ.convoke_pool = fn
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            AZ.convoke_pool = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
