#!/usr/bin/env python3
"""Pin Necropotence's policy (§0z162).

    python -m tests.test_necro_policy
    python -m tests.test_necro_policy --mutate   # 2 mutations, exact sets

CASES
  A  the clock floor is `opponents.clock_floor`: next round's chip + the pad
  B  the default floor is fixed at 10
  C  the Tower target applies while Reliquary Tower is out, and only then
  D  the buy is the least of the target, the floor and the library less
     its decking reserve (7 cards, 5 kept: 2)
  E  the Citadel's clock floor and Necropotence's are ONE function: same
     board, same pad, same number

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  necro_floor_mode="fixed"   -> A, E
  necro_tower_target=None    -> C

E WAS MISSING FROM THE FIRST WRITTEN SET, and the first mutation run said so:
E reads Necropotence's floor in clock mode, so forcing "fixed" reaches it
too. The set above is the corrected one (§0z11: the run is the check on the
expectation, not a transcript of it).

UNMUTATED (§0z15): B is the default read; D is arithmetic with every knob
at its default.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECK, CMD = build_pending("karlov")


def card(name):
    return next(c for c in DECK if c.name == name)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def filler(i):
    return EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1})


def fresh(board=(), hand=0, life=40.0, library=30, **kw):
    """Turn 5 (the pod attacks from round 3), three boards of four,
    Necropotence on the battlefield."""
    cfg = dict(DEFAULT_CFG, turns=20, opponents=False, **{**kw, **CFG})
    g = K.KarlovGame(list(DECK), CMD, cfg, 1)
    g.board = EN.Board()
    g.hand = [filler(100 + i) for i in range(hand)]
    g.graveyard = []
    g.library = [filler(i) for i in range(library)]
    g.your_life = life
    g.turn = 5
    g.commander_cast = True
    for c in (card("Necropotence"),) + tuple(board):
        g.board.append(EN.Permanent(card=c, sick=False))
    for o in g.opponents:
        o.life, o.creatures = 40.0, 4.0
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = fresh(necro_floor_mode="clock", necro_clock_pad=2.0)
    check("A the clock floor is next round's chip + the pad",
          round(K.necro_floor(g), 9),
          round(OPP.predicted_chip(g, 1) + 2.0, 9))

    check("B the default floor is fixed at 10", K.necro_floor(fresh()), 10)

    tower = card("Reliquary Tower")
    check("C the Tower target applies only with the Tower out",
          (K.necro_target(fresh(board=[tower], necro_tower_target=11)),
           K.necro_target(fresh(necro_tower_target=11))), (11, 7))

    check("D the buy is the least of target, floor and library",
          (K.necropotence_cards(fresh(hand=3)),
           K.necropotence_cards(fresh(hand=0, life=13.0)),
           K.necropotence_cards(fresh(hand=0, library=7))), (4, 3, 2))

    g = fresh(citadel_floor_mode="clock", citadel_clock_pad=3.0,
              necro_floor_mode="clock", necro_clock_pad=3.0)
    check("E the Citadel's clock floor and Necropotence's are one function",
          K.citadel_value_floor(g), K.necro_floor(g))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Necropotence's policy (§0z162)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"necro_floor_mode": "fixed"}, {"A", "E"}),
        ({"necro_tower_target": None}, {"C"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for over, want in mutations:
        CFG.update(over)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += not ok
        print(f"   {over}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else 'MISMATCH'}\n")
    print("all mutations as expected" if not bad else f"{bad} MISMATCH(ES)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
