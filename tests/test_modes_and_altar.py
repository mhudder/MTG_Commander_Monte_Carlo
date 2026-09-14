#!/usr/bin/env python3
"""§1b and §3 — castable modes, and Ashnod's Altar's mana.

    python -m tests.test_modes_and_altar
    python -m tests.test_modes_and_altar --mutate    # 4 mutations, exact sets

§1b, "cards can only have one cost", was really two problems and `alt_costs`
only solved one. A card's alternatives are not all of a kind:

    CHEAPER AND WORSE   Overlord of the Hauntwoods, Impending 4: {1}{G}{G}
                        instead of {3}{G}{G}, and a noncreature enchantment
                        for four turns. Take it only if you must.
    A DIFFERENT ROUTE   Revitalizing Repast's hybrid pip: {B} or {G}, neither
                        better. Take whichever the pool can pay.
    DEARER AND BETTER   Mizzix's Mastery, overload {5}{R}{R}{R}: copy EVERY
                        instant and sorcery in the graveyard rather than one.
                        Take it whenever the mana is there.

`alt_costs` was consulted only when the printed cost was UNAFFORDABLE, which
is right for the first two and exactly backwards for the third -- so overload
could not be expressed and lived as a hand-written branch in
`lorehold.main_phase` with its cost typed out a second time. `preference`
closes the category; `engine.choose_mode` is the single place the choice is
made, for all six engines.

§3 is Ashnod's Altar. "Sacrifice a creature: Add {C}{C}" was activated AFTER
the main phase, so the mana could never be spent -- the engine modelled the
cost and none of the benefit.
"""
import sys

import edhmc.engine as E
from edhmc.engine import Card, Permanent, ManaUnits, choose_mode, castable_modes
from edhmc.decks.rendmaw_v12 import build as rw_build
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
RD, RC = rw_build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def pool(*colours):
    """A ManaUnits of one unit per colour letter given."""
    return ManaUnits([frozenset({c}) for c in colours])


def rgame(**cfg):
    import random
    return E.Game(list(RD), RC, dict(DEFAULT_CFG, turns=20, **cfg),
                  random.Random(1), seed_for_pod=1)


def token(g, n=1):
    for _ in range(n):
        g.make_tokens(1, 1, 1, "Bird")


def main():
    print(__doc__.split("\n\n")[0]); print()

    cheap = Card(name="Cheap", types=frozenset({"Creature"}),
                 cost={"gen": 3, "G": 2},
                 alt_costs=(({"gen": 1, "G": 2}, "impending"),))
    dear = Card(name="Dear", types=frozenset({"Sorcery"}), cost={"gen": 3, "R": 1},
                alt_costs=(({"gen": 5, "R": 3}, "overload", 1.0),))

    # -- 1. a two-tuple alternative defaults to CHEAPER-AND-WORSE ----------
    check("1  a 2-tuple alt defaults to preference -1.0 (a fallback)",
          [m[2] for m in castable_modes(cheap, cheap.cost)], [0.0, -1.0])

    # -- 2. the printed cost wins when both are affordable -----------------
    got = choose_mode(cheap, cheap.cost, pool(*"GGCCC"))
    check("2  printed cost preferred over a cheaper-and-worse mode",
          got[1], None)

    # -- 3. ... and the fallback is taken when it is not -------------------
    got = choose_mode(cheap, cheap.cost, pool(*"GGC"))
    check("3  the fallback is taken when the printed cost is unaffordable",
          got[1], "impending")

    # -- 4. a DEARER-AND-BETTER mode is taken whenever affordable ----------
    got = choose_mode(dear, dear.cost, pool(*"RRRCCCCC"))
    check("4  overload is taken when the mana is there, though it costs MORE",
          got[1], "overload")

    # -- 5. ... and is not, when it is not ---------------------------------
    got = choose_mode(dear, dear.cost, pool(*"RCCC"))
    check("5  and the printed cost is used when overload is unaffordable",
          got[1], None)

    # -- 6. nothing affordable -> no mode ----------------------------------
    check("6  an unaffordable card yields no mode",
          choose_mode(dear, dear.cost, pool("C")), None)

    # -- 7. §3: the Altar's mana is spendable IN the main phase ------------
    # An empty board but for the Altar and seven spare Bird tokens, and one
    # card in hand that only {C}{C} can pay for.
    g = rgame(altar_keep=0)
    g.board.append(Permanent(card=next(c for c in RD
                                       if c.name == "Ashnod's Altar"),
                             sick=False))
    token(g, 4)
    g.hand[:] = [Card(name="Two Drop", types=frozenset({"Artifact"}),
                      cost={"gen": 2}, priority=9.0)]
    E.main_phase(g)
    check("7  §3 the Altar's mana is spendable during the main phase",
          (g.m.get("altar_sacrifices", 0), len(g.hand)), (1, 0))

    # -- 8. it does NOT sacrifice when the spell is already affordable -----
    g = rgame(altar_keep=0)
    g.board.append(Permanent(card=next(c for c in RD
                                       if c.name == "Ashnod's Altar"),
                             sick=False))
    token(g, 4)
    g.board.append(Permanent(card=Card(name="Rock", types=frozenset({"Artifact"}),
                                       mana_ability=(2, frozenset({"C"}))),
                             sick=False))
    g.hand[:] = [Card(name="Two Drop", types=frozenset({"Artifact"}),
                      cost={"gen": 2}, priority=9.0)]
    E.main_phase(g)
    check("8  it eats nothing when the spell was already castable",
          (g.m.get("altar_sacrifices", 0), len(g.hand)), (0, 0))

    # -- 9. it never eats a creature the payment is counting on ------------
    # ENDURING VITALITY IS THE WHOLE POINT OF THIS CASE. Without it a Bird
    # token owns no mana unit, so "fodder excludes mana sources" is vacuously
    # true and the mutation that removes the filter cannot be detected -- the
    # first version of this case was exactly that, and the mutation caught it.
    # With Vitality out, every untapped creature taps for mana, so eating one
    # to pay for a spell can remove more mana than the Altar adds.
    g = rgame(altar_keep=0)
    g.board.append(Permanent(card=next(c for c in RD
                                       if c.name == "Enduring Vitality"),
                             sick=False))
    token(g, 3)
    for p in g.board:                 # tokens enter tapped and sick here
        p.tapped, p.sick = False, False
    units = E.available_mana(g)
    owners = {id(o) for o in getattr(units, "owners", []) if o is not None}
    fodder = E.altar_fodder(g, units)
    check("9  a creature owning a unit in the pool is not fodder",
          (len(owners) > 0, [p for p in fodder if id(p) in owners]),
          (True, []))

    print()
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        return {f.split()[0] for f in FAIL}
    if FAIL:
        raise SystemExit(f"FAILED: {FAIL}")
    print("  PASS")
    return set()


def _no_preference():
    """The pre-§0z20 rule: alternatives are ALWAYS fallbacks."""
    E.castable_modes = lambda card, base: (
        [(base, None, 0.0)] + [(e[0], e[1], -1.0) for e in card.alt_costs])


def _alt_always_wins():
    E.castable_modes = lambda card, base: (
        [(base, None, 0.0)] + [(e[0], e[1], 1.0) for e in card.alt_costs])


def _altar_mana_off():
    E.altar_enable = lambda g, units, precombat: None


def _altar_eats_anything():
    E.altar_fodder = lambda g, units=None: [
        p for p in g.board if p.is_token and p.card.is_creature]


MUTATIONS = [
    # Preference dropped: overload becomes a fallback again, so case 4 breaks
    # and nothing else does -- cases 2/3/5 are what a fallback already does.
    ("§1b: preference ignored, alts are always fallbacks", _no_preference, {"4"}),
    # Every alt preferred: the cheaper-and-worse mode is now taken even when
    # the printed cost is affordable, so case 2 breaks.
    ("§1b: every alt preferred over the printed cost", _alt_always_wins, {"2"}),
    ("§3: the Altar's main-phase mana step removed", _altar_mana_off, {"7"}),
    # Case 9 is the only one that asserts the fodder filter.
    ("§3: fodder ignores what the payment is using", _altar_eats_anything, {"9"}),
]


def run_mutations():
    saved = {n: getattr(E, n) for n in
             ("castable_modes", "altar_enable", "altar_fodder")}
    ok = True
    for label, patch, want in MUTATIONS:
        for n, f in saved.items():
            setattr(E, n, f)
        PASS.clear(); FAIL.clear()
        patch()
        print(f"=== MUTATION: {label}")
        print(f"    expected to fail: {sorted(want)}")
        got = main()
        if got == want:
            print(f"    OK - exactly {sorted(want)} failed")
        else:
            ok = False
            print(f"    !!! UNEXPECTED - got {sorted(got)}")
    for n, f in saved.items():
        setattr(E, n, f)
    if not ok:
        raise SystemExit("FAIL: a mutation did not behave as specified.")
    print("PASS - every clause is independently pinned.")


if __name__ == "__main__":
    if MUTATE:
        run_mutations()
    else:
        main()
