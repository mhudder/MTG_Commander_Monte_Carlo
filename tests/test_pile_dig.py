#!/usr/bin/env python3
"""§0z218: the Clue dig -- a capped Deadeye loop that converts nothing
cracks the pile's Clues for a payoff, casts it, and loops again.

    python -m tests.test_pile_dig
    python -m tests.test_pile_dig --mutate   # 5 mutations, exact sets

Each case: Tivit and Deadeye Navigator on an otherwise empty battlefield,
no lands, the token piles set by hand, and the library's top card chosen.

CASES
  A  the loop caps with no payoff; the dig draws Mirkwood Bats, casts it,
     loops again: a win
  B  Revel in Riches out and ten Treasures: the pile already wins at the
     upkeep, so no Clue is cracked
  C  NEIGHBOUR: two Treasures only -- the loop runs, nothing is left to
     crack a Clue with ({2} and {1}{U} kept back): no draw
  D  the main phase, the combo out and three Clues: the dig comes BEFORE
     casting, draws Disciple of the Vault, and the loop wins
  E  a one-card library: the dig asks `draw_is_safe` and draws nothing
  F  Disciple of the Vault already out, the loop mana-neutral: each
     activation sacrifices two Treasures, so the capped loop is an
     infinite drain -- a win (`capped_drain_wins`), with no dig

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pile_dig=False                          -> A, D
  the Revel / Mechanized guard removed    -> B
  the main-phase dig removed              -> D
  the dig's draw_is_safe ignored          -> E
  capped_drain_wins=False                 -> D, F

UNMUTATED (§0z15): C is the mana limit, which both rules share.
"""
import sys

import edhmc.engine as EN
import edhmc.tivit as TV
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.tivit import TivitGame

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("tivit")


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


def fresh(top=None, treasures=10, clues=0, extra=(), **cfg):
    g = TivitGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.hand = []
    for k in g.tokens:
        g.tokens[k] = 0
    g.tokens["Treasure"] = treasures
    g.tokens["Clue"] = clues
    g.board.append(Permanent(card=g.commander, sick=False))
    g.commander_cast = True
    for name in ("Deadeye Navigator",) + tuple(extra):
        g.board.append(Permanent(card=take(g, name), sick=False))
    # no payoff anywhere but where a case puts it
    g.library = [c for c in g.library if c.name not in TV.PILE_PAYOFFS]
    if top is not None:
        g.library.append(take_any(top))      # the END is the top
    g.turn = 5
    return g


_ALL = {c.name: c for c in DECK}


def take_any(name):
    return _ALL[name]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh(top="Mirkwood Bats")
    TV.deadeye_loop(g)
    check("A the dig finds Mirkwood Bats and the loop wins",
          (g.result, g.m["pile_dig_draws"] >= 1), ("win", True))

    g = fresh(extra=("Revel in Riches",), top="Mirkwood Bats")
    TV.deadeye_loop(g)
    check("B Revel in Riches and ten Treasures: no Clue cracked",
          g.m["pile_dig_draws"], 0)

    g = fresh(treasures=2, top="Mirkwood Bats")
    TV.deadeye_loop(g)
    check("C NEIGHBOUR: two Treasures, nothing to crack with",
          (g.m["pile_dig_draws"], g.result), (0, None))

    g = fresh(treasures=6, clues=3, top="Disciple of the Vault")
    TV.main_phase(g)
    check("D the main phase digs first, finds Disciple, the loop wins",
          (g.result, g.m["pile_dig_draws"] >= 1), ("win", True))

    g = fresh(treasures=30, clues=5)
    g.library = g.library[:1]
    TV.deadeye_loop(g)
    check("E a one-card library is never drawn out",
          len(g.library), 1)
    g = fresh(extra=("Disciple of the Vault",))
    TV.deadeye_loop(g)
    check("F Disciple out, mana-neutral: the capped loop wins, no dig",
          (g.result, g.m["capped_drain_wins"], g.m["pile_digs"]),
          ("win", 1, 0))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z218: the Clue dig\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_dig = TV.dig_the_pile

    def dig_no_guard(g):
        # the same function with Revel in Riches unseen by its guard
        has = g.has
        g.has = lambda n: False if n in ("Revel in Riches",
                                         "Mechanized Production") else has(n)
        try:
            real_dig(g)
        finally:
            g.has = has

    muts = {
        "pile_dig=False": ({"A", "D"}, {"pile_dig": False}, []),
        "the Revel / Mechanized guard removed": (
            {"B"}, {}, [(TV, "dig_the_pile", dig_no_guard)]),
        "the main-phase dig removed": (
            {"D"}, {}, [(TV, "dig_before_casting", lambda g: None)]),
        "capped_drain_wins=False": (
            {"D", "F"}, {"capped_drain_wins": False}, []),
        "the dig's draw_is_safe ignored": (
            {"E"}, {}, [(TV, "draw_is_safe", lambda g, n=1: True)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
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
