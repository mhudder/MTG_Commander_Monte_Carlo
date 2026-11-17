#!/usr/bin/env python3
"""§0z229: Voldaren Bloodcaster's transform and Bloodbat Summoner's Bats
(shilgengar).

    python -m tests.test_bloodbat
    python -m tests.test_bloodbat --mutate   # 3 mutations, exact sets

Each case: a shilgengar game on an empty battlefield but for Voldaren
Bloodcaster and what a case adds; the Blood count set by hand.

CASES
  A  four Blood, one more created: five -- it transforms, a 3/3
  B  three Blood, one more: four -- not transformed, a 2/1
  C  transformed, two Blood, the beginning of combat: one becomes a 2/2
     flying Bat that can attack this turn; one plain Blood left, two in all
  D  Shilgengar out, four Blood and two Bats, a creature in the graveyard,
     three Treasures: the ultimate is paid with all six -- the Bats are
     sacrificed, the creature returns
  E  a Bat is never fed to Shilgengar (it is Blood already)
  F  NEIGHBOUR: `bloodbat` False, A's setup: not transformed

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  bloodbat=False                      -> A, C
  a Bat does not count as Blood       -> C, D
    (CORRECTED AFTER THE RUN, said so: written as D alone. C asks for two
    Blood in all, one of them the Bat, so it breaks too -- rightly.)
  a Bat may be fed to Shilgengar      -> E

UNMUTATED (§0z15): B and F are untransformed under every rule here.
"""
import sys

import edhmc.shilgengar as SH
from edhmc.decks import shilgengar_v1 as SM
from edhmc.engine import Board, remove_card
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(g, name):
    c = next(x for x in g.library if x.name == name)
    remove_card(g.library, c)
    return c


def game(blood, **cfg):
    deck, cmd = SM.build()
    g = SH.ShilgengarGame(list(deck), cmd,
                          dict(DEFAULT_CFG, **{**EXTRA_CFG, **cfg}), 1)
    g.board = Board()
    g.hand, g.graveyard = [], []
    caster = g.make_permanent(take(g, SH.BLOODCASTER), sick=False)
    g.blood = blood
    return g, caster


def create_one(g):
    g.blood += 1
    g.blood_created()


def bats(g):
    return [p for p in g.board if id(p) in g.blood_bats]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, c = game(4)
    create_one(g)
    check("A five Blood: transformed, a 3/3",
          (g.power_of(c), g.toughness_of(c)), (3, 3))

    g, c = game(3)
    create_one(g)
    check("B four Blood: a 2/1", (g.power_of(c), g.toughness_of(c)), (2, 1))

    g, c = game(4)
    create_one(g)
    g.blood = 2
    g.bloodbat_combat()
    b = bats(g)
    check("C a Bat: 2/2, flying, can attack; one plain Blood, two in all",
          (len(b), b and (g.power_of(b[0]), g.toughness_of(b[0]),
                          b[0].card.flying, b[0].sick),
           g.blood, g.blood_total()),
          (1, (2, 2, True, False), 1, 2))

    g, c = game(4)
    g.commander_cast = True
    g.make_permanent(g.commander, sick=False)
    for _ in range(2):
        g.blood_bats.add(id(g.make_permanent(SH.bat_token(), sick=False,
                                             is_token=True)))
    dead = take(g, "Priest of Fell Rites")
    g.graveyard.append(dead)
    g.treasures = 3
    g.shilgengar_ultimate()
    check("D the ultimate paid with four Blood and two Bats",
          (g.m["shilgengar_ults"], len(bats(g)), g.blood,
           any(p.card is dead for p in g.board)), (1, 0, 0, True))

    g, c = game(0)
    bat = g.make_permanent(SH.bat_token(), sick=False, is_token=True)
    g.blood_bats.add(id(bat))
    check("E a Bat is not Shilgengar's fodder", bat in g.ult_fodder(), False)

    g, c = game(4, bloodbat=False)
    create_one(g)
    check("F NEIGHBOUR: bloodbat False: a 2/1",
          (g.power_of(c), g.toughness_of(c)), (2, 1))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z229: Bloodbat Summoner\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")

    def every_creature(self):
        return [p for p in self.board
                if p.card.is_creature and p.card is not self.commander]

    muts = {
        "bloodbat=False": ({"A", "C"}, {"bloodbat": False}, []),
        "a Bat does not count as Blood": ({"C", "D"}, {}, [
            (SH.ShilgengarGame, "blood_total", lambda self: self.blood)]),
        "a Bat may be fed to Shilgengar": ({"E"}, {}, [
            (SH.ShilgengarGame, "ult_fodder", every_creature)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = dict(cfg)
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            for obj, name, val in saved:
                setattr(obj, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
