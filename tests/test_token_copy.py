#!/usr/bin/env python3
"""Pin that a token copy has its OWN Card object (§0z175; queue item 33).

    python -m tests.test_token_copy
    python -m tests.test_token_copy --mutate   # 1 mutation, exact set

A token copy carries the copiable values of the creature it copies (CR 707.2),
not the creature's Card object. Azusa's Springheart Nantuko copy and
trostani's `copy_token` (Bramble Sovereign, populate, Mimic Vat) handed the
token the original's Card, so when the original died its card went to the
graveyard while the token still held that object: one object in two zones
(9 games in 3,000 in each deck, `diagnostics/diag_zone_census.py`).

CASES
  A azusa: Springheart's copy of a host is an EQUAL card but not the host's
    object
  B azusa: the host dies (`opponents.destroy`): its card is in the graveyard
    and no permanent on the battlefield holds that object
  C trostani: `copy_token` of a nontoken creature gives the token a card
    equal to, and not the same object as, the creature's
  D `token_copy_own_card=False` restores the sharing, in both engines

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  token_copy_own_card False (cfg)   -> A, B, C

UNMUTATED (§0z15): D is the switch itself. Blind to a copy made by any other
path: the census, not this test, is what reads every zone of every game.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.trostani import TrostaniGame

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
ADECK, ACMD = build_pending("azusa")
TDECK, TCMD = build_pending("trostani")
ACARD = {c.name: c for c in ADECK}
TCARD = {c.name: c for c in TDECK}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def azusa(**kw):
    g = AzusaGame(list(ADECK), ACMD,
                  dict(DEFAULT_CFG, turns=20, **{**kw, **CFG}), 1234)
    g.board, g.hand, g.graveyard = EN.Board(), [], []
    for i in range(4):
        g.make_permanent(ACARD["Forest"], sick=False)
    host = g.make_permanent(ACARD["Lotus Cobra"], sick=False)
    g.springheart_host = host
    return g, host


def copies_of(g, host):
    return [p for p in g.board if p.is_token and p.card.name == host.card.name]


def trostani(**kw):
    g = TrostaniGame(list(TDECK), TCMD,
                     dict(DEFAULT_CFG, turns=20, **{**kw, **CFG}), 1234)
    g.board, g.hand, g.graveyard = EN.Board(), [], []
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()
    g, host = azusa()
    g.springheart_landfall()
    toks = copies_of(g, host)
    check("A Springheart's copy: an equal card, not the host's object",
          (len(toks), toks[0].card == host.card if toks else None,
           toks[0].card is host.card if toks else None), (1, True, False))

    OPP.destroy(g, host)
    on_board = {id(p.card) for p in g.board}
    check("B the host dies: its card is in the graveyard and nowhere else",
          (any(c is host.card for c in g.graveyard), id(host.card) in on_board),
          (True, False))

    g = trostani()
    wurm = TCARD["Wurmcoil Engine"]
    made = g.copy_token(wurm)
    check("C trostani's copy_token: an equal card, not the creature's object",
          (len(made), made[0].card == wurm if made else None,
           made[0].card is wurm if made else None), (1, True, False))

    g, host = azusa(token_copy_own_card=False)
    g.springheart_landfall()
    toks = copies_of(g, host)
    made = trostani(token_copy_own_card=False).copy_token(wurm)
    check("D token_copy_own_card=False shares the object, in both engines",
          (toks[0].card is host.card if toks else None,
           made[0].card is wurm if made else None), (True, True))
    return set(FAIL)


def main():
    if not MUTATE:
        print("a token copy has its own Card (§0z175)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    muts = [("token_copy_own_card False", {"A", "B", "C"},
             {"token_copy_own_card": False})]
    bad = 0
    for label, want, cfg in muts:
        print(f"-- {label}")
        CFG.clear()
        CFG.update(cfg)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
