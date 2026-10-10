#!/usr/bin/env python3
"""Mystery Booster Commander Edition: nine cards, six engines (§0z74).

    python -m tests.test_mbc
    python -m tests.test_mbc --mutate   # 11 mutations, exact sets

All text fetched from api.scryfall.com on 2026-09-29 and quoted in full in
each card's deck module and in its `edhmc/pending.py` Proposal. One
assertion per clause, on a constructed game state -- no simulation, no RNG
that the case does not seed itself.

CASES
  Selenia, the Cursed Heart
    A  shilgengar: gain 3 with Selenia out -> +6 life, ONE lifegain event
    B  karlov: gain 3 with Selenia and The Wind Crystal -> +12, one event
    C  curse_opponent curses the highest-life living opponent, and a second
       death while that curse stands makes nothing (legendary, 704.5j)
    D  life_loss doubles a cursed player's loss through damage_each and
       damage_single, and leaves an uncursed one alone
    E  shilgengar: Selenia sacrificed -> a curse; a Selenia carrying a
       finality counter is exiled, not killed -> no curse
    F  karlov: Selenia dying -> a curse
  Seluma, Light of Aysen
    G  unblocked Seluma connects -> the Angel card returns from the graveyard
    H  a chump-blocked Seluma (ten opposing creatures, one flier-capable
       blocker) triggers nothing
  Thomil, the Destroyer (shared `thomil_step`, rendmaw's engine)
    I  loyalty 4, no other creature -> +2: loyalty 6, one Zombie
    J  loyalty 6, two other creatures -> -5: loyalty 1, a Lord of the Pit
    K  once per turn: a second call in the same turn does nothing
    L  Lord of the Pit's upkeep sacrifices the smallest TOKEN (never the
       commander); alone, it deals 7 to you
  Pearl Collector
    M  gained 4 -> a Mox Pearl in hand; the same object does not trigger
       twice; gained 3 -> nothing
    N  the {2}{W} sink with mana for ONE activation: one grant, to the
       biggest nontoken creature, which then has lifelink
  Dyfed, the Guiding Hand / Powerstones (tivit)
    O  +1 -> two TAPPED Powerstones, counted as artifacts; x2 under
       Anointed Procession
    P  -1 untaps a tapped Time Sieve when five more artifacts can pay: a
       second extra turn
    Q  Powerstone mana is offered to an ability and NOT to a nonartifact
       spell
  Venser, Visionary Traveler (tivit)
    R  +1 on Tivit -> it returns at end step: one dilemma, two counters
  Autumn Willow, Harmony (azusa)
    S  its ETB makes one Forest Dryad token, a landfall trigger
    T  an untapped Dryad Arbor makes TWO units with Willow out, one without;
       a plain Forest makes one either way
  Davvol, Evincar of Rath (rendmaw)
    U  two tokens entering -> 2 life lost, {B}{B} in the pool; Davvol's own
       entry triggers nothing
    V  the pool empties at a step boundary, counted as lost
  Chief Magistrate of Mercadia (lorehold)
    W  resolving it makes you the monarch
    X  upkeep as monarch with one Pegasus: Goblin, then a copy of each ->
       four tokens, the Goblin copy hasty; without the crown, only the Goblin

MUTATIONS, WRITTEN BEFORE THE FIRST RUN, exact sets:
  life_loss ignores the curse                     -> D
  curse_opponent ignores the legend rule          -> C
  record_hits reports nothing                     -> G
  walker_ready always says yes                    -> K
  Lord of the Pit's upkeep does nothing           -> L
  perpetual_lifelink never true                   -> N
  Powerstone mana pays nonartifact spells         -> Q
  Venser's counters never set                     -> R
  Willow's land-creature test always false        -> T
  davvol_trigger does nothing                     -> U
  become_monarch does nothing                     -> W

UNMUTATED, and why (§0z15): the three doublers inside `gain_life` (A, B) and
Magistrate's copy loop (X) are inline with no seam a mutation could replace
without re-implementing them; the cases pin them directly.
"""
import random
import sys

from edhmc import engine as EN
from edhmc import opponents as OPP
from edhmc import shilgengar as SH
from edhmc import karlov as KA
from edhmc import tivit as TV
from edhmc import azusa as AZ
from edhmc import lorehold as LO
from edhmc.decks import (shilgengar_v1, karlov_v2, tivit_v1, azusa_v1,
                         rendmaw_v12, lorehold_v17)
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**k):
    return dict(DEFAULT_CFG, turns=20, **k)


def fresh(cls, module, **k):
    deck, cmd = module.build()
    g = cls(list(deck), cmd, cfg(**k), 7)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 5
    return g


def perm(card, **k):
    return EN.Permanent(card=card, sick=k.pop("sick", False),
                        base_p=card.power, base_t=card.toughness, **k)


def land(name, colour, **k):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({colour}), **k)


def body(name, p=1, t=1, **k):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=t, **k)


def selenia_cases():
    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    g.board.append(perm(shilgengar_v1.SELENIA_THE_CURSED_HEART))
    life, ev = g.your_life, g.m["lifegain_triggers"]
    g.gain_life(3)
    check("A shilgengar: +6 life, one event",
          (g.your_life - life, g.m["lifegain_triggers"] - ev), (6, 1))

    g = fresh(KA.KarlovGame, karlov_v2)
    g.board.append(perm(karlov_v2.SELENIA_THE_CURSED_HEART))
    g.board.append(perm(karlov_v2.THE_WIND_CRYSTAL))
    life, ev = g.your_life, g.m["lifegain_triggers"]
    KA.gain_life(g, 3)
    check("B karlov: Selenia x Wind Crystal = +12, one event",
          (g.your_life - life, g.m["lifegain_triggers"] - ev), (12, 1))

    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    for o, life in zip(g.opponents, (20.0, 35.0, 30.0)):
        o.life = life
    OPP.curse_opponent(g)
    OPP.curse_opponent(g)
    check("C curse: the 35-life player, once",
          ([o.cursed for o in g.opponents], g.m["curses_made"]),
          ([False, True, False], 1))

    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    for o in g.opponents:
        o.life = 40.0
    g.opponents[0].cursed = True
    OPP.damage_each(g, 1)
    g.opponents[1].life = 50.0      # single targets the lowest: the cursed one
    g.opponents[2].life = 50.0
    OPP.damage_single(g, 3)
    check("D cursed loses double, the rest single",
          [o.life for o in g.opponents], [32.0, 50.0, 50.0])

    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    s = perm(shilgengar_v1.SELENIA_THE_CURSED_HEART)
    g.board.append(s)
    g.sacrifice(s)
    made = g.m["curses_made"]
    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    s = perm(shilgengar_v1.SELENIA_THE_CURSED_HEART)
    g.board.append(s)
    g.finality.add(id(s.card))
    g.sacrifice(s)
    check("E sacrificed -> curse; with finality -> none",
          (made, g.m["curses_made"]), (1, 0))

    g = fresh(KA.KarlovGame, karlov_v2)
    s = perm(karlov_v2.SELENIA_THE_CURSED_HEART)
    g.on_creature_death(1, s)
    check("F karlov: Selenia dies -> curse", g.m["curses_made"], 1)


def seluma_cases():
    for label, blockers, want in (
            ("G unblocked Seluma returns the Angel", 0.0, (1, True)),
            ("H chump-blocked Seluma returns nothing", 10.0, (0, False))):
        g = fresh(SH.ShilgengarGame, shilgengar_v1)
        angel = next(c for c in shilgengar_v1.build()[0]
                     if c.name == "Serra's Emissary")
        g.graveyard.append(angel)
        for o in g.opponents:
            o.creatures = blockers
        g.board.append(perm(shilgengar_v1.SELUMA_LIGHT_OF_AYSEN))
        g.combat()
        check(label, (g.m["seluma_returns"],
                      any(p.card is angel for p in g.board)), want)


def rendmaw_game(**k):
    deck, cmd = rendmaw_v12.build()
    g = EN.Game(list(deck), cmd, cfg(**k), random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"F{i}", types=frozenset({"Sorcery"}),
                         cost={"gen": 9}) for i in range(20)]
    g.turn = 5
    return g


def thomil(g, loyalty):
    t = perm(rendmaw_v12.THOMIL_THE_DESTROYER)
    t.counters = loyalty
    g.board.append(t)
    return t


def step(g):
    EN.thomil_step(g, make_zombie=lambda: g.make_tokens(1, 2, 2, "Zombie"),
                   make_lord=lambda: EN.rendmaw_token(g,
                                                      EN.lord_of_the_pit_card))


def thomil_cases():
    g = rendmaw_game()
    t = thomil(g, 4)
    step(g)
    check("I +2: loyalty 6, one Zombie",
          (t.counters, sum(p.card.name == "Zombie token" for p in g.board)),
          (6, 1))

    g = rendmaw_game()
    t = thomil(g, 6)
    g.board.append(perm(body("A")))
    g.board.append(perm(body("B")))
    step(g)
    check("J -5: loyalty 1, a Lord of the Pit",
          (t.counters, g.m["thomil_lords"],
           any(p.card.script == "lord_of_the_pit" for p in g.board)),
          (1, 1, True))

    g = rendmaw_game()
    t = thomil(g, 4)
    step(g)
    step(g)
    check("K once per turn", (t.counters, g.m["thomil_zombies"]), (6, 1))

    g = rendmaw_game()
    lord = perm(EN.lord_of_the_pit_card(), is_token=True)
    cmdr = perm(g.commander)
    small = perm(body("Saproling token"), is_token=True)
    big = perm(body("Zombie token", 2, 2), is_token=True)
    for p in (lord, cmdr, small, big):
        g.board.append(p)
    EN.lord_of_the_pit_upkeep(g, lambda p: EN.rendmaw_sacrifice(g, p))
    kept = [p.card.name for p in g.board]
    g2 = rendmaw_game()
    g2.board.append(perm(EN.lord_of_the_pit_card(), is_token=True))
    life = g2.your_life
    EN.lord_of_the_pit_upkeep(g2, lambda p: EN.rendmaw_sacrifice(g2, p))
    check("L the Saproling goes, not the commander; alone -> 7 to you",
          ("Saproling token" in kept, g.commander.name in kept,
           life - g2.your_life), (False, True, 7))


def pearl_cases():
    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    g.board.append(perm(shilgengar_v1.PEARL_COLLECTOR))
    EN.pearl_collector_trigger(g, 4)
    EN.pearl_collector_trigger(g, 9)
    g2 = fresh(SH.ShilgengarGame, shilgengar_v1)
    g2.board.append(perm(shilgengar_v1.PEARL_COLLECTOR))
    EN.pearl_collector_trigger(g2, 3)
    check("M gained 4 -> one Mox Pearl, once; gained 3 -> none",
          ([c.name for c in g.hand], len(g2.hand)), (["Mox Pearl"], 0))

    g = fresh(SH.ShilgengarGame, shilgengar_v1)
    g.board.append(perm(shilgengar_v1.PEARL_COLLECTOR))
    small = perm(body("Small", 2, 2))
    big = perm(body("Big", 5, 5))
    for p in (small, big, perm(land("Plains", "W")), perm(land("Swamp", "B")),
              perm(land("Swamp", "B"))):
        g.board.append(p)
    EN.pearl_collector_lifelink(
        g, lambda c: g.pay(c, count_mana_spent=3),
        lambda p: bool(p.card.lifelink or EN.perpetual_lifelink(g, p)))
    check("N one grant, to the 5/5, which now has lifelink",
          (g.m["pearl_lifelink_grants"], EN.perpetual_lifelink(g, big),
           EN.perpetual_lifelink(g, small)), (1, True, False))


def tivit_game(**k):
    g = fresh(TV.TivitGame, tivit_v1, **k)
    g.library = [EN.Card(name=f"F{i}", types=frozenset({"Sorcery"}),
                         cost={"gen": 9}) for i in range(20)]
    return g


def tivit_cases():
    g = tivit_game()
    d = perm(tivit_v1.DYFED_THE_GUIDING_HAND)
    d.counters = 4
    g.board.append(d)
    before = g.artifact_count()
    TV.walker_step(g)
    g2 = tivit_game()
    g2.board.append(perm(tivit_v1.ANOINTED_PROCESSION))
    d2 = perm(tivit_v1.DYFED_THE_GUIDING_HAND)
    d2.counters = 4
    g2.board.append(d2)
    TV.walker_step(g2)
    check("O +1: two tapped Powerstones, artifacts; four under Procession",
          (g.tokens["Powerstone"], g.powerstones_tapped,
           g.artifact_count() - before, g2.tokens["Powerstone"], d.counters),
          (2, 2, 2, 4, 5))

    g = tivit_game()
    sieve = next(c for c in tivit_v1.build()[0] if c.name == "Time Sieve")
    sp = perm(sieve)
    sp.tapped = True
    g.board.append(sp)
    d = perm(tivit_v1.DYFED_THE_GUIDING_HAND)
    d.counters = 4
    g.board.append(d)
    g.tokens["Clue"] = 5
    TV.walker_step(g)
    check("P -1 untaps the Sieve: a second extra turn",
          (d.counters, g.extra_turns, g.m["dyfed_untaps"], sp.tapped),
          (3, 1, 1, True))

    g = tivit_game()
    g.tokens["Powerstone"] = 2
    plain = TV.mana_units(g)
    ability = TV.mana_units(g, powerstones=True)
    check("Q Powerstones pay abilities, not nonartifact spells",
          (len(plain), len(ability)), (0, 2))

    g = tivit_game()
    tivit = perm(g.commander)
    g.board.append(tivit)
    v = perm(tivit_v1.VENSER_VISIONARY_TRAVELER)
    v.counters = 4
    g.board.append(v)
    g.commander_cast = True
    TV.walker_step(g)
    trig = g.m["tivit_triggers"]
    TV.end_step(g)
    check("R Venser: one dilemma at end step, Tivit has two counters",
          (g.m["tivit_triggers"] - trig, tivit.counters, v.counters),
          (1, 2, 5))


def azusa_cases():
    g = fresh(AZ.AzusaGame, azusa_v1)
    lf = g.m["landfall_triggers"]
    g.make_permanent(azusa_v1.AUTUMN_WILLOW_HARMONY, sick=False)
    check("S Willow's ETB: one Forest Dryad, one landfall",
          (sum(p.card.name == "Forest Dryad token" for p in g.board),
           g.m["landfall_triggers"] - lf), (1, 1))

    arbor = next(c for c in azusa_v1.build()[0] if c.name == "Dryad Arbor")
    forest = next(c for c in azusa_v1.build()[0] if c.name == "Forest")
    counts = []
    for willow in (False, True):
        g = fresh(AZ.AzusaGame, azusa_v1)
        a = perm(arbor)
        f = perm(forest)
        g.board.append(a)
        g.board.append(f)
        if willow:
            g.board.append(perm(azusa_v1.AUTUMN_WILLOW_HARMONY))
        units = g.available_mana()
        counts.append((sum(o is a for o in units.owners),
                       sum(o is f for o in units.owners)))
    check("T Arbor 1 -> 2 units with Willow; the Forest 1 either way",
          counts, [(1, 1), (2, 1)])


def davvol_cases():
    g = rendmaw_game()
    g.board.append(perm(rendmaw_v12.DAVVOL_EVINCAR_OF_RATH))
    life = g.your_life
    base = len(EN.rendmaw_mana(g))
    g.make_tokens(2, 1, 1, "Saproling")
    d2 = perm(rendmaw_v12.DAVVOL_EVINCAR_OF_RATH)
    EN.davvol_trigger(g, d2)                   # his own entry: nothing
    check("U two tokens: -2 life, {B}{B} floating; Davvol himself nothing",
          (life - g.your_life, g.davvol_float,
           len(EN.rendmaw_mana(g)) - base), (2, 2, 2))

    g = rendmaw_game()
    g.davvol_float = 3
    EN.empty_mana_pool(g)
    check("V the pool empties, counted as lost",
          (g.davvol_float, g.m["davvol_mana_lost"]), (0, 3))


def magistrate_cases():
    g = fresh(LO.LoreholdGame, lorehold_v17)
    LO.resolve_spell(g, lorehold_v17.CHIEF_MAGISTRATE_OF_MERCADIA, 6)
    check("W resolving it makes you the monarch", g.monarch, True)

    out = []
    for crown in (True, False):
        g = fresh(LO.LoreholdGame, lorehold_v17)
        g.board.append(perm(lorehold_v17.CHIEF_MAGISTRATE_OF_MERCADIA))
        LO.make_tokens(g, 1, 1, 1, "Pegasus")
        g.monarch = crown
        LO.magistrate_upkeep(g)
        toks = [p for p in g.board if p.is_token]
        out.append((len(toks),
                    sum(1 for p in toks if p.card.name == "Goblin token"
                        and not p.sick)))
    check("X crown: 4 tokens, both Goblins hasty; no crown: Goblin only",
          out, [(4, 2), (2, 1)])


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    selenia_cases()
    seluma_cases()
    thomil_cases()
    pearl_cases()
    tivit_cases()
    azusa_cases()
    davvol_cases()
    magistrate_cases()
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Mystery Booster Commander Edition -- nine cards, six engines\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")

    def curse_no_legend(g):
        alive = OPP.living(g)
        victim = max(alive, key=lambda o: o.life)
        victim.cursed = True
        g.m["curses_made"] += 1
        return True

    muts = [
        ("life_loss ignores the curse", {"D"},
         OPP, "life_loss", lambda o, n: n),
        ("curse_opponent ignores the legend rule", {"C"},
         OPP, "curse_opponent", curse_no_legend),
        ("record_hits reports nothing", {"G"},
         OPP, "record_hits", lambda g, through: None),
        ("walker_ready always says yes", {"K"},
         EN, "walker_ready", lambda g, p: True),
        ("Lord of the Pit's upkeep does nothing", {"L"},
         EN, "lord_of_the_pit_upkeep", lambda g, sac: None),
        ("perpetual_lifelink never true", {"N"},
         EN, "perpetual_lifelink", lambda g, p: False),
        ("Powerstone mana pays nonartifact spells", {"Q"},
         TV, "mana_units",
         (lambda real: lambda g, powerstones=False: real(g, True))(
             TV.mana_units)),
        ("Venser's counters never set", {"R"},
         TV, "venser_counters", lambda g: None),
        ("Willow's land-creature test always false", {"T"},
         AZ.AzusaGame, "is_land_creature_now", lambda self, p: False),
        ("davvol_trigger does nothing", {"U"},
         EN, "davvol_trigger", lambda g, p: None),
        ("become_monarch does nothing", {"W"},
         OPP, "become_monarch", lambda g: None),
    ]
    bad = 0
    for label, want, where, name, fn in muts:
        print(f"-- {label}")
        real = getattr(where, name)
        setattr(where, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(where, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
