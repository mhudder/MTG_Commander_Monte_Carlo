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

So the output is split into two groups. In the MODEL-EVALUATED group a low score
is evidence about the card. In the MODEL-BLIND group a low score is evidence
about the model, and says nothing at all about the card. Do not read the second
table as a cut list.

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
import time
from multiprocessing import Pool, cpu_count

import numpy as np

# Card names carry non-ASCII (Olórin's Searing Light). On Windows a redirected
# stdout defaults to the console codepage and writes cp1252, which makes the
# saved table invalid UTF-8. Force it.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

from edhmc.engine import Card, simulate as rendmaw_sim
from edhmc.pending import build_pending
from edhmc.lorehold import simulate as lh_sim
from edhmc.karlov import simulate as karlov_sim
from edhmc.tivit import simulate as tivit_sim
from edhmc.shilgengar import simulate as shilgengar_sim
from edhmc.azusa import simulate as azusa_sim
from edhmc.experiment import DEFAULT_CFG, BLANK_PRIORITY, repl_priority

DECK = sys.argv[1] if len(sys.argv) > 1 else "lorehold"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
# Report a RANGE of horizons rather than one. The cutoff turn is a free
# parameter created by the fact that opponents have no win condition, and it
# systematically favours slow, accumulating cards. A conclusion is only
# trustworthy if its SIGN and RANK survive the whole range.
HORIZONS = tuple(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 \
    else (20,)   # with the opponent clock, games end on their own around T12
# See blank_like(). Set True to isolate a card's text from its type line.
BLANK_KEEPS_TYPES = os.environ.get("BLANK_KEEPS_TYPES", "0") == "1"

SIM = {"lorehold": lh_sim, "rendmaw": rendmaw_sim,
       "karlov": karlov_sim, "tivit": tivit_sim,
       "shilgengar": shilgengar_sim, "azusa": azusa_sim}[DECK]
METRIC_SETS = {
    "lorehold": ("mv_cheated", "damage", "miracles_cast", "total_mv_cast", "won"),
    "rendmaw": ("damage", "cards_drawn", "tokens_made", "rendmaw_triggers", "won"),
    "karlov": ("damage", "lifegain_triggers", "final_life", "cards_drawn", "won"),
    # artifacts_made is this deck's mv_cheated: the proxy the engine is built
    # around. It is NOT the objective -- follow win rate where they disagree.
    "tivit": ("damage", "artifacts_made", "tivit_triggers", "votes_cast", "won"),
    "shilgengar": ("damage", "blood_made", "creatures_sacrificed",
                  "single_reanimations", "won"),
    "azusa": ("damage", "landfall_triggers", "lands_played",
             "tokens_made", "won"),
}

# Cards whose actual text the engine implements. Everything else is a body.
SCRIPTED_RENDMAW = {
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
    # protection the opponent model respects
    "Heroic Intervention",
    # static P/T setter (implemented in Game.power_of / toughness_of)
    "March of the World Ooze",
}

# Reviewed 2026-09-03. Monologue Tax, Hidden Retreat, Urabrask and Triumph of
# Saint Katherine left the deck in v16 and are gone from this list with them.
SCRIPTED_LOREHOLD = {
    # mana
    "Sol Ring", "Arcane Signet", "Boros Signet", "Talisman of Conviction",
    "Ruby Medallion", "Bender's Waterskin", "Victory Chimes",
    # top-of-library manipulation. Penance and Scroll Rack left the deck in
    # the 2026-09-05 staging.
    "Sensei's Divining Top", "Library of Leng",
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
    # card flow
    "Thrill of Possibility", "Faithless Looting", "Big Score",
    "Unexpected Windfall", "Borrowed Knowledge", "Reforge the Soul",
    "Apex of Power",
    # treasures / cost
    "Storm-Kiln Artist", "Smothering Tithe", "Hit the Mother Lode",
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
    "The Dawning Archaic", "Blasphemous Act",
    # BLIND, despite having engine code — the implementation is not the card:
    #   Artist's Talent - Level 2 granted free and instantly; Levels 1 and 3
    #                     do not exist, and Level 3 is a damage doubler
    #   Storm Herd      - X is cfg["storm_herd_x"]=40, not your life total
    #   Approach of the Second Sun - never gets its second cast, because the
    #                     card is not put seventh from the top
}

# Reviewed 2026-09-03 against the oracle audit. Membership here is a claim
# that the ENGINE implements the card's text, so a low score is evidence about
# the card. Cards whose text is still approximated belong in the blind group
# even when they are not literally absent from the engine.
SCRIPTED_KARLOV = {
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
    # wraths
    "Damn", "Wrath of God",
}

# Written 2026-09-07 with the deck (the least tuned of the six -- see
# azusa_v1.py). Membership is a claim that edhmc.azusa implements the card's
# text; X-spells are modelled at a fixed X (documented in azusa_v1.py).
#
# ASHAYA IS THE KNOWN EXCEPTION AND IT IS A REAL PROBLEM -- KNOWN_ISSUES §0z.
# Only its */* clause is implemented; "nontoken creatures you control are
# Forest lands" does not exist in the engine, so its row is NOT evidence about
# the card and its Quirion Ranger interaction is invisible. It stays here
# rather than moving to KNOWN_BLIND because its body is real and does attack,
# which is the case for a PARTLY MODELLED category this project does not yet
# have. Do not cut it on its ablation row.
#
# (An earlier version of this comment said the gap was "called out at its
# definition in edhmc/azusa.py". It was not, and never had been -- a pointer
# to a note that does not exist is worse than no note, because it stops the
# next reader looking. The call-out now exists, in DYNAMIC_PT_LANDS.)
SCRIPTED_AZUSA = {
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
    "Bane of Progress", "Ashaya, Soul of the Wild",
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

SCRIPTED = {"lorehold": SCRIPTED_LOREHOLD, "rendmaw": SCRIPTED_RENDMAW,
            "karlov": SCRIPTED_KARLOV, "tivit": SCRIPTED_TIVIT,
            "shilgengar": SCRIPTED_SHILGENGAR, "azusa": SCRIPTED_AZUSA}[DECK]
METRICS = METRIC_SETS[DECK]


def blank_like(card, priority):
    """A do-nothing replacement-level card of the same cost.

    BLANK_KEEPS_TYPES controls what the ablation actually measures, and for a
    typal-payoff commander the difference is large:

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
    if BLANK_KEEPS_TYPES:
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


def columns(deck, commander, turns, lo, hi):
    """One metric column per METRIC, over seeds [lo, hi).

    The seeds are `5000 + i` and nothing else reads the RNG, so this is a pure
    function of (deck, commander, turns, lo, hi) — which is what lets the
    baseline be shared and the cards be split across processes.
    """
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
    rows = [SIM(deck, commander, cfg, 5000 + i) for i in range(lo, hi)]
    return {m: np.array([r[m] for r in rows], float) for m in METRICS}


def paired(keep, drop):
    """{metric: (mean_diff, 95% CI half-width)} from two metric-column dicts."""
    cell = {}
    for m in METRICS:
        d = keep[m] - drop[m]
        cell[m] = (d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d)))
    return cell


def blanked(deck, card_name):
    deck_b = list(deck)
    idx = next(i for i, c in enumerate(deck) if c.name == card_name)
    deck_b[idx] = blank_like(deck[idx], repl_priority(deck))
    return deck_b


def ablate(deck, commander, card_name, baseline=None):
    """Returns {horizon: {metric: (mean_diff, ci)}}.

    `baseline` is {turns: metric columns for the UNMODIFIED deck}. Passing it
    is what saves half the work; omitting it measures the baseline here, which
    is what the old code did for every card in turn.
    """
    deck_b = blanked(deck, card_name)
    out = {}
    for turns in HORIZONS:
        keep = (baseline[turns] if baseline is not None
                else columns(deck, commander, turns, 0, N))
        out[str(turns)] = paired(keep, columns(deck_b, commander, turns, 0, N))
    return out


# The key MUST include every parameter that changes what a cached number MEANS.
# It used to key on deck and horizons only, so resuming a run at a different
# sample size silently merged two sample sizes into one table; hence `_n{N}`.
# `_medblank` / `_deadblank` is here for the same reason: the 2026-09-06 blank
# priority change moves every number, and the pre-change files carry NEITHER
# suffix, so they can no longer be picked up by a run that would misread them.
#
# The directory is part of the path and NOT part of the key: `results/caches/`
# is where every cache has lived since the 2026-09-09 reorganisation, and the
# name inside it is unchanged, so a cache from before the move is still picked
# up by a run that should pick it up. Moving these files was allowed to change
# where they are and forbidden to change what they mean.
CACHE = os.path.join(
    "results", "caches",
    f"ablation_cache_{DECK}_{'-'.join(map(str, HORIZONS))}_n{N}"
    f"{'_sametype' if BLANK_KEEPS_TYPES else ''}"
    f"{'_deadblank' if BLANK_PRIORITY == 'dead' else '_medblank'}.json")


# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
# Each worker builds the deck once and keeps the shared baseline, so a task is
# just a card name. build_pending() is deterministic, so every worker holds an
# equal deck and a card ablated in worker 7 scores exactly what it would have
# scored in the parent.

_W = {}


def _worker_init(deck_name, n, horizons, baseline):
    # DECK/N/HORIZONS are derived from sys.argv at import. multiprocessing's
    # spawn start method does forward sys.argv to the child, but this does not
    # rely on that: the run's parameters are passed explicitly and the module
    # globals are re-derived from them, so a worker cannot end up measuring a
    # different deck or sample size than the parent asked for.
    global DECK, N, HORIZONS, SIM, SCRIPTED, METRICS
    DECK, N, HORIZONS = deck_name, n, horizons
    SIM = {"lorehold": lh_sim, "rendmaw": rendmaw_sim,
           "karlov": karlov_sim, "tivit": tivit_sim,
           "shilgengar": shilgengar_sim, "azusa": azusa_sim}[DECK]
    SCRIPTED = {"lorehold": SCRIPTED_LOREHOLD, "rendmaw": SCRIPTED_RENDMAW,
                "karlov": SCRIPTED_KARLOV, "tivit": SCRIPTED_TIVIT,
                "shilgengar": SCRIPTED_SHILGENGAR,
                "azusa": SCRIPTED_AZUSA}[DECK]
    METRICS = METRIC_SETS[DECK]
    _W["deck"], _W["commander"] = build_pending(DECK)
    _W["baseline"] = baseline


def _baseline_chunk(args):
    """A slice of the untouched deck's games, for one horizon."""
    turns, lo, hi = args
    return turns, lo, columns(_W["deck"], _W["commander"], turns, lo, hi)


def _ablate_card(name):
    return name, ablate(_W["deck"], _W["commander"], name, _W["baseline"])


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


def measure_baseline(pool, procs):
    """The untouched deck, once per horizon, split over the pool.

    Concatenating the slices reproduces the single-process array exactly —
    seeds 5000..5000+N-1 in order, one float64 per game — so every downstream
    mean and standard deviation is bit-identical.
    """
    slices = _chunks(N, procs)
    tasks = [(t, lo, hi) for t in HORIZONS for lo, hi in slices]
    parts = {t: {} for t in HORIZONS}
    runner = (pool.imap_unordered(_baseline_chunk, tasks) if pool
              else map(_baseline_chunk, tasks))
    for turns, lo, cols in runner:
        parts[turns][lo] = cols
    return {t: {m: np.concatenate([parts[t][lo][m] for lo, _ in slices])
                for m in METRICS}
            for t in HORIZONS}


def ablation_stream(todo, procs):
    """Yield (card, {horizon: {metric: (diff, ci)}}) in completion order.

    One pool measures the baseline; a second carries it to every worker in an
    initializer, so it crosses the process boundary once per worker rather than
    once per card. Breaking out of this generator closes both pools.
    """
    if procs == 1:
        _worker_init(DECK, N, HORIZONS, None)
        _W["baseline"] = measure_baseline(None, 1)
        for name in todo:
            yield _ablate_card(name)
        return

    with Pool(procs, initializer=_worker_init,
              initargs=(DECK, N, HORIZONS, None)) as scout:
        baseline = measure_baseline(scout, procs)
    with Pool(procs, initializer=_worker_init,
              initargs=(DECK, N, HORIZONS, baseline)) as work:
        yield from work.imap_unordered(_ablate_card, todo)


# Cards deliberately left out of the SCRIPTED set: the engine does NOT
# implement their text and a low score is evidence about the model. Listing
# them explicitly is what lets the assertion below be strict.
KNOWN_BLIND = {
    "rendmaw": {
        "Ashnod's Altar",
        "Assassin's Trophy",
        'Beast Within',
        'Biotransference',
        'Bow of Nylea',
        'Burnished Hart',
        'Culling Ritual',
        'Deathreap Ritual',
        "Eyeblight's Ending",
        'Filigree Familiar',
        'Gloomshrieker',
        'Hagra Mauling',
        'Haywire Mite',
        'Junk Diver',
        'Lignify',
        'Massacre Wurm',
        'Midnight Reaper',
        'Myr Retriever',
        'Nameless Inversion',
        'Overwhelming Stampede',
        'Pygmy Kavu',
        'Reap',
        'Sakura-Tribe Elder',
        'Scrap Trawler',
        'Shigeki, Jukai Visionary',
        'Toxic Deluge',
        'Village Rites',
        'Whip of Erebos',
    },
    "lorehold": {
        'Approach of the Second Sun',
        "Artist's Talent",
        'Bolt Bend',
        'Call Forth the Tempest',
        'Chaos Warp',
        "Dawn's Truce",
        "Dragon's Rage Channeler",
        'Enlightened Tutor',
        'Farewell',
        'Gamble',
        'Generous Gift',
        'Goliath Daydreamer',
        'Hexing Squelcher',
        'Improvisation Capstone',
        'Invoke Calamity',
        'Land Tax',
        'Ondu Inversion',
        'Path to Exile',
        'Perch Protection',
        'Pinnacle Monk',
        'Promise of Loyalty',
        'Restoration Seminar',
        'Sejiri Shelter',
        'Storm Herd',
        'Swords to Plowshares',
        'Ultima',
        'Volcanic Vision',
    },
    "karlov": {
        'Anguished Unmaking',
        'Austere Command',
        'Benevolent Offering',
        'Damn',
        'Damnation',
        'Enlightened Tutor',
        'Farewell',
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
        'Toxic Deluge',
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
        "Damn", "Farewell", "Promise of Loyalty", "Sadistic Shell Game",
        "Trap the Trespassers", "Council's Judgment", "Magister of Worth",
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


def check_scripted_coverage(deck):
    """Every nonland card must be classified ON PURPOSE.

    The SCRIPTED_* sets are hand-maintained name sets and NOTHING used to check
    them against the deck. On 2026-09-04 five newly added cards were
    implemented in full and then printed under MODEL-BLIND, because adding a
    card to a deck is two edits and only one of them got made. The numbers were
    right; the label was wrong, and the label is the part that tells you whether
    a low score means anything.

    A name in SCRIPTED that is no longer in the deck is stale rather than
    dangerous, so it warns. A card in the deck that is in neither SCRIPTED nor
    KNOWN_BLIND is the failure that actually bit, so it raises.
    """
    names = {c.name for c in deck if not c.is_land}
    stale = SCRIPTED - {c.name for c in deck}   # lands may be scripted too
    if stale:
        print(f"  NOTE: {len(stale)} name(s) in SCRIPTED_{DECK.upper()} are no "
              f"longer in the deck: {', '.join(sorted(stale))}", file=sys.stderr)
    unclassified = names - SCRIPTED - KNOWN_BLIND[DECK]
    if unclassified:
        raise SystemExit(
            f"\n{len(unclassified)} card(s) in the {DECK} deck are in neither "
            f"SCRIPTED_{DECK.upper()} nor KNOWN_BLIND:\n"
            + "".join(f"    {n}\n" for n in sorted(unclassified))
            + "Add each to SCRIPTED_ if the engine implements its text, or to "
              "KNOWN_BLIND if it does not. The split between MODEL-EVALUATED "
              "and MODEL-BLIND is a CLAIM, and it has to be made deliberately.")


def main():
    deck, commander = build_pending(DECK)
    nonlands = [c.name for c in deck if not c.is_land]
    check_scripted_coverage(deck)

    results = {}
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

    if todo:
        # NOT capped at len(todo): a resume with two cards left still wants
        # every core for the baseline, which is the same size either way.
        procs = max(1, int(os.environ.get("ABLATE_PROCS", "0")) or cpu_count() or 1)
        print(f"  {len(todo)} card(s) to measure on {procs} process(es)",
              file=sys.stderr)
        stream = ablation_stream(todo, procs)
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

Win rate is the objective; damage is a proxy. Where they disagree, follow win
rate. And before cutting anything, check whether another card does the same job
- leave-one-out understates every member of an interchangeable group. Pass a
list of names to ablate() to score a package together.""")
    for title, group in (("MODEL-EVALUATED — a low score is evidence about the card",
                          [n for n in nonlands if n in SCRIPTED]),
                         ("MODEL-BLIND — a low score is evidence about the MODEL, not the card",
                          [n for n in nonlands if n not in SCRIPTED])):
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
            # A score inside its own error bar is indistinguishable from a
            # blank. Say so, rather than letting the sign imply a ranking.
            d_sig = abs(results[n][last]["damage"][0]) > results[n][last]["damage"][1]
            w_sig = abs(w) > wci
            sig = ("both" if d_sig and w_sig else
                   "dmg" if d_sig else "win" if w_sig else "--")
            if len(HORIZONS) > 1 and len({np.sign(results[n][h]["damage"][0])
                                          for h in hz}) > 1:
                sig = "FLIP"
            print(f"{n:<30}{cells}{w:>+14.4f}+-{wci:<5.4f}{sig:>10}")


if __name__ == "__main__":
    main()
