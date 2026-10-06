#!/usr/bin/env python3
"""Pin the land candidates of §0z113 (2026-10-06).

    python -m tests.test_land_candidates
    python -m tests.test_land_candidates --mutate   # 7 mutations, exact sets

Every land here was proposed with its oracle text from Scryfall
(`edhmc/pending.py`, "LAND CANDIDATES"). One case per clause the engine
models, on a constructed board:

CASES
  A  Ancient Tomb offers two {C}                        (engine, shared)
  B  tapping Ancient Tomb deals 2 damage to you
  C  paying {1} with the Tomb and a Forest taps the Forest -- the Tomb hurts,
     so it is the land a pilot taps last, even where the colour-surplus rule
     reads its two {C} as the most plentiful colour
  D  Gaea's Cradle offers one {G} per creature you control (three)
  E  ... and nothing with no creatures
  F  the count-based `spend` fallback taps the Cradle ONCE for its three
     (§0z4: a mana amount said in `available_mana` and not in `spend` is
     not modelled)
  G  karlov: Scoured Barrens played from hand gains 1 life
  H  shilgengar: Scoured Barrens played from hand gains 1 life
  I  lorehold: Command Beacon at tax 4 casts the commander from hand at its
     base cost, the Beacon is gone, and the tax nets back on the next death
  J  ... and is not sacrificed at tax 2 (`beacon_min_tax` 4)
  K  tivit: Treasure Vault with eight spare mana makes four Treasures and
     leaves the battlefield
  L  ... and Treasures do not pay for it: four lands and four Treasures
     leave it uncracked
  M  azusa: Evolving Wilds fetches a Forest TAPPED
  N  azusa: Fabled Passage's Forest untaps with four lands, and not with two
  O  azusa: Myriad Landscape pays {2}, fetches two Forests tapped, two
     landfalls
  P  azusa: Field of the Dead makes a Zombie at seven land names, not six
  Q  azusa: Evolving Wilds PLAYED from hand is cracked (the land step's
     dispatch, not the crack itself)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  named_land_mana says nothing (every land makes 1)   -> A, D, E, F
  tap_reluctance forgets the Tomb                     -> C
  can_pay ranks colour surplus ahead of pain           -> C
  charge_life_costs = False                           -> B
  beacon_min_tax = 99                                 -> I
  shilgengar's land hook does nothing                 -> H
  FETCH_SCRIPTS is the true fetches only              -> Q

TWO THINGS WERE WRONG ON THE FIRST RUN, recorded rather than edited away.
C failed UNMUTATED: on a Tomb-and-Forest board `can_pay`'s colour-surplus
rule read the Tomb's two {C} as the most plentiful colour and spent it, for 2
life and a wasted {C}, on a {1} the Forest could pay -- the reluctance rank was
only a tie-break. Pain now leads the generic key (`PAINFUL_RANK`). And the
first "surplus ahead of pain" mutation broke nothing, because it moved the one
constant both `tap_reluctance` and `can_pay` read; the mutation now keeps the
Tomb's rank and blinds only `can_pay`.

UNMUTATED (§0z15): G is karlov's existing land-lifegain hook (Radiant
Fountain's, pinned by its use since 2026-09); J, K, L, M, N, O, P are each the
card's own lines with no seam a mutation could separate from the case.
"""
import random
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LO
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
import edhmc.tivit as TI
from edhmc.decks import azusa_v1 as AM
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import lorehold_v16 as LM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import shilgengar_v1 as SM
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}

RDECK, RCMD = RM.build()
KDECK, KCMD = KM.build()
SDECK, SCMD = SM.build()
LDECK, LCMD = LM.build()
TDECK, TCMD = TM.build()
ADECK, ACMD = AM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(name, produces):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset(produces))


def body(name):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=2,
                   toughness=2, cost={"gen": 2})


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, **CFG, **kw)


def rgame(*cards, **kw):
    g = EN.Game(list(RDECK), RCMD, cfg(**kw), random.Random(1),
                seed_for_pod=1)
    g.board, g.hand, g.graveyard = EN.Board(), [], []
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def azgame():
    g = AZ.AzusaGame(list(ADECK), ACMD, cfg(), 1234)
    g.board, g.hand, g.graveyard = EN.Board(), [], []
    g.library = [body(f"L{i}") for i in range(10)] + [
        land("Forest", "G") for _ in range(6)]
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    # ---- the shared engine: Ancient Tomb, Gaea's Cradle -------------------
    tomb = RM.ANCIENT_TOMB
    g = rgame(tomb)
    check("A Ancient Tomb offers two {C}",
          [sorted(u) for u in EN.available_mana(g)], [["C"], ["C"]])

    g = rgame(tomb)
    life = g.your_life
    units = EN.available_mana(g)
    EN.spend(g, EN.can_pay({"gen": 1}, units), units)
    check("B tapping Ancient Tomb deals 2 damage to you",
          (life - g.your_life, g.m["tomb_damage"]), (2, 2))

    g = rgame(tomb, land("Forest", "G"))
    units = EN.available_mana(g)
    EN.spend(g, EN.can_pay({"gen": 1}, units), units)
    check("C paying {1} taps the Forest and not the Tomb",
          [p.tapped for p in g.board], [False, True])

    cradle = RM.GAEAS_CRADLE
    g = rgame(cradle, body("a"), body("b"), body("c"))
    check("D Gaea's Cradle offers one {G} per creature",
          [sorted(u) for u in EN.available_mana(g)], [["G"]] * 3)

    g = rgame(cradle)
    check("E ... and nothing with no creatures", len(EN.available_mana(g)), 0)

    g = rgame(cradle, land("Forest", "G"), body("a"), body("b"), body("c"))
    # A pool with no owners is what sends `spend` down its count path.
    EN.spend(g, [0, 1, 2], [frozenset({"G"})] * 3)
    check("F the count-based spend taps the Cradle once for its three",
          [p.tapped for p in g.board[:2]], [True, False])

    # ---- karlov / shilgengar: Scoured Barrens -----------------------------
    g = KA.KarlovGame(list(KDECK), KCMD, cfg(), 4242)
    g.board, g.hand = EN.Board(), [KM.SCOURED_BARRENS]
    g.land_drops_used, g.land_drops = 0, 1
    life = g.your_life
    EN.play_land(g)
    check("G karlov: Scoured Barrens gains 1 life", g.your_life - life, 1)

    g = SH.ShilgengarGame(list(SDECK), SCMD, cfg(), 7)
    g.board, g.hand = EN.Board(), [SM.SCOURED_BARRENS]
    g.land_drops_used, g.land_drops = 0, 1
    life = g.your_life
    EN.play_land(g)
    check("H shilgengar: Scoured Barrens gains 1 life", g.your_life - life, 1)

    # ---- lorehold: Command Beacon ------------------------------------------
    def lgame(tax):
        g = LO.LoreholdGame(list(LDECK), LCMD, cfg(counter_threshold=99), 1)
        g.board, g.hand, g.graveyard = LO.Board(), [], []
        for c in ([LM.COMMAND_BEACON] + [land("Mountain", "R")
                                         for _ in range(4)]
                  + [land("Plains", "W")]):
            g.board.append(EN.Permanent(card=c, sick=False))
        g.commander_cast, g.commander_tax = False, tax
        return g

    g = lgame(4)
    used = LO.command_beacon(g)
    on = any(p.card is g.commander for p in g.board)
    beacon = any(p.card.name == "Command Beacon" for p in g.board)
    tax_after_cast = g.commander_tax
    dead = next((p for p in g.board if p.card is g.commander), None)
    if dead is not None:
        OPP.destroy(g, dead)
    check("I Beacon at tax 4: cast from hand, Beacon gone, tax nets back",
          (used, on, beacon, tax_after_cast, g.commander_tax),
          (True, True, False, 2, 4))

    g = lgame(2)
    check("J ... and kept at tax 2",
          (LO.command_beacon(g),
           any(p.card.name == "Command Beacon" for p in g.board)),
          (False, True))

    # ---- tivit: Treasure Vault ---------------------------------------------
    def tgame(lands, treasures):
        g = TI.TivitGame(list(TDECK), TCMD, cfg(), 1)
        g.board = type(g.board)()
        for c in [TM.TREASURE_VAULT] + [land("Wastes", "C")
                                        for _ in range(lands)]:
            g.board.append(EN.Permanent(card=c, sick=False))
        for k in list(g.tokens):
            g.tokens[k] = 0
        g.tokens["Treasure"] = treasures
        return g

    g = tgame(8, 0)
    TI.treasure_vault(g)
    check("K Vault with eight spare mana: four Treasures, Vault gone",
          (g.tokens["Treasure"],
           any(p.card.name == "Treasure Vault" for p in g.board)), (4, False))

    g = tgame(4, 4)
    TI.treasure_vault(g)
    check("L ... Treasures do not pay: four lands and four Treasures, kept",
          (g.tokens["Treasure"],
           any(p.card.name == "Treasure Vault" and not p.tapped
               for p in g.board)), (4, True))

    # ---- azusa -------------------------------------------------------------
    g = azgame()
    g.board.append(EN.Permanent(card=AM.EVOLVING_WILDS, sick=False))
    g.crack_fetch(AM.EVOLVING_WILDS)
    check("M Evolving Wilds fetches a Forest tapped",
          [p.tapped for p in g.board if p.card.name == "Forest"], [True])

    def passage(n_other):
        g = azgame()
        for _ in range(n_other):
            g.board.append(EN.Permanent(card=land("Forest", "G"), sick=False))
        g.board.append(EN.Permanent(card=AM.FABLED_PASSAGE, sick=False))
        g.crack_fetch(AM.FABLED_PASSAGE)
        return g.board[-1].tapped if g.board[-1].card.name == "Forest" else None

    check("N Fabled Passage untaps at four lands, not at two",
          (passage(3), passage(1)), (False, True))

    g = azgame()
    g.board.append(EN.Permanent(card=AM.MYRIAD_LANDSCAPE, sick=False))
    for _ in range(2):
        g.board.append(EN.Permanent(card=land("Wastes", "C"), sick=False))
    before = g.m["landfall_triggers"]
    g.myriad_landscape_step()
    forests = [p.tapped for p in g.board if p.card.name == "Forest"]
    check("O Myriad Landscape: {2}, two tapped Forests, two landfalls",
          (forests, g.m["myriad_cracked"],
           any(p.card.name == "Myriad Landscape" for p in g.board),
           g.m["landfall_triggers"] - before),
          ([True, True], 1, False, 2))

    def field(names):
        g = azgame()
        g.board.append(EN.Permanent(card=AM.FIELD_OF_THE_DEAD, sick=False))
        for i in range(names - 2):
            g.board.append(EN.Permanent(card=land(f"Land {i}", "G"),
                                        sick=False))
        new = land("Forest", "G")
        g.make_permanent(new, sick=False)
        g.land_entered(new, played=True)
        return g.m["field_zombies"]

    check("P Field of the Dead: a Zombie at seven names, none at six",
          (field(7), field(6)), (1, 0))

    g = azgame()
    g.hand = [AM.EVOLVING_WILDS]
    g.land_drops_used = 0
    g.land_drops_for_turn = lambda: 1
    g.land_step()
    check("Q Evolving Wilds played from hand is cracked",
          (AM.EVOLVING_WILDS in g.graveyard,
           sum(p.card.name == "Forest" for p in g.board)), (True, 1))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Land candidates (§0z113)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    def m_named():
        old = EN.named_land_mana
        EN.named_land_mana = lambda g, p: None
        return lambda: setattr(EN, "named_land_mana", old)

    def m_reluct():
        old = EN.tap_reluctance

        def plain(g, p):
            if p.card.name == "Ancient Tomb":
                return (0, 0)
            return old(g, p)
        EN.tap_reluctance = plain
        return lambda: setattr(EN, "tap_reluctance", old)

    def m_surplus():
        # The Tomb keeps its rank 1.5; `can_pay` stops reading it as pain.
        old_rank, old_tr = EN.PAINFUL_RANK, EN.tap_reluctance

        def kept(g, p):
            if p.card.name == "Ancient Tomb":
                return (1.5, 0)
            return old_tr(g, p)
        EN.PAINFUL_RANK, EN.tap_reluctance = -1, kept

        def undo():
            EN.PAINFUL_RANK, EN.tap_reluctance = old_rank, old_tr
        return undo

    def m_cfg(**kw):
        def apply():
            CFG.update(kw)
            return CFG.clear
        return apply

    def m_shil():
        old = SH.ShilgengarGame.play_card_trigger
        SH.ShilgengarGame.play_card_trigger = lambda self, card: None
        return lambda: setattr(SH.ShilgengarGame, "play_card_trigger", old)

    def m_fetch():
        old = AZ.FETCH_SCRIPTS
        AZ.FETCH_SCRIPTS = frozenset({"fetch"})
        return lambda: setattr(AZ, "FETCH_SCRIPTS", old)

    mutations = [
        ("named_land_mana says nothing", m_named, {"A", "D", "E", "F"}),
        ("tap_reluctance forgets the Tomb", m_reluct, {"C"}),
        ("can_pay ranks surplus ahead of pain", m_surplus, {"C"}),
        ("charge_life_costs = False", m_cfg(charge_life_costs=False), {"B"}),
        ("beacon_min_tax = 99", m_cfg(beacon_min_tax=99), {"I"}),
        ("shilgengar's land hook does nothing", m_shil, {"H"}),
        ("FETCH_SCRIPTS is the true fetches only", m_fetch, {"Q"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for label, apply, want in mutations:
        undo = apply()
        try:
            broke = run_cases()
        finally:
            undo()
        ok = broke == want
        bad += not ok
        print(f"   {label}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
