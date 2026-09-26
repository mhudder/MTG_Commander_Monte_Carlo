#!/usr/bin/env python3
"""Treasures as mana in rendmaw, and Pitiless Plunderer (§0z64).

    python -m tests.test_treasures
    python -m tests.test_treasures --mutate   # 6 mutations, exact sets

    Pitiless Plunderer {3}{B} 1/4  (Scryfall, verified 2026-09-16)
    Whenever another creature you control dies, create a Treasure token.
    (It's an artifact with "{T}, Sacrifice this token: Add one mana of any
    color.")

Rendmaw had no Treasures, so the Plunderer was abandoned in §0z26. Now
`Game.treasures` is a pile, `make_treasures` fills it through the same
doubling as every other token (`token_doublings`), and `rendmaw_mana` appends
one any-colour unit per Treasure whose owner is a `TreasureMana`: `spend`
taps it, and tapping it sacrifices it.

CASES
  A  PROPERTY: with no Treasures, `rendmaw_mana` is `available_mana` --
     units, owners' identity and weights -- over 200 random boards
  B  a death with the Plunderer out: one Treasure
  C  the Plunderer's own death: none ("another")
  D  Parallel Lives: two per death; Primal Vigor as well: four
  E  paying {1} from a Swamp and a Treasure: the Swamp is spent, the
     Treasure kept
  F  paying {2} from the same: the Treasure is spent (and counted)
  G  a Treasure pays a colour no land makes: {B} from a Forest + a Treasure
  H  main_phase casts a {1}{B} card it can only afford with the Treasure
  I  Skullclamp's loop, paid with a Treasure, spends it (`tap_treasures`)
  J  making a Treasure counts as making a token (Idol of Oblivion)
  K  NEIGHBOUR: `make_tokens` still doubles under Parallel Lives

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the Plunderer does not trigger (plunderer_count 0)   -> B, D
  Treasures are not mana (rendmaw_mana = available_mana) -> F, G, H, I
  tapping a Treasure does not sacrifice it              -> F, G, H, I
  token doubling ignored                                -> D, K
  Skullclamp does not spend its Treasure                -> I
  a Treasure is not a token (Idol of Oblivion)          -> J

  ONE EXPECTATION WAS WRONG, AND IT IS KEPT HERE. The first list had
  "Treasures are spent BEFORE lands (their weight set to 0) -> E". It broke
  NOTHING: `can_pay` spends the least flexible source first, so a
  five-colour Treasure loses every tie to a land before the weight is read.
  The FOREIGN weight is redundant for this pool, and E is really pinned by
  can_pay's flexibility rule. The mutation was replaced with J's, which has
  a seam.

UNMUTATED, and written down (§0z15): A is the property that the committed
list (which makes no Treasures) is unchanged; C is an absence that falls out
of the Plunderer having left the board, with no seam; E's protection is
can_pay's flexibility rule, shared by every engine and pinned elsewhere.
"""
import random
import sys

import edhmc.engine as EN
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = RM.build()
PLUNDERER = RM.PITILESS_PLUNDERER
BEAR = EN.Card(name="Test Bear", types=frozenset({"Creature"}),
               cost={"gen": 1, "B": 1}, power=2, toughness=2, priority=5)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(name, colour):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({colour}))


def card(name):
    """From the list, or from the module's named candidates (Parallel Lives
    is a candidate constant, not in the committed list)."""
    pool = list(DECK) + [v for v in vars(RM).values() if isinstance(v, EN.Card)]
    return next(c for c in pool if c.name == name)


def game(*cards, treasures=0):
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, turns=20),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"F{i}", types=frozenset({"Sorcery"}),
                         cost={"gen": 9}) for i in range(20)]
    g.treasures = treasures
    g.commander_cast = True
    g.turn = 6
    for o in g.opponents:
        o.counters_left = 0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def dies(g, name="Bear"):
    victim = EN.Permanent(card=EN.Card(name=name, types=frozenset({"Creature"}),
                                       power=1, toughness=1), sick=False)
    g.on_creature_death(1, victim)


def paid(cost, *cards, treasures=1):
    """Pay `cost` through can_pay/spend; return (paid?, Treasures left)."""
    g = game(*cards, treasures=treasures)
    units = EN.rendmaw_mana(g)
    idx = EN.can_pay(cost, units)
    if idx is not None:
        EN.spend(g, idx, units)
    return idx is not None, g.treasures, g.m["treasures_spent"]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    rnd, same = random.Random(3), True
    pool = [c for c in DECK if c.is_land or c.mana_ability]
    for _ in range(200):
        g = game(*rnd.sample(pool, rnd.randint(0, 10)))
        a, b = EN.rendmaw_mana(g), EN.available_mana(g)
        same &= (list(a) == list(b) and a.weights == b.weights
                 and [id(o) for o in a.owners] == [id(o) for o in b.owners])
    check("A no Treasures: rendmaw_mana is available_mana, 200 boards",
          same, True)
    g = game(PLUNDERER)
    dies(g)
    check("B a death with the Plunderer out: one Treasure", g.treasures, 1)
    g = game()
    g.on_creature_death(1, EN.Permanent(card=PLUNDERER, sick=False))
    check("C the Plunderer's own death: none", g.treasures, 0)
    g1 = game(PLUNDERER, card("Parallel Lives"))
    dies(g1)
    g2 = game(PLUNDERER, card("Parallel Lives"), card("Primal Vigor"))
    dies(g2)
    check("D Parallel Lives 2 per death; with Primal Vigor 4",
          (g1.treasures, g2.treasures), (2, 4))
    check("E {1} from a Swamp and a Treasure: the Treasure is kept",
          paid({"gen": 1}, land("Swamp", "B"))[:2], (True, 1))
    check("F {2} from the same: the Treasure is spent",
          paid({"gen": 2}, land("Swamp", "B")), (True, 0, 1))
    check("G {B} from a Forest + a Treasure",
          paid({"B": 1}, land("Forest", "G"))[:2], (True, 0))
    g = game(land("Forest", "G"), treasures=1)
    g.hand = [BEAR]
    EN.main_phase(g)
    check("H main_phase casts a {1}{B} card with the Treasure",
          (any(p.card is BEAR for p in g.board), g.treasures), (True, 0))
    g = game(RM.SKULLCLAMP, treasures=1)
    g.board.append(EN.Permanent(card=EN.Card(name="Saproling token",
                                             types=frozenset({"Creature"}),
                                             power=1, toughness=1),
                                sick=False, is_token=True))
    EN.activations(g)
    check("I Skullclamp paid with a Treasure spends it",
          (g.m["clamp_activations"], g.treasures), (1, 0))
    g = game()
    g.make_treasures(1)
    check("J a Treasure counts as a token made", g.made_token_this_turn, True)
    g = game(card("Parallel Lives"))
    g.make_tokens(1, 1, 1, "Saproling")
    check("K NEIGHBOUR: make_tokens doubles under Parallel Lives",
          g.m["tokens_made"], 2)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Treasures as mana in rendmaw; Pitiless Plunderer\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_setter = EN.TreasureMana.tapped

    def not_a_token(self, n):
        n *= EN.token_doublings(self)
        self.treasures += n
        self.m["treasures_made"] += n

    muts = {
        "the Plunderer does not trigger":
            ({"B", "D"}, EN, "plunderer_count", lambda g: 0),
        "Treasures are not mana":
            ({"F", "G", "H", "I"}, EN, "rendmaw_mana", EN.available_mana),
        "tapping a Treasure does not sacrifice it":
            ({"F", "G", "H", "I"}, EN.TreasureMana, "tapped",
             property(lambda self: self.used, lambda self, v: None)),
        "token doubling ignored":
            ({"D", "K"}, EN, "token_doublings", lambda g: 1),
        "Skullclamp does not spend its Treasure":
            ({"I"}, EN, "tap_treasures", lambda units, pay: None),
        "a Treasure is not a token":
            ({"J"}, EN.Game, "make_treasures", not_a_token),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        real = (mod.__dict__[name] if isinstance(mod, type)
                else getattr(mod, name))
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    assert EN.TreasureMana.tapped is real_setter
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
