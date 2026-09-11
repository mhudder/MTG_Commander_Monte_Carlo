"""
edhmc.azusa — a landfall/ramp/big-creature engine for Azusa, Lost but Seeking.

    Azusa, Lost but Seeking  {2}{G}  1/2
      You may play two additional lands on each of your turns.

Verified against Scryfall 2026-09-07. Two spreadsheet mana values were wrong
and are corrected in `decks/azusa_v1.py`, not the sheet: Avenger of Zendikar
is {5}{G}{G} (MV 7, not 8) and Lotus Cobra is {1}{G} (MV 2, not 3).

THE CENTRAL MODELLING FACT
---------------------------
This deck's whole plan is to play more lands than one a turn and have that
matter twice: once for the mana, once for every LANDFALL trigger that land
sets off. `land_entered()` is the one hook every landfall payoff in the deck
runs through, the same way `on_creature_death` is the aristocrats hook in
`edhmc.shilgengar`. Extra land drops stack additively from several sources
(Azusa +2, Exploration +1, Oracle of Mul Daya +1, Wayward Swordtooth +1 once
Ascended) and are computed fresh each turn in `land_drops_for_turn()`.

FETCH LANDS ARE MODELLED AS TWO LANDFALL TRIGGERS, ON PURPOSE. Playing
Terramorphic Expanse / Windswept Heath / Wooded Foothills is a land ETB
(landfall #1); cracking it fetches a second land that also enters the
battlefield (landfall #2) and the fetch itself goes to the graveyard, which is
a THIRD event (Titania's "land you control is put into a graveyard from the
battlefield"). This is a large part of why real pilots of this archetype like
fetches, and it is exactly the kind of doubled trigger this project's
`Blood Artist paid 3x its drain` and `Elas il-Kor` corrections were about
getting right rather than approximating.

WHAT IS MODEL-BLIND AND WHY (see `KNOWN_BLIND["azusa"]` in `ablation.py` for
the complete, reasoned list)
-----------------------------------------------------------------------------
Removal-on-a-body and land destruction aimed at opponents (Terastodon, Beast
Within, Krosan Grip, Crop Rotation, Wasteland/Strip Mine/Ghost Quarter/Dust
Bowl/Tectonic Edge's sacrifice abilities) — opponents' individual lands and
permanents are not tracked as objects anywhere in this project, only as an
aggregate creature count and a life total. Effects that read an OPPONENT
drawing a card (Mind's Eye) or an opponent's individual graveyard/hand are
blind for the same reason.

LAND ANIMATION, WHICH USED TO BE THE HOLE IN THIS ENGINE
---------------------------------------------------------
The deck has four ways to turn its lands into creatures and until 2026-09-07
ONE of them was implemented as animation at all. Sylvan Awakening set a
turn-scoped flag; Rude Awakening was modelled as its untap mode only; and both
Nissas had no activated abilities, so a five-mana Planeswalker was a 0/0
permanent that did nothing whatsoever. `ablation_azusa.txt` scored Sylvan
Awakening +0.0017 and Rude Awakening +0.0019, both inside their own bars, and
the honest reading of those rows was "untested", not "disproved".

`self.animations` now holds the real continuous effects. Four things about
them are load-bearing and none of the four was true before:

  1. THE SET OF LANDS IS CAPTURED AT RESOLUTION. "All lands you control
     become 2/2 creatures" applies to the lands you control AS IT RESOLVES --
     a land played afterwards is not animated. In a deck that plays three
     lands a turn after its spells resolve, treating this as a static ability
     would have been a large silent overcount.
  2. DURATION IS PER-CARD AND IT DECIDES WHETHER THEY BLOCK. Sylvan Awakening
     lasts UNTIL YOUR NEXT TURN, so its lands are still creatures during the
     pod's round and count as blockers in `opponents.combat_share` -- under
     pod v3 that is a real defensive effect and it was not modelled at all.
     Rude Awakening's mode and Nissa's +1 last until END OF TURN and are gone
     before the pod acts.
  3. HASTE IS THE DIFFERENCE BETWEEN THE TWO AWAKENINGS. `make_permanent`
     now forces every land to enter `sick=True`, so a land played this turn
     cannot attack unless the effect grants haste -- and only Sylvan Awakening
     does. Every land call site used to pass `sick=False`, which was harmless
     while no land was ever a creature and is not any more.
  4. AN ANIMATED LAND THAT ATTACKS IS TAPPED, so it cannot also be tapped for
     mana in the postcombat main phase. `spend()` taps lands before creatures,
     so the attack gets whatever the main phase left over. That makes every
     animation number here a FLOOR: a pilot who wanted the alpha strike would
     hold the mana back instead of casting the spell.

INDESTRUCTIBLE AND REACH ARE CARRIED BUT CANNOT MATTER, and that is a fact
about the pod rather than a gap in it. `spot_removal` and `board_wipe` both
exclude lands, so nothing the pod does can kill an animated land; and this
engine never blocks with your creatures, so reach does nothing either. Sylvan
Awakening's indestructible clause is worth exactly zero here -- said out loud
so its row is not read as a measurement of the whole card.

PLANESWALKER LOYALTY, SCOPED TO THIS ENGINE
--------------------------------------------
Nothing else in this project tracks loyalty, and the note here used to say
that inventing the machinery "for one card" was not worth it. There are two
cards, both Nissas, and between them they are a repeatable land drop, a
ritual, two land animations and an ultimate that puts every basic Forest left
in the library onto the battlefield -- in a deck whose payoffs all read
"whenever a land enters". `PLANESWALKERS` holds starting loyalty,
`Permanent.counters` holds the current value (no new field on a dataclass
five other engines share), and `planeswalker_step()` activates at most one
ability per walker per turn at sorcery speed, which is the whole rule. It runs
twice a turn so a walker cast this turn still activates the turn it lands.

Two deliberate omissions, both of which make these two cards a FLOOR. Nissa,
Sage Animist's -2 (a 4/4 Ashaya token) is never taken, because the +1 is a
land drop and a card every turn in a 40-land deck and the -7 is the plan. And
NO OPPONENT EVER ATTACKS A PLANESWALKER, because the pod's combat is a float
and not a set of attackers, so loyalty here only ever goes up and the
ultimates arrive sooner than they would at a real table. The pod can still
answer a Nissa with spot removal, which is the only pressure on her, and it is
why `threat` on both cards matters.

SUBTYPES AND `Card.tags`
------------------------
`Card.types` is card types, not creature types — same limitation
`edhmc.shilgengar` documents. Nothing in this engine needs a creature-type
tag; Cavern of Souls's "choose a type" restriction is not modelled (see
below) so no card here cares what type another one is.
"""

from __future__ import annotations

import inspect
import random
import re

from edhmc.engine import (Board, Card, Permanent, can_pay, available_mana,
                          spend, devotion, ManaUnits, tap_reluctance,
                          hand_colour_demand)
from edhmc.decks._evasion import FOREST, HUMAN
from edhmc import opponents as OPP

TUTOR_TARGETS_MODULE = None   # set by decks/azusa_v1.py via register_pool()

# Cards whose value is realised PER LAND DROP, so they have to be on the
# battlefield BEFORE the drops are spent or they do nothing that turn. This is
# the set `main_phase(enablers_only=True)` deploys in the pre-land main phase.
#
# Three kinds are in here and it is worth knowing which is which:
#   - drop COUNT     Azusa, Exploration, Oracle of Mul Daya, Wayward Swordtooth
#   - drop ZONES     Courser / Augur / Oracle (top), Crucible / Excavator (yard)
#   - drop PAYOFFS   the landfall triggers themselves
#
# AVENGER OF ZENDIKAR IS A DELIBERATE JUDGEMENT CALL, not an obvious one. Its
# ETB makes a Plant per land you control, so playing lands FIRST makes more
# Plants -- but its landfall clause then pumps every Plant on each later drop,
# and with three drops a turn that is +3/+3 on the whole squad against one
# extra 0/1. Avenger first is much stronger, so it deploys first.
#
# THIS SET IS CHECKED, not merely asserted -- see check_land_enabler_coverage()
# at the bottom of this module, which runs at import. It was a bare
# hand-maintained name set when it was written, carrying the identical hazard
# `ablation.SCRIPTED_*` has been bitten by twice (KNOWN_ISSUES.md 0q): a
# landfall card added to the deck and not added here is deployed AFTER the
# land drops, contributes nothing on the turn it lands, and nothing anywhere
# says so -- it just quietly scores low.
# Cards whose printed P/T is */* equal to the number of lands you control.
# A NAME SET, so it is checked: check_dynamic_pt_coverage() at the bottom of
# this module raises at import if a card here is not in the deck or the
# candidate list, and every one of them is defined with power=0/toughness=0 so
# a missing entry would silently make it a 0/0 and die on arrival. That is the
# §0q rule -- a hand-maintained set is a claim, so derive or check it.
DYNAMIC_PT_LANDS = frozenset({
    # ASHAYA IS ONLY HALF IMPLEMENTED, and this is the call-out ablation.py
    # points at. KNOWN_ISSUES §0z. The card reads:
    #
    #   "Ashaya's power and toughness are each equal to the number of lands
    #    you control. NONTOKEN CREATURES YOU CONTROL ARE FOREST LANDS IN
    #    ADDITION TO THEIR OTHER TYPES."
    #
    # The second sentence does not exist in this engine. It is the half that
    # matters most: it turns the deck's creatures into lands, which is a
    # combo with Quirion Ranger (in the deck, and in KNOWN_BLIND) and changes
    # available_mana, land_drops_for_turn, playable_lands, land_entered,
    # land_died and Titania all at once -- which is also why it is not
    # implemented. **Ashaya's ablation row is therefore not evidence about
    # Ashaya, and it must not be cut on the strength of it.** A cut of it was
    # staged and withdrawn on 2026-09-10 for exactly this reason.
    "Ashaya, Soul of the Wild",
    "Greensleeves, Maro-Sorcerer",
    "Cultivator Colossus",
})

# Lands that SACRIFICE THEMSELVES to draw a card, and the exact cost of doing
# it: {name: (mana cost, does the cost include {T}, minimum lands required)}.
#
# Table-driven rather than four special cases, because the four differ only in
# those three numbers and the differences are the entire comparison between
# them. Note the two that matter most:
#
#   Scene of the Crime pays NO {T}, so it can be cracked the turn it enters
#   and while tapped -- which is what pays for it entering tapped.
#
#   Cryptic Caves is the only one with a printed land-count condition, and at
#   five it is met on essentially every turn this ability would be wanted.
#
# The activation POLICY -- when a pilot actually cracks one -- is shared and
# lives in activations(), because it is a judgement about the deck rather than
# about the card. See KNOWN_ISSUES §0z2/§0z3.
SAC_DRAW_LANDS = {
    "Cryptic Caves":       ({"gen": 1},          True,  5),
    "Horizon of Progress": ({"gen": 1},          True,  0),
    "Scene of the Crime":  ({"gen": 2},          False, 0),
    "The Hunter Maze":     ({"gen": 1, "G": 1},  True,  0),
}

LAND_ENABLERS = frozenset({
    "Exploration", "Oracle of Mul Daya", "Wayward Swordtooth",
    "Courser of Kruphix", "Augur of Autumn",
    "Crucible of Worlds", "Ramunap Excavator",
    "Lotus Cobra", "Horn of Greed", "Seer's Sundial",
    "Tireless Provisioner", "Tireless Tracker",
    "Scute Swarm", "Rampaging Baloths", "Avenger of Zendikar",
    "Titania, Protector of Argoth",
    # Reads a land ETB to transform herself -- see land_entered().
    "Nissa, Vastwood Seer // Nissa, Sage Animist",
    # 2026-09-10 draw batch. Ka-Zar is read by top_access(); the four
    # sac-draw lands are read by activations() via SAC_DRAW_LANDS.
    "Ka-Zar of the Savage Land",
    "Cryptic Caves",
    "Horizon of Progress",
    "Scene of the Crime",
    "The Hunter Maze",
    # --- 2026-09-09 candidates (decks/azusa_candidates.py). These are NOT in
    # the deck; they are here because check_land_enabler_coverage() scans the
    # four land methods for `self.has(...)` and raises on any name it finds
    # that is missing from this set. That check firing is the system working:
    # a land-relevant card the deck deploys AFTER its land drops scores low
    # for no stated reason, which is what this set exists to prevent.
    "Case of the Locked Hothouse",
    "Ancient Greenwarden",
    "Conduit of Worlds",
    "Walk-In Closet // Forgotten Cellar",
    "Greensleeves, Maro-Sorcerer",
    "Springheart Nantuko",
    "Cultivator Colossus",
    # --- 2026-09-10 third batch. Sapling Nursery is a landfall payoff and has
    # to be out BEFORE the drops like every other one; War Room and Castle
    # Garenbrig are lands themselves and are read by land_step() and by
    # activations(). Nissa, Who Shakes the World is here because her mana
    # doubler is what PAYS for the turn's casting, so deploying her after the
    # drops would waste the Forests played this turn.
    "Sapling Nursery",
    "Nissa, Who Shakes the World",
    "War Room",
    "Castle Garenbrig",
})

# Starting loyalty. `Permanent.counters` carries the current value from there.
# Checked against the deck at import by check_planeswalker_coverage(), because
# a hand-written name set is a claim and claims rot (KNOWN_ISSUES.md 0q) -- a
# Planeswalker added to this list and forgotten here would enter with zero
# loyalty and silently never do anything, which is precisely the failure this
# engine already had for both Nissas.
PLANESWALKERS = {
    "Nissa, Worldwaker": 3,
    "Nissa, Sage Animist": 3,          # the transformed back face, below
    "Nissa, Who Shakes the World": 5,  # 2026-09-10 candidate
}

# Cards whose cost is not the cost printed on them, and what reduces it. Both
# entries are the CARD rather than a discount effect, which is why they live
# here and are applied in cost_of() rather than in a rules-wide reducer:
#
#   The Great Henge   "{X} less, where X is the greatest power among creatures
#                     you control" -- {7}{G}{G} on a board with a 5/5 is
#                     {2}{G}{G}, and with Ashaya or Greensleeves out (both */*
#                     equal to your land count) it is {G}{G}. engine.py already
#                     models this for the Rendmaw list in cost_after_reduction;
#                     this is the same rule in this engine's own hook.
#   Sapling Nursery   "Affinity for Forests" -- {1} less per FOREST, which is a
#                     land SUBTYPE and therefore read from the generated
#                     decks/_evasion.py set, not from Card.types.
#
# A NAME SET, so it is checked: check_dynamic_cost_coverage() at the bottom of
# this module raises at import if a name here is not a real card, for the same
# reason DYNAMIC_PT_LANDS is checked -- a misspelling would silently leave the
# card at its printed nine or eight mana, which in both cases is a cost nobody
# ever pays and a card that never resolves.
DYNAMIC_COST = frozenset({"The Great Henge", "Sapling Nursery"})

# The back face of Nissa, Vastwood Seer. It is not in the deck list because it
# is never drawn, cast or shuffled -- it only ever arrives by transforming the
# front face, which is why it is built here rather than in decks/azusa_v1.py.
# `threat` is what makes the pod willing to spend removal on her.
NISSA_SAGE_ANIMIST = Card(
    name="Nissa, Sage Animist", types=frozenset({"Planeswalker"}),
    cost={"gen": 2, "G": 1}, priority=7.5, threat=7.5,
    tags=frozenset({"Legendary"}))


class AzusaGame:
    def __init__(self, deck, commander, cfg, seed):
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.library = list(deck)
        self.rng.shuffle(self.library)
        self.hand: list[Card] = []
        self.board: Board = Board()
        self.graveyard: list[Card] = []
        self.commander = commander
        self.commander_cast = False
        self.commander_tax = 0
        self.turn = 0
        self.land_drops = 1
        self.land_drops_used = 0
        self.spells_this_turn = 0
        self.ascended = False           # Wayward Swordtooth's city's blessing
        self.hothouse_solved = False    # Case of the Locked Hothouse
        self.springheart_host = None    # Permanent Springheart is bestowed on
        self.craterhoof_bonus = 0
        self.wildspeaker_bonus = 0      # Return of the Wildspeaker, non-Humans
        self.creature_mana: list[frozenset] = []   # Castle Garenbrig's six {G}
        self.animations: list[dict] = []   # live land-animation effects
        self.pw_used: set[int] = set()     # walkers already activated this turn
        self.legacy_animation = False      # the pre-2026-09-07 Sylvan flag

        # Each 2026-09-07 fix behind its own knob, defaulting to the corrected
        # behaviour, so the committed table can be reproduced and each claim
        # measured on its own. See diag_azusa_animation.py.
        cfg.setdefault("land_animation", "full")     # "full"|"legacy"|"off"
        cfg.setdefault("animated_lands_block", True)
        cfg.setdefault("rude_awakening_modes", True)
        cfg.setdefault("planeswalker_abilities", True)

        # 2026-09-08: ONE ATTACK AT THE WHOLE POD, not at one player, and the
        # damage metric bounded at what could actually have mattered. Lives in
        # experiment.DEFAULT_CFG and opponents.combat_damage now that all six
        # engines are wired to it -- this line only covers a cfg built by hand
        # without DEFAULT_CFG. Worth +0.0583 +-0.0038 (T10) / +0.0624 +-0.0040
        # (T20) on this deck. See run_combat_split.py and combat_split.txt.
        cfg.setdefault("combat_split", True)
        self.bonus_mana: list[frozenset] = []   # Lotus Cobra, this turn only

        # SHUFFLE EFFECTS MUST NOT BREAK COMMON RANDOM NUMBERS, and a cracked
        # fetch land shuffles. If a mid-game shuffle drew from `self.rng`,
        # deck A and deck B would consume different numbers of draws the
        # moment their boards diverged and every later draw would decorrelate
        # -- the exact failure `opponents.py`'s docstring is about, and this
        # project's whole method rests on not having it.
        #
        # So the seeds are PRE-ROLLED from a dedicated stream and indexed by
        # how many shuffles have happened, not by when they happened. The Nth
        # shuffle in both branches therefore applies the SAME index
        # permutation to two equal-length libraries, which is precisely the
        # property that makes the OPENING shuffle CRN-safe and keeps the
        # swapped card in the same slot.
        _shuf = random.Random(seed ^ 0x5F0F)
        self.shuffle_seeds = [_shuf.getrandbits(32) for _ in range(64)]
        self.shuffles_done = 0

        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = {
            "damage": 0.0, "combat_damage": 0.0,
            "cards_drawn": 0, "mana_spent": 0, "mana_floated": 0,
            "stranded_mv": 0, "turn_lethal": 99, "turn_won": 99,
            "removal_eaten": 0, "ae_removal_eaten": 0, "wipes_suffered": 0,
            "countered": 0, "protected": 0, "loss_route": 0, "win_route": 0,
            "cast_test_card": 0, "test_card_turn": 99,
            "test_card_answered": 0, "test_card_removed": 0,
            "test_card_countered": 0,
            "lands_played": 0, "landfall_triggers": 0, "fetches_cracked": 0,
            "library_shuffles": 0, "lands_from_hand": 0,
            "lands_from_library": 0, "lands_from_graveyard": 0,
            "reroll_fetches": 0,
            "scute_swarms_made": 0, "tokens_made": 0, "life_gained": 0,
            "single_reanimations": 0, "creatures_sacrificed": 0,
            "lands_animated": 0, "animated_attacks": 0,
            "animated_damage": 0.0, "animated_blocker_turns": 0,
            "pw_activations": 0, "pw_ultimates": 0, "nissa_transforms": 0,
            "entwines": 0,
            # 2026-09-09 candidate counters. REGISTERED HERE, not created on
            # first use: `self.m` is a plain dict, so `self.m[k] += 1` on an
            # unregistered key is a KeyError that only fires in the games
            # where the card actually resolves -- which for a 7-drop is a
            # minority of them, in a worker process, inside a harness that
            # would have reported it as a crash 20 minutes in.
            "colossus_lands": 0,        # lands put onto the battlefield by
                                        # Cultivator Colossus's ETB loop
            "springheart_copies": 0,    # token copies of the bestow host;
                                        # the Insect mode is in tokens_made
            "springheart_bestowed": 0,  # 1 if it ever found a host at all
            "springheart_etbs": 0,      # token copies whose ETB fired (item 16)
            "springheart_legend_dies": 0,  # ... and copies the legend rule
                                           # killed on arrival
            "caves_cracked": 0,         # Cryptic Caves sacrificed for a card
            "hothouse_solved_turn": 99, # 99 = never solved, matching the
                                        # turn_won / turn_lethal convention
            # 2026-09-10 third batch, registered here for the same reason the
            # 2026-09-09 ones are: a KeyError in a worker, in the minority of
            # games where an eight-drop resolves, reads as a crash 20 minutes
            # into a run.
            "henge_draws": 0,           # nontoken creatures that drew off The
                                        # Great Henge
            "henge_life": 0,            # life from tapping it at end of turn
            "war_room_draws": 0,
            "castle_activations": 0,    # Castle Garenbrig's six {G}, made
            "castle_mana_spent": 0,     # ... and actually spent on a creature
            "wildspeaker_draws": 0,     # cards actually drawn off the draw mode
            "wildspeaker_asked": 0,     # ... and what it asked for. The gap is
                                        # the library running out, and it is
                                        # the card's ceiling -- see §0z4.
            "wildspeaker_pumps": 0,     # times the pump mode was chosen
            "finale_from_yard": 0,      # Finale targets taken from the
                                        # graveyard rather than the library
        }
        self.damage_by_turn = []

    # -- helpers ---------------------------------------------------------

    def has(self, name):
        return name in self.board.names

    def count(self, name):
        return self.board.names.get(name, 0)

    # -- land animation ----------------------------------------------------

    def animate_lands(self, power, toughness, *, targets, haste=False,
                      trample=False, indestructible=False, reach=False,
                      through_pod_round=False, source=""):
        """Register one continuous animation effect.

        `targets` is the set of land permanents the effect applies to, CAPTURED
        BY THE CALLER AT RESOLUTION -- see point 1 of the module docstring. It
        is held by `id()` rather than by object because `Permanent` is an
        unfrozen dataclass and therefore unhashable, and because two Forests
        compare equal field-for-field.
        """
        if not targets or self.cfg.get("land_animation", "full") != "full":
            return
        if not self.cfg.get("animated_lands_block", True):
            # Isolates the "they block during the pod's round" half of Sylvan
            # Awakening from the "they attack" half, so the two can be
            # measured separately rather than as one lump.
            through_pod_round = False
        self.animations.append({
            "power": power, "toughness": toughness, "haste": haste,
            "trample": trample, "indestructible": indestructible,
            "reach": reach, "through_pod_round": through_pod_round,
            "expires_turn": self.turn, "source": source,
            "targets": {id(p) for p in targets},
        })
        self.m["lands_animated"] += len(targets)

    def animation_of(self, perm):
        """The animation covering this permanent, biggest first, or None.

        Layers are simplified to "the biggest body wins", which only ever
        matters if two animations overlap on one land in one turn -- Nissa's
        +1 on top of an Awakening. The real layer rules would apply the later
        timestamp; taking the larger is within a point of power of that and
        does not need a timestamp on every effect.
        """
        best = None
        for a in self.animations:
            if id(perm) in a["targets"] and (best is None
                                             or a["power"] > best["power"]):
                best = a
        return best

    def counts_as_creature(self, perm):
        """Is this permanent a creature RIGHT NOW?

        NOT named `is_creature_now`, which is what the question is actually
        called elsewhere: `karlov.is_creature_now(g, card)` is a MODULE-LEVEL
        function taking a Card, and `opponents.your_creatures` discovers this
        hook by name on the game object. Two things with one name and
        different signatures, one of them found by `getattr`, is a silent
        failure waiting for whoever turns karlov's into a method.

        The same question `karlov.is_creature_now` asks for Heliod and
        `engine.devotion` asks for Erebos, with the same reason for asking it
        at the call site rather than stamping it at ETB: the answer changes
        during the turn. `opponents.combat_share` reads this through
        `OPP.your_creatures`, which is how animated lands come to count as
        blockers.
        """
        return perm.card.is_creature or (perm.card.is_land
                                         and self.animation_of(perm) is not None)

    def expire_animations(self, end_of_turn=False):
        """`end_of_turn` drops the "until end of turn" effects, before the pod
        acts; otherwise this drops the "until your next turn" ones, which have
        survived the pod's round and are what makes Sylvan Awakening a
        defensive card as well as an offensive one."""
        if end_of_turn:
            self.animations = [a for a in self.animations
                               if a["through_pod_round"]]
        else:
            self.animations = [a for a in self.animations
                               if a["expires_turn"] >= self.turn]

    def _pump(self, perm):
        """Turn-scoped pump that applies to this permanent.

        Craterhoof's bonus is unconditional; Return of the Wildspeaker's is
        NON-HUMAN ONLY, which is the difference between the two and the reason
        this is not one counter. Both reset in take_turn.
        """
        bonus = self.craterhoof_bonus
        if self.wildspeaker_bonus and perm.card.name not in HUMAN:
            bonus += self.wildspeaker_bonus
        return bonus

    def power_of(self, perm):
        anim = self.animation_of(perm) if perm.card.is_land else None
        if anim is not None:
            # An animation SETS power and toughness; it does not add to them.
            return anim["power"] + perm.counters + self._pump(perm)
        base = perm.base_p if perm.is_token else perm.card.power
        p = base + perm.counters
        if perm.card.name in DYNAMIC_PT_LANDS:
            p = sum(1 for q in self.board if q.card.is_land)
        p += self._pump(perm)
        return p

    def toughness_of(self, perm):
        anim = self.animation_of(perm) if perm.card.is_land else None
        if anim is not None:
            return anim["toughness"] + perm.counters + self._pump(perm)
        base = perm.base_t if perm.is_token else perm.card.toughness
        t = base + perm.counters
        if perm.card.name in DYNAMIC_PT_LANDS:
            t = sum(1 for q in self.board if q.card.is_land)
        t += self._pump(perm)
        return t

    def draw(self, n=1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())
                self.m["cards_drawn"] += 1

    def opening_hand(self):
        for mulls in range(4):
            self.hand = [self.library.pop() for _ in range(7)]
            if 2 <= sum(1 for c in self.hand if c.is_land) <= 5:
                break
            self.library.extend(self.hand)
            self.rng.shuffle(self.library)
        for _ in range(mulls):
            if self.hand:
                worst = max(self.hand, key=lambda c: (not c.is_land, c.mv))
                self.hand.remove(worst)
                self.library.insert(0, worst)

    def deal_pod_damage(self, amount, each=True):
        if amount <= 0:
            return
        # BOUNDED: what is recorded is what could have mattered, not what was
        # asked for -- a drain for 50 into a player on 3 life is worth 3.
        n = max(1, len(OPP.living(self)))
        dealt = (OPP.damage_each(self, amount / n) if each
                 else OPP.damage_single(self, amount))
        self.m["damage"] += dealt
        if self.damage_by_turn:
            self.damage_by_turn[-1] += dealt

    def gain_life(self, amount):
        if amount <= 0:
            return
        self.your_life += amount
        self.m["life_gained"] += amount

    def make_permanent(self, card, sick=True, tapped=False, is_token=False,
                       counters=0):
        if card.is_land:
            # A LAND THAT ENTERS THIS TURN IS SUMMONING SICK the moment
            # something animates it, and cannot attack unless the effect
            # grants haste. Every land call site in this engine passed
            # sick=False, which was harmless while lands were never creatures
            # -- `available_mana` does not read `sick` for a land -- and is
            # load-bearing now. Forced here rather than fixed at eight call
            # sites, so a ninth cannot reintroduce it.
            sick = True
        if card.name in PLANESWALKERS and not counters:
            counters = PLANESWALKERS[card.name]     # loyalty
        perm = Permanent(card=card, sick=sick, tapped=tapped,
                         is_token=is_token, counters=counters,
                         base_p=card.power, base_t=card.toughness)
        self.board.append(perm)
        # THE GREAT HENGE: "Whenever a NONTOKEN creature you control enters,
        # put a +1/+1 counter on it and draw a card."
        #
        # Hooked HERE rather than in resolve() on purpose, and that is the
        # whole difference between this card being a five-drop that draws a few
        # cards and being this deck's card engine. A creature enters from six
        # zones in this engine -- cast from hand, Genesis Wave, Finale of
        # Devastation, Green Sun's Zenith, Chord of Calling, Woodland Bellower
        # -- and only the first of those goes through resolve(). Queued item 16
        # is the same observation from the other side: make_permanent does not
        # run the ETB dispatch resolve() does, so anything hooked only into
        # resolve() misses every tutored creature.
        #
        # Dryad Arbor is a nontoken LAND CREATURE and does trigger this, which
        # is correct and is the kind of card a by-hand reading misses.
        if (card.is_creature and not is_token
                and card.name != "The Great Henge" and self.has("The Great Henge")):
            perm.counters += 1
            self.draw(1)
            self.m["henge_draws"] += 1
        return perm

    def make_tokens(self, n, p, t, subtype=""):
        for _ in range(int(n)):
            tok = Card(name=f"{subtype or 'Token'} token",
                       types=frozenset({"Creature"}), power=p, toughness=t)
            self.make_permanent(tok, sick=True, is_token=True)
            self.m["tokens_made"] += 1

    def available_mana(self):
        # Returns a ManaUnits, like engine.available_mana: it carries the
        # owner of every unit so `spend` taps what `can_pay` actually chose
        # rather than a same-sized set picked by board order (§0z8). This
        # engine overrides the shared function for Temple of the False God,
        # Eye of Ugin and Nissa's Forest doubler, so it has to carry the
        # bookkeeping itself.
        units: list[frozenset] = []
        owners: list = []
        weights: list = []

        demand = hand_colour_demand(self)

        def add(src, n, owner):
            rank, power = tap_reluctance(self, owner)
            want = max((demand.get(c, 0) for c in src), default=0)
            units.extend([src] * n)
            owners.extend([owner] * n)
            weights.extend([(rank, want, power)] * n)

        n_lands = sum(1 for p in self.board if p.card.is_land)
        # NISSA, WHO SHAKES THE WORLD: "Whenever you tap a Forest for mana, add
        # an additional {G}." A STATIC ability, not a loyalty one, so it is
        # live from the moment she resolves and has nothing to do with
        # planeswalker_step(). In this list it doubles 20 basic Forests plus
        # Dryad Arbor -- the single largest mana effect any card in this
        # project applies, which is why it is worth the matching change in
        # engine.spend() that makes one Forest cover two units rather than
        # tapping two Forests to produce them.
        nissa = self.has("Nissa, Who Shakes the World")
        for p in self.board:
            if p.tapped:
                continue
            c = p.card
            if c.is_land:
                if c.name == "Temple of the False God":
                    add(frozenset({"C"}), 2 if n_lands >= 5 else 1, p)
                elif c.name == "Eye of Ugin":
                    pass   # no mana ability on the current oracle text
                else:
                    add(c.produces, 1, p)
                if nissa and c.name in FOREST:
                    add(frozenset({"G"}), 1, p)
            elif c.mana_ability:
                if c.is_creature and p.sick:
                    continue
                amt, colors = c.mana_ability
                add(colors, amt, p)
        # Lotus Cobra's and Tireless Provisioner's floating mana has NO owner:
        # nothing on the battlefield taps for it, so `spend` must not try.
        for src in self.bonus_mana:
            units.append(src)
            owners.append(None)
            weights.append((9, 0, 0))
        return ManaUnits(units, owners, weights,
                         legacy=self.cfg.get('mana_colour_legacy', False),
                         surplus=self.cfg.get('mana_surplus', True))

    # -- landfall --------------------------------------------------------

    def land_entered(self, card, played=False):
        """The one hook every landfall payoff in the deck runs through.

        `played` distinguishes an actual land drop (counts for Horn of
        Greed's "whenever a player plays a land") from a land that entered
        via search/fetch/tutor (Cultivate, a cracked fetch land, Titania's
        ETB) — none of those are "playing a land".
        """
        self.m["landfall_triggers"] += 1
        # ANCIENT GREENWARDEN: "if a land entering causes a triggered ability
        # of a permanent you control to trigger, that ability triggers an
        # ADDITIONAL time." So every payoff below fires twice, not once, and
        # that is the whole card -- modelling it as a static bonus would be
        # the "a doubled trigger, modelled as one" error this project has
        # already corrected for Blood Artist and Elas il-Kor.
        #
        # `landfall_triggers` is counted ONCE above on purpose: one land
        # entered, and the metric counts land-entry events. What doubles is
        # the ABILITIES, which the payoff counters below record. Counting the
        # event twice would make the mechanism counter disagree with the game.
        reps = 2 if self.has("Ancient Greenwarden") else 1
        for _ in range(reps):
            self._landfall_payoffs(card, played)

    def _landfall_payoffs(self, card, played=False):
        """The payoffs themselves, split out so Ancient Greenwarden can run
        them twice. Everything here is a triggered ability of a permanent you
        control, which is exactly the set Greenwarden doubles.

        EVERY PAYOFF SCALES ON `count`, NOT `has`. Until 2026-09-10 all of
        them except Scute Swarm and Nissa were keyed on the BOOLEAN `has()`,
        so a second Lotus Cobra or a second Tireless Provisioner did exactly
        nothing. That was invisible and harmless while the list was singleton
        and no effect copied a nontoken creature -- `make_tokens` names its
        tokens "Beast token" and so on, which never collide with a card name.

        It stopped being harmless the moment Springheart Nantuko's copy mode
        was implemented, because that mode's entire point is a SECOND COPY of
        a landfall payoff. A naive Springheart would have made the token and
        the token would have been inert, and the combo would have measured as
        zero for a reason that has nothing to do with the card. See
        KNOWN_ISSUES §0z1.

        Converting to `count` is behaviour-neutral for every list in this
        project today -- checked, not argued, with check_unchanged_decks.py.
        """
        if played:
            self.draw(self.count("Horn of Greed"))
        # Zabu, Ka-Zar's token: "Landfall -- whenever a land you control
        # enters, put a +1/+1 counter on Zabu." Legendary, so at most one, and
        # it is a TOKEN, so it grows rather than multiplying -- the opposite
        # shape to Scute Swarm and the reason Ka-Zar is a card-advantage card
        # with a body attached rather than a go-wide one.
        for p in self.board:
            if p.card.name == "Zabu":
                p.counters += 1
                break
        for _ in range(self.count("Avenger of Zendikar")):
            for p in self.board:
                if p.is_token and p.card.name == "Plant token":
                    p.counters += 1
        self.gain_life(self.count("Courser of Kruphix"))
        for _ in range(self.count("Lotus Cobra")):
            self.bonus_mana.append(frozenset({"G"}))
        self.make_tokens(self.count("Rampaging Baloths"), 4, 4, "Beast")
        self.make_tokens(self.count("Greensleeves, Maro-Sorcerer"), 3, 3,
                         "Badger")
        # Sapling Nursery: "Landfall -- whenever a land you control enters,
        # create a 3/4 green Treefolk creature token with reach." The reach is
        # carried nowhere because this engine never blocks with your creatures
        # (the module docstring says so for Sylvan Awakening); the 3/4 body is
        # the whole of what is modelled, and it is the Rampaging Baloths shape
        # one size down on power and one up on toughness.
        self.make_tokens(self.count("Sapling Nursery"), 3, 4, "Treefolk")
        for _ in range(self.count("Springheart Nantuko")):
            self.springheart_landfall()
        if self.has("Scute Swarm"):
            n_lands = sum(1 for p in self.board if p.card.is_land)
            n_swarms = self.count("Scute Swarm")
            for _ in range(n_swarms):
                if n_lands >= 6 and len(self.board) < 90:   # sane hard cap
                    tok = Card(name="Scute Swarm", types=frozenset({"Creature"}),
                              power=1, toughness=1, flying=False)
                    self.make_permanent(tok, sick=True, is_token=True)
                    self.m["scute_swarms_made"] += 1
                else:
                    self.make_tokens(1, 1, 1, "Insect")
        for _ in range(self.count("Tireless Provisioner")):
            # "create a Food or a Treasure token" -- modelled as the
            # Treasure mode (immediately useful mana), the same
            # single-more-useful-mode simplification the deck's other choose-
            # one lands effects make.
            self.bonus_mana.append(frozenset({"W", "U", "B", "R", "G", "C"}))
        self.clues = getattr(self, "clues", 0) + self.count("Tireless Tracker")
        if self.count("Nissa, Vastwood Seer // Nissa, Sage Animist"):
            # "Whenever a land you control enters, IF YOU CONTROL SEVEN OR
            # MORE LANDS, exile Nissa, then return her to the battlefield
            # transformed." The trigger did not exist: only her ETB Forest
            # search was modelled, so in a deck that reaches seven lands
            # around turn five she stayed a 2/2 for the rest of the game.
            if sum(1 for p in self.board if p.card.is_land) >= 7:
                self.transform_nissa()
        for _ in range(self.count("Seer's Sundial")):
            units = self.available_mana()
            pay = can_pay({"gen": 2}, units)
            if pay is not None:
                spend(self, pay, units)
                self.m["mana_spent"] += 2
                self.draw(1)

    # -- Springheart Nantuko ---------------------------------------------
    #
    # "Bestow {1}{G}. Enchanted creature gets +1/+1. Landfall -- whenever a
    #  land you control enters, you may pay {1}{G} if this permanent is
    #  attached to a creature you control. If you do, create a token that's a
    #  copy of that creature. If you didn't create a token this way, create a
    #  1/1 green Insect creature token."
    #
    # THE ATTACHMENT IS THE WHOLE CARD, and modelling it is why this was left
    # as a floor until 2026-09-10. `springheart_host` is a single Permanent
    # reference rather than a general Aura relation -- this is the only
    # attachment in the project, and inventing a framework for one card would
    # be the wrong trade. If a second bestow card ever arrives, generalise it
    # then.
    #
    # BESTOW COSTS EXACTLY WHAT THE CREATURE MODE COSTS ({1}{G} either way),
    # so choosing is free and a pilot bestows whenever a host is worth
    # copying. That is unusual and it is why this card is a build-around.

    # What a copy is WORTH per landfall, best first. A pilot picks the host
    # whose copy compounds, not the biggest body.
    #
    # RE-RANKED 2026-09-10 WHEN COPIES STARTED RE-TRIGGERING ETBs (queued item
    # 16), because the old order was a ranking of what a BARE BODY was worth
    # and that is no longer what a copy is. Two things changed shape:
    #
    #   * THE ETB CREATURES BECAME ELIGIBLE AT ALL. Craterhoof Behemoth,
    #     Woodland Bellower, Eternal Witness and Titania were not in this list
    #     -- the queued item names them as the copies a pilot most wants, and
    #     they were absent precisely BECAUSE their ETBs did nothing, which is
    #     a hand-maintained list encoding an engine limitation as a judgement
    #     about cards. That is the §0q failure wearing a different hat.
    #   * A LEGENDARY HOST'S COPY NOW DIES to the legend rule, so it is worth
    #     ITS ETB AND NOTHING ELSE. That reverses two entries: Titania stays,
    #     because her ETB returns a land from the graveyard and the land is
    #     the point; GREENSLEEVES IS REMOVED, because her value is a LANDFALL
    #     trigger and a copy that dies on arrival never sees a landfall. It
    #     used to rank fifth and was worth a permanent, illegal second
    #     Badger-maker.
    #
    # THE ORDER IS A POLICY, NOT A MEASUREMENT, and it is a fixed rank where a
    # real pilot chooses in context. `springheart_hosts` overrides it so the
    # ranking can be measured rather than argued.
    SPRINGHEART_HOSTS = (
        "Scute Swarm",                 # copies double every landfall
        "Craterhoof Behemoth",         # ETB pumps the WHOLE team, per landfall
        "Avenger of Zendikar",         # ETB: a Plant per land you control
        "Lotus Cobra",                 # +1 mana per landfall, compounding
        "Tireless Provisioner",        # +1 Treasure per landfall
        "Woodland Bellower",           # ETB tutors a 3-drop onto the field
        "Rampaging Baloths",           # a 4/4 per landfall, per copy
        "Eternal Witness",             # ETB returns your best card
        "Titania, Protector of Argoth",  # LEGENDARY: the copy dies, but its
                                         # ETB returns a land -> a landfall
        "Courser of Kruphix",
        "Tireless Tracker",
        # Greensleeves, Maro-Sorcerer was HERE and is deliberately gone: see
        # the legend-rule note above. Copying her is now worth zero.
    )

    def springheart_pick_host(self):
        """The creature to bestow onto, or None to enter as a creature."""
        hosts = tuple(self.cfg.get("springheart_hosts")
                      or self.SPRINGHEART_HOSTS)
        best, best_rank = None, len(hosts)
        for p in self.board:
            if not p.card.is_creature or p.card.name == "Springheart Nantuko":
                continue
            try:
                rank = hosts.index(p.card.name)
            except ValueError:
                continue
            if rank < best_rank:
                best, best_rank = p, rank
        return best

    def springheart_landfall(self):
        """One Springheart trigger.

        The copy is a TOKEN, so it is summoning sick and cannot tap for mana
        the turn it arrives -- which matters for a Lotus Cobra copy, whose
        landfall trigger fires anyway because a trigger is not a tap ability.
        """
        host = self.springheart_host
        if host is not None and host not in self.board:
            host = self.springheart_host = None     # it died; Springheart is
                                                    # a creature again
        if host is not None:
            units = self.available_mana()
            pay = can_pay({"gen": 1, "G": 1}, units)
            if pay is not None:
                spend(self, pay, units)
                self.m["mana_spent"] += 2
                tok = self.make_permanent(host.card, sick=True, is_token=True)
                self.m["springheart_copies"] += 1
                # THE COPY'S ETB FIRES. Queued item 16: `make_permanent` does
                # not run the ETB dispatch that `resolve` does, so a copy of
                # Avenger of Zendikar was a 5/5 with no Plants and a copy of
                # Craterhoof Behemoth pumped nothing -- which are exactly the
                # copies a pilot pays {1}{G} a land for. "Create a token that's
                # a copy of that creature" copies the printed card, and an ETB
                # trigger reads the battlefield it arrives on, so a copy made
                # on the fifth landfall of the turn sees five more lands than
                # the original did.
                #
                # THE LEGEND RULE then applies to the copy, and it is a real
                # cost rather than a technicality: a token copy of a legendary
                # creature is put into the graveyard immediately as a
                # state-based action, and you keep only the ETB. Titania is
                # worth copying FOR HER TRIGGER, so the copy is made, the land
                # comes back, and the body goes. Before this, copying
                # Greensleeves left a permanent second Badger-maker on the
                # battlefield, which is illegal and which `count()`-based
                # payoffs then doubled (the §0z1 change is what made that
                # visible); she is no longer an eligible host.
                #
                # TWO KNOBS, NOT ONE, because the two halves push in OPPOSITE
                # directions and a single switch would report their sum as if
                # it were one finding: the ETB adds value to every copy, the
                # legend rule takes a body off the legendary ones.
                # `copy_etb=False` with `copy_legend_rule=False` reproduces
                # every azusa number published before 2026-09-10.
                if self.cfg.get("copy_etb", True):
                    self.etb(host.card, tok, is_copy=True)
                    self.m["springheart_etbs"] += 1
                if (self.cfg.get("copy_legend_rule", True)
                        and "Legendary" in host.card.tags and tok in self.board):
                    self.board.remove(tok)
                    self.m["springheart_legend_dies"] += 1
                return
        self.make_tokens(1, 1, 1, "Insect")

    def transform_nissa(self):
        """Exile Nissa, Vastwood Seer and return her transformed.

        She comes back as a NEW OBJECT with fresh loyalty, which is why this
        is a swap rather than a retype -- and she is not summoning sick,
        because a Planeswalker never is: she can activate the same turn.
        """
        if not self.cfg.get("planeswalker_abilities", True):
            return
        perm = next((p for p in self.board
                     if p.card.name
                     == "Nissa, Vastwood Seer // Nissa, Sage Animist"), None)
        if perm is None:
            return
        self.board.remove(perm)
        self.make_permanent(NISSA_SAGE_ANIMIST, sick=False)
        self.m["nissa_transforms"] += 1

    def shuffle_library(self):
        """A shuffle from a card effect, drawn from the pre-rolled seeds so it
        cannot decorrelate the A/B pair. See __init__."""
        if self.shuffles_done >= len(self.shuffle_seeds):
            return                      # absurdly long game; stop shuffling
        seed = self.shuffle_seeds[self.shuffles_done]
        self.shuffles_done += 1
        random.Random(seed).shuffle(self.library)
        self.m["library_shuffles"] += 1

    def land_died(self, card):
        """A land you control was put into a graveyard from the battlefield
        (fetch cracks; nothing else in this list sacrifices a land)."""
        self.graveyard.append(card)
        if self.has("Titania, Protector of Argoth"):
            self.make_tokens(1, 5, 3, "Elemental")

    def crack_fetch(self, fetchland_card):
        """Terramorphic Expanse / Windswept Heath / Wooded Foothills. Always
        fetches a Forest -- this list has no other basic land type. Two
        landfall events: the fetch itself (already counted by the caller) and
        the Forest it finds. Terramorphic's fetched land enters TAPPED; the
        two true fetches (paying 1 life, unmodelled) do not."""
        self.board.remove(next(p for p in self.board
                               if p.card is fetchland_card))
        self.land_died(fetchland_card)
        forest = next((c for c in self.library if c.name == "Forest"), None)
        if forest is None:
            return
        self.library.remove(forest)
        enters_tapped = fetchland_card.name == "Terramorphic Expanse"
        self.make_permanent(forest, sick=False, tapped=enters_tapped)
        self.m["fetches_cracked"] += 1
        # "...put it onto the battlefield, THEN SHUFFLE." The shuffle is part
        # of the ability's resolution and finishes before the landfall trigger
        # goes on the stack, so it happens here rather than after
        # land_entered. It is also the whole point of replaying a fetch out of
        # the graveyard with Courser/Oracle out: a dead top card gets re-rolled
        # into a fresh look. See choose_land().
        self.shuffle_library()
        self.land_entered(forest, played=False)

    def land_drops_for_turn(self):
        n = 1
        if self.commander_cast:
            n += 2
        if self.has("Exploration"):
            n += 1
        if self.has("Oracle of Mul Daya"):
            n += 1
        if self.has("Wayward Swordtooth") and self.ascended:
            n += 1
        if self.has("Case of the Locked Hothouse"):
            n += 1          # "an additional land on each of your turns" --
                            # unconditional, NOT gated on being solved
        return n

    def playable_lands(self):
        """Everywhere this deck can play a land FROM, this turn: hand, the
        top of the library (Augur of Autumn / Courser of Kruphix / Oracle of
        Mul Daya), and the graveyard (Ramunap Excavator / Crucible of
        Worlds). Returns (card, zone) pairs."""
        out = [(c, "hand") for c in self.hand if c.is_land]
        if self.library and self.library[-1].is_land and self.top_access():
            out.append((self.library[-1], "library"))
        if (self.has("Ramunap Excavator") or self.has("Crucible of Worlds")
                or self.has("Conduit of Worlds")
                or self.has("Ancient Greenwarden")
                or self.has("Walk-In Closet // Forgotten Cellar")):
            out += [(c, "graveyard") for c in self.graveyard if c.is_land]
        return out

    def top_access(self):
        """Can you play a land off the top of your library right now?

        Case of the Locked Hothouse grants this only once SOLVED (seven or
        more lands), which is why it is not a bare `has` like the other three
        -- an unsolved Case is a land drop and nothing else. `solved` is
        maintained in `end_step`, where the card says to check it.
        """
        return (self.has("Augur of Autumn") or self.has("Courser of Kruphix")
                or self.has("Oracle of Mul Daya")
                or self.has("Ka-Zar of the Savage Land")
                or (self.has("Case of the Locked Hothouse")
                    and self.hothouse_solved))

    def choose_land(self, options):
        """Which land to play, and from where. The preference order is this
        deck's, not a generic one.

        1. A FETCH LAND FROM THE GRAVEYARD, when top-of-library access is live
           and the top card is NOT a land. Cracking it searches and then
           SHUFFLES, which re-rolls a dead top card into a fresh look -- and
           it costs no card at all, because the fetch is already in the yard.
           It is also the densest drop available: two landfall triggers (the
           fetch itself, then what it finds) plus a land-to-graveyard event
           for Titania, for one land drop. Needs multiple drops a turn to be
           worth it, which is exactly what this commander does.
        2. A LAND FROM THE TOP OF THE LIBRARY. Free: the hand land keeps, and
           playing off the top is the whole reason Courser / Augur / Oracle
           are card advantage rather than a scry.
        3. ANY OTHER LAND FROM THE GRAVEYARD -- also free relative to hand.
        4. A LAND FROM HAND, last, because it is the only one that costs a
           real card.

        Within a zone a fetch outranks a plain land: two landfall triggers
        instead of one.

        THE OLD RULE WAS `max(options, key=mv)`, AND IT WAS BACKWARDS. Every
        land has mana value 0, so the key was constant, `max` returned the
        first option, and `playable_lands` builds the hand first -- so the
        engine played hand lands until the hand was empty and only then
        touched the top of the library or the graveyard.
        """
        if not options:
            return None
        top_live = self.top_access()
        top_is_land = bool(self.library) and self.library[-1].is_land
        if top_live and not top_is_land:
            for c, z in options:
                if z == "graveyard" and c.script == "fetch":
                    self.m["reroll_fetches"] += 1
                    return c, z
        for want in ("library", "graveyard", "hand"):
            picks = [(c, z) for c, z in options if z == want]
            if picks:
                picks.sort(key=lambda it: it[0].script != "fetch")
                return picks[0]
        return None

    def land_step(self):
        self.land_drops = self.land_drops_for_turn()
        while self.land_drops_used < self.land_drops:
            options = self.playable_lands()
            choice = self.choose_land(options)
            if choice is None:
                break
            card, zone = choice
            self.m[f"lands_from_{zone}"] += 1
            if zone == "hand":
                self.hand.remove(card)
            elif zone == "library":
                self.library.pop()
            else:
                self.graveyard.remove(card)
            self.land_drops_used += 1
            self.m["lands_played"] += 1
            # A LAND IS DEPLOYED HERE AND NEVER GOES THROUGH resolve(), so the
            # watch counters have to be set here too or every land candidate
            # reports P(deploy) = 0.000 and test_card_resolved = 0 -- which
            # reads as "the card never arrived" when it arrived every game.
            # Found 2026-09-10 measuring War Room and Castle Garenbrig, the
            # first land candidates to go through candidates.py.
            if card.name in self.cfg.get("watch", ()):
                self.m["cast_test_card"] = 1
                self.m["test_card_turn"] = min(self.m["test_card_turn"],
                                               self.turn)
            # CASTLE GARENBRIG: "This land enters tapped unless you control a
            # Forest." Conditional, so `Card.tapped` cannot carry it -- the
            # module has tapped=False and the condition is applied here, which
            # is also why audit_cards.py's `unless` rule passes it rather than
            # flagging it as an untapped tapped-land. In a list with 21 Forests
            # the condition is met nearly always, and "nearly" is the point:
            # modelling it as unconditionally untapped would be a small free
            # gift, and as unconditionally tapped a large false cost.
            tapped = card.tapped
            if card.name == "Castle Garenbrig" and not self.forests():
                tapped = True
            perm = self.make_permanent(card, sick=False, tapped=tapped)
            self.land_entered(card, played=True)
            if card.script == "fetch":
                self.crack_fetch(card)
            # INTERLEAVE: play a land, THEN deploy anything it just paid for,
            # then play the next one. A one-shot enabler phase before any land
            # is played cannot cast a two-mana Lotus Cobra on turn two -- the
            # mana for it comes from the land drop itself. With multiple drops
            # a turn this is the difference between Cobra seeing none of them
            # and seeing all but the first. Enablers only, so this cannot turn
            # into the whole main phase running mid-land-step.
            if self.land_drops_used < self.land_drops:
                self.main_phase(enablers_only=True)

    # -- casting -----------------------------------------------------------

    def cost_of(self, card):
        cost = dict(card.cost)
        if card.name in ("Kozilek, Butcher of Truth", "Ulamog, the Infinite Gyre") \
                and self.has("Eye of Ugin"):
            cost["gen"] = max(0, cost.get("gen", 0) - 2)
        elif card.name == "The Great Henge":
            # "This spell costs {X} less to cast, where X is the greatest power
            # among creatures you control." The reduction applies to the
            # GENERIC part only -- {G}{G} is always paid, which is why the card
            # is never free however big the board gets. `counts_as_creature`
            # rather than `card.is_creature` so an animated land counts, as it
            # legally does.
            best = max([self.power_of(p) for p in self.board
                        if self.counts_as_creature(p)] or [0])
            cost["gen"] = max(0, cost.get("gen", 0) - best)
        elif card.name == "Sapling Nursery":
            # "Affinity for Forests (This spell costs {1} less to cast for each
            # Forest you control.)" FOREST is the generated subtype set: in
            # this list that is the 20 basic Forests and Dryad Arbor, and NOT
            # Cavern of Souls or Nykthos however green they are.
            cost["gen"] = max(0, cost.get("gen", 0) - self.forests())
        return cost

    def forests(self):
        """Forests you control. A SUBTYPE, so it is read from the generated
        set rather than from Card.types -- see decks/_evasion.py."""
        return sum(1 for p in self.board if p.card.name in FOREST)

    def resolve(self, card):
        if card.name in self.cfg.get("watch", ()):
            self.m["cast_test_card"] = 1
            self.m["test_card_turn"] = min(self.m["test_card_turn"], self.turn)

        if "wipe" in card.tags:
            OPP.resolve_own_wipe(self, spare_own="onesided" in card.tags)

        script = card.script
        if script == "draw3":
            self.draw(3)
        elif script == "regrowth1":
            if self.graveyard:
                best = max(self.graveyard, key=lambda c: c.mv)
                self.graveyard.remove(best)
                self.hand.append(best)
        elif script == "loam":
            pool = [c for c in self.graveyard if c.is_land][:3]
            for c in pool:
                self.graveyard.remove(c)
                self.hand.append(c)
        elif script in ("cultivate", "seek_horizon", "journey_of_discovery",
                        "realms_uncharted"):
            n = {"cultivate": 2, "seek_horizon": 3,
                "journey_of_discovery": 2, "realms_uncharted": 2}[script]
            to_battlefield = 1 if script == "cultivate" else 0
            for _ in range(to_battlefield):
                land = next((c for c in self.library if c.name == "Forest"), None)
                if land is None:
                    break
                self.library.remove(land)
                self.make_permanent(land, sick=False, tapped=True)
                self.land_entered(land, played=False)
            for _ in range(n - to_battlefield):
                land = next((c for c in self.library if c.name == "Forest"), None)
                if land is None:
                    break
                self.library.remove(land)
                self.hand.append(land)
        elif script == "green_sun":
            self.tutor_creature(3)
        elif script == "chord_of_calling":
            self.tutor_creature(4)
        elif script == "finale":
            # Finale of Devastation {X}{G}{G}: "Search your library AND/OR
            # GRAVEYARD for a creature card with mana value X or less and put
            # it onto the battlefield." Fixed X=6, the project's X-spell
            # convention (see wave()); the graveyard half is the real
            # difference from Green Sun's Zenith and is modelled. The X>=10
            # mode -- +X/+X and haste to the team -- is NOT: it needs twelve
            # mana, and pretending a fixed X of 6 sometimes reaches ten would
            # be inventing a number rather than approximating one.
            self.tutor_creature(6, include_graveyard=True)
        elif script == "return_wildspeaker":
            self.return_of_the_wildspeaker()
        elif script == "genesis_wave":
            self.wave(6, count=3)
        elif script == "animist":
            self.wave(4, lands_only=True)
        elif script == "nylea_land":
            for _ in range(3):
                land = next((c for c in self.library if c.name == "Forest"), None)
                if land is None:
                    break
                self.library.remove(land)
                self.hand.append(land)
        elif script == "rude_awakening":
            self.rude_awakening()
        elif script == "sylvan_awakening":
            # "UNTIL YOUR NEXT TURN, all lands you control become 2/2
            # Elemental creatures with reach, indestructible, and haste.
            # They're still lands." The duration is the whole difference
            # between this card and Rude Awakening's animate mode: these
            # lands are still creatures during the pod's round, so they
            # block. Haste is the other difference -- lands played this turn
            # are `sick` and only this card lets them attack anyway.
            self.animate_lands(2, 2, targets=self.your_lands(), haste=True,
                               reach=True, indestructible=True,
                               through_pod_round=True,
                               source="Sylvan Awakening")
            if self.cfg.get("land_animation") == "legacy":
                self.legacy_animation = True
        elif script == "momentous_fall":
            self.sac_for_value(momentous=True)

        if not card.is_permanent:
            self.graveyard.append(card)
            return

        perm = self.make_permanent(card, sick=not card.haste,
                                   tapped=bool(card.tapped))
        self.ascended = self.ascended or len(self.board) >= 10
        self.etb(card, perm)

    def etb(self, card, perm, is_copy=False):
        """Everything a permanent does AS IT ENTERS.

        SPLIT OUT OF resolve() ON 2026-09-10 to close queued item 16. It was
        inline, so the ONLY way to trigger an ETB was to cast the card from
        hand -- and `make_permanent` is reached from six other places
        (Springheart's token copy, Genesis Wave, Finale of Devastation, Green
        Sun's Zenith, Chord of Calling, Woodland Bellower, Titania, Nissa's
        ultimates). A copy of Avenger of Zendikar was a 5/5 with no Plants.

        `is_copy` marks a token copy of another permanent. It is passed to the
        two ETBs that must NOT repeat on one -- see below -- and is otherwise
        unused, because the whole point is that the rest of them do.
        """
        if card.name == "Avenger of Zendikar":
            n = sum(1 for p in self.board if p.card.is_land)
            self.make_tokens(n, 0, 1, "Plant")
        elif card.name == "Craterhoof Behemoth":
            n = sum(1 for p in self.board if p.card.is_creature)
            self.craterhoof_bonus += n
        elif card.name == "Eternal Witness":
            if self.graveyard:
                best = max(self.graveyard, key=lambda c: c.mv)
                self.graveyard.remove(best)
                self.hand.append(best)
        elif card.name == "Woodland Bellower":
            self.tutor_creature(3, nonlegendary_only=True)
        elif card.name == "Nissa, Vastwood Seer // Nissa, Sage Animist":
            land = next((c for c in self.library if c.name == "Forest"), None)
            if land is not None:
                self.library.remove(land)
                self.hand.append(land)
        elif card.name == "Titania, Protector of Argoth":
            pool = [c for c in self.graveyard if c.is_land]
            if pool:
                best = max(pool, key=lambda c: c.mv)
                self.graveyard.remove(best)
                self.make_permanent(best, sick=False)
                self.land_entered(best, played=False)
        elif card.name == "Bane of Progress":
            # ETB destroys ALL artifacts/enchantments -- including yours.
            # Opponents' are not tracked as objects, so only your own side is
            # represented; see the module docstring.
            victims = [p for p in self.board
                      if p is not perm and not p.card.is_land
                      and ("Artifact" in p.card.types or "Enchantment" in p.card.types)]
            for v in victims:
                self.board.remove(v)
                if not v.is_token:
                    self.graveyard.append(v.card)
            perm.counters += len(victims)
        elif card.name == "Ka-Zar of the Savage Land":
            # "When Ka-Zar enters, create Zabu, a legendary 2/2 green Cat
            # creature token with 'Landfall -- whenever a land you control
            # enters, put a +1/+1 counter on Zabu.'"
            zabu = Card(name="Zabu", types=frozenset({"Creature"}),
                        power=2, toughness=2)
            self.make_permanent(zabu, sick=True, is_token=True)
            self.m["tokens_made"] += 1
        elif card.name == "Springheart Nantuko" and not is_copy:
            # BESTOW OR NOT, decided as it resolves. Both modes cost {1}{G},
            # so there is no mana question -- only whether a host worth
            # copying is on the battlefield. If none is, it stays a 1/1
            # creature and makes Insects, which is the mode this engine
            # modelled exclusively until 2026-09-10.
            #
            # `not is_copy`: bestow is an alternative COST paid as the spell is
            # cast, so a token copy of a bestowed Springheart is a plain 1/1
            # creature and re-running the bestow decision would let a copy
            # re-attach. springheart_pick_host() already refuses Springheart
            # as a host, so this cannot arise today; it is guarded because the
            # next copy effect will not know that.
            host = self.springheart_pick_host()
            if host is not None:
                self.springheart_host = host
                host.counters += 1              # "enchanted creature gets +1/+1"
                self.m["springheart_bestowed"] = 1
        elif card.name == "Cultivator Colossus":
            # "You may put a land card from your hand onto the battlefield
            # TAPPED. If you do, draw a card AND REPEAT THIS PROCESS." A real
            # loop, not a fixed number: each draw can find another land, so it
            # empties the hand of lands and replaces every one with a card.
            #
            # It does NOT consume land drops -- "put onto the battlefield" is
            # not playing a land -- so land_entered is called with
            # played=False, which is also what denies it Horn of Greed. That
            # distinction is the one this hook already exists to make.
            #
            # The cap is a runaway guard, not a rule: with Scute Swarm out,
            # each land doubles the board, and the loop is bounded by the hand
            # in reality but by nothing in a model that can draw more lands.
            for _ in range(40):
                land = next((c for c in self.hand if c.is_land), None)
                if land is None:
                    break
                self.hand.remove(land)
                self.make_permanent(land, tapped=True)
                self.m["colossus_lands"] += 1
                self.land_entered(land, played=False)
                self.draw(1)
        elif card.name == "Yavimaya Elder":
            pass   # its DEATH trigger is in on_creature_death

    def your_lands(self):
        return [p for p in self.board if p.card.is_land]

    def rude_awakening(self):
        """Rude Awakening {4}{G}, entwine {2}{G}. Verified 2026-09-07.

            Choose one --
            * Untap all lands you control.
            * Until end of turn, lands you control become 2/2 creatures that
              are still lands.
            Entwine {2}{G} (Choose both if you pay the entwine cost.)

        THE ANIMATE MODE AND THE ENTWINE DID NOT EXIST. The engine untapped
        the lands and stopped, which is the mode a pilot takes when they are
        ramping and the WRONG one when they are killing somebody -- and
        entwining is how this card actually ends games: untap every land and
        then swing with all of them, which is why the untap half is printed on
        an animation card in the first place.

        Entwine is paid here rather than through `Card.alt_costs` because the
        cost model is one-cost-per-card (KNOWN_ISSUES.md 1b) and `alt_costs`
        is a REPLACEMENT cost, not an additional one. This is an extra
        payment made on resolution, the same shape as Seer's Sundial's {2}.
        """
        if not self.cfg.get("rude_awakening_modes", True):
            for p in self.board:                  # the pre-2026-09-07 engine:
                if p.card.is_land:                # untap, and nothing else
                    p.tapped = False
            return
        units = self.available_mana()
        pay = can_pay({"gen": 2, "G": 1}, units)
        both = pay is not None
        if both:
            spend(self, pay, units)
            self.m["mana_spent"] += 3
            self.m["entwines"] += 1

        # Which single mode, when the entwine is unaffordable. Untapping is
        # only worth anything if there is something left to spend it on, so
        # the question "does this turn on a spell in hand" is the whole
        # decision and it is computable rather than a judgement call.
        tapped_lands = [p for p in self.board if p.card.is_land and p.tapped]
        # Never choose a mode the configuration cannot deliver: with
        # `land_animation` off or "legacy", `animate_lands` is a no-op, and
        # picking the animate mode would make the card do NOTHING AT ALL
        # rather than fall back to the untap it used to have.
        can_animate = self.cfg.get("land_animation", "full") == "full"
        animate = can_animate and (both
                                   or not self._untap_would_help(tapped_lands))
        if both or not animate:
            for p in self.board:
                if p.card.is_land:
                    p.tapped = False
        if animate:
            # No haste and no indestructible on this mode, and it is gone by
            # the pod's round -- so unlike Sylvan Awakening these lands never
            # block and the ones played this turn cannot attack.
            self.animate_lands(2, 2, targets=self.your_lands(),
                               source="Rude Awakening")

    def _untap_would_help(self, cands):
        """Would untapping these lands turn on a spell we cannot cast now?

        This is the whole untap-versus-animate decision, and it is arithmetic
        rather than a judgement call: mana you cannot spend is worth nothing,
        so untap when it buys a spell and animate when it does not.
        """
        if not cands:
            return False
        units = self.available_mana()
        after = units + [p.card.produces for p in cands]
        for c in self.hand:
            if c.is_land:
                continue
            cost = self.cost_of(c)
            if can_pay(cost, units) is None and can_pay(cost, after) is not None:
                return True
        return False

    def on_creature_death(self, n=1, perm=None):
        for _ in range(n):
            if perm is not None and perm.card.name == "Yavimaya Elder":
                for _ in range(2):
                    land = next((c for c in self.library
                                if c.name == "Forest"), None)
                    if land is None:
                        break
                    self.library.remove(land)
                    self.hand.append(land)

    def tutor_creature(self, max_mv, nonlegendary_only=False,
                       include_graveyard=False):
        """Search for a creature of mana value <= max_mv, onto the battlefield.

        `include_graveyard` is Finale of Devastation's "library AND/OR
        GRAVEYARD". The graveyard is searched FIRST when it holds an equally
        big target, because a card taken from the yard does not thin the
        library -- and in this deck the yard fills with the creatures the pod
        has already killed, which are the expensive ones.
        """
        pool = [(c, "library") for c in self.library if c.is_creature
                and c.mv <= max_mv
                and (not nonlegendary_only or "Legendary" not in c.tags)]
        if include_graveyard:
            pool += [(c, "graveyard") for c in self.graveyard if c.is_creature
                     and c.mv <= max_mv
                     and (not nonlegendary_only or "Legendary" not in c.tags)]
        if not pool:
            return
        best, zone = max(pool, key=lambda it: (it[0].mv, it[1] == "graveyard"))
        if zone == "graveyard":
            self.graveyard.remove(best)
            self.m["finale_from_yard"] += 1
        else:
            self.library.remove(best)
        perm = self.make_permanent(best, sick=True)
        self.ascended = self.ascended or len(self.board) >= 10
        return perm

    def wave(self, x, count=None, lands_only=False):
        """Genesis Wave / Animist's Awakening, both fixed-X approximations —
        see the module docstring for why X-spells here use a hardcoded X
        rather than a dynamic one, the same convention `Debt to the
        Deathless` and `Torment of Hailfire` already use elsewhere."""
        if lands_only:
            put = 0
            for _ in range(x):
                land = next((c for c in self.library if c.is_land), None)
                if land is None:
                    break
                self.library.remove(land)
                self.make_permanent(land, sick=False, tapped=True)
                self.land_entered(land, played=False)
                put += 1
            return
        pool = sorted([c for c in self.library
                      if c.is_permanent and c.mv <= x],
                     key=lambda c: -c.mv)[:count or 99]
        # TAKE THEM OUT OF THE LIBRARY FIRST, THEN resolve any ETB. Genesis
        # Wave reveals the top X and puts the permanents onto the battlefield
        # as one action, so the cards have all left the library before a
        # single trigger goes on the stack -- and doing it in the other order
        # is not just a rules nicety, it CRASHED: `land_entered` can fire
        # Seer's Sundial, which draws, which pops the library, which can take
        # a card this loop still holds a reference to and was about to
        # `remove()`. Found 2026-09-07 by the first full-size ablation run.
        for c in pool:
            self.library.remove(c)
        for c in pool:
            self.make_permanent(c, sick=not c.haste, tapped=bool(c.tapped))
            if c.is_land:
                self.land_entered(c, played=False)

    def nonhuman_creatures(self):
        """The creatures Return of the Wildspeaker can see.

        HUMAN is the generated subtype set (decks/_evasion.py). Every token
        this deck makes -- Beast, Badger, Plant, Insect, Treefolk, Scute Swarm
        copies -- is non-Human, and so is every animated land, so the six
        Humans in the list (Augur, Azusa herself, Eternal Witness, Tireless
        Tracker, Yavimaya Elder, the staged Ka-Zar) are the whole of what this
        card cannot touch.
        """
        return [p for p in self.board if self.counts_as_creature(p)
                and p.card.name not in HUMAN]

    def return_of_the_wildspeaker(self):
        """Return of the Wildspeaker {4}{G}, Instant. Verified 2026-09-10.

            Choose one --
            * Draw cards equal to the greatest power among non-Human creatures
              you control.
            * Non-Human creatures you control get +3/+3 until end of turn.

        THE MODE CHOICE IS A POLICY, NOT AN OPTIMISER, and it is said out loud
        here because the card's whole evaluation turns on it. A pilot draws
        unless the pump actually finishes someone:

            PUMP when +3/+3 across the attackers would kill a player this turn
            who would otherwise survive -- that is the only thing the pump does
            that the draw cannot do later.
            DRAW otherwise, because this deck's one measured weakness is cards
            (2.77 land drops granted a turn, 1.33 used), and a 5/5 in a deck of
            them draws five.

        `wildspeaker_mode` forces the hand ("draw" / "pump") so the two halves
        can be measured apart, the same way every 2026-09-07 animation fix got
        its own knob.

        A FLOOR IN ONE RESPECT, and it is worth stating: this is an INSTANT and
        this engine has no instant speed. A real pilot holds it up, draws off
        the biggest creature AFTER blockers are declared, or pumps in response
        to a wipe. Modelled as a sorcery, cast in the main phase, which is
        strictly the worst of the three.
        """
        forced = self.cfg.get("wildspeaker_mode", "auto")
        mine = self.nonhuman_creatures()
        if not mine:
            return
        draw_n = max(self.power_of(p) for p in mine)

        pump = False
        if forced == "pump":
            pump = True
        elif forced == "auto":
            # Would the pump kill somebody the unpumped attack would not? The
            # attackers are the ones combat() will send: untapped, not sick.
            attackers = [p for p in mine if not p.tapped and not p.sick]
            extra = 3 * len(attackers)
            alive = OPP.living(self)
            if alive and attackers:
                # The pod splits one attack across defenders, so the honest
                # question is whether the extra damage covers the smallest
                # life total still standing that the raw attack cannot.
                raw = sum(self.power_of(p) for p in attackers)
                weakest = min(o.life for o in alive)
                pump = raw < weakest <= raw + extra
        if pump:
            self.wildspeaker_bonus += 3
            self.m["wildspeaker_pumps"] += 1
        else:
            # COUNT WHAT WAS DRAWN, NOT WHAT WAS ASKED FOR. Measured at
            # N=4,000 this asks for 30.0 cards a resolution and receives 8.2,
            # because the greatest power on a Craterhoof-pumped Scute Swarm
            # board runs into the hundreds and the library is 99 cards deep.
            # Recording draw_n here would put a number in the diagnostics that
            # is nearly four times the number of cards that actually moved.
            #
            # THE GAP IS ALSO THE CARD'S CEILING, and it is worth stating
            # where the counter is: `draw()` stops at an empty library and
            # NOTHING IN THIS PROJECT LOSES TO DECKING. A pilot who really
            # drew 30 off this would have to win that turn. See §0z4.
            before = self.m["cards_drawn"]
            self.draw(draw_n)
            self.m["wildspeaker_draws"] += self.m["cards_drawn"] - before
            self.m["wildspeaker_asked"] += draw_n

    def sac_for_value(self, momentous=False):
        fodder = [p for p in self.board if p.is_token and p.card.is_creature
                 and not p.sick]
        if not fodder:
            return
        victim = min(fodder, key=self.power_of)
        p_, t_ = self.power_of(victim), self.toughness_of(victim)
        self.board.remove(victim)
        self.m["creatures_sacrificed"] += 1
        if momentous:
            self.draw(p_)
            self.gain_life(t_)
        self.on_creature_death(1, victim)

    def castle_step(self, units):
        """Castle Garenbrig: "{2}{G}{G}, {T}: Add six {G}. Spend this mana only
        to cast creature spells or activate abilities of creatures."

        Verified 2026-09-10 -- it is SIX mana for four, not the four-for-two it
        is often remembered as. Net +2, restricted.

        THE RESTRICTION IS WHY THIS IS NOT JUST +2 MANA, and it is the whole
        reason the ability is modelled as a separate pool rather than as
        `bonus_mana`. Six {G} that can only cast creatures is worth a great deal
        in a list holding Kozilek, Ulamog, Terastodon and Craterhoof, and
        nothing at all on a turn whose play is Genesis Wave or a land tutor.

        FIRED ONLY WHEN IT UNLOCKS SOMETHING. A pilot does not activate it for
        the sake of activating it: the check is whether some creature in hand is
        uncastable on the real mana and castable on what is left after paying
        the {2}{G}{G} plus the six. That is conservative in one known way -- it
        never activates to cast a creature it could already afford in order to
        hold the real mana open for something else -- and this engine has no
        instant-speed play to hold it open for, so the cost of that is zero.

        Returns True if it fired, so the caller knows to re-read the mana.
        """
        if self.creature_mana or not self.has("Castle Garenbrig"):
            return False
        castle = next((p for p in self.board
                       if p.card.name == "Castle Garenbrig" and not p.tapped),
                      None)
        if castle is None:
            return False
        cost = {"gen": 2, "G": 2}
        pay = can_pay(cost, units)
        if pay is None:
            return False
        used = set(pay)
        left = [u for i, u in enumerate(units) if i not in used]
        extra = [frozenset({"G"})] * 6
        unlocks = any(
            c.is_creature and can_pay(self.cost_of(c), units) is None
            and can_pay(self.cost_of(c), left + extra) is not None
            for c in self.hand)
        if not unlocks:
            return False
        spend(self, pay, units)
        castle.tapped = True
        self.creature_mana = list(extra)
        self.m["castle_activations"] += 1
        return True

    # -- turn loop -----------------------------------------------------------

    def main_phase(self, enablers_only=False):
        """`enablers_only` is the PRE-LAND main phase: deploy only what pays
        off per land drop (LAND_ENABLERS, and the commander above all), so
        that this turn's drops actually see them.

        Before this existed, `land_step` ran once before any spell resolved,
        which meant nothing cast on turn T could affect turn T's land drops at
        all. Measured cost of that, over 3,000 games: on the turn AZUSA
        HERSELF resolved the deck got 1.08 land drops instead of 3; Lotus
        Cobra was too late to see a drop in 51% of the games it resolved in;
        and 12.8% of all turns ended with an unused drop while a land was
        sitting somewhere legal to play it from. See diag_azusa_lands.py.
        """
        while True:
            units = self.available_mana()
            if not self.commander_cast:
                ccost = dict(self.commander.cost)
                ccost["gen"] = ccost.get("gen", 0) + self.commander_tax
                pay = can_pay(ccost, units)
                if pay is not None:
                    spend(self, pay, units)
                    self.m["mana_spent"] += sum(ccost.values())
                    idx = self.spells_this_turn
                    self.spells_this_turn += 1
                    if OPP.countered(self, self.commander, idx):
                        self.m["countered"] += 1
                        self.commander_tax += 2
                        continue
                    self.make_permanent(self.commander, sick=True)
                    self.commander_cast = True
                    self.ascended = self.ascended or len(self.board) >= 10
                    continue

            # CASTLE GARENBRIG, if it unlocks something, BEFORE the options are
            # built -- the six {G} are only worth making when a creature is
            # waiting on them.
            if self.castle_step(units):
                units = self.available_mana()
            n_real = len(units)

            options = []
            for c in self.hand:
                if c.is_land:
                    continue
                if enablers_only and c.name not in LAND_ENABLERS:
                    continue
                if "wipe" in c.tags and not OPP.should_cast_own_wipe(self):
                    continue
                # "Spend this mana only to cast CREATURE SPELLS or activate
                # abilities of creatures", so the restricted pool is offered to
                # creatures and to nothing else. It sits AFTER the real units,
                # which is what lets the payment below tell the two apart.
                pool = units + self.creature_mana if c.is_creature else units
                pay = can_pay(self.cost_of(c), pool)
                if pay is not None:
                    options.append((c, pay))
            if not enablers_only and self.library and (self.has("Augur of Autumn")):
                top = self.library[-1]
                if top.is_creature and self._coven():
                    pay = can_pay(self.cost_of(top), units)
                    if pay is not None:
                        options.append((top, pay))
            if not options:
                break
            card, pay = max(options, key=lambda it: (it[0].priority, it[0].mv))
            # Only the REAL units tap a permanent. Anything the payment took
            # from Castle Garenbrig's pool is mana that has already been paid
            # for -- charging it to the lands as well would tap four of them to
            # spend mana the Castle made, which would make the ability a cost
            # with no benefit.
            real = [i for i in pay if i < n_real]
            from_castle = len(pay) - len(real)
            spend(self, real, units)
            if from_castle:
                del self.creature_mana[:from_castle]
                self.m["castle_mana_spent"] += from_castle
            self.m["mana_spent"] += len(pay)
            from_top = bool(self.library) and card is self.library[-1]
            if from_top:
                self.library.pop()
            else:
                self.hand.remove(card)
            idx = self.spells_this_turn
            self.spells_this_turn += 1
            if OPP.countered(self, card, idx):
                self.m["countered"] += 1
                self.graveyard.append(card)
                if card.name in self.cfg.get("watch", ()):
                    self.m["test_card_answered"] += 1
                    self.m["test_card_countered"] += 1
                continue
            self.resolve(card)

    def _coven(self):
        # "If you control three or more creatures with different powers" --
        # an animated land IS a creature with a power while the animation
        # lasts, so it counts, same as it does for the blocker count.
        mine = [p for p in self.board if self.counts_as_creature(p)]
        powers = {self.power_of(p) for p in mine}
        return len(mine) >= 3 and len(powers) >= 3

    def planeswalker_step(self):
        """At most one loyalty ability per walker per turn, sorcery speed.

        Called twice a turn — once after the land step so the untap modes can
        feed the main phase, once after it so a Nissa cast THIS turn still
        activates the turn she lands, which is the actual rule. `pw_used`
        makes the second call a no-op for a walker the first one already used.
        """
        if not self.cfg.get("planeswalker_abilities", True):
            return
        for perm in list(self.board):
            if perm.card.name not in PLANESWALKERS or id(perm) in self.pw_used:
                continue
            self.pw_used.add(id(perm))
            self.m["pw_activations"] += 1
            if perm.card.name == "Nissa, Worldwaker":
                self._nissa_worldwaker(perm)
            elif perm.card.name == "Nissa, Who Shakes the World":
                self._nissa_who_shakes(perm)
            else:
                self._nissa_sage_animist(perm)

    def _nissa_worldwaker(self, perm):
        """Nissa, Worldwaker {3}{G}{G}, loyalty 3. Verified 2026-09-07.

            +1: Target land you control becomes a 4/4 Elemental creature with
                trample. It's still a land.
            +1: Untap up to four target Forests.
            -7: Search your library for any number of basic land cards, put
                them onto the battlefield, then shuffle. Those lands become
                4/4 Elemental creatures with trample.

        The ultimate is a pile of LANDS ENTERING in a deck built entirely on
        landfall, which is why it is worth implementing even though it needs
        four turns of ticking up to reach.
        """
        if perm.counters >= 7:
            perm.counters -= 7
            basics = [c for c in self.library if c.name == "Forest"]
            # EVERY CARD LEAVES THE LIBRARY BEFORE ANY OF THEM ENTERS. A
            # landfall trigger can draw (Horn of Greed) or tutor, and popping
            # the library out from under this loop is the exact crash that
            # took down Genesis Wave on 2026-09-07.
            for c in basics:
                self.library.remove(c)
            got = []
            for c in basics:
                got.append(self.make_permanent(c, sick=True))
                self.land_entered(c, played=False)
            self.shuffle_library()
            self.animate_lands(4, 4, targets=got, trample=True,
                               source="Nissa, Worldwaker -7")
            self.m["pw_ultimates"] += 1
            return

        perm.counters += 1
        forests = [p for p in self.board
                   if p.card.name == "Forest" and p.tapped][:4]
        if self._untap_would_help(forests):
            for p in forests:
                p.tapped = False
            return
        # Otherwise animate the best land that could actually attack: an
        # untapped one that has been here since the turn began, and that some
        # other effect has not already animated into something bigger.
        target = next((p for p in self.board
                       if p.card.is_land and not p.tapped and not p.sick
                       and self.animation_of(p) is None), None)
        if target is not None:
            self.animate_lands(4, 4, targets=[target], trample=True,
                               source="Nissa, Worldwaker +1")

    def _nissa_who_shakes(self, perm):
        """Nissa, Who Shakes the World {3}{G}{G}, loyalty 5. Verified against
        Scryfall 2026-09-10.

            Whenever you tap a Forest for mana, add an additional {G}.
            +1: Put three +1/+1 counters on up to one target noncreature land
                you control. Untap it. It becomes a 0/0 Elemental creature with
                vigilance and haste that's still a land.
            -8: You get an emblem with "Lands you control have indestructible."
                Search your library for any number of Forest cards, put them
                onto the battlefield tapped, then shuffle.

        THE STATIC ABILITY IS NOT HERE. It is in `available_mana` and
        `engine.spend`, because it is not a loyalty ability and does not wait
        for this method -- it is live the turn she resolves, which is most of
        why she is a five-drop worth casting in a deck with 21 Forests.

        THE +1 IS A RITUAL AS WELL AS A BODY, and the untap is the half that is
        easy to miss: a land that has already been tapped for mana this turn
        comes back untapped, so the ability pays for part of itself. It is
        therefore preferred on a TAPPED land, which is the opposite of Nissa,
        Worldwaker's +1 (that one does not untap, so it wants a land that can
        still attack).

        THE ULTIMATE IS THE SAME SHAPE AS WORLDWAKER'S -7 and is implemented
        the same way, with one difference that matters in this deck: these
        lands enter TAPPED, so they are mana next turn rather than this one --
        but every one of them is still a landfall trigger as it enters. The
        emblem is not modelled and cannot matter: `spot_removal`, `ae_removal`
        and `board_wipe` all exclude lands already, so "lands you control have
        indestructible" is worth exactly zero here. Said out loud so the row is
        not read as a measurement of the whole card.
        """
        if perm.counters >= 8:
            perm.counters -= 8
            forests = [c for c in self.library if c.name in FOREST]
            # Out of the library FIRST, then onto the battlefield -- the
            # Genesis Wave crash of 2026-09-07, and Worldwaker's -7 above,
            # for the same reason: a landfall trigger can draw.
            for c in forests:
                self.library.remove(c)
            for c in forests:
                self.make_permanent(c, sick=True, tapped=True)
                self.land_entered(c, played=False)
            self.shuffle_library()
            self.m["pw_ultimates"] += 1
            return

        perm.counters += 1
        # "up to one target NONCREATURE land": Dryad Arbor is a creature land
        # and is not a legal target, and a land some other effect has already
        # animated is a creature too. A tapped land is preferred for the untap.
        targets = [p for p in self.board if p.card.is_land
                   and not p.card.is_creature
                   and self.animation_of(p) is None]
        if not targets:
            return
        target = max(targets, key=lambda p: p.tapped)
        target.tapped = False
        target.counters += 3
        # 0/0 with three +1/+1 counters. `animate_lands` supplies the 0/0 and
        # `power_of` adds `perm.counters`, so the land is a 3/3 -- and it stays
        # a 3/3 if anything else puts counters on it later, which is the right
        # behaviour and not something a flat 3/3 animation would give.
        self.animate_lands(0, 0, targets=[target], haste=True,
                           source="Nissa, Who Shakes the World +1")

    def _nissa_sage_animist(self, perm):
        """Nissa, Sage Animist, loyalty 3 — the back face. Verified 2026-09-07.

            +1: Reveal the top card of your library. If it's a land card, put
                it onto the battlefield. Otherwise, put it into your hand.
            -2: Create Ashaya, the Awoken World, a legendary 4/4 green
                Elemental creature token.
            -7: Untap up to six target lands. They become 6/6 Elemental
                creatures. They're still lands.

        The -2 is never taken; see the module docstring. In a 40-land deck the
        +1 is a free land drop three times in five and a card the rest of the
        time, and spending to 1 loyalty gives up the -7 that untaps six lands
        as 6/6s — which, unlike the -2, can end the game on the spot.
        """
        if perm.counters >= 7:
            perm.counters -= 7
            targets = sorted((p for p in self.board if p.card.is_land),
                             key=lambda p: (not p.tapped, p.sick))[:6]
            for p in targets:
                p.tapped = False
            self.animate_lands(6, 6, targets=targets,
                               source="Nissa, Sage Animist -7")
            self.m["pw_ultimates"] += 1
            return

        perm.counters += 1
        if not self.library:
            return
        top = self.library.pop()
        if top.is_land:
            self.make_permanent(top, sick=True, tapped=bool(top.tapped))
            self.land_entered(top, played=False)
            self.m["lands_from_library"] += 1
        else:
            # "Put it into your hand" is not a draw, so it is deliberately not
            # counted in cards_drawn -- nothing that reads a draw trigger
            # should see this.
            self.hand.append(top)

    def activations(self):
        units = self.available_mana()
        clues = getattr(self, "clues", 0)
        while clues > 0:
            pay = can_pay({"gen": 2}, units)
            if pay is None:
                break
            spend(self, pay, units)
            self.m["mana_spent"] += 2
            self.draw(1)
            clues -= 1
            if self.has("Tireless Tracker"):
                for p in self.board:
                    if p.card.name == "Tireless Tracker":
                        p.counters += 1
                        break
        self.clues = clues

        # CRYPTIC CAVES: "{1}, {T}, Sacrifice this land: Draw a card.
        # Activate only if you control five or more lands."
        #
        # THE POLICY IS THE WHOLE CARD, so it is stated rather than buried.
        # Cracking it trades a land for a card, which is a bad rate in most
        # decks and a good one here -- this deck is CARD-limited and land-rich
        # (2.77 drops granted a turn against 1.33 used). It fires when:
        #
        #   * the printed condition is met (five or more lands), AND
        #   * {1} is available and the land itself is untapped, AND
        #   * EITHER a graveyard-land recursion effect is out -- Crucible of
        #     Worlds, Ramunap Excavator or Ancient Greenwarden -- in which
        #     case the land comes BACK and the whole thing is free and
        #     repeatable, and replaying it is another landfall trigger on a
        #     drop that was going begging;
        #   * OR you control six or more lands, so sacrificing one still
        #     leaves the five the ability wants and does not cut your mana.
        #
        # The SIX is a deliberately mild threshold rather than a tuned one.
        # A stricter gate would be the "conservatism that asserts a card does
        # nothing" failure this project has paid for three times (§0r, §0s,
        # §0v); a looser one would crack it on turn five holding exactly five
        # lands, which no pilot does. `cryptic_caves_min_lands` is the knob.
        for pm in list(self.board):
            spec = SAC_DRAW_LANDS.get(pm.card.name)
            if spec is None:
                continue
            cost, needs_tap, min_lands = spec
            if needs_tap and pm.tapped:
                continue            # {T} is in the cost; a tapped land cannot
            n_lands = sum(1 for p in self.board if p.card.is_land)
            if n_lands < min_lands:
                continue            # the card's own printed condition
            recursion = (self.has("Crucible of Worlds")
                         or self.has("Ramunap Excavator")
                         or self.has("Ancient Greenwarden"))
            floor = self.cfg.get("cryptic_caves_min_lands", 6)
            if not (recursion or n_lands >= floor):
                continue
            units = self.available_mana()
            pay = can_pay(cost, units)
            if pay is None:
                continue
            spend(self, pay, units)
            self.m["mana_spent"] += sum(cost.values())
            self.board.remove(pm)
            self.land_died(pm.card)
            self.draw(1)
            self.m["caves_cracked"] += 1

        # WAR ROOM: "{3}, {T}, Pay life equal to the number of colors in your
        # commanders' color identity: Draw a card." Azusa is mono-green, so
        # ONE life -- and this is one of the very few life payments in this
        # project that is actually charged. §0i is the standing finding that
        # life-loss drawbacks are free here; `your_life` is real, it is read at
        # the end of every turn by `incidental_damage`, and nothing stopped
        # this card paying properly, so it does.
        #
        # It runs AFTER the main phase, so the {3} is genuinely spare mana: a
        # pilot with a spell to cast casts it. The tap is the real cost and it
        # is modelled by the tap -- a War Room that draws produced no mana this
        # turn, which is why a colourless utility land that draws is not
        # strictly better than a Forest in a deck with {G}{G} costs in it.
        for pm in list(self.board):
            if pm.card.name != "War Room" or pm.tapped:
                continue
            units = self.available_mana()
            pay = can_pay({"gen": 3}, units)
            if pay is None:
                continue
            spend(self, pay, units)
            pm.tapped = True
            self.your_life -= 1
            self.draw(1)
            self.m["war_room_draws"] += 1

        # Perilous Forays: {1}, sac a creature -> tutor a basic land to the
        # battlefield tapped. Token fodder only -- see the shilgengar.py
        # aristocrats-policy note this mirrors: never sac a real card.
        if self.has("Perilous Forays"):
            fodder = [p for p in self.board if p.is_token and p.card.is_creature
                     and not p.sick]
            for p in fodder[:2]:
                units = self.available_mana()
                pay = can_pay({"gen": 1}, units)
                land = next((c for c in self.library if c.name == "Forest"), None)
                if pay is None or land is None:
                    break
                spend(self, pay, units)
                self.m["mana_spent"] += 1
                self.board.remove(p)
                self.m["creatures_sacrificed"] += 1
                self.on_creature_death(1, p)
                self.library.remove(land)
                self.make_permanent(land, sick=False, tapped=True)
                self.land_entered(land, played=False)

    def combat(self):
        attackers = [p for p in self.board if p.card.is_creature
                    and not p.tapped and not p.sick
                    and not (p.card.name == "Wayward Swordtooth" and not self.ascended)]
        # ANIMATED LANDS ATTACK AS THEMSELVES. They used to be fabricated as
        # throwaway 2/2 token Permanents that were never on the battlefield,
        # which meant tapping them for the attack tapped nothing: the same
        # lands then paid for the postcombat main phase. The real permanent is
        # tapped below with every other attacker, so the mana is really spent.
        if self.legacy_animation:
            # THE PRE-2026-09-07 PATH, kept so the committed ablation table
            # can be reproduced. Every untapped land became a throwaway 2/2
            # Permanent that was never on the battlefield: it could not be
            # tapped by attacking, so the same lands still paid for the
            # postcombat main phase, and it vanished at end of turn so it
            # never blocked. `cfg["land_animation"]="legacy"` selects it.
            for p in self.board:
                if p.card.is_land and not p.tapped:
                    tok = Card(name="animated land",
                               types=frozenset({"Creature"}),
                               power=2, toughness=2)
                    attackers.append(Permanent(card=tok, sick=False,
                                               tapped=False))
        n_animated = 0
        for p in self.board:
            if p.card.is_creature or p.tapped:
                continue          # creature-lands are already in `attackers`
            anim = self.animation_of(p)
            if anim is None or (p.sick and not anim["haste"]):
                continue
            attackers.append(p)
            n_animated += 1
        if n_animated:
            self.m["animated_attacks"] += n_animated
            # What the animation was WORTH this combat, defined as its
            # marginal contribution: the damage that got through with the
            # lands in the attack, minus what would have got through without
            # them. Chump blocks make that smaller than the lands' total
            # power, which is the point of measuring it this way rather than
            # summing their power.
            without = OPP.damage_through(
                self, [p for p in attackers
                       if p.card.is_creature or self.animation_of(p) is None])
            self.m["animated_damage"] += (OPP.damage_through(self, attackers)
                                          - without)
        # Annihilator 4: Kozilek / Ulamog force the defending opponent to
        # sacrifice up to four permanents. Approximated as reducing that
        # opponent's abstract `creatures` float -- value denial, not damage.
        for p in attackers:
            if p.card.name in ("Kozilek, Butcher of Truth", "Ulamog, the Infinite Gyre"):
                living = OPP.living(self)
                if living:
                    victim = min(living, key=lambda o: o.life)
                    victim.creatures = max(0.0, victim.creatures - 4)
        if not attackers:
            self.damage_by_turn.append(0.0)
            return
        # ONE attack at the whole pod, not at one player, and `dmg` is the
        # BOUNDED figure -- damage past a player's life total is meaningless
        # and in this deck it was 98.5% of the number. `raw_damage` keeps the
        # unbounded total for anyone who wants it.
        dmg = OPP.combat_damage(self, attackers)
        for p in attackers:
            p.tapped = True
        self.m["damage"] += dmg
        self.m["combat_damage"] += dmg
        self.damage_by_turn.append(dmg)
        if self.result is None and self.m["turn_lethal"] == 99 and not OPP.living(self):
            self.m["turn_lethal"] = self.turn


def take_turn(g):
    g.turn += 1
    g.spells_this_turn = 0
    g.craterhoof_bonus = 0
    g.wildspeaker_bonus = 0
    # Castle Garenbrig's pool empties with the turn, like any unspent mana.
    g.creature_mana = []
    g.bonus_mana = []
    g.pw_used = set()
    g.legacy_animation = False
    # "Until your next turn" ends HERE, at the start of it -- which is what
    # gave Sylvan Awakening's lands the pod's whole round as blockers.
    g.expire_animations()
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.land_drops = 1
    g.land_drops_used = 0

    g.draw(1)
    # ENABLERS BEFORE DROPS. Azusa's own +2, Exploration, Oracle, and every
    # landfall payoff have to be on the battlefield before the land drops are
    # spent, or they contribute nothing on the turn they arrive.
    g.main_phase(enablers_only=True)
    g.land_step()
    # Sorcery speed, before the main phase, so an untap mode feeds it.
    g.planeswalker_step()
    g.main_phase()
    if g.result is not None:
        return
    # Again, so a walker CAST this main phase still activates the turn she
    # lands. `pw_used` makes this a no-op for one that already has.
    g.planeswalker_step()
    g.combat()
    g.activations()
    # A SECOND LAND STEP, mirroring engine.py's two `play_land` calls: drops
    # granted or unlocked by something cast after the first one (a Wayward
    # Swordtooth that only just Ascended, an Oracle cast postcombat) are still
    # usable, and `land_drops_for_turn()` is re-read here rather than cached.
    g.land_step()
    g.main_phase()
    if g.result is not None:
        return

    # THE GREAT HENGE's second half: "{T}: Add {G}{G}. You gain 2 life."
    # The mana is a `mana_ability` and needs no code. The LIFE is taken HERE,
    # at the end of the turn and after the last main phase, because that is
    # when a pilot takes it: tapping the Henge earlier would hand it two mana
    # the casting might have wanted, and tapping it later than this is not a
    # thing you can do. Two life a turn is small and it is not nothing -- life
    # decides a third of this project's losses since pod v3 (§0i, §6b).
    for p in g.board:
        if p.card.name == "The Great Henge" and not p.tapped:
            p.tapped = True
            g.gain_life(2)
            g.m["henge_life"] += 2

    g.m["mana_floated"] += len(g.available_mana())
    g.m["stranded_mv"] += sum(c.mv for c in g.hand if not c.is_land)

    # "To solve -- you control seven or more lands. (If unsolved, solve at the
    # BEGINNING OF YOUR END STEP.)" Checked here rather than continuously,
    # because the card says so and because it matters: a Case that reaches
    # seven lands mid-turn does not give you top access until the next turn.
    # Once solved it stays solved -- there is no unsolve.
    if not g.hothouse_solved and g.has("Case of the Locked Hothouse"):
        if sum(1 for p in g.board if p.card.is_land) >= 7:
            g.hothouse_solved = True
            g.m["hothouse_solved_turn"] = g.turn

    # END OF TURN. Rude Awakening's mode and Nissa's +1 stop here; Sylvan
    # Awakening's does not, which is the only reason its lands ever block.
    g.expire_animations(end_of_turn=True)
    g.m["animated_blocker_turns"] += sum(
        1 for p in g.board if not p.card.is_creature
        and g.animation_of(p) is not None)

    if g.cfg.get("opponents", True):
        OPP.incidental_damage(g)
        OPP.resolve_clocks(g)
        if g.result is not None:
            return
        watch = g.cfg.get("watch", ())
        before = {p.card.name for p in g.board if p.card.name in watch}
        OPP.opponents_act(g)
        after = {p.card.name for p in g.board if p.card.name in watch}
        for _ in before - after:
            g.m["test_card_answered"] += 1
            g.m["test_card_removed"] += 1


def simulate(deck, commander, cfg, seed):
    g = AzusaGame(deck, commander, cfg, seed)
    g.opening_hand()
    for _ in range(cfg.get("turns", 20)):
        take_turn(g)
        if g.result is not None:
            break
    out = dict(g.m)
    out["damage_by_turn"] = g.damage_by_turn
    out["result"] = g.result or "timeout"
    out["turns_played"] = g.turn
    out["won"] = 1 if g.result == "win" else 0
    out["lost"] = 1 if g.result == "loss" else 0
    out["final_life"] = g.your_life
    out["opponents_killed"] = sum(1 for o in g.opponents if not o.alive)
    out["final_board_power"] = sum(g.power_of(p) for p in g.board if p.card.is_creature)
    out["test_card_resolved"] = 1 if (out["cast_test_card"] and
                                      not out["test_card_answered"]) else 0
    return out


# ---------------------------------------------------------------------------
# The LAND_ENABLERS set, checked rather than claimed
# ---------------------------------------------------------------------------

def check_land_enabler_coverage():
    """Every card this engine reads BY NAME when deciding how many lands it
    may play, where it may play them from, or what happens when one enters,
    must also be in LAND_ENABLERS -- or it will be deployed after the land
    drops and do nothing on the turn it arrives.

    WHY THIS IS DERIVED AND NOT A SECOND HAND-WRITTEN LIST. A name set that
    nothing checks is a claim, and this repo has been bitten by that exact
    shape twice already: `ablation.SCRIPTED_*` printed five fully-implemented
    cards as MODEL-BLIND on 2026-09-04, and `tag_flying.py` measured two
    fliers as ground creatures on 2026-09-05. Both were a hand-written list
    that the deck moved past. So the authority here is the ENGINE ITSELF --
    the three methods below ARE the definition of "land-relevant" -- and the
    set is checked against them at import. A new landfall payoff added to
    `land_entered` and forgotten here fails loudly instead of silently
    scoring low. KNOWN_ISSUES.md 0q.
    """
    watched = (AzusaGame.land_entered, AzusaGame.land_drops_for_turn,
               AzusaGame.playable_lands, AzusaGame.land_died)
    named = set()
    for fn in watched:
        named |= set(re.findall(r'self\.(?:has|count)\("([^"]+)"\)',
                                inspect.getsource(fn)))
    missing = named - LAND_ENABLERS
    if missing:
        raise AssertionError(
            "edhmc/azusa.py: these cards are read by the land logic but are "
            "NOT in LAND_ENABLERS, so they would be deployed after the land "
            "drops and do nothing the turn they land:\n"
            + "".join(f"    {n}\n" for n in sorted(missing))
            + "Add them to LAND_ENABLERS, or take them out of the land logic.")
    return named


def check_planeswalker_coverage():
    """Every Planeswalker in the deck must have a starting loyalty here.

    Same rule as check_land_enabler_coverage() above and the same reason for
    it (KNOWN_ISSUES.md 0q): a walker missing from PLANESWALKERS enters with
    counters=0, is never picked up by planeswalker_step(), and sits there as
    an inert permanent scoring like a blank -- which is exactly the state BOTH
    Nissas were in until 2026-09-07, with nothing anywhere saying so.

    CANDIDATES ARE CHECKED TOO, added 2026-09-10, because a candidate is where
    a new Planeswalker actually enters this project -- `candidates.py` swaps it
    into the list and measures it, and a walker with no entry here would be
    measured as an inert permanent and reported as a bad card. Nissa, Who
    Shakes the World arrived exactly that way. This is the same widening
    check_dynamic_pt_coverage() already has, and for the same reason.

    The deck is imported inside the function because decks import the engine,
    not the other way round.
    """
    from edhmc.decks import azusa_v1
    deck, _ = azusa_v1.build()
    module_cards = [v for a in dir(azusa_v1) if a.isupper()
                    for v in [getattr(azusa_v1, a)]
                    if type(v).__name__ == "Card"]
    missing = ({c.name for c in list(deck) + module_cards
                if "Planeswalker" in c.types}
               - set(PLANESWALKERS))
    if missing:
        raise AssertionError(
            "edhmc/azusa.py: these Planeswalkers have no entry in "
            "PLANESWALKERS, so they would enter with zero loyalty and never "
            "activate an ability:\n"
            + "".join(f"    {n}\n" for n in sorted(missing)))
    return missing


def check_dynamic_pt_coverage():
    """Every name in DYNAMIC_PT_LANDS must be a real card somewhere.

    These cards are printed */* and are therefore DEFINED with power=0 and
    toughness=0, with `power_of` / `toughness_of` supplying the land count.
    A name misspelled here is silently a 0/0: it enters, dies as a
    state-based action, and its row reads as a bad card rather than a broken
    one. That is the §0q failure with a worse symptom than usual, because a
    0/0 does not merely under-score -- it never exists.

    Checked against the deck AND the candidate list, because a candidate is
    exactly where a new */* card enters this project.
    """
    from edhmc.decks import azusa_v1
    deck, cmd = azusa_v1.build()
    known = {c.name for c in deck} | {cmd.name}
    # Module-level candidates too, discovered the same way audit_cards.py
    # discovers them, so this cannot drift from what that tool checks.
    module_cards = [v for a in dir(azusa_v1) if a.isupper()
                    for v in [getattr(azusa_v1, a)]
                    if type(v).__name__ == "Card"]
    known |= {c.name for c in module_cards}
    unknown = DYNAMIC_PT_LANDS - known
    if unknown:
        raise AssertionError(
            "edhmc/azusa.py: DYNAMIC_PT_LANDS names no card in the deck or "
            "the candidate list, so nothing would ever match it and the "
            "card it was meant to describe is a 0/0:\n"
            + "".join(f"    {n}\n" for n in sorted(unknown)))
    # A card in this set that is NOT defined 0/0 was almost certainly added by
    # accident, and the symptom is silent and large: its printed P/T is
    # DISCARDED and replaced by the land count, so a 3/2 becomes a 16/16 in a
    # deck that reaches sixteen lands. This fired for real on 2026-09-10 --
    # Ka-Zar of the Savage Land was added to this set instead of
    # LAND_ENABLERS by a sed whose anchor matched both blocks, and it was
    # MEASURED as a */* before anyone noticed. §0z3.
    wrong_pt = {c.name for c in module_cards
                if c.name in DYNAMIC_PT_LANDS and c.is_creature
                and (c.power, c.toughness) != (0, 0)}
    if wrong_pt:
        raise AssertionError(
            "edhmc/azusa.py: these cards are in DYNAMIC_PT_LANDS but are NOT "
            "defined 0/0, so their printed power and toughness are being "
            "silently thrown away and replaced by your land count:\n"
            + "".join(f"    {n}\n" for n in sorted(wrong_pt)))

    # And the reverse: a */* card defined 0/0 that nobody added here.
    zero_pt = {c.name for c in module_cards
               if c.is_creature and c.power == 0 and c.toughness == 0}
    stranded = zero_pt - DYNAMIC_PT_LANDS
    if stranded:
        raise AssertionError(
            "edhmc/azusa.py: these candidate creatures are defined 0/0 but "
            "are not in DYNAMIC_PT_LANDS, so they are literally 0/0 and die "
            "on arrival:\n"
            + "".join(f"    {n}\n" for n in sorted(stranded)))
    return unknown


def check_dynamic_cost_coverage():
    """Every name in DYNAMIC_COST must be a real card, and must be the same set
    cost_of() actually special-cases.

    The failure this prevents is quiet in both directions. A name misspelled
    HERE leaves the card at its printed cost -- The Great Henge at nine mana
    and Sapling Nursery at eight, neither of which anybody ever pays -- so the
    card resolves in a handful of games and its row reads as a bad card. A card
    reduced in cost_of() and missing from here is the opposite: nothing checks
    it at all, and the set stops describing the engine, which is how
    `SCRIPTED_*` went stale twice (§0q).
    """
    from edhmc.decks import azusa_v1
    deck, cmd = azusa_v1.build()
    known = {c.name for c in deck} | {cmd.name}
    known |= {v.name for a in dir(azusa_v1) if a.isupper()
              for v in [getattr(azusa_v1, a)] if type(v).__name__ == "Card"}
    unknown = DYNAMIC_COST - known
    if unknown:
        raise AssertionError(
            "edhmc/azusa.py: DYNAMIC_COST names no card in the deck or the "
            "candidate list, so the reduction would never apply and the card "
            "would be cast at its printed cost:\n"
            + "".join(f"    {n}\n" for n in sorted(unknown)))
    # And the reverse: what cost_of() actually reduces, read off the source.
    reduced = set(re.findall(r'card\.name == "([^"]+)"',
                             inspect.getsource(AzusaGame.cost_of)))
    drift = reduced - DYNAMIC_COST
    if drift:
        raise AssertionError(
            "edhmc/azusa.py: cost_of() reduces the cost of these cards but "
            "they are not in DYNAMIC_COST, so the set no longer describes the "
            "engine:\n" + "".join(f"    {n}\n" for n in sorted(drift)))
    return unknown


check_land_enabler_coverage()
check_planeswalker_coverage()
check_dynamic_pt_coverage()
check_dynamic_cost_coverage()
