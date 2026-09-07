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
blind for the same reason. Two Planeswalkers (Nissa, Worldwaker and the
transformed back face of Nissa, Vastwood Seer) have their activated abilities
left unmodelled — nothing else in this project tracks planeswalker loyalty,
and inventing that machinery for one card was judged not worth it; their
FRONT-face or on-cast value, where they have one, is scripted separately.

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
})


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
        self.land_animation_active = False
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
        }
        self.damage_by_turn = []

    # -- helpers ---------------------------------------------------------

    def has(self, name):
        return name in self.board.names

    def count(self, name):
        return self.board.names.get(name, 0)

    def power_of(self, perm):
        base = perm.base_p if perm.is_token else perm.card.power
        p = base + perm.counters
        if perm.card.name == "Ashaya, Soul of the Wild":
            p = sum(1 for q in self.board if q.card.is_land)
        p += self.craterhoof_bonus
        return p

    def toughness_of(self, perm):
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
        if self.has("Seer's Sundial"):
            units = self.available_mana()
            pay = can_pay({"gen": 2}, units)
            if pay is not None:
                spend(self, pay, units)
                self.m["mana_spent"] += 2
                self.draw(1)

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
            for p in self.board:
                if p.card.is_land:
                    p.tapped = False
        elif script == "sylvan_awakening":
            self.land_animation_active = True
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
        powers = {self.power_of(p) for p in self.board if p.card.is_creature}
        return len([p for p in self.board if p.card.is_creature]) >= 3 \
            and len(powers) >= 3

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
        if self.land_animation_active:
            for p in self.board:
                if p.card.is_land and not p.tapped:
                    tok = Card(name="animated land", types=frozenset({"Creature"}),
                              power=2, toughness=2)
                    attackers.append(Permanent(card=tok, sick=False, tapped=False))
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
    g.land_animation_active = False
    g.bonus_mana = []
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
    g.main_phase()
    if g.result is not None:
        return
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


check_land_enabler_coverage()
