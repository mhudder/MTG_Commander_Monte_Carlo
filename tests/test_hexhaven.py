#!/usr/bin/env python3
"""§0z249: Hexhaven Invigorator (azusa, the owner's proposal 2026-11-22).

    python -m tests.test_hexhaven
    python -m tests.test_hexhaven --mutate   # 5 mutations, exact sets

    "Vigilance / Whenever this creature is dealt damage, you may search your
    library for up to that many land cards, put them onto the battlefield
    tapped, then shuffle."  ({G}{G}{G}{G}, 6/6; Scryfall, 2026-11-22.)

The pod's combat tells the engine the damage each of your creatures is
dealt (`opponents.damage_to_attacker`, `damage_to_blockers`,
`your_creatures_damaged`); azusa's `on_your_creature_damaged` is the
trigger.

CASES
  A  damage_to_attacker: a 6/6 blocked by two 3/3s is dealt 6
  B  ... a 2/2 blocked by a first-striking 3/3 and a 2/2 is dealt 3 -- the
     first striker kills it, and the 2/2 deals nothing (510.4)
  C  damage_to_blockers: a 5/5 blocked by your 2/2 and 6/6 -- 2 to the 2/2
     (lethal, weakest first), the remaining 3 to the 6/6
  D  azusa: Hexhaven dealt 3, a library of Forests with Windswept Heath
     LAST and twenty sorceries: three lands onto the battlefield tapped,
     the Heath among them (`land_rank`: a fetch first), three landfall
  E  ... another creature dealt 3: nothing
  F  ... Hexhaven dealt 6, a library of six cards, four of them lands: one
     land -- the decking guard keeps five (`draw_is_safe`)
  G  END TO END: a pod 4/4 attacks you, Hexhaven blocks: dealt 4, four lands

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  your_creatures_damaged tells the engine nothing      -> G
  damage_to_blockers puts the whole power on each blocker -> C
  on_your_creature_damaged ignores the decking guard   -> F
  land_rank ranks every land the same                  -> D
  damage_to_attacker ignores first strike              -> B

UNMUTATED (§0z15): A is the plain sum; E the name check, which a mutation
would turn into every creature fetching lands -- a different card.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.azusa import AzusaGame
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = build_pending("azusa")
CATALOG_CARD = __import__("edhmc.decks.azusa_v1",
                          fromlist=["x"]).HEXHAVEN_INVIGORATOR


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def atk(power, tough, fs=False):
    return OPP._Atk(0, None, power, tough, False, False, False, False, fs,
                    False, False, 0.0, False)


def blk(ref, power, tough, fs=False):
    return OPP._Blk(ref, power, tough, False, False, 0.0, fs)


def named(name):
    return next(c for c in DECK if c.name == name)


def forest():
    return Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                produces=frozenset("G"))


def filler(i):
    return Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                cost={"gen": 1})


def fresh(library, **cfg):
    g = AzusaGame(list(DECK), CMD, dict(DEFAULT_CFG, turns=20,
                                        watch=frozenset(), **cfg), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.commander_cast = True
    g.bonus_mana = []
    g.library[:] = list(library)
    hex_ = Permanent(card=CATALOG_CARD, sick=False)
    g.board.append(hex_)
    return g, hex_


def lands_on(g):
    return [p.card.name for p in g.board if p.card.is_land]


def run_cases():
    PASS.clear()
    FAIL.clear()

    check("A a 6/6 blocked by two 3/3s is dealt 6",
          OPP.damage_to_attacker(atk(6, 6), [blk(1, 3, 3), blk(2, 3, 3)]), 6)
    check("B a first-striking 3/3 kills the 2/2 first: dealt 3",
          OPP.damage_to_attacker(atk(2, 2), [blk(1, 3, 3, fs=True),
                                             blk(2, 2, 2)]), 3)
    check("C a 5/5 into a 2/2 and a 6/6: 2 and 3",
          sorted(OPP.damage_to_blockers(atk(5, 5), [blk("big", 6, 6),
                                                    blk("small", 2, 2)])),
          [("big", 3), ("small", 2)])

    lib = ([filler(i) for i in range(20)] + [forest() for _ in range(4)]
           + [named("Windswept Heath")])
    g, hx = fresh(lib)
    before = g.m["landfall_triggers"]
    g.on_your_creature_damaged(hx, 3)
    tapped = [p.tapped for p in g.board if p.card.is_land]
    check("D dealt 3: three lands, tapped, the Heath first, three landfall",
          (g.m["hexhaven_lands"], len(tapped), all(tapped),
           "Windswept Heath" in lands_on(g),
           g.m["landfall_triggers"] - before >= 3),
          (3, 3, True, True, True))

    g, hx = fresh(lib)
    other = Permanent(card=named("Rampaging Baloths"), sick=False)
    g.board.append(other)
    g.on_your_creature_damaged(other, 3)
    check("E another creature dealt 3: nothing",
          (g.m["hexhaven_triggers"], lands_on(g)), (0, []))

    g, hx = fresh([filler(0), filler(1)] + [forest() for _ in range(4)])
    g.on_your_creature_damaged(hx, 6)
    check("F a six-card library: one land, five kept",
          (g.m["hexhaven_lands"], len(g.library)), (1, 5))

    g, hx = fresh(lib, pod_attack_safety=False)
    opp = g.opponents[0]
    opp.bodies = [OPP.PodBody(4, 4, False, 4)]
    opp.body_tapped = [False]
    opp.creatures = 1.0
    OPP._attack_you(g, opp, opp.bodies, [0], set())
    check("G a pod 4/4 attacks, Hexhaven blocks: dealt 4, four lands",
          (g.m["hexhaven_damage"], g.m["hexhaven_lands"]), (4, 4))
    return set(FAIL)


def _all_on_each(a, blks):
    if OPP._blockers_first(a, blks):
        return []
    return [(b.ref, a.power) for b in blks]


def _no_guard(self, perm, n):
    real = AZ.draw_is_safe
    AZ.draw_is_safe = lambda g, k: True
    try:
        REAL_HOOK(self, perm, n)
    finally:
        AZ.draw_is_safe = real


REAL_HOOK = AzusaGame.on_your_creature_damaged


def main() -> int:
    if not MUTATE:
        print("§0z249: Hexhaven Invigorator\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "your_creatures_damaged tells the engine nothing":
            ({"G"}, OPP, "your_creatures_damaged", lambda g, hurt: None),
        "damage_to_blockers puts the whole power on each blocker":
            ({"C"}, OPP, "damage_to_blockers", _all_on_each),
        "on_your_creature_damaged ignores the decking guard":
            ({"F"}, AzusaGame, "on_your_creature_damaged", _no_guard),
        "land_rank ranks every land the same":
            ({"D"}, AzusaGame, "land_rank", lambda self, card: 0.0),
        "damage_to_attacker ignores first strike":
            ({"B"}, OPP, "damage_to_attacker",
             lambda a, blks: OPP._damage_back(a, blks)),
    }
    bad = 0
    for label, (want, obj, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(obj, name)
        setattr(obj, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(obj, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
