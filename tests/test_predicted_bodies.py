#!/usr/bin/env python3
"""The pilot's read of the pod's next swing under A2 (§0z203;
`predict_from_bodies`, on, read only under `you_block`).

    python -m tests.test_predicted_bodies
    python -m tests.test_predicted_bodies --mutate   # 4 mutations, exact sets

Off A2 the pilot reads the formula (`_formula_chip`), as it always did.
Under A2 the swing is the pod's bodies, and the pilot reads them
(`opponents.predicted_from_bodies`): each combat body's chance of
attacking you times what it would get through alone against your blocks
as they stand. An expectation, never a roll. Read by the hold-back
(`hold_back`) and the clock floors (`clock_floor`).

Every case: one opponent alive (share 1), `pod_attack_rate` 1, A1 and A2
on, you at 40. Bodies are (toughness, mana value, black, power, utility,
reach).

CASES
  A  OFF (you_block False): the formula, `chip_amount` exactly
  B  ON, nothing of yours to block: a 3/3 body reads 3
  C  ON, your untapped 6/6 would block it: reads 0 (the formula did not
     know your blockers were there)
  D  ON, your 6/6 TAPPED: reads 3
  E  ON, a utility body never attacks: reads 0
  F  ON, two rounds: this round's 3, and next round's scaled by the pod's
     growth (1 body -> 1 + 0.7 x board)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the read ignores your blockers           -> C
  utility bodies are read as attackers     -> E
  the read is the formula                  -> B, C, D, E, F
  later rounds are not scaled by growth    -> F

UNMUTATED (§0z15): A is the OFF path, read by the plain run.
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


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(pool, mine=(), tapped=False, **cfg):
    deck, cmd = RM.build()
    base = dict(DEFAULT_CFG, pod_bodies=True, attacker_deaths=True,
                you_block=True, pod_attack_rate=1.0)
    g = EN.Game(list(deck), cmd, dict(base, **cfg), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.turn = 6
    g.your_life = 40.0
    g.monarch = False
    for o in g.opponents[1:]:
        o.alive, o.life, o.creatures = False, 0.0, 0.0
    o = g.opponents[0]
    o.life, o.creatures = 40.0, float(len(pool))
    o.body_pool, o.bodies, o.next_body = tuple(pool), [], 0
    o.body_tapped = []
    for n, power in enumerate(mine):
        c = EN.Card(name=f"Y{n}", types=frozenset({"Creature"}),
                    power=power, toughness=power)
        g.board.append(EN.Permanent(card=c, sick=False, tapped=tapped,
                                    base_p=power, base_t=power))
    return g, o


THREE = B(3, 2, False, 3, False, False)


def read(g, rounds=1):
    return round(OPP._predicted_chip(g, rounds), 9)


def run_cases():
    FAIL.clear()
    PASS.clear()

    g, o = game([THREE], you_block=False)
    want = round(OPP.chip_amount(g, o, OPP.chip_share(g, o, [])), 9)
    check("A OFF: the formula", read(g), want)

    g, o = game([THREE])
    check("B ON, no blocker: a 3/3 reads 3", read(g), 3.0)

    g, o = game([THREE], mine=(6,))
    check("C ON, your untapped 6/6 blocks it: reads 0", read(g), 0.0)

    g, o = game([THREE], mine=(6,), tapped=True)
    check("D ON, your 6/6 tapped: reads 3", read(g), 3.0)

    g, o = game([B(3, 2, False, 3, True, False)])
    check("E ON, a utility body never attacks: reads 0", read(g), 0.0)

    g, o = game([THREE])
    grown = min(7.0, 1.0 + 0.7 * o.p["board"])
    check("F ON, two rounds: 3, then 3 scaled by the pod's growth",
          read(g, 2), round(3.0 + 3.0 * grown, 9))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The pilot reads the pod's bodies under A2 (§0z203)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_pred = OPP.predicted_from_bodies

    def flat_rounds(g, rounds=1):
        return real_pred(g, 1) * sum(
            1 for r in range(rounds)
            if OPP.pod_turn(g) + r >= g.cfg.get("first_attack_turn", 3))

    muts = {
        "the read ignores your blockers":
            ({"C"}, OPP, "your_blockers", lambda g: []),
        "utility bodies are read as attackers":
            ({"E"}, OPP, "combat_bodies",
             lambda bodies: list(range(len(bodies)))),
        "the read is the formula":
            ({"B", "C", "D", "E", "F"}, OPP, "predicted_from_bodies",
             lambda g, rounds=1: OPP._formula_chip(g, rounds)),
        "later rounds are not scaled by growth":
            ({"F"}, OPP, "predicted_from_bodies", flat_rounds),
    }
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
