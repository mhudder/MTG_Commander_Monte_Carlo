#!/usr/bin/env python3
"""Pin the mechanisms of the 2026-09-10 Azusa candidates (batch 3).

    python -m tests.test_azusa_batch3
    python -m tests.test_azusa_batch3 --mutate

Same shape and same reason as `test_azusa_candidates.py`: put the permanent on
the battlefield, fire the trigger, assert the printed effect happened. No
sampling and no error bars, because "does the engine do what the card says" is
a different question from "is the card good" and only the first one can be
answered exactly.

THREE OF THESE SEVEN CARDS ARE NOT THE CARD THEY ARE REMEMBERED AS, which is
most of why the checks are worth writing down:

  * Return of the Wildspeaker reads NON-HUMAN creatures. Four Humans sit in
    this list and the staged Ka-Zar is a fifth, so a check that only counts
    creatures would pass against an engine that ignores the restriction.
  * The Great Henge costs {7}{G}{G} and is essentially never cast for it. If
    the reduction breaks, the card does not get worse -- it stops existing, and
    its row reads as a bad nine-drop.
  * Castle Garenbrig adds SIX {G}, not four, and only creature spells may spend
    it. Both halves are checked: that the pool unlocks a creature it should,
    and that the real lands are not tapped for mana the Castle made.

`--mutate` turns three implementations off and asserts the checks that depend
on them FAIL. A check that cannot fail reads like assurance and is worse than
none.
"""
import sys

from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card, can_pay, spend
import edhmc.azusa as AZ
import edhmc.engine as EN

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


def forest():
    return Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"G"}))


def landfall(g, n=1):
    for _ in range(n):
        land = forest()
        g.make_permanent(land)
        g.land_entered(land, played=True)


def named(name):
    return next(c for c in M.build()[0] if c.name == name)


def main():
    if MUTATE:
        # (a) the Human subtype set -- Wildspeaker stops discriminating
        AZ.HUMAN = frozenset()
        # (b) the dynamic cost reduction -- Henge and Nursery at printed cost
        AZ.AzusaGame.cost_of = lambda self, card: dict(card.cost)
        # (c) the Forest subtype set, in BOTH places a mana doubler has to be
        #     said: the pool in azusa.available_mana and the tapping in
        #     engine.spend. Turning off only one of the two is the failure this
        #     card could actually have shipped with.
        AZ.FOREST = frozenset()
        EN._FOREST = frozenset()
        print("MUTATED: HUMAN off, cost reduction off, FOREST off\n")

    # ---- The Great Henge --------------------------------------------------
    # 1. The cost reduction IS the card.
    g = fresh()
    printed = g.cost_of(M.THE_GREAT_HENGE)
    hoof = named("Craterhoof Behemoth")            # a 5/5
    g.make_permanent(hoof, sick=False)
    reduced = g.cost_of(M.THE_GREAT_HENGE)
    check("The Great Henge costs {7}{G}{G}, less the greatest power you control",
          (printed.get("gen"), printed.get("G"),
           reduced.get("gen"), reduced.get("G")), (7, 2, 2, 2))

    # 2. The ETB draws off NONTOKEN creatures only, and puts a counter on them.
    g = fresh()
    g.make_permanent(M.THE_GREAT_HENGE, sick=False)
    before = g.m["cards_drawn"]
    perm = g.make_permanent(named("Lotus Cobra"), sick=False)
    after_real = g.m["cards_drawn"] - before
    g.make_tokens(3, 1, 1, "Insect")
    check("The Great Henge draws off a nontoken creature, not off tokens",
          (after_real, perm.counters, g.m["cards_drawn"] - before,
           g.m["henge_draws"]), (1, 1, 1, 1))

    # 3. ... INCLUDING creatures that never go through resolve(). This is the
    # queued-item-16 shape from the other side: a tutor puts the creature
    # straight onto the battlefield, so a hook in resolve() would miss it.
    g = fresh()
    g.make_permanent(M.THE_GREAT_HENGE, sick=False)
    before = g.m["cards_drawn"]
    g.tutor_creature(6)
    check("The Great Henge draws off a TUTORED creature too",
          (g.m["cards_drawn"] - before, g.m["henge_draws"]), (1, 1))

    # ---- Sapling Nursery --------------------------------------------------
    # 4. Affinity for Forests, which is a SUBTYPE and not "a green land".
    g = fresh()
    bare = g.cost_of(M.SAPLING_NURSERY)
    for _ in range(5):
        g.make_permanent(forest())
    g.make_permanent(Card(name="Nykthos, Shrine to Nyx",
                          types=frozenset({"Land"}), is_land=True,
                          produces=frozenset({"G"})))
    with_forests = g.cost_of(M.SAPLING_NURSERY)
    check("Sapling Nursery costs {1} less per FOREST, and Nykthos is not one",
          (bare.get("gen"), with_forests.get("gen"), g.forests()), (6, 1, 5))

    # 5. The landfall half, and Ancient Greenwarden doubling it.
    counts = {}
    for warden in (False, True):
        g = fresh()
        g.make_permanent(M.SAPLING_NURSERY, sick=False)
        if warden:
            g.make_permanent(M.ANCIENT_GREENWARDEN, sick=False)
        before = g.m["tokens_made"]
        landfall(g, 2)
        counts[warden] = (g.m["tokens_made"] - before,
                          sum(1 for p in g.board if p.is_token
                              and (p.base_p, p.base_t) == (3, 4)))
    check("Sapling Nursery makes a 3/4 Treefolk per landfall, doubled by "
          "Greenwarden", (counts[False], counts[True]), ((2, 2), (4, 4)))

    # ---- Nissa, Who Shakes the World --------------------------------------
    # 6. The static doubler, in the POOL and in the TAPPING. Three Forests are
    # six mana, and paying four of it leaves ONE Forest untapped -- not none,
    # which is what happens if only the pool half is implemented.
    g = fresh()
    for _ in range(3):
        g.make_permanent(forest())
    g.make_permanent(M.NISSA_WHO_SHAKES_THE_WORLD, sick=False)
    units = g.available_mana()
    pay = can_pay({"gen": 4}, units)
    # Without the doubler three Forests cannot pay {4} at all, so `pay` is
    # None. Reported as a failed check rather than left to raise: a check that
    # dies on the mutation is not a check that FAILS on it, and the whole
    # point of --mutate is knowing exactly which ones fail.
    if pay is None:
        untapped = None
    else:
        spend(g, pay, units)
        untapped = sum(1 for p in g.board if p.card.is_land and not p.tapped)
    check("Nissa doubles Forests in the pool AND taps one Forest for two",
          (len(units), untapped), (6, 1))

    # 7. The +1: three counters, animated, and UNTAPPED -- the untap is the
    # half that makes it a ritual as well as a body.
    g = fresh()
    land = g.make_permanent(forest())
    land.tapped = True
    nissa = g.make_permanent(M.NISSA_WHO_SHAKES_THE_WORLD, sick=False)
    g.planeswalker_step()
    check("Nissa +1 animates a land as a 3/3 with haste and untaps it",
          (nissa.counters, land.counters, g.power_of(land), land.tapped,
           g.animation_of(land)["haste"]), (6, 3, 3, False, True))

    # 8. The -8: every Forest left in the library, onto the battlefield tapped,
    # each one a landfall trigger.
    #
    # COUNTED BY SUBTYPE, NOT BY NAME, and the difference is a real card. The
    # card says "search your library for any number of FOREST CARDS", and
    # Dryad Arbor ("Land Creature -- Forest Dryad") is one: 21 cards move, not
    # the 20 basics. This check asserted 20 first time and the ENGINE was
    # right -- which is the generated subtype set earning its keep, because a
    # by-hand reading of this deck gets it wrong in exactly that direction.
    g = fresh()
    nissa = g.make_permanent(M.NISSA_WHO_SHAKES_THE_WORLD, sick=False)
    nissa.counters = 8
    in_library = sum(1 for c in g.library if c.name in AZ.FOREST)
    basics = sum(1 for c in g.library if c.name == "Forest")
    before = g.m["landfall_triggers"]
    g.planeswalker_step()
    on_board = sum(1 for p in g.board if p.card.name in AZ.FOREST)
    check("Nissa -8 puts every Forest CARD from the library onto the "
          "battlefield, Dryad Arbor included",
          (in_library == basics + 1, on_board,
           g.m["landfall_triggers"] - before, g.m["pw_ultimates"]),
          (True, in_library, in_library, 1))

    # ---- Return of the Wildspeaker ----------------------------------------
    # 9. The draw mode counts NON-HUMAN power. A 9/9 Terastodon is the answer;
    # a Human is invisible however big it is.
    g = fresh()
    g.make_permanent(named("Terastodon"), sick=False)       # 9/9 Elephant
    big_human = Card(name="Tireless Tracker", types=frozenset({"Creature"}),
                     power=20, toughness=20)
    g.make_permanent(big_human, sick=False)
    before = g.m["cards_drawn"]
    g.cfg["wildspeaker_mode"] = "draw"
    g.return_of_the_wildspeaker()
    check("Wildspeaker draws off the greatest NON-HUMAN power, ignoring a "
          "20/20 Human", g.m["cards_drawn"] - before, 9)

    # 10. The pump mode, likewise: non-Humans only.
    g = fresh()
    beast = g.make_permanent(named("Rampaging Baloths"), sick=False)   # 6/6
    human = g.make_permanent(named("Tireless Tracker"), sick=False)    # 3/2
    g.cfg["wildspeaker_mode"] = "pump"
    g.return_of_the_wildspeaker()
    check("Wildspeaker pumps non-Humans by +3/+3 and leaves Humans alone",
          (g.power_of(beast), g.power_of(human), g.m["wildspeaker_pumps"]),
          (9, 3, 1))

    # ---- Finale of Devastation --------------------------------------------
    # 11. Library AND/OR GRAVEYARD, onto the battlefield. A graveyard target
    # ties with a library one at the same mana value and wins the tie, because
    # taking it does not thin the library.
    g = fresh()
    baloths = named("Rampaging Baloths")                     # MV 6
    g.graveyard.append(baloths)
    g.resolve(M.FINALE_OF_DEVASTATION)
    check("Finale puts a creature onto the battlefield, graveyard first",
          (g.m["finale_from_yard"],
           any(p.card.name == "Rampaging Baloths" for p in g.board),
           baloths in g.graveyard), (1, True, False))

    # ---- War Room ---------------------------------------------------------
    # 12. {3}, {T}, one life -- and the life is really charged, which most
    # life costs in this project are not (§0i).
    g = fresh()
    for _ in range(4):
        g.make_permanent(forest())
    war = g.make_permanent(M.WAR_ROOM)
    life, drawn = g.your_life, g.m["cards_drawn"]
    g.activations()
    check("War Room draws for {3} and a tap, and really pays the life",
          (g.m["cards_drawn"] - drawn, g.your_life - life, war.tapped,
           g.m["war_room_draws"]), (1, -1, True, 1))

    # ---- Castle Garenbrig -------------------------------------------------
    # 13. "Enters tapped unless you control a Forest."
    tapped_states = []
    for have_forest in (False, True):
        g = fresh()
        if have_forest:
            g.make_permanent(forest())
        g.hand = [M.CASTLE_GARENBRIG]
        g.land_drops, g.land_drops_used = 1, 0
        g.land_step()
        castle = next(p for p in g.board
                      if p.card.name == "Castle Garenbrig")
        tapped_states.append(castle.tapped)
    check("Castle Garenbrig enters tapped only without a Forest",
          tuple(tapped_states), (True, False))

    # 14. Six {G} for {2}{G}{G} and a tap, creature spells only. Eight Forests
    # plus the Castle casts a ten-drop; eight Forests alone do not.
    g = fresh()
    for _ in range(8):
        g.make_permanent(forest())
    g.make_permanent(M.CASTLE_GARENBRIG)
    # The commander is cast before anything else and would eat three of the
    # nine mana, which is correct play and would hide what this checks.
    g.commander_cast = True
    kozilek = named("Kozilek, Butcher of Truth")             # MV 10
    g.hand = [kozilek]
    g.main_phase()
    lands_left = sum(1 for p in g.board if p.card.is_land and not p.tapped)
    check("Castle Garenbrig's six {G} casts a ten-drop off nine lands",
          (any(p.card.name == kozilek.name for p in g.board),
           g.m["castle_activations"], g.m["castle_mana_spent"], lands_left),
          (True, 1, 6, 0))

    # 15. ... and the restriction is real: the same nine lands may NOT cast a
    # ten-mana NONCREATURE, because the Castle's mana cannot pay for it.
    g = fresh()
    for _ in range(8):
        g.make_permanent(forest())
    g.make_permanent(M.CASTLE_GARENBRIG)
    # The commander is cast before anything else and would eat three of the
    # nine mana, which is correct play and would hide what this checks.
    g.commander_cast = True
    spell = Card(name="(ten-mana sorcery)", types=frozenset({"Sorcery"}),
                 cost={"gen": 10}, priority=9)
    g.hand = [spell]
    g.main_phase()
    check("Castle Garenbrig's mana cannot cast a noncreature spell",
          (spell in g.hand, g.m["castle_activations"]), (True, 0))

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        expected_fail = {
            "The Great Henge costs {7}{G}{G}, less the greatest power you control",
            "Sapling Nursery costs {1} less per FOREST, and Nykthos is not one",
            "Nissa doubles Forests in the pool AND taps one Forest for two",
            "Nissa -8 puts every Forest CARD from the library onto the "
            "battlefield, Dryad Arbor included",
            "Wildspeaker draws off the greatest NON-HUMAN power, ignoring a "
            "20/20 Human",
            "Wildspeaker pumps non-Humans by +3/+3 and leaves Humans alone",
            "Castle Garenbrig enters tapped only without a Forest",
        }
        actual_fail = set(FAIL)
        if actual_fail == expected_fail:
            print("  MUTATION CHECK OK -- exactly the cases that depend on the "
                  "mutated code failed, and nothing else did.")
            return 0
        print(f"  MUTATION CHECK FAILED\n"
              f"    expected to fail: {sorted(expected_fail)}\n"
              f"    actually failed : {sorted(actual_fail)}\n"
              f"    unexpected      : {sorted(actual_fail - expected_fail)}\n"
              f"    did not fail    : {sorted(expected_fail - actual_fail)}")
        return 1
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
