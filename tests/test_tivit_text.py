#!/usr/bin/env python3
"""§0z214: tivit's cards played by their text -- §0z207's behaviour items
2-6 and 8, and Nadier's Nightblade's life.

    python -m tests.test_tivit_text
    python -m tests.test_tivit_text --mutate   # 7 mutations, exact sets

Each fix is behind its own switch, and each switch False is the old rule:

  tempting_contract_text  Tempting Contract: `takers` Treasures, not 1 + takers
  grudge_each             Grudge Keeper: each voter loses 2, not one player 2k
  tivit_death_triggers    Nightblade hears a creature token die; Disciple and
                          Marionette hear a nontoken artifact reach the
                          graveyard (`opponents.destroy`); Portal counts the
                          creature tokens of its own wipe
  nightblade_life         Nadier's Nightblade's "and you gain 1 life"
  pile_text               convert_the_pile: Kambal is no drain; only
                          Treasures are sacrificed
  custodi_vote            Custodi Squire returns what the vote returns

Each case builds a tivit game with an empty battlefield, three opponents on
their starting life, and the board set by hand.

CASES
  A  Tempting Contract at `tempting_offer_rate` 1: three takers, 3 Treasures
  B  NEIGHBOUR: a tempting offer is still 1 + takers (Tempt with Bunnies)
  C  Grudge Keeper, three votes against: each opponent loses 2
  E  Nightblade, a creature token destroyed: each opponent 1, you 1
  F  Disciple of the Vault, Sol Ring destroyed: the pod loses 1 in all
  G  Marionette Master, Sol Ring destroyed: one opponent loses 4
  H  Disciple, Academy Manufactor (an artifact creature) destroyed: heard
     once -- the pod loses 1, not 2
  I  Nightblade, two Treasures sacrificed: you gain 2
  J  convert_the_pile with Kambal and Time Sieve only: the pile stays and
     five extra turns are taken
  K  convert_the_pile with Disciple: the Treasures go, a Clue, a Food and a
     Powerstone stay
  L  Custodi Squire, outvoted three to one: your WORST card returns
  M  Coercive Portal's carnage with Nightblade and two creature tokens: each
     token heard once, with the life
  N  NEIGHBOUR: Custodi with one opponent left (one vote each): a tie, both
     return

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  tempting_contract_text=False                   -> A
  grudge_each=False                              -> C
  tivit_death_triggers=False                     -> E, F, G, H, M
  nightblade_life=False                          -> E, I, M
  pile_text=False                                -> J, K
  custodi_vote=False                             -> L, N
  on_creature_death hears an artifact creature too (double count) -> H

UNMUTATED (§0z15): B is the tempting-offer rule the Contract no longer
shares. N is the tie, which only the vote switch reaches.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as TV
import edhmc.voting as V
from edhmc.engine import Permanent, Card
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.tivit import TivitGame

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("tivit")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = TivitGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    for k in g.tokens:
        g.tokens[k] = 0
    return g


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def put(g, *names):
    out = []
    for n in names:
        p = Permanent(card=take(g, n), sick=False)
        g.board.append(p)
        out.append(p)
    return out


def creature_token(g):
    p = Permanent(card=Card(name="Rabbit token",
                            types=frozenset({"Creature"}), power=1,
                            toughness=1), sick=False, is_token=True)
    g.board.append(p)
    return p


def lives(g):
    return [o.life for o in g.opponents]


def lost(g, before):
    return [b - a for a, b in zip(lives(g), before)]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh(tempting_offer_rate=1.0)
    put(g, "Tempting Contract")
    TV.upkeep(g)
    check("A Tempting Contract, three takers: 3 Treasures",
          g.tokens["Treasure"], 3)

    g = fresh(tempting_offer_rate=1.0)
    check("B a tempting offer is still 1 + takers", V.tempting_offer(g), 4)

    g = fresh()
    put(g, "Grudge Keeper")
    before = lives(g)
    V.dilemma(g)
    check("C Grudge Keeper: each opponent loses 2", lost(g, before),
          [2.0, 2.0, 2.0])

    g = fresh()
    put(g, "Nadier's Nightblade")
    tok = creature_token(g)
    before, life = lives(g), g.your_life
    OPP.destroy(g, tok, destroys=True)
    check("E Nightblade hears a creature token die, with the life",
          (lost(g, before), g.your_life - life), ([1.0, 1.0, 1.0], 1))

    g = fresh()
    put(g, "Disciple of the Vault")
    ring, = put(g, "Sol Ring")
    before = lives(g)
    OPP.destroy(g, ring, destroys=True)
    check("F Disciple hears Sol Ring destroyed: the pod loses 1",
          round(sum(lost(g, before)), 4), 1.0)

    g = fresh()
    put(g, "Marionette Master")
    ring, = put(g, "Sol Ring")
    before = lives(g)
    OPP.destroy(g, ring, destroys=True)
    check("G Marionette hears Sol Ring: one opponent loses 4",
          sorted(lost(g, before)), [0.0, 0.0, 4.0])

    g = fresh()
    put(g, "Disciple of the Vault")
    mfr, = put(g, "Academy Manufactor")
    before = lives(g)
    OPP.destroy(g, mfr, destroys=True)
    check("H an artifact creature is heard once",
          round(sum(lost(g, before)), 4), 1.0)

    g = fresh()
    put(g, "Nadier's Nightblade")
    g.tokens["Treasure"] = 2
    life = g.your_life
    TV.sacrifice_tokens(g, "Treasure", 2)
    check("I Nightblade, two Treasures sacrificed: you gain 2",
          g.your_life - life, 2)

    g = fresh()
    put(g, "Kambal, Profiteering Mayor", "Time Sieve")
    g.tokens["Treasure"] = 5
    turns = g.extra_turns
    TV.convert_the_pile(g)
    check("J Kambal alone is no drain: the pile stays, Time Sieve",
          (g.tokens["Treasure"], g.extra_turns - turns), (5, 5))

    g = fresh()
    put(g, "Disciple of the Vault")
    for k in ("Treasure", "Clue", "Food", "Powerstone"):
        g.tokens[k] = 1
    TV.convert_the_pile(g)
    check("K only the Treasures are sacrificed",
          [g.tokens[k] for k in ("Treasure", "Clue", "Food", "Powerstone")],
          [0, 1, 1, 1])

    g = fresh()
    squire = take(g, "Custodi Squire")
    best, worst = take(g, "Sol Ring"), take(g, "Lightning Greaves")
    best, worst = sorted((best, worst), key=lambda c: -c.priority)
    g.graveyard[:] = [best, worst]
    g.hand[:] = []
    TV.resolve(g, squire)
    check("L Custodi outvoted: the worst card returns",
          [c.name for c in g.hand], [worst.name])

    g = fresh()
    put(g, "Nadier's Nightblade", "Coercive Portal")
    creature_token(g)
    creature_token(g)
    g.tokens["Treasure"] = 1
    before, life = lives(g), g.your_life
    TV.coercive_carnage(g)
    check("M Portal's carnage: three tokens heard once, with the life",
          (lost(g, before), g.your_life - life), ([3.0, 3.0, 3.0], 3))

    g = fresh()
    for o in g.opponents[1:]:
        o.life = 0
    squire = take(g, "Custodi Squire")
    a, b = take(g, "Sol Ring"), take(g, "Lightning Greaves")
    g.graveyard[:] = [a, b]
    g.hand[:] = []
    TV.resolve(g, squire)
    check("N one opponent left, a tie: both return",
          sorted(c.name for c in g.hand), sorted([a.name, b.name]))
    return set(FAIL)


def _double(self, n=1, perm=None):
    if (not self.cfg.get("tivit_death_triggers", True)
            or self.death_lookback):
        return
    if perm is not None and perm.is_token:
        TV.creature_token_left(self, n)
    if perm is not None and EN.is_artifact(self, perm.card):
        TV._artifacts_left(self, 1)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z214: tivit's cards by their text\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "tempting_contract_text=False": ({"A"}, None,
                                         {"tempting_contract_text": False}),
        "grudge_each=False": ({"C"}, None, {"grudge_each": False}),
        "tivit_death_triggers=False": ({"E", "F", "G", "H", "M"}, None,
                                       {"tivit_death_triggers": False}),
        "nightblade_life=False": ({"E", "I", "M"}, None,
                                  {"nightblade_life": False}),
        "pile_text=False": ({"J", "K"}, None, {"pile_text": False}),
        "custodi_vote=False": ({"L", "N"}, None, {"custodi_vote": False}),
        "an artifact creature heard twice": ({"H"}, _double, {}),
    }
    bad = 0
    for label, (want, fn, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real = TivitGame.on_creature_death
        if fn is not None:
            TivitGame.on_creature_death = fn
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            TivitGame.on_creature_death = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
