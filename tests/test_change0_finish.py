#!/usr/bin/env python3
"""Item 24's change 0, finished (§0z135): Storm Cauldron, Angel of Suffering,
and one rule each for Sun Titan and Midnight Reaper.

    python -m tests.test_change0_finish
    python -m tests.test_change0_finish --mutate   # 8 mutations, exact sets

Texts verified against Scryfall 2026-10-14: Storm Cauldron ("Each player may
play an additional land during each of their turns. Whenever a land is
tapped for mana, return it to its owner's hand."), Angel of Suffering ("If
damage would be dealt to you, prevent that damage and mill twice that many
cards."), Sun Titan ("return target permanent card with mana value 3 or
less"), Midnight Reaper ("this creature deals 1 damage to you and you draw
a card").

CASES
  A  Storm Cauldron: one more land drop; none without it
  B  ... a Forest tapped for mana returns to hand once the payment is done;
     a token land is not tapped for mana under it
  C  `storm_cauldron=False`: the Forest stays, tapped
  D  `damage_you`: without the Angel the damage passes; with it nothing
     does and twice it is milled, fractions carried (0.6 + 0.6 mills 2)
  E  the pod's chip damage with the Angel out: life untouched, cards milled
  F  a kill aimed at you: a COMBAT route's is prevented under `pod_threats`
     (no loss, twice your life milled, the clock back next round); a combo
     route's is not; on the default pod it is not
  G  shilgengar's Sun Titan takes the shared pick: a higher-priority card
     over a higher mana value (its own rule took the mana value)
  H  shilgengar's Midnight Reaper with the Angel out: a draw, no life lost
  I  azusa's fetchlands make no mana: a lone Terramorphic Expanse pays
     nothing (it paid a generic before §0z135); `fetch_phantom_mana=True`
     restores the old unit
  J  Cauldron's return is a TRIGGER: a land tapped for mana and then
     sacrificed as part of the same cost is gone when it resolves -- nothing
     returns, nothing raises
  K  a land whose {T} is part of its own activation cannot also pay the
     activation's mana (Cryptic Caves' {1}); `land_pays_own_activation=True`
     restores the old pool

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  Storm Cauldron is never live                   -> A, B
  the lands are never returned                   -> B
  damage_you ignores the Angel                   -> D, E, F, H
  a combat route's kill is never prevented       -> F
  shilgengar's Titan keeps its own rule          -> G
  (added with I, before its run)
  a land that makes no mana offers a unit         -> I
  (added with J and K, before their run)
  the trigger returns lands that left             -> J
  a land pays its own activation                  -> K

UNMUTATED (§0z15): C is the off switch, read by the plain run.
"""
import random
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
from edhmc.decks import azusa_v1 as AM
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def find(module, name):
    deck, cmd = module.build()
    return next(c for c in list(deck) + [cmd] if c.name == name)


def clean(g):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(40)]
    g.turn = 6
    g.your_life = 30.0
    for o in g.opponents:
        o.life, o.creatures, o.alive = 40.0, 3.0, True
    return g


def agame(**cfg):
    deck, cmd = AM.build()
    g = AZ.AzusaGame(list(deck), cmd, dict(DEFAULT_CFG, **cfg), 1)
    return clean(g)


def sgame(**cfg):
    deck, cmd = SM.build()
    g = SH.ShilgengarGame(list(deck), cmd, dict(DEFAULT_CFG, **cfg), 1)
    return clean(g)


def put(g, card, **kw):
    p = EN.Permanent(card=card, sick=False, **kw)
    g.board.append(p)
    return p


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    cauldron = find(AM, "Storm Cauldron")
    forest = find(AM, "Forest")

    g = agame()
    base = g.land_drops_for_turn()
    put(g, cauldron)
    check("A Storm Cauldron: one more land drop", g.land_drops_for_turn() - base, 1)

    g = agame()
    put(g, cauldron)
    put(g, forest)
    tok = put(g, forest, is_token=True)
    paid = g.response_pay({"G": 1})
    g.cauldron_flush()                    # the trigger resolves
    check("B a tapped Forest returns to hand; a token land is not tapped",
          (paid, [c.name for c in g.hand], tok in g.board and not tok.tapped,
           g.land_mana_live(tok)),
          (True, ["Forest"], True, False))

    g = agame(storm_cauldron=False)
    put(g, cauldron)
    land = put(g, forest)
    g.response_pay({"G": 1})
    g.cauldron_flush()
    check("C storm_cauldron=False: the Forest stays, tapped",
          (g.hand, land.tapped), ([], True))

    angel = find(SM, "Angel of Suffering")
    g = sgame()
    without = EN.damage_you(g, 3)
    put(g, angel)
    before = len(g.library)
    out = [EN.damage_you(g, 3), before - len(g.library)]
    out += [EN.damage_you(g, 0.6), EN.damage_you(g, 0.6),
            before - len(g.library)]
    check("D damage_you: passes without the Angel; with it 0, milled 2x",
          (without, out), (3, [0.0, 6, 0.0, 0.0, 8]))

    g = sgame(combat_targeting="open")
    put(g, angel)
    lib = len(g.library)
    OPP.incidental_damage(g)
    check("E the pod's chip damage: life untouched, cards milled",
          (g.your_life, len(g.library) < lib), (30.0, True))

    out = []
    for route, threats in (("combat", True), ("combo", True), (None, False)):
        g = sgame(pod_threats=threats)
        put(g, angel)
        o = g.opponents[0]
        o.route, o.kill_turn, o.clock_fired = route, 6, False
        for other in g.opponents[1:]:
            other.kill_turn = 99
        g.opp_rolls = [[[0.0] * OPP.N_SLOTS for _ in g.opponents]
                       for _ in range(30)]
        lib = len(g.library)
        OPP.resolve_clocks(g)
        out.append((g.result, lib - len(g.library), o.kill_turn))
    check("F a combat route's kill prevented; combo and the default pod not",
          out, [(None, 40, 7), ("loss", 0, 6), ("loss", 0, 6)])

    g = sgame()
    big = EN.Card(name="Big", types=frozenset({"Artifact"}),
                  cost={"gen": 3}, priority=1.0)
    keen = EN.Card(name="Keen", types=frozenset({"Artifact"}),
                   cost={"gen": 1}, priority=9.0)
    g.graveyard = [big, keen]
    g._sun_titan_reanimate()
    check("G shilgengar's Sun Titan: priority before mana value",
          [p.card.name for p in g.board], ["Keen"])

    reaper = find(SM, "Midnight Reaper")
    g = sgame()
    put(g, angel)
    put(g, reaper)
    dead = EN.Permanent(card=EN.Card(name="Dude", types=frozenset({"Creature"}),
                                     power=1, toughness=1), sick=False)
    hand = len(g.hand)
    g.on_creature_death(1, dead)
    check("H Midnight Reaper with the Angel out: a draw, no life lost",
          (len(g.hand) - hand, g.your_life), (1, 30.0))

    out = []
    for phantom in (False, True):
        g = agame(fetch_phantom_mana=phantom)
        put(g, find(AM, "Terramorphic Expanse"))
        out.append(g.response_pay({"gen": 1}, dry=True))
    check("I a fetchland pays nothing; the old phantom unit on request",
          out, [False, True])

    g = agame()
    put(g, cauldron)
    gone = put(g, forest)
    g.response_pay({"G": 1})
    g.board.remove(gone)                  # sacrificed as part of the cost
    g.graveyard.append(gone.card)
    g.cauldron_flush()
    check("J a land sacrificed before the trigger resolves stays gone",
          (g.hand, g.m["cauldron_returns"]), ([], 0))

    out = []
    for own in (False, True):
        g = agame(land_pays_own_activation=own)
        put(g, AM.CRYPTIC_CAVES)
        for _ in range(6):
            put(g, forest, tapped=True)     # lands to count, no mana in them
        g.activations()
        out.append(g.m["caves_cracked"])
    check("K Cryptic Caves cannot pay its own {1}; the old pool could",
          out, [0, 1])

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Item 24's change 0, finished (§0z135)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")

    def old_titan(graveyard, exclude=()):
        pool = [c for c in graveyard if c.is_permanent and float(c.mv) <= 3
                and id(c) not in exclude]
        return max(pool, key=lambda c: c.mv) if pool else None

    def blind_flush(self):
        for p in self.__dict__.pop("cauldron_queue", None) or ():
            self.hand.append(p.card)
            self.m["cauldron_returns"] += 1

    real_mana = AZ.AzusaGame.available_mana

    def phantom_mana(self):
        cfg = self.cfg
        self.cfg = dict(cfg, fetch_phantom_mana=True)
        try:
            return real_mana(self)
        finally:
            self.cfg = cfg

    muts = {
        "Storm Cauldron is never live":
            ({"A", "B"}, AZ.AzusaGame, "cauldron_live", lambda self: False),
        "the lands are never returned":
            ({"B"}, AZ.AzusaGame, "cauldron_flush", lambda self: None),
        "damage_you ignores the Angel":
            ({"D", "E", "F", "H"}, EN, "damage_you", lambda g, n: n),
        "a combat route's kill is never prevented":
            ({"F"}, OPP, "angel_prevents_kill", lambda g, o: False),
        "shilgengar's Titan keeps its own rule":
            ({"G"}, SH, "sun_titan_pick", old_titan),
        "a land that makes no mana offers a unit":
            ({"I"}, AZ.AzusaGame, "available_mana", phantom_mana),
        "the trigger returns lands that left":
            ({"J"}, AZ.AzusaGame, "cauldron_flush", blind_flush),
        "a land pays its own activation":
            ({"K"}, AZ, "backwoods_pool", lambda units, land: units),
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
