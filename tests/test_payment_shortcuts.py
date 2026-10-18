#!/usr/bin/env python3
"""Asking whether a cost can be paid without building the payment (§0z147).

    python -m tests.test_payment_shortcuts
    python -m tests.test_payment_shortcuts --mutate   # 3 mutations, exact sets

A `main_phase` asks every card in hand whether it is affordable and casts one,
so `engine.can_afford` answers the question without the generic assignment,
`engine.choose_mode_cost` chooses a mode without building any payment, and
`choose_mode` builds only the chosen mode's. Each is a speed change ONLY if
its answer is the answer the full solver gives -- so this checks identity,
over pools built to reach the cases where the greedy colour phase decides.

CASES
  A  `can_afford(cost, units)` is `can_pay(cost, units) is not None` on 20,000
     random pools and costs: mono, dual and five-colour units, empty units,
     shared owners, both `legacy` and `surplus` settings, costs at and around
     the pool's size
  B  the shortcut falls back to the greedy when a unit makes two needed
     colours: {W,G} and {W,U} paying {W}{G} -- the greedy spends the {W,G} on
     the {W} and fails, though an assignment exists -- and `can_afford` fails
     with it; and with no shared unit it counts (mono {W}, {G} pools)
  C  `choose_mode_cost` picks `choose_mode`'s mode, and `choose_mode` returns
     what the solver did before §0z147 (every mode priced, the best kept), on
     5,000 random cards with up to three modes and preferences, pools at and
     around their costs. ONE-COLOUR units only: A covers the duals, and here
     the mode choice is under test, so no mutation of the shared-unit rule
     can reach C (written before the first run)
  D  `ManaUnits + []` is the pool it was added to -- units, owners, weights,
     `legacy`, `surplus` -- which is why azusa's `main_phase` may skip it

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the shortcut ignores units shared between needed colours -> A, B
  the shortcut's generic check is off by one               -> A, B, C *
  choose_mode_cost keeps the first affordable mode         -> C

  * PREDICTED A, C. B broke too, and rightly: B's one-colour pool {W},{G}
    paying {W}{G} is exactly at the generic boundary. Recorded as a
    transcript, not a prediction (§0z14).
  The first stand-in for "ignores shared units" counted a shared unit for
  its FIRST needed colour, which agrees with the greedy on B's pool by the
  order of the colours, and broke only A. It was not the defect: dropping the
  shared check means a shared unit counts for EVERY needed colour it makes.
  Replaced with that double count, and A, B written before its run.

UNMUTATED (§0z15): D is a property of `ManaUnits.__add__`, which nothing here
changes; it is pinned because azusa's skip of `units + []` rests on it.
"""
import random
import sys

import edhmc.engine as EN

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
COLOURS = ("W", "U", "B", "R", "G", "C")
PALETTE = ([frozenset(c) for c in COLOURS] * 3
           + [frozenset("GW"), frozenset("WU"), frozenset("UB"),
              frozenset("BR"), frozenset("RG"), frozenset("GC"),
              frozenset("WUBRG"), frozenset()])


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def random_pool(rng, size, palette=PALETTE):
    owners_pool = [object() for _ in range(max(1, size // 2))]
    units = [rng.choice(palette) for _ in range(size)]
    owners = [rng.choice(owners_pool) if rng.random() < 0.8 else None
              for _ in range(size)]
    weights = [(rng.randrange(4), rng.randrange(3), rng.randrange(3))
               for _ in range(size)]
    return EN.ManaUnits(units, owners, weights,
                        legacy=rng.random() < 0.2,
                        surplus=rng.random() < 0.8)


def random_cost(rng, around):
    cost = {}
    for c in rng.sample(COLOURS, rng.randrange(0, 4)):
        cost[c] = rng.randrange(1, 3)
    gen = max(0, around - sum(cost.values()) + rng.randrange(-2, 3))
    if gen:
        cost["gen"] = gen
    return cost


def old_choose_mode(card, base_cost, units):
    """`choose_mode` as it was before §0z147: every mode priced."""
    best = None
    for cost, tag, pref in EN.castable_modes(card, base_cost):
        pay = EN.can_pay(cost, units)
        if pay is None:
            continue
        key = (pref, -sum(cost.values()))
        if best is None or key > best[0]:
            best = (key, cost, tag, pay)
    return None if best is None else (best[1], best[2], best[3])


def run_cases():
    PASS.clear()
    FAIL.clear()
    rng = random.Random(147)

    agree, both = True, {True: 0, False: 0}
    for _ in range(20000):
        size = rng.randrange(0, 14)
        units = random_pool(rng, size)
        cost = random_cost(rng, size)
        want = EN.can_pay(cost, units) is not None
        agree &= EN.can_afford(cost, units) == want
        both[want] += 1
    check("A can_afford is can_pay is not None (20,000 pools)",
          (agree, both[True] > 1000, both[False] > 1000), (True, True, True))

    shared = EN.ManaUnits([frozenset("WG"), frozenset("WU")])
    mono = EN.ManaUnits([frozenset("W"), frozenset("G")])
    wg = {"W": 1, "G": 1}
    check("B the greedy decides when a unit is shared; counting when not",
          (EN.can_pay(wg, shared) is None, EN.can_afford(wg, shared),
           EN.can_afford(wg, mono), EN.can_afford({"W": 2}, mono)),
          (True, False, True, False))

    same = True
    for _ in range(5000):
        base = random_cost(rng, rng.randrange(1, 8))
        alts = tuple((random_cost(rng, rng.randrange(1, 8)), f"alt{k}",
                      rng.choice((-1.0, 0.5, 1.0)))
                     for k in range(rng.randrange(0, 3)))
        card = EN.Card(name="Probe", types=frozenset({"Sorcery"}),
                       cost=base, alt_costs=alts)
        units = random_pool(rng, max(0, sum(base.values())
                                     + rng.randrange(-2, 3)),
                            palette=[frozenset(c) for c in COLOURS])
        new = EN.choose_mode(card, base, units)
        old = old_choose_mode(card, base, units)
        picked = EN.choose_mode_cost(card, base, units)
        same &= (new == old
                 and picked == (None if old is None else old[:2]))
    check("C choose_mode_cost and choose_mode are the old choice", same, True)

    pool = random_pool(random.Random(3), 9)
    plus = pool + []
    check("D ManaUnits + [] is the same pool",
          (list(plus) == list(pool), plus.owners == pool.owners,
           plus.weights == pool.weights, plus.legacy == pool.legacy,
           plus.surplus == pool.surplus),
          (True, True, True, True, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Affordability without the payment (§0z147)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_afford = EN.can_afford

    def counting(cost, units, off=0, ignore_shared=False):
        if sum(cost.values()) > len(units):
            return False
        pips = [(c, cost[c]) for c in COLOURS if cost.get(c, 0) > 0]
        have = dict.fromkeys([c for c, _ in pips], 0)
        for u in units:
            hits = [c for c, _ in pips if c in u]
            if len(hits) > 1 and not ignore_shared:
                return real_afford(cost, units)
            for c in hits:
                have[c] += 1
        taken = 0
        for c, n in pips:
            if have[c] < n:
                return False
            taken += n
        return cost.get("gen", 0) + off <= len(units) - taken

    def first_mode(card, base_cost, units):
        for cost, tag, _pref in EN.castable_modes(card, base_cost):
            if EN.can_afford(cost, units):
                return cost, tag
        return None

    muts = {
        "the shortcut ignores units shared between needed colours":
            ({"A", "B"}, "can_afford",
             lambda cost, units: counting(cost, units, ignore_shared=True)),
        "the shortcut's generic check is off by one":
            ({"A", "B", "C"}, "can_afford",
             lambda cost, units: counting(cost, units, off=1)),
        "choose_mode_cost keeps the first affordable mode":
            ({"C"}, "choose_mode_cost", first_mode),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        orig = getattr(EN, name)
        setattr(EN, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(EN, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
