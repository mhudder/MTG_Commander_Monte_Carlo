#!/usr/bin/env python3
"""§0z252: Angel of Despair's and Angel of the Ruins' ETBs on every entry,
not on a cast alone.

    python -m tests.test_etb_answer_returns
    python -m tests.test_etb_answer_returns --mutate   # 4 mutations, exact sets

    Angel of Despair: "When this creature enters, destroy target permanent."
    Angel of the Ruins: "When this creature enters, exile up to two target
    artifacts and/or enchantments."                    (Scryfall 2026-11-24)

Both are route answers in the census (`opponents.ANSWERS`); on a CAST the
ETB resolves from `opponents.countered` (`answer_pod_threat`). Every other
entry -- the ultimate, Avacyn, Sun Titan, the upkeep and activated returns
-- goes through `ShilgengarGame.make_permanent` without `cast=True`, and
`opponents.answer_on_entry` resolves it there.

CASES
  A  Despair enters off the cast path, a creature piece out: the piece
     leaves, one entry answer
  B  Despair through `resolve` (the cast path, `cast=True`): no entry
     answer, the piece stays -- the cast's ETB is `countered`'s, not this
  C  Ruins enters off the cast path, an artifact, an enchantment and a
     creature piece out: the two noncreature pieces leave, the creature stays
  D  Ruins with only a creature piece out: a whiff, counted, the piece stays
  E  NEIGHBOUR: despair_etb_returns=False -- A's entry removes nothing
  F  NEIGHBOUR: ruins_etb_returns=False -- C's entry removes nothing
  G  a real return path: Avacyn's end-step return of Despair takes the piece
  H  `check_etb_return_knobs`: the real set passes; a stray name and an ETB
     answer with no switch each raise

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  answer_on_entry does nothing                  -> A, C, D, G
  make_permanent ignores its cast flag          -> B
  ETB_ANSWERS without Angel of the Ruins        -> C, D, H
  Ruins' reach cut to one target                -> C

UNMUTATED (§0z15): E and F are the switches' neighbours; no mutation of the
rule reaches a leg whose switch is off.
"""
import sys

import edhmc.opponents as OPP
import edhmc.shilgengar as S
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DESPAIR = B.card("shilgengar", "Angel of Despair")
RUINS = B.card("shilgengar", "Angel of the Ruins")
CREATURE = OPP.ThreatPiece("Creature", 3, 3, 1)
ARTIFACT = OPP.ThreatPiece("Artifact", 0, 3, 1)
ENCHANTMENT = OPP.ThreatPiece("Enchantment", 0, 3, 1)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(pieces, **kw):
    """Your turn 3; opponent 0 holds `pieces`, every one out since round 0;
    the other opponents hold none, so every aim is at opponent 0."""
    g = B.fresh("shilgengar", **kw)
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


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game((CREATURE,))
    g.make_permanent(DESPAIR)
    check("A Despair off the cast path: the creature piece leaves",
          (out(g, o), g.m["entry_answers"]), ((), 1))

    g, o = game((CREATURE,))
    g.resolve(DESPAIR)
    check("B Despair through resolve: no entry answer, the piece stays",
          (out(g, o), g.m["entry_answers"]), (("Creature",), 0))

    g, o = game((ARTIFACT, ENCHANTMENT, CREATURE))
    g.make_permanent(RUINS)
    check("C Ruins: the artifact and enchantment leave, the creature stays",
          (out(g, o), g.m["entry_answers"]), (("Creature",), 1))

    g, o = game((CREATURE,))
    g.make_permanent(RUINS)
    check("D Ruins with only a creature out: a whiff, the piece stays",
          (out(g, o), g.m["entry_answers_whiffed"]), (("Creature",), 1))

    g, o = game((CREATURE,), despair_etb_returns=False)
    g.make_permanent(DESPAIR)
    check("E despair_etb_returns=False: nothing leaves",
          (out(g, o), g.m["entry_answers"]), (("Creature",), 0))

    g, o = game((ARTIFACT, ENCHANTMENT), ruins_etb_returns=False)
    g.make_permanent(RUINS)
    check("F ruins_etb_returns=False: nothing leaves",
          (out(g, o), g.m["entry_answers"]), (("Artifact", "Enchantment"), 0))

    g, o = game((CREATURE,))
    g.graveyard = [DESPAIR]
    g.avacyn_queue = [DESPAIR]
    g.avacyn_returns()
    check("G Avacyn returns Despair: the piece leaves",
          (out(g, o), g.m["avacyn_returns"], g.m["entry_answers"]),
          ((), 1, 1))

    real = (not raises(S.check_etb_return_knobs),
            raises(lambda: S.check_etb_return_knobs(
                knobs={**S.ETB_RETURN_KNOBS, "Sol Ring": "x"})),
            raises(lambda: S.check_etb_return_knobs(
                knobs={"Angel of the Ruins": "ruins_etb_returns"},
                run_by=("Angel of Despair", "Angel of the Ruins"))))
    check("H the switch set is checked against the census", real,
          (True, True, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z252: ETB answers on every entry\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_entry = OPP.answer_on_entry
    real_mp = S.ShilgengarGame.make_permanent
    real_etb = OPP.ETB_ANSWERS
    real_ruins = OPP.ANSWERS[RUINS.name]

    def ignore_cast(self, card, *a, cast=False, **k):
        return real_mp(self, card, *a, **k)

    def set_entry(v):
        OPP.answer_on_entry = v

    def set_mp(v):
        S.ShilgengarGame.make_permanent = v

    def set_etb(v):
        OPP.ETB_ANSWERS = v

    def set_ruins(v):
        OPP.ANSWERS[RUINS.name] = v

    muts = {
        "answer_on_entry does nothing": (
            {"A", "C", "D", "G"}, set_entry, lambda g, c: 0, real_entry),
        "make_permanent ignores its cast flag": (
            {"B"}, set_mp, ignore_cast, real_mp),
        "ETB_ANSWERS without Angel of the Ruins": (
            {"C", "D", "H"}, set_etb, real_etb - {RUINS.name}, real_etb),
        "Ruins' reach cut to one target": (
            {"C"}, set_ruins, real_ruins._replace(n=1), real_ruins),
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
