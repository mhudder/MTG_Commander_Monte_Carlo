#!/usr/bin/env python3
"""§0z183: azusa spends the floating mana that is about to empty on its
activations -- Eye of Ugin, then Clues -- before the pool empties.

    python -m tests.test_floating_sink
    python -m tests.test_floating_sink --mutate   # 3 mutations, exact sets

§0z177 made azusa's floating mana empty at the end of each phase (CR 500.5)
and left one question: `activations` (Eye of Ugin, Clues) waits until after
combat, so main phase 1's leftover vanished while a Clue sat uncracked.
`AzusaGame.floating_sink`, called by `empty_mana_pool` before it empties,
pays for them from the FLOATING mana only -- never a land, never a Treasure.

Each case builds a game with an empty battlefield and sets the pool, the
lands and the Clues by hand.

CASES
  A  two floating points, one Clue: cracked from the float, a card drawn,
     counted at its boundary, the Forest left untapped
  B  one floating point and two untapped Forests, one Clue: nothing (the
     float alone cannot pay, and a Forest is never added to it)
  C  one floating point and two Treasures, one Clue: nothing (a Treasure
     keeps)
  D  one floating point, one Clue: cannot pay, the point empties
  E  Eye of Ugin with seven floating points: a colourless creature fetched
  F  NEIGHBOUR: `azusa_floating_sink=False`: the Clue stays, the two empty
  G  `empty_mana_pool` runs the sink: the Clue is cracked, nothing is lost
  H  NEIGHBOUR: `activations` still cracks a Clue with land mana

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  azusa_floating_sink=False everywhere           -> A, E, G
  floating_units returns the whole pool          -> B, C
  floating_units keeps Treasures (isinstance)    -> C

UNMUTATED (§0z15): D, F and H are the neighbours -- the sink's no-op when the
float cannot pay, the switch, and the post-combat path the refactor moved
into `crack_clues`. B and C are what pin "floating ONLY": the first mutation
cannot reach them, since a sink that never runs spends nothing. Each holds
ONE floating point: with none, the sink returns before `floating_units` is
read, and the two pool mutations could not reach B or C either (caught
before the first run, when the cases were written with no float).
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def forest():
    return Permanent(card=Card(name="Forest", types=frozenset({"Land"}),
                               is_land=True, produces=frozenset({"G"})),
                     sick=False)


def fresh(points=0, treasures=0, lands=0, clues=0, **cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.bonus_mana = ([AZ.FloatingMana(frozenset({"G"})) for _ in range(points)]
                    + [AZ.TreasureMana(frozenset({"G"}))
                       for _ in range(treasures)])
    for _ in range(lands):
        g.board.append(forest())
    g.clues = clues
    return g


def floating_left(g):
    return sum(1 for f in g.bonus_mana
               if type(f) is AZ.FloatingMana and not f.tapped)


def colourless_creature(c):
    return (c.is_creature and not c.is_land
            and not any(c.cost.get(k) for k in "WUBRG"))


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh(points=2, lands=1, clues=1)
    hand = len(g.hand)
    g.floating_sink("main1")
    check("A two floating, one Clue: cracked from the float",
          (g.clues, len(g.hand) - hand, floating_left(g),
           g.m["floating_clues_main1"], g.board[0].tapped),
          (0, 1, 0, 1, False))

    g = fresh(points=1, lands=2, clues=1)
    hand = len(g.hand)
    g.floating_sink("main1")
    check("B one float, two Forests: nothing",
          (g.clues, len(g.hand) - hand, [p.tapped for p in g.board]),
          (1, 0, [False, False]))

    g = fresh(points=1, treasures=2, clues=1)
    g.floating_sink("main1")
    check("C one float, two Treasures: nothing, the Treasures keep",
          (g.clues, sum(1 for f in g.bonus_mana if not f.tapped)), (1, 3))

    g = fresh(points=1, clues=1)
    g.empty_mana_pool("main1")
    check("D one point cannot pay: the Clue stays, the point empties",
          (g.clues, g.m["floating_mana_lost"]), (1, 1))

    g = fresh(points=7)
    eye = next(c for c in DECK if c.name == "Eye of Ugin")
    g.board.append(Permanent(card=eye, sick=False))
    for c in [c for c in g.hand if colourless_creature(c)]:
        EN.remove_card(g.hand, c)
        g.library.insert(0, c)
    wanted = any(colourless_creature(c) for c in g.library)
    g.floating_sink("main1")
    check("E Eye of Ugin on seven floating: a colourless creature fetched",
          (wanted, any(colourless_creature(c) for c in g.hand),
           g.m["floating_eye_tutors"], floating_left(g)),
          (True, True, 1, 0))

    g = fresh(points=2, clues=1, azusa_floating_sink=False)
    g.empty_mana_pool("main1")
    check("F azusa_floating_sink=False: the Clue stays, two empty",
          (g.clues, g.m["floating_mana_lost"]), (1, 2))

    g = fresh(points=2, clues=1)
    g.empty_mana_pool("main1")
    check("G empty_mana_pool runs the sink: cracked, nothing lost",
          (g.clues, g.m["floating_mana_lost"], g.m["floating_clues"]),
          (0, 0, 1))

    g = fresh(lands=2, clues=1)
    hand = len(g.hand)
    g.activations()
    check("H activations still cracks a Clue with land mana",
          (g.clues, len(g.hand) - hand), (0, 1))
    return set(FAIL)


def _whole_pool(self):
    return self.available_mana()


def _with_treasures(self):
    u = self.available_mana()
    idx = [i for i, o in enumerate(u.owners)
           if isinstance(o, AZ.FloatingMana) and not o.tapped]
    return EN.ManaUnits([u[i] for i in idx], [u.owners[i] for i in idx],
                        [u.weights[i] for i in idx], legacy=u.legacy,
                        surplus=u.surplus)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z183: azusa's floating mana pays its activations\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "azusa_floating_sink=False everywhere":
            ({"A", "E", "G"}, None, {"azusa_floating_sink": False}),
        "floating_units returns the whole pool":
            ({"B", "C"}, _whole_pool, {}),
        "floating_units keeps Treasures (isinstance)":
            ({"C"}, _with_treasures, {}),
    }
    bad = 0
    for label, (want, fn, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real = AzusaGame.floating_units
        if fn is not None:
            AzusaGame.floating_units = fn
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            AzusaGame.floating_units = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
