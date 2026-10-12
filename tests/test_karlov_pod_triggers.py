#!/usr/bin/env python3
"""The owner's 2026-10-12 karlov batch (§0z128): five cards whose value is
the POD's actions turned into lifegain events, or a lifegain event turned
into the pod's life loss.

    python -m tests.test_karlov_pod_triggers
    python -m tests.test_karlov_pod_triggers --mutate   # 10 mutations

    South Wind Avatar {3}{B} 3/4   (Scryfall, every text verified 2026-10-12)
    Deathtouch / Whenever another creature you control dies, you gain life
    equal to its toughness. / Whenever you gain life, each opponent loses 1
    life.
    Epicure of Blood {4}{B} 4/4
    Whenever you gain life, each opponent loses 1 life.
    Polluted Bonds {3}{B}{B} Enchantment
    Whenever a land an opponent controls enters, that player loses 2 life
    and you gain 2 life.
    Forbidden Orchard  Land
    {T}: Add one mana of any color. / Whenever you tap this land for mana,
    target opponent creates a 1/1 colorless Spirit creature token.
    Slaughter Specialist {1}{B} 3/3
    When this creature enters, each opponent creates a 1/1 white Human
    creature token. / Whenever a creature an opponent controls dies, put a
    +1/+1 counter on this creature.  (the second sentence is NOT modelled)

CASES
  A  South Wind Avatar: one lifegain event, each opponent loses 1
  B  Epicure of Blood: the same
  C  Avatar + Exquisite Blood: the drain loop wins (win_route 5)
  D  Epicure + Exquisite Blood: the same
  E  another creature of yours dies (a 2/4): the Avatar gains 4
  F  the Avatar's OWN death gains nothing ("another")
  G  the toughness is the dying permanent's, counters included (1/1 +2 -> 3)
  H  Polluted Bonds in round 6: each of three opponents loses 2, you gain 2
     three times (three events)
  I  in round 9, past `opp_land_plateau` (8): nothing
  J  a dead opponent makes no land drop: two triggers, not three
  K  an Orchard tapped by `spend_lg` gives a Spirit; Soul Warden gains 1
  L  the Spirit goes to the LEAST threatening opponent (Offering's choice)
  M  an Orchard untapped at end of turn is tapped for its trigger when a
     payoff (Soul Warden) is out
  N  ... and NOT tapped with no payoff out
  O  ... and NOT tapped under `orchard_idle_tap=False`
  P  Slaughter Specialist resolving: each living opponent +1 creature
  R  ... and Authority of the Consuls sees three creatures enter (3 events)
  Q  OPP_ETB_PAYOFFS is exactly the set of cards, in karlov's list and its
     catalog, for which `creature_entered(mine=False)` changes a life total
     (§0q: a hand-maintained set, derived and checked)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  DRAIN_ON_GAIN without the two candidates   -> C, D
     (the drain still kills the table by recursion, by a route that is not
     the loop's -- `win_route` is what tells them apart)
  the death clause reads toughness 1         -> E, G
  `watching` ignores "another"               -> F
  the pod is always in round 1 (no plateau)  -> I
  Polluted Bonds drains ONE opponent         -> H, J
  the Orchard's trigger is missing           -> K, L, M
  the Spirit goes to the MOST threatening    -> L
  OPP_ETB_PAYOFFS is empty                   -> M, Q
  OPP_ETB_PAYOFFS loses Authority            -> Q
  the Specialist's ETB is missing            -> P, R

UNMUTATED, and written down (§0z15): A and B are the inline branch of
`gain_life`, with no seam to swap. O is a knob read, not a branch. N's gate
is mutated only through the empty-set case, which breaks M rather than N --
a gate that is always closed is not one that is always open.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
from edhmc.decks import karlov_v2 as KM
from edhmc.experiment import DEFAULT_CFG
from edhmc.ledger.karlov import CATALOG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


KDECK, KCMD = KM.build()
FILLER = [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                  cost={"gen": 1}) for i in range(30)]


def kcard(name):
    return next(c for c in KDECK if c.name == name)


def kgame(*cards, turn=6, **cfg):
    g = K.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20, **cfg), 4242)
    g.board = EN.Board()
    g.hand = []
    g.library = list(FILLER)
    g.your_life = 40.0
    g.turn = turn
    for i, o in enumerate(g.opponents):
        o.creatures = float(2 + i)              # 2, 3, 4
        o.life = 40.0
        o._pcache = dict(o.p, board=1.0 + i)    # threat rises with i
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def olives(g):
    return [o.life for o in g.opponents]


def creature(name, p, t, counters=0):
    c = EN.Card(name=name, types=frozenset({"Creature"}), power=p, toughness=t)
    return EN.Permanent(card=c, sick=False, counters=counters)


def dies(g, perm):
    g.board.remove(perm)
    g.on_creature_death(1, perm)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # -- the two "each opponent loses 1" cards --------------------------------
    g = kgame(KM.SOUTH_WIND_AVATAR)
    K.gain_life(g, 1)
    check("A Avatar: each opponent loses 1",
          (olives(g), g.m["southwind_drains"]), ([39.0] * 3, 1))
    g = kgame(KM.EPICURE_OF_BLOOD)
    K.gain_life(g, 1)
    check("B Epicure: each opponent loses 1",
          (olives(g), g.m["epicure_drains"]), ([39.0] * 3, 1))
    g = kgame(KM.SOUTH_WIND_AVATAR, kcard("Exquisite Blood"))
    K.gain_life(g, 1)
    check("C Avatar + Exquisite Blood: the drain loop wins",
          (g.result, g.m["win_route"]), ("win", 5))
    g = kgame(KM.EPICURE_OF_BLOOD, kcard("Exquisite Blood"))
    K.gain_life(g, 1)
    check("D Epicure + Exquisite Blood: the drain loop wins",
          (g.result, g.m["win_route"]), ("win", 5))

    # -- South Wind Avatar's death clause -------------------------------------
    g = kgame(KM.SOUTH_WIND_AVATAR)
    vamp = creature("Some Vampire", 2, 4)
    g.board.append(vamp)
    dies(g, vamp)
    check("E another creature (2/4) dies: gain 4",
          (g.your_life, g.m["southwind_death_gains"]), (44.0, 1))
    g = kgame(KM.SOUTH_WIND_AVATAR)
    dies(g, g.board[0])
    check("F the Avatar's own death gains nothing",
          (g.your_life, g.m["southwind_death_gains"]), (40.0, 0))
    g = kgame(KM.SOUTH_WIND_AVATAR)
    tok = creature("Some token", 1, 1, counters=2)
    g.board.append(tok)
    dies(g, tok)
    check("G toughness with counters: 1/1 +2 gains 3",
          g.your_life, 43.0)

    # -- Polluted Bonds --------------------------------------------------------
    g = kgame(KM.POLLUTED_BONDS)
    K.polluted_bonds(g)
    check("H round 6: three opponents lose 2, three events of 2",
          (olives(g), g.your_life, g.m["lifegain_triggers"],
           g.m["bonds_triggers"]), ([38.0] * 3, 46.0, 3, 3))
    g = kgame(KM.POLLUTED_BONDS, turn=9)
    K.polluted_bonds(g)
    check("I round 9, past the plateau: nothing",
          (olives(g), g.m["bonds_triggers"]), ([40.0] * 3, 0))
    g = kgame(KM.POLLUTED_BONDS)
    g.opponents[2].alive = False
    g.opponents[2].life = 0.0
    K.polluted_bonds(g)
    check("J a dead opponent makes no drop: two triggers",
          g.m["bonds_triggers"], 2)

    # -- Forbidden Orchard -----------------------------------------------------
    g = kgame(kcard("Soul Warden"))
    orchard = EN.Permanent(card=KM.FORBIDDEN_ORCHARD, sick=False)
    g.board.append(orchard)
    units = EN.available_mana(g)
    K.spend_lg(g, EN.can_pay({"W": 1}, units), units)
    check("K a paid tap: one Spirit, Soul Warden gains 1",
          (orchard.tapped, g.m["orchard_spirits"], g.your_life),
          (True, 1, 41.0))
    check("L the Spirit goes to the least threatening opponent",
          [o.creatures for o in g.opponents], [3.0, 3.0, 4.0])
    g = kgame(kcard("Soul Warden"), KM.FORBIDDEN_ORCHARD)
    K.orchard_idle_tap(g)
    check("M idle tap with a payoff out: one Spirit",
          (g.m["orchard_idle_taps"], g.m["orchard_spirits"], g.your_life),
          (1, 1, 41.0))
    g = kgame(KM.FORBIDDEN_ORCHARD)
    K.orchard_idle_tap(g)
    check("N no payoff out: not tapped",
          (g.m["orchard_idle_taps"], g.board[0].tapped), (0, False))
    g = kgame(kcard("Soul Warden"), KM.FORBIDDEN_ORCHARD,
              orchard_idle_tap=False)
    K.orchard_idle_tap(g)
    check("O orchard_idle_tap=False: not tapped",
          g.m["orchard_idle_taps"], 0)

    # -- Slaughter Specialist --------------------------------------------------
    g = kgame()
    K.resolve(g, KM.SLAUGHTER_SPECIALIST)
    check("P each opponent gets a creature",
          ([o.creatures for o in g.opponents], g.m["specialist_tokens"]),
          ([3.0, 4.0, 5.0], 3))
    g = kgame(kcard("Authority of the Consuls"))
    K.resolve(g, KM.SLAUGHTER_SPECIALIST)
    check("R Authority sees three creatures enter",
          (g.your_life, g.m["lifegain_triggers"]), (43.0, 3))

    # -- OPP_ETB_PAYOFFS, derived ----------------------------------------------
    pool = {c.name: c for c in KDECK}
    pool.update(CATALOG[1])
    pays = set()
    for name, card in sorted(pool.items()):
        if card.is_land:
            continue
        g = kgame(card)
        before = (g.your_life, olives(g))
        K.creature_entered(g, mine=False)
        if (g.your_life, olives(g)) != before:
            pays.add(name)
    check("Q OPP_ETB_PAYOFFS is what creature_entered pays for",
          sorted(set(K.OPP_ETB_PAYOFFS)), sorted(pays))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("South Wind Avatar, Epicure of Blood, Polluted Bonds, "
              "Forbidden Orchard, Slaughter Specialist\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_watching = OPP.watching

    def most_threatening(g):
        return max(OPP.living(g), key=lambda o: OPP.opponent_threat(o, g.turn))

    def bonds_one(g):
        if g.has("Polluted Bonds") and OPP.pod_turn(g) <= 8:
            g.m["bonds_triggers"] += 1
            K.drain(g, 2)

    muts = {
        "DRAIN_ON_GAIN without the two candidates":
            ({"C", "D"}, K, "DRAIN_ON_GAIN",
             tuple(n for n in K.DRAIN_ON_GAIN
                   if n not in ("South Wind Avatar", "Epicure of Blood"))),
        "the death clause reads toughness 1":
            ({"E", "G"}, K.KarlovGame, "toughness_of", lambda self, p: 1),
        "watching ignores 'another'":
            ({"F"}, OPP, "watching",
             lambda g, name, perm=None, another=False:
                 real_watching(g, name, perm, False)),
        "the pod is always in round 1":
            ({"I"}, OPP, "pod_turn", lambda g: 1),
        "Polluted Bonds drains one opponent":
            ({"H", "J"}, K, "polluted_bonds", bonds_one),
        "the Orchard's trigger is missing":
            ({"K", "L", "M"}, K, "orchard_tapped", lambda g: None),
        "the Spirit goes to the most threatening":
            ({"L"}, K, "offering_token_target", most_threatening),
        "OPP_ETB_PAYOFFS is empty":
            ({"M", "Q"}, K, "OPP_ETB_PAYOFFS", ()),
        "OPP_ETB_PAYOFFS loses Authority":
            ({"Q"}, K, "OPP_ETB_PAYOFFS",
             tuple(n for n in K.OPP_ETB_PAYOFFS
                   if n != "Authority of the Consuls")),
        "the Specialist's ETB is missing":
            ({"P", "R"}, K, "slaughter_specialist_etb", lambda g: None),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
