#!/usr/bin/env python3
"""Pin lorehold's Sensei's Divining Top policy knobs (§0z164).

    python -m tests.test_lorehold_top
    python -m tests.test_lorehold_top --mutate   # 2 mutations, exact sets

The pod's window pays from float and Treasures: 3 floating, {1} for the
spin, 2 left. A creature with its OWN miracle cost of {4} (mana value 8,
miracle value 4) is worth more than an instant of mana value 4 (Lorehold's
{2}, value 2), and is the one the window cannot pay for.

CASES
  A  "afford", nothing payable: the least wanted card on top, the best
     miracle second -- saved for a window that can pay
  B  "afford": the best miracle THIS window can pay for goes on top
  C  "value" (the default): the best miracle on top, payable or not
  D  `lorehold_top_spin` "own": no spin in the pod's window, a spin in yours
  E  `lorehold_top_spin` "never": no spin at all
  F  `miracle_need` reads a non-instant's own miracle cost ({4} here), as
     `miracle_window` pays it -- it returned Lorehold's {2} until §0z164

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  lorehold_top_order="value"   -> A, B
  lorehold_top_spin="every"    -> D, E

UNMUTATED (§0z15): C is the default order; F is a rule with no switch.
A AND B FAILED UNMUTATED ON THE FIRST RUN, and that was the engine, not the
test: `miracle_need` gave the creature Lorehold's {2}, so "afford" thought
it payable. F pins the fix.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as LH
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECK, CMD = build_pending("lorehold")
TOP = next(c for c in DECK if c.name == "Sensei's Divining Top")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def big():
    return EN.Card(name="Big", types=frozenset({"Creature"}), cost={"gen": 8},
                   miracle_cost={"gen": 4})


def instant():
    return EN.Card(name="Bolt", types=frozenset({"Instant"}), cost={"gen": 4})


def land(i):
    return EN.Card(name=f"Land {i}", types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({"R"}))


def fresh(top3, float_mana=3, **kw):
    """Lorehold cast, Top out, nothing else; `top3` listed top first."""
    cfg = dict(DEFAULT_CFG, turns=20, **{**kw, **CFG})
    g = LH.LoreholdGame(list(DECK), CMD, cfg, 1)
    g.board = EN.Board()
    g.board.append(EN.Permanent(card=TOP, sick=False))
    g.hand, g.graveyard = [], []
    g.library = [land(10 + i) for i in range(10)] + list(reversed(top3))
    g.commander_cast = True
    g.float_mana, g.treasures = float_mana, 0
    g.top_known = None
    g.turn = 6
    return g


def order(g):
    return [c.name for c in reversed(g.library[-3:])]       # top first


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = fresh([land(1), big(), land(2)], lorehold_top_order="afford")
    LH.sort_top_three(g, off_turn=True)
    check("A afford, nothing payable: a dud on top, the miracle second",
          order(g)[:2], ["Land 1", "Big"])

    g = fresh([big(), land(1), instant()], lorehold_top_order="afford")
    LH.sort_top_three(g, off_turn=True)
    check("B afford: the best payable miracle on top", order(g)[0], "Bolt")

    g = fresh([land(1), instant(), big()])
    LH.sort_top_three(g, off_turn=True)
    check("C value: the best miracle on top, payable or not",
          order(g)[0], "Big")

    g = fresh([land(1), instant(), big()], lorehold_top_spin="own")
    LH.sort_top_three(g, off_turn=True)
    pod = g.m["top_spins"]
    g.board.append(EN.Permanent(card=land(99), sick=False))
    LH.sort_top_three(g, off_turn=False)
    check("D own: no spin in the pod's window, a spin in yours",
          (pod, g.m["top_spins"]), (0, 1))

    g = fresh([land(1), instant(), big()], lorehold_top_spin="never")
    LH.sort_top_three(g, off_turn=True)
    LH.sort_top_three(g, off_turn=False)
    check("E never: no spin at all", g.m["top_spins"], 0)

    g = fresh([land(1), land(2), land(3)])
    check("F miracle_need reads a non-instant's own miracle cost",
          (LH.miracle_need(g, big()), LH.miracle_need(g, instant())), (4, 2))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Lorehold's Top policy (§0z164)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"lorehold_top_order": "value"}, {"A", "B"}),
        ({"lorehold_top_spin": "every"}, {"D", "E"}),
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
