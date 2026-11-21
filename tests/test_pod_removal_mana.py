#!/usr/bin/env python3
"""§0z240 (queue item 50, step 5): the pod's own-turn removal and wipes are
cast only when it has their cost untapped.

    python -m tests.test_pod_removal_mana
    python -m tests.test_pod_removal_mana --mutate   # 3 mutations, exact sets

Each case: a rendmaw game with `pod_mana` and `pod_removal_mana` on (unless
it says off), opponent 0 given the mana the case names, `held_answers` off,
and one pod removal event called directly with rolls that fire it.

CASES
  A  a wipe (WIPE_SPELL_MV, 4.5): with 4 left it is not cast -- your
     creature lives, `removal_unpaid_wipe` 1; with 5 it is cast, charged
  B  spot removal at a RIVAL: with 2 left, not cast and not charged; with
     3, charged
  C  spot removal at YOU: with 2 left your permanent stays; with 3 it goes
     and the opponent is left 0
  D  A/E removal at you (Ashnod's Altar): with 2 left it stays; with 3 it
     goes
  E  `removal_short_*` is counted with the gate OFF too, and the removal is
     cast: the reach a measurement reads in both legs
  F  NEIGHBOUR: the gate off and 0 mana: the wipe is cast, the deficit
     counted overspent, as in §0z237

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  wipes ignore mana (WIPE_READS_MANA False)   -> A
  spot ignores mana (SPOT_READS_MANA False)   -> B, C
  A/E ignores mana (AE_READS_MANA False)      -> D

UNMUTATED (§0z15): E and F are off under every rule here.
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


def game(mana, on=True, put=()):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "pod_mana": True, "pod_removal_mana": on,
                 "held_answers": False}, random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.commander_cast = True
    g.turn = 6
    for name in put:
        g.board.append(EN.Permanent(card=next(c for c in g.library
                                              if c.name == name),
                                    sick=False))
    o = g.opponents[0]
    o.mana_left = mana
    return g, o


def rolls(**at):
    r = [0.999] * 8
    for k, v in at.items():
        r[int(k[1:])] = v
    return r


def has(g, name):
    return any(p.card.name == name for p in g.board)


def run_cases():
    PASS.clear()
    FAIL.clear()

    got = []
    for m in (4.0, 5.0):
        g, o = game(m, put=("Blood Artist",))
        O.board_wipe(g, o, rolls(r2=0.0, r7=0.0))
        got.append((has(g, "Blood Artist"), g.m["removal_unpaid_wipe"],
                    o.mana_left))
    check("A a wipe: not with 4, cast with 5", got,
          [(True, 1, 4.0), (False, 0, 5.0 - M.WIPE_SPELL_MV)])

    got = []
    for m in (2.0, 3.0):
        g, o = game(m)
        O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.9999))
        got.append((g.m["pod_spent_spot"], o.mana_left))
    check("B at a rival: not with 2, charged with 3", got,
          [(0, 2.0), (R.SPOT_SPELL_MV, 3.0 - R.SPOT_SPELL_MV)])

    got = []
    for m in (2.0, 3.0):
        g, o = game(m, put=("Blood Artist",))
        O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.0))
        got.append((has(g, "Blood Artist"), o.mana_left))
    check("C at you: stays with 2, goes with 3", got,
          [(True, 2.0), (False, 3.0 - R.SPOT_SPELL_MV)])

    got = []
    for m in (2.0, 3.0):
        g, o = game(m, put=("Ashnod's Altar",))
        O.ae_removal(g, o, g.opponents[1:], rolls(r1=0.0, r3=0.0))
        got.append(has(g, "Ashnod's Altar"))
    check("D A/E at you: stays with 2, goes with 3", got, [True, False])

    g, o = game(2.0, on=False, put=("Blood Artist",))
    O.spot_removal(g, o, g.opponents[1:], rolls(r0=0.0, r3=0.0))
    check("E the gate off: short is counted, the removal cast",
          (g.m["removal_short_spot"], g.m["removal_unpaid_spot"],
           has(g, "Blood Artist")), (1, 0, False))

    g, o = game(0.0, on=False, put=("Blood Artist",))
    O.board_wipe(g, o, rolls(r2=0.0, r7=0.0))
    check("F NEIGHBOUR: off, 0 mana: the wipe is cast, overspent",
          (has(g, "Blood Artist"), g.m["pod_overspent_wipe"]),
          (False, M.WIPE_SPELL_MV))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z240: the pod's own-turn removal needs its cost\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "wipes ignore mana": ({"A"}, [("WIPE_READS_MANA", False)]),
        "spot ignores mana": ({"B", "C"}, [("SPOT_READS_MANA", False)]),
        "A/E ignores mana": ({"D"}, [("AE_READS_MANA", False)]),
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
