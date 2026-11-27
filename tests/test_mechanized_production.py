#!/usr/bin/env python3
"""§0z270: Mechanized Production by its text (tivit, §0z207 item 15).

    python -m tests.test_mechanized_production
    python -m tests.test_mechanized_production --mutate   # 5 mutations

    "Enchant artifact you control. At the beginning of your upkeep, create
    a token that's a copy of enchanted artifact. Then if you control eight
    or more artifacts with the same name as one another, you win the game."
                                          ({2}{U}{U}; Scryfall 2026-11-27)

It was a Treasure each upkeep and a win at eight Treasures. Now it copies
what it enchants (`mech_enchant`, a policy: the largest token pile, ties to
the kind spent least) and any eight of a name win.

CASES (tivit, Mechanized Production on the battlefield)
  A  it enters over 3 Clues and 2 Treasures: it enchants the Clues
  B  a tie, 2 Food and 2 Treasures: it enchants the Food
  C  enchanting a Clue, the upkeep copies a Clue: 3 -> 4
  D  7 Clues, the upkeep's copy makes 8: you win
  E  enchanting a Clue, 8 Food already: you win
  F  enchanting a Clue, no Clue left: the Aura falls off, nothing copied
  G  NEIGHBOUR: mech_text=False -- a Treasure each upkeep, 8 Clues no win
  H  Academy Manufactor: a copied Clue is one of each
  I  no token at all: it enchants a real artifact (Sol Ring), and the
     upkeep counts a copy of it

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the win reads Treasures only              -> D, E
  the copy is always a Treasure             -> C, D
  the Aura never falls off                  -> F
  a tie goes to the Treasure                -> B
  it always enchants a Treasure             -> A, B, I

UNMUTATED (§0z15): G is the switch's neighbour; H holds under the second
mutation too (a Manufactor Treasure is also one of each).
"""
import sys

import edhmc.tivit as TI
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
MECH = "Mechanized Production"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(piles=None, extra=(), target=None, **cfg):
    board = [B.card("tivit", MECH)] + [B.card("tivit", n) for n in extra]
    g = B.fresh("tivit", board=board, **{**EXTRA_CFG, **cfg})
    g.turn = 4
    for k in g.tokens:
        g.tokens[k] = 0
    for k, v in (piles or {}).items():
        g.tokens[k] = v
    g.mech_target = target
    g.mech_real_copies = 0
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game({"Clue": 3, "Treasure": 2})
    TI.mech_enchant(g)
    check("A it enchants the larger pile, the Clues", g.mech_target, "Clue")

    g = game({"Food": 2, "Treasure": 2})
    TI.mech_enchant(g)
    check("B a tie goes to the Food", g.mech_target, "Food")

    g = game({"Clue": 3}, target="Clue")
    TI.mech_upkeep(g)
    check("C the upkeep copies a Clue", g.tokens["Clue"], 4)

    g = game({"Clue": 7}, target="Clue")
    check("D the eighth Clue wins", (TI.mech_upkeep(g), g.result),
          (True, "win"))

    g = game({"Clue": 2, "Food": 8}, target="Clue")
    check("E eight Food win", (TI.mech_upkeep(g), g.result), (True, "win"))

    g = game({"Treasure": 3}, target="Clue")
    TI.mech_upkeep(g)
    check("F no Clue: the Aura falls off, nothing copied",
          (g.has(MECH), MECH in [c.name for c in g.graveyard],
           g.tokens["Treasure"]), (False, True, 3))

    g = game({"Clue": 8, "Treasure": 1}, target="Clue", mech_text=False)
    won = TI.mech_upkeep(g)
    check("G mech_text=False: a Treasure, eight Clues no win",
          (won, g.tokens["Treasure"], g.tokens["Clue"]), (False, 2, 8))

    g = game({"Clue": 3}, extra=["Academy Manufactor"], target="Clue")
    TI.mech_upkeep(g)
    check("H Manufactor: one of each",
          (g.tokens["Treasure"], g.tokens["Clue"], g.tokens["Food"]),
          (1, 4, 1))

    g = game({}, extra=["Sol Ring"])
    TI.mech_enchant(g)
    TI.mech_upkeep(g)
    check("I no token: a real artifact, its copy counted",
          (g.mech_target, TI.mech_count(g)), (("real", "Sol Ring"), 2))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z270: Mechanized Production by its text\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(TI, n) for n in
            ("mech_wins_now", "make_token", "mech_enchant", "mech_upkeep")}

    def treasures_only(g):
        return g.tokens["Treasure"] >= 8

    def treasure_copy(g, kind, n=1, tapped=False):
        return real["make_token"](g, "Treasure" if kind in TI.MECH_KINDS
                                  else kind, n, tapped)

    def never_falls(g):
        if g.mech_target is not None and not isinstance(g.mech_target,
                                                        tuple):
            g.tokens[g.mech_target] = max(1, g.tokens[g.mech_target])
        return real["mech_upkeep"](g)

    def tie_to_treasure(g):
        piles = [k for k in TI.MECH_KINDS if g.tokens.get(k, 0) > 0]
        if piles:
            g.mech_target = max(reversed(piles), key=lambda k: g.tokens[k])
            return
        real["mech_enchant"](g)

    def always_treasure(g):
        g.mech_target = "Treasure"

    muts = {
        "the win reads Treasures only": (
            {"D", "E"}, "mech_wins_now", treasures_only),
        "the copy is always a Treasure": (
            {"C", "D"}, "make_token", treasure_copy),
        "the Aura never falls off": ({"F"}, "mech_upkeep", never_falls),
        "a tie goes to the Treasure": ({"B"}, "mech_enchant",
                                       tie_to_treasure),
        "it always enchants a Treasure": ({"A", "B", "I"}, "mech_enchant",
                                          always_treasure),
    }
    bad = 0
    for label, (want, name, value) in muts.items():
        print(f"-- {label}")
        setattr(TI, name, value)
        try:
            broke = run_cases()
        finally:
            setattr(TI, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
