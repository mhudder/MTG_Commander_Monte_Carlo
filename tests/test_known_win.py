#!/usr/bin/env python3
"""The pod reacts to a win it can see coming (§0z62).

    python -m tests.test_known_win
    python -m tests.test_known_win --mutate   # 4 mutations, exact sets

Approach of the Second Sun, once it has resolved and gone seventh from the top,
is a win the whole table knows about. Lorehold sets `g.known_win` to its name;
`opponents.known_win_share` then floors your share of the pod's removal and
kills at `known_win_focus` (default 1.0), and `opponents.counter_threat`
treats a recast of that card as maximum threat.

CASES
  A  before Approach resolves: no known win
  B  Approach resolves from hand the first time: the win is known
  H  a Bombardment COPY resolving does not make it known (no card moved)
  C  known, focus 1.0, an empty board: your share is 1.0
  D  known, focus 0.5, an empty board: 0.5
  E  known, focus 0.5, a board whose own share is higher: the higher one --
     the focus is a FLOOR, not a cap
  F1 a threat-8 Approach against a 0.95 roll, win NOT known: not countered
  F2 the same, win known: countered (threat raised to the cap)
  G  NEIGHBOUR: another threat-8 spell against the same roll while the win
     is known: not countered -- the bump is for the known card only

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  known_win_share ignores the flag                  -> C, D
  the focus is a cap instead of a floor             -> E
  Approach does not make the win known              -> B
  counterspells ignore the known win                -> F2

UNMUTATED (§0z15): A and H are the absence cases; F1 and G are the
neighbours the counterspell bump must not reach.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
import edhmc.opponents as OPP
from edhmc.decks import lorehold_v16 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = LM.build()
APPROACH = next(c for c in DECK if c.name == "Approach of the Second Sun")
OTHER = EN.Card(name="Other Sorcery", types=frozenset({"Sorcery"}),
                cost={"gen": 7}, threat=8.0)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(**cfg):
    g = L.LoreholdGame(list(DECK), CMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"F{i}", types=frozenset({"Sorcery"}),
                         cost={"gen": 1}) for i in range(20)]
    g.turn = 8
    g.m["approach_casts"] = 0
    return g


def share(g):
    opp, others = g.opponents[0], g.opponents[1:]
    return round(OPP.your_share(g, opp, others), 4)


def countered(g, card):
    g.counter_rolls = [[[0.95] * len(g.opponents)
                        for _ in range(OPP.N_COUNTER_SLOTS)] for _ in range(40)]
    for o in g.opponents:
        o.counters_left = 1
        o._pcache = dict(o.p, counter=1.0)
    return OPP.countered(g, card, 0)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    g = game()
    check("A before Approach resolves: no known win", g.known_win, None)
    L.resolve_spell(g, APPROACH, 0, from_hand=True)
    check("B Approach resolved: the win is known",
          g.known_win, "Approach of the Second Sun")
    g = game()
    L.apply_spell_effects(g, APPROACH, is_copy=True)
    check("H a Bombardment copy does not make it known", g.known_win, None)
    g = game(known_win_focus=1.0)
    g.known_win = APPROACH.name
    check("C known, focus 1.0, empty board: share 1.0", share(g), 1.0)
    g = game(known_win_focus=0.5)
    g.known_win = APPROACH.name
    check("D known, focus 0.5, empty board: 0.5", share(g), 0.5)
    g = game(known_win_focus=0.5)
    big = EN.Card(name="Huge", types=frozenset({"Creature"}), power=500,
                  toughness=500)
    g.board.append(EN.Permanent(card=big, sick=False))
    g.known_win = APPROACH.name
    check("E focus is a floor: a bigger board share stays", share(g) > 0.5, True)
    g = game()
    check("F1 threat-8 Approach, roll 0.95, win unknown: not countered",
          countered(g, APPROACH), False)
    g = game()
    g.known_win = APPROACH.name
    check("F2 the same with the win known: countered", countered(g, APPROACH), True)
    g = game()
    g.known_win = APPROACH.name
    check("G another threat-8 spell, win known: not countered",
          countered(g, OTHER), False)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The pod reacts to a known win\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {"known_win_share": OPP.known_win_share,
            "counter_threat": OPP.counter_threat,
            "approach_resolves": L.approach_resolves}

    def as_cap(g, s):
        if getattr(g, "known_win", None):
            return g.cfg.get("known_win_focus", 1.0)
        return s

    def approach_silent(g, card, is_copy, was_cast, from_hand):
        real["approach_resolves"](g, card, is_copy, was_cast, from_hand)
        g.known_win = None

    def threat_blind(g, card):
        return (float(card.threat) if card.threat
                else max(card.power * 0.8, card.mv * 0.5))

    muts = {
        "known_win_share ignores the flag":
            ({"C", "D"}, OPP, "known_win_share", lambda g, s: s),
        "the focus is a cap instead of a floor":
            ({"E"}, OPP, "known_win_share", as_cap),
        "Approach does not make the win known":
            ({"B"}, L, "approach_resolves", approach_silent),
        "counterspells ignore the known win":
            ({"F2"}, OPP, "counter_threat", threat_blind),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
