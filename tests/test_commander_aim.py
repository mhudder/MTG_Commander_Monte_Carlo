#!/usr/bin/env python3
"""Aiming the commander, and a defender who knows 104.3j (§0z67).

    python -m tests.test_commander_aim
    python -m tests.test_commander_aim --mutate   # 5 mutations, exact sets

§0z65 modelled commander damage without teaching either side about it: the
pilot put the commander wherever its power sorted in the life-damage plan,
and a defender on 16 blocked by power per blocker as if 21 did not exist.
`opponents.commander_target` aims it (`commander_aim`: off / lethal / focus);
`opponents.commander_must_block` makes a defender it would kill block it
first (`commander_block_aware`).

The fixture is rendmaw's commander, a 5/5 with MENACE -- a block on it costs
two blockers, which F and G rely on.

CASES
  A  PROPERTY: with no commander attacking, "lethal" and "focus" leave every
     opponent exactly as "off" does, over 300 random boards
  B  lethal: opponent 1 is on 16 commander damage and the plan is chipping
     opponent 0 -- the commander goes at opponent 1 and kills them
  C  lethal, two candidates (40 life on 16, 35 life on 18): the one with MORE
     life, the kill life damage is furthest from
  D  focus: nobody is in range, opponent 2 is on 5 -- the commander goes there
  E  lethal, nobody in range: the commander stays in the plan (opponent 2,
     on 5, is not hit)
  F1 aware: a defender on 16 with two blockers blocks the commander, not the
     4/4 beside it -- they survive
  F2 unaware: the same defender chumps the 4/4 and dies to the commander
  G  aware, but the hit would not reach 21 (on 10): the defender blocks by
     power per blocker as before -- the commander connects
  H  an aimed swing is counted (`commander_aimed`)
  I  lethal, but the target has two blockers and knows 104.3j: NOT aimed --
     the commander stays in the plan (opponent 0's group) and opponent 1,
     on 16, is untouched. The first version aimed it into the block.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the commander is never aimed                       -> B, C, D, H
  lethal aims at the LEAST life                      -> C
  no defender knows 104.3j                           -> F1
  every defender blocks the commander first, lethal or not -> G
  the aim ignores whether the commander gets through  -> I

  ONE MUTATION WAS WRONG ON ITS FIRST RUN, AND IT IS KEPT HERE. The last
  one replaced `commander_must_block` wholesale and so removed the
  `commander_block_aware` gate along with the lethality test: F2, which
  turns awareness off, broke too. A mutation removes ONE rule; it now keeps
  the gate and the expected set stands.

UNMUTATED (§0z15): A is the property that nothing changes without a
commander; E and F2 are the neighbours the aim and the awareness must not
reach.
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


def creature(name, power):
    return EN.Permanent(card=EN.Card(name=name, types=frozenset({"Creature"}),
                                     power=power, toughness=power), sick=False)


def commander():
    return EN.Permanent(card=CMD, sick=False, base_p=CMD.power,
                        base_t=CMD.toughness)


def game(lives=(30, 40, 40), cmdr=(0, 0, 0), blockers=(0, 0, 0), **cfg):
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, block_share=1.0,
                                      flier_block_share=0.3, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    for o, life, c, b in zip(g.opponents, lives, cmdr, blockers):
        o.life, o.cmdr_damage = float(life), float(c)
        o.creatures, o.goaded_birds = float(b), 0.0
    return g


def state(g):
    return [(o.alive, o.life, o.cmdr_damage) for o in g.opponents]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    rnd, same = random.Random(5), True
    for _ in range(300):
        lives = [rnd.randint(1, 40) for _ in range(3)]
        cmdr = [rnd.choice([0, 0, 10, 18]) for _ in range(3)]
        blk = [rnd.randint(0, 4) for _ in range(3)]
        atk = [(f"C{i}", rnd.randint(0, 9)) for i in range(rnd.randint(1, 7))]
        out = []
        for mode in ("off", "lethal", "focus"):
            g = game(lives, cmdr, blk, commander_aim=mode)
            OPP.combat_damage(g, [creature(n, p) for n, p in atk])
            out.append(state(g))
        same &= out[0] == out[1] == out[2]
    check("A no commander: lethal and focus are off, 300 boards", same, True)
    smalls = [creature(f"s{i}", 1) for i in range(3)]
    g = game(cmdr=(0, 16, 0), commander_aim="lethal")
    OPP.combat_damage(g, [commander()] + smalls)
    check("B lethal: the commander kills opponent 1 on 16",
          g.opponents[1].alive, False)
    g = game(lives=(30, 40, 35), cmdr=(0, 16, 18), commander_aim="lethal")
    OPP.combat_damage(g, [commander()])
    check("C lethal, two in range: the one on 40 life",
          (g.opponents[1].alive, g.opponents[2].alive), (False, True))
    g = game(cmdr=(0, 0, 5), commander_aim="focus")
    OPP.combat_damage(g, [commander()] + smalls)
    check("D focus: the commander goes at opponent 2, on 5",
          g.opponents[2].cmdr_damage, 10.0)
    g = game(cmdr=(0, 0, 5), commander_aim="lethal")
    OPP.combat_damage(g, [commander()] + smalls)
    check("E lethal, nobody in range: opponent 2 is not hit",
          g.opponents[2].cmdr_damage, 5.0)
    four = creature("Four", 4)
    g = game(cmdr=(16, 0, 0), blockers=(2, 0, 0), commander_block_aware=True,
             commander_aim="off")
    OPP.combat_damage(g, [commander(), four])
    check("F1 aware: a defender on 16 blocks the commander and survives",
          g.opponents[0].alive, True)
    g = game(cmdr=(16, 0, 0), blockers=(2, 0, 0), commander_block_aware=False,
             commander_aim="off")
    OPP.combat_damage(g, [commander(), four])
    check("F2 unaware: they chump the 4/4 and die to the commander",
          g.opponents[0].alive, False)
    g = game(cmdr=(10, 0, 0), blockers=(2, 0, 0), commander_block_aware=True,
             commander_aim="off")
    OPP.combat_damage(g, [commander(), four])
    check("G aware, not lethal: the commander connects (10 -> 15)",
          g.opponents[0].cmdr_damage, 15.0)
    g = game(cmdr=(0, 16, 0), commander_aim="lethal")
    OPP.combat_damage(g, [commander()] + smalls)
    check("H an aimed swing is counted", g.m["commander_aimed"], 1)
    g = game(cmdr=(0, 16, 0), blockers=(0, 2, 0), commander_aim="lethal",
             commander_block_aware=True)
    OPP.combat_damage(g, [commander()] + smalls)
    check("I lethal but blocked: not aimed, opponent 1 untouched",
          (g.m["commander_aimed"], g.opponents[1].cmdr_damage), (0, 16.0))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Aiming the commander; a defender who knows 104.3j\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(OPP, n) for n in ("commander_target",
                                         "commander_must_block",
                                         "commander_gets_through")}

    def least_life(g, attackers, alive):
        cmdr, aim = real["commander_target"](g, attackers, alive)
        if cmdr is None:
            return cmdr, aim
        pw = g.power_of(cmdr)
        lethal = [o for o in alive if o.cmdr_damage + pw >= 21]
        return (cmdr, min(lethal, key=lambda o: o.life)) if lethal \
            else (cmdr, aim)

    def always_block(g, perm, defender):
        # Keeps the knob; drops ONLY the lethality test. The first version
        # dropped both and broke F2 as well -- see the docstring.
        return (g.cfg.get("commander_block_aware", True)
                and defender is not None and perm.card is g.commander)

    muts = {
        "the commander is never aimed":
            ({"B", "C", "D", "H"}, "commander_target",
             lambda g, a, alive: (None, None)),
        "lethal aims at the least life":
            ({"C"}, "commander_target", least_life),
        "no defender knows 104.3j":
            ({"F1"}, "commander_must_block", lambda g, p, d: False),
        "every defender blocks the commander first":
            ({"G"}, "commander_must_block", always_block),
        "the aim ignores whether the commander gets through":
            ({"I"}, "commander_gets_through", lambda g, c, d: True),
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
