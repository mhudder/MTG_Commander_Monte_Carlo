#!/usr/bin/env python3
"""Pin §0z116's remainder, fixed in §0z151.

    python -m tests.test_oracle_remainder
    python -m tests.test_oracle_remainder --mutate   # 12 mutations, exact sets

On the default pod (POD_V4). A counterspell is FORCED where a case needs one:
`counter_threshold` 0, every counter roll 0, and each opponent holding
counters at `p["counter"]` 1.

CASES
  A  tivit: Void Rend ("This spell can't be countered") is not countered, the
     table keeps its counterspell, and the save is counted
  B  lorehold: with Hexing Squelcher out, a plain sorcery is not countered
  C  karlov: Cavern of Souls covers the commander (its type) once a turn --
     not countered, then countered the same turn, then covered next turn
  D  karlov: ... and a creature that shares no type with the commander is
     countered with Cavern unused
  E  karlov: a COUNTERED spell still sets off Aetherflux Reservoir
  F  rendmaw: a countered two-type card still makes Rendmaw's Birds
  G  lorehold: a countered noncreature spell still triggers Longshot
  H  tivit: a countered noncreature spell still blinks Tivit (Displacer
     Kitten)
  I  karlov: the commander's own cast sets off Aetherflux Reservoir
  J  rendmaw: Darkbore Pathway enters as the colour your lands lack
  K  karlov: Anguished Unmaking costs 3 life when it resolves
  L  karlov: Toxic Deluge pays X life, X the toughest creature it kills
  M  karlov: Land Tax takes the basic of the colour you are short of, any
     basic, and shuffles
  N  lorehold: Smothering Tithe makes a Treasure per living opponent
  O  shilgengar: Massacre Wurm's -2/-2 takes a toughness-2 creature route
     piece, as rendmaw's does
  P  shilgengar: Elesh Norn gives the commander +2/+2
  Q  shilgengar: Elesh Norn entering kills the pod's toughness-2 bodies
  R  karlov: with Kalitas out, the pod's dying creatures become Zombies for
     you and Blood Artist does not hear them
  S  karlov: Sorin, Solemn Visitor gives your creatures +1/+0
  T  rendmaw: with Bow of Nylea out an attacker has deathtouch, as with
     Ohran Frostfang (the same words)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  uncounterable=False            -> A, B, C
  cast_triggers_countered=False  -> E, F, G, H
  commander_cast_triggers=False  -> I
  modal_land_face=False          -> J
  spell_life_costs=False         -> K, L
  land_tax_shared=False          -> M
  tithe_shared=False             -> N
  wurm_route_pieces=False        -> O
  norn_text=False                -> P, Q
  kalitas_text=False             -> R
  sorin_power=False              -> S
  bow_deathtouch=False           -> T

UNMUTATED (§0z15): D is the positive control C is measured against -- a
creature of another type is countered whether or not Cavern is read.
"""
import dataclasses
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LO
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
import edhmc.tivit as TI
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECKS = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar")
LISTS = {d: build_pending(d) for d in DECKS}


def card(deck, name):
    return next(c for c in LISTS[deck][0] if c.name == name)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def filler(i, types=("Sorcery",)):
    return EN.Card(name=f"Filler {i}", types=frozenset(types),
                   cost={"gen": 1})


def body(name, p=2, types=("Creature",)):
    return EN.Card(name=name, types=frozenset(types), power=p, toughness=p,
                   cost={"gen": 3})


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, counter_threshold=99,
                **{**kw, **CFG})


def fresh(deck, board=(), hand=(), sick=(), **kw):
    d, cmd = LISTS[deck]
    c = cfg(**kw)
    if deck == "rendmaw":
        g = EN.Game(list(d), cmd, c, random.Random(1), seed_for_pod=1)
    elif deck == "karlov":
        g = KA.KarlovGame(list(d), cmd, c, 4242)
    elif deck == "lorehold":
        g = LO.LoreholdGame(list(d), cmd, c, 1)
    elif deck == "shilgengar":
        g = SH.ShilgengarGame(list(d), cmd, c, 7)
    else:
        g = TI.TivitGame(list(d), cmd, c, 1)
    g.board = EN.Board()
    g.hand = list(hand)
    g.graveyard = []
    g.library = [filler(i) for i in range(30)]
    g.your_life = 40.0
    g.turn = 7
    g.commander_cast = False
    for o in g.opponents:
        o.life = 40.0
        o.creatures = 0.0
        o.bodies = []
        o.pieces, o.piece_lands = (), []
    for x in board:
        g.board.append(EN.Permanent(card=x, sick=x in sick))
    return g


def force_counters(g):
    """Every spell the table sees is countered, unless it can't be."""
    g.cfg["counter_threshold"] = 0
    g.counter_rolls = [[[0.0] * len(g.opponents)
                        for _ in range(OPP.N_COUNTER_SLOTS)]
                       for _ in range(60)]
    for o in g.opponents:
        o.counters_left = 9
        o._pcache = dict(o.p, counter=1.0)


def lands(deck, *names):
    """Distinct copies: `card` returns the deck's one object per name, and
    three of it is one card (§0z112)."""
    return [dataclasses.replace(card(deck, n)) for n in names]


def perm(g, name):
    return next(p for p in g.board if p.card.name == name)


def run_cases():
    PASS.clear()
    FAIL.clear()

    # -- can't be countered ---------------------------------------------------
    g = fresh("tivit")
    force_counters(g)
    held = sum(o.counters_left for o in g.opponents)
    got = (OPP.countered(g, card("tivit", "Void Rend"), 0),
           sum(o.counters_left for o in g.opponents) == held,
           g.m["counters_shielded"])
    check("A Void Rend: not countered, the counter kept, the save counted",
          got, (False, True, 1))
    g = fresh("lorehold", board=[card("lorehold", "Hexing Squelcher")])
    force_counters(g)
    check("B Hexing Squelcher out: a plain sorcery is not countered",
          OPP.countered(g, filler(1), 0), False)
    g = fresh("karlov", board=lands("karlov", "Cavern of Souls"))
    force_counters(g)
    first = OPP.countered(g, g.commander, 0)
    again = OPP.countered(g, g.commander, 1)
    g.turn += 1
    check("C Cavern covers the commander once a turn",
          (first, again, OPP.countered(g, g.commander, 0)),
          (False, True, False))
    g = fresh("karlov", board=lands("karlov", "Cavern of Souls"))
    force_counters(g)
    check("D ... and not a creature of another type",
          OPP.countered(g, body("Typeless Bear"), 0), True)

    # -- cast triggers fire on a countered spell -------------------------------
    g = fresh("karlov", board=lands("karlov", "Plains")
              + [card("karlov", "Aetherflux Reservoir")], hand=[filler(1)])
    force_counters(g)
    KA.main_phase(g)
    check("E karlov: a countered spell still sets off the Reservoir",
          (g.m["countered"], g.your_life), (1, 41.0))
    rcmd = LISTS["rendmaw"][1]
    g = fresh("rendmaw", board=lands("rendmaw", "Forest") + [rcmd],
              hand=[filler(1, ("Artifact", "Creature"))])
    g.commander_cast = True
    force_counters(g)
    EN.main_phase(g)
    check("F rendmaw: a countered two-type card still makes the Birds",
          (g.m["countered"], g.m["rendmaw_triggers"]), (1, 1))
    g = fresh("lorehold", board=lands("lorehold", "Mountain")
              + [card("lorehold", "Longshot, Rebel Bowman")],
              hand=[filler(1)])
    force_counters(g)
    LO.main_phase(g)
    check("G lorehold: a countered sorcery still triggers Longshot",
          (g.m["countered"], [o.life for o in g.opponents]),
          (1, [38.0, 38.0, 38.0]))
    tcmd = LISTS["tivit"][1]
    g = fresh("tivit", board=lands("tivit", "Plains") + [
        tcmd, card("tivit", "Displacer Kitten")], hand=[filler(1)])
    g.commander_cast = True
    force_counters(g)
    TI.main_phase(g)
    check("H tivit: a countered sorcery still blinks Tivit",
          (g.m["countered"], g.m["blinks"]), (1, 1))
    g = fresh("karlov", board=lands("karlov", "Plains", "Swamp")
              + [card("karlov", "Aetherflux Reservoir")])
    KA.main_phase(g)
    check("I karlov: the commander's cast sets off the Reservoir",
          (g.commander_cast, g.your_life), (True, 41.0))

    # -- Pathways, and life costs ---------------------------------------------
    path = card("rendmaw", "Darkbore Pathway")
    g = fresh("rendmaw", board=lands("rendmaw", "Swamp"))
    one = EN.enter_land(g, path).card.produces
    g = fresh("rendmaw", board=lands("rendmaw", "Forest"))
    check("J Darkbore Pathway enters as the colour your lands lack",
          (one, EN.enter_land(g, path).card.produces),
          (frozenset({"G"}), frozenset({"B"})))
    g = fresh("karlov")
    OPP.countered(g, card("karlov", "Anguished Unmaking"), 0)
    check("K Anguished Unmaking: 3 life on resolution", g.your_life, 37.0)
    g = fresh("karlov", board=[body("Wall", 3)])
    OPP.resolve_own_wipe(g, card=card("karlov", "Toxic Deluge"))
    check("L Toxic Deluge: X life, X the toughest creature it kills",
          (g.your_life, g.m["deluge_life_paid"]), (37.0, 3))

    # -- one rule each: Land Tax, Smothering Tithe, Massacre Wurm --------------
    g = fresh("karlov", board=lands("karlov", "Plains", "Plains")
              + [card("karlov", "Land Tax")])
    g.library = ([filler(i) for i in range(10)] + [card("karlov", "Swamp")]
                 + lands("karlov", "Plains", "Plains", "Plains"))
    KA.upkeep(g)
    check("M Land Tax: the Swamp you lack, three basics, and a shuffle",
          (sorted(c.name for c in g.hand if c.is_land),
           [c.name for c in g.library[:10]] != [f"Filler {i}"
                                                  for i in range(10)]),
          (["Plains", "Plains", "Swamp"], True))
    g = fresh("lorehold", board=[card("lorehold", "Smothering Tithe")])
    before = g.m["treasures_made"]
    LO.take_turn(g)
    check("N Smothering Tithe: a Treasure per living opponent",
          g.m["treasures_made"] - before, 3)
    g = fresh("shilgengar")
    o = g.opponents[0]
    o.pieces = (OPP.ThreatPiece("Creature", 2, 2, 1),)
    o.piece_lands = [0]
    g.resolve(card("shilgengar", "Massacre Wurm"))
    check("O shilgengar's Wurm takes a toughness-2 creature route piece",
          OPP.present_pieces(g, o), [])

    # -- Elesh Norn, Kalitas, Sorin -------------------------------------------
    scmd = LISTS["shilgengar"][1]
    g = fresh("shilgengar", board=[scmd,
                                   card("shilgengar",
                                        "Elesh Norn, Grand Cenobite")])
    c = perm(g, scmd.name)
    check("P Elesh Norn: the commander gets +2/+2",
          (g.power_of(c), g.toughness_of(c)),
          (scmd.power + 2, scmd.toughness + 2))
    g = fresh("shilgengar")
    for o in g.opponents:
        o.bodies = [OPP.PodBody(2, 2), OPP.PodBody(5, 4)]
        o.creatures = 2.0
    g.make_permanent(card("shilgengar", "Elesh Norn, Grand Cenobite"))
    check("Q Elesh Norn entering kills the toughness-2 bodies",
          [[b.toughness for b in o.bodies] for o in g.opponents],
          [[5], [5], [5]])
    g = fresh("karlov", board=[card("karlov", "Kalitas, Traitor of Ghet"),
                               card("karlov", "Blood Artist")])
    o = g.opponents[0]
    o.bodies = [OPP.PodBody(3, 3), OPP.PodBody(4, 4)]
    o.creatures = 2.0
    OPP.kill_pod_bodies(g, o)
    check("R Kalitas: two Zombies, and Blood Artist hears nothing",
          (sum(1 for p in g.board if p.card.name == "Zombie token"),
           [x.life for x in g.opponents]),
          (2, [40.0, 40.0, 40.0]))
    g = fresh("karlov", board=[card("karlov", "Sorin, Solemn Visitor"),
                               body("Bear")])
    check("S Sorin, Solemn Visitor: +1/+0", g.power_of(perm(g, "Bear")), 3)
    g = fresh("rendmaw", board=[card("rendmaw", "Bow of Nylea"),
                                body("Bear")])
    check("T Bow of Nylea: an attacker has deathtouch",
          OPP.deathtouch_of(g, perm(g, "Bear")), True)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z116's remainder (§0z151)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"uncounterable": False}, {"A", "B", "C"}),
        ({"cast_triggers_countered": False}, {"E", "F", "G", "H"}),
        ({"commander_cast_triggers": False}, {"I"}),
        ({"modal_land_face": False}, {"J"}),
        ({"spell_life_costs": False}, {"K", "L"}),
        ({"land_tax_shared": False}, {"M"}),
        ({"tithe_shared": False}, {"N"}),
        ({"wurm_route_pieces": False}, {"O"}),
        ({"norn_text": False}, {"P", "Q"}),
        ({"kalitas_text": False}, {"R"}),
        ({"sorin_power": False}, {"S"}),
        ({"bow_deathtouch": False}, {"T"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for over, want in mutations:
        CFG.update(over)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += not ok
        print(f"   {over}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
