#!/usr/bin/env python3
"""§0z226: cycling and landcycling, one rule (`engine.cycle_step`).

    python -m tests.test_cycling
    python -m tests.test_cycling --mutate   # 3 mutations, exact sets

Karlov cases drive `cycle_step` with karlov's own `pay_cost` on a battlefield
of untapped Swamps and Plains set by hand; shilgengar cases with its
`pay`. The cards and costs are `_evasion.CYCLING` (generated).

CASES
  A  karlov, Barren Moor in hand, six lands out: it is cycled ({B}) -- to
     the graveyard, a card drawn
  B  the same with five lands out: kept (`cycle_land_floor` 6)
  C  six lands but a one-card library: kept (the draw is not safe)
  D  shilgengar, Angel of the Ruins in hand and no land, three lands out
     (3 + 1 < 7): plainscycled for {2} -- a Plains CARD to hand, and the
     one with the most land types (Godless Shrine over a basic Plains; the
     first run expected the basic, which the rule does not fetch -- the
     expectation corrected, said so), the Angel to the graveyard
  E  the same with a land in hand: kept
  F  NEIGHBOUR: `cycling` False, A's setup: kept

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  cycling=False                  -> A, D
  cycle_land_floor=0             -> B
  the draw is always safe        -> C

UNMUTATED (§0z15): E and F keep the card under every rule here.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as KV
import edhmc.shilgengar as SH
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(zone, name):
    c = next(x for x in zone if x.name == name)
    EN.remove_card(zone, c)
    return c


def lands_out(g, names):
    for n in names:
        g.board.append(EN.Permanent(card=take(g.library, n), sick=False))


def karlov(n_lands, library=None):
    deck, cmd = KM.build()
    g = KV.KarlovGame(list(deck), cmd, dict(DEFAULT_CFG, **EXTRA_CFG), 1)
    g.board = EN.Board()
    g.hand = [take(g.library, "Barren Moor")]
    lands_out(g, ["Swamp"] * min(n_lands, 4) + ["Plains"] * max(0, n_lands - 4))
    if library is not None:
        g.library = g.library[:library]
    return g


def shil(land_in_hand):
    deck, cmd = SM.build()
    g = SH.ShilgengarGame(list(deck), cmd, dict(DEFAULT_CFG, **EXTRA_CFG), 1)
    g.board = EN.Board()
    g.hand = [take(g.library, "Angel of the Ruins")]
    lands_out(g, ["Plains"] * 3)
    if land_in_hand:
        g.hand.append(take(g.library, "Swamp"))
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = karlov(6)
    hand = len(g.hand)
    EN.cycle_step(g, lambda c: KV.pay_cost(g, c))
    check("A six lands: Barren Moor cycled, a card drawn",
          ("Barren Moor" in [c.name for c in g.graveyard], len(g.hand),
           g.m["cycled"]), (True, hand, 1))

    g = karlov(5)
    EN.cycle_step(g, lambda c: KV.pay_cost(g, c))
    check("B five lands: kept", g.m["cycled"], 0)

    g = karlov(6, library=1)
    EN.cycle_step(g, lambda c: KV.pay_cost(g, c))
    check("C a one-card library: kept", g.m["cycled"], 0)

    g = shil(False)
    EN.cycle_step(g, lambda c: g.pay(c))
    from edhmc.decks._evasion import LAND_SUBTYPES
    got = [c.name for c in g.hand]
    check("D the Angel plainscycled: a Plains-typed dual to hand",
          (len(got), "Plains" in LAND_SUBTYPES.get(got[0] if got else "", ()),
           len(LAND_SUBTYPES.get(got[0] if got else "", ())) >= 2,
           "Angel of the Ruins" in [c.name for c in g.graveyard]),
          (1, True, True, True))

    g = shil(True)
    EN.cycle_step(g, lambda c: g.pay(c))
    check("E a land in hand: the Angel kept", g.m["landcycled"], 0)

    g = karlov(6)
    g.cfg["cycling"] = False
    EN.cycle_step(g, lambda c: KV.pay_cost(g, c))
    check("F NEIGHBOUR: cycling False: kept", g.m["cycled"], 0)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z226: cycling and landcycling\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "cycling=False": ({"A", "D"}, {"cycling": False}, []),
        "cycle_land_floor=0": ({"B"}, {"cycle_land_floor": 0}, []),
        "the draw is always safe": ({"C"}, {}, [
            (EN, "draw_is_safe", lambda g, n=1: True)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = dict(cfg)
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
