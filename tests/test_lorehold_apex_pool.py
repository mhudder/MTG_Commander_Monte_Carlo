#!/usr/bin/env python3
"""§0z178: Apex of Power's mana -- only from the hand, and only for the phase.

    python -m tests.test_lorehold_apex_pool
    python -m tests.test_lorehold_apex_pool --mutate   # 2 mutations, exact sets

Apex of Power (Scryfall, 2026-11-07): "Exile the top seven cards of your
library. Until end of turn, you may cast spells from among them. If this
spell was cast from your hand, add ten mana of any one color." Two defects:

  - THE HAND CLAUSE was read only as "not a copy", so every free cast from
    the library, graveyard or exile -- Galvanoth, The Dawning Archaic's and
    Goliath Daydreamer's attack triggers, discover, Sunbird's Invocation,
    Paradigm, rebound, Past in Flames, Underworld Breach -- made ten
    (`apex_from_hand`).
  - THE POOL (`g.apex_mana`, Explosive Welcome's {R}{R}{R} too) lasted the
    turn; CR 106.4 empties it at the end of each step and phase
    (`lorehold.empty_pool`, `lorehold_pool_empties`).

CASES
  A  `empty_pool` empties Apex's pool and counts it (`apex_mana_lost`,
     `apex_lost_main1`)
  B  NEIGHBOUR: `lorehold_pool_empties=False` empties nothing
  C  a turn empties the pool at upkeep, draw, main1, combat, main2, in order
  D  Apex cast from the hand: ten mana, and the seven exiled
  E  Apex cast NOT from the hand: no mana, the seven still exiled, and
     counted (`apex_not_from_hand`)
  F  NEIGHBOUR: `apex_from_hand=False` gives the non-hand cast its ten
  G  a COPY makes nothing and is not counted as a non-hand cast
  H  THE RESOLVE PATH carries the zone: `resolve_spell(..., from_hand=False)`
     makes no mana, and `from_hand=True` makes ten
  I  `empty_pool` leaves the Treasures alone

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  lorehold_pool_empties=False everywhere   -> A
  apex_from_hand=False everywhere          -> E, H

UNMUTATED (§0z15): B and F are the knobs' own neighbours; C records the
calls `your_turn` makes, so neither knob reaches it -- it fails if a
boundary's call is removed or moved; D and G hold under both knobs (a hand
cast always makes ten, a copy never does); I holds because the Treasures are
not the pool.
"""
import sys

import edhmc.lorehold as L
from edhmc.decks import lorehold_v17 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}          # a mutation's cfg overrides, under each case's own

DECK, CMD = LM.build()
APEX = next(c for c in DECK if c.name == "Apex of Power")
LANDS = [c for c in DECK if c.is_land][:7]   # seven OBJECTS (§0z112)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    """A game whose library is seven lands, so Apex exiles seven and casts
    none of them: its ten stay in the pool where a case can read them."""
    g = L.LoreholdGame(list(DECK), CMD,
                       dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                            **{**EXTRA_CFG, **cfg}), 1234)
    g.library = list(LANDS)                   # seven lands; none castable
    g.apex_mana = 0
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh()
    g.apex_mana = 10
    L.empty_pool(g, "main1")
    check("A the pool empties at main 1's end, and is counted",
          (g.apex_mana, g.m["apex_mana_lost"], g.m["apex_lost_main1"]),
          (0, 10, 10))

    g = fresh(lorehold_pool_empties=False)
    g.apex_mana = 10
    L.empty_pool(g, "main1")
    check("B lorehold_pool_empties=False empties nothing", g.apex_mana, 10)

    g = L.LoreholdGame(list(DECK), CMD,
                       dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                            **EXTRA_CFG), 7)
    for o in g.opponents:
        o.life = float(10 ** 9)
    g.opening_hand()
    seen, real = [], L.empty_pool

    def record(g, where):
        seen.append(where)
        real(g, where)

    L.empty_pool = record
    try:
        L.your_turn(g)
    finally:
        L.empty_pool = real
    check("C a turn empties at upkeep, draw, main1, combat, main2",
          seen, ["upkeep", "draw", "main1", "combat", "main2"])

    g = fresh()
    L.apex_of_power(g, from_hand=True)
    check("D a hand cast: ten mana, seven exiled",
          (g.apex_mana, g.m["apex_exiled"]), (10, 7))

    g = fresh()
    L.apex_of_power(g, from_hand=False)
    check("E not from the hand: no mana, seven exiled, counted",
          (g.apex_mana, g.m["apex_exiled"], g.m["apex_not_from_hand"]),
          (0, 7, 1))

    g = fresh(apex_from_hand=False)
    L.apex_of_power(g, from_hand=False)
    check("F apex_from_hand=False: the non-hand cast makes ten",
          g.apex_mana, 10)

    g = fresh()
    L.apex_of_power(g, is_copy=True, from_hand=True)
    check("G a copy makes nothing, and is not a non-hand cast",
          (g.apex_mana, g.m["apex_not_from_hand"]), (0, 0))

    got = []
    for zone in (False, True):
        g = fresh()
        L.resolve_spell(g, APEX, 0, from_hand=zone)
        got.append(g.apex_mana)
    check("H resolve_spell carries the zone: not hand 0, hand 10",
          got, [0, 10])

    g = fresh()
    g.apex_mana, g.treasures = 4, 3
    L.empty_pool(g, "main2")
    check("I the Treasures are not the pool", g.treasures, 3)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z178: Apex of Power's mana, from the hand and for the phase\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "lorehold_pool_empties=False everywhere":
            ({"A"}, {"lorehold_pool_empties": False}),
        "apex_from_hand=False everywhere":
            ({"E", "H"}, {"apex_from_hand": False}),
    }
    bad = 0
    for label, (want, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
