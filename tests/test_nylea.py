#!/usr/bin/env python3
"""§0z256: Nylea's Intervention searches for up to X LAND cards, not Forests.

    python -m tests.test_nylea
    python -m tests.test_nylea --mutate   # 3 mutations, exact sets

    "Choose one -- * Search your library for up to X land cards, reveal
    them, put them into your hand, then shuffle. * Nylea's Intervention
    deals twice X damage to each creature with flying."
                                    ({X}{G}{G}, Sorcery; Scryfall 2026-11-25)

Resolved directly, so X is the card's fixed `x_pips` (3) -- `x_paid`'s
answer when the main phase did not pay it. The flier mode is not modelled
(the pod's bodies carry one flag for flying or reach) and is not tested.

CASES -- the library is set whole: three Forests, Evolving Wilds, Fabled
Passage, Strip Mine, and filler.
  A  any land, by `land_rank`: Evolving Wilds, Fabled Passage (fetches),
     then a Forest (green) -- not Strip Mine
  B  NEIGHBOUR: nylea_any_land=False -- three Forests, the old rule
  C  `x_limit` counts every land (6), not the Forests (3)
  D  a library whose only land is Strip Mine: it is taken; no crash

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  nylea_any_land=False everywhere            -> A, C, D
  land_rank ranks every land alike           -> A
  x_limit counts the Forests only            -> C

UNMUTATED (§0z15): B is the switch's neighbour.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")
LANDS = ["Forest", "Forest", "Forest", "Evolving Wilds", "Fabled Passage",
         "Strip Mine"]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def filler(i):
    return EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1})


def game(lands=LANDS, **cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.library.extend(g.hand)
    g.hand = []
    nylea = take(g, "Nylea's Intervention")
    picked = [take(g, n) for n in lands]
    g.library = [filler(i) for i in range(10)] + picked
    g.board = EN.Board()
    return g, nylea


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, nylea = game()
    g.resolve(nylea)
    check("A any land by rank: the two fetches, then a Forest",
          sorted(c.name for c in g.hand),
          ["Evolving Wilds", "Fabled Passage", "Forest"])

    g, nylea = game(nylea_any_land=False)
    g.resolve(nylea)
    check("B nylea_any_land=False: three Forests",
          sorted(c.name for c in g.hand), ["Forest", "Forest", "Forest"])

    g, nylea = game()
    lim = g.x_limit(nylea)
    check("C x_limit counts every land", (lim(6), lim(7)), (True, False))

    g, nylea = game(lands=["Strip Mine"])
    g.resolve(nylea)
    check("D only Strip Mine: it is taken",
          [c.name for c in g.hand], ["Strip Mine"])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z256: Nylea's Intervention\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_rank = AzusaGame.land_rank
    real_limit = AzusaGame.x_limit

    def forests_limit(self, card):
        if card.script != "nylea_land":
            return real_limit(self, card)
        n = sum(1 for c in self.library if c.is_land and c.name == "Forest")
        return lambda x: x <= max(card.x_pips, n)

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_rank(v):
        AzusaGame.land_rank = v

    def set_limit(v):
        AzusaGame.x_limit = v

    muts = {
        "nylea_any_land=False everywhere": (
            {"A", "C", "D"}, set_cfg, {"nylea_any_land": False}, {}),
        "land_rank ranks every land alike": (
            {"A"}, set_rank, lambda self, card: 0.0, real_rank),
        "x_limit counts the Forests only": (
            {"C"}, set_limit, forests_limit, real_limit),
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
