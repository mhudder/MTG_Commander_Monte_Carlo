#!/usr/bin/env python3
"""Your own sweeper asks the wipe gate at every OPTIONAL cast site (§0z104).

    python -m tests.test_wipe_gate
    python -m tests.test_wipe_gate --mutate   # 1 mutation, exact set

`opponents.should_cast_own_wipe` -- sweep only when the table's creatures
meaningfully outnumber yours -- was asked in the main phase alone, so
lorehold's miracle, discover and other free casts, and karlov's Bolas's
Citadel, wiped boards the pilot was winning with. WINNING below is five
bodies against one creature per opponent (gate closed); LOSING is no bodies
against five each (gate open).

CASES
  A  lorehold `pilot_may_cast(Farewell)`: False winning, True losing
  B  lorehold miracle: Farewell drawn as the turn's first card while
     winning goes to HAND, uncast
  C  lorehold discover 10 hitting Farewell while winning puts it in hand
     ("cast it ... or put it into your hand")
  D  karlov Bolas's Citadel with Damn on top while winning: the dig STOPS,
     Damn stays on top, and `citadel_wipe_held` counts it
  E  NEIGHBOUR: the same miracle while LOSING casts Farewell

MUTATION, WRITTEN BEFORE THE RUN, exact set:
  wipe_gate_all_casts=False (the old engine)   -> A, B, C, D

UNMUTATED (§0z15): E is the neighbour -- the gate must not stop a wipe the
pilot wants.
"""
import sys

from edhmc import engine as EN
from edhmc import karlov as KA
from edhmc import lorehold as LO
from edhmc.decks import karlov_v2, lorehold_v16
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import DECKS as CATALOG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA = {}
LDECK, LCMD = lorehold_v16.build()
KDECK, KCMD = karlov_v2.build()
FAREWELL = next(c for c in LDECK if c.name == "Farewell")
DAMN = next(c for c in KDECK if c.name == "Damn")
CITADEL = CATALOG["karlov"][1]["Bolas's Citadel"]
BODY = EN.Card(name="Body", types=frozenset({"Creature"}), power=2,
               toughness=2, cost={"gen": 2})


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def filler(n):
    return [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                    cost={"gen": 9}) for i in range(n)]


def land(colour):
    return EN.Card(name=f"Land {colour}", types=frozenset({"Land"}),
                   is_land=True, produces=frozenset({colour}))


def table(g, winning):
    for _ in range(5 if winning else 0):
        g.board.append(EN.Permanent(card=BODY, sick=False, base_p=2, base_t=2))
    for o in g.opponents:
        o.alive, o.creatures = True, (1.0 if winning else 5.0)


def lorehold(winning):
    g = LO.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, **EXTRA), 1)
    g.board = LO.Board()
    g.hand, g.graveyard, g.dream_exile = [], [], []
    g.library = filler(20)
    g.commander_cast = True
    for c in ("W", "W", "R", "R", "W", "R", "W"):
        g.board.append(EN.Permanent(card=land(c), sick=False))
    table(g, winning)
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    a = [LO.pilot_may_cast(lorehold(w), FAREWELL) for w in (True, False)]
    check("A pilot_may_cast refuses a wipe only while winning", a,
          [False, True])

    g = lorehold(True)
    g.library.append(FAREWELL)
    LO.miracle_window(g)
    check("B a miracled Farewell while winning goes to hand",
          (FAREWELL in g.hand, g.m["own_wipes_cast"]), (True, 0))

    g = lorehold(True)
    g.library = filler(5) + [FAREWELL]
    LO.discover(g, 10)
    check("C discover puts a refused wipe into hand",
          (FAREWELL in g.hand, g.m["discover_to_hand"]), (True, 1))

    g = KA.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, **EXTRA), 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.board.append(EN.Permanent(card=CITADEL, sick=False))
    g.your_life = 40.0
    g.library = filler(5) + [DAMN]
    table(g, True)
    KA.citadel_step(g)
    check("D the Citadel's dig stops at a refused wipe",
          (g.library[-1] is DAMN, g.m["citadel_wipe_held"]), (True, 1))

    g = lorehold(False)
    g.library.append(FAREWELL)
    LO.miracle_window(g)
    check("E NEIGHBOUR: a miracled Farewell while losing is cast",
          g.m["own_wipes_cast"], 1)
    return set(FAIL)


def main() -> int:
    global EXTRA
    if not MUTATE:
        print("The wipe gate at every optional cast site (§0z104)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact set\n")
    want = {"A", "B", "C", "D"}
    EXTRA = {"wipe_gate_all_casts": False}
    try:
        broke = run_cases()
    finally:
        EXTRA = {}
    ok = broke == want
    print(f"   broke {sorted(broke) or 'nothing'}  expected {sorted(want)}  "
          f"{'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{int(ok)} passed, {int(not ok)} failed (1 mutation, exact set)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
