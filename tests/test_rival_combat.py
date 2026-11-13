#!/usr/bin/env python3
"""A4 of §0z197: rivals lose life to each other (§0z200, queue items 44/45;
`rival_combat`, OFF until the batch flips together).

    python -m tests.test_rival_combat
    python -m tests.test_rival_combat --mutate   # 7 mutations, exact sets

Under the switch, on A2's combat (`you_block`), a body whose aim roll does
not pick you attacks a rival chosen by openness (`opponents.rival_target`,
from the same roll). The rival blocks with its untapped bodies by the pod's
rule, the attacker reads those blocks first (`pod_safe_attack` at the
rival's life), the unblocked power is life loss (`life_loss`: Selenia's
Curse doubles it), "whenever an opponent loses life" hears it
(`lost_life`), and dead bodies on both sides die as events. Rules read: CR
120.3a (damage to a player is life loss), 506.4, 509.1a, 510.1-510.2,
704.5a (a player at 0 life loses).

Every case: opponent 0 attacks, opponent 1 is the rival, opponent 2 is
dead; `pod_attack_rate` 1 and every body aimed away from you (the share at
you patched to 0), so each combat body of opponent 0 attacks opponent 1.
Bodies are (toughness, mana value, black, power, utility, reach).

CASES
  A  OFF: the body aimed at the rival goes nowhere -- the rival stays at 40
  B  a 3/3 at an open rival: 3 life lost, the attacker taps, you untouched
  C  the rival's untapped 6/6 would kill it for nothing: it stays home
  D  the rival's TAPPED 6/6 does not block: 3 lost
  E  a rival at 3 is eliminated by it
  G  "whenever an opponent loses life" hears the rival's loss
  H  Selenia's Curse on the rival doubles it: 6 lost
  I  the rival is picked by openness: an empty board at 0.5, the board of
     three at 0.9 (weights 1 and 1/4)
  J  under pressure (12 life, floor 10) the rival's 1/1 chumps a 5/5 and
     dies; no life lost
  K  at 3 life the attacker's read keeps its 3/3 home (the rival's 3/3
     trades with it, and a trade it chose is one it loses); with the read
     off (`pod_attack_safety=False`) it comes, the rival's 3/3 worth 1
     trades with the 3/3 worth 2, both bodies die, the rival lives

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  an attack at a rival goes nowhere      -> B, C, D, E, G, H, J, K
  the rival's tapped bodies block        -> D
  the attacker sends everything          -> C, K
  a rival's life loss is unheard         -> G
  rivals are chosen evenly               -> I
  the curse is ignored on a rival        -> H
  bodies that die in combat do not die   -> J, K

  * THE FIRST RUN FOUND TWO WRONG CASES, not wrong code: E's kill counter
    read `living`, which already leaves out a player at 0 (the code's
    counter was fixed), and K expected an attack the attacker's read
    rightly refuses (the case now pins both). "the attacker sends
    everything" gained K when K was rewritten, after that first run: a
    revision, not a prediction (§0z14).

UNMUTATED (§0z15): A is the OFF path, read by the plain run.
"""
import random
import sys
from contextlib import contextmanager

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


@contextmanager
def aimed_away():
    """Every body's aim roll misses you: the share at you is 0."""
    real = OPP.chip_share
    OPP.chip_share = lambda g, opp, others: 0.0
    try:
        yield
    finally:
        OPP.chip_share = real


def game(attackers, rival=(), rival_life=40.0, **cfg):
    deck, cmd = RM.build()
    base = dict(DEFAULT_CFG, pod_bodies=True, attacker_deaths=True,
                you_block=True, rival_combat=True, pod_attack_rate=1.0)
    g = EN.Game(list(deck), cmd, dict(base, **cfg), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    g.monarch = False
    a, r, dead = g.opponents
    dead.alive, dead.life, dead.creatures = False, 0.0, 0.0
    for o, pool, life in ((a, attackers, 40.0), (r, rival, rival_life)):
        o.alive, o.life, o.creatures = True, life, float(len(pool))
        o.body_pool, o.bodies, o.next_body = tuple(pool), [], 0
        o.body_tapped = []
        o.goaded_birds = 0.0
    return g, a, r


def body(t, p, mv=2, utility=False):
    return B(t, mv, False, p, utility, False)


THREE = body(3, 3)


def seat(g):
    with aimed_away():
        OPP.chip_damage_seat(g, 0)


def run_cases():
    FAIL.clear()
    PASS.clear()

    g, a, r = game([THREE], rival_combat=False)
    seat(g)
    check("A OFF: an attack at a rival goes nowhere", r.life, 40.0)

    g, a, r = game([THREE])
    seat(g)
    check("B a 3/3 at an open rival: 3 lost, it taps, you untouched",
          (r.life, a.body_tapped, g.your_life), (37.0, [True], 40.0))

    g, a, r = game([THREE], rival=[body(6, 6)])
    seat(g)
    check("C the rival's 6/6 would kill it for nothing: it stays home",
          (r.life, a.body_tapped, g.m["rival_attackers_held"]),
          (40.0, [False], 1))

    g, a, r = game([THREE], rival=[body(6, 6)])
    OPP.pod_bodies(g, r)
    r.body_tapped = [True]
    seat(g)
    check("D the rival's tapped 6/6 does not block", r.life, 37.0)

    g, a, r = game([THREE], rival_life=3.0)
    seat(g)
    check("E a rival at 3 is eliminated",
          (r.alive, g.m["rival_combat_kills"]), (False, 1))

    g, a, r = game([THREE])
    heard = []
    g.on_opponent_lost_life = lambda o, n: heard.append((o is r, n))
    seat(g)
    check("G 'whenever an opponent loses life' hears it", heard, [(True, 3.0)])

    g, a, r = game([THREE])
    r.cursed = True
    seat(g)
    check("H Selenia's Curse doubles a rival's loss", r.life, 34.0)

    g, a, r = game([THREE])
    o1, o2 = r, g.opponents[2]
    o1.creatures, o2.creatures = 0.0, 3.0
    picks = (OPP.rival_target(g, [o1, o2], 0.5) is o1,
             OPP.rival_target(g, [o1, o2], 0.9) is o2)
    check("I the rival is picked by openness", picks, (True, True))

    g, a, r = game([body(5, 5)], rival=[body(1, 1)], rival_life=12.0)
    seat(g)
    check("J under pressure the rival's 1/1 chumps and dies",
          (r.life, r.creatures), (12.0, 0.0))

    g, a, r = game([THREE], rival=[body(3, 3, mv=1)], rival_life=3.0)
    seat(g)
    read = (g.m["rival_attackers_held"], a.creatures)
    g, a, r = game([THREE], rival=[body(3, 3, mv=1)], rival_life=3.0,
                   pod_attack_safety=False)
    seat(g)
    check("K the read keeps it home; off, both bodies die in a trade",
          (read, r.life, r.alive, r.creatures, a.creatures),
          ((1, 1.0), 3.0, True, 0.0, 0.0))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("A4: rivals lose life to each other (§0z200)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "an attack at a rival goes nowhere":
            ({"B", "C", "D", "E", "G", "H", "J", "K"}, OPP, "_attack_rival",
             lambda g, opp, bodies, rival, ks, dead: 0.0),
        "the rival's tapped bodies block":
            ({"D"}, OPP, "body_tapped", lambda o, i: False),
        "the attacker sends everything":
            ({"C", "K"}, OPP, "pod_safe_attack",
             lambda g, sent, plan, life=None: sent),
        "a rival's life loss is unheard":
            ({"G"}, OPP, "lost_life", lambda g, losses: None),
        "rivals are chosen evenly":
            ({"I"}, OPP, "rival_target",
             lambda g, others, u: others[int(u * len(others))]),
        "the curse is ignored on a rival":
            ({"H"}, OPP, "life_loss", lambda o, n: n),
        "bodies that die in combat do not die":
            ({"J", "K"}, OPP, "kill_pod_bodies",
             lambda g, o, dies=None: 0),
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
