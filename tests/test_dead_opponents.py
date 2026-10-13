#!/usr/bin/env python3
"""Eliminated opponents take no turns (§0z133; `dead_opponents_act`).

    python -m tests.test_dead_opponents
    python -m tests.test_dead_opponents --mutate   # 3 mutations, exact sets

An eliminated player is out of the game. Five sites let one act anyway, by
omission: `opponents_act` regrew its board and rolled its spot removal,
artifact removal and wraths at you, and counted its threat when a living
opponent chose a target; `countered` let it spend a counterspell; the
"weakest board" `damage_through` defaults to ranged over the dead; rendmaw's
Ezuri's Predation aimed at seat 0 dead or alive; lorehold opened a window on
every opponent's turn, the dead ones' included. Each case runs both rules:
`dead_opponents_act=False` (the fix) and True (the old loops).

CASES
  A  a dead opponent whose removal rolls fire (its wrath held back, which
     would also clear the board it regrows): under the fix its board stays
     empty and your creature survives; under the old rule it regrows and
     its spot removal takes the creature
  B  a living opponent's spot removal, its share roll set between the share
     with the dead counted and without: the fix aims it at you, the old
     rule at a rival
  C  a dead blue opponent with a counterspell left: the old rule counters
     your spell, the fix does not
  D  `damage_through` with no defender named: the weakest LIVING board
     blocks your attacker; on the old rule the dead player's empty board
     lets it through
  E  `acting` -- the pod's turns, lorehold's windows: two with one player
     out, three on the old rule
  F  Ezuri's Predation with seat 0 dead: the Horrors are sized off and fight
     the living (fix only)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the dead always act (dead_act -> True)          -> A, B, C, D, E, F
  the dead never act (dead_act -> False)          -> A, B, C, D, E
  acting counts every seat                        -> E, F

UNMUTATED (§0z15): every case reads `dead_act`, so the first two mutations
are the whole switch; F has no old-rule half (it was seat 0 regardless).
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


def game(old):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd, dict(DEFAULT_CFG, dead_opponents_act=old),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    for o in g.opponents:
        o.life, o.creatures, o.alive, o.counters_left = 40.0, 3.0, True, 0
    dead = g.opponents[0]
    dead.alive, dead.life, dead.creatures = False, 0.0, 0.0
    # every roll a miss, except where a case sets one
    g.opp_rolls = [[[0.99] * OPP.N_SLOTS for _ in g.opponents]
                   for _ in range(30)]
    return g


def body(power=4, name="Bear"):
    c = EN.Card(name=name, types=frozenset({"Creature"}), power=power,
                toughness=power, threat=5.0)
    return EN.Permanent(card=c, sick=False, base_p=power, base_t=power)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    out = []
    for old in (False, True):
        g = game(old)
        g.board.append(body())
        g.opp_rolls[6][0] = [0.0] * OPP.N_SLOTS        # the dead seat fires:
        g.opp_rolls[6][0][2] = 0.99                    # removal, not a wrath
        OPP.opponents_act(g)
        out.append((len(g.board), g.opponents[0].creatures > 0))
    check("A the dead do not act; on the old rule they regrow and remove",
          out, [(1, False), (0, True)])

    out = []
    for old in (False, True):
        g = game(old)
        g.board.append(body())
        live, other = g.opponents[1], g.opponents[2]
        with_dead = OPP.your_share(g, live, [g.opponents[0], other])
        without = OPP.your_share(g, live, [other])
        g.opp_rolls[6][1][0] = 0.0                     # its spot removal fires
        g.opp_rolls[6][1][3] = (with_dead + without) / 2
        OPP.opponents_act(g)
        out.append((without > with_dead, len(g.board)))
    check("B a living opponent's share no longer counts the dead",
          out, [(True, 0), (True, 1)])

    out = []
    for old in (False, True):
        g = game(old)
        g.opponents[0].counters_left = 1
        g.counter_rolls = [[[0.0] * 3 for _ in range(OPP.N_COUNTER_SLOTS)]
                           for _ in range(30)]
        spell = EN.Card(name="Big Spell", types=frozenset({"Sorcery"}),
                        threat=9.0)
        out.append(OPP.countered(g, spell, 0))
    check("C a dead player's counterspell: never under the fix",
          out, [False, True])

    out = []
    for old in (False, True):
        g = game(old)
        g.opponents[1].creatures, g.opponents[2].creatures = 5.0, 6.0
        out.append(OPP.damage_through(g, [body(5)]))
    check("D the weakest LIVING board blocks; the dead let it through",
          out, [0.0, 5.0])

    check("E acting: two seats with one out, three on the old rule",
          [len(OPP.acting(game(False))), len(OPP.acting(game(True)))],
          [2, 3])

    g = game(False)
    g.opponents[1].creatures, g.opponents[2].creatures = 2.0, 5.0
    EN.run_etb(g, EN.Permanent(card=RM.EZURIS_PREDATION, sick=False))
    horrors = sum(1 for p in g.board if p.card.name.startswith("Horror")
                  or "Horror" in p.card.name)
    check("F Predation: sized off the living, fights a living player",
          (horrors, g.opponents[0].creatures, g.opponents[1].creatures),
          (2, 0.0, 0.0))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Eliminated opponents take no turns (§0z133)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "the dead always act":
            ({"A", "B", "C", "D", "E", "F"}, OPP, "dead_act",
             lambda g: True),
        "the dead never act":
            ({"A", "B", "C", "D", "E"}, OPP, "dead_act", lambda g: False),
        "acting counts every seat":
            ({"E", "F"}, OPP, "acting", lambda g: list(g.opponents)),
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
