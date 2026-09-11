#!/usr/bin/env python3
"""Pin the mechanisms of the 2026-09-09 Azusa candidates.

    python -m tests.test_azusa_candidates
    python -m tests.test_azusa_candidates --mutate

Why this exists rather than a statistical smoke test. The first check on these
cards compared mean counters over 600 games with the card swapped in, and it
read as though GREENSLEEVES MADE FEWER TOKENS and Springheart made almost
none. Both were wrong: `tokens_made` has a baseline near 63 in this deck
because Scute Swarm doubles on every landfall, so its variance swamps a
three-token-a-game effect at that sample size. The card was fine and the
measurement was not.

So these are DIRECT checks -- put the permanent on the battlefield, fire a
landfall, assert the printed effect happened. No sampling, no bars, nothing to
misread. That is the right shape for "does the engine do what the card says",
which is a different question from "is the card good".

`--mutate` turns the implementations off and asserts the checks FAIL. Six of
the eight depend on the mutated behaviour and must break; the two graveyard
cases do not and must survive. A check that cannot fail reads like assurance
and is worse than none.
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


def fresh():
    deck, cmd = M.build()
    return AzusaGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)


def mkland():
    return Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"G"}))


def landfall(g, n=1):
    for _ in range(n):
        land = mkland()
        g.make_permanent(land)
        g.land_entered(land, played=True)


def main():
    if MUTATE:
        # Turn the implementations off, one knob each.
        AZ.DYNAMIC_PT_LANDS = frozenset({"Ashaya, Soul of the Wild"})
        orig = AZ.AzusaGame.land_entered

        def undoubled(self, card, played=False):
            self.m["landfall_triggers"] += 1
            self._landfall_payoffs(card, played)   # once, never twice
        AZ.AzusaGame.land_entered = undoubled
        print("MUTATED: */* P/T off, Ancient Greenwarden doubling off\n")

    # 1-2. Greensleeves: a 3/3 Badger per landfall, and */* off the land count.
    g = fresh()
    g.make_permanent(M.GREENSLEEVES, sick=False)
    before = g.m["tokens_made"]
    landfall(g, 3)
    check("Greensleeves makes one 3/3 Badger per landfall",
          (g.m["tokens_made"] - before,
           sum(1 for p in g.board if p.is_token and p.base_p == 3)), (3, 3))
    gp = next(p for p in g.board if p.card.name == M.GREENSLEEVES.name)
    n_lands = sum(1 for p in g.board if p.card.is_land)
    check("Greensleeves is */* equal to your land count",
          (g.power_of(gp), g.toughness_of(gp)), (n_lands, n_lands))

    # 3. Springheart with NO host -- the 1/1 Insect mode.
    g = fresh()
    g.resolve(M.SPRINGHEART_NANTUKO)
    before = g.m["tokens_made"]
    landfall(g, 3)
    check("Springheart with no host makes a 1/1 Insect per landfall",
          (g.m["tokens_made"] - before, g.m["springheart_copies"]), (3, 0))

    # 3b. Springheart BESTOWED -- a token copy of the host per landfall, paid
    # for. This is the half that was unimplemented until 2026-09-10 (§0z1).
    cobra = next(c for c in M.build()[0] if c.name == "Lotus Cobra")
    g = fresh()
    for _ in range(12):
        g.make_permanent(mkland())
    g.resolve(cobra)
    g.resolve(M.SPRINGHEART_NANTUKO)
    host = g.springheart_host
    landfall(g, 3)
    check("Springheart bestows on Lotus Cobra and copies it per landfall",
          (host.card.name if host else None, host.counters if host else None,
           g.m["springheart_copies"], g.count("Lotus Cobra")),
          ("Lotus Cobra", 1, 3, 4))

    # 3c. THE PREREQUISITE: payoffs count, they are not booleans. A second
    # Lotus Cobra must actually produce a second mana, or every copy above is
    # an inert token and the combo measures zero for the wrong reason.
    g = fresh()
    for _ in range(6):
        g.make_permanent(mkland())
    g.resolve(cobra)
    g.resolve(cobra)
    before = len(g.bonus_mana)
    landfall(g, 1)
    check("two Lotus Cobras give TWO mana on one landfall (count, not has)",
          len(g.bonus_mana) - before, 2)

    # 4-5. Ancient Greenwarden DOUBLES the ability but not the EVENT.
    counts = {}
    for warden in (False, True):
        g = fresh()
        g.make_permanent(M.GREENSLEEVES, sick=False)
        if warden:
            g.make_permanent(M.ANCIENT_GREENWARDEN, sick=False)
        before = g.m["tokens_made"]
        landfall(g, 1)
        counts[warden] = (g.m["tokens_made"] - before, g.m["landfall_triggers"])
    check("Ancient Greenwarden doubles the landfall ABILITY",
          (counts[False][0], counts[True][0]), (1, 2))
    check("...but the landfall EVENT still counts once",
          (counts[False][1], counts[True][1]), (1, 1))

    # 6. Cultivator Colossus empties the hand of lands and draws for each.
    g = fresh()
    g.hand = [mkland() for _ in range(5)]
    g.resolve(M.CULTIVATOR_COLOSSUS)
    cp = next(p for p in g.board if p.card.name == "Cultivator Colossus")
    check("Cultivator Colossus loops until no land is left in hand",
          (g.m["colossus_lands"] >= 5,
           sum(1 for c in g.hand if c.is_land),
           g.m["cards_drawn"] == g.m["colossus_lands"],
           g.power_of(cp) == sum(1 for p in g.board if p.card.is_land)),
          (True, 0, True, True))

    # 7. Hothouse: the drop is unconditional, the top access is not.
    g = fresh()
    g.make_permanent(M.CASE_OF_THE_LOCKED_HOTHOUSE, sick=False)
    unsolved = (g.land_drops_for_turn(), g.top_access())
    g.hothouse_solved = True
    check("Case of the Locked Hothouse: +1 drop always, top access only solved",
          (unsolved, g.top_access()), ((2, False), True))

    # 8. The three graveyard granters. NOT mutated -- these must survive.
    got = []
    for c in (M.CONDUIT_OF_WORLDS, M.WALK_IN_CLOSET, M.ANCIENT_GREENWARDEN):
        g = fresh()
        g.graveyard.append(mkland())
        g.make_permanent(c, sick=False)
        got.append(len([z for _, z in g.playable_lands() if z == "graveyard"]))
    check("Conduit / Walk-In Closet / Greenwarden each play lands from the "
          "graveyard", tuple(got), (1, 1, 1))

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        # THREE cases depend on the mutated code, not two. The third is
        # Colossus, and getting that wrong first time is the reason this mode
        # is worth having: Cultivator Colossus is ALSO a */* card, so turning
        # DYNAMIC_PT_LANDS off makes it a 0/0 as well, and its check asserts
        # its power equals the land count. The mutation check caught an error
        # in the expectations rather than in the engine, which is still the
        # check working -- a wrong list of what should break is exactly how
        # one of these silently stops testing anything.
        expected_fail = {
            "Greensleeves is */* equal to your land count",
            "Ancient Greenwarden doubles the landfall ABILITY",
            "Cultivator Colossus loops until no land is left in hand",
        }
        actual_fail = set(FAIL)
        if actual_fail == expected_fail:
            print("  MUTATION CHECK OK -- exactly the three cases that depend "
                  "on the mutated code failed, and nothing else did.")
            return 0
        print(f"  MUTATION CHECK FAILED\n"
              f"    expected to fail: {sorted(expected_fail)}\n"
              f"    actually failed : {sorted(actual_fail)}")
        return 1
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
