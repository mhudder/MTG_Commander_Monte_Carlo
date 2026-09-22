#!/usr/bin/env python3
"""Queued item 18 -- the one-card cast lookahead, `engine.lookahead_pick`.

    python -m tests.test_cast_lookahead
    python -m tests.test_cast_lookahead --mutate   # 4 mutations, exact sets

WHAT IT DOES. Every engine's `main_phase` casts `max(options, key=rank)`. With
`cast_lookahead=True`, before the greedy pick G is cast it asks, of each
other affordable option O: is O stranded once G is paid, and is G still
affordable once O is paid? Then O first casts both, and greedy casts one. It
never drops G -- it reorders.

THE CASE THAT MOTIVATES THE TEST, found by probing `can_pay` rather than
assumed: a Plains and a colourless rock. `can_pay` breaks the generic tie on
`tap_reluctance`, lands before rocks, so {1} taps the PLAINS -- and a {W}
card in hand is stranded that casting first would have kept. That is a real
shape (every deck taps lands before rocks), and it is the ONLY shape the
lookahead can fix: §0z8's own Voice/Lurrus case could not cast both cards
from the mana on the table, so it is a question about `priority`, not about
order. The docstring on `lookahead_pick` says so.

CASES
  A  pool_after: paying ONE unit of a two-unit source removes BOTH
  B  pool_after: an ownerless unit (a Treasure) goes alone
  C  knob off: the greedy pick, even with a rescue available
  D  knob on: the rescue is cast first, and counted
  E  knob on: no rescue when O-first would strand G instead
  F  knob on: no rescue when greedy already casts both
  G  knob on: of two rescues, the higher-ranked
  H  end to end, rendmaw's main_phase with `mana_surplus=False`: one card
     cast with the knob off, both with it on (with the surplus rule ON the
     engine does not strand this hand at all -- see the case)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pool_after forgets the tapped source's other units   -> A
  the lookahead ignores its knob (always on)           -> C, H
  the rescue test drops "G still affordable after O"   -> E
  of several rescues, the LOWEST-ranked is taken       -> G

WHAT HAS NO MUTATION (§0z15). The wiring into the other five engines is
checked by the measurement (a nonzero `lookahead_reorders` per deck), not
here; B is a regression case for Treasure-shaped pools.
"""
import random
import sys

import edhmc.engine as EN
from edhmc.decks import rendmaw_v12 as RM
from edhmc.engine import Card, ManaUnits, Permanent
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
W, B, C = frozenset({"W"}), frozenset({"B"}), frozenset({"C"})


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


class Src:
    """An owner: pool_after only needs identity."""


class G:
    """Just enough game for lookahead_pick: a cfg and a metrics dict."""
    def __init__(self, on):
        self.cfg = {"cast_lookahead": on}
        self.m = EN.Metrics({})


def card(name, cost, prio):
    return Card(name=name, types=frozenset({"Artifact"}), cost=cost,
                priority=prio)


def pick(on, units, *cards):
    """options the way the engines build them: (card, pay) with the cost
    looked up by identity."""
    opts = []
    for c in cards:
        pay = EN.can_pay(c.cost, units)
        if pay is not None:
            opts.append((c, pay))
    g = G(on)
    got = EN.lookahead_pick(g, opts, units,
                            lambda it: (it[0].priority, it[0].mv),
                            cost_of=lambda it: it[0].cost,
                            pay_of=lambda it: it[1])
    return got[0].name, g.m["lookahead_reorders"]


def plains_and_rock():
    return ManaUnits([W, C], [Src(), Src()], [(0, 0, 0), (5, 0, 0)])


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A / B: the prediction ------------------------------------------
    ring = Src()
    u = ManaUnits([C, C, B], [ring, ring, Src()])
    check("A paying one Sol Ring unit taps both",
          list(EN.pool_after(u, [0])), [B])
    u = ManaUnits([W, B], [Src(), Src()]) + [frozenset({"W", "B"})]
    check("B an ownerless unit goes alone",
          list(EN.pool_after(u, [2])), [W, B])

    generic = card("generic one", {"gen": 1}, 9)
    white = card("white one", {"W": 1}, 5)

    # ---- C / D: the motivating case, knob off and on --------------------
    check("C knob off: greedy, rescue or not",
          pick(False, plains_and_rock(), generic, white), ("generic one", 0))
    check("D knob on: the stranded {W} card is cast first",
          pick(True, plains_and_rock(), generic, white), ("white one", 1))

    # ---- E: O first would strand G -- no rescue --------------------------
    u = ManaUnits([W], [Src()])
    check("E one Plains, {W} p9 and {W} p5: greedy",
          pick(True, u, card("white nine", {"W": 1}, 9), white),
          ("white nine", 0))

    # ---- F: nothing is stranded -----------------------------------------
    u = ManaUnits([W, W], [Src(), Src()])
    check("F two Plains: greedy casts both, no reorder",
          pick(True, u, generic, white), ("generic one", 0))

    # ---- G: two rescues, the higher-ranked -------------------------------
    white7 = card("white seven", {"W": 1}, 7)
    check("G of two rescues, the higher-ranked",
          pick(True, plains_and_rock(), generic, white, white7),
          ("white seven", 1))

    # ---- H: end to end through rendmaw's main_phase ---------------------
    got = []
    for on in (False, True):
        deck, cmd = RM.build()
        # mana_surplus=False, deliberately: with §0z8's SURPLUS rule on,
        # `available_mana` already reads the hand and keeps the Plains for
        # the {W} card, so the live engine does not strand it and there is
        # nothing to rescue -- which is itself the finding, and is measured
        # rather than asserted here. This case pins the WIRING.
        g = EN.Game(deck, cmd, dict(DEFAULT_CFG, turns=20,
                                    cast_lookahead=on, mana_surplus=False),
                    random.Random(3), 1234)
        g.commander_cast = True
        g.board = EN.Board()
        plains = Card(name="Plains", types=frozenset({"Land"}),
                      is_land=True, produces=W)
        rock = Card(name="Test Rock", types=frozenset({"Artifact"}),
                    mana_ability=(1, C))
        g.board.append(Permanent(card=plains, sick=False))
        g.board.append(Permanent(card=rock, sick=False))
        g.hand = [card("generic one", {"gen": 1}, 9),
                  card("white one", {"W": 1}, 5)]
        EN.main_phase(g)
        got.append(sorted(c.name for c in g.hand))
    check("H rendmaw main_phase: off strands the {W} card, on casts both",
          got, [["white one"], []])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("the one-card cast lookahead (queued item 18)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_after = EN.pool_after
    real_pick = EN.lookahead_pick
    expected = {
        "pool_after forgets the tapped source's other units": {"A"},
        "the lookahead ignores its knob (always on)": {"C", "H"},
        "the rescue test drops 'G still affordable after O'": {"E"},
        "of several rescues, the LOWEST-ranked is taken": {"G"},
    }

    def variant(ignore_knob=False, no_second=False, lowest=False):
        # A copy of lookahead_pick with ONE rule changed; everything else is
        # the real function's logic, so each mutation reports on one rule.
        def f(g, options, units, rank, cost_of, pay_of):
            best = max(options, key=rank)
            on = True if ignore_knob else g.cfg.get("cast_lookahead", False)
            if not on or len(options) < 2:
                return best
            after_best = EN.pool_after(units, pay_of(best))
            rescues = []
            for it in options:
                if it is best or it[0] is best[0]:
                    continue
                if EN.can_pay(cost_of(it), after_best) is not None:
                    continue
                if no_second or EN.can_pay(
                        cost_of(best),
                        EN.pool_after(units, pay_of(it))) is not None:
                    rescues.append(it)
            if not rescues:
                return best
            g.m["lookahead_reorders"] += 1
            return (min if lowest else max)(rescues, key=rank)
        return f

    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label.startswith("pool_after"):
            def forgetful(units, pay_idx):
                paid = set(pay_idx)
                keep = [i for i in range(len(units)) if i not in paid]
                return ManaUnits([units[i] for i in keep],
                                 [units.owners[i] for i in keep])
            EN.pool_after = forgetful
        elif label.startswith("the lookahead ignores"):
            EN.lookahead_pick = variant(ignore_knob=True)
        elif label.startswith("the rescue test"):
            EN.lookahead_pick = variant(no_second=True)
        else:
            EN.lookahead_pick = variant(lowest=True)
        try:
            broke = run_cases()
        finally:
            EN.pool_after = real_after
            EN.lookahead_pick = real_pick
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
