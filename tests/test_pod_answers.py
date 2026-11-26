#!/usr/bin/env python3
"""§0z239 (queue item 50, step 4): the pod's answers on YOUR turn read the
mana it left untapped.

    python -m tests.test_pod_answers
    python -m tests.test_pod_answers --mutate   # 4 mutations, exact sets

Each case: a rendmaw game with `pod_mana` and `pod_answer_mana` on (unless
it says off), on a battlefield set by hand, opponent 0 given the mana the
case names, and one pod action called directly.

CASES
  A  ward reads mana: Tivit's {3} on a 3-mana removal needs 6 -- with 5
     left it is not paid, with 6 it is (on pod turn 6, where the old rule,
     6 >= 3 + 3, pays it either way)
  B  NEIGHBOUR: `pod_answer_mana` off, pod turn 6: the old rule pays it
  C  a counterspell needs its cost left: 1 mana, not cast; 2 mana, cast --
     charged 2, one counterspell fewer
  D  no turn-3 gate under the switch: on pod turn 2 with 2 mana left, cast
     (the old rule casts nothing before pod turn 3)
  E  a held answer (A6) at your end step: 2 mana left, not cast, counted
     unpaid, the permanent stays; 3 left, cast and charged
  F  decision 4's hold-up: a blue opponent with a counterspell left, 4
     mana, a 4-mana body arriving: 2 is kept up, 2 counted overspent
  G  the same reading for a held answer: no counterspell, an answer held,
     4 mana, a 4-mana body: 3 is kept up
  H  NEIGHBOUR: the switch off, F's setup: the body takes everything

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  ward reads the turn (WARD_READS_MANA False)        -> A
  counters read the ramp (COUNTER_READS_MANA False)  -> C, D
  held answers ignore mana (HELD_READS_MANA False)   -> E
  nothing kept up (KEEP_ANSWER_UP False)             -> F, G

UNMUTATED (§0z15): B and H are off under every rule here.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
from edhmc.decks import _pod_mana as M
from edhmc.decks import _removal as R
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(mana, turn=6, on=True, **cfg):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd,
                # pod_develop_gated off (§0z266): F and G pin the reserve
                # as the floor of the CHARGED body (§0z239); under the gate
                # it is tests/test_pod_development.py's H and J.
                {**DEFAULT_CFG, "pod_mana": True, "pod_answer_mana": on,
                 "pod_develop_gated": False, **cfg},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.commander_cast = True
    g.turn = turn
    for j, o in enumerate(g.opponents):
        o.mana_left = mana if j == 0 else 0.0
        o.counters_left = 0
    return g, g.opponents[0]


def countered(g, o):
    o.counters_left = 1
    row = g.counter_rolls[min(O.pod_turn(g), len(g.counter_rolls) - 1)]
    row[0] = [0.0] * len(row[0])
    card = max(g.library, key=lambda c: O.counter_threat(g, c))
    return O._countered(g, card, 0)


def run_cases():
    PASS.clear()
    FAIL.clear()

    got = []
    for m in (5.0, 6.0):
        g, o = game(m)
        got.append(O.ward_payable(g, 3, o))
    check("A Tivit's {3}: not with 5 left, paid with 6", got, [False, True])

    g, o = game(0.0, on=False)
    check("B NEIGHBOUR: off, pod turn 6: the old rule pays",
          O.ward_payable(g, 3, o), True)

    got = []
    for m in (1.0, 2.0):
        g, o = game(m)
        got.append((countered(g, o), o.mana_left, o.counters_left))
    check("C a counterspell needs 2: not with 1, cast with 2", got,
          [(False, 1.0, 1), (True, 2.0 - M.COUNTER_SPELL_MV, 0)])

    g, o = game(2.0, turn=2)
    check("D no turn-3 gate: pod turn 2, 2 left, cast", countered(g, o),
          True)

    got = []
    for m in (2.0, 3.0):
        g, o = game(m, held_answers=True)
        artist = next(c for c in g.library if c.name == "Blood Artist")
        g.board.append(EN.Permanent(card=artist, sick=False))
        o.held_rolls = [0.999] * 8
        o.held_threat = 0.0
        O.held_answer_window(g, "end")
        got.append((g.m["answers_held_unpaid"], g.m["answers_spent_end"],
                    any(p.card.name == "Blood Artist" for p in g.board),
                    o.mana_left))
    check("E a held answer: unpaid with 2, cast with 3", got,
          [(1, 0, True, 2.0), (0, 1, False, 3.0 - R.SPOT_SPELL_MV)])

    g, o = game(4.0)
    o.counters_left = 1
    o.body_pool = (O.PodBody(2, 4, False),)
    o.bodies, o.body_tapped, o.next_body = [], [], 0
    o.creatures = 1.0
    O.charge_growth(g, o, 0.0)
    check("F a counterspell's 2 kept up before a 4-mana body",
          (o.mana_left, g.m["pod_overspent"]),
          (M.COUNTER_SPELL_MV, 4.0 - (4.0 - M.COUNTER_SPELL_MV)))

    g, o = game(4.0)
    o.held_rolls = [0.999] * 8
    o.body_pool = (O.PodBody(2, 4, False),)
    o.bodies, o.body_tapped, o.next_body = [], [], 0
    o.creatures = 1.0
    O.charge_growth(g, o, 0.0)
    check("G a held answer's 3 kept up before a 4-mana body",
          o.mana_left, R.SPOT_SPELL_MV)

    g, o = game(4.0, on=False)
    o.counters_left = 1
    o.body_pool = (O.PodBody(2, 4, False),)
    o.bodies, o.body_tapped, o.next_body = [], [], 0
    o.creatures = 1.0
    O.charge_growth(g, o, 0.0)
    check("H NEIGHBOUR: off, the body takes everything", o.mana_left, 0.0)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z239: the pod's answers on your turn read its mana\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "ward reads the turn": ({"A"}, [("WARD_READS_MANA", False)]),
        "counters read the ramp": ({"C", "D"},
                                   [("COUNTER_READS_MANA", False)]),
        "held answers ignore mana": ({"E"}, [("HELD_READS_MANA", False)]),
        "nothing kept up": ({"F", "G"}, [("KEEP_ANSWER_UP", False)]),
    }
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")
        saved = [(name, getattr(O, name)) for name, _ in patches]
        for name, val in patches:
            setattr(O, name, val)
        try:
            broke = run_cases()
        finally:
            for name, val in saved:
                setattr(O, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
