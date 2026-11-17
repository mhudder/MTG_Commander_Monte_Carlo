#!/usr/bin/env python3
"""§0z228: Memory Jar (azusa) -- the hand exiled, seven drawn, and at the
end step the seven discarded and the hand returned.

    python -m tests.test_memory_jar
    python -m tests.test_memory_jar --mutate   # 3 mutations, exact sets

Each case: an azusa game, the battlefield set by hand with an untapped
Memory Jar on it, and a hand of the size a case names.

CASES
  A  a hand of two: cracked -- the Jar to the graveyard, the two exiled,
     seven in hand
  B  then the end step: the seven discarded to the graveyard, the two back
  C  a hand of three: kept (`memory_jar_hand` 2)
  D  a library of eight: kept (the seven would leave fewer than the
     decking reserve)
  E  NEIGHBOUR: `memory_jar` False, A's setup: kept

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  memory_jar=False              -> A, B
  memory_jar_hand=9             -> C
  the draw is always safe       -> D

UNMUTATED (§0z15): E keeps the Jar under every rule here.
"""
import sys

import edhmc.azusa as AZ
from edhmc.decks import azusa_v1 as AM
from edhmc.engine import Board, Permanent, remove_card
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(hand, library=None, **cfg):
    deck, cmd = AM.build()
    g = AZ.AzusaGame(list(deck), cmd,
                     dict(DEFAULT_CFG, **{**EXTRA_CFG, **cfg}), 1)
    g.board = Board()
    g.graveyard = []
    jar = next(c for c in g.library if c.name == AZ.MEMORY_JAR)
    remove_card(g.library, jar)
    g.board.append(Permanent(card=jar, sick=False))
    g.hand = [g.library.pop() for _ in range(hand)]
    if library is not None:
        g.library = g.library[:library]
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game(2)
    kept = list(g.hand)
    AZ.memory_jar_crack(g)
    check("A cracked: the Jar gone, the two exiled, seven in hand",
          (AZ.MEMORY_JAR in [c.name for c in g.graveyard], len(g.hand),
           g.jar_exiled == kept), (True, 7, True))
    seven = list(g.hand)
    AZ.memory_jar_return(g)
    check("B the end step: the seven discarded, the two back",
          (g.hand == kept, all(c in g.graveyard for c in seven)
           if seven and len(seven) == 7 else False),
          (True, True))

    g = game(3)
    AZ.memory_jar_crack(g)
    check("C a hand of three: kept", g.m["memory_jar_cracks"], 0)

    g = game(2, library=8)
    AZ.memory_jar_crack(g)
    check("D a library of eight: kept", g.m["memory_jar_cracks"], 0)

    g = game(2, memory_jar=False)
    AZ.memory_jar_crack(g)
    check("E NEIGHBOUR: memory_jar False: kept", g.m["memory_jar_cracks"], 0)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z228: Memory Jar\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "memory_jar=False": ({"A", "B"}, {"memory_jar": False}, []),
        "memory_jar_hand=9": ({"C"}, {"memory_jar_hand": 9}, []),
        "the draw is always safe": ({"D"}, {}, [
            (AZ, "draw_is_safe", lambda g, n=1: True)]),
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
