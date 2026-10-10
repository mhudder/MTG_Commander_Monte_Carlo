#!/usr/bin/env python3
"""Item 8: the pod's clock and the horizon both count ROUNDS (§0z86).

    python -m tests.test_pod_clock
    python -m tests.test_pod_clock --mutate   # 3 mutations, exact sets

Time Sieve's priority move flipped sign between horizons (§0z44), and the
guess written down was "extra turns count against the horizon". Two things
were wrong, and both were the same concept modelled two ways:

  - every pod timer read `g.turn`, which a tivit extra turn advances, so an
    extra turn brought each opponent's KILL a round closer while giving them
    no turn to take it in. `opponents.pod_turn(g)` is your turns minus the
    extra turns taken (`pod_clock_rounds`).
  - tivit counted extra turns against the horizon and lorehold did not, so
    T10 meant ten of your turns in one engine and ten rounds in the other.
    Both count rounds now (`horizon_counts`), and tivit's chain is bounded by
    `extra_turns_round_cap` instead.

CASES
  A  pod_turn: turn 10 with 3 extra turns taken is pod turn 7
  B  NEIGHBOUR: `pod_clock_rounds=False` reads g.turn (10)
  C  a clock armed for turn 8 does NOT fire on your turn 9 when two of your
     turns were extra -- the pod has lived through 7
  D  a clock that fires re-arms from the POD's turn: fired at pod turn 8
     (your turn 10, two extra) it re-arms for 8 + clock_rearm = 12
  E  five extra turns at played 19 of 20: all five are taken, and the
     horizon still reads 19 -- an extra turn is not a round
  F  a hundred extra turns queued: the chain stops at extra_turns_round_cap
     (40), not at the horizon
  G  NEIGHBOUR: lorehold, whose extra turns never advanced g.turn, reads
     pod_turn == g.turn
  H  NEIGHBOUR: `horizon_counts="turns"` is the old rule -- one of the five
     is taken and the horizon reads 20

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pod_turn reads g.turn                      -> A, C, D
  the horizon counts your turns              -> E, F
  the chain has no cap                       -> F

CASE C FAILED ITS FIRST MUTATION RUN ON THE TEST, NOT THE ENGINE: it read
`clock_fired`, which a clock that kills an opponent sets and then CLEARS when
it re-arms -- so a fired clock and a waiting one looked the same. It reads the
kill turn, who is alive and the result now.

UNMUTATED (§0z15): B, G, H are neighbours and knobs.
"""
import sys

import edhmc.lorehold as L
import edhmc.opponents as OPP
import edhmc.tivit as T
from edhmc.decks import lorehold_v17 as LM
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}          # a mutation's cfg overrides, under each case's own


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


TDECK, TCMD = TM.build()
LDECK, LCMD = LM.build()


def tgame(turn=10, taken=0, **cfg):
    g = T.TivitGame(list(TDECK), TCMD,
                    {**DEFAULT_CFG, **EXTRA_CFG, **cfg}, 3)
    g.turn = turn
    g.m["extra_turns_taken"] = taken
    return g


def stub_turn(g, extra=False):
    """A turn that only advances the counters take_turn advances."""
    g.turn += 1
    if extra:
        g.m["extra_turns_taken"] += 1


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = tgame(10, 3)
    check("A pod_turn is your turns minus extra turns", OPP.pod_turn(g), 7)
    g = tgame(10, 3, pod_clock_rounds=False)
    check("B pod_clock_rounds=False reads g.turn", OPP.pod_turn(g), 10)

    g = tgame(9, 2)
    opp = g.opponents[0]
    opp.kill_turn, opp.clock_fired = 8, False
    for o in g.opponents[1:]:
        o.kill_turn = 99
    OPP.resolve_clocks(g)
    check("C a turn-8 clock waits out two extra turns",
          (opp.kill_turn, sum(o.alive for o in g.opponents), g.result),
          (8, 3, None))

    g = tgame(10, 2)
    opp = g.opponents[0]
    opp.kill_turn, opp.clock_fired = 8, False
    for o in g.opponents[1:]:
        o.kill_turn = 99
    OPP.resolve_clocks(g)
    rearm = g.cfg.get("clock_rearm", 4)
    # Resolution picks a victim by threat; if it picked YOU the game is over
    # and nothing re-arms. The seed puts it on an opponent -- say so.
    check("D the clock re-arms from the pod's turn",
          (g.result, opp.kill_turn), (None, 8 + rearm))

    real = T.take_turn
    T.take_turn = stub_turn
    try:
        g = tgame(19, 0)
        g.extra_turns = 5
        played = T.take_extra_turns(g, 19, 20)
        check("E five extra turns at 19 of 20: all taken, horizon 19",
              (g.m["extra_turns_taken"], played), (5, 19))
        g = tgame(0, 0)
        g.extra_turns = 100
        T.take_extra_turns(g, 0, 20)
        check("F the chain stops at extra_turns_round_cap",
              g.m["extra_turns_taken"], 40)
        g = tgame(19, 0, horizon_counts="turns")
        g.extra_turns = 5
        played = T.take_extra_turns(g, 19, 20)
        check("H horizon_counts=turns: one taken, horizon 20",
              (g.m["extra_turns_taken"], played), (1, 20))
    finally:
        T.take_turn = real

    g = L.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, **EXTRA_CFG), 3)
    g.turn = 9
    g.m["extra_turns"] = 3
    check("G lorehold's pod turn is g.turn", OPP.pod_turn(g), 9)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("Item 8: the pod clock and the horizon count rounds\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "pod_turn reads g.turn":
            ({"A", "C", "D"}, (OPP, "pod_turn", lambda g: g.turn), {}),
        "the horizon counts your turns":
            ({"E", "F"}, None, {"horizon_counts": "turns"}),
        "the chain has no cap":
            ({"F"}, None, {"extra_turns_round_cap": 10 ** 6}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        if patch:
            owner, name, fn = patch
            real = getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
                setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
