#!/usr/bin/env python3
"""Pin the mechanisms of the 2026-09-13 Azusa candidates (batch 4).

    python -m tests.test_azusa_batch4
    python -m tests.test_azusa_batch4 --mutate

Same shape and same reason as `test_azusa_batch3.py`: put the permanent on the
battlefield, fire the trigger, assert the printed effect happened. No sampling
and no error bars -- "does the engine do what the card says" is a different
question from "is the card good", and only the first can be answered exactly.

FOUR OF THESE CLAIMS ARE THE KIND THAT LOOK RIGHT AND ARE NOT:

  * Nissa, Resurgent Animist finds a card on the SECOND resolution and only the
    second. A third and fourth land add mana and nothing else. An engine that
    gave a card per land would be a strictly better card, and its row would be
    a measurement of a card that does not exist.
  * ... and "second RESOLUTION" is not "second land": with Ancient Greenwarden
    or Traveling Chocobo out, the FIRST land already resolves it twice. That
    falls out of counting resolutions and would not fall out of counting lands.
  * Traveling Chocobo STACKS with Ancient Greenwarden. Two effects that each
    say "triggers an additional time" make one land fire a payoff three times,
    not four -- each adds one instance.
  * Awaken the Woods' tokens are LAND CREATURES, so 302.6 applies to their mana
    ability and they tap for nothing the turn they arrive. The same rule was
    already being broken by Dryad Arbor, which is in the deck, and case 16
    pins that regression rather than leaving the fix untested.

`--mutate` turns four implementations off and asserts exactly the checks that
depend on them fail. A check that cannot fail reads like assurance and is worse
than none (§0z15).
"""
import inspect
import sys

from edhmc.azusa import AzusaGame, is_forest
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card
from edhmc import opponents as OPP
import edhmc.azusa as AZ

MUTATE = "--mutate" in sys.argv
CFG_EXTRA = {}

PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    deck, cmd = M.build()
    return AzusaGame(deck, cmd,
                     dict(DEFAULT_CFG, turns=20, **CFG_EXTRA, **cfg), 1234)


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


def _land_entered_pre_chocobo(self, card, played=False):
    """`land_entered` as it stood before Traveling Chocobo: Greenwarden is the
    only doubler. The mutation is the card's whole first half."""
    self.m["landfall_triggers"] += 1
    reps = 2 if self.has("Ancient Greenwarden") else 1
    self.m["landfall_ability_resolutions"] += reps
    for _ in range(reps):
        self._landfall_payoffs(card, played)


def main():
    if MUTATE:
        # (a) 302.6 for land creatures -- Awaken's tokens and Dryad Arbor tap
        #     for mana the turn they arrive again.
        CFG_EXTRA["land_creature_sick"] = False
        # (b) Traveling Chocobo's doubler, leaving Greenwarden's alone, so the
        #     STACKING case and the solo case are distinguished.
        AZ.AzusaGame.land_entered = _land_entered_pre_chocobo
        # (c) the Elf/Elemental subtype set -- Nissa's reveal finds nothing.
        AZ.ELF_ELEMENTAL = frozenset()
        # (d) the Forest-token set -- Awaken's tokens stop being Forests, which
        #     is a different claim from being lands and is checked separately.
        AZ.FOREST_TOKENS = frozenset()
        print("MUTATED: land-creature sickness off, Chocobo's doubler off, "
              "ELF_ELEMENTAL off, FOREST_TOKENS off\n")

    # ---- Nissa, Resurgent Animist -----------------------------------------
    # 1. Mana on EVERY landfall; a card on the SECOND resolution and no other.
    g = fresh()
    g.make_permanent(M.NISSA_RESURGENT_ANIMIST, sick=False)
    hand_before = len(g.hand)
    landfall(g, 3)
    check("Nissa adds mana on every landfall and finds a card on the SECOND "
          "only",
          (g.m["animist_mana"], len(g.bonus_mana), g.m["animist_cards"],
           len(g.hand) - hand_before), (3, 3, 1, 1))

    # 2. The counter is PER TURN, and take_turn is where it resets. Checked on
    # a game with no Nissa on the battlefield, so nothing can increment it
    # again during the turn take_turn plays.
    g = fresh()
    g.animist_resolutions = 5
    AZ.take_turn(g)
    check("the second-resolution counter resets at the start of each turn",
          g.animist_resolutions, 0)

    # 3. "Second time this ability has RESOLVED", not "second land": a doubler
    # gets there on the first land.
    g = fresh()
    g.make_permanent(named("Ancient Greenwarden"), sick=False)
    g.make_permanent(M.NISSA_RESURGENT_ANIMIST, sick=False)
    landfall(g, 1)
    check("with a doubler out, the FIRST land resolves it twice and finds the "
          "card",
          (g.m["animist_mana"], g.m["animist_cards"]), (2, 1))

    # 4. The reveal DIGS: exactly one card leaves the library for hand and the
    # rest go to the bottom, which is what re-rolls a dead top card.
    g = fresh()
    g.make_permanent(M.NISSA_RESURGENT_ANIMIST, sick=False)
    lib_before = len(g.library)
    landfall(g, 2)
    check("the reveal takes exactly one card out of the library and bottoms "
          "the rest",
          (lib_before - len(g.library), g.m["animist_revealed"] >= 1,
           g.m["animist_cards"]), (1, True, 1))

    # 5. A LIBRARY WITH NO ELF OR ELEMENTAL reveals the whole thing and finds
    # nothing. Deliberately an assertion about the WHIFF, so it still passes
    # under the mutation that empties the subtype set -- the mutation must not
    # be able to make every Nissa case fail for one reason.
    g = fresh()
    g.library = [Card(name="(filler)", types=frozenset({"Sorcery"}),
                      cost={"gen": 1}) for _ in range(5)]
    g.make_permanent(M.NISSA_RESURGENT_ANIMIST, sick=False)
    landfall(g, 2)
    check("with no Elf or Elemental left, it reveals the library and finds "
          "nothing",
          (g.m["animist_cards"], g.m["animist_whiffs"], len(g.library)),
          (0, 1, 5))

    # ---- Traveling Chocobo ------------------------------------------------
    # 6. The doubler is the card: one land, two Beasts.
    g = fresh()
    g.make_permanent(named("Rampaging Baloths"), sick=False)
    before = g.m["tokens_made"]
    landfall(g, 1)
    solo = g.m["tokens_made"] - before
    g2 = fresh()
    g2.make_permanent(named("Rampaging Baloths"), sick=False)
    g2.make_permanent(M.TRAVELING_CHOCOBO, sick=False)
    before2 = g2.m["tokens_made"]
    landfall(g2, 1)
    check("Traveling Chocobo doubles a landfall payoff",
          (solo, g2.m["tokens_made"] - before2), (1, 2))

    # 7. TWO doublers are three triggers, not four: each adds one instance.
    g = fresh()
    g.make_permanent(named("Rampaging Baloths"), sick=False)
    g.make_permanent(named("Ancient Greenwarden"), sick=False)
    g.make_permanent(M.TRAVELING_CHOCOBO, sick=False)
    before = g.m["tokens_made"]
    landfall(g, 1)
    check("Chocobo STACKS with Ancient Greenwarden: three triggers, not four",
          (g.m["tokens_made"] - before,
           g.m["landfall_ability_resolutions"]), (3, 3))

    # 8. "You may play lands ... from the top of your library" -- the half that
    # makes it a fifth top-of-library enabler.
    g = fresh()
    without = g.top_access()
    g.make_permanent(M.TRAVELING_CHOCOBO, sick=False)
    check("Traveling Chocobo grants top-of-library land access",
          (without, g.top_access()), (False, True))

    # ---- Archdruid's Charm ------------------------------------------------
    # 9. The land half: onto the BATTLEFIELD, TAPPED, firing landfall, and
    # costing no land drop.
    g = fresh(archdruid_mode="land")
    lands_before = sum(1 for p in g.board if p.card.is_land)
    triggers = g.m["landfall_triggers"]
    drops = g.land_drops_used
    g.archdruids_charm()
    put = [p for p in g.board if p.card.is_land]
    check("Archdruid's Charm puts a land onto the battlefield tapped, for a "
          "landfall and no land drop",
          (len(put) - lands_before, put and put[-1].tapped,
           g.m["landfall_triggers"] - triggers, g.land_drops_used - drops,
           g.m["charm_lands"]), (1, True, 1, 0, 1))

    # 10. The creature half goes to HAND, not to the battlefield. That is the
    # difference between this and a Green Sun's Zenith and it is most of why
    # the mode choice is not obvious.
    g = fresh(archdruid_mode="creature")
    hand_before = len(g.hand)
    board_before = len(g.board)
    g.archdruids_charm()
    check("Archdruid's Charm's creature mode goes to HAND, not the battlefield",
          (len(g.hand) - hand_before, len(g.board) - board_before,
           g.m["charm_creatures"]), (1, 0, 1))

    # 11. The "auto" policy, stated in one place and checked here: the land
    # while a land-relevant permanent is out, the creature otherwise.
    g = fresh(archdruid_mode="auto")
    g.archdruids_charm()
    empty_board = (g.m["charm_lands"], g.m["charm_creatures"])
    g = fresh(archdruid_mode="auto")
    g.make_permanent(named("Lotus Cobra"), sick=False)
    g.archdruids_charm()
    check("auto takes the creature on an empty board and the land with a "
          "payoff out",
          (empty_board, (g.m["charm_lands"], g.m["charm_creatures"])),
          ((0, 1), (1, 0)))

    # ---- Awaken the Woods --------------------------------------------------
    # 12. X tokens, each a LAND and a CREATURE, each firing landfall.
    g = fresh()
    triggers = g.m["landfall_triggers"]
    g.awaken_the_woods(3)
    toks = [p for p in g.board if p.card.name == "Forest Dryad token"]
    check("Awaken the Woods makes X land-creature tokens, each firing landfall",
          (len(toks), all(p.card.is_land and p.card.is_creature for p in toks),
           g.m["landfall_triggers"] - triggers, g.m["awaken_tokens"]),
          (3, True, 3, 3))

    # 13. 302.6: they are creatures, so their {T} mana ability is off the turn
    # they arrive -- the card's own reminder text says so -- and on the next.
    g = fresh()
    g.awaken_the_woods(2)
    same_turn = len(g.available_mana())
    for p in g.board:
        p.sick = False                      # what take_turn does
    check("Awaken's tokens make no mana the turn they arrive, and do the next",
          (same_turn, len(g.available_mana())), (0, 2))

    # 14. They are FORESTS, which is a different claim from being lands: it is
    # what Sapling Nursery's affinity and Nissa Who Shakes the World read.
    g = fresh()
    g.awaken_the_woods(3)
    check("Awaken's tokens are Forests for Sapling Nursery's affinity",
          (g.forests(), g.cost_of(M.SAPLING_NURSERY)["gen"],
           all(is_forest(p.card) for p in g.board)), (3, 3, True))

    # 15. And they are creatures for the POD, so a wrath kills them. Animated
    # lands deliberately do not die to one (see opponents.is_creature_now);
    # these are not animated lands and must not inherit that exemption.
    g = fresh()
    g.awaken_the_woods(1)
    tok = next(p for p in g.board if p.card.name == "Forest Dryad token")
    check("Awaken's tokens are creatures for the pod's wraths",
          OPP.is_creature_now(g, tok), True)

    # ---- Dryad Arbor, the same rule on a card already in the deck ----------
    # 16. THE REGRESSION THIS FIX CLOSES. Dryad Arbor is a Land Creature and
    # has been in this list since 2026-09-07, tapping for {G} on the turn it
    # was played for the life of the project.
    g = fresh()
    g.make_permanent(named("Dryad Arbor"))
    same_turn = len(g.available_mana())
    for p in g.board:
        p.sick = False
    check("Dryad Arbor makes no mana the turn it is played (302.6)",
          (same_turn, len(g.available_mana())), (0, 1))

    # ---- Expedition Map ----------------------------------------------------
    # 17. {2}, {T}, sacrifice -> a land in HAND, and the densest one it can
    # find, which is a fetch.
    g = fresh()
    g.hand = []
    for _ in range(2):
        g.make_permanent(forest(), sick=False)
    g.make_permanent(M.EXPEDITION_MAP, sick=False)
    g.expedition_map_step()
    check("Expedition Map sacrifices itself for a fetch land in hand",
          (g.m["map_cracked"], len(g.hand),
           bool(g.hand) and g.hand[0].script == "fetch",
           any(p.card.name == "Expedition Map" for p in g.board),
           "Expedition Map" in [c.name for c in g.graveyard]),
          (1, 1, True, False, True))

    # 18. ... and it does NOT fire for a land it cannot use: a land already in
    # hand and no drop left is three mana for nothing.
    g = fresh()
    g.hand = [forest()]
    g.land_drops_used = g.land_drops
    for _ in range(2):
        g.make_permanent(forest(), sick=False)
    g.make_permanent(M.EXPEDITION_MAP, sick=False)
    g.expedition_map_step()
    check("Expedition Map holds when the land it would find is dead weight",
          (g.m["map_cracked"],
           any(p.card.name == "Expedition Map" for p in g.board)),
          (0, True))

    # ---- Zuran Orb ---------------------------------------------------------
    # 19. With Titania out, each sacrificed land is a 5/3 and two life, and the
    # land reaches the graveyard where her trigger reads it.
    g = fresh()
    g.make_permanent(named("Titania, Protector of Argoth"), sick=False)
    g.make_permanent(M.ZURAN_ORB, sick=False)
    for _ in range(8):
        g.make_permanent(forest(), tapped=True)
    life_before = g.your_life
    g.zuran_orb_step()
    check("Zuran Orb sacrifices tapped lands for life and Titania's "
          "Elementals",
          (g.m["zuran_sacs"], g.your_life - life_before,
           sum(1 for p in g.board if p.card.name == "Elemental token"),
           sum(1 for p in g.board if p.card.is_land)), (2, 4, 2, 6))

    # 20. With no payoff and a healthy life total it does NOTHING. Two life for
    # a land is a bad rate, and a policy that took it anyway would be inventing
    # a play rather than modelling one.
    g = fresh()
    g.make_permanent(M.ZURAN_ORB, sick=False)
    for _ in range(8):
        g.make_permanent(forest(), tapped=True)
    g.zuran_orb_step()
    check("Zuran Orb does nothing without Titania, recursion or a low life "
          "total", (g.m["zuran_sacs"], sum(1 for p in g.board
                                           if p.card.is_land)), (0, 8))

    # 21. And it never cuts into the lands it promised to keep.
    g = fresh(zuran_keep=6)
    g.make_permanent(named("Titania, Protector of Argoth"), sick=False)
    g.make_permanent(M.ZURAN_ORB, sick=False)
    for _ in range(6):
        g.make_permanent(forest(), tapped=True)
    g.zuran_orb_step()
    check("Zuran Orb stops at zuran_keep lands",
          (g.m["zuran_sacs"], sum(1 for p in g.board if p.card.is_land)),
          (0, 6))

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        # WRITTEN BEFORE THE RUN, per the standing finding: a mutation list
        # written after seeing the output is a transcript, not a test.
        expected_fail = {
            # (a) land-creature summoning sickness
            "Awaken's tokens make no mana the turn they arrive, and do the next",
            "Dryad Arbor makes no mana the turn it is played (302.6)",
            # (b) Chocobo's doubler
            "Traveling Chocobo doubles a landfall payoff",
            "Chocobo STACKS with Ancient Greenwarden: three triggers, not four",
            # (c) the Elf/Elemental set
            "Nissa adds mana on every landfall and finds a card on the SECOND "
            "only",
            "with a doubler out, the FIRST land resolves it twice and finds "
            "the card",
            "the reveal takes exactly one card out of the library and bottoms "
            "the rest",
            # (d) the Forest-token set
            "Awaken's tokens are Forests for Sapling Nursery's affinity",
        }
        actual_fail = set(FAIL)
        if actual_fail == expected_fail:
            print("  MUTATION CHECK OK -- exactly the cases that depend on the "
                  "mutated code failed, and nothing else did.")
            return 0
        print(f"  MUTATION CHECK FAILED\n"
              f"    unexpected   : {sorted(actual_fail - expected_fail)}\n"
              f"    did not fail : {sorted(expected_fail - actual_fail)}")
        return 1
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
