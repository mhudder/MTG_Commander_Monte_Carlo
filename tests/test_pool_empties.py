#!/usr/bin/env python3
"""§0z177: azusa's floating mana empties at the end of each step and phase.

    python -m tests.test_pool_empties
    python -m tests.test_pool_empties --mutate   # 3 mutations, exact sets

CR 500.5: "As a step or phase ends ... any unspent mana left in a player's
mana pool empties." Azusa's floating mana -- Lotus Cobra's, Nissa, Resurgent
Animist's, Nykthos's and Crystal Vein's (`bonus_mana`), Castle Garenbrig's six
{G} (`creature_mana`) -- was cleared only at the start of the next turn, so
the first main phase's leftover paid for combat and the second main phase,
and the second's paid for responses on the pod's turn (`response_pay`).
`AzusaGame.empty_mana_pool(where)` empties it at the end of main phase 1, of
combat and of main phase 2. A Treasure is a permanent and keeps. And a pilot
who knows the pool empties pays with it FIRST (`azusa_floating_first`).

CASES
  A  an unspent floating point is emptied at the end of main 1, and counted
     (`floating_mana_lost`, `floating_lost_main1`)
  B  a Treasure (`TreasureMana`) survives the empty
  C  Castle Garenbrig's six {G} are emptied and counted (`castle_mana_lost`)
  D  a point already SPENT this phase is dropped and not counted as lost
  E  NEIGHBOUR: `azusa_pool_empties=False` empties nothing
  F  after the end of main 2, a response on the pod's turn cannot pay with
     main 2's floating mana (`response_pay`, dry)
  G  a real turn empties the pool three times, in order: main1, combat, main2
  H  one Forest and one floating {G}, paying {G}: the floating point pays and
     the Forest stays untapped
  I  NEIGHBOUR: `azusa_floating_first=False` taps the Forest and keeps the
     floating point (the old order)
  J  a Treasure is still spent LAST: one Forest and one Treasure, paying {G},
     the Forest pays

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the empty drops Treasures too                     -> B
  azusa_pool_empties=False everywhere               -> A, C, D, F, H
  azusa_floating_first=False everywhere             -> H

THE FIRST MUTATION RUN FAILED TWO WAYS, AND BOTH WERE THE TEST. The first
stand-in rewrote the empty -- without the per-boundary count, the Castle count
or the knob -- so it broke A, C and E too: a stand-in that copies a signature
and not the function (§0z141). It runs the real empty on a pool whose
Treasures are plain floating mana now. And B asserted that ONLY the Treasure
was left, which also needs the floating point emptied, so the second mutation
broke it; B checks the one thing its label says now. The expected sets above
are as first written.

UNMUTATED (§0z15): E and I are the knobs' own neighbours. G records the calls
`take_turn` makes, so a mutation INSIDE `empty_mana_pool` cannot reach it; it
fails if a boundary's call is removed or moved past another. J holds under
every mutation because a Treasure's weight never changes.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card, Permanent, can_pay
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}          # a mutation's cfg overrides, under each case's own

DECK, CMD = M.build()
FOREST = Card(name="Forest", types=frozenset({"Land"}), is_land=True,
              produces=frozenset({"G"}))


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(points=0, lands=0, treasures=0, **cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, **{**EXTRA_CFG, **cfg}), 1234)
    g.board = EN.Board()
    g.bonus_mana = ([AZ.FloatingMana(frozenset({"G"})) for _ in range(points)]
                    + [AZ.TreasureMana(frozenset({"G"}))
                       for _ in range(treasures)])
    for _ in range(lands):
        g.board.append(Permanent(card=FOREST, sick=False))
    return g


def pay(g, cost):
    """Pay `cost` through the module's `spend` (§0z38's lesson)."""
    units = g.available_mana()
    got = can_pay(cost, units)
    if got is None:
        return False
    EN.spend(g, got, units)
    return True


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh(points=1)
    g.empty_mana_pool("main1")
    check("A an unspent point empties at the end of main 1, and is counted",
          (len(g.bonus_mana), g.m["floating_mana_lost"],
           g.m["floating_lost_main1"]), (0, 1, 1))

    g = fresh(points=1, treasures=1)
    g.empty_mana_pool("main1")
    check("B a Treasure survives the empty",
          sum(1 for f in g.bonus_mana if isinstance(f, AZ.TreasureMana)), 1)

    g = fresh()
    g.creature_mana = [frozenset({"G"})] * 6
    g.empty_mana_pool("main2")
    check("C Castle Garenbrig's six {G} empty, and are counted",
          (g.creature_mana, g.m["castle_mana_lost"],
           g.m["floating_lost_main2"]), ([], 6, 6))

    g = fresh(points=1)
    g.bonus_mana[0].tapped = True
    g.empty_mana_pool("combat")
    check("D a point spent this phase is dropped, not counted as lost",
          (len(g.bonus_mana), g.m["floating_mana_lost"]), (0, 0))

    g = fresh(points=1, azusa_pool_empties=False)
    g.creature_mana = [frozenset({"G"})] * 6
    g.empty_mana_pool("main1")
    check("E azusa_pool_empties=False empties nothing",
          (len(g.bonus_mana), len(g.creature_mana)), (1, 6))

    g = fresh(points=1)
    g.empty_mana_pool("main2")
    check("F no response on the pod's turn pays with main 2's floating mana",
          g.response_pay({"gen": 1}, dry=True), False)

    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, **EXTRA_CFG), 7)
    for o in g.opponents:
        o.life = float(10 ** 9)
    g.opening_hand()
    seen = []
    real = g.empty_mana_pool

    def record(where):
        seen.append(where)
        real(where)

    g.empty_mana_pool = record
    AZ.take_turn(g)
    check("G a turn empties the pool at main1, combat, main2, in order",
          seen, ["main1", "combat", "main2"])

    g = fresh(points=1, lands=1)
    pay(g, {"G": 1})
    check("H floating {G} pays before a Forest; the Forest stays untapped",
          (g.bonus_mana[0].tapped, g.board[0].tapped), (True, False))

    g = fresh(points=1, lands=1, azusa_floating_first=False)
    pay(g, {"G": 1})
    check("I azusa_floating_first=False taps the Forest, keeps the point",
          (g.bonus_mana[0].tapped, g.board[0].tapped), (False, True))

    g = fresh(lands=1, treasures=1)
    pay(g, {"G": 1})
    check("J a Treasure is still spent last: the Forest pays",
          (g.bonus_mana[0].tapped, g.board[0].tapped), (False, True))
    return set(FAIL)


REAL_EMPTY = AzusaGame.empty_mana_pool


def drops_treasures(self, where):
    """The mutation: the empty takes the Treasures with it -- the REAL empty,
    run on a pool whose Treasures have been made plain floating mana."""
    for f in self.bonus_mana:
        if isinstance(f, AZ.TreasureMana):
            f.__class__ = AZ.FloatingMana
    REAL_EMPTY(self, where)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z177: azusa's floating mana empties at each phase's end\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "the empty drops Treasures too":
            ({"B"}, (AzusaGame, "empty_mana_pool", drops_treasures), {}),
        "azusa_pool_empties=False everywhere":
            ({"A", "C", "D", "F", "H"}, None, {"azusa_pool_empties": False}),
        "azusa_floating_first=False everywhere":
            ({"H"}, None, {"azusa_floating_first": False}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        if patch:
            owner, name, fn = patch
            real = getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
                setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
