#!/usr/bin/env python3
"""Devotion is one rule, and Daxos's toughness reads it (§0z72).

    python -m tests.test_devotion
    python -m tests.test_devotion --mutate   # 2 mutations, exact sets

    Daxos, Blessed by the Sun {W}{W} 2/*  (Scryfall, verified 2026-09-27)
    Daxos's toughness is equal to your devotion to white. (Each {W} in the
    mana costs of permanents you control counts toward your devotion to
    white.) Whenever another creature you control enters or dies, you gain 1
    life.

`engine.devotion` counted plain pips and `karlov.devotion_white` counted
hybrid ones -- the same rule twice, two ways. CR 107.4e: a hybrid symbol is
all of its colours, so Lurrus's {1}{W/B}{W/B} is two devotion to white AND
two to black. One function now; Daxos's toughness is `daxos_toughness`.

CASES
  A Daxos alone: toughness 2 (his own {W}{W})
  B Daxos and Auriok Champion ({W}{W}): 4
  C Daxos and Lurrus: 4 -- the hybrid pips count
  D a token (no mana cost) adds nothing: 2
  E engine.devotion to BLACK with Lurrus out: 2 -- a hybrid pip is both
  F NEIGHBOUR, rendmaw's Erebos: devotion to black is plain pips as before
    (Erebos {3}{B} and Blood Artist {1}{B}: 2)
  G PROPERTY: karlov.devotion_white equals engine.devotion(g, "W") on 200
    random karlov boards

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  devotion counts plain pips only           -> C, E
  Daxos's toughness ignores devotion        -> A, B, C, D

UNMUTATED (§0z15): F is the neighbour the merge must not move; G is the
property that there is one rule.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as K
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
KDECK, KCMD = KM.build()
RDECK, RCMD = RM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def kc(name):
    return next(c for c in KDECK if c.name == name)


def kgame(*cards):
    g = K.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20), 1)
    g.board = EN.Board()
    for c in cards:
        g.board.append(c if isinstance(c, EN.Permanent)
                       else EN.Permanent(card=c, sick=False))
    return g


def daxos_t(*others):
    g = kgame(kc("Daxos, Blessed by the Sun"), *others)
    d = next(p for p in g.board if p.card.name.startswith("Daxos"))
    return g.toughness_of(d)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    check("A Daxos alone: 2", daxos_t(), 2)
    check("B with Auriok Champion: 4", daxos_t(kc("Auriok Champion")), 4)
    check("C with Lurrus: 4 (hybrid counts)",
          daxos_t(kc("Lurrus of the Dream-Den")), 4)
    tok = EN.Permanent(card=EN.Card(name="Spirit token",
                                    types=frozenset({"Creature"}),
                                    power=1, toughness=1), is_token=True)
    check("D a token adds nothing: 2", daxos_t(tok), 2)
    g = kgame(kc("Lurrus of the Dream-Den"))
    check("E devotion to black with Lurrus: 2", EN.devotion(g, "B"), 2)
    rg = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG), random.Random(1),
                 seed_for_pod=1)
    rg.board = EN.Board()
    for n in ("Erebos, Bleak-Hearted", "Blood Artist"):
        rg.board.append(EN.Permanent(card=next(c for c in RDECK if c.name == n),
                                     sick=False))
    check("F rendmaw's devotion to black: 2", EN.devotion(rg, "B"), 2)
    rnd, same = random.Random(9), True
    perms = [c for c in KDECK if not c.is_land]
    for _ in range(200):
        g = kgame(*rnd.sample(perms, rnd.randint(0, 12)))
        same &= K.devotion_white(g) == EN.devotion(g, "W")
    check("G one rule: devotion_white == devotion(W), 200 boards", same, True)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Devotion, one rule; Daxos's toughness\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {"devotion": EN.devotion, "daxos_toughness": K.daxos_toughness,
            "EN_devotion": K.EN_devotion}

    def plain(g, colour):
        return sum(p.card.cost.get(colour, 0) for p in g.board)

    muts = {
        "devotion counts plain pips only":
            ({"C", "E"}, [(EN, "devotion", plain), (K, "EN_devotion", plain)]),
        "Daxos's toughness ignores devotion":
            ({"A", "B", "C", "D"}, [(K, "daxos_toughness", lambda g: 0)]),
    }
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")
        for mod, name, fn in patches:
            setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            for mod, name, _ in patches:
                setattr(mod, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
