#!/usr/bin/env python3
"""The crown does not end the pod's chip round, and trostani's two life
floors are the owner's (§0z97).

    python -m tests.test_life_policies
    python -m tests.test_life_policies --mutate   # 3 mutations, exact sets

CASES
  A  the crown is taken by the FIRST opponent (`monarch_loss_scale` makes the
     roll certain): every later opponent still deals chip damage, and the
     life lost is the sum of creatures x rate x share x power over all three,
     with the share floored by the crown up to and including the seat that
     took it and unfloored after -- to 1e-9
  B  NEIGHBOUR: without the crown, the same board loses the same sum (the
     fix changes nothing that never held the crown)
  C  Phyrexian Processor pays min(PROCESSOR_LIFE, life - 12): at 40 life it
     pays the cap; at 18 it pays 6; at 15 it pays 3 and is not cast
  D  Sylvan Library at 28 life keeps BOTH extra cards (28 -> 24 -> 20); at
     27 it keeps one (27 -> 23, and 19 would be under 20)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the old `break` (crown_loss_ends_chip=True)   -> A
  Processor's floor back at 20                  -> C
  Sylvan Library's floor back at 25             -> D

UNMUTATED (§0z15): B is the neighbour.
"""
import sys

import edhmc.opponents as OPP
import edhmc.trostani as T
from edhmc.decks import trostani_v1 as TM
from edhmc.engine import Board
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA = {}
DECK, CMD = TM.build()
BY_NAME = {c.name: c for c in DECK}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = T.TrostaniGame(list(DECK), CMD,
                       dict(DEFAULT_CFG, turns=20, **{**cfg, **EXTRA}), 1)
    g.board, g.hand, g.graveyard = Board(), [], []
    g.your_life = 1e6
    g.turn = 6
    g.turn_key = (6, 0)
    g.m["extra_turns_taken"] = 0
    for o, n in zip(g.opponents, (3.0, 4.0, 5.0)):
        o.alive, o.creatures = True, n
    return g


def chip_sum(g, crown_seat):
    """Creatures x rate x share x power, the crown flooring every seat up
    to and including the one that takes it."""
    rate = g.cfg.get("incidental_rate", 0.45)
    total = 0.0
    for i, o in enumerate(g.opponents):
        g.monarch = crown_seat is not None and i <= crown_seat
        total += o.creatures * rate * g.attack_share(i) * o.p.get("power", 1.0)
    return total


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh(monarch_loss_scale=100.0)
    want = chip_sum(g, 0)
    g.monarch, g.your_life = True, 1e6
    OPP.incidental_damage(g)
    check("A the crown is lost to seat 0 and seats 1-2 still swing",
          (abs((1e6 - g.your_life) - want) < 1e-9, g.monarch), (True, False))

    g = fresh()
    want = chip_sum(g, None)
    g.monarch, g.your_life = False, 1e6
    OPP.incidental_damage(g)
    check("B without the crown the sum is unchanged",
          abs((1e6 - g.your_life) - want) < 1e-9, True)

    g = fresh()
    pays = []
    for life in (40, 18, 15):
        g.your_life = float(life)
        pays.append(g.processor_payment())
    cast = g.worth_casting(BY_NAME["Phyrexian Processor"])
    check("C Processor pays the cap, then down to 12, and 3 is not cast",
          (pays, cast), ([min(T.PROCESSOR_LIFE, 28), 6, 3], False))

    kept = []
    for life in (28, 27):
        g = fresh()
        g.board.append(T.Permanent(card=BY_NAME["Sylvan Library"], sick=False))
        g.library = [c for c in DECK if c.name != "Sylvan Library"][:30]
        g.your_life = float(life)
        g.draw_step()
        kept.append(g.m["library_kept"])
    check("D Sylvan Library keeps down to 20 life", kept, [2, 1])
    return set(FAIL)


def main() -> int:
    global EXTRA
    if not MUTATE:
        print("The crown and trostani's life floors (§0z97)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "the old break": ({"A"}, {"crown_loss_ends_chip": True}),
        "Processor's floor back at 20": ({"C"}, {"processor_floor": 20}),
        "Sylvan Library's floor back at 25": ({"D"},
                                              {"library_life_floor": 25}),
    }
    bad = 0
    for label, (want, extra) in muts.items():
        print(f"-- {label}")
        EXTRA = extra
        try:
            broke = run_cases()
        finally:
            EXTRA = {}
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
