#!/usr/bin/env python3
"""§0z227: Woe Strider's free sacrifice outlet and its escape (rendmaw).

    python -m tests.test_woe_strider
    python -m tests.test_woe_strider --mutate   # 3 mutations, exact sets

Each case: a rendmaw game on a battlefield set by hand, with
`woe_strider_outlet` True (set here after the first run, when its default
was False; it is True since §0z233, said in `engine.woe_strider_outlet`),
and the death step's old rule, `altar_death_step` "two". The outlet cases
call `activations` with Blood Artist out and eight Goat tokens (`altar_keep`
6, so two are fodder); the escape cases put Woe Strider in the graveyard
beside the cards a case names and five untapped Swamps out, and call
`main_phase` (postcombat) on an empty hand.

CASES
  A  Woe Strider and Blood Artist, no Ashnod's Altar: two Goats sacrificed
     -- two deaths Blood Artist sees
  B  NEIGHBOUR: Blood Artist alone, no outlet: nothing sacrificed
  C  Woe Strider and four other cards in the graveyard, {3}{B}{B} open: it
     escapes -- on the battlefield with two +1/+1 counters, a Goat made, the
     graveyard empty
  D  three other cards only: no escape
  E  Proft, Sinister Mastermind in hand and six cards in the graveyard
     (Proft not castable yet; escaping would leave one): no escape, Proft's
     threshold kept
  F  NEIGHBOUR: `woe_strider_escape` False, C's setup: no escape

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  woe_strider_outlet=False      -> A
  woe_strider_escape=False      -> C
  the Proft guard removed       -> E

(E and its mutation CORRECTED AFTER THE RUN, said so; the set is unchanged.
The mutation was first PROFT_THRESHOLD lowered, which also ungated Proft's
own cast; the guard is its own seam now, `woe_spares_proft`. And E first
had eight cards in the graveyard, where Proft is castable, outranks the
escape and takes the mana -- E held without the guard. Six cards: Proft
cannot be cast, so only the guard stops the escape.)

UNMUTATED (§0z15): B has no outlet under any rule; D and F cannot escape
under any rule here.
"""
import random
import sys

import edhmc.engine as EN
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(zone, name):
    c = next(x for x in zone if x.name == name)
    EN.remove_card(zone, c)
    return c


def game(**cfg):
    deck, cmd = RM.build()
    # the outlet is set on explicitly (its default was False until §0z233),
    # and a mutation's cfg still wins over a case's
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "woe_strider_outlet": True,
                 # the death step's old rule, which case A pins the outlet
                 # under (the default is "lethal" since §0z233; set after
                 # the flip, no expectation changed)
                 "altar_death_step": "two", **cfg,
                 **EXTRA_CFG},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.commander_cast = True
    g.turn = 6
    return g


def outlet_game(woe):
    g = game()
    names = ["Blood Artist"] + (["Woe Strider"] if woe else [])
    for n in names:
        g.board.append(EN.Permanent(card=take(g.library, n), sick=False))
    g.make_tokens(8, 0, 1, "Goat")
    for p in g.board:
        p.sick = False
    return g


def escape_game(others, proft=False, **cfg):
    g = game(**cfg)
    for _ in range(5):
        g.board.append(EN.Permanent(card=take(g.library, "Swamp"), sick=False))
    g.graveyard.append(take(g.library, "Woe Strider"))
    spare = [c for c in g.library if not c.is_land
             and c.name != "Wickerfolk Indomitable"][:others]
    for c in spare:
        EN.remove_card(g.library, c)
        g.graveyard.append(c)
    if proft:
        g.hand.append(RM.PROFT_SINISTER_MASTERMIND)
    return g


def goats(g):
    # a token's name is "<subtype> token" (the first run counted "Goat" and
    # found none -- a helper fixed after the run, no expectation changed)
    return sum(1 for p in g.board if p.is_token and p.card.name == "Goat token")


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = outlet_game(True)
    before = goats(g)
    EN.activations(g)
    check("A Woe Strider and Blood Artist: two Goats sacrificed",
          (before - goats(g), g.m["woe_strider_sacs"]), (2, 2))

    g = outlet_game(False)
    before = goats(g)
    EN.activations(g)
    check("B NEIGHBOUR: no outlet: nothing sacrificed", before - goats(g), 0)

    g = escape_game(4)
    EN.main_phase(g)
    woe = [p for p in g.board if p.card.name == "Woe Strider"]
    check("C escaped: two counters, a Goat, the graveyard empty",
          (len(woe), woe[0].counters if woe else None, goats(g),
           len(g.graveyard), g.m["woe_strider_escapes"]),
          (1, 2, 1, 0, 1))

    g = escape_game(3)
    EN.main_phase(g)
    check("D three other cards: no escape", g.m["woe_strider_escapes"], 0)

    g = escape_game(5, proft=True)
    EN.main_phase(g)
    check("E Proft in hand, six cards: no escape",
          g.m["woe_strider_escapes"], 0)

    g = escape_game(4, woe_strider_escape=False)
    EN.main_phase(g)
    check("F NEIGHBOUR: woe_strider_escape False: no escape",
          g.m["woe_strider_escapes"], 0)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z227: Woe Strider\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "woe_strider_outlet=False": ({"A"}, {"woe_strider_outlet": False}, []),
        "woe_strider_escape=False": ({"C"}, {"woe_strider_escape": False}, []),
        "the Proft guard removed": ({"E"}, {}, [
            (EN, "woe_spares_proft", lambda g: False)]),
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
