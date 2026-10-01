#!/usr/bin/env python3
"""An `id(permanent)` used as a key must not outlive its permanent (§0z98).

    python -m tests.test_id_reuse
    python -m tests.test_id_reuse --mutate   # 2 mutations, exact sets

CPython hands a freed object's id to the next object of the same size, so
state keyed on `id(perm)` that is not cleared when the permanent leaves is
inherited by whatever permanent is allocated next -- and WHICH one depends on
the process's allocation history. The same seed then plays differently in two
processes: one trostani game in 15,000 did, found by
`diagnostics/run_groups.py`'s reproduction check. The fix holds the permanent
for as long as its id is a key.

CASES
  A  trostani: a permanent made and then removed is still held, and none of
     200 permanents made after it shares its id
  B  engine.walker_ready: a walker activated this turn, removed, and freed;
     a NEW walker made afterwards in the same turn may still activate
  C  azusa's `pw_used` holds the walker it marks (the same rule, per-turn)
  D  NEIGHBOUR: the same seeds played twice in one process, with 5,000
     permanents allocated and freed in between, give identical outputs on
     every deck -- 20 seeds each at T20

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  trostani holds nothing (`held.append` is a no-op)  -> A
  walker_ready keeps a bare id again                -> B

UNMUTATED (§0z15): C is structural and D is the neighbour; D cannot be made to
fail on demand, since whether an id is reused inside a game depends on the
allocator, which is the whole problem.
"""
import gc
import sys

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


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, by = trostani_game()
    p = g.make_permanent(by["Phyrexian Processor"])
    old = id(p)
    g.board.remove(p)
    del p
    gc.collect()
    fresh = [g.make_permanent(by["Sol Ring"]) for _ in range(200)]
    check("A a removed permanent's id is never reused in the game",
          any(id(q) == old for q in fresh), False)

    g, by = trostani_game()
    walker = by["Elspeth, Sun's Champion"]
    first = Permanent(card=walker)
    EN.walker_ready(g, first)
    old = id(first)
    del first
    gc.collect()
    ready, reused = True, False
    for _ in range(200):
        nxt = Permanent(card=walker)
        reused |= id(nxt) == old
        ready &= EN.walker_ready(g, nxt)
    check("B a new walker in the same turn may activate", ready, True)

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
    for deck_name in DECKS:
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
    check("D every deck replays identically after other allocations", bad, [])
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

    muts = {
        "trostani holds nothing": ({"A"}, (T.TrostaniGame, "make_permanent",
                                           make_unheld)),
        "walker_ready keeps a bare id": ({"B"}, (EN, "walker_ready",
                                                 bare_ready)),
    }
    bad = 0
    for label, (want, (owner, name, fn)) in muts.items():
        print(f"-- {label}")
        real = getattr(owner, name)
        setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
