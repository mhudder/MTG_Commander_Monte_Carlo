#!/usr/bin/env python3
"""§0z221, A6: held answers -- the pod's spot removal at you, held into
your turn and cast at your biggest new threat (`held_answers`).

    python -m tests.test_held_answers
    python -m tests.test_held_answers --mutate   # 4 mutations, exact sets

Each case: a shilgengar game, an empty battlefield but for the creatures a
case puts there, `held_answer_share` 1 (every answer at you is held),
opponent 0's spot removal row forced to fire at you.

CASES
  A  spot removal at you is HELD: nothing dies, one answer held
  B  the answer held against an Old 4-threat; a New 9-threat enters this
     turn: the combat window kills New, Old lives
  C  NEIGHBOUR: held, and nothing new this turn: the combat window keeps
     it -- Old lives, the answer still held
  D  Old alive until the end window, which casts what is still held at
     the top threat: Old dies there
  E  held against Old; a Big 9-threat and a Piece enter: the combo window
     kills the piece it is given, not the top threat
  F  NEIGHBOUR: `held_answers` False: the removal is cast at once, Old dies
  G  HOLD ONLY TO GAIN: a 9-threat on the battlefield (the bar is 6) is
     answered now, not held (Old is 4: every other case holds against it)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  held_answers=False                         -> A, B, C, D, E
    (CORRECTED AFTER THE RUN, said so: written as A, B, D, E. Under the old
    rule the removal is cast at once at Old, so C -- Old lives -- breaks
    too, and D as first written ("Old dies") held under both rules and
    pinned nothing; D now also asks that Old lived until the end window.)
  the combat window spends like the end step -> C
  the end window casts nothing               -> D
  held_answer_bar=None (hold whatever)       -> G
  (G and this mutation were added with the bar, 2026-11-16, before their
  run.)

UNMUTATED (§0z15): F is the old rule, which both readings share; G holds
under the old rule too (cast at once).
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

# §0z243: THE POD BEFORE ITEM 50'S FLIP, NAMED. This file pins a mechanism
# that is not the pod's mana, on opponents set up by hand with none; under
# the flipped pod its event would be gated by that mana instead. Set after
# the flip, no expectation changed; the mana model's own tests are
# tests/test_pod_*.py.
from edhmc.experiment import POD_PRE_ITEM50 as _PRE_ITEM50  # noqa: E402
DEFAULT_CFG = dict(DEFAULT_CFG, **_PRE_ITEM50)

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
BASE = {"held_answers": True, "held_answer_share": 1.0}
EXTRA_CFG = dict(BASE)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def body(name, threat):
    return EN.Permanent(card=EN.Card(name=name, types=frozenset({"Creature"}),
                                     power=2, toughness=2, threat=threat),
                        sick=False)


def game(**cfg):
    deck, cmd = SM.build()
    g = SH.ShilgengarGame(list(deck), cmd,
                          dict(DEFAULT_CFG, **{**EXTRA_CFG, **cfg}), 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    old = body("Old", 4.0)
    g.board.append(old)
    opp = g.opponents[0]
    opp.p["spot"] = 1.0
    others = [o for o in g.opponents[1:]]
    rolls = [-1.0] * OPP.N_SLOTS
    rolls[5] = rolls[7] = 0.999          # no protection, the default kind
    return g, opp, others, rolls, old


def fire(g, opp, others, rolls):
    OPP.spot_removal(g, opp, others, rolls)
    g.held_seen = {id(p) for p in g.board}     # the next turn begins here


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, opp, others, rolls, old = game()
    OPP.spot_removal(g, opp, others, rolls)
    check("A held: nothing dies, one answer held",
          (old in g.board, g.m["answers_held"]), (True, 1))

    g, opp, others, rolls, old = game()
    fire(g, opp, others, rolls)
    new = body("New", 9.0)
    g.board.append(new)
    OPP.held_answer_window(g, "combat")
    check("B the combat window kills the New 9-threat; Old lives",
          (new in g.board, old in g.board), (False, True))

    g, opp, others, rolls, old = game()
    fire(g, opp, others, rolls)
    OPP.held_answer_window(g, "combat")
    check("C NEIGHBOUR: nothing new: kept, Old lives",
          (old in g.board, bool(getattr(opp, "held_rolls", None))),
          (True, bool(EXTRA_CFG.get("held_answers"))))

    g, opp, others, rolls, old = game()
    fire(g, opp, others, rolls)
    alive = old in g.board
    OPP.held_answer_window(g, "end")
    check("D Old alive until the end window, which kills it",
          (alive, old in g.board), (True, False))

    g, opp, others, rolls, old = game()
    fire(g, opp, others, rolls)
    big = body("Big", 9.0)
    g.board.append(big)
    piece = body("Piece", 1.0)
    g.board.append(piece)
    OPP.held_answer_window(g, "combo", pieces=[piece])
    check("E the combo window kills its piece, not the top threat",
          (piece in g.board, big in g.board), (False, True))

    g, opp, others, rolls, old = game(held_answers=False)
    OPP.spot_removal(g, opp, others, rolls)
    check("F NEIGHBOUR: held_answers False: cast at once, Old dies",
          old in g.board, False)

    g, opp, others, rolls, old = game()
    good = body("Good", 9.0)
    g.board.append(good)
    OPP.spot_removal(g, opp, others, rolls)
    check("G a target at or above the bar is answered now, not held",
          (good in g.board, g.m["answers_held"]), (False, 0))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z221 A6: held answers\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.held_answer_window

    def combat_as_end(g, when, pieces=()):
        return real(g, "end" if when == "combat" else when, pieces)

    def end_does_nothing(g, when, pieces=()):
        if when == "end":
            return None
        return real(g, when, pieces)

    muts = {
        "held_answers=False": ({"A", "B", "C", "D", "E"},
                               {"held_answers": False},
                               []),
        "the combat window spends like the end step": ({"C"}, {}, [
            (OPP, "held_answer_window", combat_as_end)]),
        "the end window casts nothing": ({"D"}, {}, [
            (OPP, "held_answer_window", end_does_nothing)]),
        "held_answer_bar=None": ({"G"}, {"held_answer_bar": None}, []),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = {**BASE, **cfg}
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = dict(BASE)
            for obj, name, val in saved:
                setattr(obj, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
