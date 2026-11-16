#!/usr/bin/env python3
"""§0z221, A5: the pod attacks your planeswalkers (`pod_attacks_walkers`).

    python -m tests.test_walker_attacks
    python -m tests.test_walker_attacks --mutate   # 3 mutations, exact sets

Each case drives one opponent's declared attack at you
(`opponents._attack_you`) on a karlov game with an empty battlefield, the
pod's attack safety off so every body sent is sent, and Sorin, Vengeful
Bloodlord as the walker where there is one.

CASES
  A  Sorin at 4, bodies of power 5 and 3, you at 40: the 5 goes at Sorin
     and kills it; the 3 hits you
  B  the same at 5 life: the attack is lethal as declared, every body goes
     at you, Sorin untouched
  C  Sorin at 10, bodies 5 and 3: no body set reaches 10, nothing at Sorin
  D  Sorin at 4, one body of power 5, a 1/1 of yours untapped: it chumps for
     Sorin, who lives
  E  Grist's upkeep with the switch on: loyalty 3 on its first +1, so 4
  F  NEIGHBOUR: no walker -- bodies 5 and 3, you take 8

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pod_attacks_walkers=False                -> A, D, E
  the lethal check removed                 -> B
  no blocks for a walker                   -> D

UNMUTATED (§0z15): C and F read the same under both rules.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as KV
import edhmc.opponents as OPP
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {"pod_attacks_walkers": True}
SORIN = "Sorin, Vengeful Bloodlord"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(module, name):
    deck, cmd = module.build()
    return next(c for c in list(deck) + [cmd] if c.name == name)


def game(life, loyalty=None, powers=(5, 3), **cfg):
    deck, cmd = KM.build()
    g = KV.KarlovGame(list(deck), cmd,
                      dict(DEFAULT_CFG, pod_attack_safety=False,
                           **{**EXTRA_CFG, **cfg}), 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.your_life = float(life)
    walker = None
    if loyalty is not None:
        walker = EN.Permanent(card=card(KM, SORIN), sick=False)
        walker.counters = loyalty
        g.board.append(walker)
    opp = g.opponents[0]
    bodies = [OPP.PodBody(4, 3, False, p) for p in powers]
    opp.body_tapped = [False] * len(bodies)
    return g, opp, bodies, walker


def rabbit(g):
    g.board.append(EN.Permanent(card=EN.Card(
        name="Rabbit token", types=frozenset({"Creature"}), power=1,
        toughness=1), sick=False, is_token=True))


def attack(g, opp, bodies):
    OPP._attack_you(g, opp, bodies, list(range(len(bodies))), set())


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, opp, bodies, w = game(40, loyalty=4)
    attack(g, opp, bodies)
    check("A Sorin at 4, bodies 5 and 3: Sorin dies, you take 3",
          (w in g.board, g.your_life), (False, 37.0))

    g, opp, bodies, w = game(5, loyalty=4)
    attack(g, opp, bodies)
    check("B at 5 life the attack is lethal: all at you, Sorin untouched",
          (w.counters, g.your_life <= 0), (4, True))

    g, opp, bodies, w = game(40, loyalty=10)
    attack(g, opp, bodies)
    check("C Sorin at 10: nothing reaches it, you take 8",
          (w.counters, g.your_life), (10, 32.0))

    g, opp, bodies, w = game(40, loyalty=4, powers=(5,))
    rabbit(g)
    attack(g, opp, bodies)
    check("D a 1/1 chumps for Sorin, who lives",
          (w in g.board, w.counters, g.your_life), (True, 4, 40.0))

    deck, cmd = RM.build()
    from edhmc.engine import Game
    import random
    rg = Game(list(deck), cmd, dict(DEFAULT_CFG, **EXTRA_CFG),
              random.Random(1), 1)
    rg.board = EN.Board()
    grist = EN.Permanent(card=card(RM, "Grist, the Hunger Tide"), sick=False)
    rg.board.append(grist)
    EN.upkeep(rg)
    check("E Grist's first +1 with the switch on: loyalty 4", grist.counters, 4)

    g, opp, bodies, w = game(40)
    attack(g, opp, bodies)
    check("F NEIGHBOUR: no walker, you take 8", g.your_life, 32.0)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z221 A5: the pod attacks your planeswalkers\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_split = OPP.split_for_walker
    real_plan = OPP.plan_blocks

    def split_no_lethal(g, bodies, sent, plan):
        life, g.your_life = g.your_life, 1e9
        try:
            return real_split(g, bodies, sent, plan)
        finally:
            g.your_life = life

    def plan_no_walker(g, life, atk, blockers, cap, **kw):
        if kw.get("prefix") == "walker_block_":
            return {}
        return real_plan(g, life, atk, blockers, cap, **kw)

    muts = {
        "pod_attacks_walkers=False": ({"A", "D", "E"},
                                      {"pod_attacks_walkers": False}, []),
        "the lethal check removed": ({"B"}, {}, [
            (OPP, "split_for_walker", split_no_lethal)]),
        "no blocks for a walker": ({"D"}, {}, [
            (OPP, "plan_blocks", plan_no_walker)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = {"pod_attacks_walkers": True, **cfg}
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {"pod_attacks_walkers": True}
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
