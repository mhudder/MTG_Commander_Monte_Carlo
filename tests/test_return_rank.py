#!/usr/bin/env python3
"""§0z277: Eternal Witness and Regrowth return the card with the highest
win-rate row (azusa, the oracle audit's Tier 4 item 15; the owner,
2026-11-27: "lets try highest winrate card instead of highest CMC").

    python -m tests.test_return_rank
    python -m tests.test_return_rank --mutate   # 4 mutations, exact sets

`AzusaGame.return_pick` reads `decks/_return_rank.py`, which
`tools.return_rank` GENERATES from azusa's ablation cache. Case E is the
check that the file is current: after a rebuild, `--write` it.

CASES (azusa)
  A  Mole Man (the table's top row), Genesis Wave and Ulamog (the highest
     mana value) in the graveyard: Mole Man
  B  a land and a nonland card: the nonland
  C  a card with no row (mana value 9) and Abundance (a row): Abundance
  D  NEIGHBOUR: return_by_row=False -- A's graveyard, Ulamog
  E  the generated file is the cache's ranking, as `tools.return_rank`
     derives it today
  F  Regrowth resolving (`_resolve`) returns by the same rule: Mole Man

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the rows ignored (an empty rank)            -> A, C, E, F
  a land before a nonland                     -> B
  the file one row off the cache              -> E
  Regrowth reads the highest mana value       -> F

UNMUTATED (§0z15): D is the switch's neighbour.

BEFORE THE FIRST RUN (§0z11) the first set was re-read and E added: an
empty rank is not the cache's.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.decks import _return_rank as RR
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from tools import return_rank as TOOL

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(**cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    return g


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def grave(g, names):
    g.graveyard = [take(g, n) for n in names]


A_GRAVE = ["Genesis Wave", "Mole Man, Moloid Master",
           "Ulamog, the Infinite Gyre"]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    grave(g, A_GRAVE)
    check("A the top row, not the highest mana value",
          g.return_pick(g.graveyard).name, "Mole Man, Moloid Master")

    g = game()
    grave(g, ["Strip Mine", "Abundance"])
    check("B a nonland before a land", g.return_pick(g.graveyard).name,
          "Abundance")

    g = game()
    grave(g, ["Abundance"])
    g.graveyard.append(EN.Card(name="Unranked", types=frozenset({"Sorcery"}),
                               cost={"gen": 9}))
    check("C a card with a row before one without",
          g.return_pick(g.graveyard).name, "Abundance")

    g = game(return_by_row=False)
    grave(g, A_GRAVE)
    check("D return_by_row=False: the highest mana value",
          g.return_pick(g.graveyard).name, "Ulamog, the Infinite Gyre")

    check("E the generated file is current", RR.RANK, TOOL.derive())

    g = game()
    grave(g, A_GRAVE)
    regrowth = take(g, "Regrowth")
    g.hand = []
    g._resolve(regrowth)
    check("F Regrowth returns by the row", [c.name for c in g.hand],
          ["Mole Man, Moloid Master"])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z277: returns by the win-rate row\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_rank = RR.RANK
    real_pick = AzusaGame.return_pick

    def lands_first(self, pool):
        lands = [c for c in pool if c.is_land]
        return lands[0] if lands else real_pick(self, pool)

    def off_by_one(v):
        rank = {d: dict(r) for d, r in real_rank.items()}
        k = next(iter(rank["azusa"]))
        rank["azusa"][k] += 0.001
        return rank

    def regrowth_mv(self, pool):
        import inspect
        caller = inspect.stack()[1].function
        if caller == "_resolve":
            return max(pool, key=lambda c: c.mv)
        return real_pick(self, pool)

    def set_rank(v):
        RR.RANK = v

    def set_pick(v):
        AzusaGame.return_pick = v

    muts = {
        "the rows ignored": ({"A", "C", "E", "F"}, set_rank, {"azusa": {}},
                             real_rank),
        "a land before a nonland": ({"B"}, set_pick, lands_first, real_pick),
        "the file one row off the cache": ({"E"}, set_rank,
                                           off_by_one(None), real_rank),
        "Regrowth reads the highest mana value": ({"F"}, set_pick,
                                                  regrowth_mv, real_pick),
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
