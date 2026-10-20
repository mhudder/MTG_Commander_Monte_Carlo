#!/usr/bin/env python3
"""The cost of a game, cut without changing one (§0z149).

    python -m tests.test_game_cost
    python -m tests.test_game_cost --mutate   # 3 mutations, exact sets

Every main phase priced every affordable card in hand and cast one; the
battlefield's `remove` and `in` compared whole permanents field by field; and
`opponents.is_creature_now` ran an import statement on every call. Each change
is a speed change ONLY if its answer is the answer it replaced -- so this
checks identity, over inputs built to reach the cases where they could differ.

CASES
  A  `engine.lazy_pay_of` is `choose_mode`'s payment: on 3,000 random cards
     (up to three modes) and pools, an option `(card, None)` priced from
     `choose_mode_cost`'s mode equals `choose_mode`'s third element, `cost`
     included; at `slot=2` the same; an option that carries a payment gets
     that object back; a second ask returns the first answer's object; and
     an option found affordable in its OWN pool (`pools`) is priced there --
     {G}{G}{G} against two Forests and a third in the creature pool
  B  `Board._find` is `list.index`: over 300 shuffled boards holding EQUAL
     but distinct permanents (one Card, the same fields), removing each
     permanent in turn, and an equal copy that is not on the board, leaves
     the same objects in the same order and the same `names` counts as a
     plain list, and `in` agrees with the list's; a Card (not a Permanent)
     is not `in` a board, and removing it raises ValueError
  C  `opponents.is_creature_now` reads `engine.is_battlefield_creature` at
     CALL time: after a first call, replacing the engine's function changes
     the answer; with `pod_reads_battlefield_creatures` off a creature card
     is a creature without asking

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  `lazy_pay_of` prices every option against `pool`, ignoring `pools` -> A
  `Board._find` matches identity only, never equality             -> B
  `is_creature_now` keeps the FUNCTION from its first call         -> C

  The first run of the second one CRASHED in B rather than failing it: the
  identity-only board raised on removing the equal copy the list removed.
  B now records that as a disagreement; the set was not changed.

UNMUTATED (§0z15): `should_cast_own_wipe` building the whole-board list only
under the measures that read it, and `available_mana` memoising the hand's
demand per colour set, are pinned by the full-output comparison in §0z149
(21,000 games identical), not here: each is a removed recomputation with
nothing left to break but the recomputation itself.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
COLOURS = ("W", "U", "B", "R", "G", "C")
PALETTE = ([frozenset(c) for c in COLOURS] * 3
           + [frozenset("GW"), frozenset("BR"), frozenset("WUBRG")])


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def random_cost(rng, around):
    cost = {}
    for _ in range(max(1, around)):
        k = rng.choice(COLOURS + ("gen", "gen"))
        cost[k] = cost.get(k, 0) + 1
    return cost


def random_pool(rng, size):
    owners = [object() for _ in range(max(1, size // 2))]
    return EN.ManaUnits([rng.choice(PALETTE) for _ in range(size)],
                        [rng.choice(owners) for _ in range(size)],
                        [(rng.randrange(3), rng.randrange(3), 0)
                         for _ in range(size)])


def run_cases():
    PASS.clear()
    FAIL.clear()
    rng = random.Random(149)

    same, priced = True, 0
    for _ in range(3000):
        base = random_cost(rng, rng.randrange(1, 7))
        alts = tuple((random_cost(rng, rng.randrange(1, 7)), f"alt{k}",
                      rng.choice((-1.0, 0.5, 1.0)))
                     for k in range(rng.randrange(0, 3)))
        card = EN.Card(name="Probe", types=frozenset({"Sorcery"}),
                       cost=base, alt_costs=alts)
        pool = random_pool(rng, max(0, sum(base.values())
                                    + rng.randrange(-1, 4)))
        want = EN.choose_mode(card, base, pool)
        mode = EN.choose_mode_cost(card, base, pool)
        if want is None or mode is None:
            same &= want is None and mode is None
            continue
        priced += 1
        pay_of = EN.lazy_pay_of({id(card): mode[0]}, pool)
        got = pay_of((card, None))
        at2 = EN.lazy_pay_of({id(card): mode[0]}, pool, slot=2)(
            (card, mode[0], None))
        same &= (list(got) == list(want[2]) and got.cost == want[2].cost
                 and list(at2) == list(want[2])
                 and pay_of((card, None)) is got)
    carried = EN.Payment([7])
    keeps = EN.lazy_pay_of({}, EN.ManaUnits())((card, carried)) is carried
    forest = EN.Card(name="Bear", types=frozenset({"Creature"}),
                     cost={"G": 3})
    lands = EN.ManaUnits([frozenset("G"), frozenset("G")])
    own = lands + [frozenset("G")]
    in_own = EN.lazy_pay_of({id(forest): forest.cost}, lands,
                            {id(forest): own})((forest, None))
    check("A lazy_pay_of is choose_mode's payment, in the option's own pool",
          (same, priced > 1000, keeps, in_own is not None
           and list(in_own) == [0, 1, 2]),
          (True, True, True, True))

    def perm(card, **kw):
        return EN.Permanent(card=card, **kw)

    same, counted = True, True
    for _ in range(300):
        token = EN.Card(name="Insect", types=frozenset({"Creature"}),
                        power=1, toughness=1)
        other = EN.Card(name="Forest", types=frozenset({"Land"}),
                        is_land=True)
        cards = ([perm(token, is_token=True) for _ in range(3)]
                 + [perm(token, is_token=True, tapped=True)]
                 + [perm(other) for _ in range(2)] + [perm(other, sick=False)])
        rng.shuffle(cards)
        absent = perm(token, is_token=True)     # equal to three, on no board
        for target in list(cards) + [absent]:
            plain, board = list(cards), EN.Board(cards)
            same &= (target in plain) == (target in board)
            if target in plain:
                plain.remove(target)
                try:
                    board.remove(target)
                except ValueError:      # the list found it; the board did not
                    same = False
                    continue
                same &= [id(p) for p in plain] == [id(p) for p in board]
                counted &= board.names == EN.Board(plain).names
    board = EN.Board([perm(token)])
    try:
        board.remove(token)
        raised = False
    except ValueError:
        raised = True
    check("B Board._find is list.index, equal copies included",
          (same, counted, token in board, raised), (True, True, False, True))

    g = type("G", (), {})()
    g.cfg, g.turn, g.board = dict(DEFAULT_CFG), 5, []
    bear = perm(EN.Card(name="Bear", types=frozenset({"Creature"}),
                        power=2, toughness=2))
    first = OPP.is_creature_now(g, bear)
    real = EN.is_battlefield_creature
    EN.is_battlefield_creature = lambda g, p: False
    try:
        patched = OPP.is_creature_now(g, bear)
    finally:
        EN.is_battlefield_creature = real
    g.cfg["pod_reads_battlefield_creatures"] = False
    type_line = OPP.is_creature_now(g, bear)
    check("C is_creature_now reads the engine's function at call time",
          (first, patched, type_line), (True, False, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The cost of a game, cut without changing one (§0z149)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_lazy = EN.lazy_pay_of

    def lazy_ignores_pools(mode_cost, pool, pools=None, slot=1):
        return real_lazy(mode_cost, pool, None, slot)

    def identity_only(self, perm):
        for i, q in enumerate(list.__iter__(self)):
            if q is perm:
                return i
        return -1

    kept = []

    def keeps_function(g, perm):
        if not perm.card.is_creature:
            return False
        if not g.cfg.get("pod_reads_battlefield_creatures", True):
            return True
        if not kept:
            kept.append(EN.is_battlefield_creature)
        return kept[0](g, perm)

    muts = {
        "`lazy_pay_of` prices every option against `pool`":
            ({"A"}, EN, "lazy_pay_of", lazy_ignores_pools),
        "`Board._find` matches identity only":
            ({"B"}, EN.Board, "_find", identity_only),
        "`is_creature_now` keeps the function from its first call":
            ({"C"}, OPP, "is_creature_now", keeps_function),
    }
    bad = 0
    for label, (want, owner, name, value) in muts.items():
        print(f"-- {label}")
        orig = getattr(owner, name)
        setattr(owner, name, value)
        try:
            broke = run_cases()
        finally:
            setattr(owner, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
