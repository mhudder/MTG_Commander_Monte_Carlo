#!/usr/bin/env python3
"""March of the World Ooze's Elephant trigger (§0z47, queued item 4).

    python -m tests.test_march_elephant
    python -m tests.test_march_elephant --mutate   # 4 mutations, exact sets

    {3}{G}{G}{G} Enchantment  (Scryfall, verified 2026-09-25)
    Creatures you control have base power and toughness 6/6 and are Oozes in
    addition to their other types.
    Whenever an opponent casts a spell, if it's not their turn, you create a
    3/3 green Elephant creature token.

HOW IT IS WIRED. The only opponent spell this model puts on YOUR turn is a
counterspell, and it is cast inside `opponents.countered`. That function now
calls `g.opponent_cast_on_your_turn(i)` when an engine defines it -- the
optional-behaviour protocol in docs/ARCHITECTURE.md -- and only rendmaw's
`Game` does, which runs `engine.march_elephant`. The token goes through
`make_tokens`, the one token path, so the doublers apply to it.

CASES
  A  March out, an opponent counters: one Elephant, and it is 6/6
  B  no March, an opponent counters: no Elephant
  C  March out, nobody counters: no Elephant
  D  March and Primal Vigor out, an opponent counters: two Elephants
  E  the hook is defined on rendmaw's Game and on NO other engine's game
     class, nor on BaseGame -- an engine that grew one would fire on every
     counterspell in its games
  F  NEIGHBOUR: the counter still counts -- `countered` returns True and
     the opponent spends one of its counterspells
  G  ARASTA OF THE ENDLESS WEB, the same event's other reader in this deck:
     "Whenever an opponent casts an instant or sorcery spell, create a 1/2
     green Spider creature token with reach." A counterspell is an instant,
     so it makes a Spider. Before §0z47 Arasta read only its per-round
     `opp_instant_rate` roll and a counterspell made nothing -- the rule
     written twice (§0u), found while writing the first.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  march_elephant does nothing                    -> A, D
  the Elephant is made without March on board    -> B
  the Elephant bypasses make_tokens              -> D
  arasta_spider does nothing                     -> G

UNMUTATED, and written down (§0z15): C is guarded by `countered`'s own roll,
which this change did not touch; E is a census of classes; F is the
neighbour whose return value the hook must not change.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as M
from edhmc.experiment import DEFAULT_CFG
from edhmc.registry import DECKS as REGISTRY

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

DECK, CMD = M.build()
MARCH = next(c for c in DECK if c.name == "March of the World Ooze")
VIGOR = next(c for c in DECK if c.name == "Primal Vigor")
ARASTA = next(c for c in DECK if c.name == "Arasta of the Endless Web")
SPELL = EN.Card(name="Big Spell", types=frozenset({"Sorcery"}),
                cost={"gen": 6}, threat=9.0)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(*cards, counter=True):
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, turns=20),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    g.turn = 8
    roll = 0.0 if counter else 1.0      # p is forced to 1.0; `rolls[i] < p`
    g.counter_rolls = [[[roll] * len(g.opponents)
                        for _ in range(OPP.N_COUNTER_SLOTS)]
                       for _ in range(40)]
    for o in g.opponents:
        o.counters_left = 1
        o._pcache = dict(o.p, counter=1.0)
    return g


def elephants(g):
    return [p for p in g.board if p.card.name == "Elephant token"]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    g = game(MARCH)
    OPP.countered(g, SPELL, 0)
    e = elephants(g)
    check("A March out, a counter: one 6/6 Elephant",
          (len(e), [(g.power_of(p), g.toughness_of(p)) for p in e],
           g.m["march_elephants"]), (1, [(6, 6)], 1))
    g = game()
    OPP.countered(g, SPELL, 0)
    check("B no March: no Elephant", len(elephants(g)), 0)
    g = game(MARCH, counter=False)
    OPP.countered(g, SPELL, 0)
    check("C nobody counters: no Elephant", len(elephants(g)), 0)
    g = game(MARCH, VIGOR)
    OPP.countered(g, SPELL, 0)
    check("D March + Primal Vigor: two Elephants", len(elephants(g)), 2)
    holders = sorted({spec.sim.__module__ for spec in REGISTRY.values()})
    classes = [v for mod in holders for v in vars(sys.modules[mod]).values()
               if isinstance(v, type) and issubclass(v, EN.BaseGame)]
    check("E only rendmaw's Game defines the hook",
          sorted(c.__module__ + "." + c.__name__ for c in classes
                 if hasattr(c, "opponent_cast_on_your_turn")),
          ["edhmc.engine.Game"])
    g = game(MARCH)
    left = sum(o.counters_left for o in g.opponents)
    got = OPP.countered(g, SPELL, 0)
    check("F the counter still counts",
          (got, left - sum(o.counters_left for o in g.opponents)), (True, 1))
    g = game(ARASTA)
    OPP.countered(g, SPELL, 0)
    check("G Arasta out, a counter: one Spider",
          sum(1 for p in g.board if p.card.name == "Spider token"), 1)
    return set(FAIL)


def direct_elephant(g):
    """The mutation: the same token, appended by hand."""
    if not g.has("March of the World Ooze"):
        return
    card = EN.Card(name="Elephant token", types=frozenset({"Creature"}),
                   power=3, toughness=3)
    g.board.append(EN.Permanent(card=card, sick=True, is_token=True,
                                base_p=3, base_t=3))
    g.m["march_elephants"] += 1


def main() -> int:
    if not MUTATE:
        print("March of the World Ooze -- the Elephant trigger\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = EN.march_elephant
    real_arasta = EN.arasta_spider
    expected = {
        "march_elephant does nothing": {"A", "D"},
        "the Elephant is made without March on board": {"B"},
        "the Elephant bypasses make_tokens": {"D"},
        "arasta_spider does nothing": {"G"},
    }
    muts = {
        "march_elephant does nothing": lambda g: None,
        "the Elephant is made without March on board":
            lambda g: (g.make_tokens(1, 3, 3, "Elephant"),
                       g.m.__setitem__("march_elephants",
                                       g.m["march_elephants"] + 1)),
        "the Elephant bypasses make_tokens": direct_elephant,
        "arasta_spider does nothing": None,
    }
    bad = 0
    for label, fn in muts.items():
        print(f"-- {label}")
        if fn is None:
            EN.arasta_spider = lambda g: None
        else:
            EN.march_elephant = fn
        try:
            broke = run_cases()
        finally:
            EN.march_elephant = real
            EN.arasta_spider = real_arasta
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
