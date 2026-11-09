#!/usr/bin/env python3
"""§0z189: the pod's crack-back read in main phase 1 with your coming attack
tapped (`opponents.planned_attack`, `crack_back_planned`).

    python -m tests.test_planned_crack_back
    python -m tests.test_planned_crack_back --mutate   # 5 mutations, exact sets

The pod's turns read your board as your turn left it (§0z186): an attacker
tapped in combat does not block. Read BEFORE combat -- Bolas's Citadel's dig
floor (§0z161) -- every creature about to attack counted as a blocker, and
the floor read low. Karlov declares its attack (`KarlovGame.
planned_attackers`, the list `combat` starts from) and `combat_declared`
(cleared in the untap step, set as combat begins, before its hold-back).

CASES
  A  main 1, one attacker: the read with the attack planned is higher than
     `crack_back_planned=False`'s
  B  NEIGHBOUR: combat declared: the read is the old one
  C  NEIGHBOUR: a VIGILANT attacker stays a blocker: the old read
  D  NEIGHBOUR: inside the pod's round (`pod_seat` set): the old read
  E  the read puts back the tapped flags and every count, and counts itself
     (`crack_back_planned` +1)
  F  the planned attack is the hold-back's: with a lethal crack-back the
     weakest attacker stays home and is not tapped for the read (at
     `hold_back_pad=0`, whose thresholds its life total sits between)
  G  NEIGHBOUR: `untapped_blockers=False`: no planned attack
  H  NEIGHBOUR: an engine with no hook (rendmaw): no planned attack
  I  karlov's combat sets `combat_declared` before its hold-back
  J  karlov's untap step clears it

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  crack_back_planned=False everywhere          -> A, E, F
  KarlovGame.planned_attackers returns []      -> A, E, F
  combat_declared can never be set (False)     -> B, I
  OPP.hold_back sends every attacker           -> F
  OPP.vigilant is always False                 -> C

UNMUTATED (§0z15): D, G and H are neighbours already on the old side; J's
flag is written by take_turn, which no mutation here touches. The second
mutation leaves I standing: `combat` still calls the hold-back, with nobody.
"""
import sys

import edhmc.engine as E
import edhmc.karlov as K
import edhmc.opponents as OPP
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
KARLOV = build_pending("karlov")
REND = build_pending("rendmaw")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**kw):
    return dict(DEFAULT_CFG, watch=frozenset(), **{**EXTRA_CFG, **kw})


def body(power=2, name="Bear", vigilance=False):
    c = Card(name=name, types=frozenset({"Creature"}), power=power,
             toughness=2, vigilance=vigilance)
    return Permanent(card=c, sick=False, base_p=power, base_t=2)


def game(*bodies, declared=False, **kw):
    """A karlov main phase 1 (pod turn 5, opponents with seven creatures and
    no kill), your board `bodies`."""
    lst, cmd = KARLOV
    g = K.KarlovGame(list(lst), cmd, cfg(**kw), 3)
    g.opening_hand()
    g.board = E.Board()
    g.turn = 5
    g.your_life = 1e6
    for o in g.opponents:
        o.kill_turn, o.life, o.creatures = 99, 1e9, 7.0
    g.board.extend(bodies)
    g.combat_declared = declared
    return g


def read(g):
    return round(OPP.predicted_chip(g), 9)


def old_read(*bodies, **kw):
    return read(game(*bodies, crack_back_planned=False, **kw))


def lethal_split():
    """Two attackers (power 1 and 5) and a life total between the crack-back
    with both tapped and with only the strong one tapped."""
    one, five = body(1, name="One"), body(5, name="Five")
    g = game(one, five, crack_back_planned=False, hold_back_pad=0.0)

    def tapped(*ps):
        for p in ps:
            p.tapped = True
        try:
            return OPP.predicted_chip(g)
        finally:
            for p in ps:
                p.tapped = False
    life = (tapped(one, five) + tapped(five)) / 2.0
    g = game(one, five, hold_back_pad=0.0)     # pad 0's thresholds, §0z191
    g.your_life = life
    return g, one, five


def run_cases():
    PASS.clear()
    FAIL.clear()

    a = read(game(body()))
    off = old_read(body())
    check("A main 1: the planned attack reads higher", a > off, True)
    check("B combat declared: the old read",
          read(game(body(), declared=True)), off)
    check("C a vigilant attacker stays a blocker",
          read(game(body(vigilance=True))), old_read(body(vigilance=True)))
    g = game(body())
    g.pod_seat = 0
    check("D inside the pod's round: the old read", read(g), off)

    b = body()
    g = game(b)
    before = dict(g.m)
    OPP.predicted_chip(g)
    after = dict(g.m)
    planned = after.pop("crack_back_planned", 0)
    before.pop("crack_back_planned", None)
    check("E flags and counts put back, the read counted",
          (b.tapped, after == before, planned), (False, True, 1))

    g, one, five = lethal_split()
    send = OPP.planned_attack(g)
    check("F the hold-back's attack: the weakest stays home",
          [p.card.name for p in send or ()], ["Five"])

    check("G untapped_blockers=False: no planned attack",
          OPP.planned_attack(game(body(), untapped_blockers=False)), None)
    lst, cmd = REND
    rg = E.Game(list(lst), cmd, cfg(), E.make_rng(3, cfg()), seed_for_pod=3)
    rg.opening_hand()
    rg.board = E.Board([body()])
    check("H no hook (rendmaw): no planned attack",
          OPP.planned_attack(rg), None)

    g = game(body())
    seen = []
    real = OPP.hold_back

    def spy(gg, attackers):
        seen.append(gg.combat_declared)
        return real(gg, attackers)
    OPP.hold_back = spy
    try:
        K.combat(g)
    finally:
        OPP.hold_back = real
    check("I combat declares before its hold-back", seen, [True])

    g = game(body(), declared=True)
    flags = []
    real_up = K.upkeep

    def up(gg):
        flags.append(gg.combat_declared)
        return real_up(gg)
    K.upkeep = up
    try:
        K.take_turn(g)
    finally:
        K.upkeep = real_up
    check("J the untap step clears it", flags[:1], [False])
    return set(FAIL)


class _NeverSet:
    def __get__(self, obj, cls):
        return False

    def __set__(self, obj, value):
        pass


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z189: the crack-back read in main 1 with the attack "
              "planned\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "crack_back_planned=False everywhere":
            ({"A", "E", "F"}, None, {"crack_back_planned": False}),
        "KarlovGame.planned_attackers returns []":
            ({"A", "E", "F"}, (K.KarlovGame, "planned_attackers",
                               lambda self: []), {}),
        "combat_declared can never be set (False)":
            ({"B", "I"}, (K.KarlovGame, "combat_declared", _NeverSet()), {}),
        "OPP.hold_back sends every attacker":
            ({"F"}, (OPP, "hold_back", lambda g, attackers: attackers), {}),
        "OPP.vigilant is always False":
            ({"C"}, (OPP, "vigilant", lambda g, p: False), {}),
    }
    bad = 0
    for label, (want, patch, extra) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = extra
        if patch:
            owner, name, fn = patch
            real = owner.__dict__[name] if isinstance(owner, type) \
                else getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
                setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
