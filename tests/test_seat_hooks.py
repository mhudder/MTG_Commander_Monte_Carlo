#!/usr/bin/env python3
"""§0z179: azusa's and karlov's stand-ins for the pod's turns, per seat.

    python -m tests.test_seat_hooks
    python -m tests.test_seat_hooks --mutate   # 3 mutations, exact sets

Under the seat order (`pod_seat_turns`) each opponent's turn has an upkeep
and a main phase an engine can hook (`g.pod_upkeep(i)`, `g.pod_main(i)`).
Three stand-ins for "the pod's round" move onto them:

  azusa   Verdant Kraken, "at the beginning of EACH PLAYER'S upkeep": one
          token at each opponent's upkeep -- where three were made before
          the round, however many opponents were left (`azusa_seat_upkeeps`)
  karlov  Ginger, "at the beginning of EACH upkeep, if you're the monarch":
          one at each opponent's upkeep; and `opponent_activity` -- the pod's
          creatures and spells, which karlov taxes -- spread across the seats'
          main phases with the round's old totals (`karlov_seat_pod`); and the
          Citadel's piece window aimed at the seat whose turn it is

Each case runs a real `take_turn` at pod turn 5 and records, for each call,
the seat whose turn it ran in (`g.pod_seat`, None outside the round).

CASES
  A  azusa: your upkeep's token, then one at each opponent's upkeep, 0, 1, 2
  B  NEIGHBOUR: `azusa_seat_upkeeps=False` -- three at once, before the round,
     with one opponent dead as with none
  C  azusa, one opponent dead: no token at its upkeep (it has none)
  D  karlov as the monarch: your upkeep's Gingerbrute, then one call at each
     opponent's upkeep
  E  karlov's activity, three opponents living: the round's creatures (2) at
     seats 1 and 2 and its spells (4) at seats 0, 1, 2, 2 -- the old totals,
     spread
  F  the Citadel's piece aim, at seat 1's turn, does not answer seat 0's
     landing piece; outside the round it does
  G  NEIGHBOUR: `karlov_seat_pod=False` -- the activity once, in the first
     seat's main phase, and Ginger's three before the round

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  azusa_seat_upkeeps=False everywhere   -> A, C
  karlov_seat_pod=False everywhere      -> D, E, F
  pod_seat_turns=False everywhere       -> A, C, D, E, F, G

THE THIRD EXPECTATION WAS WRONG, and corrected after the first run. It read
"A, C, D, E, F", on the claim that B and G hold under the old round. B does;
G does not, and should not: G pins where the activity runs under the SEAT
order with karlov's knob off -- once, in seat 0's main phase -- and the old
round has no seat 0's main phase to run it in (`g.pod_seat` is None there).

UNMUTATED (§0z15): B and G are the knobs' neighbours; B holds under the old
round too.
"""
import sys

import edhmc.azusa as AZ
import edhmc.karlov as KV
import edhmc.opponents as OPP
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}

AZ_DECK, AZ_CMD = build_pending("azusa")
KV_DECK, KV_CMD = build_pending("karlov")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def seat(g):
    return getattr(g, "pod_seat", None)


def prepare(g, dead=()):
    g.opening_hand()
    g.turn = 4                       # take_turn makes it 5
    for i, o in enumerate(g.opponents):
        o.kill_turn, o.life = 99, float(10 ** 9)
        if i in dead:
            o.alive, o.life = False, 0.0
    return g


def azusa_tokens(dead=(), **cfg):
    g = prepare(AZ.AzusaGame(list(AZ_DECK), AZ_CMD,
                             dict(DEFAULT_CFG, watch=frozenset(),
                                  **{**EXTRA_CFG, **cfg}), 2), dead)
    g.board.append(Permanent(card=Card(name="Verdant Kraken",
                                       types=frozenset({"Creature"}),
                                       power=6, toughness=6), sick=False))
    log, real = [], AZ.AzusaGame.verdant_kraken_tokens

    def rec(self, upkeeps):
        log.append((seat(self), upkeeps))
        return real(self, upkeeps)
    AZ.AzusaGame.verdant_kraken_tokens = rec
    try:
        AZ.take_turn(g)
    finally:
        AZ.AzusaGame.verdant_kraken_tokens = real
    return log


def karlov_turn(**cfg):
    g = prepare(KV.KarlovGame(list(KV_DECK), KV_CMD,
                              dict(DEFAULT_CFG, watch=frozenset(),
                                   **{**EXTRA_CFG, **cfg}), 2))
    g.monarch = True
    log = {"ginger": [], "creature": [], "spell": [], "activity": []}
    inside = {"on": False}
    real = (KV.gingerbrute_tokens, KV.creature_entered, KV._opponent_spell,
            KV.seat_activity, KV.opponent_activity)

    def ginger(gg, upkeeps):
        log["ginger"].append((seat(gg), upkeeps))
        return real[0](gg, upkeeps)

    def creature(gg, *a, **kw):
        if inside["on"] and kw.get("mine") is False:
            log["creature"].append(seat(gg))
        return real[1](gg, *a, **kw)

    def spell(gg):
        log["spell"].append(seat(gg))
        return real[2](gg)

    def activity_of(fn, tag):
        def run(gg, *a):
            log["activity"].append((tag, seat(gg)))
            inside["on"] = True
            try:
                return fn(gg, *a)
            finally:
                inside["on"] = False
        return run

    KV.gingerbrute_tokens, KV.creature_entered, KV._opponent_spell = \
        ginger, creature, spell
    KV.seat_activity = activity_of(real[3], "seat")
    KV.opponent_activity = activity_of(real[4], "round")
    try:
        KV.take_turn(g)
    finally:
        (KV.gingerbrute_tokens, KV.creature_entered, KV._opponent_spell,
         KV.seat_activity, KV.opponent_activity) = real
    return log


def citadel_aim(**cfg):
    """(at seat 1's turn, outside the round) -- the aim for seat 0's piece."""
    g = prepare(KV.KarlovGame(list(KV_DECK), KV_CMD,
                              dict(DEFAULT_CFG, watch=frozenset(),
                                   **{**EXTRA_CFG, **cfg}), 2))
    g.turn = 5
    t = OPP.pod_turn(g)
    o = g.opponents[0]
    if not o.pieces:
        return ("no pieces", None)
    o.kill_turn = t
    o.piece_lands[0] = t
    reach = next((r for r in OPP.ANSWERS.values() if OPP.hits(r, o.pieces[0])),
                 None)
    if reach is None:
        return ("no answer", None)
    g.pod_seat = 1
    during = KV.citadel_piece_target(g, reach)
    g.pod_seat = None
    outside = KV.citadel_piece_target(g, reach)
    return (during, outside is not None and outside[0] is o)


def run_cases():
    PASS.clear()
    FAIL.clear()

    check("A azusa: your upkeep, then each opponent's, 0, 1, 2",
          azusa_tokens(), [(None, 1), (0, 1), (1, 1), (2, 1)])
    check("B azusa_seat_upkeeps=False: three at once, a dead seat or not",
          (azusa_tokens(azusa_seat_upkeeps=False),
           azusa_tokens(dead=(1,), azusa_seat_upkeeps=False)),
          ([(None, 1), (None, 3)], [(None, 1), (None, 3)]))
    check("C azusa, seat 1 dead: no token at its upkeep",
          azusa_tokens(dead=(1,)), [(None, 1), (0, 1), (2, 1)])

    log = karlov_turn()
    check("D karlov monarch: your Gingerbrute, then each opponent's upkeep",
          log["ginger"], [(None, 1), (0, 1), (1, 1), (2, 1)])
    check("E karlov activity: the old totals, spread across the seats",
          (log["creature"], log["spell"]), ([1, 2], [0, 1, 2, 2]))

    check("F the Citadel's aim: seat 1's turn skips seat 0's piece",
          citadel_aim(), (None, True))

    log = karlov_turn(karlov_seat_pod=False)
    check("G karlov_seat_pod=False: activity once at seat 0, Ginger's three",
          (log["activity"], log["ginger"]),
          ([("round", 0)], [(None, 1), (None, 3)]))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z179: azusa's and karlov's stand-ins, per seat\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "azusa_seat_upkeeps=False everywhere":
            ({"A", "C"}, {"azusa_seat_upkeeps": False}),
        "karlov_seat_pod=False everywhere":
            ({"D", "E", "F"}, {"karlov_seat_pod": False}),
        "pod_seat_turns=False everywhere":
            ({"A", "C", "D", "E", "F", "G"}, {"pod_seat_turns": False}),
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
