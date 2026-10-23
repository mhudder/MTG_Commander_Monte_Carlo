#!/usr/bin/env python3
"""An `id(permanent)` used as a key must not outlive its permanent (§0z98).

    python -m tests.test_id_reuse
    python -m tests.test_id_reuse --mutate   # 4 mutations, exact sets

CPython hands a freed object's id to the next object of the same size, so
state keyed on `id(perm)` that is not cleared when the permanent leaves is
inherited by whatever permanent is allocated next -- and WHICH one depends on
the process's allocation history. The same seed then plays differently in two
processes: one trostani game in 15,000 did, found by
`diagnostics/run_groups.py`'s reproduction check. The fix holds the permanent
for as long as its id is a key -- and since §0z100 the engine holds EVERY
Card and Permanent made during a game (`engine.begin_game`), so any id key is
safe, including ones not written yet. The local holds below stay as defence
in depth, and the mutations prove each one on its own.

CASES
  A  trostani: a permanent that left the battlefield is still alive (its
     own `held` list), so its id cannot be handed on
  B  engine.walker_ready: a walker it marked is still alive after every
     other reference is dropped, and a NEW walker that turn may activate
  C  azusa's `pw_used` holds the walker it marks (the same rule, per-turn)
  D  NEIGHBOUR: the same seeds played twice in one process, with 5,000
     permanents allocated and freed in between, give identical outputs on
     every deck -- 20 seeds each at T20
  E  the CENTRAL hold: a Permanent made after `begin_game()` is still alive
     after every reference to it is dropped
  F  the same for a Card
  G  azusa's land animation holds the lands it targets (§0z158)
  A, B, E, F and G ask "is it alive" by weak reference, not "was its id
  reused": reuse is the allocator's choice, and a case that waits for it
  passed once with the hold switched off.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the central hold is off                            -> E, F
  ... and trostani holds nothing                     -> A, E, F
  ... and walker_ready keeps a bare id               -> B, E, F
  ... and azusa's animations keep bare ids           -> E, F, G   (D not run)
  (A, B and G pass with the central hold off: their local holds still work.)

UNMUTATED (§0z15): C is structural and D is the neighbour; D cannot be made to
fail on demand, since whether an id is reused inside a game depends on the
allocator, which is the whole problem.

D WAS FLAKY UNDER THE FIRST MUTATION (§0z158): about one run in six it broke
too, on azusa. That was D doing its job -- azusa's `animate_lands` kept its
targets as a bare set of ids, held by nothing but the central hold, so with
the hold off a dead animated land's id could go to a new permanent. The
targets hold their permanents now, G pins it, and the fourth mutation is
the one that takes that hold away. D's expectation (it passes) was not
widened; the engine was fixed so that the expectation is true: 20 runs of
the first three mutations, D held every time.

UNDER THE FOURTH, D IS NOT RUN. That mutation puts the bare ids back, and D
broke in 4 of 20 runs of it -- the original flake, on demand, which is the
evidence the diagnosis is right. Its outcome there is the allocator's
choice by construction, so asserting either result would be a coin flip
written down as a test. It is not asked; E, F and G are.
"""
import gc
import sys
import weakref

import edhmc.engine as EN
import edhmc.trostani as T
from edhmc.azusa import AzusaGame, PLANESWALKERS
from edhmc.decks import azusa_v1, trostani_v1
from edhmc.engine import Board, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def trostani_game():
    deck, cmd = trostani_v1.build()
    g = T.TrostaniGame(list(deck), cmd, dict(DEFAULT_CFG, turns=20), 1)
    g.board, g.hand, g.graveyard = Board(), [], []
    return g, {c.name: c for c in deck}


def run_cases(neighbour=True):
    PASS.clear()
    FAIL.clear()

    # HELD, CHECKED BY WEAK REFERENCE. Whether a freed id is actually REUSED
    # is up to the allocator, so a case that waits for reuse is itself
    # non-deterministic -- the first version of E passed with the hold off.
    # What the fix promises is that the object is still ALIVE while its id is
    # a key, and a weak reference answers that exactly.
    g, by = trostani_game()
    p = g.make_permanent(by["Phyrexian Processor"])
    ref = weakref.ref(p)
    g.board.remove(p)
    del p
    gc.collect()
    check("A trostani still holds a permanent that left the battlefield",
          ref() is not None, True)

    g, by = trostani_game()
    walker = by["Elspeth, Sun's Champion"]
    first = Permanent(card=walker)
    EN.walker_ready(g, first)
    ref = weakref.ref(first)
    del first
    gc.collect()
    nxt = Permanent(card=walker)
    check("B walker_ready holds the walker it marked; a new one may activate",
          (ref() is not None, EN.walker_ready(g, nxt)), (True, True))

    deck, cmd = azusa_v1.build()
    a = AzusaGame(list(deck), cmd, dict(DEFAULT_CFG, turns=20), 1)
    a.board = Board()
    # The module list holds no walker today (Nissa, Worldwaker was cut), so
    # one is built: the rule is the engine's, not the card's.
    name = EN.Card(name="Nissa, Worldwaker", types=frozenset({"Planeswalker"}),
                   cost={"gen": 3, "G": 1})
    assert name.name in PLANESWALKERS
    w = Permanent(card=name, counters=5)
    a.board.append(w)
    a.planeswalker_step()
    check("C azusa's pw_used holds the walker it marks",
          a.pw_used.get(id(w)) is w, True)

    bad = []
    for deck_name in (DECKS if neighbour else ()):
        cards, cmd = build_pending(deck_name)
        sim = DECKS[deck_name].sim
        cfg = dict(DEFAULT_CFG, turns=20)
        first = [dict(sim(list(cards), cmd, cfg, s)) for s in range(5000, 5020)]
        junk = [Permanent(card=cards[0]) for _ in range(5000)]
        del junk
        second = [dict(sim(list(cards), cmd, cfg, s))
                  for s in reversed(range(5000, 5020))][::-1]
        if first != second:
            bad.append(deck_name)
    if neighbour:
        check("D every deck replays identically after other allocations",
              bad, [])
    cards, cmd = build_pending(list(DECKS)[-1])   # E's card, as before

    card = cards[0]
    EN.begin_game()
    p = Permanent(card=card)
    ref = weakref.ref(p)
    del p
    gc.collect()
    check("E the engine holds a freed Permanent until the next game",
          ref() is not None, True)

    EN.begin_game()
    c = EN.Card(name="(probe)", types=frozenset({"Sorcery"}), cost={})
    ref = weakref.ref(c)
    del c
    gc.collect()
    check("F the engine holds a freed Card until the next game",
          ref() is not None, True)

    deck, cmd = azusa_v1.build()
    a = AzusaGame(list(deck), cmd, dict(DEFAULT_CFG, turns=20), 1)
    a.board = Board()
    forest = next(c for c in deck if c.is_land)
    land = Permanent(card=forest)
    a.board.append(land)
    a.animate_lands(2, 2, targets=[land])
    ref = weakref.ref(land)
    a.board.remove(land)
    del land
    gc.collect()
    check("G azusa's animation holds the lands it targets",
          ref() is not None, True)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("id(permanent) keys do not outlive their permanent (§0z98)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_make = T.TrostaniGame.make_permanent

    def make_unheld(self, *a, **k):
        perm = real_make(self, *a, **k)
        self.held.remove(perm)
        return perm

    def bare_ready(g, perm):
        used = g.__dict__.setdefault("pw_activated_turn", {})
        if used.get(id(perm)) == g.turn:
            return False
        used[id(perm)] = g.turn
        return True

    def no_hold(self):
        pass

    real_animate = AzusaGame.animate_lands

    def animate_bare(self, *a, **k):
        real_animate(self, *a, **k)
        if self.animations:
            last = self.animations[-1]
            last["targets"] = {i: None for i in last["targets"]}

    central = [(EN.Permanent, "__post_init__", no_hold),
               (EN.Card, "__post_init__", no_hold)]
    muts = {
        "the central hold is off": ({"E", "F"}, central),
        "... and trostani holds nothing": (
            {"A", "E", "F"},
            central + [(T.TrostaniGame, "make_permanent", make_unheld)]),
        "... and walker_ready keeps a bare id": (
            {"B", "E", "F"}, central + [(EN, "walker_ready", bare_ready)]),
        "... and azusa's animations keep bare ids": (
            {"E", "F", "G"},
            central + [(AzusaGame, "animate_lands", animate_bare)]),
    }
    # The one mutation under which D's result is the allocator's (docstring).
    no_neighbour = {"... and azusa's animations keep bare ids"}
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")
        saved = [(o, n, getattr(o, n)) for o, n, _ in patches]
        for o, n, fn in patches:
            setattr(o, n, fn)
        try:
            broke = run_cases(neighbour=label not in no_neighbour)
        finally:
            for o, n, real in saved:
                setattr(o, n, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
