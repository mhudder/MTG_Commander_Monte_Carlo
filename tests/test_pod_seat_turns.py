#!/usr/bin/env python3
"""§0z179: the pod's round as three turns, in seat order.

    python -m tests.test_pod_seat_turns
    python -m tests.test_pod_seat_turns --mutate   # 3 mutations, exact sets

`opponents.pod_phase` ran the round by KIND -- every opponent's chip damage,
then every clock, then every opponent's removal -- so no opponent's turn was
a unit. Under `pod_seat_turns` each opponent takes its turn whole, in seat
order: main 1 (its pieces and your responses, its kill if due, then its
removal), combat (its chip damage, its goaded Birds), main 2 (its board
grows), end step. Each case drives the real `pod_phase` on a karlov game at
pod turn 5, with the per-seat functions wrapped to record what ran, in order.

CASES
  A  three living opponents: pieces, clock, removal, chip, goad, grow, end
     for seat 0, then seat 1, then seat 2, then the held answers
  B  `before_act` (karlov's `opponent_activity`) runs ONCE, after seat 0's
     kill and before seat 0's removal
  C  NEIGHBOUR: `pod_seat_turns=False` is the old round -- every seat's
     pieces at once first, and no per-seat clock or chip at all
  D  an eliminated opponent takes no turn: no step of seat 1 runs
  E  a kill that ends the game ends the round: nothing runs after it
  F  each seat's chip damage reads the board it STARTED its turn with -- its
     own growth comes after
  G  NEIGHBOUR: `pod_seat_grow="start"` grows the board first, before its
     pieces and its kill
  H  `g.pod_seat` names the seat whose step is running, and is None after
  I  before pod turn 3: boards grow, and no removal or end step runs

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pod_seat_turns=False everywhere        -> A, B, E, F, G, H
  pod_seat_grow="start" everywhere       -> A, F
  dead_opponents_act=True everywhere     -> D

THE FIRST RUN FAILED B, AND THE TEST WAS WRONG: its `before_act` lambda
appended to the `log` name that existed when it was CALLED -- case A's list,
since B's is bound only when `run_round` returns. `run_round` records the
activity into its own log now. The first mutation run also crashed on H
(`g.pod_seat` is never set by the old round) instead of failing it; H reads
it with `getattr` now. And the second mutation then passed F, which it must
break: the pieces step OVERWROTE the turn-start board that the growth step had
recorded, so with growth first "the start" was the grown board. The first
step to run records it now, and the second keeps it. The expected sets above
are as first written.

UNMUTATED (§0z15): C and G are the knobs' neighbours; I holds in both
rounds (the turn-3 gate is the same line's twin in each).
"""
import sys

import edhmc.karlov as KV
import edhmc.opponents as OPP
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}          # a mutation's cfg overrides, under each case's own

DECK, CMD = build_pending("karlov")
NAMES = ("respond_to_pieces", "resolve_clock_seat", "opponent_removal",
         "chip_damage_seat", "goaded_combat", "grow_board",
         "pod_end_step_hook", "end_step_answers")
LABEL = dict(zip(NAMES, ("pieces", "clock", "removal", "chip", "goad",
                         "grow", "end", "answers")))


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(turn=5, **cfg):
    g = KV.KarlovGame(list(DECK), CMD,
                      dict(DEFAULT_CFG, watch=frozenset(),
                           **{**EXTRA_CFG, **cfg}), 1)
    g.opening_hand()
    g.turn = turn
    for o in g.opponents:
        o.kill_turn = 99                 # no clock fires unless a case says so
    return g


def run_round(g, activity=False, on_clock=None):
    """`pod_phase` with every per-seat step recorded. Returns (log, seats,
    creatures): `log` the steps as "name seat", `seats` whether `g.pod_seat`
    named the step's seat, `creatures` each chip step's attacker board and
    each seat's board as its turn began."""
    log, seats, boards = [], [], {"start": {}, "chip": {}}
    real = {n: getattr(OPP, n) for n in NAMES}

    def wrap(name):
        def rec(*a, **kw):
            gg = a[0]
            if name == "grow_board":
                opp = a[0]
                gg = g
                seat = g.opponents.index(opp)
            elif name in ("respond_to_pieces", "goaded_combat"):
                seat = kw.get("seat")
            elif name == "end_step_answers":
                seat = None
            else:
                seat = a[1]
            # The board AS THE TURN BEGAN: the first of these two steps to
            # run for the seat records it, and the second must not overwrite.
            if (name in ("respond_to_pieces", "grow_board")
                    and seat is not None):
                boards["start"].setdefault(seat, g.opponents[seat].creatures)
            if name == "chip_damage_seat":
                boards["chip"][seat] = g.opponents[seat].creatures
            log.append(f"{LABEL[name]} {seat}")
            if seat is not None:
                seats.append(getattr(gg, "pod_seat", None) == seat)
            out = real[name](*a, **kw)
            if name == "resolve_clock_seat" and on_clock is not None:
                on_clock(gg, seat)
            return out
        return rec

    before_act = (lambda gg: log.append("activity")) if activity else None
    for n in NAMES:
        setattr(OPP, n, wrap(n))
    try:
        OPP.pod_phase(g, before_act=before_act)
    finally:
        for n, f in real.items():
            setattr(OPP, n, f)
    return log, seats, boards


def seat_steps(i):
    return [f"{x} {i}" for x in ("pieces", "clock", "removal", "chip", "goad",
                                 "grow", "end")]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    log, seats, boards = run_round(g)
    check("A seat 0, 1, 2 each whole, then the held answers",
          log, seat_steps(0) + seat_steps(1) + seat_steps(2) + ["answers None"])

    g = game()
    log, _, _ = run_round(g, activity=True)
    at = log.index("activity") if "activity" in log else -1
    check("B before_act once, after seat 0's kill, before its removal",
          (log.count("activity"), log[at - 1:at + 2] if at > 0 else None),
          (1, ["clock 0", "activity", "removal 0"]))

    g = game(pod_seat_turns=False)
    log, _, _ = run_round(g)
    check("C pod_seat_turns=False: every seat's pieces first, no seat clock",
          (log[0], any(x.startswith(("clock", "chip")) for x in log)),
          ("pieces None", False))

    g = game()
    g.opponents[1].alive = False
    g.opponents[1].life = 0.0
    log, _, _ = run_round(g)
    check("D an eliminated opponent takes no turn",
          [x for x in log if x.endswith(" 1")], [])

    g = game()

    def kill_you(gg, seat):
        if seat == 0:
            gg.result = "loss"
    log, _, _ = run_round(g, on_clock=kill_you)
    check("E a kill that ends the game ends the round",
          (log[-1] if log else None, "answers None" in log),
          ("clock 0", False))

    g = game()
    log, _, boards = run_round(g)
    check("F each seat's chip reads the board it started its turn with",
          (len(boards["chip"]) == 3
           and all(boards["chip"][i] == boards["start"][i] for i in range(3))),
          True)

    g = game(pod_seat_grow="start")
    log, _, _ = run_round(g)
    check("G pod_seat_grow=start grows each board before its pieces",
          log[:3], ["grow 0", "pieces 0", "clock 0"])

    g = game()
    log, seats, _ = run_round(g)
    check("H g.pod_seat names the running seat, None after",
          (bool(seats) and all(seats), getattr(g, "pod_seat", None)),
          (True, None))

    g = game(turn=2)
    log, _, _ = run_round(g)
    check("I before pod turn 3: boards grow, no removal or end step",
          (sum(x.startswith("grow") for x in log),
           any(x.startswith(("removal", "end")) for x in log)), (3, False))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z179: the pod's round as three turns, in seat order\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "pod_seat_turns=False everywhere":
            ({"A", "B", "E", "F", "G", "H"}, {"pod_seat_turns": False}),
        'pod_seat_grow="start" everywhere':
            ({"A", "F"}, {"pod_seat_grow": "start"}),
        "dead_opponents_act=True everywhere":
            ({"D"}, {"dead_opponents_act": True}),
    }
    bad = 0
    for label, (want, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
