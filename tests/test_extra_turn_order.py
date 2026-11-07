#!/usr/bin/env python3
"""§0z176: tivit's extra turns come BEFORE the pod's round (CR 500.7).

    python -m tests.test_extra_turn_order
    python -m tests.test_extra_turn_order --mutate   # 3 mutations, exact sets

"Some effects can give a player extra turns. They do this by adding the turns
directly after the specified turn." Tivit ran the pod's round at the end of
`take_turn` and took the extra turns after it, so the opponents' removal and
kill clocks acted between your turn and the turns it had bought. Lorehold was
fixed for the same thing in §0z153. `tivit.play_round` is the round now --
your turn, its extra turns, then the pod -- and `simulate`, `test_time_sieve`
and `diag_time_sieve` all drive the game through it.

Each case drives `play_round` on a real tivit game, with `take_turn` and
`opponents.pod_phase` wrapped to record what ran, in order. Two extra turns
are queued during the first turn by the wrapper, so the order is the engine's
and the extra turns are not.

CASES
  A  two extra turns: the order is turn, extra, extra, pod
  B  the pod acts on the board the LAST extra turn left: `g.turn` is 3 when
     it acts, and its own clock (`pod_turn`) reads 1 -- one round
  C  one pod round per round, whatever the extra turns (`pod_rounds` 1)
  D  NEIGHBOUR: `extra_turns_before_pod=False` is the old order --
     turn, pod, extra, extra
  E  NEIGHBOUR: no extra turn -- turn, pod
  F  a game won on your turn gives the pod no round -- turn
  G  every driver of the round calls `play_round` and none reimplements it
     (no `take_extra_turns(` call outside `tivit.play_round`)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  play_round runs the pod before the extra turns     -> A, B
  an extra turn hands the pod a round (§0z86's bug)  -> A, B, C, D
  pod_round never runs the pod                       -> A, B, C, D, E

THE FIRST MUTATION RUN BROKE D TOO, AND THE DEFECT WAS THE STAND-IN: it called
`take_turn` and then `pod_round` itself, and with the knob off `take_turn`
runs the pod already, so D saw two pod rounds. The stand-in sets the knob and
calls the real `play_round` now. Its first run then broke F, and that was the
test as well: the wrapper set the win AFTER the real turn returned, by which
time the old order had already run the pod inside `take_turn`. The win is set
before the turn now, so the game is won during it. The expected sets above are
as first written.

UNMUTATED (§0z15): D and E are the neighbours, and F's early return is the
same `g.result` check every engine makes -- each mutation keeps it. G reads
source text, so a mutation that patches a function cannot reach it; it fails
if a new driver copies the loop instead of calling `play_round`.
"""
import inspect
import sys

import diagnostics.diag_time_sieve as DIAG
import edhmc.opponents as OPP
import edhmc.tivit as T
import tests.test_time_sieve as SIEVE
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}          # a mutation's cfg overrides, under each case's own

DECK, CMD = TM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def drive(n_extra=0, win=False, **cfg):
    """One `play_round` from turn 0. Returns (log, pod_seen, game): `log` the
    calls in order, `pod_seen` (g.turn, pod_turn) at each pod round."""
    g = T.TivitGame(list(DECK), CMD,
                    dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                         **{**EXTRA_CFG, **cfg}), 7)
    for o in g.opponents:
        o.life = float(10 ** 9)          # nobody dies: the order is the test
    g.opening_hand()
    log, seen = [], []
    real_turn, real_pod = T.take_turn, OPP.pod_phase

    def turn(g, extra=False):
        log.append("extra" if extra else "turn")
        if win and not extra:
            g.result = "win"             # won DURING the turn, before its end
        real_turn(g, extra=extra)
        if not extra:
            g.extra_turns = n_extra      # bought on this turn

    def pod(g, *a, **kw):
        log.append("pod")
        seen.append((g.turn, OPP.pod_turn(g)))
        g.your_life = max(g.your_life, 40.0)
        return real_pod(g, *a, **kw)

    T.take_turn, OPP.pod_phase = turn, pod
    try:
        T.play_round(g, 0, 20)
    finally:
        T.take_turn, OPP.pod_phase = real_turn, real_pod
    return log, seen, g


def run_cases():
    PASS.clear()
    FAIL.clear()
    log, seen, g = drive(n_extra=2)
    check("A two extra turns: turn, extra, extra, pod",
          log, ["turn", "extra", "extra", "pod"])
    check("B the pod acts after the chain: g.turn 3, pod_turn 1",
          seen[:1], [(3, 1)])
    check("C one pod round for the round", g.m["pod_rounds"], 1)

    log, _seen, _g = drive(n_extra=2, extra_turns_before_pod=False)
    check("D extra_turns_before_pod=False: turn, pod, extra, extra",
          log, ["turn", "pod", "extra", "extra"])

    log, _seen, _g = drive(n_extra=0)
    check("E no extra turn: turn, pod", log, ["turn", "pod"])

    log, _seen, _g = drive(n_extra=2, win=True)
    check("F a game won on your turn: no pod round", log, ["turn"])

    copies = []
    for name, src in (("tivit.simulate", inspect.getsource(T.simulate)),
                      ("test_time_sieve.drive", inspect.getsource(SIEVE.drive)),
                      ("diag_time_sieve", inspect.getsource(DIAG))):
        if "play_round(" not in src or "take_extra_turns(" in src:
            copies.append(name)
    check("G every driver calls play_round, none copies it", copies, [])
    return set(FAIL)


REAL_PLAY_ROUND = T.play_round


def old_order(g, played, budget):
    """The mutation: the pod's round between your turn and its extra turns,
    whatever the knob says -- the old order, run by the engine's own code."""
    g.cfg["extra_turns_before_pod"] = False
    return REAL_PLAY_ROUND(g, played, budget)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z176: tivit's extra turns before the pod's round\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "play_round runs the pod before the extra turns":
            ({"A", "B"}, (T, "play_round", old_order), {}),
        "an extra turn hands the pod a round (§0z86's bug)":
            ({"A", "B", "C", "D"}, None,
             {"extra_turns_skip_opponents": False}),
        "pod_round never runs the pod":
            ({"A", "B", "C", "D", "E"}, (T, "pod_round", lambda g: None), {}),
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
