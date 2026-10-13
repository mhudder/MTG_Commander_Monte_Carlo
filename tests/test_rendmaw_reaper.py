#!/usr/bin/env python3
"""Midnight Reaper in rendmaw (item 24, change 0): KNOWN_BLIND there while
shilgengar modelled it.

    python -m tests.test_rendmaw_reaper
    python -m tests.test_rendmaw_reaper --mutate   # 3 mutations, exact sets

    Midnight Reaper {2}{B} 3/2   (Scryfall, verified 2026-10-13)
    Whenever a nontoken creature you control dies, this creature deals 1
    damage to you and you draw a card.

CASES (the Reaper is placed FIRST on the board, so a wipe removes it first)
  A  a wipe of the Reaper and three nontoken creatures: four draws, 4 life
     (its own death and the three after it, by look-back, §0z76)
  B  a TOKEN dying draws nothing
  C  one nontoken creature destroyed: one draw, 1 life
  D  the Reaper destroyed alone: one draw (it sees its own death)
  E  with an empty library the draw is still taken, and loses (§0z42)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  midnight_reaper does nothing                 -> A, C, D, E
  the Reaper counts tokens                     -> B
  the Reaper reads the live board only         -> A, D

UNMUTATED (§0z15): the 1 damage and the draw are one branch; every case
reads both, so no mutation separates them.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


RDECK, RCMD = RM.build()
REAPER = next(c for c in RDECK if c.name == "Midnight Reaper")


def body(name):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=2,
                   toughness=2)


def rgame(*perms, library=30):
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(library)]
    g.turn = 6
    g.your_life = 40.0
    for o in g.opponents:
        o.life = 40.0
    for p in perms:
        g.board.append(p)
    return g


def perm(card, token=False):
    return EN.Permanent(card=card, sick=False, is_token=token,
                        base_p=card.power, base_t=card.toughness)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    g = rgame(perm(REAPER), *(perm(body(f"B{i}")) for i in range(3)))
    with OPP.simultaneous(g):
        for p in [p for p in g.board if OPP.is_creature_now(g, p)]:
            OPP.destroy(g, p, destroys=True)
    check("A wipe: four draws, 4 life",
          (g.m["reaper_draws"], g.your_life), (4, 36.0))

    g = rgame(perm(REAPER), perm(body("Bird"), token=True))
    OPP.destroy(g, g.board[1], destroys=True)
    check("B a token dying draws nothing", g.m["reaper_draws"], 0)

    g = rgame(perm(REAPER), perm(body("Bear")))
    OPP.destroy(g, g.board[1], destroys=True)
    check("C one nontoken death: one draw, 1 life",
          (g.m["reaper_draws"], g.your_life, len(g.hand)), (1, 39.0, 1))

    g = rgame(perm(REAPER))
    OPP.destroy(g, g.board[0], destroys=True)
    check("D the Reaper's own death draws", g.m["reaper_draws"], 1)

    g = rgame(perm(REAPER), perm(body("Bear")), library=0)
    OPP.destroy(g, g.board[1], destroys=True)
    check("E an empty library: the draw is taken and loses",
          (g.m["reaper_draws"], g.result), (1, "loss"))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Midnight Reaper (rendmaw, item 24)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = EN.midnight_reaper
    real_watching = OPP.watching

    def counts_tokens(g, n, p):
        if p is not None and p.is_token:
            p = EN.Permanent(card=p.card, sick=False)
            p.is_token = False
        real(g, n, p)

    def live_only(g, name, perm=None, another=False):
        return g.count(name)

    muts = {
        "midnight_reaper does nothing":
            ({"A", "C", "D", "E"}, EN, "midnight_reaper",
             lambda g, n, p: None),
        "the Reaper counts tokens":
            ({"B"}, EN, "midnight_reaper", counts_tokens),
        "the Reaper reads the live board only":
            ({"A", "D"}, OPP, "watching", live_only),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        orig = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
