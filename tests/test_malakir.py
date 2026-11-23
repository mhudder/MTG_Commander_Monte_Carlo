#!/usr/bin/env python3
"""§0z251: Malakir Rebirth's front face is a protection spell, held for the
pod's removal -- it was cast into nothing in shilgengar's main phase.

    python -m tests.test_malakir
    python -m tests.test_malakir --mutate   # 4 mutations, exact sets

    "Choose target creature. You lose 2 life. Until end of turn, that
    creature gains 'When this creature dies, return it to the battlefield
    tapped under its owner's control.'"  ({B}, Instant; Scryfall 2026-11-23)

`opponents.PROTECTION` prices it as "indestructible" for one creature
against spot removal, and charges its 2 life (`protection_life`); it is on
shilgengar's `protection_cards` unless `malakir_text=False`.

CASES
  A  a pure response: never cast in a main phase (`pure_response`)
  B  NEIGHBOUR: malakir_text=False -- not a protection card, not pure
  C  the pod's spot removal at your creature, a Swamp untapped: answered
     "indestructible", 2 life paid, the card in the graveyard
  D  ... at a noncreature permanent: not answered
  E  ... a wrath: not answered (one creature, no wrath entry)
  F  the main phase, Malakir in hand and {B} untapped: held, not cast
  G  NEIGHBOUR: malakir_text=False -- the old rule casts it (the blank)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  PROTECTION without Malakir's entry          -> A, C, F
  its "creature" flag dropped                 -> D
  its life cost dropped                       -> C
  protection_life charges nothing             -> C

UNMUTATED (§0z15): B and G are the switch's neighbour; E is the absent
wrath entry, which a mutation would turn into a different card.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as S
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = build_pending("shilgengar")
MALAKIR = next(c for c in DECK if c.name == S.MALAKIR)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def swamp():
    return Permanent(card=Card(name="Swamp", types=frozenset({"Land"}),
                               is_land=True, produces=frozenset("B")),
                     sick=False)


def fresh(**cfg):
    g = S.ShilgengarGame(list(DECK), CMD,
                         dict(DEFAULT_CFG, turns=20, watch=frozenset(), **cfg),
                         1)
    g.board = EN.Board()
    g.board.append(swamp())
    g.hand, g.graveyard = [MALAKIR], []
    g.library = [Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                      cost={"gen": 9}) for i in range(20)]
    g.turn, g.commander_cast, g.your_life = 2, True, 40.0
    return g


def bear():
    return Permanent(card=Card(name="Test Bear", types=frozenset({"Creature"}),
                               power=2, toughness=2), sick=False)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh()
    check("A a pure response", OPP.pure_response(g, MALAKIR), True)
    g = fresh(malakir_text=False)
    check("B malakir_text=False: not pure", OPP.pure_response(g, MALAKIR),
          False)

    g = fresh()
    b = bear()
    g.board.append(b)
    how = OPP.try_protect(g, 0.0, event="spot", victim=b)
    check("C spot removal at a creature: indestructible, 2 life, graveyard",
          (how, g.your_life, MALAKIR in g.graveyard, MALAKIR in g.hand),
          ("indestructible", 38.0, True, False))

    g = fresh()
    rock = Permanent(card=Card(name="Test Rock", types=frozenset({"Artifact"})),
                     sick=False)
    g.board.append(rock)
    check("D at a noncreature: not answered",
          OPP.try_protect(g, 0.0, event="spot", victim=rock), None)

    g = fresh()
    g.board.append(bear())
    check("E a wrath: not answered",
          OPP.try_protect(g, 0.0, event="wipe"), None)

    g = fresh()
    g.main_phase(reserve=0)
    check("F main phase: held, not cast",
          (MALAKIR in g.hand, g.m["agadeem_blank_casts"]), (True, 0))

    g = fresh(malakir_text=False)
    g.main_phase(reserve=0)
    check("G malakir_text=False: the old blank cast",
          (MALAKIR in g.hand, MALAKIR in g.graveyard), (False, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z251: Malakir Rebirth\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    entry = OPP.PROTECTION[S.MALAKIR]
    muts = {
        "PROTECTION without Malakir's entry": (
            {"A", "C", "F"}, OPP.PROTECTION,
            {k: v for k, v in OPP.PROTECTION.items() if k != S.MALAKIR}),
        "its creature flag dropped": (
            {"D"}, OPP.PROTECTION,
            {**OPP.PROTECTION, S.MALAKIR: {k: v for k, v in entry.items()
                                           if k != "creature"}}),
        "its life cost dropped": (
            {"C"}, OPP.PROTECTION,
            {**OPP.PROTECTION, S.MALAKIR: {k: v for k, v in entry.items()
                                           if k != "life"}}),
        "protection_life charges nothing": ({"C"}, None, None),
    }
    bad = 0
    for label, (want, table, value) in muts.items():
        print(f"-- {label}")
        saved_table = dict(OPP.PROTECTION)
        saved_life = OPP.protection_life
        if table is not None:
            OPP.PROTECTION.clear()
            OPP.PROTECTION.update(value)
        else:
            OPP.protection_life = lambda g, card: None
        try:
            broke = run_cases()
        finally:
            OPP.PROTECTION.clear()
            OPP.PROTECTION.update(saved_table)
            OPP.protection_life = saved_life
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
