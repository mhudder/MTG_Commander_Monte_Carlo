#!/usr/bin/env python3
"""The split plan's blocker count (§0z205; `opponents.plan_blockers`,
`split_blockers`, default "formula").

    python -m tests.test_plan_blockers
    python -m tests.test_plan_blockers --mutate   # 4 mutations, exact sets

`_attack_groups` (the pilot's split across defenders, §0v) takes a defender
on with `k = m + 1 + b` attackers: the m that must connect, one for the
biggest it removes, and `b` it might block. Under A1 the combat resolves
against `available_blockers` -- under A2 every untapped body and Bird --
while the default `b` is the formula's count (`_blocker_counts`:
`block_share` of every creature, tapped or not). §0z205 measured three
rules: "formula" (kept, the best), "untapped" (the resolution's count:
-0.0020 at T20, it over-insures) and "share" (`block_share` of the
untapped count: inside the bar). This pins all three.

Every case: opponent 0 has five 2/2 combat bodies; A1 and A2 on unless
said; `block_share` 0.6, so the formula's count is int(5 x 0.6) = 3.

CASES
  A  "untapped", none tapped: b = 5, every untapped body
  B  "untapped", four tapped (they attacked on their turn): b = 1
  C  the default ("formula"), four tapped: b = 3, tapped or not
  D  "untapped", Serra's Emissary on your battlefield: b = 0
  E  "untapped" off A1 (`attacker_deaths`, `you_block` False): the formula, 3
  F  the plan reads it: ten 1/1s at opponent 0 on 4 life, four of its
     bodies tapped, opponent 1 on 40 with no creatures -- opponent 0's
     group is 4 + 1 + 1 = 6 attackers under "untapped", 4 + 1 + 3 = 8 under
     the default
  G  "share": four tapped int(1 x 0.6) = 0, none tapped int(5 x 0.6) = 3

MUTATIONS, WRITTEN BEFORE THE FIRST RUN, exact sets:
  tapped bodies are counted under A2          -> B, F, G
  every mode reads the formula                -> A, B, D, F, G
  Serra's Emissary is not read                -> D
  "share" ignores the share                   -> G

UNMUTATED (§0z15): C and E are the formula's paths, read by the plain run.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
B = OPP.PodBody
TWO = B(2, 2, False, 2, False, False)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(tapped=0, mine=(), **cfg):
    deck, cmd = RM.build()
    base = dict(DEFAULT_CFG, pod_bodies=True, attacker_deaths=True,
                you_block=True, block_share=0.6)
    g = EN.Game(list(deck), cmd, dict(base, **cfg), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.turn = 6
    g.your_life = 40.0
    g.monarch = False
    o, o1 = g.opponents[0], g.opponents[1]
    for x in g.opponents[2:]:
        x.alive, x.life, x.creatures = False, 0.0, 0.0
    o.life, o.creatures, o.goaded_birds = 4.0, 5.0, 0.0
    o.body_pool, o.bodies, o.next_body = tuple([TWO] * 5), [], 0
    OPP.pod_bodies(g, o)
    o.body_tapped = [i < tapped for i in range(5)]
    o1.life, o1.creatures, o1.goaded_birds = 40.0, 0.0, 0.0
    o1.body_pool, o1.bodies, o1.next_body, o1.body_tapped = (), [], 0, []
    for c in mine:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g, o


def ones(g, n):
    out = []
    for k in range(n):
        c = EN.Card(name=f"One{k}", types=frozenset({"Creature"}),
                    power=1, toughness=1)
        p = EN.Permanent(card=c, sick=False, base_p=1, base_t=1)
        g.board.append(p)
        out.append(p)
    return out


def group_size(g, o, attackers):
    plan, _cmdr = OPP._attack_groups(g, attackers)
    for grp in plan:
        if grp[0] is o:
            return len(grp[1])
    return 0


def run_cases():
    FAIL.clear()
    PASS.clear()
    U = dict(split_blockers="untapped")

    g, o = game(**U)
    check("A untapped, none tapped: every untapped body, 5",
          OPP.plan_blockers(g, o), 5)

    g, o = game(tapped=4, **U)
    check("B untapped, four tapped: 1", OPP.plan_blockers(g, o), 1)

    g, o = game(tapped=4)
    check("C the default, the formula: 3", OPP.plan_blockers(g, o), 3)

    emissary = EN.Card(name="Serra's Emissary",
                       types=frozenset({"Creature"}), power=7, toughness=7)
    g, o = game(mine=(emissary,), **U)
    check("D untapped, Serra's Emissary: 0", OPP.plan_blockers(g, o), 0)

    g, o = game(tapped=4, attacker_deaths=False, you_block=False, **U)
    check("E untapped off A1: the formula, 3", OPP.plan_blockers(g, o), 3)

    g, o = game(tapped=4, **U)
    on = group_size(g, o, ones(g, 10))
    g, o = game(tapped=4)
    off = group_size(g, o, ones(g, 10))
    check("F the plan: 6 at opponent 0 untapped, 8 on the formula",
          (on, off), (6, 8))

    S = dict(split_blockers="share")
    g, o = game(tapped=4, **S)
    a = OPP.plan_blockers(g, o)
    g, o = game(**S)
    check("G share: 0 with four tapped, 3 with none",
          (a, OPP.plan_blockers(g, o)), (0, 3))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The split plan reads the combat's blockers (§0z205)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.plan_blockers

    def variant(count_tapped=False, emissary=True, share=True):
        def f(g, opp):
            mode = g.cfg.get("split_blockers", "formula")
            if mode != "formula" and OPP.trades_on(g):
                if emissary and OPP.protected_from_creatures(g):
                    return 0
                n = (len(OPP.pod_bodies(g, opp)) if count_tapped
                     else OPP.available_blockers(g, opp)[1])
                if mode == "share" and share:
                    n = int(n * g.cfg.get("block_share", 0.60))
                return n
            return OPP._blocker_counts(g, opp)[0]
        return f

    muts = {
        "tapped bodies are counted under A2":
            ({"B", "F", "G"}, OPP, "plan_blockers", variant(count_tapped=True)),
        "every mode reads the formula":
            ({"A", "B", "D", "F", "G"}, OPP, "plan_blockers",
             lambda g, opp: OPP._blocker_counts(g, opp)[0]),
        "Serra's Emissary is not read":
            ({"D"}, OPP, "plan_blockers", variant(emissary=False)),
        '"share" ignores the share':
            ({"G"}, OPP, "plan_blockers", variant(share=False)),
    }
    assert real is OPP.plan_blockers
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        orig = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
