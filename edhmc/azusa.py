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
                          spend, devotion)
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
}

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
        self.craterhoof_bonus = 0
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

    def power_of(self, perm):
        anim = self.animation_of(perm) if perm.card.is_land else None
        if anim is not None:
            # An animation SETS power and toughness; it does not add to them.
            return anim["power"] + perm.counters + self.craterhoof_bonus
        base = perm.base_p if perm.is_token else perm.card.power
        p = base + perm.counters
        if perm.card.name == "Ashaya, Soul of the Wild":
            p = sum(1 for q in self.board if q.card.is_land)
        p += self.craterhoof_bonus
        return p

    def toughness_of(self, perm):
        anim = self.animation_of(perm) if perm.card.is_land else None
        if anim is not None:
            return anim["toughness"] + perm.counters + self.craterhoof_bonus
        base = perm.base_t if perm.is_token else perm.card.toughness
        t = base + perm.counters
        if perm.card.name == "Ashaya, Soul of the Wild":
            t = sum(1 for q in self.board if q.card.is_land)
        t += self.craterhoof_bonus
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
        self.m["damage"] += amount
        if self.damage_by_turn:
            self.damage_by_turn[-1] += amount
        n = max(1, len(OPP.living(self)))
        OPP.damage_each(self, amount / n) if each else OPP.damage_single(self, amount)

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
        return perm

    def make_tokens(self, n, p, t, subtype=""):
        for _ in range(int(n)):
            tok = Card(name=f"{subtype or 'Token'} token",
                       types=frozenset({"Creature"}), power=p, toughness=t)
            self.make_permanent(tok, sick=True, is_token=True)
            self.m["tokens_made"] += 1

    def available_mana(self):
        units: list[frozenset] = []
        n_lands = sum(1 for p in self.board if p.card.is_land)
        for p in self.board:
            if p.tapped:
                continue
            c = p.card
            if c.is_land:
                if c.name == "Temple of the False God":
                    units.extend([frozenset({"C"})] * (2 if n_lands >= 5 else 1))
                elif c.name == "Eye of Ugin":
                    pass   # no mana ability on the current oracle text
                else:
                    units.extend([c.produces] * 1)
            elif c.mana_ability:
                if c.is_creature and p.sick:
                    continue
                amt, colors = c.mana_ability
                units.extend([colors] * amt)
        units.extend(self.bonus_mana)
        return units

    # -- landfall --------------------------------------------------------

    def land_entered(self, card, played=False):
        """The one hook every landfall payoff in the deck runs through.

        `played` distinguishes an actual land drop (counts for Horn of
        Greed's "whenever a player plays a land") from a land that entered
        via search/fetch/tutor (Cultivate, a cracked fetch land, Titania's
        ETB) — none of those are "playing a land".
        """
        self.m["landfall_triggers"] += 1
        if played and self.has("Horn of Greed"):
            self.draw(1)
        if self.has("Avenger of Zendikar"):
            for p in self.board:
                if p.is_token and p.card.name == "Plant token":
                    p.counters += 1
        if self.has("Courser of Kruphix"):
            self.gain_life(1)
        if self.has("Lotus Cobra"):
            self.bonus_mana.append(frozenset({"G"}))
        if self.has("Rampaging Baloths"):
            self.make_tokens(1, 4, 4, "Beast")
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
        if self.has("Tireless Provisioner"):
            # "create a Food or a Treasure token" -- modelled as the
            # Treasure mode (immediately useful mana), the same
            # single-more-useful-mode simplification the deck's other choose-
            # one lands effects make.
            self.bonus_mana.append(frozenset({"W", "U", "B", "R", "G", "C"}))
        if self.has("Tireless Tracker"):
            self.clues = getattr(self, "clues", 0) + 1
        if self.count("Nissa, Vastwood Seer // Nissa, Sage Animist"):
            # "Whenever a land you control enters, IF YOU CONTROL SEVEN OR
            # MORE LANDS, exile Nissa, then return her to the battlefield
            # transformed." The trigger did not exist: only her ETB Forest
            # search was modelled, so in a deck that reaches seven lands
            # around turn five she stayed a 2/2 for the rest of the game.
            if sum(1 for p in self.board if p.card.is_land) >= 7:
                self.transform_nissa()
        if self.has("Seer's Sundial"):
            units = self.available_mana()
            pay = can_pay({"gen": 2}, units)
            if pay is not None:
                spend(self, pay, units)
                self.m["mana_spent"] += 2
                self.draw(1)

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
        return n

    def playable_lands(self):
        """Everywhere this deck can play a land FROM, this turn: hand, the
        top of the library (Augur of Autumn / Courser of Kruphix / Oracle of
        Mul Daya), and the graveyard (Ramunap Excavator / Crucible of
        Worlds). Returns (card, zone) pairs."""
        out = [(c, "hand") for c in self.hand if c.is_land]
        if self.library and self.library[-1].is_land and (
                self.has("Augur of Autumn") or self.has("Courser of Kruphix")
                or self.has("Oracle of Mul Daya")):
            out.append((self.library[-1], "library"))
        if self.has("Ramunap Excavator") or self.has("Crucible of Worlds"):
            out += [(c, "graveyard") for c in self.graveyard if c.is_land]
        return out

    def top_access(self):
        return (self.has("Augur of Autumn") or self.has("Courser of Kruphix")
                or self.has("Oracle of Mul Daya"))

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
            perm = self.make_permanent(card, sick=False, tapped=card.tapped)
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
        return cost

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

    def tutor_creature(self, max_mv, nonlegendary_only=False):
        pool = [c for c in self.library if c.is_creature and c.mv <= max_mv
               and (not nonlegendary_only or "Legendary" not in c.tags)]
        if not pool:
            return
        best = max(pool, key=lambda c: c.mv)
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

            options = []
            for c in self.hand:
                if c.is_land:
                    continue
                if enablers_only and c.name not in LAND_ENABLERS:
                    continue
                if "wipe" in c.tags and not OPP.should_cast_own_wipe(self):
                    continue
                pay = can_pay(self.cost_of(c), units)
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
            spend(self, pay, units)
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
        dmg = OPP.damage_through(self, attackers)
        for p in attackers:
            p.tapped = True
        self.m["damage"] += dmg
        self.m["combat_damage"] += dmg
        self.damage_by_turn.append(dmg)
        OPP.damage_single(self, dmg)
        if self.result is None and self.m["turn_lethal"] == 99 and not OPP.living(self):
            self.m["turn_lethal"] = self.turn


def take_turn(g):
    g.turn += 1
    g.spells_this_turn = 0
    g.craterhoof_bonus = 0
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

    g.m["mana_floated"] += len(g.available_mana())
    g.m["stranded_mv"] += sum(c.mv for c in g.hand if not c.is_land)

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

    The deck is imported inside the function because decks import the engine,
    not the other way round.
    """
    from edhmc.decks import azusa_v1
    deck, _ = azusa_v1.build()
    missing = ({c.name for c in deck if "Planeswalker" in c.types}
               - set(PLANESWALKERS))
    if missing:
        raise AssertionError(
            "edhmc/azusa.py: these Planeswalkers have no entry in "
            "PLANESWALKERS, so they would enter with zero loyalty and never "
            "activate an ability:\n"
            + "".join(f"    {n}\n" for n in sorted(missing)))
    return missing


check_land_enabler_coverage()
check_planeswalker_coverage()
