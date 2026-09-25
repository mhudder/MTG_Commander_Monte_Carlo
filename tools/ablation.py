#!/usr/bin/env python3
"""
Leave-one-out ablation for the Lorehold deck.

For each nonland card, replace it with a neutral blank of the same mana value
and measure the paired difference. Common random numbers make a one-card
ablation measurable; the blank occupies the same library slot, so the other 98
cards are dealt identically in both branches.

    contribution = metric(with card) - metric(with blank)

Positive means the card earns its slot. Near zero means it does nothing the
model can see.

READ THE CAVEAT
---------------
The engine scripts roughly 30 of the 65 nonland cards. The rest are modelled
faithfully as a mana cost, a type line and a body, which is correct for a
creature but blind for a removal spell: Swords to Plowshares kills nothing here,
because the opponents' boards are abstracted to a blocker count.

So the output is split into THREE groups (the third added 2026-09-10):

  MODEL-EVALUATED  the engine implements the card. A low score is evidence
                   about the card.
  PARTLY MODELLED  the engine implements PART of the card, and the missing
                   part can only add. A HIGH score is evidence; A LOW SCORE IS
                   NOT. Each row prints the specific gap. Never cut on one --
                   two swaps have already been withdrawn or refused on exactly
                   this (§0z, §0z2).
  MODEL-BLIND      the engine does not implement the card at all. A low score
                   is evidence about the MODEL. Not a cut list.

Usage:  python ablation.py [deck] [n_games] [turns]

RUNTIME
-------
Two things make this fast, and NEITHER changes a single simulated game.

1. THE BASELINE IS SIMULATED ONCE, NOT ONCE PER CARD. Every card's paired
   difference is `metric(real deck) - metric(deck with this slot blanked)`,
   and the first term does not depend on which card is under test. The old
   loop re-simulated the untouched deck for all 65 cards, so exactly half of
   every run was spent recomputing one fixed number. Cards are never mutated
   anywhere in edhmc and `simulate` copies the deck it is handed, so the
   baseline really is identical — see the verification note below.

2. CARDS ARE ABLATED IN PARALLEL. Each card is an independent, deterministic
   function of (deck, seed), so the work splits across cores with no shared
   state. `ABLATE_PROCS` sets the worker count and defaults to every core;
   `ABLATE_PROCS=1` forces the old single-process path, which is the one to
   use when debugging and which writes the identical cache.

VERIFIED OUTPUT-IDENTICAL. Both changes are pure scheduling: the same seeds
feed the same engines and the arrays are subtracted in the same order, so the
numbers are bit-for-bit what the serial code produced. The check that matters
is not this comment — it is that regenerating a cache from empty reproduces
the committed one to the last digit.
"""
import json
import os
import sys
import textwrap
import time
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count

import numpy as np

# Card names carry non-ASCII (Olórin's Searing Light). On Windows a redirected
# stdout defaults to the console codepage and writes cp1252, which makes the
# saved table invalid UTF-8. Force it.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

from edhmc.engine import Card
from edhmc.pending import build_pending
from edhmc.registry import DECKS
from edhmc.experiment import DEFAULT_CFG, BLANK_PRIORITY, repl_priority

# Derived from edhmc/registry.py (§0z32): one place names an engine and its
# metric columns, and a seventh deck cannot be simulated without a table
# definition or vice versa.
SIMS = {name: spec.sim for name, spec in DECKS.items()}


@dataclass(frozen=True)
class Run:
    """One ablation run's parameters, passed explicitly to everything.

    Until 2026-09-17 (M4 of that day's review) these were module globals
    derived from `sys.argv` AT IMPORT -- `DECK = sys.argv[1]` -- and rebound
    a second time inside `_worker_init` so a spawned worker could not measure
    a different deck than the parent asked for. Importing the module from
    anywhere else (a test of the classification checker, a re-render of a
    table from its cache, `pending.py` wanting to know whether a proposed cut
    is MODEL-BLIND) picked up whatever argv the importer had, and three docs
    described working around that. Now `main()` parses argv into one of
    these and hands it down; a worker gets the same object in its
    initializer; nothing reads argv but `parse_args`.
    """
    deck: str
    n: int
    # Report a RANGE of horizons rather than one. The cutoff turn is a free
    # parameter created by the fact that opponents have no win condition, and
    # it systematically favours slow, accumulating cards. A conclusion is only
    # trustworthy if its SIGN and RANK survive the whole range.
    horizons: tuple = (20,)   # with the opponent clock, games end around T12
    # See blank_like(). True isolates a card's text from its type line.
    blank_keeps_types: bool = False

    @property
    def sim(self):
        return SIMS[self.deck]

    @property
    def metrics(self):
        return METRIC_SETS[self.deck]

    @property
    def scripted(self):
        return SCRIPTED_BY_DECK[self.deck]

    @property
    def cache(self):
        # The key MUST include every parameter that changes what a cached
        # number MEANS. It used to key on deck and horizons only, so resuming
        # a run at a different sample size silently merged two sample sizes
        # into one table; hence `_n{N}`. `_medblank` / `_deadblank` is here
        # for the same reason: the 2026-09-06 blank priority change moves
        # every number, and the pre-change files carry NEITHER suffix, so
        # they can no longer be picked up by a run that would misread them.
        #
        # The directory is part of the path and NOT part of the key:
        # `results/caches/` is where every cache has lived since the
        # 2026-09-09 reorganisation, and the name inside it is unchanged, so
        # a cache from before the move is still picked up by a run that
        # should pick it up. Moving these files was allowed to change where
        # they are and forbidden to change what they mean.
        return os.path.join(
            "results", "caches",
            f"ablation_cache_{self.deck}_{'-'.join(map(str, self.horizons))}"
            f"_n{self.n}"
            f"{'_sametype' if self.blank_keeps_types else ''}"
            f"{'_deadblank' if BLANK_PRIORITY == 'dead' else '_medblank'}.json")


def parse_args(argv) -> Run:
    """`deck [N [h1,h2,...]]`, plus BLANK_KEEPS_TYPES from the environment."""
    deck = argv[0] if argv else "lorehold"
    n = int(argv[1]) if len(argv) > 1 else 4000
    horizons = (tuple(int(x) for x in argv[2].split(","))
                if len(argv) > 2 else (20,))
    return Run(deck, n, horizons,
               os.environ.get("BLANK_KEEPS_TYPES", "0") == "1")
METRIC_SETS = {name: spec.metrics for name, spec in DECKS.items()}

# Cards whose actual text the engine implements. Everything else is a body.
SCRIPTED_RENDMAW = {
    # --- scripted LANDS, classified since 2026-09-12 ---
    # `check_scripted_coverage` used to skip every land, so a script on a
    # land was an unchecked claim. These are implemented; Rogue's Passage
    # was the one that was not, and it is in KNOWN_BLIND with its reason.
    "Khalni Garden",               # engine.run_etb -> a 0/1 Plant
    # mana
    "Sol Ring", "Arcane Signet", "Golgari Signet", "Copper Myr", "Leaden Myr",
    "Palladium Myr", "Ornithopter of Paradise", "Twitching Doll",
    "Dryad of the Ilysian Grove", "Enduring Vitality", "The Great Henge",
    "Overlord of the Hauntwoods", "Foundry Inspector",
    # token engines
    "Bitterblossom", "Ophiomancer", "Tendershoot Dryad", "Grist, the Hunger Tide",
    "Grave Titan", "Woe Strider", "Arasta of the Endless Web",
    "Primal Vigor", "Metallic Mimic",
    # payoffs / draw / sac  (Skullclamp left the deck in v12)
    "Idol of Oblivion", "Steel Overseer", "Ohran Frostfang",
    "Coat of Arms", "Beastmaster Ascension", "Verdurous Gearhulk",
    "Roaming Throne", "Erebos, Bleak-Hearted", "Dockside Chef",
    "Solemn Simulacrum",
    # aristocrats drain
    "Blood Artist", "The Meathook Massacre",
    # Staged 2026-09-04. Both halves are in engine.py: the "each opponent
    # loses 1 life and you gain 1" death trigger, and the {1}{B}{G}, {T}, sac
    # a creature reanimation in activations().
    "Cauldron of Essence",
    # --- §3 closed 2026-09-13 (§0z20). Both were in KNOWN_BLIND while being
    # implemented in activations(), which is §0q's shape: the label is a claim
    # and the claim was false.
    # Ashnod's Altar: "Sacrifice a creature: Add {C}{C}." Both halves now --
    # the deaths it manufactures for Blood Artist / Meathook, and the MANA,
    # which used to arrive after the main phase and so could not be spent.
    # Deathreap Ritual: "At the beginning of EACH end step, if a creature died
    # this turn, you may draw a card" -- your end step plus the pod's three,
    # each gated on opp_death_rate. It was never unimplemented at all.
    "Ashnod's Altar", "Deathreap Ritual",
    # --- §7 closed for Rendmaw 2026-09-13 (§0z19) ---
    # "When this creature dies, return ANOTHER target artifact card from your
    # graveyard to your hand." Both are the same trigger; Junk Diver also
    # flies, which decks/_evasion.py already carries. Fully implemented in
    # Game.artifact_died, reached through opponents.destroy().
    "Myr Retriever", "Junk Diver",
    # protection the opponent model respects
    "Heroic Intervention",
    # static P/T setter (implemented in Game.power_of / toughness_of), and
    # since §0z47 the Elephant trigger, on the one opponent spell the model
    # puts on your turn (a counterspell) -- `engine.march_elephant`
    "March of the World Ooze",
}

# Reviewed 2026-09-03. Monologue Tax, Hidden Retreat, Urabrask and Triumph of
# Saint Katherine left the deck in v16 and are gone from this list with them.
SCRIPTED_LOREHOLD = {
    # --- §0f closed 2026-09-12, except Borrowed Knowledge's mode 1 ---
    # Apex of Power: exile seven, cast from among them, and ten mana of ONE
    # colour -- and no mana on a copy, which is the 'cast from your hand'
    # clause. Hit the Mother Lode: Discover 10 with the free cast and
    # 10-minus-MV TAPPED Treasures, which are not mana until they untap.
    "Apex of Power", "Hit the Mother Lode",
    # --- §7 closed for Lorehold 2026-09-13 (§0z19) ---
    # Invoke Calamity: up to two instants/sorceries, TOTAL mana value 6 or
    # less, from graveyard AND hand, free, then exiled. A FLOOR only in that
    # it is an instant and this engine casts at sorcery speed.
    # Goliath Daydreamer: BOTH halves, and the first is a drawback -- spells
    # cast from hand are exiled with a dream counter instead of reaching the
    # graveyard this deck's whole engine feeds on. Measured at +0.0033
    # ±0.0057, i.e. inside its bar: the anti-synergy §7 warned about is real
    # and does not dominate.
    "Invoke Calamity", "Goliath Daydreamer",
    # mana
    "Sol Ring", "Arcane Signet", "Boros Signet", "Talisman of Conviction",
    "Ruby Medallion", "Bender's Waterskin", "Victory Chimes",
    # top-of-library manipulation. Penance and Scroll Rack are STAGED OUT
    # (2026-09-05) and stay classified: both are implemented (lorehold's
    # top-setter table prices them), and a staged cut's row has to be known
    # to have been evidence -- `pending.check_cuts_are_measured` refuses a
    # cut in no category (§0z31). A name here that is not in the measured
    # list is a NOTE, not a failure, by check_scripted_coverage's design.
    "Sensei's Divining Top", "Library of Leng", "Penance", "Scroll Rack",
    "Verge Rangers",
    # Replaced Penance in the 2026-09-05 re-staging, having beaten Galvanoth
    # head to head (+0.0093 win at 20 turns). Implemented in full in
    # lorehold.apply_spell_effects: a +1/+1 counter FIRST, then damage equal
    # to its power to ONE opponent, on every instant or sorcery CAST — so
    # Bombardment and Mastery copies set it off and Double Vision copies,
    # which are put on the stack rather than cast, do not. It is a flier and
    # is tagged as one in decks/_evasion.py; that was not true before
    # 2026-09-05, when tag_flying.py did not walk candidates.
    "Caldera Pyremaw",
    # card flow. Borrowed Knowledge and Apex of Power were here until
    # 2026-09-10 and are now in PARTLY_MODELLED -- §0f found neither is
    # implemented as its text, and this set is a claim that they are.
    "Thrill of Possibility", "Faithless Looting", "Big Score",
    "Unexpected Windfall", "Reforge the Soul",
    # treasures / cost. Hit the Mother Lode likewise: see PARTLY_MODELLED.
    "Storm-Kiln Artist", "Smothering Tithe",
    # damage / win conditions
    "Guttersnipe", "Longshot, Rebel Bowman", "Soulfire Eruption",
    "Boros Charm", "Olórin's Searing Light", "Emeria's Call",
    "Rise of the Eldrazi",
    # Staged 2026-09-04. lorehold.sunbird() implements the whole text: reveal
    # the top X where X is the triggering spell's mana value, free-cast one
    # spell of MV <= X from among them, bottom the rest in random order — and
    # it fires only on casts FROM HAND, so miracles trigger it and Galvanoth,
    # Scrollwielder, Archaic and the copy engines do not.
    "Sunbird's Invocation",
    # copy engines
    "Double Vision", "Arcane Bombardment", "Mizzix's Mastery",
    "Monastery Mentor", "Monument to Endurance",
    # protection the opponent model respects
    "Lightning Greaves", "Mother of Runes",
    # cost reduction that scales with the graveyard / board
    # (Blasphemous Act moved to PARTLY_MODELLED 2026-09-12: it is a symmetric
    #  wipe, and those are derived into that category -- see symmetric_wipes().)
    "The Dawning Archaic",
    # All three levels since §0z48: the level-1 rummage, the level-2
    # noncreature discount, the level-3 +2 per noncombat hit at
    # `deal_pod_damage`, and a level-up POLICY (spare post-combat mana). It
    # was BLIND until then -- level 2 granted free on resolution, applied to
    # creature spells too, and levels 1 and 3 absent.
    "Artist's Talent",
    # BLIND, despite having engine code — the implementation is not the card:
    #   Storm Herd      - X is cfg["storm_herd_x"]=40, not your life total
    #   Approach of the Second Sun - never gets its second cast, because the
    #                     card is not put seventh from the top
}

# Reviewed 2026-09-03 against the oracle audit. Membership here is a claim
# that the ENGINE implements the card's text, so a low score is evidence about
# the card. Cards whose text is still approximated belong in the blind group
# even when they are not literally absent from the engine.
SCRIPTED_KARLOV = {
    # Bolas's Citadel (staged 2026-09-12). `karlov.citadel_step` plays lands
    # and casts spells off the top paying LIFE = mana value, in forced library
    # order, and `citadel_land_step` spends the land drop on a land on top so
    # it does not block the dig. The sac-ten drain is implemented lethal-only,
    # which is a floor on that half. It used to be called a CEILING for
    # queued item 17 (nothing lost to decking); decking loses now and the
    # karlov baseline did not move with it, so that caveat is closed (§0z42).
    "Bolas's Citadel",
    # lifegain engines
    "Soul Warden", "Soul's Attendant", "Suture Priest", "Auriok Champion",
    "Daxos, Blessed by the Sun", "Authority of the Consuls",
    "Ajani's Mantra", "Fountain of Renewal", "Drana's Emissary",
    "Blind Obedience", "Kambal, Consul of Allocation", "Sunscorch Regent",
    "Elas il-Kor, Sadistic Pilgrim", "Radiant Fountain",
    # lifegain payoffs
    "Voice of the Blessed", "Archangel of Thune", "Cliffhaven Vampire",
    "Marauding Blight-Priest", "Sanguine Bond", "Vito, Thorn of the Dusk Rose",
    "Vizkopa Guildmage", "Exquisite Blood", "Felidar Sovereign",
    "Aetherflux Reservoir", "Well of Lost Dreams", "Cosmos Elixir",
    "Dawn of Hope", "Blood Artist", "Syr Konrad, the Grim",
    "Debt to the Deathless", "Serra Ascendant",
    # other
    "Sol Ring", "Orzhov Signet", "Pristine Talisman", "Land Tax",
    "Phyrexian Arena", "Mother of Runes",
    "Swiftfoot Boots", "Sorin, Vengeful Bloodlord",
    "Sorin, Solemn Visitor", "Kalitas, Traitor of Ghet",
    # Added to the deck in v2, 2026-09-04. All three have their full text in
    # karlov.py: Starscape Cleric's "each opponent loses 1" and its Offspring
    # token copy, Enduring Tenacity's Sanguine Bond trigger AND its
    # return-as-an-enchantment death trigger (it is also in COMBO_LOOP), and
    # Exemplar of Light's counter-per-lifegain-event with the once-a-turn
    # draw. Their FLYING is unmodelled, but flying is unmodelled for every
    # creature in the engine — a global gap, not a per-card approximation, and
    # the same one Serra Ascendant already carries in this set.
    "Starscape Cleric", "Enduring Tenacity", "Exemplar of Light",
    # MOVED OUT to the blind group 2026-09-03, still approximated:
    #   Necropotence      - modelled as "draw 2", not skip-draw-step + pay life
    #   Benevolent Offering - flat 4 life, no per-creature scaling, no tokens
    #   Ranger of Eos     - "draw 2", not a tutor for two specific one-drops
}

# Written 2026-09-05 with the deck. Membership here is a CLAIM THAT THE ENGINE
# IMPLEMENTS THE CARD'S TEXT, so a low score is evidence about the card. A card
# whose text is only approximated belongs in KNOWN_BLIND even when it has
# engine code -- that distinction is the one this project has got wrong twice.
SCRIPTED_TIVIT = {
    # 2026-09-16 (§0z26). Doubles BOTH of this engine's token paths --
    # make_tokens() for creature tokens and the module-level
    # make_token() for the Clue/Food/Treasure piles. Fully implemented,
    # so a low score would be evidence about the card.
    "Anointed Procession",

    # --- scripted LANDS, classified since 2026-09-12 ---
    # `check_scripted_coverage` used to skip every land, so a script on a
    # land was an unchecked claim. These are implemented; Rogue's Passage
    # was the one that was not, and it is in KNOWN_BLIND with its reason.
    "Havengul Laboratory // Havengul Mystery",   # tivit.resolve `havengul`
    # --- the artifact engine ---
    # Every one of these is fully implemented in tivit.make_token /
    # sacrifice_tokens / deadeye_loop.
    "Academy Manufactor",          # the Clue/Food/Treasure replacement
    "Time Sieve", "Mechanized Production", "Revel in Riches",
    "Disciple of the Vault", "Marionette Master", "Mirkwood Bats",
    "Nadier's Nightblade", "Kambal, Profiteering Mayor",
    "Cyberdrive Awakener",
    # --- blink: each is a fresh Tivit ETB, which is a fresh dilemma ---
    "Ephemerate", "Soulherder", "Displacer Kitten", "Teleportation Circle",
    "Conjurer's Closet", "Deadeye Navigator",
    # --- sweepers, live since 2026-09-12 ---
    # `tivit.resolve` had no `wipe` branch, so these did nothing; they are
    # implemented now. DAMN AND FAREWELL LEFT THIS SET ON 2026-09-12 (the same
    # day) for PARTLY_MODELLED: both are SYMMETRIC wipes, and the claim made
    # here -- that "your board dies, theirs goes to 0" is faithful -- is only
    # half true. Your half is faithful; theirs zeroes an abstract creature
    # count. See symmetric_wipes(), which now derives that category.
    # Sadistic Shell Game STAYS, and the distinction is the point: it is one
    # kill per player off the biggest board, which is exactly what its text
    # says and what the `creatures` float can carry. It is not a wipe.
    "Sadistic Shell Game",
    # --- the vote ---
    # Extra votes are the whole mechanic and are read by voting.my_votes().
    "Ballot Broker", "Brago's Representative",
    "Illusion of Choice",          # voting.vote_control
    "Grudge Keeper",               # voting._vote_payoffs
    "Master of Ceremonies", "Tempting Contract", "Tempt with Bunnies",
    "Coercive Portal", "Plea for Power", "Lieutenants of the Guard",
    "Messenger Jays", "Tyrant's Choice", "Custodi Squire",
    # --- mana and draw ---
    "Sol Ring", "Arcane Signet", "Azorius Signet", "Dimir Signet",
    "Orzhov Signet", "Model of Unity", "Monologue Tax",
    "Tamiyo's Journal", "Demonic Tutor", "Idyllic Tutor",
    # --- protection the opponent model respects ---
    "Lightning Greaves",
}

# Written 2026-09-07 with the deck (the least tuned of the five -- see
# shilgengar_v1.py). Membership is a claim that edhmc.shilgengar implements
# the card's text; several entries are explicitly PARTIAL and say so at their
# definition in that module (Massacre Wurm's ETB, Elesh Norn's team half only,
# Avacyn's protection against opponent-sourced destroy() only, Skullclamp
# restricted to token fodder, Voldaren Bloodcaster with no transform).
SCRIPTED_SHILGENGAR = {
    # NOTE: the commander itself is never in `deck` (build() returns it
    # separately), so it does not belong in this set -- same as every other
    # deck's commander.
    # Angels tribal
    "Archangel of Thune", "Resplendent Angel", "Righteous Valkyrie",
    "Bishop of Wings", "Giada, Font of Hope", "Youthful Valkyrie",
    "Lyra Dawnbringer", "Speaker of the Heavens",
    "Emeria's Call // Emeria, Shattered Skyclave",
    "Elesh Norn, Grand Cenobite", "Avacyn, Angel of Hope",
    # aristocrats: death triggers and sac outlets
    "Blood Artist", "Zulaport Cutthroat", "Midnight Reaper", "Grim Haruspex",
    "Dark Prophecy", "Pitiless Plunderer", "Requiem Angel",
    "Voldaren Bloodcaster // Bloodbat Summoner", "Viscera Seer",
    "Cartel Aristocrat", "Vampiric Rites", "Skullclamp",
    # reanimation
    "Priest of Fell Rites", "Sun Titan", "Reya Dawnbringer",
    "Emeria Shepherd",
    # drain / removal on a body that is a REAL death trigger, not blank
    "Kokusho, the Evening Star", "Massacre Wurm",
    # mana and draw
    "Smothering Tithe", "Black Market Connections", "Phyrexian Arena",
    "Sol Ring", "Arcane Signet", "Orzhov Signet", "Fellwar Stone",
    "Mind Stone", "Marble Diamond", "Talisman of Hierarchy",
    "Wayfarer's Bauble",
    # protection the opponent model respects
    "Flawless Maneuver", "Teferi's Protection",
    # The two wraths (Damn, Wrath of God) moved to PARTLY_MODELLED 2026-09-12:
    # symmetric wipes are derived into that category by symmetric_wipes().
}

# Written 2026-09-07 with the deck (the least tuned of the six -- see
# azusa_v1.py). Membership is a claim that edhmc.azusa implements the card's
# text; X-spells are modelled at a fixed X (documented in azusa_v1.py).
#
# ASHAYA AND BANE OF PROGRESS HAVE MOVED to PARTLY_MODELLED (2026-09-10),
# which is the third category this comment used to say the project did not
# have. Queued items 14 and 14b, KNOWN_ISSUES §0z and §0z2.
#
# (An earlier version of this comment said Ashaya's gap was "called out at its
# definition in edhmc/azusa.py". It was not, and never had been -- a pointer
# to a note that does not exist is worse than no note, because it stops the
# next reader looking. The call-out now exists, in DYNAMIC_PT_LANDS.)
SCRIPTED_AZUSA = {
    # ASHAYA CAME BACK 2026-09-13 (§0z18, queued 15). Both clauses are now
    # implemented: the */* off the land count, and "nontoken creatures you
    # control are Forest lands in addition to their other types" -- the mana
    # ability (305.7), the landfall its creatures fire as they enter (the
    # official ruling, and the opposite of what the old note said), Titania
    # reading creature deaths as land deaths, and the Forest count that
    # Sapling Nursery and Nissa read. It spent three days in PARTLY_MODELLED,
    # which is the category working as designed: the label named the missing
    # clause, the clause got written, and the label moved back.
    "Ashaya, Soul of the Wild",
    # --- scripted LANDS, classified since 2026-09-12 ---
    # `check_scripted_coverage` used to skip every land, so a script on a
    # land was an unchecked claim. These are implemented; Rogue's Passage
    # was the one that was not, and it is in KNOWN_BLIND with its reason.
    # Fetches crack for a land, which is a landfall trigger and a shuffle
    # drawn from a pre-rolled stream so CRN survives (engine.CRNStreams).
    "Terramorphic Expanse", "Windswept Heath", "Wooded Foothills",
    # extra land drops
    "Exploration", "Oracle of Mul Daya", "Wayward Swordtooth",
    # landfall payoffs
    "Avenger of Zendikar", "Courser of Kruphix", "Lotus Cobra",
    "Rampaging Baloths", "Scute Swarm", "Tireless Provisioner",
    "Tireless Tracker", "Titania, Protector of Argoth", "Seer's Sundial",
    "Horn of Greed",
    # play lands from an extra zone
    "Augur of Autumn", "Ramunap Excavator", "Crucible of Worlds",
    # tutors / ETB value
    "Craterhoof Behemoth", "Eternal Witness", "Woodland Bellower",
    "Nissa, Vastwood Seer // Nissa, Sage Animist", "Yavimaya Elder",
    # Bane of Progress and Ashaya were HERE until 2026-09-10 and are now in
    # PARTLY_MODELLED, which is the category this comment block used to say the
    # project did not have. See below.
    # --- 2026-09-10 additions. Each of these is a CLAIM that edhmc.azusa
    # implements the card's text, made deliberately and with its limits said:
    #
    #   Ancient Greenwarden   FULL -- graveyard lands, the 5/7 reach body, and
    #       the landfall DOUBLER (every payoff in _landfall_payoffs runs
    #       twice). §0x measured the halves apart; both are real.
    #   Greensleeves          FULL -- landfall makes a 3/3 Badger, and its
    #       */* reads the land count via DYNAMIC_PT_LANDS.
    #   Ka-Zar of the Savage  FULL -- top-of-library land access plus Zabu,
    #       Land              the token that takes a +1/+1 counter on every
    #                         landfall. (STAGED, not committed; it is here
    #                         because build_pending applies the stage.)
    #   Springheart Nantuko   A FLOOR, and the only one of the four that is.
    #       Bestow and the pay-{1}{G}-to-copy-the-host mode ARE implemented
    #       (§0z1), but a token copy does NOT re-trigger the host's ETB, so
    #       copying Avenger of Zendikar or Craterhoof scores as a bare body.
    #       SCRIPTED rather than KNOWN_BLIND because the mechanism is real and
    #       measured; the understatement is bounded and one-directional.
    "Ancient Greenwarden", "Greensleeves, Maro-Sorcerer",
    "Ka-Zar of the Savage Land", "Springheart Nantuko",
    # Traveling Chocobo (STAGED 2026-09-22, not committed; here because
    # build_pending applies the stage). FULL on what the list can reach: the
    # landfall DOUBLER stacks with Greenwarden's (three reps, not four), and
    # it is a source of `top_access`. "Cast Bird spells from the top" is
    # modelled as nothing because this card is the only Bird in the list --
    # exact for this list, a floor for any list with another Bird. The
    # doubler does NOT reach Horn of Greed, which triggers on PLAYING a land
    # (§0z41), and until that fix it did.
    "Traveling Chocobo",
    "Green Sun's Zenith", "Chord of Calling",
    # ramp / land tutors
    "Cultivate", "Kodama's Reach", "Seek the Horizon", "Journey of Discovery",
    "Realms Uncharted", "Nylea's Intervention", "Life from the Loam",
    "Regrowth", "Animist's Awakening", "Genesis Wave",
    # sac-for-value (token fodder only)
    "Perilous Forays", "Momentous Fall",
    # LAND ANIMATION IS GONE FROM THIS DECK as of 2026-09-10. Sylvan Awakening,
    # Rude Awakening and Nissa, Worldwaker were all here -- the animations were
    # real continuous effects with per-card durations as of 2026-09-07, and
    # Nissa moved here from KNOWN_BLIND the same day -- and all three were cut
    # for Ancient Greenwarden, Greensleeves and Springheart Nantuko (§0y).
    # Their scripts remain in edhmc/azusa.py because diag_azusa_animation.py
    # is the evidence for the cut and still exercises them.
    #
    # Nissa, Vastwood Seer // Sage Animist is NOT affected and stays: §0s found
    # the Nissas were never the animation story, and she is a top-five card.
    "Sol Ring", "Harmonize", "Eye of Ugin",
    # Annihilator, approximated as reducing an opponent's abstract creature
    # count -- value denial, not damage
    "Kozilek, Butcher of Truth", "Ulamog, the Infinite Gyre",
}

# ---------------------------------------------------------------------------
# PARTLY MODELLED — the third category (2026-09-10, queued items 14 and 14b)
# ---------------------------------------------------------------------------
# The two-way split was a lie for five cards, and CLAUDE.md had asked for this
# category twice: "the project needs a third category, PARTLY MODELLED, where
# A LOW SCORE MEANS NOTHING AND A HIGH SCORE MEANS SOMETHING."
#
# That asymmetry is the whole definition. These cards have a real, implemented
# component -- a body that attacks, a draw that happens -- and a missing one,
# and every missing component here UNDERSTATES. So:
#
#   a HIGH score is evidence. The card cleared the bar on the half that works,
#   and the missing half can only add to it.
#   a LOW score is NOT evidence, about the card or against it. It is the score
#   of a fraction of the card, and nobody knows what fraction.
#
# NEVER CUT ON A ROW IN THIS TABLE. Two swaps have already been withdrawn or
# refused on exactly this: a cut of Ashaya was staged and withdrawn (§0z), and
# Ka-Zar's best-scoring cut was Bane of Progress and was refused (§0z2).
#
# THE REASON IS REQUIRED, not decorative. A name in a set says "something is
# wrong here" and a reader cannot tell what; check_scripted_coverage() raises
# on an empty reason, and the reason is PRINTED in the table, so the row
# carries its own caveat to whoever reads it next.
PARTLY_MODELLED = {
    "karlov": {
        "Ginger, Queen of Sweets":
            "Two clauses of three are modelled and the third is a POLICY "
            "omission rather than a gap. MODELLED: the ETB crown "
            "(opponents.become_monarch), the Gingerbrute at each of the four "
            "upkeeps while you hold it, the token's HASTE, and its "
            "'{2}, {T}, Sacrifice: gain 3 life' -- which in this deck is a "
            "lifegain EVENT and not merely three life. NOT MODELLED, and "
            "named: (1) the Gingerbrute's '{1}: can't be blocked except by "
            "creatures with haste', because the opponents' blockers are an "
            "abstract count and there is no haste among them to check (§4) -- "
            "so an evasive attacker is scored as a ground one; and (2) "
            "Ginger's OWN '{2}, {T}, Sacrifice Ginger: you gain 6 life', "
            "deliberately unimplemented because a pilot who sacrifices her "
            "ends the token engine and the crown that feeds it, and a greedy "
            "sacrifice policy is the exact shape of the four conservatisms in "
            "CLAUDE.md's policy table. Both make the row a FLOOR. And the "
            "pod's three upkeeps are taken before pod_phase can take the "
            "crown, which makes the TOKEN COUNT a ceiling by at most two in "
            "the round it changes hands -- so the row is bounded on both "
            "sides and neither bound is tight.",
        "Bloodthirsty Conqueror":
            "Its text -- 'whenever an opponent loses life, you gain that much "
            "life' -- is WORD FOR WORD Exquisite Blood's, and this engine "
            "models that text as a COMBO DETECTOR rather than as a continuous "
            "trigger: it closes the loop with Sanguine Bond, Vito and "
            "Enduring Tenacity and does nothing the rest of the game. So the "
            "lifegain it would generate off every point the pod loses, all "
            "game, is UNMODELLED for this card exactly as it is for Exquisite "
            "Blood. Giving the newer card the general trigger and not the "
            "older one would have made a strictly-worse card measure strictly "
            "better, which is §0u's shape -- so both are understated by the "
            "same amount and both rows are FLOORS. The 5/5 flying deathtouch "
            "body IS modelled. §0z26.",
    },
    "rendmaw": {
        "Scrap Trawler":
            "Its own-death trigger is implemented (2026-09-13, §0z19) and "
            "returns a LESSER-mana-value artifact. Its SECOND clause -- "
            "'whenever ANOTHER ARTIFACT YOU CONTROL is put into a graveyard "
            "from the battlefield' -- is live only for artifact CREATURES, "
            "because `opponents.destroy` only ever kills permanents that are "
            "creatures right now: no noncreature artifact in this list (Sol "
            "Ring, the signets, Idol of Oblivion) is ever destroyed, and "
            "tokens never reach the graveyard. That is the pod model's limit "
            "(§4), not the card's, and it makes this row a FLOOR. §7.",
    },
    "azusa": {
        "Bane of Progress":
            "The wipe destroys only YOUR OWN artifacts and enchantments, "
            "because opponents own no permanent objects in this project "
            "(§4). Its negative score is a ONE-SIDED WIPE WITH THE SIDEDNESS "
            "REMOVED -- the cost with none of the benefit. §0z2.",
    },
    "tivit": {
        "Promise of Loyalty":
            "Implemented as a symmetric wipe (2026-09-12). The card is "
            "'each player puts a vow counter on a creature they control and "
            "SACRIFICES THE REST' -- everyone KEEPS ONE, and the model keeps "
            "none. It overstates in both directions at once, so a high score "
            "is still evidence and a low one is not. Sacrifice also gets "
            "around indestructible, which is why it is in "
            "WIPE_IGNORES_INDESTRUCTIBLE.",
        "Magister of Worth":
            "The CONDEMNATION half is implemented (2026-09-12): a symmetric "
            "wipe that spares only itself, conditional on the council vote. "
            "GRACE -- 'EACH PLAYER returns each creature card from their "
            "graveyard to the battlefield' -- is modelled for you and "
            "invisible for the pod, which has no graveyard (§4), so that mode "
            "understates. Condemnation also needs vote control to land at all "
            "under the adversarial `opp_vote_policy` default.",
    },
    "lorehold": {
        "Volcanic Vision":
            "The RECURSION half is implemented (2026-09-13, §0z19): it "
            "returns the largest instant or sorcery from the graveyard to "
            "hand and exiles itself. The DAMAGE half -- 'deals damage equal "
            "to that card's mana value to each creature your opponents "
            "control' -- is not, because opponents' boards are a blocker "
            "count with no toughness to compare a mana value against (§4). "
            "Both halves scale with the SAME choice of target, so the "
            "unmodelled half is largest exactly when the modelled one is: "
            "this row is a floor. §7.",
        "Borrowed Knowledge":
            "MODE 2 IS IMPLEMENTED as of 2026-09-11 ('discard your hand, then "
            "draw cards equal to the number of cards discarded this way'), "
            "including the discards, which is the half this deck's graveyard "
            "engines actually wanted. Mode 1 -- 'draw cards equal to the "
            "number of cards in TARGET OPPONENT'S HAND' -- is UNMODELABLE "
            "rather than unimplemented: this opponent model has no hand to "
            "count (§4). Mode 1 is the stronger half against a full grip, so "
            "this row is a FLOOR. §0f.",
    },
}
# ---------------------------------------------------------------------------
# A SYMMETRIC WIPE IS PARTLY MODELLED BY CONSTRUCTION (2026-09-12)
# ---------------------------------------------------------------------------
# `opponents.resolve_own_wipe` does two different-quality things in one call:
# it destroys YOUR real board through `destroy()`, honouring indestructible
# from the sweeper's own oracle text (§0z10) -- faithful -- and it sets each
# living opponent's `creatures` float to 0.0, which is the §4 abstraction with
# no card-level detail behind it. So the cost is modelled and the benefit is
# an estimate: a HIGH score is evidence, a LOW score is not. That is the
# definition of PARTLY MODELLED, and it is true of every symmetric wipe in
# every deck.
#
# THIS SET IS DERIVED FROM THE `wipe` TAG, NOT LISTED. Before this, the same
# card carried different labels in different decks -- Farewell was SCRIPTED in
# tivit and KNOWN_BLIND in lorehold and karlov, Damn was SCRIPTED in tivit and
# shilgengar and KNOWN_BLIND in karlov -- through the IDENTICAL shared code
# path. `check_scripted_coverage` could not see it, because it checks one deck
# at a time and each deck was internally consistent. §0q's rule is that the fix
# for a hand-maintained name set is derivation, so the category now follows the
# tag that makes the card a wipe in the first place.
#
# ONESIDED WIPES ARE EXCLUDED and stay KNOWN_BLIND: `spare_own=True` skips the
# half that is faithful, so a one-sided wipe is ALL abstraction and a high
# score means no more than a low one. Massacre Wurm (rendmaw) is the only one.
SYMMETRIC_WIPE_REASON = (
    "SYMMETRIC WIPE. Your half is faithful (destroyed through destroy(), "
    "honouring indestructible from this card's oracle text, §0z10); the "
    "opponents' half only zeroes an abstract creature count (§4). The COST is "
    "modelled and the BENEFIT is an estimate."
)

# Cards carrying `wipe` that are NOT symmetric wipes, with the reason each is
# judged faithfully modelled instead. Adding a name here is a CLAIM.
WIPE_NOT_SYMMETRIC = {
    # One kill per player off the biggest board, which is exactly what the
    # text says and exactly what the `creatures` float can carry -- it needs
    # no knowledge of WHICH creature dies. It is not a board wipe. §0z12.
    "Sadistic Shell Game",
}


def symmetric_wipes(deck):
    """The wipe-tagged cards in `deck` that are symmetric, hence PARTLY."""
    return {c.name for c in deck
            if "wipe" in getattr(c, "tags", frozenset())
            and "onesided" not in getattr(c, "tags", frozenset())
            and c.name not in WIPE_NOT_SYMMETRIC}


def partly_for(deck_name, deck):
    """PARTLY_MODELLED for `deck_name`, plus the derived symmetric wipes.

    A hand-written entry WINS over the derived one: Promise of Loyalty
    (tivit) and Magister of Worth already carry reasons naming the specific
    clause that is missing, which is strictly more useful than the generic
    wipe reason.
    """
    out = dict(PARTLY_MODELLED.get(deck_name, {}))
    for name in symmetric_wipes(deck):
        out.setdefault(name, SYMMETRIC_WIPE_REASON)
    return out


SCRIPTED_BY_DECK = {"lorehold": SCRIPTED_LOREHOLD, "rendmaw": SCRIPTED_RENDMAW,
                    "karlov": SCRIPTED_KARLOV, "tivit": SCRIPTED_TIVIT,
                    "shilgengar": SCRIPTED_SHILGENGAR, "azusa": SCRIPTED_AZUSA}


def blank_like(card, priority, keep_types=False):
    """A do-nothing replacement-level card of the same cost.

    `keep_types` (BLANK_KEEPS_TYPES in the environment, via `Run`) controls
    what the ablation actually measures, and for a typal-payoff commander the
    difference is large:

      True  - the blank copies the card's type line, so for Rendmaw an Artifact
              Creature blank still triggers the commander. This isolates the
              card's TEXT, with the type-line payoff cancelling out on both
              sides. Right question for "is this card's ability any good".
      False - the blank is a single-type body, so the swapped card's type line
              counts toward its score. Right question for "is this SLOT pulling
              its weight", which is the deckbuilding question.

    Default is False, because a card's type line is part of what it does.

    `priority` comes from `repl_priority()` -- read it before changing this.
    """
    if keep_types:
        types = card.types
    elif card.is_creature:
        types = frozenset({"Creature"})
    elif card.is_land:
        types = card.types
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0,
                priority=priority)


def columns(run, deck, commander, turns, lo, hi):
    """One metric column per `run.metrics`, over seeds [lo, hi).

    The seeds are `5000 + i` and nothing else reads the RNG, so this is a pure
    function of (deck, commander, turns, lo, hi) — which is what lets the
    baseline be shared and the cards be split across processes.
    """
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
    rows = [run.sim(deck, commander, cfg, 5000 + i) for i in range(lo, hi)]
    return {m: np.array([r[m] for r in rows], float) for m in run.metrics}


def paired(run, keep, drop):
    """{metric: (mean_diff, 95% CI half-width)} from two metric-column dicts."""
    cell = {}
    for m in run.metrics:
        d = keep[m] - drop[m]
        cell[m] = (d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d)))
    return cell


def blanked(run, deck, card_name):
    deck_b = list(deck)
    idx = next(i for i, c in enumerate(deck) if c.name == card_name)
    deck_b[idx] = blank_like(deck[idx], repl_priority(deck),
                             keep_types=run.blank_keeps_types)
    return deck_b


def ablate(run, deck, commander, card_name, baseline=None):
    """Returns {horizon: {metric: (mean_diff, ci)}}.

    `baseline` is {turns: metric columns for the UNMODIFIED deck}. Passing it
    is what saves half the work; omitting it measures the baseline here, which
    is what the old code did for every card in turn.
    """
    deck_b = blanked(run, deck, card_name)
    out = {}
    for turns in run.horizons:
        keep = (baseline[turns] if baseline is not None
                else columns(run, deck, commander, turns, 0, run.n))
        out[str(turns)] = paired(run, keep,
                                 columns(run, deck_b, commander, turns, 0, run.n))
    return out




# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
# Each worker builds the deck once and keeps the shared baseline, so a task is
# just a card name. build_pending() is deterministic, so every worker holds an
# equal deck and a card ablated in worker 7 scores exactly what it would have
# scored in the parent.

_W = {}


def _worker_init(run, baseline):
    # The run's parameters arrive as ONE OBJECT, the same one the parent
    # parsed, so a worker cannot measure a different deck or sample size than
    # the parent asked for. (Until 2026-09-17 they were module globals derived
    # from sys.argv at import and re-derived here; a worker only measures, so
    # the classification sets it used to rebind as well are not needed.)
    _W["run"] = run
    _W["deck"], _W["commander"] = build_pending(run.deck)
    _W["baseline"] = baseline


def _baseline_chunk(args):
    """A slice of the untouched deck's games, for one horizon."""
    turns, lo, hi = args
    return turns, lo, columns(_W["run"], _W["deck"], _W["commander"],
                              turns, lo, hi)


def _ablate_card(name):
    return name, ablate(_W["run"], _W["deck"], _W["commander"], name,
                        _W["baseline"])


def _chunks(n, parts):
    """Split range(n) into `parts` contiguous slices, largest first remainder."""
    step, extra = divmod(n, parts)
    lo, out = 0, []
    for k in range(parts):
        hi = lo + step + (1 if k < extra else 0)
        if hi > lo:
            out.append((lo, hi))
        lo = hi
    return out


def measure_baseline(run, pool, procs):
    """The untouched deck, once per horizon, split over the pool.

    Concatenating the slices reproduces the single-process array exactly —
    seeds 5000..5000+N-1 in order, one float64 per game — so every downstream
    mean and standard deviation is bit-identical.
    """
    slices = _chunks(run.n, procs)
    tasks = [(t, lo, hi) for t in run.horizons for lo, hi in slices]
    parts = {t: {} for t in run.horizons}
    runner = (pool.imap_unordered(_baseline_chunk, tasks) if pool
              else map(_baseline_chunk, tasks))
    for turns, lo, cols in runner:
        parts[turns][lo] = cols
    return {t: {m: np.concatenate([parts[t][lo][m] for lo, _ in slices])
                for m in run.metrics}
            for t in run.horizons}


def ablation_stream(run, todo, procs):
    """Yield (card, {horizon: {metric: (diff, ci)}}) in completion order.

    One pool measures the baseline; a second carries it to every worker in an
    initializer, so it crosses the process boundary once per worker rather than
    once per card. Breaking out of this generator closes both pools.
    """
    if procs == 1:
        _worker_init(run, None)
        _W["baseline"] = measure_baseline(run, None, 1)
        for name in todo:
            yield _ablate_card(name)
        return

    with Pool(procs, initializer=_worker_init, initargs=(run, None)) as scout:
        baseline = measure_baseline(run, scout, procs)
    with Pool(procs, initializer=_worker_init,
              initargs=(run, baseline)) as work:
        yield from work.imap_unordered(_ablate_card, todo)


# Cards deliberately left out of the SCRIPTED set: the engine does NOT
# implement their text and a low score is evidence about the model. Listing
# them explicitly is what lets the assertion below be strict.
KNOWN_BLIND = {
    "rendmaw": {
        "Assassin's Trophy",
        'Beast Within',
        'Biotransference',
        'Bow of Nylea',
        'Burnished Hart',
        "Eyeblight's Ending",
        'Filigree Familiar',
        'Gloomshrieker',
        'Hagra Mauling',
        'Haywire Mite',
        'Lignify',
        'Massacre Wurm',
        'Midnight Reaper',
        'Nameless Inversion',
        'Overwhelming Stampede',
        'Pygmy Kavu',
        'Reap',
        'Sakura-Tribe Elder',
        'Shigeki, Jukai Visionary',
        'Village Rites',
        'Whip of Erebos',
    },
    "lorehold": {
        'Approach of the Second Sun',
        'Bolt Bend',
        'Call Forth the Tempest',
        'Chaos Warp',
        "Dawn's Truce",
        "Dragon's Rage Channeler",
        'Enlightened Tutor',
        'Gamble',
        'Generous Gift',
        'Hexing Squelcher',
        'Improvisation Capstone',
        'Land Tax',
        'Path to Exile',
        'Perch Protection',
        'Pinnacle Monk',
        'Restoration Seminar',
        'Sejiri Shelter',
        'Storm Herd',
        'Swords to Plowshares',
    },
    "karlov": {
        'Anguished Unmaking',
        'Benevolent Offering',
        'Enlightened Tutor',
        'Fracture',
        'Lurrus of the Dream-Den',
        'Necropotence',
        'Path to Exile',
        'Phyrexian Reclamation',
        'Ranger of Eos',
        'Return to Dust',
        "Sensei's Divining Top",
        'Soulmender',
        'Sun Titan',
        'Swords to Plowshares',
        "Umezawa's Jitte",
    },
    # Explicitly blind, with the reason. check_scripted_coverage() raises if a
    # nonland card is in neither set, which is the guard against the 2026-09-04
    # labelling bug -- but nothing can CHECK that a classification is TRUE, so
    # these reasons are the record.
    "tivit": {
        # Opponents' boards are a blocker count, so nothing that removes a
        # permanent can be evaluated at all. This is the deepest limitation in the
        # project and it puts a third of this list here.
        "An Offer You Can't Refuse", "Path to Exile", "Swords to Plowshares",
        "Counterspell", "Dovin's Veto", "Muddle the Mixture", "Void Rend",
        "Trap the Trespassers", "Council's Judgment",
        # THE FIVE SWEEPERS LEFT THIS SET ON 2026-09-12. They were grouped
        # under "nothing that removes a permanent can be evaluated", which is
        # true of Path to Exile and was never quite true of a board wipe: a
        # wipe against an abstract creature COUNT is expressible — you set it
        # to zero — and it was only blind because `tivit.resolve` had no
        # `wipe` branch, so all five did nothing at all. They do now, so a
        # row that prints "not measured" would be the §0f error inverted: a
        # score that IS evidence, labelled as if it were not.
        # Rogue's Passage: "{4}, {T}: Target creature can't be blocked this
        # turn." UNIMPLEMENTED — and the thing it buys is already assumed.
        # Tivit's second trigger fires on `dmg > 0 and Tivit attacked`
        # (tivit.combat), which never asks whether TIVIT connected, so the
        # model already behaves as though the commander is unblockable. The
        # {4} activation is uncharged too, so both halves are missing and
        # they point opposite ways. Implementing it would be worth ~nothing
        # until combat tracks damage per attacker.
        "Rogue's Passage",
        # Ward {3}, and an attack tax, cannot be expressed against an opponent
        # model whose combat is a damage share rather than declared attackers.
        "Ghostly Prison", "Propaganda",
        # BLIND DESPITE HAVING ENGINE CODE -- the implementation is not the card:
        #   Expropriate      the extra turns land, but "gain control of a
        #                    permanent owned by the voter" needs opposing
        #                    permanents to steal. UNDERSTATES, badly.
        #   Torment of Hailfire  X is fixed at 6 and every opponent takes the life
        #                    branch, because they have neither a hand nor
        #                    permanents to give up. A CEILING, not an estimate.
        #   Rhystic Study    "unless that player pays {1}" is a social fact this
        #                    model cannot see; it is a flat draw rate.
        #   Capital Punishment / Bite of the Black Rose / Split Decision /
        #   Trial of a Time Lord / Vault 11  cast the vote correctly, so Grudge
        #                    Keeper and Model of Unity see them -- but their
        #                    EFFECTS (sacrifice, discard, counter, exile) all need
        #                    opposing permanents or hands.
        "Expropriate", "Torment of Hailfire", "Rhystic Study",
        "Capital Punishment", "Bite of the Black Rose", "Split Decision",
        "Trial of a Time Lord", "Vault 11: Voter's Dilemma",
    },
    "azusa": {
        # removal / land destruction aimed at opponents -- this project
        # tracks no opponent land or permanent objects at all, only an
        # aggregate creature count and a life total
        "Terastodon", "Beast Within", "Krosan Grip", "Crop Rotation",
        # (Nissa, Worldwaker was here, on the grounds that nothing in this
        # project tracks planeswalker loyalty. It does now -- see
        # PLANESWALKERS in edhmc/azusa.py -- so she is SCRIPTED as of
        # 2026-09-07.)
        # reads an OPPONENT drawing a card / a symmetric hand-refill effect,
        # neither of which this model tracks at that granularity
        "Mind's Eye", "Memory Jar",
        # "each land tapped for mana returns to hand" is a global replacement
        # on the shared mana model every engine uses; too easy to get subtly
        # wrong for one deck's build-around
        "Storm Cauldron",
        # modelled as the non-greedy "reveal 3, keep 1, pay no life" line,
        # which is close to a real blank in this engine
        "Sylvan Library",
        # symmetric mana-color-lock with no clear implementation path in an
        # abstracted mana model, and situational even in paper play
        "Hall of Gemstone",
        # a sac-for-value engine whose real value depends on WHEN to fire it
        # -- exactly the judgement-heavy timing this project is cautious
        # about automating (see "the greedy policy is the largest source of
        # model error")
        "Greater Good",
        # replaces every draw() call across the engine with a choice; too
        # much retrofitting for the many independent draw sources in this list
        "Abundance",
        # untaps a target creature once a turn for no modelled payoff
        "Quirion Ranger",
        # a plain land tutor to hand with no clear "best" target among 19
        # distinct utility lands
        "Sylvan Scrying",
        # a two-step fate-counter board wipe that would need per-permanent
        # tracking on BOTH sides of the table (it hits your own stuff too,
        # like Bane of Progress) -- more engineering than the card is worth
        "Oblivion Stone",
    },
    "shilgengar": {
        # removal, on a body or off one -- opponents' boards are a blocker
        # count, so none of it has a legal target. Same limitation as every
        # other deck in this project.
        "Angel of Despair", "Angel of Serenity", "Angel of the Ruins",
        "Path to Exile", "Swords to Plowshares", "Anguished Unmaking",
        "Generous Gift", "Despark", "Vindicate", "Mortify", "Utter End",
        # HALF implemented, and the half that works is NOT the obvious one.
        # Its Treasure-generation clause needs opponents' creatures to die as
        # discrete events, which nothing in this model tracks -- but its
        # ALTERNATE WIN (ten Treasures at upkeep) is live, and it fires off
        # Treasures other cards made. Measured 2026-09-07 at N=15,000 it is
        # +0.0063 +-0.0019 win rate, which is why it is the one card in this
        # deck's blind table that is not near zero. Traced: it resolves in
        # 12.1% of games, wins via the alt-win in 0.83% of ALL games, and in
        # 33 of 33 of those wins SMOTHERING TITHE WAS ON THE BATTLEFIELD.
        # THAT MAKES IT A KNOB RESULT: `shilgengar.upkeep` gives Tithe one
        # Treasure per living opponent per turn on the assumption that
        # opponents never pay the {2}. Make them pay sometimes and this line
        # gets much worse. Do not read the +0.0063 as a fact about the card.
        "Revel in Riches",
        # a damage-prevention/mill replacement effect whose interaction with
        # resolve_clocks (a game-loss check, not a damage event) is not
        # confidently representable -- see edhmc/shilgengar.py's docstring
        "Angel of Suffering",
        # landfall recursion + conditional haste unmodelled; a cheap enough
        # body that this is not worth the engine complexity
        "Bloodghast",
        # cost reduction scaling with its own counters, plus an attack
        # trigger -- a real engine piece, but not wired into
        # cost_after_reduction; a body only for now
        "Herald of War",
        # static opponent-behaviour restriction; the model does not track
        # per-opponent "cast a spell this turn" / "attacked this turn" at
        # that granularity
        "Angelic Arbiter",
        # ETB regrowth-the-turn's-deaths and persist, both unmodelled
        "Twilight Shepherd",
        # protection from a chosen card type -- unmodelled, a floor; body only
        "Serra's Emissary",
        # X-spell mass reanimation, largely redundant with Shilgengar's own
        # ultimate and Priest of Fell Rites / Sun Titan / Reya Dawnbringer;
        # played almost entirely as its land back face in this model
        "Agadeem's Awakening // Agadeem, the Undercrypt",
        # reactive protection spell shaped like Flawless Maneuver but for ONE
        # creature's death trigger -- no removal-in-response context to react
        # to here; played almost entirely as its land back face
        "Malakir Rebirth // Malakir Mire",
    },
}


def check_scripted_coverage(deck_name, deck, partly):
    """Every nonland card must be classified ON PURPOSE.

    `deck_name` picks the SCRIPTED_* and KNOWN_BLIND sets; `partly` is
    `partly_for(deck_name, deck)`, derived from the deck after it is built.

    The SCRIPTED_* sets are hand-maintained name sets and NOTHING used to check
    them against the deck. On 2026-09-04 five newly added cards were
    implemented in full and then printed under MODEL-BLIND, because adding a
    card to a deck is two edits and only one of them got made. The numbers were
    right; the label was wrong, and the label is the part that tells you whether
    a low score means anything.

    A name in SCRIPTED that is no longer in the deck is stale rather than
    dangerous, so it warns. A card in the deck that is in none of the three
    categories is the failure that actually bit, so it raises.

    THREE CATEGORIES SINCE 2026-09-10, and a card must be in EXACTLY ONE. A
    card in both SCRIPTED and PARTLY_MODELLED is the worse kind of ambiguity:
    it would print under MODEL-EVALUATED, where a low score is evidence, while
    something elsewhere claims it is not. Both halves of that are checked here.
    """
    # LANDS ARE EXEMPT, EXCEPT WHEN THEY CARRY A SCRIPT. A basic Forest needs
    # no classification and putting 36 of them in a name set would be noise.
    # But a `script` on a land IS a claim that the engine does something with
    # it, and that claim went unchecked: Rogue's Passage sat in tivit with
    # `script="rogues_passage"` that nothing dispatched and nothing
    # implemented, in NONE of the three categories, because this line skipped
    # it. §0q's shape in the checker itself — a check with a blind spot reads
    # like coverage and is not.
    SCRIPTED, PARTLY, DECK = SCRIPTED_BY_DECK[deck_name], partly, deck_name
    names = {c.name for c in deck if not c.is_land or c.script}
    stale = SCRIPTED - {c.name for c in deck}   # lands may be scripted too
    if stale:
        print(f"  NOTE: {len(stale)} name(s) in SCRIPTED_{DECK.upper()} are no "
              f"longer in the deck: {', '.join(sorted(stale))}", file=sys.stderr)
    overlap = (set(PARTLY) & SCRIPTED) | (set(PARTLY) & KNOWN_BLIND[DECK])
    if overlap:
        raise SystemExit(
            f"\n{len(overlap)} card(s) are in PARTLY_MODELLED AND in another "
            f"category, so their row would be printed under a heading that "
            f"contradicts it:\n"
            + "".join(f"    {n}\n" for n in sorted(overlap))
            + "A card is in exactly one of the three.\n"
            + "If the card is a SYMMETRIC WIPE it is put in PARTLY_MODELLED "
              "automatically by symmetric_wipes() and must not also be listed "
              "by hand -- remove the hand-written entry rather than the "
              "derivation. If you believe it is NOT a symmetric wipe, say so "
              "in WIPE_NOT_SYMMETRIC with the reason.")
    no_reason = [n for n, why in PARTLY.items() if not (why or "").strip()]
    if no_reason:
        raise SystemExit(
            f"\n{len(no_reason)} card(s) in PARTLY_MODELLED have no reason:\n"
            + "".join(f"    {n}\n" for n in sorted(no_reason))
            + "The reason is the category's whole content -- it is printed in "
              "the table so the row carries its own caveat. 'Partly modelled' "
              "with no statement of WHICH part is a label, not a finding.")
    stale_partly = set(PARTLY) - {c.name for c in deck}
    if stale_partly:
        print(f"  NOTE: {len(stale_partly)} name(s) in PARTLY_MODELLED are no "
              f"longer in the {DECK} deck: {', '.join(sorted(stale_partly))}",
              file=sys.stderr)
    unclassified = names - SCRIPTED - KNOWN_BLIND[DECK] - set(PARTLY)
    if unclassified:
        raise SystemExit(
            f"\n{len(unclassified)} card(s) in the {DECK} deck are in none of "
            f"SCRIPTED_{DECK.upper()}, PARTLY_MODELLED or KNOWN_BLIND:\n"
            + "".join(f"    {n}\n" for n in sorted(unclassified))
            + "Add each to SCRIPTED_ if the engine implements its text, to "
              "PARTLY_MODELLED (with the reason) if it implements part of it, "
              "or to KNOWN_BLIND if it does not. The split is a CLAIM, and it "
              "has to be made deliberately.")


def main(argv=None):
    run = parse_args(sys.argv[1:] if argv is None else argv)
    deck, commander = build_pending(run.deck)
    # Derived from the deck, so it exists only once the deck does — and it is
    # needed BEFORE check_scripted_coverage, which is what enforces the split.
    partly = partly_for(run.deck, deck)
    nonlands = [c.name for c in deck if not c.is_land]
    check_scripted_coverage(run.deck, deck, partly)
    CACHE = run.cache

    results = {}
    # A run that starts with NO cache file is a rebuild: its numbers are new
    # and its provenance stamp must be too (§0z29 -- a rebuild from an empty
    # cache once kept the previous stamp). A run that resumes keeps the stamp
    # of the run that created the cache, which is the fact being recorded.
    fresh = {"run": not os.path.exists(CACHE)}
    if os.path.exists(CACHE):
        results = json.load(open(CACHE))
    todo = [n for n in nonlands if n not in results]
    budget = float(os.environ.get("ABLATE_BUDGET", "240"))
    t0 = time.time()

    def save():
        # Written in DECK ORDER, not completion order, so the file is the same
        # bytes whichever worker finishes first and whether or not the run was
        # resumed. Names no longer in the deck are kept, at the end.
        ordered = {n: results[n] for n in nonlands if n in results}
        ordered.update({k: v for k, v in results.items() if k not in ordered})
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(ordered, open(CACHE, "w"))       # resumable across runs
        # STAMP WHAT THIS CACHE WAS BUILT AT, once, on creation. The manifest
        # used to record the fingerprint computed when the MANIFEST was
        # generated, which says nothing about what produced the numbers and
        # made regenerating the manifest a way to certify any cache at all.
        # Written here because here is the only place that knows the numbers
        # are new. Idempotent within a run: the first save of a rebuild
        # stamps fresh (superseding the deleted cache's record), every later
        # save and every resumed run is a no-op.
        try:
            from tools.cache_manifest import stamp_built
            stamp_built(os.path.basename(CACHE), run.deck, fresh=fresh["run"])
            fresh["run"] = False
        except Exception as exc:                      # never fail a measurement
            print(f"  WARNING: could not stamp cache provenance: {exc}",
                  file=sys.stderr)

    if todo:
        # NOT capped at len(todo): a resume with two cards left still wants
        # every core for the baseline, which is the same size either way.
        procs = max(1, int(os.environ.get("ABLATE_PROCS", "0")) or cpu_count() or 1)
        print(f"  {len(todo)} card(s) to measure on {procs} process(es)",
              file=sys.stderr)
        stream = ablation_stream(run, todo, procs)
        try:
            for name, cell in stream:
                results[name] = cell
                save()
                print(f"  done {len(results)}/{len(nonlands)}: {name}",
                      file=sys.stderr)
                if time.time() - t0 > budget:
                    break
        finally:
            stream.close()             # shuts the pools down on the way out
    remaining = [n for n in nonlands if n not in results]
    if remaining:
        print(f"\n{len(remaining)} cards still to do — rerun to resume.",
              file=sys.stderr)
        return
    sys.stdout.write(render_table(run, results, nonlands, partly))


def flips(res, hz) -> bool:
    """Does this card's DAMAGE effect genuinely reverse between horizons?

    Only when damage is SIGNIFICANT at every horizon and the signs disagree
    (§0z24). The override used to read `np.sign()` of the raw point estimate
    at each horizon, with no significance test, so a card whose damage was
    statistically zero -- a coin-flip sign -- was labelled FLIP whenever the
    two coins disagreed. 11 of 22 FLIP rows in the committed tables would have
    read `--` on their own merits: the strongest-sounding label on the rows
    with the least evidence, overriding the one label that says "unmeasured".

    A GATE, NOT A REMOVAL. Damn, Wrath of God, Promise of Loyalty and
    Mechanized Production are significant at both horizons with opposite
    signs -- a wipe costs damage early and repays it late -- and that is a
    real horizon effect, which is what this label is for.

    A function rather than an inline condition for §0z38's reason: a mutation
    has to be able to switch this rule off alone.
    """
    if len(hz) < 2:
        return False
    dmg = [res[h]["damage"] for h in hz]
    if not all(abs(m) > ci for m, ci in dmg):
        return False
    return len({np.sign(m) for m, _ci in dmg}) > 1


def signal(res, hz) -> str:
    """The row's signal. A score inside its own error bar is indistinguishable
    from a blank -- say so, rather than letting the sign imply a ranking."""
    last = hz[-1]
    d_sig = abs(res[last]["damage"][0]) > res[last]["damage"][1]
    w, wci = res[last]["won"]
    w_sig = abs(w) > wci
    sig = ("both" if d_sig and w_sig else
           "dmg" if d_sig else "win" if w_sig else "--")
    return "FLIP" if flips(res, hz) else sig


def render_table(run, results, nonlands, partly) -> str:
    """The table, as the text `main()` prints. A pure function of the cache
    contents and the classification sets, so a test can re-render a committed
    table from its committed cache and diff the two (§0z4's check, made
    repeatable) without running a game."""
    out = []

    def print(*parts, **_kw):           # shadows the builtin on purpose:
        out.append(" ".join(str(x) for x in parts) + "\n")   # same bytes

    HORIZONS, N, SCRIPTED, PARTLY = (run.horizons, run.n, run.scripted,
                                     partly)
    # The table did not used to say what N it was run at, so `ablation_tivit.txt`
    # at N=2000 looked exactly like the other three at N=6000 and CLAUDE.md had
    # to carry the warning in prose. A table should describe its own precision.
    floor = float(np.median([results[n][str(HORIZONS[-1])]["won"][1]
                             for n in nonlands]))
    print(f"""
Horizons: {HORIZONS}.  N = {N:,} paired games per card, seeds 5000..{5000 + N - 1}.
All figures are paired differences with 95% CIs.

NOISE FLOOR: the median win-rate CI half-width over this deck is +-{floor:.4f}.
Two cards closer together than that are not ranked by this table, however their
point estimates happen to fall. Halving it costs FOUR TIMES the games.

  signal = both : the card beats its error bars on damage AND win rate
           dmg  : significant on damage only
           win  : significant on win rate only
           --   : INSIDE its own error bars - indistinguishable from a blank.
                  Not a weak card, an unmeasured one. Do not rank these.
           FLIP : damage is SIGNIFICANT at every horizon and changes sign
                  between them -- a real horizon effect (a wipe costs
                  damage early and repays it late). Read win rate for
                  the verdict; the sign is the finding, not a ranking.

Win rate is the objective; damage is a proxy. Where they disagree, follow win
rate. And before cutting anything, check whether another card does the same job
- leave-one-out understates every member of an interchangeable group. Pass a
list of names to ablate() to score a package together.""")
    for title, group in (("MODEL-EVALUATED — a low score is evidence about the card",
                          [n for n in nonlands if n in SCRIPTED]),
                         ("PARTLY MODELLED — a HIGH score is evidence; a LOW score is NOT.\n"
                          "Every gap below UNDERSTATES, so these rows are floors. NEVER CUT ON ONE.",
                          [n for n in nonlands if n in PARTLY]),
                         ("MODEL-BLIND — a low score is evidence about the MODEL, not the card",
                          [n for n in nonlands
                           if n not in SCRIPTED and n not in PARTLY])):
        if not group:
            continue
        last = str(HORIZONS[-1])
        rows = sorted(group, key=lambda n: -results[n][last]["damage"][0])
        print(f"\n{'=' * 84}\n{title}\n{'=' * 84}")
        hz = [str(h) for h in HORIZONS]
        last = hz[-1]
        head = "".join(f"{'damage T' + h:>20}" for h in hz)
        print(f"{'card':<30}{head}{'win rate':>21}{'signal':>10}")
        for n in rows:
            cells = ""
            for h in hz:
                m, ci = results[n][h]["damage"]
                cells += f"{m:>+13.2f}+-{ci:<5.2f}"
            w, wci = results[n][last]["won"]
            sig = signal(results[n], hz)
            print(f"{n:<30}{cells}{w:>+14.4f}+-{wci:<5.4f}{sig:>10}")
            # THE REASON TRAVELS WITH THE ROW. A heading is read once and a
            # row is read on its own -- and the row is the thing somebody
            # copies into a cut list. Wrapped under its own card rather than
            # collected in a footnote for that reason.
            if n in PARTLY:
                for line in textwrap.wrap(PARTLY[n], 76):
                    print(f"      {line}")
    return "".join(out)


if __name__ == "__main__":
    main()
