#!/usr/bin/env python3
"""Pin the land rules of §0z115: how a land enters, what it costs, and the
utility lands' abilities.

    python -m tests.test_land_rules
    python -m tests.test_land_rules --mutate   # 14 mutations, exact sets

Every rule is read from the land's Scryfall text (`tag_flying.classify_land`
into `_evasion.LAND_RULES`) and applied by `engine` for the engines that play
lands through `play_land`, by azusa for its own. Each has a switch that
restores the pre-§0z115 engine.

CASES
  A  the classifier reads every rule kind from oracle text, and raises on an
     enters-tapped clause it cannot read
  B  every land the generator calls unconditionally tapped is built tapped
  C  trostani's hand-written land tags say what the generated rules say
  D  a shockland pays 2 life and enters untapped above `shock_life_floor`,
     and enters tapped (no life) at it
  E  `shock_pay="needed"`: with nothing to cast it enters tapped, free
  F  a fastland is untapped with two other lands, tapped with three
  G  a check land is tapped without its type, untapped with a Swamp
  H  a painland costs 1 life paying {W}, nothing paying {1}
  I  a horizon land costs 1 life on any tap
  J  lorehold's own payer charges a painland once, not twice
  K  shilgengar's Marsh Flats is cracked as it is played: 1 life, a Plains
     or Swamp onto the battlefield, the library one shorter
  L  lorehold's Fabled Passage: the basic enters tapped below four lands,
     untapped at four
  M  rendmaw's Golgari Rot Farm returns a land to hand
  N  Tainted Field makes {C} only without a Swamp, {W}/{B} with one
  O  Temple of the False God makes nothing below five lands, {C}{C} at five
  P  ... and so in azusa's own mana code
  Q  azusa's Windswept Heath pays 1 life when cracked
  R  Nykthos at devotion 5 floats five {G} when that unlocks a card
  S  Eldrazi Temple takes {1} off Kozilek while it is untapped
  T  Vault of the Archangel pays {2}{W}{B} and a tap for team lifelink
  U  Castle Locthwain draws and loses life equal to the hand
  V  Castle Ardenvale makes a 1/1 at the end step
  W  rendmaw's High Market sacrifices a token for 1 life (and Blood
     Artist, which the Market requires, drains for the other)
  X  lorehold's Mikokoro opens a miracle window with Lorehold not out
  Y  azusa's Petrified Field returns a fetch from the graveyard
  Z  azusa's Crystal Vein is sacrificed when its {C}{C} unlocks a card

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  land_etb_rules=False      -> D, E, F, G
  painland_life=False       -> H, I, J
  land_fetch=False          -> K, L, Q
  karoo_bounce=False        -> M
  land_only_if=False        -> N, O, P
  nykthos_devotion=False    -> R
  eldrazi_temple=False      -> S
  vault_paid=False          -> T
  locthwain=False           -> U
  castle_ardenvale=False    -> V
  high_market=False         -> W
  draw_lands=False          -> X
  petrified_field=False     -> Y
  crystal_vein=False        -> Z

ONE CASE WAS WRONG ON THE FIRST RUN, recorded rather than edited away: W
expected 1 life and got 2 -- the Blood Artist the Market's policy requires
gains its own 1 on the death. The test, not the engine.

UNMUTATED (§0z15): A is the classifier on fixed text; B and C check the
generated data against two hand-written sources and switch nothing.
"""
import random
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LO
import edhmc.shilgengar as SH
from edhmc.decks._evasion import LAND_RULES
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from tools.tag_flying import classify_land

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
LISTS = {d: build_pending(d) for d in ("rendmaw", "karlov", "lorehold",
                                       "shilgengar", "azusa", "trostani")}


def card(deck, name):
    return next(c for c in LISTS[deck][0] if c.name == name)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def filler(i):
    return EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1})


def body(name, cost=None, p=3):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=p, cost=cost or {"gen": 2})


def plain_land(name, produces):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset(produces))


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, **{**kw, **CFG})


def fresh(deck, board=(), hand=(), library=None, **kw):
    d, cmd = LISTS[deck]
    if deck == "rendmaw":
        g = EN.Game(list(d), cmd, cfg(**kw), random.Random(1), seed_for_pod=1)
    elif deck == "karlov":
        g = KA.KarlovGame(list(d), cmd, cfg(**kw), 4242)
    elif deck == "lorehold":
        g = LO.LoreholdGame(list(d), cmd, cfg(counter_threshold=99, **kw), 1)
    elif deck == "shilgengar":
        g = SH.ShilgengarGame(list(d), cmd, cfg(**kw), 7)
    else:
        g = AZ.AzusaGame(list(d), cmd, cfg(**kw), 1234)
        g.clues = 0
    g.board = EN.Board()
    g.hand = list(hand)
    g.graveyard = []
    g.library = list(library) if library is not None else [
        filler(i) for i in range(20)]
    g.your_life = 40.0
    g.turn = 5
    g.land_drops, g.land_drops_used = 1, 0
    for c in board:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def played(g):
    EN.play_land(g)
    return g.board[-1] if g.board else None


def run_cases():
    PASS.clear()
    FAIL.clear()

    texts = [
        ("As this land enters, you may pay 2 life. If you don't, it enters "
         "tapped.", {"etb": ("shock",)}),
        ("This land enters tapped unless you control two or fewer other "
         "lands. {T}: Add {W} or {B}.", {"etb": ("fast",)}),
        ("This land enters tapped unless you control two or more other "
         "lands.", {"etb": ("slow",)}),
        ("This land enters tapped unless you control two or more basic "
         "lands.", {"etb": ("battle",)}),
        ("This land enters tapped unless you have two or more opponents.",
         {"etb": ("bond",)}),
        ("This land enters tapped unless you control a Plains or a Swamp.",
         {"etb": ("check", ("Plains", "Swamp"))}),
        ("This land enters tapped unless you control three or more other "
         "Swamps.", {"etb": ("count", "Swamp", 3)}),
        ("As this land enters, you may reveal a Plains or Swamp card from "
         "your hand. If you don't, this land enters tapped.",
         {"etb": ("reveal", ("Plains", "Swamp"))}),
        ("{T}: Add {C}.\n{T}: Add {W} or {B}. This land deals 1 damage to "
         "you.", {"pain": (1, ("B", "W"), False)}),
        ("{T}, Pay 1 life: Add {W} or {B}.", {"pain": (1, ("B", "W"), True)}),
        ("{T}: Add {C}{C}. This land deals 2 damage to you.",
         {"pain": (2, (), True)}),
        ("{T}, Pay 1 life, Sacrifice this land: Search your library for a "
         "Plains or Swamp card, put it onto the battlefield, then shuffle.",
         {"fetch": (1, ("Plains", "Swamp"), "untapped")}),
        ("This land enters tapped.\nWhen this land enters, return a land you "
         "control to its owner's hand.\n{T}: Add {B}{G}.",
         {"etb": ("tapped",), "karoo": True}),
        ("{T}: Add {C}.\n{T}: Add {W} or {B}. Activate only if you control a "
         "Swamp.", {"only_if": ("control", "Swamp", ("B", "W"))}),
        ("{1}, {T}, Sacrifice this land: Draw a card. Activate only if you "
         "control five or more lands.", {}),
    ]
    bad = [t for t, want in texts if classify_land(t) != want]
    try:
        classify_land("This land enters tapped unless it is a full moon.")
        raised = False
    except ValueError:
        raised = True
    check("A the classifier reads every rule kind, and raises on one it "
          "cannot", (bad, raised), ([], True))

    wrong = sorted({c.name for d, (deck, _) in LISTS.items() for c in deck
                    if c.is_land and LAND_RULES.get(c.name, {}).get("etb")
                    == ("tapped",) and not c.tapped})
    check("B every unconditionally tapped land is built tapped", wrong, [])

    tag_of = {"shock": "shock", "check": "check", "battle": "battle",
              "reveal": "reveal"}
    disagree = []
    for c in LISTS["trostani"][0]:
        rule = LAND_RULES.get(c.name, {})
        kind = (rule.get("etb") or (None,))[0]
        if kind in tag_of and tag_of[kind] not in c.tags:
            disagree.append(c.name)
        if rule.get("karoo") and "bounce" not in c.tags:
            disagree.append(c.name)
        if "fetch" in rule and "fetch" not in c.tags:
            disagree.append(c.name)
    check("C trostani's tags agree with the generated rules",
          sorted(set(disagree)), [])

    shrine = card("karlov", "Godless Shrine")
    g = fresh("karlov", hand=[shrine])
    a = (played(g).tapped, 40 - g.your_life)
    g = fresh("karlov", hand=[shrine])
    g.your_life = 16.0
    b = (played(g).tapped, 16 - g.your_life)
    check("D a shock pays 2 above the floor, enters tapped at it",
          (a, b), ((False, 2), (True, 0)))

    g = fresh("karlov", hand=[shrine], shock_pay="needed")
    check("E shock_pay needed: nothing to cast, tapped and free",
          (played(g).tapped, 40 - g.your_life), (True, 0))

    court = card("karlov", "Concealed Courtyard")
    two = fresh("karlov", board=[plain_land(f"L{i}", "W") for i in range(2)])
    three = fresh("karlov", board=[plain_land(f"L{i}", "W") for i in range(3)])
    check("F a fastland: untapped with two lands, tapped with three",
          (EN.land_enters_tapped(two, court, True),
           EN.land_enters_tapped(three, court, True)), (False, True))

    chapel = card("karlov", "Isolated Chapel")
    swamp = card("karlov", "Swamp")
    g1 = fresh("karlov", board=[plain_land("Command Tower", "WB")])
    g2 = fresh("karlov", board=[swamp])
    check("G a check land: tapped without its type, untapped with a Swamp",
          (EN.land_enters_tapped(g1, chapel, True),
           EN.land_enters_tapped(g2, chapel, True)), (True, False))

    caves = card("karlov", "Caves of Koilos")

    def paid(cost, land, deck="karlov"):
        g = fresh(deck, board=[land])
        units = EN.available_mana(g)
        EN.spend(g, EN.can_pay(cost, units), units)
        return 40 - g.your_life
    check("H a painland: 1 life for {W}, nothing for {1}",
          (paid({"W": 1}, caves), paid({"gen": 1}, caves)), (1, 0))

    check("I a horizon land: 1 life on any tap",
          paid({"gen": 1}, card("shilgengar", "Silent Clearing")), 1)

    g = fresh("lorehold", board=[card("lorehold", "Battlefield Forge")])
    LO.pay(g, {"R": 1}, LO.mana_units(g))
    check("J lorehold's payer charges a painland once", 40 - g.your_life, 1)

    flats = card("shilgengar", "Marsh Flats")
    lib = [filler(i) for i in range(10)] + [card("shilgengar", "Plains"),
                                            card("shilgengar", "Swamp")]
    g = fresh("shilgengar", hand=[flats], library=lib)
    played(g)
    check("K Marsh Flats cracks as it is played",
          (40 - g.your_life, [p.card.name for p in g.board],
           flats in g.graveyard, len(g.library)),
          (1, [g.board[0].card.name], True, 11))
    if g.board and g.board[0].card.name not in ("Plains", "Swamp"):
        FAIL.append("K")

    fabled = card("lorehold", "Fabled Passage")
    lib = [filler(i) for i in range(10)] + [card("lorehold", "Mountain")]

    def fabled_tapped(n):
        g = fresh("lorehold", hand=[fabled], library=list(lib),
                  board=[plain_land(f"L{i}", "R") for i in range(n)])
        EN.play_land(g)
        found = [p for p in g.board if p.card.name == "Mountain"]
        return found[0].tapped if found else None
    check("L Fabled Passage: tapped below four lands, untapped at four",
          (fabled_tapped(1), fabled_tapped(3)), (True, False))

    farm = card("rendmaw", "Golgari Rot Farm")
    forest = card("rendmaw", "Forest")
    g = fresh("rendmaw", board=[forest], hand=[farm])
    played(g)
    check("M Golgari Rot Farm returns a land to hand",
          ([c.name for c in g.hand], g.m["karoo_bounces"]), (["Forest"], 1))

    tainted = card("karlov", "Tainted Field")
    check("N Tainted Field: {C} without a Swamp, {W}/{B} with one",
          (sorted(EN.land_colours(fresh("karlov"), tainted)),
           sorted(EN.land_colours(fresh("karlov", board=[swamp]), tainted))),
          (["C"], ["B", "W"]))

    temple = card("karlov", "Temple of the False God")

    def temple_mana(n):
        g = fresh("karlov", board=[temple] + [plain_land(f"L{i}", "W")
                                              for i in range(n - 1)])
        return EN.named_land_mana(g, g.board[0])
    check("O Temple of the False God: nothing below five lands, two at five",
          (temple_mana(4), temple_mana(5)), (0, 2))

    atemple = card("azusa", "Temple of the False God")

    def az_temple(n):
        g = fresh("azusa", board=[atemple] + [card("azusa", "Forest")
                                              for _ in range(n - 1)])
        return len(g.available_mana()) - (n - 1)
    check("P ... and in azusa's mana", (az_temple(4), az_temple(5)), (0, 2))

    heath = card("azusa", "Windswept Heath")
    g = fresh("azusa", board=[heath], library=[filler(i) for i in range(5)]
              + [card("azusa", "Forest")])
    g.crack_fetch(heath)
    check("Q azusa's true fetch pays 1 life", 40 - g.your_life, 1)

    nyk = card("azusa", "Nykthos, Shrine to Nyx")
    devout = body("Devout", {"G": 5})
    six = body("Five-drop", {"gen": 5})
    g = fresh("azusa", board=[nyk, card("azusa", "Forest"),
                              card("azusa", "Forest"), devout], hand=[six])
    fired = g.nykthos_step(g.available_mana())
    check("R Nykthos floats devotion mana when it unlocks a card",
          (fired, len(g.bonus_mana)), (True, 5))

    koz = card("azusa", "Kozilek, Butcher of Truth")
    g = fresh("azusa", board=[card("azusa", "Eldrazi Temple")])
    check("S Eldrazi Temple takes {1} off Kozilek", g.cost_of(koz)["gen"], 9)

    vault = card("karlov", "Vault of the Archangel")
    lands = [card("karlov", "Plains"), swamp, plain_land("X1", "W"),
             plain_land("X2", "B")]
    g = fresh("karlov", board=[vault] + lands + [body("Bear")])
    attackers = [p for p in g.board if p.card.name == "Bear"]
    on = EN.vault_of_the_archangel(g, attackers, lambda c: KA.pay_cost(g, c))
    check("T Vault of the Archangel pays {2}{W}{B} and a tap",
          (on, EN.vault_active(g), sum(p.tapped for p in g.board)),
          (True, True, 5))

    castle = card("rendmaw", "Castle Locthwain")
    g = fresh("rendmaw", board=[castle, card("rendmaw", "Swamp"),
                                card("rendmaw", "Swamp"),
                                plain_land("X1", "B")])
    EN.castle_locthwain(g, lambda c: EN.pay_from(g, EN.rendmaw_mana(g), c))
    check("U Castle Locthwain draws, then life equal to the hand",
          (len(g.hand), 40 - g.your_life), (1, 1))

    ard = card("shilgengar", "Castle Ardenvale")
    g = fresh("shilgengar", board=[ard, card("shilgengar", "Plains"),
                                   card("shilgengar", "Plains"),
                                   plain_land("X1", "W"),
                                   plain_land("X2", "W")])
    g.castle_ardenvale()
    check("V Castle Ardenvale makes a 1/1",
          sum(p.card.name == "Human token" for p in g.board), 1)

    token = EN.Permanent(card=body("Saproling", p=1), sick=False,
                         is_token=True)
    g = fresh("rendmaw", board=[card("rendmaw", "High Market"),
                                card("rendmaw", "Blood Artist")])
    g.board.append(token)
    EN.high_market(g)
    # 2 life: the Market's 1, and Blood Artist's drain on the death.
    check("W High Market sacrifices a token for 1 life",
          (token in g.board, g.m["high_market_sacs"], g.your_life - 40),
          (False, 1, 2))

    miko = card("lorehold", "Mikokoro, Center of the Sea")
    g = fresh("lorehold", board=[miko])
    g.commander_cast = False
    g.draw_lands_ready = [g.board[0]]
    g.float_mana = 5
    LO.draw_land_windows(g)
    check("X Mikokoro opens a window with Lorehold not out",
          (g.m["draw_land_windows"], g.float_mana), (1, 2))

    field = card("azusa", "Petrified Field")
    g = fresh("azusa", board=[field])
    g.graveyard = [heath]
    g.petrified_field_step()
    check("Y Petrified Field returns a fetch",
          ([c.name for c in g.hand], field in g.graveyard),
          (["Windswept Heath"], True))

    vein = card("azusa", "Crystal Vein")
    g = fresh("azusa", board=[vein, card("azusa", "Forest"),
                              card("azusa", "Forest")],
              hand=[body("Four-drop", {"gen": 4})])
    check("Z Crystal Vein is sacrificed when it unlocks a card",
          (g.crystal_vein_step(g.available_mana()), len(g.bonus_mana)),
          (True, 2))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Land rules (§0z115)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"land_etb_rules": False}, {"D", "E", "F", "G"}),
        ({"painland_life": False}, {"H", "I", "J"}),
        ({"land_fetch": False}, {"K", "L", "Q"}),
        ({"karoo_bounce": False}, {"M"}),
        ({"land_only_if": False}, {"N", "O", "P"}),
        ({"nykthos_devotion": False}, {"R"}),
        ({"eldrazi_temple": False}, {"S"}),
        ({"vault_paid": False}, {"T"}),
        ({"locthwain": False}, {"U"}),
        ({"castle_ardenvale": False}, {"V"}),
        ({"high_market": False}, {"W"}),
        ({"draw_lands": False}, {"X"}),
        ({"petrified_field": False}, {"Y"}),
        ({"crystal_vein": False}, {"Z"}),
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
