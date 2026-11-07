#!/usr/bin/env python3
"""Pin the karoo land-drop guard (§0z172).

    python -m tests.test_karoo_drop
    python -m tests.test_karoo_drop --mutate   # 1 mutation, exact set

Golgari Rot Farm: "When this land enters, return a land you control to its
owner's hand." `engine.play_land` ranked new colours first, so on an empty
battlefield the two-colour karoo beat every basic, returned ITSELF, and won
the next turn's drop the same way (567 of 887 entries in 2,000 rendmaw games).

CASES
  A empty battlefield, Rot Farm and a Forest in hand: the Forest is played
  B a land on the battlefield: the Rot Farm is played, and returns that land
  C empty battlefield, the Rot Farm the only land in hand: it is played (and
    returns itself -- nothing else could be done with the drop)
  D `karoo_needs_land=False` restores the old pick: the Rot Farm on an empty
    battlefield, returning itself

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  karoo_needs_land False (cfg)   -> A

UNMUTATED (§0z15): B and C are the guard's limits, D is the switch itself.
Blind to trostani, which has its own karoo code and is SUSPENDED.
"""
import random
import sys

import edhmc.engine as EN
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECK, CMD = build_pending("rendmaw")
CARD = {c.name: c for c in DECK}
FARM, FOREST = CARD["Golgari Rot Farm"], CARD["Forest"]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(hand, board=(), **kw):
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, **{**kw, **CFG}),
                random.Random(1), seed_for_pod=1)
    g.board, g.hand, g.graveyard = EN.Board(), list(hand), []
    for c in board:
        g.board.append(EN.Permanent(card=c, sick=False))
    g.turn, g.land_drops_used = 2, 0
    return g


def state(g):
    return (sorted(p.card.name for p in g.board), sorted(c.name for c in g.hand),
            g.m["karoo_bounces"])


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = game([FARM, FOREST])
    EN.play_land(g)
    check("A empty battlefield: the Forest, not the karoo",
          state(g), (["Forest"], ["Golgari Rot Farm"], 0))
    swamp = CARD["Swamp"]
    g = game([FARM], board=[swamp])
    EN.play_land(g)
    check("B a land out: the karoo is played and returns it",
          state(g), (["Golgari Rot Farm"], ["Swamp"], 1))
    g = game([FARM])
    EN.play_land(g)
    check("C the karoo alone in hand: played, and it returns itself",
          state(g), ([], ["Golgari Rot Farm"], 1))
    g = game([FARM, FOREST], karoo_needs_land=False)
    EN.play_land(g)
    check("D karoo_needs_land=False: the old pick",
          state(g), ([], ["Forest", "Golgari Rot Farm"], 1))
    return set(FAIL)


def main():
    if not MUTATE:
        print("the karoo land-drop guard (§0z172)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    muts = [("karoo_needs_land False", {"A"}, {"karoo_needs_land": False})]
    bad = 0
    for label, want, cfg in muts:
        print(f"-- {label}")
        CFG.clear()
        CFG.update(cfg)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
