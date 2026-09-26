#!/usr/bin/env python3
"""Commander damage, CR 104.3j (§0z65).

    python -m tests.test_commander_damage
    python -m tests.test_commander_damage --mutate   # 5 mutations, exact sets

    104.3j  Any player who's been dealt 21 or more combat damage by the same
            commander over the course of the game loses the game.

The project did not model this at all. Now `damage_through` can report which
attackers got through a defender's blocks (`unblocked`), `commander_hit` reads
the commander's power among them, each `Opponent` accumulates `cmdr_damage`,
and `_check_eliminations` removes a player at 21. Only YOUR commander is
tracked; the opponents are an abstract board.

The fixture is rendmaw's commander, a 5/5 with MENACE -- so a block on it
costs the defender two blockers, which E relies on.

CASES
  A  PROPERTY: over 400 random boards (menace and fliers included), asking
     for `unblocked` changes no damage figure, and the unblocked attackers'
     power sums to exactly the damage returned
  B  an unblocked commander hit credits its power (5)
  C  16 + 5 = 21: eliminated at 30 life, counted as a commander-damage kill
  D  15 + 5 = 20: alive
  E  a BLOCKED commander deals no commander damage (its 1/1 partner connects)
  F  a non-commander creature's damage is not commander damage
  G  `commander_damage=False`: C's hit leaves them alive at 16
  H  the single-swing path (`combat_split=False`) credits the player hit
  I  `scale` does not inflate it: scale 2 takes 10 life and credits 5
  J  a hit that is lethal by life AND by commander damage is a life kill --
     the counter is the rule's own contribution only

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  21 never eliminates (commander_damage_lethal False) -> C
  blocks are not reported (chump ignores `blocked`)    -> A, E
  every unblocked attacker counts as the commander     -> E, F
  the knob is ignored                                  -> G
  commander damage checked BEFORE life                 -> J

  ONE EXPECTATION WAS WRONG, AND IT IS KEPT HERE. The third was written as
  "-> F" and broke E as well: E's 1/1 partner connects, so an attacker-blind
  count credits it 1. E is the case for a blocked commander AND a live
  partner, which makes it a check on both halves; the set is {E, F}.

UNMUTATED, and written down (§0z15): B, D and H are the positive and boundary
cases the mutations are measured against; I has no seam -- the scale is
simply never passed to `commander_hit`, which is the point of the case.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = RM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def creature(name, power, flying=False):
    return EN.Permanent(card=EN.Card(name=name, types=frozenset({"Creature"}),
                                     power=power, toughness=power,
                                     flying=flying), sick=False)


def commander():
    return EN.Permanent(card=CMD, sick=False, base_p=CMD.power,
                        base_t=CMD.toughness)


def game(blockers=0, **cfg):
    """Three opponents on 40 with `blockers` creatures each; opponent 0 on
    30, so every plan and every single swing reaches them first."""
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, block_share=1.0,
                                      flier_block_share=0.3, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    for o in g.opponents:
        o.life, o.creatures, o.goaded_birds = 40.0, float(blockers), 0.0
    g.opponents[0].life = 30.0
    return g


def hit(g, attackers, scale=1.0):
    OPP.combat_damage(g, attackers, scale=scale)
    return g.opponents[0]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    rnd, same = random.Random(11), True
    for _ in range(400):
        g = game(rnd.randint(0, 8))
        d = g.opponents[rnd.randrange(3)]
        atk = [creature(f"C{i}", rnd.randint(0, 9), rnd.random() < 0.3)
               for i in range(rnd.randint(0, 8))]
        if rnd.random() < 0.5:
            atk.append(commander())
        through = []
        plain = OPP.damage_through(g, atk, defender=d)
        told = OPP.damage_through(g, atk, defender=d, unblocked=through)
        same &= (plain == told
                 and float(sum(g.power_of(p) for p in through)) == told)
    check("A unblocked changes nothing, and sums to the damage, 400 boards",
          same, True)
    g = game()
    check("B an unblocked commander credits 5",
          sum(o.cmdr_damage for o in (hit(g, [commander()]), *g.opponents[1:])),
          5.0)
    g = game()
    g.opponents[0].cmdr_damage = 16.0
    o = hit(g, [commander()])
    check("C 16 + 5 = 21: eliminated at 25 life, one commander kill",
          (o.alive, o.life, g.m["commander_damage_kills"]), (False, 25.0, 1))
    g = game()
    g.opponents[0].cmdr_damage = 15.0
    check("D 15 + 5 = 20: alive", hit(g, [commander()]).alive, True)
    g = game(blockers=2)
    o = hit(g, [commander(), creature("Pip", 1)])
    check("E a blocked commander deals none; its partner connects",
          (o.cmdr_damage, o.life), (0.0, 29.0))
    g = game()
    hit(g, [creature("Big", 9)])
    check("F a non-commander's damage is not commander damage",
          sum(o.cmdr_damage for o in g.opponents), 0.0)
    g = game(commander_damage=False)
    g.opponents[0].cmdr_damage = 16.0
    o = hit(g, [commander()])
    check("G commander_damage=False: alive at 16", (o.alive, o.cmdr_damage),
          (True, 16.0))
    g = game(combat_split=False, combat_defender="target")
    check("H the single-swing path credits the player hit",
          hit(g, [commander()]).cmdr_damage, 5.0)
    g = game()
    o = hit(g, [commander()], scale=2.0)
    check("I scale 2: 10 life, 5 commander damage", (o.life, o.cmdr_damage),
          (20.0, 5.0))
    g = game()
    g.opponents[0].life, g.opponents[0].cmdr_damage = 3.0, 16.0
    o = hit(g, [commander()])
    check("J lethal both ways is a life kill",
          (o.alive, g.m["commander_damage_kills"]), (False, 0))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Commander damage (CR 104.3j)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(OPP, n) for n in
            ("commander_damage_lethal", "chump", "commander_hit",
             "_check_eliminations")}

    def chump_silent(items, budget, blocked=None):
        return real["chump"](items, budget)

    def every_attacker(g, through):
        if not g.cfg.get("commander_damage", True):
            return 0.0
        return float(sum(g.power_of(p) for p in through))

    def ignores_knob(g, through):
        return float(sum(g.power_of(p) for p in through
                         if p.card is g.commander))

    def cmdr_first(g):
        for o in g.opponents:
            if o.alive and OPP.commander_damage_lethal(g, o):
                o.alive, o.creatures = False, 0.0
                g.m["commander_damage_kills"] += 1
            elif o.alive and o.life <= 0:
                o.alive, o.creatures = False, 0.0
        if not OPP.living(g) and g.result is None:
            g.result = "win"

    muts = {
        "21 never eliminates":
            ({"C"}, "commander_damage_lethal", lambda g, o: False),
        "blocks are not reported":
            ({"A", "E"}, "chump", chump_silent),
        "every unblocked attacker counts as the commander":
            ({"E", "F"}, "commander_hit", every_attacker),
        "the knob is ignored":
            ({"G"}, "commander_hit", ignores_knob),
        "commander damage checked before life":
            ({"J"}, "_check_eliminations", cmdr_first),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(OPP, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(OPP, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
