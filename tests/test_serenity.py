#!/usr/bin/env python3
"""§0z263 (was §0z255): Angel of Serenity's ETB, a census route answer.

    python -m tests.test_serenity
    python -m tests.test_serenity --mutate   # 4 mutations, exact sets

    "When this creature enters, you may exile up to three other target
    creatures from the battlefield and/or creature cards from graveyards.
    When this creature leaves the battlefield, return the exiled cards to
    their owners' hands."            ({4}{W}{W}{W}; Scryfall 2026-11-25)

The census missed the card -- its exile rule read "(another )?target" --
and §0z255 read it by hand in shilgengar. Since §0z263 the rule reads
"(an)?other target" and `answer_reach` reads "up to three" through twenty
characters, not twelve, so `opponents.ANSWERS` has it: its cast answers
from `countered` (`answer_pod_threat`), every other entry from
`answer_on_entry` (shilgengar's `ETB_RETURN_KNOBS`, `serenity_etb_returns`).

CASES (opponent 0 holds the pieces, out since round 0; the others none)
  A  the cast's answer, an artifact piece first and three creature pieces:
     the three creatures leave, the artifact stays
  B  a return (`make_permanent`), one creature piece: it leaves
  C  four creature pieces, a return: exactly three leave
  D  only an artifact piece, a return: nothing leaves; the entry counted
  E  NEIGHBOUR: serenity_etb_returns=False -- B's return, nothing leaves
  F  the census clause reads three creature targets (`answer_reach`)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  serenity_etb_returns=False everywhere          -> B, C
  Serenity's reach cut to one target             -> A, C
  Serenity's reach reaches artifacts too         -> A, D
  answer_reach misses "up to three other"        -> F

UNMUTATED (§0z15): E is the switch's neighbour.
"""
import sys

import edhmc.opponents as OPP
from edhmc.decks import _removal
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
NAME = "Angel of Serenity"
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


def angel():
    return B.card("shilgengar", NAME)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game((ARTIFACT, CREATURE, CREATURE, CREATURE))
    OPP.answer_pod_threat(g, angel())
    check("A the cast: three creature pieces leave, the artifact stays",
          out(g, o), ("Artifact",))

    g, o = game((CREATURE,))
    g.make_permanent(angel())
    check("B a return: the creature piece leaves", out(g, o), ())

    g, o = game((CREATURE,) * 4)
    g.make_permanent(angel())
    check("C four creature pieces: three leave", out(g, o), ("Creature",))

    g, o = game((ARTIFACT,))
    g.make_permanent(angel())
    check("D only an artifact: nothing leaves, the entry counted",
          (out(g, o), g.m["etb_answer_returns"]), (("Artifact",), 1))

    g, o = game((CREATURE,), serenity_etb_returns=False)
    g.make_permanent(angel())
    check("E serenity_etb_returns=False: nothing leaves", out(g, o),
          ("Creature",))

    r = OPP.answer_reach(_removal.INTERACTION[NAME][2])
    check("F the census clause: three creature targets",
          (sorted(r.types), r.n), (["Creature"], 3))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z263: Angel of Serenity\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.ANSWERS[NAME]
    real_reach = OPP.answer_reach

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_answer(v):
        OPP.ANSWERS[NAME] = v

    def set_reach(v):
        OPP.answer_reach = v

    def twelve(clause):
        r = real_reach(clause)
        return r._replace(n=1) if "three other target" in clause.lower() else r

    muts = {
        "serenity_etb_returns=False everywhere": (
            {"B", "C"}, set_cfg, {"serenity_etb_returns": False}, {}),
        "Serenity's reach cut to one target": (
            {"A", "C"}, set_answer, real._replace(n=1), real),
        "Serenity's reach reaches artifacts too": (
            {"A", "D"}, set_answer,
            real._replace(types=frozenset({"Creature", "Artifact"})), real),
        "answer_reach misses 'up to three other'": (
            {"F"}, set_reach, twelve, real_reach),
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
