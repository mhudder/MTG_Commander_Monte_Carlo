#!/usr/bin/env python3
"""§0z37 — floating landfall mana is consumed when it is spent.

    python -m tests.test_floating_mana
    python -m tests.test_floating_mana --mutate   # 3 mutations, exact sets

WHAT WENT WRONG. `engine.spend` consumes a unit BY TAPPING ITS OWNER. Azusa's
landfall mana -- Lotus Cobra's, Tireless Provisioner's and Nissa, Resurgent
Animist's -- was appended to the pool with `owner=None`, because nothing on the
battlefield taps for it. So it was paid with and NEVER CONSUMED: one trigger
funded every spell cast that turn, and `main_phase` recast Awaken the Woods 258
times in a single turn off it (an eleven-hour hang, seed 6328).

THE FIX IS AN OWNER, NOT A DEDUCTION AT THE CALL SITE. `FloatingMana` is not a
permanent but does have a `tapped` flag, so the existing mechanism applies with
no change to `spend` and none to azusa's payment sites. The two pools that were
already correct -- lorehold's Treasures and this engine's own Castle Garenbrig
`creature_mana` -- each deduct by index arithmetic at their call site, and a
third spelling of that would have been §0u's shape for the fourth time.

CASES
  A  one point pays once and is then no longer offered
  B  a second payment of the same cost cannot be made
  C  two points pay two spells -- not one spell twice
  D  the pool is cleared with the turn, like any unspent mana
  E  paying with a LAND leaves floating mana untouched (no over-consumption)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the spent flag is ignored when the pool is read  -> A, B and C
  the turn does not clear the floating pool        -> D
  every payment also consumes a floating point     -> C and E

The third is the OPPOSITE failure mode and is here because a fix that consumes
too much would pass every other case in this file. It breaks C as well as E:
with two points and two payments, an extra mark per payment exhausts the pool
before the second spell.
"""
import sys

from edhmc.azusa import AzusaGame
import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card, Permanent, can_pay

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(points=0, lands=0):
    deck, cmd = M.build()
    g = AzusaGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)
    g.board = EN.Board()
    g.bonus_mana = [AZ.FloatingMana(frozenset({"G"})) for _ in range(points)]
    for i in range(lands):
        g.board.append(Permanent(card=Card(
            name="Forest", types=frozenset({"Land"}), is_land=True,
            produces=frozenset({"G"})), sick=False))
    return g


def pay_one(g, cost=None):
    """Pay {G} if it can be paid. True if the payment happened."""
    units = g.available_mana()
    got = can_pay(cost or {"G": 1}, units)
    if got is None:
        return False
    # THROUGH THE MODULE, deliberately. `from edhmc.engine import spend` binds
    # the function into this file, and a mutation that replaces `EN.spend`
    # never reaches a call made through that local name -- the third mutation
    # below broke NOTHING on its first run for exactly that reason, which is
    # §0z38's lesson arriving one file later: when a mutation breaks nothing,
    # the first suspect is the mutation.
    EN.spend(g, got, units)
    return True


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A: one point pays once, then is not offered ----------------------
    g = fresh(points=1)
    before = len(g.available_mana())
    paid = pay_one(g)
    check("A one floating point pays once and is then not offered",
          (before, paid, len(g.available_mana())), (1, True, 0))

    # ---- B: the second payment cannot be made -----------------------------
    g = fresh(points=1)
    pay_one(g)
    check("B a second payment of the same cost cannot be made",
          pay_one(g), False)

    # ---- C: two points pay two spells -------------------------------------
    g = fresh(points=2)
    first, second = pay_one(g), pay_one(g)
    check("C two points pay two spells, and the pool is then empty",
          (first, second, len(g.available_mana())), (True, True, 0))

    # ---- D: the pool clears with the turn ---------------------------------
    g = fresh(points=2)
    AZ.take_turn(g)
    check("D the floating pool is cleared with the turn",
          len(g.bonus_mana), 0)

    # ---- E: a land payment does not consume floating mana -----------------
    g = fresh(points=1, lands=2)
    units = g.available_mana()
    # pay {G}{G}: two lands can cover it, and a correct `spend` taps the two
    # lands it was assigned rather than reaching into the floating pool.
    got = can_pay({"G": 2}, units)
    assert got is not None, "two Forests should cover {G}{G}"
    EN.spend(g, got, units)
    left = sum(1 for f in g.bonus_mana if not f.tapped)
    check("E paying from lands leaves the floating point untouched", left, 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z37 -- floating landfall mana is consumed when spent\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_avail = AZ.AzusaGame.available_mana
    real_take = AZ.take_turn
    real_spend = EN.spend
    expected = {
        "the spent flag is ignored when the pool is read": {"A", "B", "C"},
        "the turn does not clear the floating pool": {"D"},
        "every payment also consumes a floating point": {"C", "E"},
    }
    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == "the spent flag is ignored when the pool is read":
            def blind(self):
                for f in self.bonus_mana:
                    f.tapped = False          # the pre-§0z37 behaviour
                return real_avail(self)
            AZ.AzusaGame.available_mana = blind
        elif label == "the turn does not clear the floating pool":
            def keep(g):
                saved = list(g.bonus_mana)
                real_take(g)
                g.bonus_mana = saved
            AZ.take_turn = keep
        else:
            def greedy(g, pay_idx, units):
                real_spend(g, pay_idx, units)
                for f in getattr(g, "bonus_mana", []):
                    if not f.tapped:
                        f.tapped = True       # one too many
                        break
            EN.spend = greedy
            AZ.spend = greedy
        try:
            broke = run_cases()
        finally:
            AZ.AzusaGame.available_mana = real_avail
            AZ.take_turn = real_take
            EN.spend = real_spend
            AZ.spend = real_spend
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
