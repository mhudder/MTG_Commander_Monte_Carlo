#!/usr/bin/env python3
"""§0z247 (queue item 52): the pod's mana creatures and its development
gated by mana.

    python -m tests.test_pod_development
    python -m tests.test_pod_development --mutate   # 5 mutations, exact sets

`pod_mana_creatures`: a share of the pod's utility bodies taps for one mana
from its controller's next untap (302.6); the share is the census's
(`_pod_mana.POD_MANA_CREATURE_SHARE`, generated). `pod_develop_gated`: a
route piece is cast only when the mana is untapped, else it waits a round
and the kill with it; a body only from the mana above what the opponent
keeps up for your turn, else it waits, and is cast first next turn.

CASES
  A  the untap step counts the mana creatures on the battlefield: two
     mana bodies and a plain one add 2 to the row's mana
  B  a mana creature that died makes nothing: the same board after the
     mana bodies are killed adds 0
  C  `pod_mana_creatures` off: no body in a rolled pool taps for mana; on,
     some do, and only utility ones
  D  a route piece it cannot pay for waits a round: its landing turn +1,
     the kill +1 (its lead puts it at the kill turn), and nothing spent
  E  a piece it can pay for lands and is charged, the kill unmoved
  F  bodies: 4 mana above the reserve and arrivals of mana value 3 and 2 --
     the first is cast, the second waits (1 left is not 2); one body owed
  G  the owed body is cast first next turn, before the new ones
  H  the reserve is not spent on bodies: a counterspell left (its cost kept
     up) and exactly that much untapped -- no body is cast
  I  `pod_develop_gated` off: the old charge, every arrival paid down to
     the reserve, nothing owed
  J  §0z266, the default (`pod_gate_reserve` off): H's setup, and the body
     IS cast, from the mana the counterspell would have kept up

H pins `pod_gate_reserve=True` and I `pod_develop_gated=False`: both were
the defaults when they were written, and are not since §0z266.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  mana creatures make no mana (MANA_CREATURE_MANA 0)  -> A
  a delayed piece never moves the kill
    (delay_piece leaves kill_turn)                     -> D
  the reserve is spent on bodies (answer_reserve 0)    -> H
  an owed body is forgotten (body_debt never added)    -> G
  the reserve-drop switch never read (the default True) -> J   (§0z266,
    written before the run)

UNMUTATED (§0z15): B, C, E, F and I (J's neighbour); B and F still hold under the first
mutations (nothing to count; the order of payment unchanged), C is the
roll, E and I the paths no gate stops.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
from edhmc.decks import tivit_v1 as TV
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(**cfg):
    deck, cmd = TV.build()
    g = EN.Game(list(deck), cmd,
                # pod_body_mv_cap off (§0z264): F and G pin the gate on
                # bodies at their OWN mana values; the cap is
                # tests/test_pod_cost_cap.py's.
                {**DEFAULT_CFG, "pod_mana": True, "pod_body_mv_cap": False,
                 **cfg},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 6
    g.pod_seat = 0
    for o in g.opponents:
        o.mana_left, o.counters_left, o.held_rolls = 0.0, 0, None
        o.gift_lands, o.treasures, o.body_debt = 0.0, 0.0, 0
    return g, g.opponents[0]


def body(mv=2, mana=False, utility=None):
    utility = mana if utility is None else utility
    return O.PodBody(2, mv, False, 0 if utility else 2, utility, False, mana)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game(pod_mana_creatures=True)
    o.body_pool = (body(mana=True), body(mana=True), body())
    o.bodies, o.body_tapped, o.next_body, o.creatures = [], [], 0, 3.0
    spare = O.pod_mana_row(g, o).spare
    O.pod_untap(g, 0)
    check("A the untap step counts two mana creatures",
          o.mana_left - spare, 2.0)
    O.kill_pod_bodies(g, o, lambda b: b.mana)
    O.pod_untap(g, 0)
    check("B a dead mana creature makes nothing", o.mana_left - spare, 0.0)

    def rolled(on):
        cfg = {**DEFAULT_CFG, "pod_mana_creatures": on}
        opps, _, _ = O.make_pod(cfg, 4242)
        pool = opps[0].body_pool
        bodies = [pool[k] for k in range(len(pool))]
        return (sum(b.mana for b in bodies),
                all(b.utility for b in bodies if b.mana))
    off, on = rolled(False), rolled(True)
    check("C off no mana creatures; on some, all utility",
          (off[0], on[0] > 0, on[1]), (0, True, True))

    g, o = game(pod_develop_gated=True)
    o.pieces = (O.ThreatPiece("Creature", 2, 4, 0),)
    o.kill_turn = 6
    o.piece_lands = [6]
    o.mana_left = 3.0
    O.charge_pieces(g, o)
    check("D an unpaid piece waits a round, the kill with it",
          (o.piece_lands[0], o.kill_turn, o.mana_left), (7, 7, 3.0))
    g, o = game(pod_develop_gated=True)
    o.pieces = (O.ThreatPiece("Creature", 2, 4, 0),)
    o.kill_turn, o.piece_lands, o.mana_left = 6, [6], 5.0
    O.charge_pieces(g, o)
    check("E a piece it can pay for lands and is charged",
          (o.piece_lands[0], o.kill_turn, o.mana_left), (6, 6, 1.0))

    g, o = game(pod_develop_gated=True)
    o.body_pool = (body(3), body(2), body(1), body(1))
    o.bodies, o.body_tapped, o.next_body = [], [], 0
    o.creatures, o.mana_left = 2.0, 4.0
    O.charge_growth(g, o, 0.0)
    check("F the first body cast, the second waits; one owed",
          (o.creatures, o.body_debt, o.mana_left), (1.0, 1, 1.0))
    o.mana_left = 3.0
    before = o.creatures
    o.creatures = before + 1.0                         # this turn's growth
    O.charge_growth(g, o, before)
    check("G the owed body first, then the new one",
          (o.creatures, o.body_debt, o.mana_left), (3.0, 0, 0.0))

    from edhmc.decks._pod_mana import COUNTER_SPELL_MV
    for label, reserve, want in (
            ("H the reserve is not spent on bodies", True,
             (0.0, 1, COUNTER_SPELL_MV)),
            ("J no reserve before bodies (the default): the body is cast",
             None, (1.0, 0, COUNTER_SPELL_MV - 1.0))):
        g, o = game(pod_develop_gated=True,
                    **({} if reserve is None else {"pod_gate_reserve": reserve}))
        o.body_pool = (body(1),)
        o.bodies, o.body_tapped, o.next_body = [], [], 0
        o.counters_left = 1
        o.creatures, o.mana_left = 1.0, COUNTER_SPELL_MV
        O.charge_growth(g, o, 0.0)
        check(label, (o.creatures, o.body_debt, o.mana_left), want)

    g, o = game(pod_develop_gated=False)
    o.body_pool = (body(3), body(2))
    o.bodies, o.body_tapped, o.next_body = [], [], 0
    o.creatures, o.mana_left = 2.0, 4.0
    O.charge_growth(g, o, 0.0)
    check("I gate off: every arrival charged, nothing owed",
          (o.creatures, o.body_debt, o.mana_left), (2.0, 0, 0.0))
    return set(FAIL)


def _keep_kill(g, o, k):
    o.piece_lands[k] = O.pod_turn(g) + 1


def _no_debt(g, o, before):
    o.body_debt = 0
    return _real_growth(g, o, before)


_real_growth = O.charge_growth


def main() -> int:
    if not MUTATE:
        print("§0z247: the pod's mana creatures and its gated development\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "mana creatures make no mana": (
            {"A"}, [("MANA_CREATURE_MANA", 0.0)]),
        "a delayed piece never moves the kill": (
            {"D"}, [("delay_piece", _keep_kill)]),
        "the reserve is spent on bodies": (
            {"H"}, [("answer_reserve", lambda g, o: 0.0)]),
        "an owed body is forgotten": (
            {"G"}, [("charge_growth", _no_debt)]),
        "the reserve-drop switch never read": (
            {"J"}, [("POD_DEFAULTS",
                     {**O.POD_DEFAULTS, "pod_gate_reserve": True})]),
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
