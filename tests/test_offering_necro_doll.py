#!/usr/bin/env python3
"""Benevolent Offering (§0z56), Necropotence (§0z57), Twitching Doll (§0z58).

    python -m tests.test_offering_necro_doll
    python -m tests.test_offering_necro_doll --mutate   # 7 mutations

    Benevolent Offering {3}{W} Instant  (Scryfall, verified 2026-09-25)
    Choose an opponent. You and that player each create three 1/1 white
    Spirit creature tokens with flying.
    Choose an opponent. You gain 2 life for each creature you control and
    that player gains 2 life for each creature they control.
      -- was `lifegain=4`. BOTH sentences happen; it is not modal.

    Necropotence {B}{B}{B}
    Skip your draw step. Whenever you discard a card, exile that card from
    your graveyard. Pay 1 life: Exile the top card of your library face down.
    Put that card into your hand at the beginning of your next end step.
      -- was `script="draw2"`.

    Twitching Doll {1}{G} 2/2
    {T}: Add one mana of any color. Put a nest counter on this creature.
    {T}, Sacrifice this creature: Create a 2/2 green Spider creature token
    with reach for each counter on this creature. Activate only as a sorcery.
      -- neither clause existed, though the card was classified SCRIPTED.

CASES
  A  Offering with no creatures of yours: three flying Spirits, 6 life
  B  its Spirits go to the LEAST threatening opponent (+3 creatures)
  C  its lifegain goes to the opponent with the FEWEST creatures (2 each)
  D  NEIGHBOUR: Soul Warden sees all six Spirits enter (both sides)
  E  Necropotence, hand 3, life 40: buys 4 cards, pays 4 life
  F  life 12, empty hand: buys 2 -- the 10-life floor (the owner's, 2026-09-26;
     it was 20 and this case read "life 22")
  G  a one-card library: buys 1
  H  the cards are not DRAWN (`cards_drawn` does not move)
  I  with Necropotence out the draw step is skipped
  J  a Doll tapped for mana by `spend` gets a nest counter
  K  the end-of-turn nest tap gives a counter, and the Doll stays home
  L  at 3 counters it is sacrificed for 3 Spiders, reaches the graveyard,
     and its death is a death (Blood Artist drains)
  M  at 2 counters it is not

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  Offering is the old flat 4 life                 -> A, B, C, D
  the Spirits go to the MOST threatening opponent -> B, C
                  (C moves with it: the second choice is made after the
                  Spirits exist. Rewritten BEFORE the re-run -- the first
                  run's C failure was an ENGINE defect: both choices were
                  made up front.)
  Necropotence ignores the life floor             -> F
  Necropotence buys nothing                       -> E, F, G
  a mana tap adds no nest counter                 -> J, K
  the sacrifice ignores its threshold             -> M
  the sacrifice skips the death route             -> L

UNMUTATED, and written down (§0z15): H is a property of where the cards come
from, not a branch; I is inline in `take_turn`, with no seam.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


KDECK, KCMD = KM.build()
RDECK, RCMD = RM.build()


def kcard(name):
    return next(c for c in KDECK if c.name == name)


def rcard(name):
    return next(c for c in RDECK if c.name == name)


FILLER = [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                  cost={"gen": 1}) for i in range(30)]


def kgame(*cards, life=40.0, hand=0, lib=30, **cfg):
    g = K.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20, **cfg), 4242)
    g.board = EN.Board()
    g.hand = list(FILLER[:hand])
    g.library = list(FILLER[:lib])
    g.your_life = life
    g.turn = 6
    for i, o in enumerate(g.opponents):
        o.creatures = float(2 + i)          # 2, 3, 4
        o.life = 40.0
        o._pcache = dict(o.p, board=1.0 + i)   # threat rises with i
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def offering(*cards):
    g = kgame(*cards)
    before = [o.creatures for o in g.opponents]
    life0, olife0 = g.your_life, [o.life for o in g.opponents]
    K.benevolent_offering(g)
    spirits = [p for p in g.board if p.card.name == "Spirit token"]
    return g, before, life0, olife0, spirits


def rgame(*cards, **cfg):
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG, turns=20, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def doll_of(g):
    return next(p for p in g.board if p.card.name == "Twitching Doll")


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    g, before, life0, olife0, spirits = offering()
    check("A three flying Spirits and 6 life",
          (len(spirits), all(p.card.flying for p in spirits),
           g.your_life - life0), (3, True, 6.0))
    check("B the Spirits go to the least threatening opponent",
          [o.creatures - b for o, b in zip(g.opponents, before)], [3.0, 0.0, 0.0])
    # after B, opponent 0 has 5 creatures; fewest is now opponent 1 (3)
    check("C the lifegain goes to the opponent with the fewest creatures",
          [o.life - l for o, l in zip(g.opponents, olife0)], [0.0, 6.0, 0.0])
    g, *_ = offering(kcard("Soul Warden"))
    check("D Soul Warden sees all six Spirits",
          g.m["lifegain_triggers"], 7)       # six Warden gains + the Offering
    g = kgame(hand=3)
    g.board.append(EN.Permanent(card=kcard("Necropotence"), sick=False))
    K.necropotence_step(g)
    check("E hand 3, life 40: 4 cards for 4 life",
          (len(g.hand), g.your_life), (7, 36.0))
    g = kgame(kcard("Necropotence"), life=12.0)
    K.necropotence_step(g)
    check("F life 12, empty hand: 2 cards (the floor)", len(g.hand), 2)
    g = kgame(kcard("Necropotence"), lib=1)
    K.necropotence_step(g)
    check("G a one-card library: 1 card", len(g.hand), 1)
    g = kgame(kcard("Necropotence"))
    K.necropotence_step(g)
    check("H the cards are not drawn", g.m["cards_drawn"], 0)
    g = kgame(kcard("Necropotence"), hand=7, opponents=False)
    K.take_turn(g)
    check("I the draw step is skipped",
          (g.m["draw_steps_skipped"], g.m["cards_drawn"]), (1, 0))
    g = rgame(rcard("Twitching Doll"))
    units = EN.available_mana(g)
    idx = EN.can_pay({"G": 1}, units)
    EN.spend(g, idx, units)
    check("J a mana tap puts a nest counter on the Doll", doll_of(g).nest, 1)
    g = rgame(rcard("Twitching Doll"))
    EN.twitching_doll_nest(g)
    check("K the end-of-turn tap nests, and the Doll stays home",
          (doll_of(g).nest, EN.doll_stays_home(g, doll_of(g))), (1, True))
    g = rgame(rcard("Twitching Doll"), rcard("Blood Artist"))
    doll_of(g).nest = 3
    EN.twitching_doll_sacrifice(g)
    spiders = [p for p in g.board if p.card.name == "Spider token"]
    check("L 3 counters: 3 Spiders, graveyard, a death Blood Artist sees",
          (len(spiders), rcard("Twitching Doll") in g.graveyard,
           g.m["damage"] > 0), (3, True, True))
    g = rgame(rcard("Twitching Doll"))
    doll_of(g).nest = 2
    EN.twitching_doll_sacrifice(g)
    check("M 2 counters: no sacrifice", g.m["doll_sacrifices"], 0)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Benevolent Offering, Necropotence, Twitching Doll\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    def swapped(g):
        return max(OPP.living(g), key=lambda o: OPP.opponent_threat(o, g.turn))

    def no_floor(g):
        return max(0, min(7 - len(g.hand), int(g.your_life), len(g.library)))

    def sac_any(g):
        for p in [q for q in g.board if q.card.name == "Twitching Doll"]:
            if p.tapped or p.sick or p.nest < 1:
                continue
            g.board.remove(p)
            g.on_creature_death(1, p)
            g.graveyard.append(p.card)
            g.make_tokens(p.nest, 2, 2, "Spider")
            g.m["doll_sacrifices"] += 1

    def sac_quiet(g):
        for p in [q for q in g.board if q.card.name == "Twitching Doll"]:
            if p.tapped or p.sick or p.nest < 3:
                continue
            g.board.remove(p)
            g.graveyard.append(p.card)
            g.make_tokens(p.nest, 2, 2, "Spider")
            g.m["doll_sacrifices"] += 1

    muts = {
        "Offering is the old flat 4 life":
            ({"A", "B", "C", "D"}, K, "benevolent_offering",
             lambda g: K.gain_life(g, 4)),
        "the Spirits go to the most threatening opponent":
            ({"B", "C"}, K, "offering_token_target", swapped),
        "Necropotence ignores the life floor":
            ({"F"}, K, "necropotence_cards", no_floor),
        "Necropotence buys nothing":
            ({"E", "F", "G"}, K, "necropotence_cards", lambda g: 0),
        "a mana tap adds no nest counter":
            ({"J", "K"}, EN, "on_mana_tap", lambda g, p: None),
        "the sacrifice ignores its threshold":
            ({"M"}, EN, "twitching_doll_sacrifice", sac_any),
        "the sacrifice skips the death route":
            ({"L"}, EN, "twitching_doll_sacrifice", sac_quiet),
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
