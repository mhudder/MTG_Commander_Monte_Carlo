#!/usr/bin/env python3
"""Item 24's change 4: one "which card do I want next" for selection and
tutors (§0z139).

    python -m tests.test_change4_selection
    python -m tests.test_change4_selection --mutate   # 9 mutations, exact sets

Texts verified against Scryfall 2026-10-14: Sensei's Divining Top ("{1}:
Look at the top three cards of your library, then put them back in any
order."), Enlightened Tutor ("...then shuffle and put that card on top."),
Gamble ("...put that card into your hand, discard a card at random, then
shuffle."), Sylvan Library ("...pay 4 life or put the card on top of your
library."), Abundance ("If you would draw a card, you may instead choose
land or nonland..."; ruling: it can stop you losing to an empty library),
Sylvan Scrying (a land to hand), Crop Rotation (sacrifice a land, a land onto
the battlefield).

CASES
  A  the shared want order: a land first while short of one, last when one
     is in hand; a castable spell before an uncastable one; then priority
  B  karlov's tier: Exquisite Blood over a higher-priority artifact when
     Sanguine Bond is out; the artifact without it
  C  karlov's Enlightened Tutor puts that card ON TOP; the library keeps its
     size; the Tutor goes to the graveyard
  D  karlov's Top: {1} from a land left untapped, the top three in want
     order, once a turn; nothing without mana
  E  `stack_top`: a castable card over an uncastable higher-priority one
  F  lorehold's Top costs {1} (float 3 -> 2), is not paid again for cards
     it already ordered; `lorehold_top_cost=0` is free
  G  ... and is not spun when {1} plus a miracle cannot be paid
  H  Gamble: the pilot casts it with two other cards in hand, not one; it
     finds the wanted card, then one card of the hand is discarded
  I  azusa's Sylvan Library: the better of the two chosen kept for 4 life
     while life stays at the floor (20); the worse back on top. At 22 life
     both go back, the better one on top
  J  Abundance: a land while short -- the nonlands revealed go to the
     bottom; an empty library loses nothing
  K  Abundance and Sylvan Library together: no card was DRAWN, so nothing
     goes back and no life is paid
  L  Sylvan Scrying takes a fetch over a Forest
  M  Crop Rotation sacrifices the tapped Forest and finds the fetch, which
     is cracked: two landfall triggers
  N  the land need: azusa wants a second land with three drops; karlov
     with one in hand does not; karlov with none does

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the land need is never felt              -> A, J, N
  karlov's tier is always 0                -> B, C
  Top's {1} is never paid                  -> D
  lorehold's Top is free again             -> F, G
  Gamble finds nothing                     -> H
  Abundance's cards count as drawn         -> K
  Abundance is a plain draw                -> J, K
  azusa's lands are all one rank           -> L, M
  every card is castable next turn         -> A, E

UNMUTATED (§0z15): F's `lorehold_top_cost=0` off switch and D's
once-a-turn are read by the plain run.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LH
from edhmc.decks import azusa_v1 as AM
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import lorehold_v17 as LM
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


def spell(name, mv=0, pri=0.0, types=("Sorcery",)):
    return EN.Card(name=name, types=frozenset(types),
                   cost={"gen": mv} if mv else {}, priority=pri)


def fillers(n=20):
    return [spell(f"F{i}") for i in range(n)]


def clean(g):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = fillers()
    g.turn = 6
    g.your_life = 30.0
    for o in g.opponents:
        o.life, o.creatures, o.alive = 40.0, 3.0, True
    return g


def make(engine, module, **cfg):
    deck, cmd = module.build()
    return clean(engine(list(deck), cmd, dict(DEFAULT_CFG, **cfg), 1))


def put(g, card, **kw):
    p = EN.Permanent(card=card, sick=False, **kw)
    g.board.append(p)
    return p


def names(cards):
    return [c.name for c in cards]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    plains = find(KM, "Plains")
    forest = find(AM, "Forest")

    # A ---------------------------------------------------------------
    g = make(KA.KarlovGame, KM)
    hi, lo, big = spell("Hi", pri=9), spell("Lo", pri=1), spell("Big", 6, 10)
    land = find(KM, "Swamp")
    short = names(EN.want_order(g, [hi, land, lo, big]))
    g.hand = [plains]
    flood = names(EN.want_order(g, [hi, land, lo, big]))
    check("A want order: land first when short, last when not; castable first",
          (short, flood), (["Swamp", "Hi", "Lo", "Big"],
                           ["Hi", "Lo", "Big", "Swamp"]))

    # B ---------------------------------------------------------------
    blood = find(KM, "Exquisite Blood")
    bond = find(KM, "Sanguine Bond")
    x = spell("X", pri=10, types=("Artifact",))
    g = make(KA.KarlovGame, KM)
    put(g, bond)
    with_bond = EN.want_best(g, [x, blood]).name
    g = make(KA.KarlovGame, KM)
    check("B karlov's tier: the missing half of the loop over priority",
          (with_bond, EN.want_best(g, [x, blood]).name),
          ("Exquisite Blood", "X"))

    # C ---------------------------------------------------------------
    g = make(KA.KarlovGame, KM)
    put(g, bond)
    g.library = fillers() + [x, blood] + fillers(5)
    n = len(g.library)
    et = find(KM, "Enlightened Tutor")
    KA.resolve(g, et)
    check("C Enlightened Tutor: Blood on top, the library its size",
          (g.library[-1].name, len(g.library), names(g.graveyard)),
          ("Exquisite Blood", n, ["Enlightened Tutor"]))

    # D ---------------------------------------------------------------
    top = find(KM, "Sensei's Divining Top")
    best, mid, worst = spell("Best", pri=9), spell("Mid", pri=5), spell("Worst", pri=1)
    g = make(KA.KarlovGame, KM)
    g.hand = [plains]                           # not short of lands
    put(g, top)
    land_p = put(g, plains)
    g.library = fillers() + [best, mid, worst]  # Worst on top
    g.top_turn = 0
    KA.top_spin(g, "left_up")
    first = (land_p.tapped, names(g.library[-3:]), g.m["top_spins"])
    g.library[-3:] = [best, mid, worst]
    KA.top_spin(g, "upkeep")                    # same turn: no second spin
    again = (names(g.library[-3:]), g.m["top_spins"])
    g = make(KA.KarlovGame, KM)
    put(g, top)
    KA.top_spin(g, "upkeep")
    check("D karlov's Top: {1}, want order, once a turn; nothing without mana",
          (first, again, g.m["top_spins"]),
          ((True, ["Worst", "Mid", "Best"], 1),
           (["Best", "Mid", "Worst"], 1), 0))

    # E ---------------------------------------------------------------
    g = make(KA.KarlovGame, KM)
    g.hand = [plains]
    c_lo, big_hi, c_hi = spell("CLo", pri=1), spell("BigHi", 6, 10), spell("CHi", pri=5)
    g.library = fillers() + [c_lo, big_hi, c_hi]
    EN.stack_top(g, 3)
    check("E stack_top: castable before uncastable, best on top",
          names(g.library[-3:]), ["BigHi", "CLo", "CHi"])

    # F, G ------------------------------------------------------------
    ltop = find(LM, "Sensei's Divining Top")
    out = []
    for cost in (1, 0):
        g = make(LH.LoreholdGame, LM, lorehold_top_cost=cost)
        put(g, ltop)
        g.float_mana, g.treasures = 3, 0
        LH.sort_top_three(g, off_turn=True)
        a = g.float_mana
        LH.sort_top_three(g, off_turn=True)
        out.append((a, g.float_mana, g.m["top_spins"]))
    check("F lorehold's Top: {1}, not again for known cards; cost 0 is free",
          out, [(2, 2, 1), (3, 3, 0)])
    g = make(LH.LoreholdGame, LM)
    put(g, ltop)
    g.float_mana, g.treasures = 2, 0
    lib = list(g.library)
    g.library[-3:] = [spell("S1", 7), spell("S2", 1), spell("S3", 4)]
    order = names(g.library[-3:])
    LH.sort_top_three(g, off_turn=True)
    check("G lorehold's Top unspun when {1} + a miracle cannot be paid",
          (g.float_mana, names(g.library[-3:]), g.m["top_unpaid"]),
          (2, order, 1))

    # H ---------------------------------------------------------------
    gamble = find(LM, "Gamble")
    a1, a2 = spell("A1"), spell("A2")
    g = make(LH.LoreholdGame, LM)
    g.hand = [gamble, a1]
    one = LH.pilot_may_cast(g, gamble)
    g.hand = [gamble, a1, a2]
    two = LH.pilot_may_cast(g, gamble)
    g.hand = [a1, a2]
    star = spell("Star", pri=9)
    g.library = fillers() + [star] + fillers(5)
    n = len(g.library)
    LH.apply_spell_effects(g, gamble)
    check("H Gamble: cast with two others; finds Star, discards one at random",
          (one, two, len(g.hand), len(g.graveyard), n - len(g.library),
           star in g.hand or star in g.graveyard),
          (False, True, 2, 1, 1, True))

    # I ---------------------------------------------------------------
    library = find(AM, "Sylvan Library")
    out = []
    for life in (25.0, 22.0):
        g = make(AZ.AzusaGame, AM)
        put(g, library)
        g.your_life = life
        g.library = fillers() + [spell("Low", pri=1), spell("Mid", pri=5),
                                 spell("High", pri=9)]
        before = len(g.hand)
        g.draw(1)
        EN.sylvan_library(g, before)
        out.append((sorted(names(g.hand)), names(g.library[-2:]), g.your_life))
    check("I Sylvan Library: keep the better for 4 life to the floor",
          out, [(["High", "Mid"], ["F19", "Low"], 21.0),
                (["High"], ["Low", "Mid"], 22.0)])

    # J ---------------------------------------------------------------
    abundance = find(AM, "Abundance")
    g = make(AZ.AzusaGame, AM)
    put(g, abundance)
    g.library = fillers(3) + [forest, spell("N1"), spell("N2")]
    g.draw(1)
    got = (names(g.hand), names(g.library[:2]), g.m["abundance_lands"])
    g.library = []
    g.draw(1)
    check("J Abundance: a land while short, the rest bottomed; no decking",
          (got, g.result, g.m["abundance_empty_saves"]),
          ((["Forest"], ["N2", "N1"], 1), None, 1))

    # K ---------------------------------------------------------------
    g = make(AZ.AzusaGame, AM)
    put(g, abundance)
    put(g, library)
    before = len(g.hand)
    g.draw(1)
    EN.sylvan_library(g, before)
    check("K Abundance + Library: nothing drawn, nothing back, no life",
          (len(g.hand), g.your_life, g.m["library_none_drawn"]), (3, 30.0, 1))

    # L ---------------------------------------------------------------
    heath = find(AM, "Windswept Heath")
    g = make(AZ.AzusaGame, AM)
    g.library = fillers() + [forest, heath] + fillers(3)
    g.resolve(find(AM, "Sylvan Scrying"))
    check("L Sylvan Scrying: the fetch over the Forest",
          names(g.hand), ["Windswept Heath"])

    # M ---------------------------------------------------------------
    g = make(AZ.AzusaGame, AM)
    put(g, forest, tapped=True)
    keep = put(g, find(AM, "Cavern of Souls"))
    g.library = fillers() + [find(AM, "Dust Bowl"), heath,
                             EN.Card(name="Forest", types=frozenset({"Land"}),
                                     is_land=True, produces=frozenset("G"))]
    g.resolve(find(AM, "Crop Rotation"))
    check("M Crop Rotation: the tapped Forest for the fetch, cracked",
          (keep in g.board, g.m["fetches_cracked"], g.m["landfall_triggers"],
           sorted(names(g.graveyard))),
          (True, 1, 2, ["Crop Rotation", "Forest", "Windswept Heath"]))

    # N ---------------------------------------------------------------
    g = make(AZ.AzusaGame, AM)
    g.commander_cast = True
    g.hand = [forest]
    az = EN.lands_short(g, 1)
    g = make(KA.KarlovGame, KM)
    check("N the land need: azusa's drops; karlov's one land",
          (az, EN.lands_short(g, 1), EN.lands_short(g, 0)),
          (True, False, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Item 24's change 4: which card do I want next (§0z139)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")

    def old_free_top(g, off_turn=False):
        if not g.has("Sensei's Divining Top") or len(g.library) < 3:
            return
        top3 = [g.library.pop() for _ in range(3)]
        top3.sort(key=lambda c: LH.miracle_value(g, c))
        g.library.extend(top3)

    real_abundance = AZ.abundance_draw

    def counted_as_drawn(g):
        real_abundance(g)
        g.__dict__.pop("abundance_ids", None)

    muts = {
        "the land need is never felt":
            ({"A", "J", "N"}, EN, "lands_short", lambda g, n: False),
        "karlov's tier is always 0":
            ({"B", "C"}, KA.KarlovGame, "want_tier", lambda self, c: 0),
        "Top's {1} is never paid":
            ({"D"}, KA, "pay_cost", lambda g, cost: True),
        "lorehold's Top is free again":
            ({"F", "G"}, LH, "sort_top_three", old_free_top),
        "Gamble finds nothing":
            ({"H"}, LH, "tutor_take", lambda g, pool, stream: None),
        "Abundance's cards count as drawn":
            ({"K"}, AZ, "abundance_draw", counted_as_drawn),
        "Abundance is a plain draw":
            ({"J", "K"}, AZ, "abundance_draw",
             lambda g: EN.BaseGame.draw(g, 1)),
        "azusa's lands are all one rank":
            ({"L", "M"}, AZ.AzusaGame, "land_rank", lambda self, c: 0.0),
        "every card is castable next turn":
            ({"A", "E"}, EN, "mana_next_turn", lambda g, n: 99),
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
