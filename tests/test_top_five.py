#!/usr/bin/env python3
"""Pin §0z116's top five, fixed in §0z117.

    python -m tests.test_top_five
    python -m tests.test_top_five --mutate   # 4 mutations, exact sets

CASES
  A  Kokusho sacrificed: each opponent loses 5, you gain what they lost
  B  ... and destroyed by the pod's removal, the same
  C  Biotransference: a creature card is an artifact; a sorcery is not
  D  ... Foundry Inspector discounts a creature spell
  E  ... casting a creature spell costs 1 life and makes a 2/2 Necron
  F  ... a one-type creature spell is a two-type card: a Rendmaw trigger
  G  ... Steel Overseer counts a non-artifact creature
  H  Thrill of Possibility discards one, then draws two: hand +1, one card in
     the graveyard
  I  Faithless Looting draws two, then discards two: hand unchanged
  J  a COPY of Thrill pays no additional cost: hand +2
  K  shilgengar's tribe tags come from the type line: Avacyn and Angel of
     Suffering are Angels, Bishop of Wings a Cleric
  L  Avacyn fed to Shilgengar makes Blood equal to her toughness (8)
  M  Coercive Portal's carnage: the Portal and Sol Ring are gone, the
     Treasures are gone, the artifact land stays

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  kokusho_text=False          -> A, B
  biotransference_text=False  -> C, D, E, F, G
  discard_text=False          -> H, I
  portal_text=False           -> M

UNMUTATED (§0z15): J is the copy rule, which holds with the fix off too (the
old code discarded for no copy); K and L are generated data with no switch.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.lorehold as LO
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
import edhmc.tivit as TI
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
LISTS = {d: build_pending(d) for d in ("rendmaw", "lorehold", "shilgengar",
                                       "tivit")}


def card(deck, name):
    return next(c for c in LISTS[deck][0] if c.name == name)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def filler(i):
    return EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1})


def body(name, cost=None, p=2):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=p, cost=cost or {"gen": 3})


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, **{**kw, **CFG})


def fresh(deck, board=(), hand=()):
    d, cmd = LISTS[deck]
    if deck == "rendmaw":
        g = EN.Game(list(d), cmd, cfg(), random.Random(1), seed_for_pod=1)
    elif deck == "lorehold":
        g = LO.LoreholdGame(list(d), cmd, cfg(), 1)
    elif deck == "shilgengar":
        g = SH.ShilgengarGame(list(d), cmd, cfg(), 7)
    else:
        g = TI.TivitGame(list(d), cmd, cfg(), 1)
    g.board = EN.Board()
    g.hand = list(hand)
    g.graveyard = []
    g.library = [filler(i) for i in range(30)]
    g.your_life = 40.0
    g.turn = 5
    for o in g.opponents:
        o.life = 40.0
    for c in board:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    kok = card("shilgengar", "Kokusho, the Evening Star")
    g = fresh("shilgengar", board=[kok])
    g.sacrifice(g.board[0])
    check("A Kokusho sacrificed: each opponent loses 5, you gain it",
          ([o.life for o in g.opponents], g.your_life),
          ([35.0, 35.0, 35.0], 55.0))
    g = fresh("shilgengar", board=[kok])
    OPP.destroy(g, g.board[0])
    check("B ... and destroyed, the same", g.your_life, 55.0)

    bio = card("rendmaw", "Biotransference")
    bear = body("Bear")
    g = fresh("rendmaw", board=[bio])
    check("C Biotransference: a creature card is an artifact",
          (EN.is_artifact(g, bear), EN.is_artifact(g, filler(0))),
          (True, False))
    g = fresh("rendmaw", board=[bio, card("rendmaw", "Foundry Inspector")])
    check("D ... Foundry Inspector discounts a creature spell",
          EN.cost_after_reduction(g, bear)["gen"], 2)
    g = fresh("rendmaw", board=[bio])
    EN.biotransference_cast(g, bear)
    check("E ... a creature spell costs 1 life and makes a Necron",
          (40 - g.your_life, sum(p.card.name.startswith("Necron")
                                 or "Necron" in p.card.name
                                 for p in g.board)), (1, 1))
    g = fresh("rendmaw", board=[bio])
    g.commander_cast = True
    g.play_card_trigger(bear)
    check("F ... a one-type creature spell is a two-type card",
          g.m["rendmaw_triggers"], 1)
    g = fresh("rendmaw", board=[bio, card("rendmaw", "Steel Overseer"),
                                bear])
    EN.steel_overseer(g)
    check("G ... Steel Overseer counts a non-artifact creature",
          next(p for p in g.board if p.card is bear).counters, 1)

    thrill = card("lorehold", "Thrill of Possibility")
    g = fresh("lorehold", hand=[filler(100 + i) for i in range(6)])
    LO.apply_spell_effects(g, thrill)
    check("H Thrill: discard one, draw two",
          (len(g.hand), len(g.graveyard)), (7, 1))
    g = fresh("lorehold", hand=[filler(100 + i) for i in range(6)])
    LO.apply_spell_effects(g, card("lorehold", "Faithless Looting"))
    check("I Faithless Looting: draw two, discard two",
          (len(g.hand), len(g.graveyard)), (6, 2))
    g = fresh("lorehold", hand=[filler(100 + i) for i in range(6)])
    LO.apply_spell_effects(g, thrill, is_copy=True)
    check("J a copy of Thrill pays no additional cost", len(g.hand), 8)

    tags = {n: card("shilgengar", n).tags & {"angel", "cleric"}
            for n in ("Avacyn, Angel of Hope", "Angel of Suffering",
                      "Bishop of Wings")}
    check("K shilgengar's tribe tags come from the type line", tags,
          {"Avacyn, Angel of Hope": {"angel"},
           "Angel of Suffering": {"angel"},
           "Bishop of Wings": {"cleric"}})
    g = fresh("shilgengar", board=[card("shilgengar",
                                        "Avacyn, Angel of Hope")])
    g.sacrifice(g.board[0], to_shilgengar=True)
    check("L Avacyn fed to Shilgengar makes 8 Blood", g.blood, 8)

    g = fresh("tivit", board=[card("tivit", "Coercive Portal"),
                              card("tivit", "Sol Ring"),
                              card("tivit", "Seat of the Synod")])
    for k in list(g.tokens):
        g.tokens[k] = 0
    g.tokens["Treasure"] = 3
    TI.coercive_carnage(g)
    check("M Coercive Portal's carnage",
          (sorted(p.card.name for p in g.board), g.tokens["Treasure"]),
          (["Seat of the Synod"], 0))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z116's top five (§0z117)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"kokusho_text": False}, {"A", "B"}),
        ({"biotransference_text": False}, {"C", "D", "E", "F", "G"}),
        ({"discard_text": False}, {"H", "I"}),
        ({"portal_text": False}, {"M"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for over, want in mutations:
        CFG.update(over)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += not ok
        print(f"   {over}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
