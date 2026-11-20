#!/usr/bin/env python3
"""§0z237 (queue item 50, step 2): what the pod spends on its own turn.

    python -m tests.test_pod_spending
    python -m tests.test_pod_spending --mutate   # 4 mutations, exact sets

Each case: a rendmaw game with `pod_mana` on, on a battlefield set by hand,
opponent 0 given 10 mana (`mana_left`) unless the case says otherwise, and
one pod action called directly. A case reads what was charged.

CASES
  A  its untap step: `mana_left` is its row's `spare` on the pod's turn
  B  route pieces: the one landing THIS turn (mana value 3) is charged, the
     one that landed last turn is not -- 10 -> 7
  C  a wipe that fires is charged WIPE_SPELL_MV (the census's 4.5)
  D  spot removal aimed at a RIVAL is charged SPOT_SPELL_MV (3) -- the
     owner, 2026-11-20: the pod casts it either way
  E  spot removal at you, at Roaming Throne (ward {2}), on pod turn 10 where
     the ward is payable: the spell and the ward, 3 + 2 -- 10 -> 5
  F  a HELD answer (A6) is not charged on its own turn: 10 stays 10
  G  a body arriving is charged ITS mana value (the pool's first body, 3),
     not the pool's mean (2.5)
  H  a deficit stops at 0 and is counted: 2 mana, 5 spent -> 0, overspent 3
  I  NEIGHBOUR: `pod_mana` off -- nothing is charged, nothing is counted

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  removal at a rival is not charged     -> D
  a paid ward is not charged            -> E
  a deficit is not clamped              -> H
  a body costs the pool's mean          -> G

UNMUTATED (§0z15): A, B, C and F read rules no mutation here touches; I is
off under every rule.
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


def game(turn=6, on=True, **cfg):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "pod_mana": on, "held_answers": False, **cfg},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.commander_cast = True
    g.turn = turn
    o = g.opponents[0]
    o.mana_left = 10.0
    return g, o


def rolls(**at):
    r = [0.999] * 8
    for k, v in at.items():
        r[int(k[1:])] = v
    return r


def spent(g, what):
    return g.m[f"pod_spent_{what}"]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game(turn=5)
    O.pod_untap(g, 0)
    check("A the untap step: its row's spare",
          o.mana_left, O.pod_mana_row(g, o).spare)

    g, o = game(turn=5)
    o.pieces = (O.ThreatPiece("Creature", 2, 3, 1),
                O.ThreatPiece("Creature", 2, 2, 1))
    o.piece_lands = [5, 4]
    O.charge_pieces(g, o)
    check("B the piece landing this turn, 10 -> 7",
          (o.mana_left, spent(g, "piece")), (7.0, 3.0))

    g, o = game(turn=6)
    O.board_wipe(g, o, rolls(r2=0.0))
    check("C a wipe that fires: 4.5",
          (spent(g, "wipe"), o.mana_left), (M.WIPE_SPELL_MV,
                                            10.0 - M.WIPE_SPELL_MV))

    g, o = game(turn=6)
    O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.9999))
    check("D spot removal at a rival: 3", (spent(g, "spot"), o.mana_left),
          (R.SPOT_SPELL_MV, 10.0 - R.SPOT_SPELL_MV))

    g, o = game(turn=10)
    g.board.append(EN.Permanent(card=next(c for c in g.library
                                          if c.name == "Roaming Throne"),
                                sick=False))
    O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.0))
    check("E at you, through Roaming Throne's ward {2}: 3 + 2, 10 -> 5",
          (g.m["ward_paid"], o.mana_left), (1, 5.0))

    g, o = game(turn=6, held_answers=True, held_answer_share=1.0,
                held_answer_bar=99.0)
    g.board.append(EN.Permanent(card=next(c for c in g.library
                                          if c.name == "Blood Artist"),
                                sick=False))
    O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.0))
    check("F a held answer is not charged on its own turn",
          (g.m["answers_held"], o.mana_left), (1, 10.0))

    g, o = game(turn=6)
    o.body_pool = (O.PodBody(2, 3, False), O.PodBody(2, 1, False))
    o.bodies, o.body_tapped, o.next_body = [], [], 0
    o.creatures = 1.2
    O.charge_growth(g, o, 0.5)
    check("G a body arriving: its own mana value, 3",
          (spent(g, "body"), o.mana_left), (3.0, 7.0))

    g, o = game(turn=6)
    o.mana_left = 2.0
    O.pod_spend(g, o, 5.0, "body")
    check("H a deficit stops at 0 and is counted",
          (o.mana_left, g.m["pod_overspent"], g.m["pod_overspend_events"]),
          (0.0, 3.0, 1))

    g, o = game(turn=6, on=False)
    O.pod_spend(g, o, 5.0, "body")
    O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.9999))
    check("I NEIGHBOUR: pod_mana off charges nothing",
          (o.mana_left, "pod_spent_body" in g.m, "pod_spent_spot" in g.m),
          (10.0, False, False))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z237: what the pod spends on its own turn\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "removal at a rival is not charged": (
            {"D"}, [("charge_at_rival", lambda g, o, cost, what: None)]),
        "a paid ward is not charged": (
            {"E"}, [("charge_ward", lambda g, o, n: None)]),
        "a deficit is not clamped": ({"H"}, [("POD_SPEND_CLAMP", False)]),
        "a body costs the pool's mean": (
            {"G"}, [("ARRIVALS_BY_IDENTITY", False)]),
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
