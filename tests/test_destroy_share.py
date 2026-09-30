#!/usr/bin/env python3
"""Item 9: indestructible is priced per KIND of pod answer, from a census
(§0z87).

    python -m tests.test_destroy_share
    python -m tests.test_destroy_share --mutate   # 3 mutations, exact sets

The pod's answers are anonymous rolls (§4), so `opponents.destroy` prices
INDESTRUCTIBLE with the share of answers that DESTROY. That was one assumed
0.60 for spot removal and wipes alike. `tools.removal_census` classifies every
targeted answer and wipe in the six lists from Scryfall text into
`decks/_removal.py`: spot 0.45, wipe 0.54, and the artifact-and-enchantment
event takes the spot share because its own sample is four cards.

CASES
  A  the spot share is the census's DESTROY_SHARE_SPOT
  B  the wipe share is the census's DESTROY_SHARE_WIPE
  C  the ae share is the census's DESTROY_SHARE_AE (the spot share)
  D  NEIGHBOUR: `destroy_share_split=False` is the flat 0.60 for every kind
  E  NEIGHBOUR: a caller that names no kind reads the flat 0.60
  F  an indestructible creature, spot removal rolled 0.50: DESTROYED -- 0.50
     is above the census's 0.45 (the flat 0.60 would have saved it)
  G  the same creature, a wipe rolled 0.50: it SURVIVES -- below 0.54
  H  the census classifies known text: Swords to Plowshares spot/other,
     Beast Within spot/destroy, Wrath of God wipe/destroy, Farewell
     wipe/other, Lightning Bolt ("any target") nothing
  I  the census does not count YOUR OWN "target creature you control":
     Ephemerate is not an answer
  J  the pod's three events name their kinds: spot removal "spot", a single
     Naturalize "ae", the artifact sweeper and a wrath "wipe"

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  destroy_share_for ignores kind (flat 0.60)   -> A, B, C, F
  a wipe takes the spot share                  -> B, G
  the census counts "you control" targets      -> I

UNMUTATED (§0z15): D and E are the knob and the old path. H pins the
classifier's rules against text, and each rule is its own seam. J pins
literal arguments at three call sites, which a mutation could only reach by
editing the source; it fails if any of them is dropped or changed.
"""
import random
import re
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import tools.removal_census as RC
from edhmc.decks import _removal
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
RDECK, RCMD = RM.build()

TEXT = {   # oracle text, api.scryfall.com, 2026-09-30
    "Swords to Plowshares":
        "Exile target creature. Its controller gains life equal to its power.",
    "Beast Within":
        "Destroy target permanent. Its controller creates a 3/3 green Beast "
        "creature token.",
    "Wrath of God": "Destroy all creatures. They can't be regenerated.",
    "Farewell":
        "Choose one or more —\n• Exile all artifacts.\n• Exile all creatures."
        "\n• Exile all enchantments.\n• Exile all graveyards.",
    "Lightning Bolt": "Lightning Bolt deals 3 damage to any target.",
    "Ephemerate":
        "Exile target creature you control, then return it to the battlefield "
        "under its owner's control.\nRebound (If you cast this spell from "
        "your hand, exile it as it resolves. At the beginning of your next "
        "upkeep, you may cast this card from exile.)",
}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(**cfg):
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 6
    return g


def hardy():
    c = EN.Card(name="Hardy", types=frozenset({"Creature"}), power=4,
                toughness=4, indestructible=True)
    return EN.Permanent(card=c, base_p=4, base_t=4, sick=False)


def kinds_named():
    """Which kind each pod event passes to `destroy`."""
    seen = []
    real = OPP.destroy

    def spy(g, perm, roll=None, destroys=None, kind=None):
        seen.append(kind)
        return real(g, perm, roll, destroys, kind)

    OPP.destroy = spy
    out = {}
    try:
        for label, event in (("spot", "spot"), ("ae single", "ae"),
                             ("ae sweeper", "ae"), ("wrath", "wipe")):
            g = game()
            art = EN.Card(name="Relic", types=frozenset({"Artifact"}))
            g.board.append(hardy())
            g.board.append(EN.Permanent(card=art, sick=False))
            opp, others = g.opponents[0], g.opponents[1:]
            opp.bracket = 4 if label == "ae sweeper" else 2
            rolls = [0.0] * 10
            if label == "ae single":
                rolls[4] = 0.99           # not the sweeper
            seen.clear()
            if event == "spot":
                OPP.spot_removal(g, opp, others, rolls)
            elif event == "ae":
                OPP.ae_removal(g, opp, others, rolls)
            else:
                OPP.board_wipe(g, opp, rolls)
            out[label] = sorted(set(seen))
    finally:
        OPP.destroy = real
    return out


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = game()
    check("A spot share from the census",
          OPP.destroy_share_for(g, "spot"), _removal.DESTROY_SHARE_SPOT)
    check("B wipe share from the census",
          OPP.destroy_share_for(g, "wipe"), _removal.DESTROY_SHARE_WIPE)
    check("C ae share from the census",
          OPP.destroy_share_for(g, "ae"), _removal.DESTROY_SHARE_AE)
    g = game(destroy_share_split=False)
    check("D destroy_share_split=False: the flat 0.60",
          [OPP.destroy_share_for(g, k) for k in ("spot", "wipe", "ae")],
          [0.60] * 3)
    g = game()
    check("E no kind: the flat 0.60", OPP.destroy_share_for(g, None), 0.60)

    g = game()
    p = hardy()
    g.board.append(p)
    OPP.destroy(g, p, roll=0.50, kind="spot")
    check("F spot removal at 0.50 destroys an indestructible",
          p in g.board, False)
    g = game()
    p = hardy()
    g.board.append(p)
    OPP.destroy(g, p, roll=0.50, kind="wipe")
    check("G a wipe at 0.50 does not", p in g.board, True)

    got = {n: (RC.classify(TEXT[n]) or (None, None))[:2]
           for n in ("Swords to Plowshares", "Beast Within", "Wrath of God",
                     "Farewell", "Lightning Bolt")}
    check("H the census classifies known text", got, {
        "Swords to Plowshares": ("spot", "other"),
        "Beast Within": ("spot", "destroy"),
        "Wrath of God": ("wipe", "destroy"),
        "Farewell": ("wipe", "other"),
        "Lightning Bolt": (None, None)})
    check("I Ephemerate is not an answer", RC.classify(TEXT["Ephemerate"]),
          None)
    check("J each pod event names its kind", kinds_named(), {
        "spot": ["spot"], "ae single": ["ae"], "ae sweeper": ["wipe"],
        "wrath": ["wipe"]})
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Item 9: indestructible priced per kind of answer\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_share = OPP.destroy_share_for
    muts = {
        "destroy_share_for ignores kind (flat 0.60)":
            ({"A", "B", "C", "F"}, OPP, "destroy_share_for",
             lambda g, kind: g.cfg.get("destroy_share", 0.60)),
        "a wipe takes the spot share":
            ({"B", "G"}, OPP, "destroy_share_for",
             lambda g, kind: real_share(g, "spot" if kind == "wipe" else kind)),
        "the census counts \"you control\" targets":
            ({"I"}, RC, "MINE", re.compile(r"(?!)")),
    }
    bad = 0
    for label, (want, owner, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(owner, name)
        setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
