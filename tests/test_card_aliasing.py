#!/usr/bin/env python3
"""One Card object per copy (§0z112).

    python -m tests.test_card_aliasing
    python -m tests.test_card_aliasing --mutate   # 1 mutation, exact set

Every deck module built its basics as `[L("Forest", "G")] * n` -- n references
to ONE Card -- and every rule that compares cards by identity then read two
copies as one card. The land ablation's NOOP arm found it: a basic replaced by
a field-identical copy changed 54 rendmaw games and 7 trostani games in
15,000.

CASES
  A  every deck as built (`build_pending`) holds one object per card
  B  NEIGHBOUR: `pending.validate` refuses a list with an aliased basic
  C  Shigeki reveals two copies of Forest among four: ONE goes onto the
     battlefield, the other to the graveyard ("You may put A land card")
  D  trostani's hideaway with four Forests on top: one is exiled, the other
     three go to the bottom -- the library is one card shorter, not four

MUTATION, WRITTEN BEFORE THE RUN, exact set:
  copies of a basic share one object (the old modules)   -> A, C, D

UNMUTATED (§0z15): B checks the check, which does not depend on how a deck
was built.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.trostani as T
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import trostani_v1 as TM
from edhmc.engine import Board
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import BASICS, build_pending, validate
from edhmc.registry import DECKS

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
ALIAS = False
RDECK, RCMD = RM.build()
TDECK, TCMD = TM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def copies(make, n):
    """n copies of a card -- one object each, or (the mutation) one object."""
    if ALIAS:
        return [make()] * n
    return [make() for _ in range(n)]


def realias(deck):
    first = {}
    return [first.setdefault(c.name, c) if c.name in BASICS else c
            for c in deck]


def forest():
    return EN.Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({"G"}))


def body(name):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=2,
                   toughness=2, cost={"gen": 2})


def run_cases():
    PASS.clear()
    FAIL.clear()

    bad = []
    for d in DECKS:
        deck, _ = build_pending(d)
        if ALIAS:
            deck = realias(deck)
        if len({id(c) for c in deck}) != len(deck):
            bad.append(d)
    check("A every built list holds one object per card", bad, [])

    deck, cmd = build_pending("azusa")
    try:
        validate(realias(deck), cmd)
        raised = False
    except AssertionError:
        raised = True
    check("B NEIGHBOUR: validate refuses an aliased list", raised, True)

    shig = next(c for c in RDECK if c.name == "Shigeki, Jukai Visionary")
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG), random.Random(1),
                seed_for_pod=1)
    g.board, g.hand, g.graveyard = EN.Board(), [], []
    g.turn = 6
    g.board.append(EN.Permanent(card=shig, sick=False))
    for col in ("G", "G"):
        g.board.append(EN.Permanent(card=EN.Card(
            name=f"Land {col}", types=frozenset({"Land"}), is_land=True,
            produces=frozenset({col})), sick=False))
    g.library = ([body(f"L{i}") for i in range(20)] + [body("x1")]
                 + copies(forest, 2) + [body("x2")])
    EN.shigeki(g)
    check("C Shigeki puts ONE of two revealed Forests onto the battlefield",
          (sum(p.card.name == "Forest" for p in g.board),
           sum(c.name == "Forest" for c in g.graveyard)), (1, 1))

    g = T.TrostaniGame(list(TDECK), TCMD, dict(DEFAULT_CFG, turns=20), 1)
    g.board, g.hand, g.graveyard = Board(), [], []
    g.library = [body(f"L{i}") for i in range(10)] + copies(forest, 4)
    before = len(g.library)
    g.hideaway_etb(EN.Permanent(card=forest(), sick=False))
    check("D hideaway over four Forests exiles one and keeps three",
          before - len(g.library), 1)
    return set(FAIL)


def main() -> int:
    global ALIAS
    if not MUTATE:
        print("One Card object per copy (§0z112)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact set\n")
    want = {"A", "C", "D"}
    ALIAS = True
    try:
        broke = run_cases()
    finally:
        ALIAS = False
    ok = broke == want
    print(f"   broke {sorted(broke) or 'nothing'}  expected {sorted(want)}  "
          f"{'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{int(ok)} passed, {int(not ok)} failed (1 mutation, exact set)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
