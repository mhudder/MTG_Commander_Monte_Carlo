#!/usr/bin/env python3
"""§0z216: tivit's Lightning Greaves under the owner's policy -- "greaves
should be equipped to tivit only when the deck has no blink abilities in
play or in hand" (2026-11-15).

    python -m tests.test_greaves_policy
    python -m tests.test_greaves_policy --mutate   # 5 mutations, exact sets

`greaves_blink_policy` False is the old rule: shroud for as long as Greaves
is on the battlefield, and every blink still targets Tivit.

CASES
  A  Greaves and Tivit, no blink anywhere: equipped, Tivit shrouded
  B  Soulherder in play: Greaves moves to it, Tivit not shrouded, and the
     end step blinks Tivit
  C  Ephemerate in hand and a Rabbit: Greaves off, not shrouded
  D  Ephemerate in hand and NO other creature: equip has no other target,
     Greaves stays on and Tivit stays shrouded; the rebound is refused
  E  Deadeye's blink (does not target) goes through with Greaves on Tivit,
     and Greaves falls off; the next sorcery-speed step re-equips it
  F  Venser's +1 with Greaves stuck on Tivit: no exile
  G  A pending rebound counts as a blink in play: Greaves off
  H  NEIGHBOUR: an engine with no `shroud_attached` reads presence
  I  Tivit cast from the command zone with Soulherder in hand: no haste
  J  NEIGHBOUR: the same cast with no blink anywhere: haste

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  greaves_blink_policy=False                       -> B, C, D, E, F, G, I
  Venser not a targeted blink                      -> F
  equip ignores "another creature" (Greaves moves to anything) -> D
  blink_pending ignores the rebound                -> G
  shroud_attached always True (presence again)     -> B, C, G

UNMUTATED (§0z15): A and J are what both rules agree on; H is the other
engines' path through `commander_shrouded`.
"""
import sys
from types import SimpleNamespace

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as TV
from edhmc.engine import Permanent, Card
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.tivit import TivitGame
from edhmc.decks.tivit_v1 import VENSER_VISIONARY_TRAVELER

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("tivit")
TIVIT = "Tivit, Seller of Secrets"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = TivitGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.hand = [c for c in g.hand if c.name not in TV.TARGETED_BLINKS]
    for k in g.tokens:
        g.tokens[k] = 0
    return g


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    if name == VENSER_VISIONARY_TRAVELER.name:   # a candidate, not listed
        return VENSER_VISIONARY_TRAVELER
    raise LookupError(name)


def put(g, *names):
    for n in names:
        if n == TIVIT:
            g.board.append(Permanent(card=g.commander, sick=False))
            g.commander_cast = True
        else:
            g.board.append(Permanent(card=take(g, n), sick=False))


def to_hand(g, name):
    g.hand.append(take(g, name))


def rabbit(g):
    g.board.append(Permanent(card=Card(name="Rabbit token",
                                       types=frozenset({"Creature"}),
                                       power=1, toughness=1),
                             sick=False, is_token=True))


def tivit_perm(g):
    return next(p for p in g.board if p.card is g.commander)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh()
    put(g, TIVIT, "Lightning Greaves")
    TV.greaves_step(g)
    check("A no blink anywhere: shrouded", OPP.commander_shrouded(g), True)

    g = fresh()
    put(g, TIVIT, "Lightning Greaves", "Soulherder")
    g.greaves_on_tivit = True
    TV.greaves_step(g)
    shr = OPP.commander_shrouded(g)
    b0 = g.m["blinks"]
    TV.end_step(g)
    check("B Soulherder in play: not shrouded, the end step blinks Tivit",
          (shr, g.m["blinks"] - b0), (False, 1))

    g = fresh()
    put(g, TIVIT, "Lightning Greaves")
    rabbit(g)
    to_hand(g, "Ephemerate")
    g.greaves_on_tivit = True
    TV.greaves_step(g)
    check("C Ephemerate in hand, a Rabbit: not shrouded",
          OPP.commander_shrouded(g), False)

    g = fresh()
    put(g, TIVIT, "Lightning Greaves")
    TV.greaves_step(g)                     # no blink yet: equipped
    to_hand(g, "Ephemerate")
    TV.greaves_step(g)                     # no other creature to move it to
    shr = OPP.commander_shrouded(g)
    g.turn = 1                       # 0 would read as "no rebound armed"
    g.ephemerate_rebound = 1
    b0 = g.m["blinks"]
    TV.upkeep(g)
    check("D no other creature: stays shrouded, the rebound is refused",
          (shr, g.m["blinks"] - b0), (True, 0))

    g = fresh()
    put(g, TIVIT, "Lightning Greaves")
    TV.greaves_step(g)
    b0 = g.m["blinks"]
    TV.blink_tivit(g, "Deadeye Navigator")
    off = g.greaves_on_tivit
    TV.greaves_step(g)
    check("E Deadeye blinks through Greaves, it falls off, re-equipped",
          (g.m["blinks"] - b0, off, g.greaves_on_tivit), (1, False, True))

    g = fresh()
    put(g, TIVIT, "Lightning Greaves", "Venser, Visionary Traveler")
    g.greaves_on_tivit = True
    venser = next(p for p in g.board
                  if p.card.name == "Venser, Visionary Traveler")
    venser.counters = 4
    TV.walker_step(g)
    check("F Venser's +1, Greaves stuck on Tivit: no exile",
          g.venser_return, False)

    g = fresh()
    put(g, TIVIT, "Lightning Greaves")
    rabbit(g)
    g.greaves_on_tivit = True
    g.ephemerate_rebound = g.turn + 1
    TV.greaves_step(g)
    check("G a pending rebound: not shrouded",
          OPP.commander_shrouded(g), False)

    other = SimpleNamespace(cfg={"shroud_sources": ("Swiftfoot Boots",)},
                            has=lambda n: n == "Swiftfoot Boots")
    check("H NEIGHBOUR: no shroud_attached reads presence",
          OPP.commander_shrouded(other), True)

    for label, extra, want in (
            ("I Tivit cast, Soulherder in hand: no haste", "Soulherder",
             True),
            ("J NEIGHBOUR: Tivit cast, no blink: haste", None, False)):
        g = fresh()
        g.hand = []
        g.library = [c for c in g.library if c.name not in TV.TARGETED_BLINKS
                     or c.name == extra]
        put(g, "Lightning Greaves")
        if extra:
            to_hand(g, extra)
        g.tokens["Treasure"] = 6
        TV.main_phase(g)
        check(label, tivit_perm(g).sick, want)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z216: Lightning Greaves under the owner's policy\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    no_venser = tuple(n for n in TV.TARGETED_BLINKS
                      if n != "Venser, Visionary Traveler")
    real_blink_pending = TV.blink_pending

    def pending_no_rebound(g):
        saved, g.ephemerate_rebound = g.ephemerate_rebound, 0
        try:
            return real_blink_pending(g)
        finally:
            g.ephemerate_rebound = saved

    muts = {
        "greaves_blink_policy=False": (
            {"B", "C", "D", "E", "F", "G", "I"},
            {"greaves_blink_policy": False}, []),
        "Venser not a targeted blink": (
            {"F"}, {}, [(TV, "TARGETED_BLINKS", no_venser)]),
        "equip ignores another creature": (
            {"D"}, {}, [(OPP, "is_creature_now", lambda g, p: True)]),
        "blink_pending ignores the rebound": (
            {"G"}, {}, [(TV, "blink_pending", pending_no_rebound)]),
        "shroud_attached always True": (
            {"B", "C", "G"}, {},
            [(TivitGame, "shroud_attached", lambda self, n: True)]),
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
