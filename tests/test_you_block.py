#!/usr/bin/env python3
"""A2 of §0z197: you block; the pod declares its attacks (§0z199, queue
item 44; `you_block`, OFF until the batch flips together).

    python -m tests.test_you_block
    python -m tests.test_you_block --mutate   # 10 mutations, exact sets

Under the switch, on `pod_bodies`, an opponent's combat step is a combat
(`opponents.seat_attack`): its untapped combat bodies attack you (at
`pod_attack_rate`, which every case here sets to 1, aimed by `chip_share`,
which is 1 with one opponent alive), it keeps home a body your blocks would
kill at a loss unless the attack kills you (`pod_safe_attack`), and you
block by the same rule as the pod (`plan_blocks`): free kills, trades you
win, safe blocks, chumps under pressure, utility creatures only at lethal.
Rules read: CR 506.4, 508.1f (attacking taps), 509.1a (only untapped
creatures block), 509.1b (flying: blocked by flying or reach, 702.9b,
702.17b), 510.1-510.4, 702.12b (indestructible), 702.15b (lifelink), the
monarch's rule ("whenever a creature deals combat damage to the
monarch..."). Bloodghast's "can't block" is the generated CANT_BLOCK, Verge
Rangers' first strike FIRST_STRIKE, Ancient Greenwarden's reach REACH
(Scryfall, 2026-11-13).

Every case: one opponent alive, you at 40 unless named, a body is (toughness,
mana value, black, power, utility, reach). Your creatures are valued at
`threat_of` (0.8 x power with no `threat`), its bodies at mana value.

CASES
  A  OFF: the formula -- no body attacks, your life falls by `chip_amount`
  B  an unblocked 3/3 body deals you 3, and taps
  C  the POD'S READ: your untapped 6/6 would kill its 3/3 for nothing, so
     it stays home -- no damage, the body alive and untapped
  D  at 3 life the pod's read keeps the 3/3 home too (your 6/6 makes the
     attack not lethal); with the read off (`pod_attack_safety=False`) it
     comes, and your 6/6 kills it
  E  (the read off) your UTILITY 6/6 (a mana creature) does not block at 40
     -- 3 through -- and does at 3, killing the body
  F  a TAPPED 6/6 does not block: 3 through
  G  Bloodghast (here a 6/6) CAN'T BLOCK: 3 through
  H  a FLYING body: your ground 6/6 cannot block it (3 through); Ancient
     Greenwarden (reach, here a 6/6) can, so the body stays home
  I  PRESSURE: at 12 life (floor 10) your 1/1 token chumps a 5/5 body and
     dies, 0 through; at 40 it does not, 5 through
  J  (the read off) YOUR FIRST STRIKE: at 3 life, Verge Rangers (3/3 first
     strike) kills the 3/3 body and lives; a plain 3/3 trades with it
  K  your INDESTRUCTIBLE 2/2 blocks a 5/5 at 3 life and lives (the pod
     sends it: its body does not die)
  L  (the read off) LIFELINK: your 6/6 lifelinker blocks at 3 life, kills
     the body and gains 6 -- you end at 9
  M  the CROWN: an unblocked body takes it; a body your 1/5 blocks does not
  N  a body that ATTACKED is tapped and does not block on your turn: your
     3/3 gets through it (A1 would have free-killed it)
  O  the BRIDGE: `pod_attack_rate` unset is incidental_rate x power x count /
     the combat bodies' power, at most 1
  P  `kill_pod_bodies` keeps the tapped flags beside the bodies

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  your creatures never block (`your_blockers` is [])  -> C, D, E, H, I, J, K, L, M
  utility creatures block like any other             -> E
  an attacking body stays untapped                   -> N
  first strike on your blockers is not read          -> J
  "can't block" is ignored (CANT_BLOCK empty)        -> G
  the pod sends everything (`pod_safe_attack` is identity) -> C, D, H
  lifelink on a block is not gained                  -> L
  the crown does not move on combat damage           -> M
  the bridge is a flat 1                             -> O
  and, not a mutation of A2's own code:
  `kill_pod_bodies` drops the tapped flags' alignment -> P

UNMUTATED (§0z15): A is the OFF path; B, F are what a combat with nothing in
front of it deals, read by the plain run.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import _evasion as EV
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


def game(life=40.0, pool=(), **cfg):
    deck, cmd = RM.build()
    base = dict(DEFAULT_CFG, pod_bodies=True, attacker_deaths=True,
                you_block=True, pod_attack_rate=1.0, block_share=1.0)
    g = EN.Game(list(deck), cmd, dict(base, **cfg), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = life
    g.monarch = False
    for o in g.opponents[1:]:
        o.alive, o.life, o.creatures = False, 0.0, 0.0
    o = g.opponents[0]
    o.life, o.creatures = 40.0, float(len(pool))
    o.body_pool, o.bodies, o.next_body = tuple(pool), [], 0
    o.body_tapped = []
    return g, o


def mine(g, power, tough=None, name=None, tapped=False, **kw):
    c = EN.Card(name=name or f"Y{power}", types=frozenset({"Creature"}),
                power=power, toughness=power if tough is None else tough,
                **kw)
    p = EN.Permanent(card=c, sick=False, tapped=tapped, base_p=c.power,
                     base_t=c.toughness)
    g.board.append(p)
    return p


def body(t, p, mv=2, reach=False, utility=False):
    return B(t, mv, False, p, utility, reach)


def seat(g):
    OPP.chip_damage_seat(g, 0)


THREE = body(3, 3)


def run_cases():
    FAIL.clear()
    PASS.clear()

    g, o = game(pool=[THREE], you_block=False)
    others = []
    want = 40.0 - OPP.chip_amount(g, o, OPP.chip_share(g, o, others))
    seat(g)
    check("A OFF: the formula, no body attacks",
          (round(g.your_life, 6), g.m["pod_attacks"]), (round(want, 6), 0))

    g, o = game(pool=[THREE])
    seat(g)
    check("B an unblocked 3/3 deals 3 and taps",
          (g.your_life, o.body_tapped), (37.0, [True]))

    g, o = game(pool=[THREE])
    mine(g, 6)
    seat(g)
    check("C the pod keeps home a body your 6/6 would kill for nothing",
          (g.your_life, o.creatures, o.body_tapped, g.m["pod_attackers_held"]),
          (40.0, 1.0, [False], 1))

    g, o = game(life=3.0, pool=[THREE])
    mine(g, 6)
    seat(g)
    held = (o.creatures, g.m["pod_attackers_held"])
    g, o = game(life=3.0, pool=[THREE], pod_attack_safety=False)
    y = mine(g, 6)
    seat(g)
    check("D the read keeps it home at 3 too; off, it comes and dies",
          (held, g.your_life, o.creatures, y in g.board),
          ((1.0, 1), 3.0, 0.0, True))

    got = []
    for life in (40.0, 3.0):
        g, o = game(life=life, pool=[THREE], pod_attack_safety=False)
        y = mine(g, 6, mana_ability=(1, frozenset({"G"})))
        seat(g)
        got.append((g.your_life, o.creatures))
    check("E a utility creature blocks only at lethal",
          got, [(37.0, 1.0), (3.0, 0.0)])

    g, o = game(pool=[THREE])
    mine(g, 6, tapped=True)
    seat(g)
    check("F a tapped creature does not block", g.your_life, 37.0)

    g, o = game(pool=[THREE])
    mine(g, 6, name="Bloodghast")
    seat(g)
    check("G Bloodghast can't block", g.your_life, 37.0)

    g, o = game(pool=[body(3, 3, reach=True)])
    mine(g, 6)
    seat(g)
    ground = g.your_life
    g, o = game(pool=[body(3, 3, reach=True)])
    mine(g, 6, name="Ancient Greenwarden")
    seat(g)
    check("H a flier: ground can't block it; reach can, so it stays home",
          (ground, g.your_life, g.m["pod_attackers_held"]), (37.0, 40.0, 1))

    got = []
    for life in (12.0, 40.0):
        g, o = game(life=life, pool=[body(5, 5)])
        y = mine(g, 1)
        y.is_token = True
        seat(g)
        got.append((g.your_life, y in g.board))
    check("I under pressure your token chumps; at 40 it does not",
          got, [(12.0, False), (35.0, True)])

    g, o = game(life=3.0, pool=[THREE], pod_attack_safety=False)
    r = mine(g, 3, name="Verge Rangers")
    seat(g)
    rangers = (r in g.board, o.creatures)
    g, o = game(life=3.0, pool=[THREE], pod_attack_safety=False)
    q = mine(g, 3)
    seat(g)
    check("J your first striker kills its attacker first and lives",
          (rangers, (q in g.board, o.creatures)),
          ((True, 0.0), (False, 0.0)))

    g, o = game(life=3.0, pool=[body(5, 5)])
    k = mine(g, 2, indestructible=True)
    seat(g)
    check("K your indestructible 2/2 blocks a 5/5 and lives",
          (g.your_life, k in g.board), (3.0, True))

    g, o = game(life=3.0, pool=[THREE], pod_attack_safety=False)
    mine(g, 6, lifelink=True)
    seat(g)
    check("L a lifelink blocker gains its damage", g.your_life, 9.0)

    g, o = game(pool=[THREE])
    g.monarch = True
    seat(g)
    lost = not g.monarch
    g, o = game(pool=[THREE])
    g.monarch = True
    mine(g, 1, tough=5)
    seat(g)
    check("M combat damage to you takes the crown; a full block does not",
          (lost, g.monarch), (True, True))

    g, o = game(pool=[body(6, 6)])
    seat(g)
    tapped = list(o.body_tapped)
    a = mine(g, 3)
    dealt = OPP.combat_damage(g, [a])
    check("N a body that attacked does not block on your turn",
          (tapped, dealt, a in g.board), ([True], 3.0, True))

    g, o = game(pool=[THREE], pod_attack_rate=None)
    o.creatures = 2.0
    want = min(1.0, g.cfg["incidental_rate"] * o.p["power"] * 2.0 / 4.0)
    check("O the bridge is rate x power x count / the combat power",
          round(OPP.pod_attack_rate(g, o, 4), 9), round(want, 9))

    g, o = game(pool=[body(1, 1), body(2, 2), body(3, 3)])
    OPP.pod_bodies(g, o)
    o.body_tapped = [True, False, True]
    OPP.kill_pod_bodies(g, o, lambda b: b.toughness == 2)
    check("P killing a body keeps the tapped flags beside the bodies",
          ([b.toughness for b in o.bodies], o.body_tapped),
          ([1, 3], [True, True]))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("A2: you block; the pod declares its attacks (§0z199)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_kill = OPP.kill_pod_bodies

    def unaligned_kill(g, o, dies=None):
        flags = list(o.body_tapped)
        n = real_kill(g, o, dies)
        o.body_tapped = flags[:len(o.bodies)]
        return n

    muts = {
        "your creatures never block":
            ({"C", "D", "E", "H", "I", "J", "K", "L", "M"}, OPP,
             "your_blockers", lambda g: []),
        "utility creatures block like any other":
            ({"E"}, OPP, "your_utility", lambda g, p: False),
        "an attacking body stays untapped":
            ({"N"}, OPP, "body_tapped", lambda o, i: False),
        "first strike on your blockers is not read":
            ({"J"}, OPP, "first_strike_of", lambda g, p: False),
        "can't block is ignored":
            ({"G"}, EV, "CANT_BLOCK", set()),
        "the pod sends everything":
            ({"C", "D", "H"}, OPP, "pod_safe_attack",
             lambda g, sent, plan: sent),
        "lifelink on a block is not gained":
            ({"L"}, OPP, "_your_lifelink", lambda g, n: None),
        "the crown does not move on combat damage":
            ({"M"}, OPP, "crown_on_combat_damage", lambda g, dealt: None),
        "the bridge is a flat 1":
            ({"O"}, OPP, "pod_attack_rate", lambda g, o, p: 1.0),
        "kill_pod_bodies drops the flags' alignment":
            ({"P"}, OPP, "kill_pod_bodies", unaligned_kill),
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
