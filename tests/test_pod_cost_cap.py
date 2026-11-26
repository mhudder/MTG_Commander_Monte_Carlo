#!/usr/bin/env python3
"""§0z264: an arriving body's charged cost is capped at its opponent's
sources this turn (`pod_body_mv_cap`); §0z265: the board grows at
`pod_growth_rate` (`opponents.growth_rate`).

    python -m tests.test_pod_cost_cap
    python -m tests.test_pod_cost_cap --mutate   # 4 mutations, exact sets

A body's mana value is rolled 1..4 at the pool whatever the turn, so on the
pod's turns 1-3 most arrivals cost more than every source the opponent has
(`diagnostics.diag_pod_mana_budget`). Capped, a turn-1 body costs 1.

CASES -- one opponent, its pool one body of mana value 3, arriving now
  A  the cap on, one source this turn: the body is charged 1
  B  the cap on, five sources: charged its own 3
  C  NEIGHBOUR: pod_body_mv_cap=False, one source: charged 3
  D  the cap on, no source at all: charged 1, never 0
  E  `grow_board` at pod_growth_rate 1.0 adds 1.0 x `board`, not 0.7 x
  G  reading the cap changes nothing: the bodies list, `next_body` and the
     mana-creature counter are as they were (§0z265: the first cut called
     `mana_creature_mana`, which reconciles the pool and counts)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the cap's switch never read (always off)      -> A, D
  the cap without its floor of 1                -> D
  growth_rate always 0.7                        -> E
  the cap reads mana_creature_mana (the first cut) -> G

UNMUTATED (§0z15): B is the cap's no-op side, C its switch's neighbour.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(sources, **cfg):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "pod_mana": True, "pod_mana_creatures": False,
                 **EXTRA_CFG, **cfg},
                random.Random(1), seed_for_pod=1)
    g.turn = 3
    o = g.opponents[0]
    o.mana_rows = tuple(O.PodMana(sources, 0, sources, sources)
                        for _ in range(30))
    o.body_pool = (O.PodBody(3, 3),)
    o.bodies, o.next_body = [], 0
    o.creatures = 1.0
    return g, o


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game(1.0)
    check("A capped at one source: charged 1", O._arrival_mvs(g, o, 0.0),
          [1.0])
    g, o = game(5.0)
    check("B five sources: its own 3", O._arrival_mvs(g, o, 0.0), [3.0])
    g, o = game(1.0, pod_body_mv_cap=False)
    check("C the cap off: 3", O._arrival_mvs(g, o, 0.0), [3.0])
    g, o = game(0.0)
    check("D no source: 1, never 0", O._arrival_mvs(g, o, 0.0), [1.0])

    g, o = game(5.0, pod_growth_rate=1.0)
    o.creatures = 0.0
    O.grow_board(g, o)
    check("E growth at rate 1.0", round(o.creatures, 6),
          round(min(7.0, 1.0 * o.p["board"]), 6))
    g, o = game(5.0, pod_mana_creatures=True)
    o.body_pool = tuple(O.PodBody(2, 2, mana=True) for _ in range(6))
    o.creatures = 3.0
    before = (list(o.bodies), o.next_body, g.m["pod_mana_creature_mana"])
    O._arrival_mvs(g, o, 1.0)
    check("G reading the cap changes nothing",
          (list(o.bodies), o.next_body, g.m["pod_mana_creature_mana"]),
          before)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z264-§0z265: the cost cap and the growth rate\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_rate = O.growth_rate

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_rate(v):
        O.growth_rate = v

    real_arrivals = O._arrival_mvs

    def no_floor(g, o, before):
        # the cap at the sources, with no floor of 1: below one source the
        # capped cost is the sources themselves
        out = real_arrivals(g, o, before)
        row = O.pod_mana_row(g, o)
        src = row.sources if row is not None else 0.0
        if O.pod_knob(g.cfg, "pod_body_mv_cap") and src < 1.0:
            return [min(mv, src) for mv in out]
        return out

    def set_arrivals(v):
        O._arrival_mvs = v

    def first_cut(g, o, before):
        # the first cut's side effect, put back: it read the sources
        # through `mana_creature_mana`
        if O.pod_knob(g.cfg, "pod_body_mv_cap"):
            O.mana_creature_mana(g, o)
        return real_arrivals(g, o, before)

    muts = {
        "the cap's switch never read": (
            {"A", "D"}, set_cfg, {"pod_body_mv_cap": False}, {}),
        "the cap without its floor of 1": (
            {"D"}, set_arrivals, no_floor, real_arrivals),
        "growth_rate always 0.7": (
            {"E"}, set_rate, lambda g: 0.7, real_rate),
        "the cap reads mana_creature_mana": (
            {"G"}, set_arrivals, first_cut, real_arrivals),
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
