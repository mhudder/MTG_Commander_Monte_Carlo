#!/usr/bin/env python3
"""A1 of §0z197: your attackers can die to the pod's blockers (§0z198,
queue item 44; `attacker_deaths`, OFF until the batch flips together).

    python -m tests.test_attacker_deaths
    python -m tests.test_attacker_deaths --mutate   # 8 mutations, exact sets

Under the switch, on `pod_bodies`, each defender EVALUATES its blocks
(`opponents.plan_blocks`): a free kill, a trade it wins on value, a block
its creature survives, and chumps only under pressure -- utility creatures
only when the swing is lethal. A blocker's power is dealt back, a first
striker kills first (510.4), an indestructible attacker lives. The pilot
keeps home an attacker the pod would kill at a loss, unless it buys an
elimination (`opponents.safe_attackers`). Rules read: CR 506.4, 509.1,
510.1-510.4, 702.7b (first strike), 702.12b (indestructible), 702.9b
(flying: a blocker needs flying or reach). Verge Rangers' first strike is
the generated FIRST_STRIKE set (Scryfall keywords, 2026-11-13).

Every case is one opponent alive, `block_share` 1.0 (so the cap is the
board), at 40 life unless named. A body is (toughness, mana value, black,
power, utility, reach); a defender values it at its mana value, and your
attacker at `threat_of` (its `threat`, else 0.8 x power).

CASES
  A  OFF: a 6/6 body in front of a 3/3 -- no block (the old cost-aware
     rule at 40 life), no death of yours, ever
  B  a FREE KILL: a 6/6 body blocks the 3/3 and kills it, and lives; the
     card is in your graveyard
  C  a TRADE it wins on value: a 3/3 body worth 2 trades with a 3/3 worth 5
  D  no trade DOWN: the same 3/3 body worth 4 does not trade with a 3/3
     worth 2 -- the 3 damage goes through
  E  a SAFE BLOCK: a 1/5 body blocks the 3/3, neither dies, nothing through
  F  a UTILITY creature (6/6) does not block at 40, nor at 12 (pressure,
     not lethal); at 3 (lethal) it does, and kills the attacker
  G  FIRST STRIKE: at 3 life, Verge Rangers (3/3 first strike) is chumped by
     a 3/3 body, kills it first and lives; a plain 3/3 trades with it
  H  an INDESTRUCTIBLE 3/3 is safe-blocked by the 6/6 body, not killed
  I  a FLIER: the 6/6 body without reach cannot block it; with reach it
     free-kills it
  J  the PILOT: a 3/3 the pod would free-kill stays home; two 3/3s into
     one 6/6 body at 3 life both go, because the second one kills
  K  your COMMANDER (Rendmaw, 5/5 menace) chumped by two 9-toughness bodies
     at 5 life dies, and goes to the command zone with its tax
  L  the pool under the switch: toughness, mana value and black are the
     switch-off bodies, body for body; power, utility and reach in range

  -- added with the lifelink pilot (§0z201, 2026-11-13) --
  M  `pilot_life_value` 1: a doomed 3/3 lifelinker worth 2 is SENT (its 3
     life is worth 3 >= 2); the same at 0 stays home, and a 3/3 without
     lifelink at 1 stays home. Karlov's hook (`has_lifelink`) reads
     Sorin, Vengeful Bloodlord's team lifelink on a vanilla creature

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  your attackers never die (`_kills` is False)     -> B, C, F, G, I, J, K
                                                      (+ M, §0z201)
  first strike is never read                       -> G
  utility creatures block like any other           -> F
  the defender trades down (every attacker worth 99) -> D (+ M, §0z201)
  a flier is blocked by anything                   -> I
  the pilot sends everything                       -> J (+ M, §0z201)
  indestructible is ignored                        -> H
  (§0z201, written before its run)
  the pilot's life is never counted (`life_worth` 0) -> M

UNMUTATED (§0z15): A is the OFF path, read by the plain run; L is a
property of `roll_body_pools`. Neither is blind to a defect in the plan:
it is what they do not read.
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


def rgame(**cfg):
    deck, cmd = RM.build()
    base = dict(DEFAULT_CFG, pod_bodies=True, attacker_deaths=True,
                block_share=1.0)
    g = EN.Game(list(deck), cmd, dict(base, **cfg), random.Random(1),
                seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    return g


def solo(g, pool, life=40.0):
    for o in g.opponents[1:]:
        o.alive, o.life, o.creatures = False, 0.0, 0.0
    o = g.opponents[0]
    o.life, o.creatures = life, float(len(pool))
    o.body_pool, o.bodies, o.next_body = tuple(pool), [], 0
    return o


def attacker(g, power, tough=None, name=None, threat=0.0, **kw):
    c = EN.Card(name=name or f"A{power}", types=frozenset({"Creature"}),
                power=power, toughness=power if tough is None else tough,
                threat=threat, **kw)
    p = EN.Permanent(card=c, sick=False, base_p=c.power, base_t=c.toughness)
    g.board.append(p)
    return p


def alive(g, p):
    return p in g.board


def fight(pool, life=40.0, **akw):
    """One attacker into `pool`: (dealt, attacker alive, bodies left, g)."""
    cfg = akw.pop("cfg", {})
    g = rgame(**cfg)
    o = solo(g, pool, life)
    a = attacker(g, **akw)
    dealt = OPP.combat_damage(g, [a])
    return dealt, alive(g, a), o.creatures, g


SIX = B(6, 2, False, 6, False, False)


def run_cases():
    FAIL.clear()
    PASS.clear()

    dealt, up, left, g = fight([SIX], power=3, cfg=dict(attacker_deaths=False))
    check("A OFF: no block at 40, and no attacker of yours dies",
          (dealt, up, g.m["attackers_died"]), (3.0, True, 0))

    dealt, up, left, g = fight([SIX], power=3)
    check("B a free kill: the 6/6 kills the 3/3 and lives",
          (dealt, up, left, g.m["pod_block_free"], g.m["attackers_died"],
           [c.name for c in g.graveyard]),
          (0.0, False, 1.0, 1, 1, ["A3"]))

    dealt, up, left, g = fight([B(3, 2, False, 3, False, False)], power=3,
                               threat=5.0)
    check("C a trade it wins on value: both die",
          (dealt, up, left, g.m["pod_block_trade"]), (0.0, False, 0.0, 1))

    dealt, up, left, g = fight([B(3, 4, False, 3, False, False)], power=3,
                               threat=2.0)
    check("D no trade down: the 3 goes through",
          (dealt, up, left), (3.0, True, 1.0))

    dealt, up, left, g = fight([B(5, 1, False, 1, False, False)], power=3)
    check("E a safe block: neither dies, nothing through",
          (dealt, up, left, g.m["pod_block_safe"]), (0.0, True, 1.0, 1))

    util = [B(6, 3, False, 6, True, False)]
    got = []
    for life in (40.0, 12.0, 3.0):
        dealt, up, left, g = fight(util, life=life, power=3)
        got.append((dealt, up))
    check("F a utility creature blocks only at lethal",
          got, [(3.0, True), (3.0, True), (0.0, False)])

    body = [B(3, 1, False, 3, False, False)]
    _d, rangers_up, rangers_left, _g = fight(body, life=3.0, power=3,
                                             name="Verge Rangers",
                                             threat=5.0)
    _d, plain_up, plain_left, _g = fight(body, life=3.0, power=3, threat=5.0)
    check("G first strike: Verge Rangers kills its blocker first and lives",
          (rangers_up, rangers_left, plain_up, plain_left),
          (True, 0.0, False, 0.0))

    dealt, up, left, g = fight([SIX], power=3, indestructible=True)
    check("H an indestructible attacker is blocked, not killed",
          (dealt, up, left), (0.0, True, 1.0))

    d1, up1, _l, _g = fight([SIX], power=3, flying=True)
    d2, up2, _l, _g = fight([B(6, 2, False, 6, False, True)], power=3,
                            flying=True)
    check("I a flier: no reach, no block; reach free-kills it",
          (d1, up1, d2, up2), (3.0, True, 0.0, False))

    g = rgame()
    solo(g, [SIX])
    a = attacker(g, 3)
    first = OPP.hold_back(g, [a])
    kept = g.m["attack_kept_safe"]
    g = rgame()
    solo(g, [SIX], life=3.0)
    a1, a2 = attacker(g, 3, name="X1"), attacker(g, 3, name="X2")
    second = OPP.hold_back(g, [a1, a2])
    check("J the pilot keeps a doomed attacker home, not one that buys a kill",
          (len(first), kept, len(second)), (0, 1, 2))

    g = rgame()
    solo(g, [B(9, 1, False, 9, False, False) for _ in range(2)], life=5.0)
    cmd = EN.Permanent(card=g.commander, sick=False,
                       base_p=g.commander.power, base_t=g.commander.toughness)
    g.board.append(cmd)
    g.commander_cast = True
    tax = g.commander_tax
    OPP.combat_damage(g, [cmd])
    check("K your commander dies in combat and goes to the command zone",
          (alive(g, cmd), g.commander_cast, g.commander_tax - tax,
           g.m["commander_died_in_combat"]), (False, False, 2, 1))

    same, ranged = True, True
    for seed in (1, 77, 5003):
        off = OPP.make_pod(dict(DEFAULT_CFG, pod_bodies=True,
                                attacker_deaths=False, you_block=False),
                           seed)[0]
        on = OPP.make_pod(dict(DEFAULT_CFG, pod_bodies=True,
                               attacker_deaths=True), seed)[0]
        for o_off, o_on in zip(off, on):
            for k in range(40):
                b0, b1 = o_off.body_pool[k], o_on.body_pool[k]
                same &= (b0 == (b1.toughness, b1.mv, b1.black, 0, False,
                                False))
                ranged &= ((0 <= b1.power <= 2) if b1.utility
                           else (1 <= b1.power <= 6))
    check("L under the switch the old fields are the old bodies; power ranged",
          (same, ranged), (True, True))

    got = []
    for value, link in ((1.0, True), (0.0, True), (1.0, False)):
        g = rgame(pilot_life_value=value)
        solo(g, [SIX])
        a = attacker(g, 3, threat=2.0, lifelink=link)
        got.append(len(OPP.hold_back(g, [a])))
    import edhmc.karlov as K
    from edhmc.decks import karlov_v2 as KM
    kd, kc = KM.build()
    kg = K.KarlovGame(list(kd), kc, dict(DEFAULT_CFG), 1)
    kg.board = EN.Board()
    plain = EN.Card(name="Vanilla", types=frozenset({"Creature"}),
                    power=2, toughness=2)
    vp = EN.Permanent(card=plain, sick=False, base_p=2, base_t=2)
    kg.board.append(vp)
    before = OPP.lifelink_of(kg, vp)
    sorin = next(c for c in list(kd) + [v for v in vars(KM).values()
                                        if isinstance(v, EN.Card)]
                 if c.name == "Sorin, Vengeful Bloodlord")
    kg.board.append(EN.Permanent(card=sorin, sick=False))
    check("M a doomed lifelinker goes when its life is worth it; karlov's "
          "hook reads Sorin",
          (got, before, OPP.lifelink_of(kg, vp)), ([1, 0, 0], False, True))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("A1: your attackers can die to blockers (§0z198)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_avail = OPP.available_blockers

    def all_combat(g, defender):
        out, cap = real_avail(g, defender)
        return [b._replace(utility=False) for b in out], cap

    muts = {
        "your attackers never die":
            ({"B", "C", "F", "G", "I", "J", "K", "M"}, OPP, "_kills",
             lambda a, blks: False),
        "first strike is never read":
            ({"G"}, OPP, "first_strike_of", lambda g, p: False),
        "utility creatures block like any other":
            ({"F"}, OPP, "available_blockers", all_combat),
        "the defender trades down":
            ({"D", "M"}, OPP, "threat_of", lambda g, p: 99.0),
        "a flier is blocked by anything":
            ({"I"}, OPP, "flying_of", lambda g, p: False),
        "the pilot sends everything":
            ({"J", "M"}, OPP, "safe_attackers",
             lambda g, attackers: attackers),
        "indestructible is ignored":
            ({"H"}, OPP, "is_hardy", lambda g, p: False),
        "the pilot's life is never counted":
            ({"M"}, OPP, "life_worth", lambda g, a: 0.0),
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
