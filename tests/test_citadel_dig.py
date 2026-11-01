#!/usr/bin/env python3
"""Pin Bolas's Citadel's dig (§0z160).

    python -m tests.test_citadel_dig
    python -m tests.test_citadel_dig --mutate   # 6 mutations, exact sets

CASES
  A  X = 0 (CR 107.3b): Debt to the Deathless costs 4 life off the top, not 7
  B  ... and cast through the Citadel it drains nothing and gains nothing
  C  the value dig STOPS at a Debt on top and leaves it there
  D  Sensei's Divining Top gets past a land with no land drop: the land goes
     to hand, Top is recast for 1 life, and the dig goes on to the spells
  E  Necropotence gets past it for 1 life; the card reaches the hand at the
     beginning of the end step, not before
  F  Syr Konrad gets past it for {1}{B}: the land is milled
  G  with no way past, a land with no land drop stops the dig
  H  your turn digs in BOTH main phases (two `citadel_main` calls)
  I  an instant on top is cast at the end of the pod's round, for life
  J  an answer on top with nothing to hit is left there
  K  all-in digs to 1: at 12 life, three 4-drops -- value casts 0, all-in 2
  L  Top's spin puts the castable spell above the lands when no drop is left
  M  the dig stops `decking_reserve` cards from the bottom (§0z42)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  citadel_x0=False             -> A, B, C
  citadel_skip=False           -> D, E, F
  citadel_main2=False          -> H
  citadel_pod_instants=False   -> I
  citadel_spin=False           -> L
  citadel_decking_guard=False  -> D, M

UNMUTATED (§0z15): G is the old dig's own stop and holds with every knob
off; J holds when the window is off too (nothing is cast either way); K is
the policy read, not a mechanism with a switch. D is in the guard's set
because its library is short enough that the guard is what ends it.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as K
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


def spell(i, mv=1, types=("Sorcery",)):
    return EN.Card(name=f"Filler {i}", types=frozenset(types),
                   cost={"gen": mv})


def land(i, produces="C"):
    return EN.Card(name=f"Wastes {i}", types=frozenset({"Land"}),
                   is_land=True, produces=frozenset(produces))


def fresh(board=(), library=(), life=40.0, **kw):
    """A karlov game on turn 2 (`pod_turn` < 3: nothing is countered), the
    land drop spent, the Citadel on the battlefield."""
    cfg = dict(DEFAULT_CFG, turns=20, opponents=False, **{**kw, **CFG})
    g = K.KarlovGame(list(DECK), CMD, cfg, 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = list(library)
    g.your_life = g.turn_life = life
    g.turn = 2
    g.commander_cast = True
    g.land_drops, g.land_drops_used = 1, 1
    for c in (card("Bolas's Citadel"),) + tuple(board):
        g.board.append(EN.Permanent(card=c, sick=False))
    for o in g.opponents:
        o.life = 40.0
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()
    debt = card("Debt to the Deathless")

    g = fresh()
    check("A Debt costs 4 life off the top", K.citadel_cost(g, debt), 4.0)

    g = fresh(library=[spell(i) for i in range(10)] + [debt],
              citadel_allin="always")
    K.citadel_step(g)
    check("B ... and drains nothing through the Citadel",
          ([o.life for o in g.opponents], g.m["lifegain_triggers"]),
          ([40.0, 40.0, 40.0], 0))

    g = fresh(library=[spell(i) for i in range(10)] + [debt])
    K.citadel_step(g)
    check("C the value dig stops at Debt, leaving it on top",
          (g.library[-1] is debt, g.your_life), (True, 40.0))

    top = card("Sensei's Divining Top")
    g = fresh(board=[top], library=[spell(i) for i in range(10)] + [land(0)])
    K.citadel_step(g)
    check("D Top: the land to hand, Top recast, the dig goes on",
          ([c.name for c in g.hand], g.has("Sensei's Divining Top"),
           g.m["citadel_skips_top"], g.m["citadel_casts"], g.your_life),
          (["Wastes 0"], True, 1, 6, 34.0))

    g = fresh(board=[card("Necropotence")],
              library=[spell(i) for i in range(10)] + [land(0)])
    K.citadel_step(g)
    early = [c.name for c in g.hand]
    K.end_step(g)
    check("E Necropotence: 1 life, the card at the end step",
          (early, [c.name for c in g.hand], g.m["citadel_skips_necro"]),
          ([], ["Wastes 0"], 1))

    g = fresh(board=[card("Syr Konrad, the Grim"), land(7, "B"), land(8, "B")],
              library=[spell(i) for i in range(10)] + [land(0)])
    K.citadel_step(g)
    check("F Syr Konrad mills the land for {1}{B}",
          ("Wastes 0" in [c.name for c in g.graveyard],
           g.m["citadel_skips_konrad"]), (True, 1))

    g = fresh(library=[spell(i) for i in range(10)] + [land(0)])
    K.citadel_step(g)
    check("G no way past: a land with no drop stops the dig",
          (g.library[-1].name, g.m["citadel_stop_land"]), ("Wastes 0", 1))

    calls = []
    real = K.citadel_main
    K.citadel_main = lambda gg: calls.append(gg.turn)
    try:
        g = fresh(library=[spell(i) for i in range(30)])
        K.take_turn(g)
    finally:
        K.citadel_main = real
    check("H both main phases dig", len(calls), 2)

    instant = spell(99, mv=2, types=("Instant",))
    g = fresh(library=[spell(i) for i in range(10)] + [instant])
    K.citadel_pod_window(g, "end")
    check("I an instant on top is cast at the end of the pod's round",
          (instant in g.graveyard, g.your_life, g.m["citadel_pod_casts"]),
          (True, 38.0, 1))

    swords = card("Swords to Plowshares")
    g = fresh(library=[spell(i) for i in range(10)] + [swords])
    K.citadel_pod_window(g, "end")
    check("J an answer with nothing to hit stays on top",
          (g.library[-1] is swords, g.your_life), (True, 40.0))

    def allin_casts(policy):
        g = fresh(library=[spell(i) for i in range(10)]
                  + [spell(90 + i, mv=4) for i in range(3)], life=12.0,
                  citadel_allin=policy)
        K.citadel_step(g)
        return g.m["citadel_casts"]
    check("K all-in digs to 1: value 0, all-in 2",
          (allin_casts("never"), allin_casts("always")), (0, 2))

    g = fresh(board=[top, land(7, "B")],
              library=[spell(i) for i in range(10)]
              + [spell(50), land(1), land(0)])
    K.citadel_spin(g, 10.0)
    check("L Top's spin puts the castable spell on top",
          g.library[-1].name, "Filler 50")

    g = fresh(library=[spell(i) for i in range(8)])
    K.citadel_step(g)
    check("M the dig stops decking_reserve cards from the bottom",
          (len(g.library), g.m["citadel_stop_library"]), (5, 1))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Bolas's Citadel's dig (§0z160)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"citadel_x0": False}, {"A", "B", "C"}),
        ({"citadel_skip": False}, {"D", "E", "F"}),
        ({"citadel_main2": False}, {"H"}),
        ({"citadel_pod_instants": False}, {"I"}),
        ({"citadel_spin": False}, {"L"}),
        ({"citadel_decking_guard": False}, {"D", "M"}),
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
