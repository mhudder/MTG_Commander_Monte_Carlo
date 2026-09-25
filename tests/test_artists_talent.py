#!/usr/bin/env python3
"""Artist's Talent, all three levels (§0z48, queued item 2).

    python -m tests.test_artists_talent
    python -m tests.test_artists_talent --mutate   # 6 mutations, exact sets

    {1}{R} Enchantment — Class  (Scryfall, verified 2026-09-25)
    (Gain the next level as a sorcery to add its ability.)
    Whenever you cast a noncreature spell, you may discard a card. If you do,
    draw a card.
    {2}{R}: Level 2
    Noncreature spells you cast cost {1} less to cast.
    {2}{R}: Level 3
    If a source you control would deal noncombat damage to an opponent or a
    permanent an opponent controls, it deals that much damage plus 2 instead.

WHAT WAS WRONG. The card was one line in `reduce_cost`: `if g.has(...)`, so
level 2 arrived free the moment the Class resolved, it discounted CREATURE
spells as well, and levels 1 and 3 did not exist. The level is a property of
the permanent now (`Permanent.level`, CR 716.2d's default of 1), bought by a
stated policy (`artist_level_up`: spare post-combat mana, never the miracle
reserve).

CASES
  A  level 1: a noncreature spell is NOT discounted  -- the old reading was
  B  level 2: a noncreature spell costs {1} less
  C  level 2: a CREATURE spell is not discounted     -- the other old error
  D  the miracle discount follows the level: 0 at level 1, 1 at level 2
  E  level 1: casting a noncreature spell rummages (discard the pick, draw)
  F  casting a creature spell does not rummage
  G  before your draw step the rummage is declined
  H  level 3: one hit of 3 to one opponent deals 5
  I  level 3: LIFE LOSS (hits=0, Monument's drain) is not increased
  J  level 2: no damage bonus
  K1 three spare red-capable sources: level 1 -> 2
  K2 six: level 1 -> 3, in one main phase
  K3 three, with a miracle reserve of 1: stays at 1
  L  NEIGHBOUR: a fresh Permanent has level 1 (716.2d)
  M  the claim `hits=1` rests on: every lorehold card carrying `pod_damage`
     is single-target damage -- the set is exactly {Boros Charm}
  N  NEIGHBOUR, per §0z28: the rummage's discard triggers Monument to
     Endurance, which shares `discard_triggers` with Lorehold's own rummage
  O  level 3, Guttersnipe: 2 to each of three opponents becomes 4 each
  P  `artist_max_level=1` buys nothing

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the level is ignored (any Artist's Talent is level 3)  -> A, D, J
  the level-2 discount applies to creature spells too    -> C
  level 1's rummage does nothing                          -> E, N
  level 3 adds a flat +2 per call, ignoring hits          -> I, O
  level 3's bonus starts at level 2                       -> J
  the level-up policy ignores the miracle reserve         -> K3

UNMUTATED, and written down (§0z15): F and G pin gates inside
`artist_rummage` that no seam separates from the rest of it; L is a
dataclass default; M is a census, which fails when a card is added rather
than when code changes; P pins a knob; B, H, K1 and K2 are the positive
cases the mutations above are measured against.
"""
import sys

import edhmc.lorehold as L
import edhmc.opponents as OPP
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import lorehold_v16 as M
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


DECK, CMD = M.build()
ARTIST = next(c for c in DECK if c.name == "Artist's Talent")
MONUMENT = next(c for c in DECK if c.name == "Monument to Endurance")
SNIPE = next(c for c in DECK if c.name == "Guttersnipe")
SORCERY = Card(name="Test Sorcery", types=frozenset({"Sorcery"}),
               cost={"gen": 3, "R": 1})
BEAR = Card(name="Test Bear", types=frozenset({"Creature"}),
            cost={"gen": 3, "R": 1}, power=2, toughness=2)
FILLER = [Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
               cost={"gen": 1}) for i in range(20)]


def mountain():
    return Card(name="Mountain", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"R"}))


def game(level=None, mountains=0, **extra):
    g = L.LoreholdGame(list(DECK), CMD, dict(DEFAULT_CFG, **extra), 1)
    g.board = L.Board()
    g.hand = []
    g.graveyard = []
    g.library = list(FILLER)
    g.treasures = 0
    g.before_draw_step = False
    for o in g.opponents:
        o.life = 40.0
    if level is not None:
        g.board.append(Permanent(card=ARTIST, sick=False, level=level))
    for _ in range(mountains):
        g.board.append(Permanent(card=mountain(), sick=False))
    return g


def cost_of(level, card):
    return sum(L.reduce_cost(game(level), card).values())


def rummaged(card, before_draw=False, monument=False):
    g = game(1)
    if monument:
        g.board.append(Permanent(card=MONUMENT, sick=False))
    g.before_draw_step = before_draw
    g.hand = [BEAR]
    L.on_cast_triggers(g, card)
    return (g.m["artist_rummages"], [c.name for c in g.graveyard],
            g.m["monument_triggers"])


def dealt(level, amount, hits, each=False):
    g = game(level)
    L.deal_pod_damage(g, amount, each=each, hits=hits, spell=False)
    return round(g.m["spell_damage"], 3)


def levelled(mountains, reserve=0, **extra):
    g = game(1, mountains=mountains, **extra)
    L.artist_level_up(g, reserve=reserve)
    # the permanent's own level, not `artist_level` -- a mutation of that
    # reader must not be charged to the policy
    return next(p.level for p in g.board if p.card is ARTIST)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    check("A level 1: noncreature spell not discounted", cost_of(1, SORCERY), 4)
    check("B level 2: noncreature spell costs 1 less", cost_of(2, SORCERY), 3)
    check("C level 2: creature spell not discounted", cost_of(2, BEAR), 4)
    check("D miracle discount follows the level",
          (L.miracle_reduction(game(1), SORCERY),
           L.miracle_reduction(game(2), SORCERY)), (0, 1))
    check("E level 1: a noncreature cast rummages",
          rummaged(SORCERY)[:2], (1, ["Test Bear"]))
    check("F a creature cast does not rummage", rummaged(BEAR)[0], 0)
    check("G before the draw step the rummage is declined",
          rummaged(SORCERY, before_draw=True)[0], 0)
    check("H level 3: a 3-damage hit deals 5", dealt(3, 3.0, 1), 5.0)
    check("I level 3: life loss (hits=0) is not increased",
          dealt(3, 9.0, 0, each=True), 9.0)
    check("J level 2: no damage bonus", dealt(2, 3.0, 1), 3.0)
    check("K1 three spare sources: level 2", levelled(3), 2)
    check("K2 six spare sources: level 3", levelled(6), 3)
    check("K3 three sources, reserve 1: stays level 1", levelled(3, 1), 1)
    check("L a fresh Permanent has level 1",
          Permanent(card=SORCERY).level, 1)
    carriers = {c.name for c in list(DECK) + list(build_pending("lorehold")[0])
                + [v for v in vars(M).values() if isinstance(v, Card)]
                if getattr(c, "pod_damage", 0)}
    check("M every pod_damage card is single-target damage",
          carriers, {"Boros Charm"})
    check("N the rummage's discard triggers Monument",
          rummaged(SORCERY, monument=True)[2], 1)
    g = game(3)
    g.board.append(Permanent(card=SNIPE, sick=False))
    L.on_cast_triggers(g, SORCERY)
    check("O level 3 Guttersnipe: 4 to each of three", g.m["spell_damage"], 12.0)
    check("P artist_max_level=1 buys nothing",
          levelled(6, artist_max_level=1), 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Artist's Talent -- three levels\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(L, n) for n in
            ("artist_level", "artist_discount", "artist_rummage",
             "artist_bonus", "artist_level_up")}
    expected = {
        "the level is ignored (any Artist's Talent is level 3)": {"A", "D", "J"},
        "the level-2 discount applies to creature spells too": {"C"},
        "level 1's rummage does nothing": {"E", "N"},
        "level 3 adds a flat +2 per call, ignoring hits": {"I", "O"},
        "level 3's bonus starts at level 2": {"J"},
        "the level-up policy ignores the miracle reserve": {"K3"},
    }
    muts = {
        "the level is ignored (any Artist's Talent is level 3)":
            ("artist_level", lambda g: 3 if g.has("Artist's Talent") else 0),
        "the level-2 discount applies to creature spells too":
            ("artist_discount",
             lambda g, c: 1 if real["artist_level"](g) >= 2 else 0),
        "level 1's rummage does nothing":
            ("artist_rummage", lambda g: None),
        "level 3 adds a flat +2 per call, ignoring hits":
            ("artist_bonus",
             lambda g, hits: 2.0 if real["artist_level"](g) >= 3 else 0.0),
        "level 3's bonus starts at level 2":
            ("artist_bonus",
             lambda g, hits: 2.0 * hits if real["artist_level"](g) >= 2 else 0.0),
        "the level-up policy ignores the miracle reserve":
            ("artist_level_up",
             lambda g, reserve=0: real["artist_level_up"](g, reserve=0)),
    }
    bad = 0
    for label, (name, fn) in muts.items():
        print(f"-- {label}")
        setattr(L, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(L, name, real[name])
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
