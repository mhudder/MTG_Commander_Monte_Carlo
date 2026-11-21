#!/usr/bin/env python3
"""§0z224: ward against the pod's spot removal (`ward_text`).

    python -m tests.test_ward
    python -m tests.test_ward --mutate   # 3 mutations, exact sets

Each case fires opponent 0's spot removal at you (its row forced, A6's
holding off) at a battlefield set by hand: Tivit, Seller of Secrets (ward
{3}) or Hexing Squelcher (ward -- pay 2 life) as the most threatening
permanent, and a lesser creature beside it where a case says.

CASES
  A  Tivit, `ward_pay_share` 1: the ward is paid, Tivit dies
  B  Tivit and a lesser creature, share 0: the pod cannot pay and re-aims --
     the lesser creature dies, Tivit lives
  C  Tivit alone, share 0: no other target, the removal is not cast
  D  Hexing Squelcher, the opponent at 40: it pays 2 life (38) and the
     Squelcher dies
  E  Hexing Squelcher and a lesser ARTIFACT, the opponent at 2: paying would
     kill it, so it re-aims -- the artifact dies (a creature would be warded
     by the Squelcher's grant, G)
  F  NEIGHBOUR: `ward_text` False, share 0: Tivit dies, the old rule
  G  Squelcher's GRANT: another creature of yours, the top threat, has
     "Ward--Pay 2 life": the opponent pays 2 (38) and it dies
  H  THE DEFAULT RULE, the pod's mana by its turn: pod turn 5, the removal
     costs `SPOT_SPELL_MV` (3) and the ward 3 more -- unpaid, re-aimed: the
     lesser dies, Tivit lives
  I  pod turn 6: 3 + 3 is affordable, the ward is paid, Tivit dies
  (A-C pin the first build's roll, `ward_pay_rule` "share".)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  ward_text=False                              -> B, C, D, E, G, H
  (G added with the grant, before its run. H CORRECTED AFTER ITS RUN, said
  so: left out of this set by mistake -- with no ward Tivit dies at turn 5.)
  an unpaid ward counters instead of re-aiming -> B, E, H
  the removal spell costs nothing               -> H
  (H, I and the last mutation added with the mana rule, 2026-11-17, before
  their run; B, E's set gains H for the same reason.)

UNMUTATED (§0z15): A and F are Tivit dying under both rules; I is the
ward paid, which no mutation stops.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as LH
import edhmc.opponents as OPP
import edhmc.tivit as TV
from edhmc.decks import _removal as _REM
from edhmc.decks import lorehold_v17 as LM
from edhmc.decks import tivit_v1 as TM
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
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def lesser(g):
    p = EN.Permanent(card=EN.Card(name="Lesser", types=frozenset({"Creature"}),
                                  power=1, toughness=1, threat=1.0), sick=False)
    g.board.append(p)
    return p


def prep(g):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    opp = g.opponents[0]
    opp.p["spot"] = 1.0
    rolls = [-1.0] * OPP.N_SLOTS
    rolls[5] = rolls[7] = 0.999
    return opp, rolls


def tivit(share, **cfg):
    """`share` set: the first build's roll (`ward_pay_rule` "share"), which
    A-C pin; `share` None: the default, the pod's mana by its turn (H, I)."""
    deck, cmd = TM.build()
    rule = ({} if share is None
            else dict(ward_pay_rule="share", ward_pay_share=share))
    g = TV.TivitGame(list(deck), cmd,
                     dict(DEFAULT_CFG, held_answers=False,
                          **{**rule, **EXTRA_CFG, **cfg}), 1)
    opp, rolls = prep(g)
    t = EN.Permanent(card=cmd, sick=False)
    g.board.append(t)
    return g, opp, rolls, t


def squelcher(life):
    deck, cmd = LM.build()
    g = LH.LoreholdGame(list(deck), cmd,
                        dict(DEFAULT_CFG, held_answers=False, **EXTRA_CFG), 1)
    opp, rolls = prep(g)
    card = next(c for c in deck if c.name == "Hexing Squelcher")
    q = EN.Permanent(card=card, sick=False)
    g.board.append(q)
    opp.life = float(life)
    return g, opp, rolls, q


def fire(g, opp, rolls):
    OPP.spot_removal(g, opp, g.opponents[1:], rolls)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, opp, rolls, t = tivit(1.0)
    fire(g, opp, rolls)
    check("A share 1: the ward is paid, Tivit dies", t in g.board, False)

    g, opp, rolls, t = tivit(0.0)
    low = lesser(g)
    fire(g, opp, rolls)
    check("B share 0: re-aimed -- the lesser dies, Tivit lives",
          (t in g.board, low in g.board), (True, False))

    g, opp, rolls, t = tivit(0.0)
    fire(g, opp, rolls)
    check("C share 0, Tivit alone: nothing cast", t in g.board, True)

    g, opp, rolls, q = squelcher(40)
    fire(g, opp, rolls)
    check("D Squelcher: 2 life paid, it dies", (opp.life, q in g.board),
          (38.0, False))

    g, opp, rolls, q = squelcher(2)
    # an ARTIFACT, not a creature: the Squelcher's grant would ward a
    # creature too, and then nothing is affordable (G's rule)
    low = EN.Permanent(card=EN.Card(name="Rock", types=frozenset({"Artifact"}),
                                    threat=1.0), sick=False)
    g.board.append(low)
    fire(g, opp, rolls)
    check("E the opponent at 2: re-aimed -- the lesser dies",
          (q in g.board, low in g.board, opp.life), (True, False, 2.0))

    g, opp, rolls, q = squelcher(40)
    big = EN.Permanent(card=EN.Card(name="Big", types=frozenset({"Creature"}),
                                    power=5, toughness=5, threat=20.0),
                       sick=False)
    g.board.append(big)
    fire(g, opp, rolls)
    check("G Squelcher's grant: 2 life paid for Big, which dies",
          (opp.life, big in g.board, q in g.board), (38.0, False, True))

    for turn, want in ((5, (True, False)), (6, (False, True))):
        g, opp, rolls, t = tivit(None)
        g.turn = turn
        low = lesser(g)
        fire(g, opp, rolls)
        check(("H pod turn 5, a 3-mana removal and ward {3} (6 > 5): "
               "re-aimed" if turn == 5 else
               "I pod turn 6 (3 + 3): the ward is paid, Tivit dies"),
              (t in g.board, low in g.board), want)

    g, opp, rolls, t = tivit(0.0, ward_text=False)
    fire(g, opp, rolls)
    check("F NEIGHBOUR: ward_text False: Tivit dies", t in g.board, False)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z224: ward against the pod's spot removal\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.ward_choice

    def counter_not_reaim(g, opp, victim, targets):
        got = real(g, opp, victim, targets)
        return None if got is not victim else got

    muts = {
        "ward_text=False": ({"B", "C", "D", "E", "G", "H"},
                            {"ward_text": False},
                            []),
        "an unpaid ward counters instead of re-aiming": ({"B", "E", "H"}, {}, [
            (OPP, "ward_choice", counter_not_reaim)]),
        "the removal spell costs nothing": ({"H"}, {}, [
            (_REM, "SPOT_SPELL_MV", 0.0)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = dict(cfg)
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
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
