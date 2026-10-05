#!/usr/bin/env python3
"""Rogue's Passage: "{4}, {T}: Target creature can't be blocked this turn."
(§0z107)

    python -m tests.test_rogues_passage
    python -m tests.test_rogues_passage --mutate   # 1 mutation, exact set

It was a colourless land in karlov and tivit, and tivit's `script=` named a
function nothing defined. Now `opponents.rogues_passage` is a pilot step
before blocks and `damage_through` never offers an unblockable attacker to
the chump assignment.

CASES
  A  damage_through: a 5-power attacker against three blockers deals 0;
     marked unblockable this turn it deals 5
  B  the mark expires: the same attacker on the NEXT turn deals 0 again
  C  the step fires when an attacker would be chumped: the Passage taps,
     four other lands pay, `passage_activations` counts 1
  D  NEIGHBOUR: it does not fire when nothing would be blocked (no
     blockers), and the Passage stays untapped
  E  NEIGHBOUR: it does not fire on three spare mana, and the Passage is
     left untapped (it cannot pay for itself)
  F  the target is the COMMANDER when the commander would be blocked, even
     beside a bigger attacker. Four creatures a seat, which is two blockers
     at `block_share` 0.6, so both attackers would be chumped -- with one
     blocker the chump falls on the bigger body and the commander was never
     at risk, which is what this case's first draft got wrong
  G  karlov's combat, end to end: a blocked Karlov with the Passage and
     four spare lands deals his power to the pod

MUTATION, WRITTEN BEFORE THE RUN, exact set:
  rogues_passage=False (the card as a plain land)   -> C, F, G

UNMUTATED (§0z15): A and B drive `damage_through` directly, and D and E are
the cases where the step correctly does nothing.
"""
import sys

from edhmc import engine as EN
from edhmc import karlov as KA
from edhmc import opponents as OPP
from edhmc.decks import karlov_v2
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA = {}
KDECK, KCMD = karlov_v2.build()
PASSAGE = next(c for c in KDECK if c.name == "Rogue's Passage")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def body(name, power):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=power,
                   toughness=power, cost={"gen": 2})


def land(colour):
    return EN.Card(name=f"Land {colour}", types=frozenset({"Land"}),
                   is_land=True, produces=frozenset({colour}))


def game(blockers=3.0, spare=4):
    g = KA.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, **EXTRA), 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 5
    g.board.append(EN.Permanent(card=PASSAGE, sick=False))
    for _ in range(spare):
        g.board.append(EN.Permanent(card=land("W"), sick=False))
    for o in g.opponents:
        o.alive, o.creatures, o.goaded_birds = True, blockers, 0
    return g


def attacker(g, card):
    p = EN.Permanent(card=card, sick=False)
    g.board.append(p)
    return p


def passage(g):
    return next(p for p in g.board if p.card.name == "Rogue's Passage")


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    big = attacker(g, body("Big", 5))
    before = OPP.damage_through(g, [big])
    g.unblockable = (g.turn, {id(big)})
    check("A an unblockable attacker is never chumped",
          (before, OPP.damage_through(g, [big])), (0.0, 5.0))

    g.turn += 1
    check("B the mark lasts one turn", OPP.damage_through(g, [big]), 0.0)

    g = game()
    big = attacker(g, body("Big", 5))
    fired = OPP.rogues_passage(g, [big], lambda c: KA.pay_cost(g, c))
    check("C fires when an attacker would be chumped",
          (fired, passage(g).tapped, g.m["passage_activations"],
           OPP.damage_through(g, [big])), (True, True, 1, 5.0))

    g = game(blockers=0.0)
    big = attacker(g, body("Big", 5))
    fired = OPP.rogues_passage(g, [big], lambda c: KA.pay_cost(g, c))
    check("D NEIGHBOUR: no blockers, no activation",
          (fired, passage(g).tapped), (False, False))

    g = game(spare=3)
    big = attacker(g, body("Big", 5))
    fired = OPP.rogues_passage(g, [big], lambda c: KA.pay_cost(g, c))
    check("E NEIGHBOUR: three spare mana cannot pay, Passage left untapped",
          (fired, passage(g).tapped), (False, False))

    g = game(blockers=4.0)                # int(4 * 0.6) = 2 blockers
    cmdr = attacker(g, KCMD)
    huge = attacker(g, body("Huge", 9))
    g.karlov_counters = 0                 # Karlov is a 1/1 here
    OPP.rogues_passage(g, [cmdr, huge], lambda c: KA.pay_cost(g, c))
    check("F the commander is the target when it would be blocked",
          id(cmdr) in OPP.unblockable_ids(g), True)

    g = game(blockers=3.0)
    cmdr = attacker(g, KCMD)
    g.karlov_counters = 6                 # a 7/7 Karlov, chumped alone
    for o in g.opponents:
        o.life = 40.0
    KA.combat(g)
    check("G karlov's combat: a blocked Karlov connects through the Passage",
          g.m["combat_damage"] > 0, True)
    return set(FAIL)


def main() -> int:
    global EXTRA
    if not MUTATE:
        print("Rogue's Passage (§0z107)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact set\n")
    want = {"C", "F", "G"}
    EXTRA = {"rogues_passage": False}
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
