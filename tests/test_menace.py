#!/usr/bin/env python3
"""Menace in the blocking model (§0z61).

    python -m tests.test_menace
    python -m tests.test_menace --mutate   # 3 mutations, exact sets

    Menace (CR 702.111b): "A creature with menace can't be blocked except by
    two or more creatures."

Opponents' boards are a blocker COUNT (`_blocker_counts`), and
`damage_through` chump-blocks your biggest attackers with it. A menace
attacker takes two of those blockers (`chump` prices each attacker at 1 or 2
and stops the most power per blocker). MENACE is generated from Scryfall's
keywords by `tag_flying`; in the current lists it is Rendmaw and
Gloomshrieker. With no menace on the board the rule is the old one exactly.

CASES
  A  PROPERTY: over 400 random boards with no menace, `damage_through`
     equals the old biggest-first rule to the digit
  B  one menace 6/6 against one blocker: all 6 through
  C  one menace 6/6 against two blockers: blocked
  D  a menace 4/4 and two 3/3s against two blockers: the two 3/3s are
     blocked and the 4/4 connects (power per blocker, 3 beats 2)
  E  a menace FLIER against one flying-capable blocker: unblockable by it,
     and ground blockers cannot help -- all 5 through
  F  menace_of: Rendmaw yes, a vanilla creature no, Edgar no (his menace is
     conditional, so it is not in the generated set)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  menace is ignored (menace_of always False)        -> B, D, E, F
  chump ignores the blocker cost                    -> B, D, E
  chump blocks biggest-first, not power per blocker -> D

UNMUTATED (§0z15): A is the property that the change is inert without
menace; C is the positive case B's mutation is measured against.
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


def game(blockers, fshare=0.0):
    """A defender with exactly `blockers` blockers, `fshare` of them able to
    catch a flier."""
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, block_share=1.0,
                                      flier_block_share=fshare),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    d = g.opponents[0]
    d.creatures, d.goaded_birds = float(blockers), 0.0
    return g, d


def menace(power, flying=False):
    """A creature the generated MENACE set names: Rendmaw's name, any stats."""
    return creature("Rendmaw, Creaking Nest", power, flying)


def old_rule(g, attackers, d):
    n_block, n_fly = OPP._blocker_counts(g, d)
    fly = sorted((g.power_of(p) for p in attackers if OPP.flying_of(g, p)),
                 reverse=True)
    gr = sorted((g.power_of(p) for p in attackers if not OPP.flying_of(g, p)),
                reverse=True)
    bf = min(n_fly, len(fly))
    bg = min((n_block - n_fly) + (n_fly - bf), len(gr))
    return float(sum(fly[bf:]) + sum(gr[bg:]))


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    rnd, same = random.Random(7), True
    for _ in range(400):
        g, d = game(rnd.randint(0, 8), rnd.choice([0.0, 0.3, 0.5, 1.0]))
        atk = [creature(f"C{i}", rnd.randint(0, 9), rnd.random() < 0.3)
               for i in range(rnd.randint(0, 10))]
        same &= OPP.damage_through(g, atk, defender=d) == old_rule(g, atk, d)
    check("A no menace: the old rule, to the digit, over 400 boards", same, True)
    g, d = game(1)
    check("B menace 6/6 vs one blocker: 6 through",
          OPP.damage_through(g, [menace(6)], defender=d), 6.0)
    g, d = game(2)
    check("C menace 6/6 vs two blockers: blocked",
          OPP.damage_through(g, [menace(6)], defender=d), 0.0)
    g, d = game(2)
    check("D menace 4/4 + two 3/3s vs two blockers: 4 through",
          OPP.damage_through(g, [menace(4), creature("x", 3), creature("y", 3)],
                             defender=d), 4.0)
    g, d = game(2, fshare=0.5)
    check("E menace flier vs one flying-capable blocker: 5 through",
          OPP.damage_through(g, [menace(5, flying=True)], defender=d), 5.0)
    g, _ = game(0)
    edgar = EN.Permanent(card=EN.Card(name="Edgar, Charmed Groom",
                                      types=frozenset({"Creature"}), power=4,
                                      toughness=4), sick=False)
    check("F menace_of: Rendmaw yes, vanilla no, Edgar no",
          (OPP.menace_of(g, menace(5)), OPP.menace_of(g, creature("v", 2)),
           OPP.menace_of(g, edgar)), (True, False, False))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Menace in the blocking model\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_menace, real_chump = OPP.menace_of, OPP.chump

    def chump_no_cost(items, budget):
        return real_chump([(pw, 1) for pw, _ in items], budget)

    def chump_biggest_first(items, budget):
        stopped, used = 0.0, 0
        for pw, cost in sorted(items, key=lambda it: it[0], reverse=True):
            if used + cost <= budget:
                used += cost
                stopped += pw
        return stopped, used

    muts = {
        "menace is ignored": ({"B", "D", "E", "F"}, "menace_of",
                              lambda g, p: False),
        "chump ignores the blocker cost": ({"B", "D", "E"}, "chump", chump_no_cost),
        "chump blocks biggest-first": ({"D"}, "chump", chump_biggest_first),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(OPP, name, fn)
        try:
            broke = run_cases()
        finally:
            OPP.menace_of, OPP.chump = real_menace, real_chump
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
