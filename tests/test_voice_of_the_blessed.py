#!/usr/bin/env python3
"""Voice of the Blessed's third clause: indestructible at ten counters (8b).

    python -m tests.test_voice_of_the_blessed
    python -m tests.test_voice_of_the_blessed --mutate   # 3 mutations, exact sets

    {W}{W} 2/2 Creature — Spirit Cleric  (Scryfall, verified 2026-09-25)
    Whenever you gain life, put a +1/+1 counter on this creature.
    As long as this creature has four or more +1/+1 counters on it, it has
    flying and vigilance.
    As long as this creature has ten or more +1/+1 counters on it, it has
    indestructible.

WHY IT WAS MISSING. §0n kept Voice OUT of the generated INDESTRUCTIBLE set on
purpose, because a static tag would make it indestructible at zero counters.
That was right, but it left the clause with nowhere to live, so the card was
never indestructible at all -- and ten counters is reachable in a deck whose
whole engine is lifegain events. It now lives in `opponents.indestructible_of`,
beside `flying_of`, which already carried the four-counter clause.

`destroy()` is the ONLY place indestructible is read, so one routed read
covers spot removal, the pod's wipes and your own wipes.

CASES
  A  nine counters: a destroy kills it           -- the threshold is ten
  B  ten counters: a destroy does NOT            -- the clause
  C  ten counters: an exile-type answer still kills it (indestructible
     never saves exile, sacrifice or -X/-X; `destroy_share` prices which)
  D  ten counters, your own KNOWN destroy (destroys=True): survives
  E  ten counters, your own KNOWN exile (destroys=False): dies
  F  a card that is NOT Voice, at ten counters: dies -- the rule is Voice's
  G  NEIGHBOUR, re-checked per §0z28: four-counter flying still holds, and
     three counters still does not fly

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the ten-counter clause is removed             -> B and D
  the threshold is four counters, not ten       -> A
  any creature with ten counters is indestructible -> F

C and E carry no mutation of their own, and that is written down (§0z15):
they pin that the new clause did not widen indestructible past destruction,
and both are guarded by `destroy()`'s existing roll/`destroys` logic, which
this change did not touch.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.karlov import KarlovGame
from edhmc.decks import karlov_v2 as M
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DESTROY, EXILE = 0.0, 0.99      # rolls either side of destroy_share (0.60)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def voice_card():
    deck, _cmd = M.build()
    return next(c for c in deck if c.name == "Voice of the Blessed")


def game_with(card, counters):
    deck, cmd = M.build()
    g = KarlovGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 777)
    g.board = EN.Board()
    perm = EN.Permanent(card=card, sick=False)
    perm.counters = counters
    g.board.append(perm)
    return g, perm


def survives(counters, card=None, **kw):
    g, perm = game_with(card or voice_card(), counters)
    OPP.destroy(g, perm, **kw)
    return perm in g.board


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    other = EN.Card(name="Plain Bear", types=frozenset({"Creature"}),
                    power=2, toughness=2)
    check("A nine counters: a destroy kills it", survives(9, roll=DESTROY), False)
    check("B ten counters: a destroy does not", survives(10, roll=DESTROY), True)
    check("C ten counters: an exile-type answer still kills it",
          survives(10, roll=EXILE), False)
    check("D ten counters vs your own known destroy: survives",
          survives(10, destroys=True), True)
    check("E ten counters vs your own known exile: dies",
          survives(10, destroys=False), False)
    check("F a non-Voice creature at ten counters: dies",
          survives(10, card=other, roll=DESTROY), False)
    g4, p4 = game_with(voice_card(), 4)
    g3, p3 = game_with(voice_card(), 3)
    check("G neighbour: flying at four counters, not at three",
          (OPP.flying_of(g4, p4), OPP.flying_of(g3, p3)), (True, False))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Voice of the Blessed -- indestructible at ten counters\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.indestructible_of
    expected = {
        "the ten-counter clause is removed": {"B", "D"},
        "the threshold is four counters, not ten": {"A"},
        "any creature with ten counters is indestructible": {"F"},
    }
    muts = {
        "the ten-counter clause is removed":
            lambda g, p: p.card.indestructible,
        "the threshold is four counters, not ten":
            lambda g, p: p.card.indestructible or (
                p.card.name == "Voice of the Blessed" and p.counters >= 4),
        "any creature with ten counters is indestructible":
            lambda g, p: p.card.indestructible or p.counters >= 10,
    }
    bad = 0
    for label, fn in muts.items():
        print(f"-- {label}")
        OPP.indestructible_of = fn
        try:
            broke = run_cases()
        finally:
            OPP.indestructible_of = real
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
