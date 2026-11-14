#!/usr/bin/env python3
"""The pod's hold-back (§0z202, queue item 44; `pod_hold_back`, OFF until
the batch flips together).

    python -m tests.test_pod_hold_back
    python -m tests.test_pod_hold_back --mutate   # 4 mutations, exact sets

Under A2 a body that attacks stays tapped through your turn (508.1f,
502.3) and does not block (509.1a). Under the switch the opponent asks,
before it attacks, whether your next attack would take it to
`pod_hold_back_pad` (10) or below with those bodies tapped
(`opponents.pod_crack_back`: `damage_through`, A1's evaluated blocks); if
so it keeps home its toughest bodies one at a time until it would not, and
if nothing saves it, attacks with everything (`pod_hold_back`).

Every case: one opponent alive (so every body aims at you),
`pod_attack_rate` 1, A1 and A2 on; your creatures are TAPPED -- they
attacked this turn, so they cannot block its attack now, and they untap
for your next one. Bodies are (toughness, mana value, black, power,
utility, reach).

CASES
  A  OFF: at 14 life, with your 5/5 to come back, its 3/3 attacks anyway:
     you take 3
  B  ON: the same 3/3 stays home (tapped, your 5/5 would take it to 9; home,
     it chumps and it stays at 14), untapped; the crack-back wrote no
     block counter
  C  ON, hopeless: against two 5/5s one 3/3 home cannot save it (14 -> 9),
     so it attacks: you take 3
  D  ON at 40: nothing to fear, it attacks
  E  ON, which stays home: of a 3/3 and a 1/6, the 1/6 (the toughest) stays
     home and blocks your 5/5 safely; the 3/3 attacks

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the pod never holds back                         -> B, E
  the pod keeps its weakest bodies home first      -> E
  a hopeless hold-back keeps everyone home         -> C
  your tapped creatures are left out of the crack-back -> B, E

UNMUTATED (§0z15): A is the OFF path; D is the safe case, read by the plain
run.
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


def game(pool, life=14.0, mine=(5,), **cfg):
    deck, cmd = RM.build()
    base = dict(DEFAULT_CFG, pod_bodies=True, attacker_deaths=True,
                you_block=True, pod_hold_back=True, pod_attack_rate=1.0)
    g = EN.Game(list(deck), cmd, dict(base, **cfg), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    g.monarch = False
    for o in g.opponents[1:]:
        o.alive, o.life, o.creatures = False, 0.0, 0.0
    o = g.opponents[0]
    o.life, o.creatures = life, float(len(pool))
    o.body_pool, o.bodies, o.next_body = tuple(pool), [], 0
    o.body_tapped = []
    for n, power in enumerate(mine):
        c = EN.Card(name=f"Y{n}", types=frozenset({"Creature"}),
                    power=power, toughness=power)
        g.board.append(EN.Permanent(card=c, sick=False, tapped=True,
                                    base_p=power, base_t=power))
    return g, o


def body(t, p):
    return B(t, 2, False, p, False, False)


THREE = body(3, 3)


def blocks_counted(g):
    return sum(v for k, v in g.m.items() if k.startswith("pod_block_"))


def run_cases():
    FAIL.clear()
    PASS.clear()

    g, o = game([THREE], pod_hold_back=False)
    OPP.chip_damage_seat(g, 0)
    check("A OFF: it attacks into your crack-back", g.your_life, 37.0)

    g, o = game([THREE])
    OPP.chip_damage_seat(g, 0)
    check("B ON: the 3/3 stays home, untapped; the crack-back counted nothing",
          (g.your_life, o.body_tapped, g.m["pod_held_back"],
           blocks_counted(g)), (40.0, [False], 1, 0))

    g, o = game([THREE], mine=(5, 5))
    OPP.chip_damage_seat(g, 0)
    check("C ON, hopeless: nothing kept home saves it, so it attacks",
          (g.your_life, g.m["pod_held_back"]), (37.0, 0))

    g, o = game([THREE], life=40.0)
    OPP.chip_damage_seat(g, 0)
    check("D ON at 40: it attacks", g.your_life, 37.0)

    g, o = game([THREE, body(6, 1)])
    OPP.chip_damage_seat(g, 0)
    check("E ON: the toughest stays home; the 3/3 attacks",
          (g.your_life, o.body_tapped, g.m["pod_held_back"]),
          (37.0, [True, False], 1))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The pod's hold-back (§0z202)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.pod_hold_back

    def hopeless_home(g, opp, bodies, ks):
        home = real(g, opp, bodies, ks)
        if home:
            return home
        pad = g.cfg.get("pod_hold_back_pad", g.cfg.get("hold_back_pad", 10))
        if opp.life - OPP.pod_crack_back(g, opp, bodies, ks) > pad:
            return set()
        return set(ks)

    def untapped_only(g):
        return [p for p in g.board
                if OPP.is_creature_now(g, p) and not p.tapped]

    muts = {
        "the pod never holds back":
            ({"B", "E"}, OPP, "pod_hold_back", lambda g, o, b, ks: set()),
        "the pod keeps its weakest bodies home first":
            ({"E"}, OPP, "pod_keep_order",
             lambda bodies, ks: sorted(ks, key=lambda k: (
                 bodies[k].toughness, bodies[k].power, k))),
        "a hopeless hold-back keeps everyone home":
            ({"C"}, OPP, "pod_hold_back", hopeless_home),
        "your tapped creatures are left out of the crack-back":
            ({"B", "E"}, OPP, "your_next_attackers", untapped_only),
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
