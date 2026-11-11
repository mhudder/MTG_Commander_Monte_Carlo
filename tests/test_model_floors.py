#!/usr/bin/env python3
"""The floors §0z192 found holding, pinned (queue item 43).

    python -m tests.test_model_floors
    python -m tests.test_model_floors --mutate   # 2 mutations, exact sets

The core review (§0z192, `diagnostics/diag_core_review.py anatomy`) checked
two facts about the model that nothing else checks, and that would be loud if
a pod change broke them. This makes them permanent, at a few hundred seeds a
deck instead of 1,500, on every ACTIVE deck's staged list (`build_pending`),
T20, `DEFAULT_CFG`, seeds 5000.. (the tables' block).

"nothing" is the list with every NONLAND card replaced by a do-nothing
sorcery of its cost -- the deck that does not play. It still casts its
commander and plays its lands (every engine casts the commander by its own
rule), which is where its few wins come from.

"share@fire" is `opponents.your_share` at the moment a clock FIRES with
three opponents alive (two rivals), read by wrapping `opponents._clock_seat`
without changing it. 1/3 is the share of a board no scarier than the rivals'.

CASES (every active deck in each; a case fails if any deck is outside)
  A  FLOOR: "nothing" wins under 0.08 and loses over 0.88 at T20.
     §0z192 at N=1,500: wins 0.000-0.047, losses 0.917-0.964.
  B  SCALE: a real list's mean share@fire is in [0.22, 0.42].
     §0z192: 0.30-0.36.
  C  SEPARATION: "nothing"'s mean share@fire is under 0.20 -- the threat
     scale tells a board from no board. §0z192: 0.06-0.12.
  D  A REAL LIST PLAYS: it wins at least 0.20 at T20 and at least 0.15 more
     than "nothing". §0z192: 0.31-0.62.

THE BANDS ARE WIDER THAN §0z192's RANGES ON PURPOSE. The seeds are fixed, so
a run is deterministic; what the margin absorbs is an engine change that
moves a few of 300 games. At N=300 a win rate of 0.5 has a standard error of
~0.03 and a mean share over ~100-140 fires ~0.01. At the commit that wrote
this the tightest margins were rendmaw's "nothing" losses (0.910 against
0.88) and shilgengar's "nothing" wins (0.050 against 0.08), about two
standard errors; every share sat 0.07 or more inside its band. The values
each run measures are printed beside the bands.

FIRST RUN (2026-11-11): plain 4 of 4; --mutate 2 of 2, each expected set
exactly right. Under `threat_of` 0 the real shares fell to 0.09-0.21; under
the aimed clock the real lists won 0.10-0.37 and D broke on rendmaw and
shilgengar only, so D is the coarser of the two.

MUTATIONS, WRITTEN BEFORE THE FIRST RUN, exact sets:
  `threat_of` returns 0 (the table sees creature power only)  -> B
  every clock is aimed at you (its roll always under your share) -> D

  The share is read inside `_clock_seat` BEFORE the aim is rolled, so the
  second mutation leaves B and C's numbers as they were; it ends every game
  at the first clock, which is what D is for.

UNMUTATED (§0z15): A and C. A floor that only falls when the deck plays is
what A is; this file does not know a mutation that lifts a do-nothing deck's
win rate without breaking D first, and says so rather than inventing one.
"""
import sys

import edhmc.opponents as OPP
from edhmc.engine import Card
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import ACTIVE, DECKS

MUTATE = "--mutate" in sys.argv
N = 300
SEED0 = 5000
PASS, FAIL = [], []

FLOOR_WIN, FLOOR_LOSS = 0.08, 0.88
SHARE_BAND = (0.22, 0.42)
NOTHING_SHARE = 0.20
REAL_WIN, REAL_MARGIN = 0.20, 0.15

_FIRES = []
_REAL_SEAT = OPP._clock_seat


def counting_seat(g, i, rolls_t):
    """`_clock_seat`, unchanged, recording `your_share` when it fires with
    three opponents alive. Reads `OPP._clock_seat_inner` so a mutation can
    replace the real seat underneath the counter."""
    opp = g.opponents[i]
    due = (opp.alive and not opp.clock_fired and g.result is None
           and OPP.pod_turn(g) >= opp.kill_turn)
    if due:
        others = [o for j, o in enumerate(g.opponents) if j != i and o.alive]
        if len(others) == 2:
            _FIRES.append(OPP.your_share(g, opp, others))
    return _INNER[0](g, i, rolls_t)


_INNER = [_REAL_SEAT]


def do_nothing(deck):
    return [c if c.is_land else
            Card(name="(blank)", types=frozenset({"Sorcery"}),
                 cost=dict(c.cost), priority=1.0) for c in deck]


def leg(deck_name, nothing):
    lst, cmd = build_pending(deck_name)
    if nothing:
        lst = do_nothing(lst)
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset())
    sim = DECKS[deck_name].sim
    del _FIRES[:]
    won = lost = 0
    for s in range(N):
        r = sim(lst, cmd, dict(cfg), SEED0 + s)
        won += r["result"] == "win"
        lost += r["result"] == "loss"
    share = sum(_FIRES) / len(_FIRES) if _FIRES else float("nan")
    return won / N, lost / N, share, len(_FIRES)


def check(label, ok, detail):
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def run_cases():
    del PASS[:], FAIL[:]
    OPP._clock_seat = counting_seat
    try:
        got = {d: (leg(d, False), leg(d, True)) for d in ACTIVE}
    finally:
        OPP._clock_seat = _REAL_SEAT

    def row(fn):
        return "  ".join(f"{d} {fn(*got[d])}" for d in ACTIVE)

    check(f"A floor: nothing wins < {FLOOR_WIN}, loses > {FLOOR_LOSS}",
          all(n[0] < FLOOR_WIN and n[1] > FLOOR_LOSS
              for _r, n in got.values()),
          row(lambda r, n: f"{n[0]:.3f}/{n[1]:.3f}"))
    check(f"B scale: real share@fire in {list(SHARE_BAND)}",
          all(SHARE_BAND[0] <= r[2] <= SHARE_BAND[1]
              for r, _n in got.values()),
          row(lambda r, n: f"{r[2]:.3f}({r[3]})"))
    check(f"C separation: nothing share@fire < {NOTHING_SHARE}",
          all(n[2] < NOTHING_SHARE or n[3] == 0 for _r, n in got.values()),
          row(lambda r, n: f"{n[2]:.3f}({n[3]})"))
    check(f"D a real list plays: wins >= {REAL_WIN} and >= nothing + "
          f"{REAL_MARGIN}",
          all(r[0] >= REAL_WIN and r[0] - n[0] >= REAL_MARGIN
              for r, n in got.values()),
          row(lambda r, n: f"{r[0]:.3f}"))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print(f"The model's floors (§0z192), N={N} a leg, T20\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")

    def aimed_at_you(g, i, rolls_t):
        rolls = list(rolls_t)
        rolls[i] = list(rolls[i])
        rolls[i][6] = -1.0                 # under any share
        return _REAL_SEAT(g, i, rolls)

    real_threat = OPP.threat_of
    muts = {
        "threat_of returns 0": ({"B"}, "threat"),
        "every clock is aimed at you": ({"D"}, "seat"),
    }
    bad = 0
    for label, (want, what) in muts.items():
        print(f"-- {label}")
        if what == "threat":
            OPP.threat_of = lambda g, perm: 0.0
        else:
            _INNER[0] = aimed_at_you
        try:
            broke = run_cases()
        finally:
            OPP.threat_of = real_threat
            _INNER[0] = _REAL_SEAT
        ok = broke == want
        bad += not ok
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
