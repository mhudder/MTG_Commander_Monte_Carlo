#!/usr/bin/env python3
"""The monarch — the crown's draw, and the combat that takes it away.

    python -m tests.test_monarch
    python -m tests.test_monarch --mutate   # 4 mutations, exact sets

WHY THIS EXISTS BEFORE ANY CARD DOES. The owner asked for the monarch on
2026-09-22 as a common mechanic, and `docs/TRIAGE.md` had it recorded as the
blocker behind Ginger, Queen of Sweets. **No card in any of the six lists
grants it yet**, so this test is the only thing exercising the mechanism --
which is deliberate and is §0z12's lesson applied forwards. That finding is
about five `wipe` tags that nothing read: they looked harmless for months and
two of them were WRONG the moment the branch was wired up. The read side here
is built and pinned first, so the cards arrive at a tested mechanism instead
of making one live.

THE MODELLING DECISION, said out loud because CLAUDE.md requires it. "A
creature deals combat damage to you" has no object-level answer in this engine:
the opponents' boards are a float count (§4), not permanents, so there is no
creature to connect. The crown is therefore lost ON THE PATH THAT ALREADY
MODELS THEIR CREATURES GETTING THROUGH -- inside `incidental_damage`, off the
same threat-weighted `share` that decides how much of their swing is aimed at
you. The knob is `monarch_loss_scale` and its default is `incidental_rate`
itself (0.45), because that constant already means "how much of a swing lands"
and a second uncalibrated number meaning the same thing is §0u's shape.
**IT HAS NOT BEEN SWEPT.** No card depends on it yet; the sweep is owed before
one does.

CASES
  A  not the monarch: the end step draws nothing and writes no counter
  B  `become_monarch` takes the crown, and taking it twice is one event
  C  the monarch draws exactly one card at its own end step
  D  the crown PASSES when the pod has creatures and is past first_attack_turn
  E  the crown cannot pass before `first_attack_turn` -- nobody is attacking
  F  the crown cannot pass to an opponent with no creatures
  G  once the crown is gone the draws stop
  H  NOT holding the crown consumes NO monarch roll -- the six decks are unmoved
  I  `monarch_start` begins the game as the monarch
  J  `monarch_draws` is credited from the draw that HAPPENED (empty library)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the end step draws nothing                          -> C
  the crown never passes                              -> D and G
  the pass check ignores whether they have creatures   -> F
  the roll is consumed even without the crown          -> H

WHAT HAS NO MUTATION, written down rather than left to be found (§0z15).
Case E is guarded by `incidental_damage`'s own early return on
`first_attack_turn`, which is shared with the damage path and cannot be
switched off without either reimplementing that function in this file or
changing the case's own input. So E is pinned as a regression case with no
mutation behind it, and a future refactor that moves the turn guard should
add one.

Case H is the load-bearing one. `crn_random` is index-addressed per NAME
(§0z17), so a new stream cannot shift an old one -- but a roll CONSUMED in a
game that should not have rolled would still be a behaviour change in all six
decks. H asserts the roll is never reached while `monarch` is False, which is
what makes "this change moves no deck" a checked claim instead of an argument.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as M
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(creatures=0.0, turn=8, **cfg):
    """A real game with a controlled pod, so `your_share` has a board to read."""
    deck, cmd = M.build()
    g = EN.Game(deck, cmd, dict(DEFAULT_CFG, turns=20, **cfg),
                random.Random(99), 1234)
    g.turn = turn
    g.opponents = [OPP.Opponent(bracket=3, has_blue=False,
                                creatures=creatures, life=40.0)
                   for _ in range(3)]
    return g


def spy_rolls():
    """Wrap `crn_random` and record the names it is asked for.

    `opponents.incidental_damage` imports it from the module at CALL time, so
    replacing `EN.crn_random` is seen -- which is why that import is local.
    `test_floating_mana` learned the inverse the hard way: a mutation aimed at
    a name already bound into a file reaches nothing.
    """
    seen = []
    real = EN.crn_random

    def spy(g, name):
        seen.append(name)
        return real(g, name)
    EN.crn_random = spy
    return seen, real


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A: no crown, no draw, no counters --------------------------------
    g = fresh()
    before = len(g.hand)
    OPP.monarch_end_step(g)
    check("A without the crown the end step draws nothing",
          (len(g.hand) - before, g.m["monarch_draws"], g.m["monarch_turns"]),
          (0, 0, 0))

    # ---- B: taking the crown, and taking it twice ------------------------
    g = fresh()
    OPP.become_monarch(g)
    OPP.become_monarch(g)
    check("B become_monarch takes the crown and counts one event",
          (g.monarch, g.m["monarch_gained"]), (True, 1))

    # ---- C: the crown draws one at your end step -------------------------
    g = fresh()
    OPP.become_monarch(g)
    before = len(g.hand)
    OPP.monarch_end_step(g)
    check("C the monarch draws exactly one card at its end step",
          (len(g.hand) - before, g.m["monarch_draws"], g.m["monarch_turns"]),
          (1, 1, 1))

    # ---- D: the crown passes to a board that can attack ------------------
    # scale forced to 1.0 so min(1, share*scale) == 1 and the roll always hits:
    # the CASE is "does the path fire", not "at what rate".
    g = fresh(creatures=3.0, monarch_loss_scale=100.0)
    OPP.become_monarch(g)
    OPP.incidental_damage(g)
    check("D the crown passes when the pod's creatures get through",
          (g.monarch, g.m["monarch_lost"]), (False, 1))

    # ---- E: nobody attacks before first_attack_turn ----------------------
    g = fresh(creatures=3.0, turn=1, monarch_loss_scale=100.0)
    OPP.become_monarch(g)
    OPP.incidental_damage(g)
    check("E the crown cannot pass before first_attack_turn",
          (g.monarch, g.m["monarch_lost"]), (True, 0))

    # ---- F: an empty board takes nothing ---------------------------------
    g = fresh(creatures=0.0, monarch_loss_scale=100.0)
    OPP.become_monarch(g)
    OPP.incidental_damage(g)
    check("F the crown cannot pass to opponents with no creatures",
          (g.monarch, g.m["monarch_lost"]), (True, 0))

    # ---- G: the draws stop when the crown is gone ------------------------
    g = fresh(creatures=3.0, monarch_loss_scale=100.0)
    OPP.become_monarch(g)
    OPP.incidental_damage(g)          # crown lost here
    before = len(g.hand)
    OPP.monarch_end_step(g)           # next end step
    check("G once the crown is gone the draws stop",
          (g.monarch, len(g.hand) - before), (False, 0))

    # ---- H: no crown, no roll -- the reason six decks do not move --------
    seen, real = spy_rolls()
    try:
        g = fresh(creatures=3.0)
        OPP.incidental_damage(g)      # monarch is False
        without = [n for n in seen if n.startswith("monarch")]
        seen.clear()
        g = fresh(creatures=3.0, monarch_loss_scale=100.0)
        OPP.become_monarch(g)
        OPP.incidental_damage(g)
        with_crown = [n for n in seen if n.startswith("monarch")]
    finally:
        EN.crn_random = real
    check("H without the crown no monarch roll is consumed",
          (without, bool(with_crown)), ([], True))

    # ---- I: monarch_start ------------------------------------------------
    g = fresh(monarch_start=True)
    g.opening_hand()
    check("I monarch_start begins the game as the monarch",
          (g.monarch, g.m["monarch_gained"]), (True, 1))

    # ---- J: attribution against an empty library (§0z28) -----------------
    g = fresh()
    OPP.become_monarch(g)
    g.library = []
    drawn_before = g.m["cards_drawn"]
    OPP.monarch_end_step(g)
    check("J monarch_draws counts the draw that happened, not the attempt",
          (g.m["monarch_draws"], g.m["cards_drawn"] - drawn_before), (0, 0))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("the monarch -- the crown's draw and the combat that takes it\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_end = OPP.monarch_end_step
    real_inc = OPP.incidental_damage
    real_crn = EN.crn_random
    expected = {
        "the end step draws nothing": {"C"},
        "the crown never passes": {"D", "G"},
        "the pass check ignores whether they have creatures": {"F"},
        "the roll is consumed even without the crown": {"H"},
    }
    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == "the end step draws nothing":
            def no_draw(g):
                if not g.monarch or g.result is not None:
                    return
                g.m["monarch_turns"] += 1      # the counter, not the card
            OPP.monarch_end_step = no_draw
        elif label == "the crown never passes":
            def keeps(g):
                held = g.monarch
                real_inc(g)
                g.monarch = held               # the crown is never taken
            OPP.incidental_damage = keeps
        elif label == "the pass check ignores whether they have creatures":
            def ungated(g):
                real_inc(g)
                # the gate the real code applies, removed: past the turn guard,
                # an empty board takes the crown anyway.
                if g.monarch and g.turn >= g.cfg.get("first_attack_turn", 3):
                    g.monarch = False
                    g.m["monarch_lost"] += 1
            OPP.incidental_damage = ungated
        else:
            def always_rolls(g):
                # the roll, taken whether or not the crown is held
                for i in range(len(g.opponents)):
                    EN.crn_random(g, f"monarch{i}")
                real_inc(g)
            OPP.incidental_damage = always_rolls
        try:
            broke = run_cases()
        finally:
            OPP.monarch_end_step = real_end
            OPP.incidental_damage = real_inc
            EN.crn_random = real_crn
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
