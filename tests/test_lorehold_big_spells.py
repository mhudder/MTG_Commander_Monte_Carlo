#!/usr/bin/env python3
"""The owner's second lorehold batch: seven big instants and sorceries
(2026-10-09), one assertion per modelled clause.

    python -m tests.test_lorehold_big_spells
    python -m tests.test_lorehold_big_spells --mutate   # 6 mutations, exact sets

Oracle text from api.scryfall.com, 2026-10-09, verbatim on each Proposal in
edhmc/pending.py.

CASES
  A  FURYGALE FLOCKING, three sorceries in the graveyard: the hardcast costs
     {5}{R}{R} and the miracle {2} costs nothing (601.2f)
  B  Furygale, an empty graveyard: {8}{R}{R}, and the miracle costs {2}
  C  Furygale resolves, three opponents: six 3/3 FLYING tokens, unsick;
     with one opponent dead, four
  D  SEARING WIND: 10 to the opponent closest to dying, nobody else
  E  EXPLOSIVE WELCOME: 5 to the lowest, 3 to the NEXT -- two targets
  F  Welcome, the lowest on 3: the 3 kills them and the 5 goes to the next
  G  Welcome's {R}{R}{R}: kept in a main phase, lost outside one (500.4)
  H  GIDEON'S PHALANX: four 2/2 Knights, not flying; spell mastery counted
  I  RAPHAEL'S TECHNIQUE: the hand of three to the graveyard, seven drawn
  J  IMMOLATING GYRE, X = 3, `gyre_full_x` 6: half of each pod board dies,
     and your own creature survives (one-sided)
  K  Gyre, X = 7: every pod creature dies
  L  PROFOUND JOURNEY: Sol Ring and a Mountain in the graveyard -- Sol Ring
     returns, the Mountain stays
  M  Journey from HAND in the main phase: REBOUND exiles it, the next upkeep
     casts it free for a second return, and then it is in the graveyard
  N  Journey, no permanent card in the graveyard: no legal target, no cast
  O  NEIGHBOUR: a Pinnacle Monk returned by Journey still regrows a spell --
     the ETBs moved into `enters_battlefield` with the reanimation path

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  `self_reduction` returns 0                        -> A
  `damage_single` ignores `target`                  -> E
  REBOUND is empty                                  -> M
  `reanimation_target` finds nothing                -> L, M, O
  `gyre_share` is always 1                          -> J
  `enters_battlefield` puts the card down, no ETBs  -> O

UNMUTATED (§0z15): B, D, H, I and K have no seam of their own here -- the
wheel and the token path are pinned by older tests -- and G's lost branch is
the default when nothing sets `in_main`. F is unreachable by the `target`
mutation, deliberately: with the lowest on 3, the closest-to-dying pick lands
both halves where the pilot's plan put them.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
import edhmc.opponents as OPP
from edhmc.decks import lorehold_v17 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

DECK, CMD = LM.build()
FURY = LM.FURYGALE_FLOCKING
WIND = LM.SEARING_WIND
WELCOME = LM.EXPLOSIVE_WELCOME
PHALANX = LM.GIDEONS_PHALANX
RAPHAEL = LM.RAPHAELS_TECHNIQUE
GYRE = LM.IMMOLATING_GYRE
JOURNEY = LM.PROFOUND_JOURNEY
SOL_RING = next(c for c in DECK if c.name == "Sol Ring")
MONK = next(c for c in DECK if c.name == "Pinnacle Monk")
BOROS_CHARM = next(c for c in DECK if c.name == "Boros Charm")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def lands(name, colour, n):
    return [EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                    produces=frozenset({colour})) for _ in range(n)]


def sorceries(n):
    return [EN.Card(name=f"Spent {i}", types=frozenset({"Sorcery"}),
                    cost={"gen": 1}) for i in range(n)]


def filler(n):
    return [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                    cost={"gen": 9}) for i in range(n)]


def game(**cfg):
    g = L.LoreholdGame(list(DECK), CMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard, g.dream_exile = [], [], []
    g.library = filler(20)
    g.turn = 1                      # before the pod's counterspells start
    g.treasures = 0
    for o in g.opponents:
        o.life, o.alive, o.creatures = 40.0, True, 0.0
    return g


def lives(g):
    return tuple(round(o.life, 2) for o in g.opponents)


def set_lives(g, *ls):
    for o, life in zip(g.opponents, ls):
        o.life = life


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    g.graveyard.extend(sorceries(3))
    check("A Furygale, three in the yard: hardcast {5}{R}{R}, miracle free",
          (L.reduce_cost(g, FURY), L.miracle_need(g, FURY)),
          ({"gen": 5, "R": 2}, 0))

    g = game()
    check("B Furygale, empty yard: {8}{R}{R}, miracle {2}",
          (L.reduce_cost(g, FURY), L.miracle_need(g, FURY)),
          ({"gen": 8, "R": 2}, 2))

    g = game()
    L.apply_spell_effects(g, FURY)
    toks = [p for p in g.board if p.is_token]
    g2 = game()
    g2.opponents[0].life, g2.opponents[0].alive = 0.0, False
    L.apply_spell_effects(g2, FURY)
    check("C Furygale: six 3/3 unsick fliers; four with one opponent dead",
          (len(toks), {(p.card.power, p.card.toughness, p.card.flying,
                        p.sick) for p in toks},
           sum(1 for p in g2.board if p.is_token)),
          (6, {(3, 3, True, False)}, 4))

    g = game()
    set_lives(g, 40.0, 15.0, 30.0)
    L.apply_spell_effects(g, WIND)
    check("D Searing Wind: 10 to the lowest only", lives(g),
          (40.0, 5.0, 30.0))

    g = game()
    set_lives(g, 40.0, 20.0, 30.0)
    L.apply_spell_effects(g, WELCOME)
    check("E Explosive Welcome: 5 to the lowest, 3 to the next", lives(g),
          (40.0, 15.0, 27.0))

    g = game()
    set_lives(g, 40.0, 3.0, 30.0)
    L.apply_spell_effects(g, WELCOME)
    check("F Welcome, lowest on 3: the 3 kills, the 5 goes on",
          (lives(g), g.opponents[1].alive), ((40.0, 0.0, 25.0), False))

    g = game()
    g.in_main = True
    L.apply_spell_effects(g, WELCOME)
    kept = (g.apex_mana, g.apex_color)
    g = game()
    L.apply_spell_effects(g, WELCOME)
    check("G Welcome's {R}{R}{R}: kept in a main phase, lost outside",
          (kept, g.apex_mana, g.m["welcome_mana_lost"]),
          ((3, "R"), 0, 3))

    g = game()
    g.graveyard.extend(sorceries(2))
    L.apply_spell_effects(g, PHALANX)
    toks = [p for p in g.board if p.is_token]
    check("H Phalanx: four 2/2 Knights, not flying; mastery counted",
          (len(toks), {(p.card.power, p.card.toughness, p.card.flying)
                       for p in toks}, g.m["phalanx_mastery"]),
          (4, {(2, 2, False)}, 1))

    g = game()
    g.hand.extend(sorceries(3))
    L.apply_spell_effects(g, RAPHAEL)
    check("I Raphael's Technique: three to the yard, seven drawn",
          (len(g.graveyard), len(g.hand), g.m["wheel_casts"]), (3, 7, 1))

    g = game()
    g.graveyard.extend(sorceries(3))
    for o in g.opponents:
        o.creatures = 4.0
    mine = EN.Permanent(card=MONK, sick=False)
    g.board.append(mine)
    L.apply_spell_effects(g, GYRE)
    check("J Gyre, X = 3 of 6: half of each pod board, yours spared",
          (tuple(o.creatures for o in g.opponents), mine in g.board),
          ((2.0, 2.0, 2.0), True))

    g = game()
    g.graveyard.extend(sorceries(7))
    for o in g.opponents:
        o.creatures = 4.0
    L.apply_spell_effects(g, GYRE)
    check("K Gyre, X = 7: every pod creature dies",
          tuple(o.creatures for o in g.opponents), (0.0, 0.0, 0.0))

    g = game()
    mtn = lands("Mountain", "R", 1)[0]
    g.graveyard.extend([mtn, SOL_RING])
    L.apply_spell_effects(g, JOURNEY)
    check("L Journey: Sol Ring returns, the Mountain stays",
          ([p.card.name for p in g.board], g.graveyard == [mtn],
           g.m["journey_returns"]),
          (["Sol Ring"], True, 1))

    g = game()
    for c in lands("Plains", "W", 7):
        g.board.append(EN.Permanent(card=c, sick=False))
    g.graveyard.extend([SOL_RING, MONK])
    g.hand.append(JOURNEY)
    L.main_phase(g, reserve=0)
    exiled = (JOURNEY in g.rebound_exile, JOURNEY in g.graveyard)
    L.rebound_upkeep(g)
    check("M Journey from hand: rebound, a second free return, then the yard",
          (exiled, g.m["rebound_casts"], g.m["journey_returns"],
           JOURNEY in g.graveyard, g.rebound_exile),
          ((True, False), 1, 2, True, []))

    g = game()
    g.graveyard.extend(sorceries(2))
    check("N Journey, no permanent card in the yard: no cast",
          L.pilot_may_cast(g, JOURNEY), False)

    g = game()
    g.graveyard.extend([MONK, BOROS_CHARM])
    L.apply_spell_effects(g, JOURNEY)
    check("O NEIGHBOUR: a returned Pinnacle Monk regrows a spell",
          (any(p.card is MONK for p in g.board), BOROS_CHARM in g.hand,
           g.m["monk_returns"]),
          (True, True, 1))
    return set(FAIL)


def _ignore_target(orig):
    def wrapped(g, n, target=None):
        return orig(g, n)
    return wrapped


def _no_etb(_orig):
    def wrapped(g, card):
        g.board.append(EN.Permanent(card=card, sick=not card.haste))
    return wrapped


# (label, module, attribute, replacement factory, expected broken set)
MUTATIONS = [
    ("`self_reduction` returns 0", L, "self_reduction",
     lambda _o: (lambda g, card: 0), {"A"}),
    ("`damage_single` ignores `target`", OPP, "damage_single",
     _ignore_target, {"E"}),
    ("REBOUND is empty", L, "REBOUND", lambda _o: frozenset(), {"M"}),
    ("`reanimation_target` finds nothing", L, "reanimation_target",
     lambda _o: (lambda g: None), {"L", "M", "O"}),
    ("`gyre_share` is always 1", OPP, "gyre_share",
     lambda _o: (lambda g: 1.0), {"J"}),
    ("`enters_battlefield` puts the card down, no ETBs", L,
     "enters_battlefield", _no_etb, {"O"}),
]


def main() -> int:
    if not MUTATE:
        print("Lorehold's second 2026-10-09 batch: seven big spells\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    good = 0
    for label, mod, attr, make, want in MUTATIONS:
        saved = getattr(mod, attr)
        setattr(mod, attr, make(saved))
        try:
            broke = run_cases()
        finally:
            setattr(mod, attr, saved)
        ok = broke == want
        good += ok
        print(f"   {label}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    bad = len(MUTATIONS) - good
    print(f"{good} passed, {bad} failed ({len(MUTATIONS)} mutations, "
          f"exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
