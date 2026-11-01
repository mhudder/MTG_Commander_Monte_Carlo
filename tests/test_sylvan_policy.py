#!/usr/bin/env python3
"""Pin Sylvan Library's policy knobs (§0z163).

    python -m tests.test_sylvan_policy
    python -m tests.test_sylvan_policy --mutate   # 2 mutations, exact sets

CASES
  A  the clock floor is `opponents.clock_floor`: next round's chip + the pad
  B  the default floor is fixed at 20
  C  `library_pay_max` 1 keeps one card for 4 life where the floor allows two
  D  on a quiet table the clock floor pays for both where 20 pays for none
  E  `turn_cfg` reaches the shared engine: a knob set on its own turn only

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  library_floor_mode="fixed"   -> A, D
  library_pay_max=2            -> C

UNMUTATED (§0z15): B is the default read; E is the diagnostic switch.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import azusa_v1 as AM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECK, CMD = AM.build()
LIBRARY = next(c for c in DECK if c.name == "Sylvan Library")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def spell(name, pri=0.0):
    return EN.Card(name=name, types=frozenset({"Sorcery"}), priority=pri)


def fresh(life=30.0, creatures=3.0, **kw):
    """Turn 6, Sylvan Library out, three opponents of `creatures` each."""
    cfg = dict(DEFAULT_CFG, **{**kw, **CFG})
    g = AZ.AzusaGame(list(DECK), CMD, cfg, 1)
    g.board = EN.Board()
    g.board.append(EN.Permanent(card=LIBRARY, sick=False))
    g.hand, g.graveyard = [], []
    g.library = ([spell(f"F{i}") for i in range(20)]
                 + [spell("Low", 1), spell("Mid", 5), spell("High", 9)])
    g.turn = 6
    g.your_life = life
    for o in g.opponents:
        o.life, o.creatures, o.alive = 40.0, creatures, True
    return g


def step(g):
    """The draw step, then Sylvan Library's choice. Returns life paid."""
    before = len(g.hand)
    life = g.your_life
    g.draw(1)
    EN.sylvan_library(g, before)
    return life - g.your_life


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = fresh(library_floor_mode="clock", library_clock_pad=3.0)
    check("A the clock floor is next round's chip + the pad",
          round(EN.library_floor(g), 9),
          round(OPP.predicted_chip(g, 1) + 3.0, 9))

    check("B the default floor is fixed at 20", EN.library_floor(fresh()), 20)

    check("C library_pay_max 1 keeps one card where the floor allows two",
          (step(fresh(life=30.0)), step(fresh(life=30.0, library_pay_max=1))),
          (8.0, 4.0))

    quiet = dict(life=18.0, creatures=0.0)
    check("D a quiet table: the clock pays for both, 20 for none",
          (step(fresh(**quiet, library_floor_mode="clock")),
           step(fresh(**quiet, library_floor_mode="fixed"))), (8.0, 0.0))

    g = fresh(turn_cfg=(7, {"library_life_floor": 5}))
    on6 = EN.library_floor(g)
    g.turn = 7
    check("E turn_cfg reaches the shared engine, on its own turn only",
          (on6, EN.library_floor(g)), (20, 5))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Sylvan Library's policy (§0z163)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"library_floor_mode": "fixed"}, {"A", "D"}),
        ({"library_pay_max": 2}, {"C"}),
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
