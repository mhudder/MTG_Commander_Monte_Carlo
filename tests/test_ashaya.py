#!/usr/bin/env python3
"""§0z18 / queued 15 — Ashaya's second clause, one assertion per rule.

    python -m tests.test_ashaya
    python -m tests.test_ashaya --mutate    # 3 mutations, exact sets

Ashaya, Soul of the Wild, verified against Scryfall 2026-09-13:

    Ashaya's power and toughness are each equal to the number of lands you
    control. Nontoken creatures you control are Forest lands in addition to
    their other types. (They're still affected by summoning sickness.)

The second sentence went unimplemented for the life of the project and was the
reason Ashaya sat in PARTLY_MODELLED. Each case below pins one rule, and the
rules are the ones `docs/COMP_RULES.md` already researched plus the two
official rulings that contradict its conclusion.

THE ONE THE DESIGN NOTE GOT WRONG. COMP_RULES.md said, of 603.6a, "**it must
not fire landfall**". That is true of creatures ALREADY on the battlefield
when Ashaya resolves, and false of every creature that enters afterwards --
the official ruling is explicit:

    "You can't play creature cards as lands; you'll still have to cast them
     as spells, and THEY'LL ENTER THE BATTLEFIELD AS LANDS (in addition to
     their other types)."          (2020-09-25)

In a 28-creature landfall list that branch is the larger half of the card, and
a naive implementation of the note would have shipped the card understated.
Cases 1 and 2 pin both directions, because getting either one wrong is a large
error in opposite directions.
"""
import sys

from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card
import edhmc.azusa as AZ

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    deck, cmd = M.build()
    return AzusaGame(deck, cmd, dict(DEFAULT_CFG, turns=20, **cfg), 1234)


def named(name):
    return next(c for c in M.build()[0] if c.name == name)


def bear(name="Grizzly Bear"):
    return Card(name=name, types=frozenset({"Creature"}),
                cost={"gen": 1, "G": 1}, power=2, toughness=2)


def main():
    print(__doc__.split("\n\n")[0])
    print()
    ashaya = named("Ashaya, Soul of the Wild")

    # -- 1. a nontoken creature ENTERING under Ashaya fires landfall --------
    g = fresh()
    g.make_permanent(ashaya)
    before = g.m["landfall_triggers"]
    g.make_permanent(bear())
    check("1  nontoken creature entering fires landfall (official ruling)",
          g.m["landfall_triggers"] - before, 1)

    # -- 2. 603.6a: creatures ALREADY out when Ashaya lands fire nothing ----
    g = fresh()
    for i in range(4):
        g.make_permanent(bear(f"Bear {i}"))
    before = g.m["landfall_triggers"]
    g.make_permanent(ashaya)
    # Ashaya itself enters as a land and fires ONE. The four already on the
    # battlefield gain the type without an ETB event and fire NOTHING.
    check("2  603.6a — creatures already out fire nothing when Ashaya lands",
          g.m["landfall_triggers"] - before, 1)

    # -- 3. tokens are excluded ("NONTOKEN creatures you control") ----------
    g = fresh()
    g.make_permanent(ashaya)
    before = g.m["landfall_triggers"]
    g.make_tokens(3, 1, 1, "Insect")
    check("3  token creatures are not lands and fire no landfall",
          g.m["landfall_triggers"] - before, 0)

    # -- 4. 305.7: the creature-lands tap for {G} ---------------------------
    g = fresh()
    g.make_permanent(ashaya)
    p = g.make_permanent(bear(), sick=False)
    units = g.available_mana()
    check("4  305.7 — a non-sick creature-land taps for {G}",
          sum(1 for i, u in enumerate(units) if units.owners[i] is p
              and "G" in u), 1)

    # -- 5. 302.6: not the turn it arrives ----------------------------------
    g = fresh()
    g.make_permanent(ashaya)
    p = g.make_permanent(bear(), sick=True)
    units = g.available_mana()
    check("5  302.6 — a summoning-sick creature-land taps for nothing",
          sum(1 for i, u in enumerate(units) if units.owners[i] is p), 0)

    # -- 6. a creature with its own mana ability does not double ------------
    g = fresh()
    g.make_permanent(ashaya)
    dork = Card(name="Llanowar Elves", types=frozenset({"Creature"}),
                cost={"G": 1}, power=1, toughness=1,
                mana_ability=(1, frozenset({"G"})))
    p = g.make_permanent(dork, sick=False)
    units = g.available_mana()
    check("6  a mana dork gains Forest's ability but has ONE {T} to spend",
          sum(1 for i in range(len(units)) if units.owners[i] is p), 1)

    # -- 7. Ashaya's own */* counts the creature-lands, itself included -----
    g = fresh(ashaya_lands=True)
    perm = g.make_permanent(ashaya)
    g.make_permanent(bear("A"))
    g.make_permanent(bear("B"))
    # three nontoken creatures on an empty board, no real lands
    check("7  ruling 2 — Ashaya's */* counts the creature-lands AND itself",
          g.power_of(perm), 3)

    # -- 8. forests() sees them (Sapling Nursery / Nissa read this) ---------
    g = fresh()
    g.make_permanent(ashaya)
    g.make_permanent(bear())
    check("8  forests() counts the creature-lands", g.forests(), 2)

    # -- 9. Titania: a creature death IS a land death -----------------------
    g = fresh()
    g.make_permanent(ashaya)
    g.make_permanent(named("Titania, Protector of Argoth"))
    victim = g.make_permanent(bear())
    before = g.m["tokens_made"]
    g.board.remove(victim)
    g.on_creature_death(1, victim)
    check("9  Titania makes a 5/3 when a creature-land dies",
          g.m["tokens_made"] - before, 1)

    print()
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        return {f.split()[0] for f in FAIL}
    if FAIL:
        raise SystemExit(f"FAILED: {FAIL}")
    print("  PASS")
    return set()


MUTATIONS = [
    # (label, patch, the EXACT cases that must fail, written from the rule)
    #
    # A blunt off-switch cannot test an assertion of ABSENCE: cases 3, 5 and 6
    # each say "this does NOT happen", and with the clause off it does not
    # happen for the trivial reason. That is why there are three mutations and
    # not one. Getting this wrong first time is recorded in §0z18 -- the
    # expectation was written before the run, as CLAUDE.md requires, and two
    # of its nine entries were wrong for exactly this reason.
    ("clause OFF wholesale",
     lambda: setattr(AZ.AzusaGame, "ashaya_lands", lambda self: False),
     {"1", "2", "4", "7", "8", "9"}),

    ("302.6 dropped — sick creature-lands tap",
     lambda: setattr(AZ.AzusaGame, "creature_land_mana",
                     lambda self, p: (self.ashaya_lands()
                                      and self.is_creature_land(p)
                                      and not p.card.mana_ability)),
     {"5"}),

    ("one-{T} rule dropped — a dork taps twice",
     lambda: setattr(AZ.AzusaGame, "creature_land_mana",
                     lambda self, p: (self.ashaya_lands()
                                      and self.is_creature_land(p)
                                      and not p.sick)),
     {"6"}),
]


def run_mutations():
    originals = {n: getattr(AZ.AzusaGame, n)
                 for n in ("ashaya_lands", "creature_land_mana")}
    ok = True
    for label, patch, want in MUTATIONS:
        for n, f in originals.items():
            setattr(AZ.AzusaGame, n, f)
        PASS.clear(); FAIL.clear()
        patch()
        print(f"=== MUTATION: {label}")
        print(f"    expected to fail: {sorted(want)}")
        got = main()
        if got == want:
            print(f"    OK — exactly {sorted(want)} failed")
        else:
            ok = False
            print(f"    !!! UNEXPECTED — got {sorted(got)}")
    for n, f in originals.items():
        setattr(AZ.AzusaGame, n, f)
    if not ok:
        raise SystemExit("FAIL: a mutation did not behave as specified.")
    print("PASS — every clause of the rule is independently pinned.")


if __name__ == "__main__":
    if MUTATE:
        run_mutations()
    else:
        main()
