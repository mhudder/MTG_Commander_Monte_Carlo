"""
edhmc.shilgengar — a Blood/aristocrats engine for Shilgengar, Sire of Famine.

    Shilgengar, Sire of Famine  {3}{B}{B}  6/6 flying
      Sacrifice another creature: Create a Blood token. If you sacrificed an
      Angel this way, create a number of Blood tokens equal to its toughness
      instead.
      {W/B}{W/B}{W/B}, Sacrifice six Blood tokens: Return each creature card
      from your graveyard to the battlefield with a finality counter on it.
      Those creatures are Vampires in addition to their other types.

Verified against Scryfall 2026-09-07. Note what the card does NOT say: it is
not a combat-damage edict. Its whole engine is "sacrifice for Blood, then
spend Blood on a mass reanimation" — closer to Ashnod's Altar than to any
"whenever this deals combat damage" demon.

THE CENTRAL MODELLING FACT
---------------------------
This is two decks stapled together and Shilgengar is the staple. Half the list
is a white Angels-tribal lifegain-and-tokens shell (Righteous Valkyrie, Giada,
Bishop of Wings, Lyra Dawnbringer, Archangel of Thune); the other half is a
black aristocrats shell (Blood Artist, Zulaport Cutthroat, Midnight Reaper,
Grim Haruspex, Dark Prophecy, Pitiless Plunderer, Vampiric Rites, Viscera
Seer, Cartel Aristocrat). Shilgengar's activated ability is the thing that
makes sacrificing a big-toughness Angel into the black shell's best play,
which is the deck's actual thesis and is why both halves get real engine code
rather than one being window dressing for the other.

SUBTYPES, WHICH `Card.types` DOES NOT CARRY
--------------------------------------------
`Card.types` is CARD TYPES ("Creature", "Enchantment"), not creature types —
nothing in this project has ever needed to ask "is this an Angel" before.
Angels and Clerics are marked with `tags=("angel",)` / `("cleric",)` in the
deck module, the same mechanism `rendmaw_v12.py` uses for "swamp" and "wipe".
Token Angels made by this engine (`make_angel_tokens`) carry the tag too, or
Righteous Valkyrie / Giada / Youthful Valkyrie / Bishop of Wings would silently
never see them enter.

THE SACRIFICE POLICY, SAID OUT LOUD
------------------------------------
A real pilot sometimes feeds a live Lyra Dawnbringer to Shilgengar for five
Blood on the way to the six-Blood reanimation. This model does not attempt
that judgement call — see README's "your own decision quality" disclaimer —
and only ever sacrifices EXPENDABLE TOKENS (1/1 Spirits from Requiem Angel and
Bishop of Wings; never the 4/4 Angel tokens, which stay on board as real
attackers/blockers, and never a real card). That understates Shilgengar's own
ability and the six-Blood reanimation, which in practice both fire more often
than this engine ever lets them. Said once here rather than at every call site.

WHAT IS MODEL-BLIND AND WHY
-----------------------------------------------------------------------------
Half of this list is removal on a body (Angel of Despair, Angel of Serenity,
Angel of the Ruins) or plain removal (Path to Exile, Swords to Plowshares,
Anguished Unmaking, Generous Gift, Despark, Vindicate, Mortify, Utter End) —
opponents' boards are a blocker count, so none of it has a legal target, same
as every other deck in this project. Revel in Riches needs opponents'
creatures to die as discrete events, which nothing here tracks. Angel of
Suffering's damage-prevention-into-mill replacement effect was deliberately
NOT modelled: it is not clear how it should interact with `resolve_clocks`
elimination (a game-loss check, not a damage event), and guessing that
interaction risks silently making the deck unkillable. See `KNOWN_BLIND` in
`ablation.py` for the full, reasoned list.

WIN CONDITIONS
--------------
  1. Combat, drain, and the mass-reanimation swing (the default plan).
  2. Revel in Riches — 10 or more Treasures (its OWN generation is
     model-blind, but Treasures from Smothering Tithe / Black Market
     Connections / Pitiless Plunderer / Wayfarer's Bauble still count).
"""

from __future__ import annotations

import random

from edhmc.engine import (Board, Card, Permanent, can_pay, available_mana,
                          spend, play_land)
from edhmc import opponents as OPP

ANGEL_TOKEN_STATS = (4, 4)   # every Angel token this deck makes is a 4/4 flier


class ShilgengarGame:
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
        self.treasures = 0
        self.blood = 0
        self.life_gained_this_turn = 0.0     # Resplendent Angel / Speaker
        self.died_this_turn = 0              # diagnostics only
        self.marble_diamond_played = set()   # ids already handled as tapped

        cfg.setdefault("shroud_sources", ())
        cfg.setdefault("protection_cards",
                       ("Flawless Maneuver", "Teferi's Protection"))
        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = {
            "damage": 0.0, "combat_damage": 0.0, "drain_damage": 0.0,
            "cards_drawn": 0, "mana_spent": 0, "mana_floated": 0,
            "stranded_mv": 0, "turn_lethal": 99, "turn_won": 99,
            "removal_eaten": 0, "ae_removal_eaten": 0, "wipes_suffered": 0,
            "countered": 0, "protected": 0, "loss_route": 0, "win_route": 0,
            "cast_test_card": 0, "test_card_turn": 99,
            "test_card_answered": 0, "test_card_removed": 0,
            "test_card_countered": 0,
            "creatures_sacrificed": 0, "blood_made": 0, "blood_spent": 0,
            "shilgengar_ults": 0, "shilgengar_reanimated": 0,
            "single_reanimations": 0, "treasures_made": 0,
            "life_gained": 0, "lifegain_triggers": 0,
            "angel_tokens_made": 0, "spirit_tokens_made": 0,
        }
        self.damage_by_turn = []

    # -- helpers ---------------------------------------------------------

    def has(self, name):
        return name in self.board.names

    def count(self, name):
        return self.board.names.get(name, 0)

    def is_angel(self, perm):
        return "angel" in perm.card.tags

    def power_of(self, perm):
        base = perm.base_p if perm.is_token else perm.card.power
        p = base + perm.counters
        if perm.card is not self.commander:
            if self.has("Elesh Norn, Grand Cenobite") \
                    and perm.card.name != "Elesh Norn, Grand Cenobite":
                p += 2
            if self.has("Lyra Dawnbringer") and self.is_angel(perm) \
                    and perm.card.name != "Lyra Dawnbringer":
                p += 1
        if self.has("Righteous Valkyrie") and self._life_threshold():
            p += 2
        return p

    def toughness_of(self, perm):
        base = perm.base_t if perm.is_token else perm.card.toughness
        t = base + perm.counters
        if perm.card is not self.commander:
            if self.has("Elesh Norn, Grand Cenobite") \
                    and perm.card.name != "Elesh Norn, Grand Cenobite":
                t += 2
            if self.has("Lyra Dawnbringer") and self.is_angel(perm) \
                    and perm.card.name != "Lyra Dawnbringer":
                t += 1
        if self.has("Righteous Valkyrie") and self._life_threshold():
            t += 2
        return t

    def lifelink_of(self, perm):
        if perm.card.lifelink:
            return True
        return (self.has("Lyra Dawnbringer") and self.is_angel(perm)
                and perm.card.name != "Lyra Dawnbringer")

    def _life_threshold(self):
        # "As long as you have at least 7 life more than your starting life
        # total, creatures you control get +2/+2." Righteous Valkyrie's own
        # power_of call reads this too, which is correct: she pumps herself.
        return self.your_life >= self.cfg.get("starting_life", 40) + 7

    def play_card_trigger(self, card):
        """`engine.play_land` calls this unconditionally on every land played
        (it is Rendmaw's "2+ card types -> Bird" hook there). No land in this
        list has an ETB effect worth modelling, so it is a no-op here."""
        return

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
        self.m["drain_damage"] += amount
        if self.damage_by_turn:
            self.damage_by_turn[-1] += amount
        n = max(1, len(OPP.living(self)))
        OPP.damage_each(self, amount / n) if each else OPP.damage_single(self, amount)

    # -- tokens ------------------------------------------------------------

    def make_permanent(self, card, sick=True, tapped=False, is_token=False,
                       counters=0):
        perm = Permanent(card=card, sick=sick, tapped=tapped,
                         is_token=is_token, counters=counters,
                         base_p=card.power, base_t=card.toughness)
        self.board.append(perm)
        return perm

    def make_spirit_tokens(self, n=1):
        for _ in range(n):
            tok = Card(name="Spirit token", types=frozenset({"Creature"}),
                       power=1, toughness=1, flying=True)
            self.make_permanent(tok, sick=True, is_token=True)
            self.m["spirit_tokens_made"] += 1

    def make_angel_tokens(self, n=1, vigilance=True):
        """4/4 white Angel(/Warrior) tokens with flying — Resplendent Angel,
        Speaker of the Heavens, and Emeria's Call all make this exact body.
        Tagged "angel" so Righteous Valkyrie / Giada / Youthful Valkyrie /
        Bishop of Wings see it enter, same as a real Angel card would."""
        for _ in range(n):
            p, t = ANGEL_TOKEN_STATS
            tok = Card(name="Angel token", types=frozenset({"Creature"}),
                       power=p, toughness=t, flying=True, tags=frozenset({"angel"}))
            counters = 0
            if self.has("Giada, Font of Hope"):
                counters = sum(1 for q in self.board if self.is_angel(q))
            perm = self.make_permanent(tok, sick=True, is_token=True,
                                       counters=counters)
            self.m["angel_tokens_made"] += 1
            self.angel_entered(perm)

    # -- death / sacrifice ---------------------------------------------------

    def on_creature_death(self, n=1, perm=None):
        """Fired for EVERY creature death — combat, removal, wipes (via
        `opponents.destroy` / `resolve_own_wipe`, which both check
        `hasattr(g, "on_creature_death")`) and voluntary sacrifice (via
        `sacrifice()` below). `perm` is the permanent that died, when known."""
        for _ in range(n):
            if self.has("Blood Artist"):
                OPP.damage_single(self, 1)
                self.m["damage"] += 1
                self.m["drain_damage"] += 1
                self.your_life += 1
            if self.has("Zulaport Cutthroat"):
                k = len(OPP.living(self))
                OPP.damage_each(self, 1)
                self.m["damage"] += k
                self.m["drain_damage"] += k
                self.your_life += 1
            nontoken = perm is not None and not perm.is_token
            if nontoken and self.has("Midnight Reaper"):
                self.your_life -= 1
                self.draw(1)
            # "ANOTHER nontoken creature" -- Grim Haruspex does not see its
            # own death.
            if nontoken and self.count("Grim Haruspex") and \
                    not (perm.card.name == "Grim Haruspex"):
                self.draw(1)
            if perm is not None and self.has("Dark Prophecy"):
                self.draw(1)
                self.your_life -= 1
            if perm is not None and self.count("Pitiless Plunderer") and \
                    perm.card.name != "Pitiless Plunderer":
                self.treasures += 1
                self.m["treasures_made"] += 1
            if perm is not None and self.count("Requiem Angel") and \
                    perm.card.name != "Requiem Angel" and \
                    perm.card.name != "Spirit token":
                self.make_spirit_tokens(1)
            if perm is not None and perm.card.tags and "angel" in perm.card.tags \
                    and self.has("Bishop of Wings"):
                self.make_spirit_tokens(1)
            if nontoken and self.has("Voldaren Bloodcaster"):
                self.blood += 1
                self.m["blood_made"] += 1

    def sacrifice(self, perm, to_shilgengar=False):
        """A voluntary sacrifice — Viscera Seer, Cartel Aristocrat, Vampiric
        Rites, Skullclamp's death, or Shilgengar's own ability. Distinct from
        `opponents.destroy`, which is the pod answering something."""
        self.board.remove(perm)
        if not perm.is_token:
            self.graveyard.append(perm.card)
        self.m["creatures_sacrificed"] += 1
        if to_shilgengar:
            amt = self.toughness_of(perm) if self.is_angel(perm) else 1
            self.blood += amt
            self.m["blood_made"] += amt
        self.on_creature_death(1, perm)

    def aristocrats_step(self):
        """Once a turn: feed spare TOKENS (never real cards, never the 4/4
        Angel tokens — see the module docstring) to whatever outlet is live,
        preferring Shilgengar so the Blood counts toward the ultimate."""
        payoff = any(self.has(n) for n in (
            "Blood Artist", "Zulaport Cutthroat", "Midnight Reaper",
            "Grim Haruspex", "Dark Prophecy", "Pitiless Plunderer",
            "Requiem Angel", "Voldaren Bloodcaster")) or self.commander_cast
        if not payoff:
            return
        fodder = [p for p in self.board if p.is_token and p.card.is_creature
                 and not p.sick and self.power_of(p) <= 1]
        free_outlet = self.has("Viscera Seer") or self.has("Cartel Aristocrat") \
            or self.commander_cast
        for p in fodder[:3]:
            if not free_outlet:
                break
            self.sacrifice(p, to_shilgengar=self.commander_cast)
        # Vampiric Rites: paid outlet, worth using on whatever fodder is left
        # even without a payoff on board, since it draws a card on its own.
        if self.has("Vampiric Rites"):
            leftover = [p for p in self.board if p.is_token and p.card.is_creature
                       and not p.sick and self.power_of(p) <= 1]
            for p in leftover[:2]:
                units = available_mana(self)
                pay = can_pay({"gen": 1, "B": 1}, units)
                if pay is None:
                    break
                spend(self, pay, units)
                self.m["mana_spent"] += 2
                self.your_life += 1
                self.draw(1)
                self.sacrifice(p, to_shilgengar=False)

    def shilgengar_ultimate(self):
        """{W/B}{W/B}{W/B}, sac 6 Blood: mass-reanimate the graveyard.

        Hybrid pips modelled as 3 generic — this deck floods WB mana anyway,
        so the simplification almost never changes whether it is affordable.
        """
        if not self.commander_cast or self.blood < 6:
            return
        pool = [c for c in self.graveyard if c.is_creature]
        if not pool:
            return
        units = available_mana(self)
        pay = can_pay({"gen": 3}, units)
        if pay is None:
            return
        spend(self, pay, units)
        self.m["mana_spent"] += 3
        self.blood -= 6
        self.m["blood_spent"] += 6
        for card in pool:
            self.graveyard.remove(card)
            perm = self.make_permanent(card, sick=True)
            if self.is_angel(perm):
                self.angel_entered(perm)
        self.m["shilgengar_ults"] += 1
        self.m["shilgengar_reanimated"] += len(pool)

    # -- lifegain / Angel triggers -------------------------------------------

    def gain_life(self, amount):
        if amount <= 0:
            return
        self.your_life += amount
        self.life_gained_this_turn += amount
        self.m["life_gained"] += amount
        self.m["lifegain_triggers"] += 1
        if self.has("Archangel of Thune"):
            for p in self.board:
                if p.card.is_creature:
                    p.counters += 1

    def angel_entered(self, perm):
        """An Angel (or, for Righteous Valkyrie, a Cleric) entered under your
        control. `perm` is the permanent that just entered."""
        tags = perm.card.tags
        is_payoff_target = "angel" in tags or "cleric" in tags
        if is_payoff_target and self.has("Righteous Valkyrie") \
                and perm.card.name != "Righteous Valkyrie":
            self.gain_life(self.toughness_of(perm))
        if "angel" in tags and self.has("Bishop of Wings"):
            self.gain_life(4)
        if "angel" in tags and self.has("Youthful Valkyrie") \
                and perm.card.name != "Youthful Valkyrie":
            for p in self.board:
                if p.card.name == "Youthful Valkyrie":
                    p.counters += 1

    def creature_entered(self, perm):
        if self.is_angel(perm) or "cleric" in perm.card.tags:
            self.angel_entered(perm)

    # -- casting / ETB scripts ------------------------------------------------

    def resolve(self, card):
        self.m["mana_spent"] += 0  # spent already at the call site
        self.m["cards_drawn"] += 0
        if card.name in self.cfg.get("watch", ()):
            self.m["cast_test_card"] = 1
            self.m["test_card_turn"] = min(self.m["test_card_turn"], self.turn)

        if "wipe" in card.tags:
            OPP.resolve_own_wipe(self, spare_own="onesided" in card.tags)

        if card.script == "emeria_call":
            self.make_angel_tokens(2)

        if not card.is_permanent:
            self.graveyard.append(card)
            return

        tapped = bool(card.tapped)   # Marble Diamond: "enters tapped"
        perm = self.make_permanent(card, sick=not card.haste, tapped=tapped)

        if card.script == "massacre_wurm":
            # ETB "-2/-2 to opponents' creatures" is a per-permanent effect on
            # a board this model represents as a float. Approximated as a
            # cull proportional to the float, with the death-drain paid on
            # the creatures assumed killed — a wrath-adjacent effect, not a
            # precise one. Said out loud rather than guessed silently.
            share = self.cfg.get("wurm_kill_share", 0.35)
            for o in OPP.living(self):
                killed = min(o.creatures, o.creatures * share + 1)
                o.creatures = max(0.0, o.creatures - killed)
                if killed > 0:
                    o.life -= 2.0 * killed
            OPP._check_eliminations(self)

        if perm.card.is_creature:
            self.creature_entered(perm)
        if card.name == "Sun Titan":
            # "Whenever this creature enters OR ATTACKS" -- the ETB half; the
            # attack half is in combat().
            self._sun_titan_reanimate()
        return perm

    # -- casting and turn loop -----------------------------------------------

    def main_phase(self):
        while True:
            units = available_mana(self)
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
                    continue

            options = []
            for c in self.hand:
                if c.is_land:
                    continue
                if "wipe" in c.tags and not OPP.should_cast_own_wipe(self):
                    continue
                pay = can_pay(c.cost, units)
                if pay is not None:
                    options.append((c, pay))
            if not options:
                break
            card, pay = max(options, key=lambda it: (it[0].priority, it[0].mv))
            spend(self, pay, units)
            self.m["mana_spent"] += len(pay)
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

    def activations(self):
        units = available_mana(self)
        # Skullclamp — restricted to TOKEN fodder; see the module docstring.
        if self.has("Skullclamp"):
            for _ in range(3):
                fodder = [p for p in self.board if p.is_token
                         and p.card.is_creature and self.toughness_of(p) == 1]
                units = available_mana(self)
                pay = can_pay({"gen": 1}, units)
                if not fodder or pay is None:
                    break
                spend(self, pay, units)
                self.m["mana_spent"] += 1
                self.sacrifice(fodder[0], to_shilgengar=False)
                self.draw(2)

        # Priest of Fell Rites: {T}, pay 3 life, sac itself, sorcery-speed
        # reanimate. Unearth is not modelled (a one-shot value line; scope).
        if self.count("Priest of Fell Rites") and self.your_life > 10:
            pool = [c for c in self.graveyard if c.is_creature]
            priest = next((p for p in self.board
                          if p.card.name == "Priest of Fell Rites"
                          and not p.sick), None)
            if pool and priest is not None:
                best = max(pool, key=lambda c: c.mv)
                self.graveyard.remove(best)
                self.your_life -= 3
                self.sacrifice(priest, to_shilgengar=False)
                perm = self.make_permanent(best, sick=True)
                if perm.card.is_creature:
                    self.creature_entered(perm)
                self.m["single_reanimations"] += 1

        # Wayfarer's Bauble: "{2}, {T}, Sacrifice this artifact: search for a
        # basic land, put it onto the battlefield tapped." An activated
        # ability of a permanent already in play, not an ETB -- so it is
        # handled here rather than in resolve(), a turn or more after casting
        # in the model just as it would be at a real table.
        if self.has("Wayfarer's Bauble"):
            units = available_mana(self)
            pay = can_pay({"gen": 2}, units)
            basics = [c for c in self.library if c.name in ("Swamp", "Plains")]
            bauble = next((p for p in self.board
                          if p.card.name == "Wayfarer's Bauble"), None)
            if pay is not None and basics and bauble is not None:
                spend(self, pay, units)
                self.m["mana_spent"] += 2
                self.board.remove(bauble)
                land = basics[0]
                self.library.remove(land)
                self.make_permanent(land, sick=False, tapped=True)

        self.aristocrats_step()
        self.shilgengar_ultimate()

    def combat(self):
        attackers = [p for p in self.board if p.card.is_creature
                    and not p.tapped and not p.sick]
        if not attackers:
            self.damage_by_turn.append(0.0)
            return
        # Sun Titan: "whenever this creature enters OR ATTACKS" -- the attack
        # half. The ETB half fires in resolve()/sun_titan below.
        if any(p.card.name == "Sun Titan" for p in attackers):
            self._sun_titan_reanimate()

        dmg = OPP.damage_through(self, attackers)
        for p in attackers:
            p.tapped = True
        self.m["damage"] += dmg
        self.m["combat_damage"] += dmg
        self.damage_by_turn.append(dmg)
        OPP.damage_single(self, dmg)
        for p in attackers:
            if self.lifelink_of(p):
                self.gain_life(self.power_of(p))
        if self.result is None and self.m["turn_lethal"] == 99 and not OPP.living(self):
            self.m["turn_lethal"] = self.turn

    def _sun_titan_reanimate(self):
        pool = [c for c in self.graveyard
               if c.is_permanent and float(c.mv) <= 3]
        if not pool:
            return
        best = max(pool, key=lambda c: c.mv)
        self.graveyard.remove(best)
        perm = self.make_permanent(best, sick=True)
        if perm.card.is_creature:
            self.creature_entered(perm)
        self.m["single_reanimations"] += 1

    def upkeep(self):
        if self.has("Phyrexian Arena"):
            self.draw(1)
            self.your_life -= 1
        if self.has("Black Market Connections"):
            # "Choose one or more" -- approximated as always taking Buy
            # Information (draw a card, lose 2 life), the steady-value mode,
            # rather than trying to model the turn-by-turn choice among all
            # three. Said out loud: this undercounts the card's ceiling.
            self.draw(1)
            self.your_life -= 2
        if self.has("Smothering Tithe"):
            # "whenever an opponent draws a card, they may pay {2}; if they
            # don't, you create a Treasure." Approximated as one Treasure per
            # living opponent per round and no RNG (opponents nearly always
            # have a better use for two mana early), matching how
            # `karlov.opponent_activity` sizes opponent behaviour off a flat
            # rate rather than a per-event roll.
            n = len(OPP.living(self))
            self.treasures += n
            self.m["treasures_made"] += n
        if self.has("Reya Dawnbringer"):
            pool = [c for c in self.graveyard if c.is_creature]
            if pool:
                best = max(pool, key=lambda c: c.mv)
                self.graveyard.remove(best)
                perm = self.make_permanent(best, sick=True)
                if perm.card.is_creature:
                    self.creature_entered(perm)
                self.m["single_reanimations"] += 1

    def end_step(self):
        # Resplendent Angel / Speaker of the Heavens both key off "gained 5+
        # life this turn" / "7+ over starting life", checked once here rather
        # than at every gain_life() call so a turn with several small gains is
        # counted correctly.
        if self.has("Resplendent Angel") and self.life_gained_this_turn >= 5:
            self.make_angel_tokens(1)
        if self.has("Speaker of the Heavens") and self._life_threshold():
            self.make_angel_tokens(1)

    def land_step(self):
        before = sum(1 for p in self.board if p.card.is_land)
        play_land(self)
        if sum(1 for p in self.board if p.card.is_land) > before \
                and self.has("Emeria Shepherd"):
            # Landfall: "return target nonland permanent card from your
            # graveyard to your hand; if that land is a Plains, to the
            # battlefield instead." Approximated as always to the battlefield
            # when possible, since this deck always prefers the body.
            pool = [c for c in self.graveyard if c.is_permanent and not c.is_land]
            if pool:
                best = max(pool, key=lambda c: c.mv)
                self.graveyard.remove(best)
                perm = self.make_permanent(best, sick=True)
                if perm.card.is_creature:
                    self.creature_entered(perm)
                self.m["single_reanimations"] += 1


def take_turn(g):
    g.turn += 1
    g.spells_this_turn = 0
    g.life_gained_this_turn = 0.0
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.land_drops = 1
    g.land_drops_used = 0

    g.upkeep()
    if g.result is not None:
        return
    g.draw(1)
    g.land_step()
    g.main_phase()
    if g.result is not None:
        return
    g.combat()
    g.activations()
    g.main_phase()
    if g.result is not None:
        return
    g.end_step()

    # Revel in Riches — its OWN Treasure generation is model-blind (needs
    # opponents' creatures to die as discrete events), but Treasures from
    # every other source still count toward the alternate win.
    if g.has("Revel in Riches") and g.treasures >= 10 and g.result is None:
        g.result = "win"
        g.m["turn_won"] = g.turn
        g.m["win_route"] = 2

    g.m["mana_floated"] += len(available_mana(g))
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
    g = ShilgengarGame(deck, commander, cfg, seed)
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
