#!/usr/bin/env python3
"""§0z255: Angel of Serenity's ETB, read by hand -- the census misses it.

    python -m tests.test_serenity
    python -m tests.test_serenity --mutate   # 4 mutations, exact sets

    "When this creature enters, you may exile up to three other target
    creatures from the battlefield and/or creature cards from graveyards.
    When this creature leaves the battlefield, return the exiled cards to
    their owners' hands."            ({4}{W}{W}{W}; Scryfall 2026-11-25)

The census's exile rule reads "another target", so `opponents.ANSWERS`
has no entry for the card and `countered` answers nothing on its cast.
`ShilgengarGame.make_permanent` fires `serenity_etb` on EVERY entry, cast
or not, at up to three creature route pieces (`SERENITY_REACH`).

CASES (opponent 0 holds the pieces, out since round 0; the others none)
  A  the cast (`resolve`), an artifact piece first and three creature
     pieces: the three creatures leave, the artifact stays
  B  a return (`make_permanent`), one creature piece: it leaves
  C  four creature pieces: exactly three leave
  D  only an artifact piece: nothing leaves; the entry is still counted
  E  NEIGHBOUR: serenity_text=False -- A's setup, nothing leaves, counted
  F  `check_serenity_reach`: the real census passes; a census that reads
     the card raises

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  serenity_text=False everywhere               -> A, B, C
  SERENITY_REACH cut to one target             -> A, C
  SERENITY_REACH reaches artifacts too         -> A, D
  check_serenity_reach does nothing            -> F

UNMUTATED (§0z15): E is the switch's neighbour.
"""
import sys

import edhmc.opponents as OPP
import edhmc.shilgengar as S
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
CREATURE = OPP.ThreatPiece("Creature", 3, 3, 1)
ARTIFACT = OPP.ThreatPiece("Artifact", 0, 3, 1)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(pieces, **cfg):
    g = B.fresh("shilgengar", **{**EXTRA_CFG, **cfg})
    g.turn = 3
    for i, o in enumerate(g.opponents):
        o.pieces = tuple(pieces) if i == 0 else ()
        o.piece_lands = [0] * len(o.pieces)
    return g, g.opponents[0]


def out(g, o):
    return tuple(o.pieces[k].type for k in OPP.present_pieces(g, o))


def raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def angel():
    return B.card("shilgengar", S.SERENITY)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game((ARTIFACT, CREATURE, CREATURE, CREATURE))
    g.resolve(angel())
    check("A the cast: three creature pieces leave, the artifact stays",
          (out(g, o), g.m["serenity_exiled"]), (("Artifact",), 3))

    g, o = game((CREATURE,))
    g.make_permanent(angel())
    check("B a return: the creature piece leaves", out(g, o), ())

    g, o = game((CREATURE,) * 4)
    g.make_permanent(angel())
    check("C four creature pieces: three leave", out(g, o), ("Creature",))

    g, o = game((ARTIFACT,))
    g.make_permanent(angel())
    check("D only an artifact: nothing leaves, the entry counted",
          (out(g, o), g.m["serenity_entries"]), (("Artifact",), 1))

    g, o = game((ARTIFACT, CREATURE, CREATURE, CREATURE),
                serenity_text=False)
    g.resolve(angel())
    check("E serenity_text=False: nothing leaves, counted",
          (out(g, o), g.m["serenity_entries"]),
          (("Artifact", "Creature", "Creature", "Creature"), 1))

    check("F the guard: the census passes; one that reads the card raises",
          (not raises(S.check_serenity_reach),
           raises(lambda: S.check_serenity_reach(
               {**OPP.ANSWERS, S.SERENITY: S.SERENITY_REACH}))),
          (True, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z255: Angel of Serenity\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_reach = S.SERENITY_REACH
    real_check = S.check_serenity_reach

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_reach(v):
        S.SERENITY_REACH = v

    def set_check(v):
        S.check_serenity_reach = v

    muts = {
        "serenity_text=False everywhere": (
            {"A", "B", "C"}, set_cfg, {"serenity_text": False}, {}),
        "SERENITY_REACH cut to one target": (
            {"A", "C"}, set_reach, real_reach._replace(n=1), real_reach),
        "SERENITY_REACH reaches artifacts too": (
            {"A", "D"}, set_reach,
            real_reach._replace(types=frozenset({"Creature", "Artifact"})),
            real_reach),
        "check_serenity_reach does nothing": (
            {"F"}, set_check, lambda answers=None: None, real_check),
    }
    bad = 0
    for label, (want, setter, value, restore) in muts.items():
        print(f"-- {label}")
        setter(value)
        try:
            broke = run_cases()
        finally:
            setter(restore)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
