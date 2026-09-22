#!/usr/bin/env python3
"""Ginger, Queen of Sweets — the first card that uses the monarch (§0z39).

    python -m tests.test_ginger
    python -m tests.test_ginger --mutate   # 5 mutations, exact sets

PREVIEW TEXT. Reality Fracture releases 2026-10-02; this text was fetched from
Scryfall on 2026-09-22 and can change before release.

    {6}  6/4  Legendary Artifact Creature — Food Noble
    When Ginger enters, you become the monarch.
    {2}, {T}, Sacrifice Ginger: You gain 6 life.
    At the beginning of each upkeep, if you're the monarch, create a
    Gingerbrute token. (a {1} 1/1 Food Golem artifact creature with haste,
    "{1}: This token can't be blocked this turn except by creatures with
    haste," and "{2}, {T}, Sacrifice this token: You gain 3 life.")

WHY KARLOV AND NOT TIVIT, since colour identity is empty and every list is
legal. Tivit is the stronger raw fit and that is the argument against it: a
Gingerbrute is a FOOD, so it would trigger Academy Manufactor, be doubled by
the staged Anointed Procession and feed Time Sieve (§0m) — three interactions
at once, and §0z27 is the finding that redundancy rewrites every row around
it. In karlov the value decomposes into things measured separately: the
crown's card, 1/1 HASTE bodies (§0v made width worth something), and a
lifegain EVENT per sacrifice, which is the payoff this deck counts.

CASES
  A  Ginger's ETB takes the crown
  B  your own upkeep makes a Gingerbrute while you hold it
  C  and makes NONE when you do not — "if you're the monarch" is a condition
  D  the token is a 1/1 ARTIFACT creature with HASTE (enters unsick)
  E  the pod's three upkeeps make three
  F  two Gingers make two per upkeep — it is a per-copy trigger
  G  a Gingerbrute ENTERING is a creature entering, so the sisters read it
  H  the sacrifice gains 3 life as an EVENT, and is a DEATH
  I  it keeps `gingerbrute_keep` bodies back rather than converting the board
  J  and cannot be taken without the {2}

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the ETB does not take the crown            -> A
  the upkeep token ignores the crown         -> C
  the token enters summoning sick            -> D
  the sacrifice does not gain life           -> H
  the sacrifice ignores gingerbrute_keep     -> I

B, E and F take the crown with `become_monarch` directly rather than by
casting Ginger, so that the ETB mutation reports on A alone — a mutation that
changes one rule and breaks four cases says nothing about which rule broke.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
from edhmc.decks import karlov_v2 as M
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(lands=0, **cfg):
    deck, cmd = M.build()
    g = K.KarlovGame(deck, cmd, dict(DEFAULT_CFG, turns=20, **cfg), 4242)
    g.board = EN.Board()
    g.turn = 8
    for _ in range(lands):
        g.board.append(EN.Permanent(card=EN.Card(
            name="Plains", types=frozenset({"Land"}), is_land=True,
            produces=frozenset({"W"})), sick=False))
    return g


def put(g, name, **kw):
    """A permanent on the battlefield by name, without casting it."""
    card = next(c for c in (M.GINGER_QUEEN_OF_SWEETS,) if c.name == name) \
        if name == "Ginger, Queen of Sweets" else EN.Card(
            name=name, types=frozenset({"Creature"}), power=1, toughness=1)
    g.board.append(EN.Permanent(card=card, sick=False))


def brutes(g):
    return [p for p in g.board if p.card.name == "Gingerbrute token"]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A: the ETB takes the crown --------------------------------------
    g = fresh()
    was = g.monarch
    K.resolve(g, M.GINGER_QUEEN_OF_SWEETS)
    check("A Ginger's ETB takes the crown",
          (was, g.monarch, g.m["monarch_gained"]), (False, True, 1))

    # ---- B: your upkeep, holding the crown --------------------------------
    g = fresh()
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 1)
    check("B your own upkeep makes a Gingerbrute while you hold the crown",
          (len(brutes(g)), g.m["gingerbrutes_made"]), (1, 1))

    # ---- C: and none without it ------------------------------------------
    g = fresh()
    put(g, "Ginger, Queen of Sweets")
    K.gingerbrute_tokens(g, 1)          # no crown
    check("C no crown, no Gingerbrute -- the condition is read",
          (len(brutes(g)), g.m["gingerbrutes_made"]), (0, 0))

    # ---- D: haste, artifact, 1/1 -----------------------------------------
    g = fresh()
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 1)
    b = brutes(g)[0]
    check("D the token is a 1/1 artifact creature with HASTE",
          (b.sick, b.is_token, b.card.power, b.card.toughness,
           "Artifact" in b.card.types, "Creature" in b.card.types),
          (False, True, 1, 1, True, True))

    # ---- E: the pod's three ----------------------------------------------
    g = fresh()
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 3)
    check("E the pod's three upkeeps make three", len(brutes(g)), 3)

    # ---- F: per copy ------------------------------------------------------
    g = fresh()
    put(g, "Ginger, Queen of Sweets")
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 1)
    check("F two Gingers make two per upkeep", len(brutes(g)), 2)

    # ---- G: entering is a creature entering -------------------------------
    g = fresh()
    put(g, "Ginger, Queen of Sweets")
    put(g, "Suture Priest")
    OPP.become_monarch(g)
    before = g.m["lifegain_triggers"]
    K.gingerbrute_tokens(g, 1)
    check("G a Gingerbrute entering is a creature entering",
          g.m["lifegain_triggers"] > before, True)

    # ---- H: the sacrifice is life AND a death -----------------------------
    # exactly {2} available, so only ONE sacrifice can be paid for.
    g = fresh(lands=2, gingerbrute_keep=0)
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 1)
    life, trig = g.your_life, g.m["lifegain_triggers"]
    K.gingerbrute_sacrifices(g)
    check("H the sacrifice gains 3 life as an event, and is a death",
          (g.your_life - life, g.m["lifegain_triggers"] > trig,
           g.m["gingerbrute_sacs"], g.creature_died_this_turn,
           len(brutes(g))),
          (3.0, True, 1, True, 0))

    # ---- I: it keeps bodies back ------------------------------------------
    g = fresh(lands=8, gingerbrute_keep=2)
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 3)          # three bodies, mana for three sacs
    K.gingerbrute_sacrifices(g)
    check("I gingerbrute_keep bodies are kept as attackers",
          (len(brutes(g)), g.m["gingerbrute_sacs"]), (2, 1))

    # ---- J: no mana, no sacrifice -----------------------------------------
    g = fresh(lands=0, gingerbrute_keep=0)
    put(g, "Ginger, Queen of Sweets")
    OPP.become_monarch(g)
    K.gingerbrute_tokens(g, 1)
    K.gingerbrute_sacrifices(g)
    check("J the sacrifice cannot be taken without the {2}",
          (len(brutes(g)), g.m["gingerbrute_sacs"]), (1, 0))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Ginger, Queen of Sweets -- the crown, the brutes, the life\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_tokens = K.gingerbrute_tokens
    real_sacs = K.gingerbrute_sacrifices
    real_etb = K.ginger_etb
    real_gain = K.gain_life
    expected = {
        "the ETB does not take the crown": {"A"},
        "the upkeep token ignores the crown": {"C"},
        "the token enters summoning sick": {"D"},
        "the sacrifice does not gain life": {"H"},
        "the sacrifice ignores gingerbrute_keep": {"I"},
    }
    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == "the ETB does not take the crown":
            # ONLY the ETB, which is why it is its own function. Patching
            # OPP.become_monarch instead disabled the crown for every case in
            # this file -- eight failures reporting on one rule.
            K.ginger_etb = lambda g: None
        elif label == "the upkeep token ignores the crown":
            def ungated(g, upkeeps):
                held, g.monarch = g.monarch, True
                real_tokens(g, upkeeps)
                g.monarch = held
            K.gingerbrute_tokens = ungated
        elif label == "the token enters summoning sick":
            def sick(g, upkeeps):
                real_tokens(g, upkeeps)
                for p in g.board:
                    if p.card.name == "Gingerbrute token":
                        p.sick = True          # the haste, dropped
            K.gingerbrute_tokens = sick
        elif label == "the sacrifice does not gain life":
            def nolife(g):
                K.gain_life = lambda g_, n, _depth=0: None
                try:
                    real_sacs(g)
                finally:
                    K.gain_life = real_gain
            K.gingerbrute_sacrifices = nolife
        else:
            def greedy(g):
                g.cfg = dict(g.cfg, gingerbrute_keep=0)   # the knob, ignored
                real_sacs(g)
            K.gingerbrute_sacrifices = greedy
        try:
            broke = run_cases()
        finally:
            K.gingerbrute_tokens = real_tokens
            K.gingerbrute_sacrifices = real_sacs
            K.ginger_etb = real_etb
            K.gain_life = real_gain
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
