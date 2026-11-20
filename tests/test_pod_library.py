#!/usr/bin/env python3
"""§0z236 (queue item 50, step 1): the pod's library and land drops.

    python -m tests.test_pod_library
    python -m tests.test_pod_library --mutate   # 4 mutations, exact sets

The mulligan cases hand `opponents.opening_hand` a stand-in shuffle that
deals the hands a case names; the turn cases call `opponents.land_drops` on
a kept hand and a library in draw order, with the census's costs (a rock
costs 2 and nets 1, a land ramp costs 3 and puts one land in tapped).

CASES
  A  the template: 99 cards, POD_LANDS lands, POD_ROCKS rocks,
     POD_LAND_RAMP land ramp (the census, `decks/_pod_mana.py`)
  B  CRN: `make_pod` with `pod_mana` on draws the same opponents and the
     same grid as with it off, and the same seed rolls the same rows
  C1 a first hand of three lands is kept: seven cards
  C2 one land, then two: the FREE mulligan (103.5c), seven cards kept
  C3 six lands, then one, then three: one counted mulligan, six kept
  C4 no hand ever has two lands: kept at five cards, never below (the rule)
  C5 six lands, then six again: the second hand is kept, seven cards
  D  a rock taps the turn it is cast (302.6 is a creature rule): lands 1, 2,
     3 from an all-land library; the rock cast on turn 2 leaves spare 1,
     and turn 3 has 3 lands + 1 = 4 sources
  E  a land ramp's land enters tapped: cast on turn 3 (sources 3, spare 0),
     lands 4 at the end of turn 3, and turn 4 has 5 sources
  F  103.8c: a kept hand with NO land and a land on top of the library --
     the first turn's draw finds it, so turn 1 has one land

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the first mulligan is counted            -> C2, C3, C5
  no draw on the first turn                -> F
  a rock is not tapped the turn it is cast -> D
  a land ramp's land is untapped at once   -> E

THE FIRST-DRAW MUTATION WAS CORRECTED AFTER ITS FIRST RUN, said so: it was
a stand-in `land_drops` that shifted every row a turn, which broke D and E
too -- a different rule from "no draw on the first turn". It is the real
seam now, `opponents.POD_FIRST_DRAW` False; the expected set is unchanged.
The rock and land-ramp mutations were stand-ins that edited the rows after
the fact; they are seams now too (`ROCK_TAPS_ON_CAST`, `RAMP_LAND_TAPPED`),
the sets unchanged, and so is the mulligan's (`POD_FREE_MULLIGANS` 0, for a
re-implementation of `opening_hand`).

UNMUTATED (§0z15): A reads the census; B's identity has no seam to mutate
here (`check_unchanged_decks --cfg=pod_mana=True` is its whole-game proof,
§0z236); C1 and C4 are kept by every rule mutated.
"""
import random
import sys

import edhmc.opponents as O
from edhmc.decks import _pod_mana as M
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
COSTS = (M.ROCK_MV, M.ROCK_NET, M.LAND_RAMP_COST, M.LAND_RAMP_LANDS)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


class Deal:
    """A shuffle that deals the next named hand: `lands` lands then spells
    in the first seven, and the rest of the template after."""

    def __init__(self, *land_counts):
        self.left = list(land_counts)

    def shuffle(self, lib):
        n = self.left.pop(0)
        lands = [c for c in lib if c == "land"]
        rest = [c for c in lib if c != "land"]
        lib[:] = lands[:n] + rest[:7 - n] + lands[n:] + rest[7 - n:]


def kept(*land_counts):
    hand, library = O.opening_hand(Deal(*land_counts),
                                   O.pod_library_template())
    return len(hand), len(hand) + len(library)


def run_cases():
    PASS.clear()
    FAIL.clear()

    t = O.pod_library_template()
    check("A the template is the census",
          (len(t), t.count("land"), t.count("rock"), t.count("ramp")),
          (M.POD_LIBRARY, M.POD_LANDS, M.POD_ROCKS, M.POD_LAND_RAMP))

    off = O.make_pod(dict(DEFAULT_CFG, turns=20), 77)
    on = O.make_pod(dict(DEFAULT_CFG, turns=20, pod_mana=True), 77)
    again = O.make_pod(dict(DEFAULT_CFG, turns=20, pod_mana=True), 77)
    check("B CRN: the same pod and grid on or off, the same rows again",
          ([o.kill_turn for o in off[0]] == [o.kill_turn for o in on[0]]
           and off[1] == on[1] and off[2] == on[2]
           and [o.mana_rows for o in on[0]]
           == [o.mana_rows for o in again[0]]
           and all(o.mana_rows for o in on[0])
           and not any(o.mana_rows for o in off[0])), True)

    check("C1 three lands: kept, seven cards", kept(3), (7, 99))
    check("C2 one land, then two: the free mulligan, seven", kept(1, 2),
          (7, 99))
    check("C3 six, one, three: one counted, six kept", kept(6, 1, 3),
          (6, 99))
    check("C4 never two lands: kept at five", kept(0, 1, 0, 1), (5, 99))
    check("C5 six, then six: the second is kept, seven", kept(6, 6), (7, 99))

    rows = O.land_drops(["land", "rock", "other"], ["land"] * 10, 3, COSTS)
    check("D a rock taps the turn it is cast",
          [(r.lands, r.rocks, r.sources, r.spare) for r in rows[1:]],
          [(1.0, 0, 1.0, 1.0), (2.0, 1, 2.0, 1.0), (3.0, 1, 4.0, 4.0)])

    rows = O.land_drops(["land", "ramp", "other"], ["land"] * 10, 4, COSTS)
    check("E a land ramp's land enters tapped",
          [(r.lands, r.sources, r.spare) for r in rows[3:]],
          [(4.0, 3.0, 0.0), (5.0, 5.0, 5.0)])

    rows = O.land_drops(["other"] * 7, ["land"] + ["other"] * 10, 1, COSTS)
    check("F 103.8c: the first turn draws, and finds the land",
          rows[1].lands, 1.0)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z236: the pod's library and land drops\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "the first mulligan is counted": (
            {"C2", "C3", "C5"}, [("POD_FREE_MULLIGANS", 0)]),
        "no draw on the first turn": ({"F"}, [("POD_FIRST_DRAW", False)]),
        "a rock is not tapped the turn it is cast": (
            {"D"}, [("ROCK_TAPS_ON_CAST", False)]),
        "a land ramp's land is untapped at once": (
            {"E"}, [("RAMP_LAND_TAPPED", False)]),
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
