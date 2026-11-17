#!/usr/bin/env python3
"""§0z231, §0z232 (§0z206 floors 2-5): keywords an engine grants and a card
name cannot carry -- an animated land's reach and indestructible, Nissa's
emblem, Sapling Nursery's Treefolk's reach (azusa), and The Swarmweaver's
delirium deathtouch (rendmaw, a candidate).

    python -m tests.test_granted_keywords
    python -m tests.test_granted_keywords --mutate   # 3 mutations, exact sets

Azusa cases set the battlefield by hand and read `opponents.is_hardy` and
`opponents.reach_of`, which combat reads (`attack_facts`, `your_blockers`).

CASES
  A  azusa, a Forest animated by Sylvan Awakening's effect (reach,
     indestructible): hardy, and reach
  B  NEIGHBOUR: a Forest animated without them (Nissa's +1): neither
  C  Nissa's emblem, an unanimated Forest: hardy
  D  Sapling Nursery's landfall makes a 3/4 Treefolk: reach
  E  rendmaw, The Swarmweaver out, delirium, an Insect token: deathtouch
     attacking (`deathtouch_of`) and blocking (`your_blockers`)
  F  NEIGHBOUR: `animated_land_text` False, A's setup: neither

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  animated_land_text=False                -> A, C, D
  swarmweaver_deathtouch=False            -> E
  reach_of reads the name only            -> A, D

UNMUTATED (§0z15): B and F are the old reading under every rule here.
"""
import random
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import azusa_v1 as AM
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


def take(zone, name):
    c = next(x for x in zone if x.name == name)
    EN.remove_card(zone, c)
    return c


def azusa(**cfg):
    deck, cmd = AM.build()
    g = AZ.AzusaGame(list(deck), cmd,
                     dict(DEFAULT_CFG, **{**cfg, **EXTRA_CFG}), 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 4
    forest = g.make_permanent(take(g.library, "Forest"), sick=False)
    return g, forest


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, f = azusa()
    g.animate_lands(2, 2, targets=[f], haste=True, reach=True,
                    indestructible=True, through_pod_round=True,
                    source="Sylvan Awakening")
    check("A Sylvan Awakening's land: hardy, reach",
          (OPP.is_hardy(g, f), OPP.reach_of(g, f)), (True, True))

    g, f = azusa()
    g.animate_lands(0, 0, targets=[f], haste=True, source="Nissa")
    check("B NEIGHBOUR: a plain animation: neither",
          (OPP.is_hardy(g, f), OPP.reach_of(g, f)), (False, False))

    g, f = azusa()
    g.nissa_emblem = True
    check("C Nissa's emblem: a Forest is hardy", OPP.is_hardy(g, f), True)

    g, f = azusa()
    g.make_permanent(AM.SAPLING_NURSERY, sick=False)    # a candidate
    before = {id(p) for p in g.board}
    g._landfall_payoffs(take(g.library, "Forest"), played=True)
    trees = [p for p in g.board if id(p) not in before
             and p.card.name == "Treefolk token"]
    check("D Sapling Nursery's Treefolk: reach",
          (len(trees) >= 1, all(OPP.reach_of(g, p) for p in trees)),
          (True, True))

    deck, cmd = RM.build()
    r = EN.Game(list(deck), cmd, dict(DEFAULT_CFG, **EXTRA_CFG),
                random.Random(1), seed_for_pod=1)
    r.board = EN.Board()
    r.board.append(EN.Permanent(card=RM.THE_SWARMWEAVER, sick=False))
    r.graveyard = [EN.Card(name=f"x{i}", types=frozenset({t}))
                   for i, t in enumerate(("Creature", "Artifact",
                                          "Enchantment", "Land"))]
    bug = r.make_tokens(1, 1, 1, "Insect", flying=True)[0]
    bug.sick = False
    blk = [b for b in OPP.your_blockers(r) if b.ref is bug]
    check("E The Swarmweaver: an Insect has deathtouch both ways",
          (OPP.deathtouch_of(r, bug), bool(blk) and blk[0].dt),
          (True, True))

    g, f = azusa(animated_land_text=False)
    g.animate_lands(2, 2, targets=[f], haste=True, reach=True,
                    indestructible=True, through_pod_round=True,
                    source="Sylvan Awakening")
    check("F NEIGHBOUR: animated_land_text False: neither",
          (OPP.is_hardy(g, f), OPP.reach_of(g, f)), (False, False))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z231-§0z232: granted keywords\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    from edhmc.decks._evasion import REACH

    def name_only(g, perm):
        return perm.card.name in REACH

    muts = {
        "animated_land_text=False": ({"A", "C", "D"},
                                     {"animated_land_text": False}, []),
        "swarmweaver_deathtouch=False": ({"E"},
                                         {"swarmweaver_deathtouch": False}, []),
        "reach_of reads the name only": ({"A", "D"}, {}, [
            (OPP, "reach_of", name_only)]),
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
