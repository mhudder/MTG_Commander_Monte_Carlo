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
This engine used to sacrifice EXPENDABLE TOKENS ONLY (1/1 Spirits, never a
real card), on the grounds that feeding a live Lyra Dawnbringer to Shilgengar
was a pilot judgement call the model should not attempt. That was measured on
2026-09-07 and it starved the deck's own thesis: Spirit tokens only exist once
an Angel has already died, so `blood_made` averaged 0.10 a game and THE
SIX-BLOOD ULTIMATE FIRED ZERO TIMES IN 3,000 GAMES. The commander's defining
ability was untested rather than tested and found wanting.

`cfg["shilgengar_sac_policy"]` now defaults to "ultimate", and the old
behaviour is `"tokens"`. The new policy is NOT a judgement call — it is
arithmetic, which is why it is safe to automate:

  - "Sacrifice ANOTHER creature: create a Blood token. If you sacrificed an
    ANGEL this way, create Blood equal to ITS TOUGHNESS instead." A 5-toughness
    Angel is five sixths of the ultimate on its own.
  - The ultimate returns EACH creature card from your graveyard — INCLUDING
    the Angel you just sacrificed to pay for it. A nontoken sacrifice is a
    LOAN, not a cost.
  - `activations()` runs after `combat()`, so the bodies fed to the ability
    have already attacked this turn, and `take_turn` clears summoning sickness
    at the start of the next one. The reanimated board is sick for the
    remainder of a turn in which it had already acted.

So the line is only ever taken when it COMPLETES THE ULTIMATE THIS TURN
(`ult_plan`). Sacrificing an Angel to bank Blood across turns is a real risk
that this model still does not take, and a pilot holding five Blood and a Lyra
would sometimes take it — the engine is a floor on the ability, not a ceiling.
Two further deliberate conservatisms: the plan must leave you with at least
`shilgengar_ult_min_gain` (1) more creatures on the battlefield than it
sacrificed, so the line is never a pure shuffle, and the death triggers it
sets off (Blood Artist, Grim Haruspex, Pitiless Plunderer) are not counted as
part of the case for taking it even though they are real value.

REAL CARDS SORT AHEAD OF TOKENS AS FODDER, which is the exact reverse of the
old policy, and the reason is the loan: a nontoken creature comes back off the
ultimate and a token ceases to exist.

FINALITY COUNTERS ARE MODELLED, because without them the line loops. The
ultimate returns creatures "with a finality counter on it" — if such a
creature would die again it is EXILED instead of hitting the graveyard, so the
same Angel cannot be fed to a second ultimate. `self.finality` tracks it and
`yard_creatures()` is the filtered graveyard pool every recursion effect in
this deck reads. Without that, sac-Angel/return-Angel/repeat is an engine
that plays a card the game does not print.

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

TREASURES ARE MANA AS OF 2026-09-10 (queued item 13)
-----------------------------------------------------
They used to be a COUNTER THAT ONLY REVEL IN RICHES READ. Pitiless Plunderer,
Smothering Tithe, Black Market Connections and Wayfarer's Bauble all made them
and nothing ever spent one, so three of this deck's mana sources were scored as
though they produced no mana — and the commander's ultimate was held a
three-mana reserve (§0t measured what that reserve COSTS) that a pile of
Treasures could have paid instead. `pay()` now spends them, real mana first,
and `ult_reserve()` returns 0 when the Treasures already cover the ultimate.

READ SMOTHERING TITHE'S NUMBER WITH CARE NOW. Its approximation — one Treasure
per living opponent per round, no roll, because "opponents nearly always have a
better use for two mana early" — was written when a Treasure was inert, and it
is now three mana a turn in a model where the opponents never pay the {2}. That
assumption has gone from harmless to load-bearing and it is the first thing to
suspect if this card's row looks too good. `treasures_as_mana=False` restores
the old behaviour exactly.

WIN CONDITIONS
--------------
  1. Combat, drain, and the mass-reanimation swing (the default plan).
  2. Revel in Riches — 10 or more Treasures (its OWN generation is
     model-blind, but Treasures from Smothering Tithe / Black Market
     Connections / Pitiless Plunderer / Wayfarer's Bauble still count).
     NOTE THE TENSION with the change above: a Treasure spent on mana is a
     Treasure not counted toward the ten. Resolving it greedily in favour of
     mana cost Revel in Riches 0.0056 win rate against its own ±0.0021 bar —
     the only row in the regenerated table to move outside its own bar. The
     pilot's fix (hoard while Revel is out) was implemented and MEASURED at
     -0.0013, p=0.16: it does not pay, because the deck makes 1.9 Treasures a
     game and ten is out of reach. Greedy is the default and Revel's lower row
     is its honest value. `treasure_hoard=True` keeps the seam. §0z6.
"""

from __future__ import annotations

import random

from edhmc.engine import (Board, Card, Permanent, can_pay, available_mana,
                          spend, play_land, engine_cfg)
from edhmc import opponents as OPP

ANGEL_TOKEN_STATS = (4, 4)   # every Angel token this deck makes is a 4/4 flier


class ShilgengarGame:
    def __init__(self, deck, commander, cfg, seed):
        # A PRIVATE copy: the cfg.setdefault block below stamps this
        # engine's defaults, and doing that to the CALLER'S dict let the
        # first engine constructed decide them for every later one.
        # See engine.engine_cfg.
        self.cfg = cfg = engine_cfg(cfg)
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
        # Cards carrying a finality counter, by id(). A set of Card objects
        # would be wrong twice over: Card is an unfrozen dataclass and so
        # unhashable, and its __eq__ is field-wise, which would make one
        # marked Swamp mark every Swamp. Every card is referenced by the
        # library, hand, graveyard or board for the whole game, so no id is
        # recycled underneath this.
        self.finality: set[int] = set()

        cfg.setdefault("shroud_sources", ())
        cfg.setdefault("protection_cards",
                       ("Flawless Maneuver", "Teferi's Protection"))
        # See "THE SACRIFICE POLICY, SAID OUT LOUD" in the module docstring.
        cfg.setdefault("shilgengar_sac_policy", "ultimate")   # or "tokens"
        cfg.setdefault("shilgengar_ult_min_gain", 1)
        cfg.setdefault("shilgengar_ult_reserve", 3)
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
            "angels_fed": 0, "cards_fed": 0, "finality_marked": 0,
            "shilgengar_ults": 0, "shilgengar_reanimated": 0,
            "single_reanimations": 0, "treasures_made": 0,
            # Queued item 13: Treasures were made and never spent. Registered
            # here, not created on first use -- `self.m` is a plain dict, so an
            # unregistered key is a KeyError in whichever worker first spends
            # a Treasure.
            "treasures_spent": 0,
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

    def blood_yield(self, perm):
        """Blood from feeding this permanent to Shilgengar's first ability.

        "...create a number of Blood tokens equal to ITS TOUGHNESS instead" —
        toughness as it stands on the battlefield, so Lyra Dawnbringer's +1/+1
        to other Angels, Elesh Norn's +2/+2 and Righteous Valkyrie's +2/+2 all
        raise the Blood an Angel is worth. That is the rules answer and not a
        modelling choice: the ability reads the creature's toughness as it
        last existed on the battlefield.
        """
        return self.toughness_of(perm) if self.is_angel(perm) else 1

    def yard_creatures(self):
        """Creature cards in the graveyard that recursion can actually return.

        A card returned by the ultimate comes back WITH A FINALITY COUNTER, so
        the next time it would die it is exiled instead. This engine leaves it
        in the graveyard list and filters it here, which is behaviourally the
        same thing for this deck — nothing in the list reads a graveyard COUNT,
        and every effect that returns a creature (the ultimate, Reya
        Dawnbringer, Priest of Fell Rites, Sun Titan, Emeria Shepherd) reads
        this pool.
        """
        return [c for c in self.graveyard
                if c.is_creature and id(c) not in self.finality]

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
        # BOUNDED: record what could have mattered, not what was asked for.
        # The divisor is the FULL POD, not the living count -- see OPP.pod_size.
        n = OPP.pod_size(self)
        dealt = (OPP.damage_each(self, amount / n) if each
                 else OPP.damage_single(self, amount))
        self.m["damage"] += dealt
        self.m["drain_damage"] += dealt
        if self.damage_by_turn:
            self.damage_by_turn[-1] += dealt

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
                dealt = OPP.damage_single(self, 1)
                self.m["damage"] += dealt
                self.m["drain_damage"] += dealt
                self.your_life += 1
            if self.has("Zulaport Cutthroat"):
                dealt = OPP.damage_each(self, 1)
                self.m["damage"] += dealt
                self.m["drain_damage"] += dealt
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
                # Treasures pay for this too -- queued item 13. A Treasure is
                # any colour, so it covers the {B} pip as well as the {1}.
                if not self.pay({"gen": 1, "B": 1}, count_mana_spent=2):
                    break
                self.your_life += 1
                self.draw(1)
                self.sacrifice(p, to_shilgengar=False)

    def ult_fodder(self):
        """Creatures that may legally be fed to Shilgengar, best first.

        "Sacrifice ANOTHER creature" — never the commander itself. Real cards
        sort ahead of tokens because the ultimate returns a card and does not
        return a token, and within each group the most Blood per body sorts
        first so the plan spends as few bodies as it can.
        """
        return sorted(
            (p for p in self.board
             if p.card.is_creature and p.card is not self.commander),
            key=lambda p: (p.is_token, -self.blood_yield(p)))

    def ult_plan(self):
        """The sacrifices that would fire the ultimate THIS TURN, or None.

        `[]` means the Blood is already banked and nothing needs to die. See
        the module docstring for why this is arithmetic rather than a pilot's
        judgement call, and for the two conservatisms in it.
        """
        if self.cfg.get("shilgengar_sac_policy", "ultimate") != "ultimate":
            return None
        if not self.commander_cast:
            return None
        if not self.yard_creatures() and self.blood >= 6:
            return None          # nothing to return; shilgengar_ultimate agrees
        need = 6 - self.blood
        if need <= 0:
            return []
        chosen, gained = [], 0
        for p in self.ult_fodder():
            if gained >= need:
                break
            chosen.append(p)
            gained += self.blood_yield(p)
        if gained < need:
            return None
        # The line must be a real gain and not a shuffle: count what the
        # ultimate would put back against what this plan kills to pay for it.
        # Tokens are on the wrong side of that subtraction by construction —
        # they die and do not come back — which is what makes an Angel the
        # right fodder and a Spirit token the wrong one.
        returning = len(self.yard_creatures()) + sum(1 for p in chosen
                                                    if not p.is_token)
        if returning - len(chosen) < self.cfg.get("shilgengar_ult_min_gain", 1):
            return None
        return chosen

    # -- Treasures as mana (queued item 13) --------------------------------
    #
    # "SACRIFICE THIS ARTIFACT: ADD ONE MANA OF ANY COLOR." Until 2026-09-10
    # this deck's Treasures were a COUNTER THAT ONLY REVEL IN RICHES READ:
    # they accumulated from Pitiless Plunderer, Smothering Tithe, Black Market
    # Connections and Wayfarer's Bauble, and nothing ever spent one. So the
    # three Treasure-makers were scored as though their Treasures did nothing
    # but count toward a ten-Treasure alternate win, and the commander's
    # ultimate was held a three-mana reserve it could often have paid out of
    # the pile instead.
    #
    # A Treasure is ANY COLOUR and it is a sacrifice, not a tap, so it is
    # available the turn it arrives and cannot be Stone Rained. It is modelled
    # as a unit of any colour appended AFTER the real mana, which is what lets
    # `pay()` below tell the two apart -- the same device
    # `azusa.main_phase` uses for Castle Garenbrig's restricted pool.
    #
    # `treasures_as_mana=False` restores the pre-2026-09-10 behaviour and
    # reproduces every shilgengar number published before that date.
    ANY = frozenset({"W", "U", "B", "R", "G", "C"})

    def spendable_treasures(self):
        """How many Treasures the pilot is willing to spend as mana.

        NOT simply `self.treasures`, and the reason was MEASURED rather than
        anticipated. When Treasures first became mana (queued item 13) the
        engine spent them greedily, and the regenerated table moved exactly one
        row beyond its own error bar: **Revel in Riches +0.0081 -> +0.0025**,
        a 0.0056 drop against a +-0.0021 bar. The mechanism is not subtle --
        "at the beginning of your upkeep, if you control ten or more
        Treasures, you win the game", and the engine was cracking them for
        mana before the count could ever reach ten.

        THE OBVIOUS FIX WAS IMPLEMENTED, MEASURED, AND IS NOT SHIPPED. The
        pilot's answer is "with Revel in Riches out, Treasures are a win
        condition and not mana -- hoard them until the tenth". That is
        `treasure_hoard=True`, it is implemented below, and at N=3,000 paired
        it is **-0.0013 [-0.0033, +0.0003], p=0.16** against spending them
        greedily. It does not pay, and the reason is arithmetic: this deck
        makes **1.9 Treasures a game**, so ten is reached almost only when
        Smothering Tithe lands early, while the mana forgone is spent on every
        turn of every game. Revel's alternate win is 0.5% of games either way.

        So the DEFAULT IS GREEDY, and Revel in Riches' row falling from +0.0081
        to +0.0025 is not damage to be repaired -- it is the honest new value
        of a card whose resource now has a better use. The project's rule is to
        follow win rate, and the win rate declined to endorse the pilot's
        instinct. `treasure_hoard=True` is kept, because a future list with
        more Treasure generation would flip this and the seam should already
        exist when it does.
        """
        if not self.cfg.get("treasures_as_mana", True):
            return 0
        if (self.cfg.get("treasure_hoard", False)
                and self.has("Revel in Riches") and self.treasures < 10):
            return 0
        return self.treasures

    def pay(self, cost, count_mana_spent=None):
        """Pay `cost` from the battlefield, then from Treasures.

        Returns True if it was paid. REAL MANA FIRST and Treasures only for
        what is left: a Treasure is a one-shot resource and a land is not, so
        spending the land first is strictly better and is what a pilot does.
        `can_pay` walks the pool in order and prefers the least flexible
        source, so appending the any-colour Treasures at the END gets this for
        free rather than by a special case.
        """
        units = available_mana(self)
        n_real = len(units)
        n_treasure = self.spendable_treasures()
        pool = units + [self.ANY] * n_treasure
        idx = can_pay(cost, pool)
        if idx is None:
            return False
        real = [i for i in idx if i < n_real]
        used = len(idx) - len(real)
        spend(self, real, units)
        if used:
            self.treasures -= used
            self.m["treasures_spent"] += used
        self.m["mana_spent"] += (len(idx) if count_mana_spent is None
                                 else count_mana_spent)
        return True

    def can_afford(self, cost):
        """Affordability INCLUDING Treasures, without spending anything."""
        units = available_mana(self)
        return can_pay(cost, units
                       + [self.ANY] * self.spendable_treasures()) is not None

    def ult_reserve(self):
        """Mana to hold back through the main phase for the ultimate.

        Without this the ability is unaffordable in practice and the measured
        answer is a fact about the casting policy, not about the card:
        `main_phase` is greedy and `activations()` runs after it, so every
        point of mana is already spent by the time the ultimate is checked.
        Nothing is held back on a turn where the line is not live, so this
        costs the deck nothing on the turns it does not apply.
        """
        if self.ult_plan() is None:
            return 0
        # NOTHING NEEDS RESERVING IF THE TREASURES ALREADY COVER IT (queued
        # item 13). This is the half of that item with a real behavioural
        # consequence: §0t measured what holding three mana back COSTS, and
        # the answer was a fact about a policy that a pile of Treasures makes
        # unnecessary. A pilot sitting on three Treasures spends their whole
        # main phase and cracks the Treasures for the ultimate.
        if self.can_afford({"gen": 3}) and self.treasures >= 3:
            return 0
        return self.cfg.get("shilgengar_ult_reserve", 3)

    def ultimate_line(self):
        """Take the whole sac-for-Blood-then-reanimate line, if it is there.

        THE MANA IS CHECKED BEFORE ANYTHING DIES. `shilgengar_ultimate` also
        checks it and returns early, which would otherwise leave the Angels
        sacrificed and the ability uncast — paying the cost for none of the
        effect.
        """
        for _ in range(2):        # a second one needs six more Blood; rare
            plan = self.ult_plan()
            if plan is None:
                break
            if not self.can_afford({"gen": 3}):
                break
            for p in plan:
                if p not in self.board:
                    continue      # a death trigger got to it first
                if self.is_angel(p):
                    self.m["angels_fed"] += 1
                if not p.is_token:
                    self.m["cards_fed"] += 1
                self.sacrifice(p, to_shilgengar=True)
            before = self.m["shilgengar_ults"]
            self.shilgengar_ultimate()
            if self.m["shilgengar_ults"] == before:
                break

    def shilgengar_ultimate(self):
        """{W/B}{W/B}{W/B}, sac 6 Blood: mass-reanimate the graveyard.

        Hybrid pips modelled as 3 generic — this deck floods WB mana anyway,
        so the simplification almost never changes whether it is affordable.
        """
        if not self.commander_cast or self.blood < 6:
            return
        pool = self.yard_creatures()
        if not pool:
            return
        # Treasures may pay for this -- see pay() and queued item 13.
        if not self.pay({"gen": 3}, count_mana_spent=3):
            return
        self.blood -= 6
        self.m["blood_spent"] += 6
        # Out of the graveyard FIRST, then resolve the ETB triggers. "Return
        # EACH creature card from your graveyard to the battlefield" is one
        # action, so every card has left the graveyard before a trigger goes
        # on the stack. Nothing in `angel_entered` touches the graveyard
        # today, so this is behaviour-neutral -- VERIFIED by regenerating this
        # deck's whole ablation table and diffing it byte for byte, not
        # argued -- but the interleaved form is the shape that crashed the
        # Azusa engine's Genesis Wave on 2026-09-07.
        for card in pool:
            self.graveyard.remove(card)
        for card in pool:
            perm = self.make_permanent(card, sick=True)
            # "...with a finality counter on it." Marked here, enforced in
            # yard_creatures(): this card can never be returned again.
            self.finality.add(id(card))
            self.m["finality_marked"] += 1
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
            OPP.resolve_own_wipe(self, spare_own="onesided" in card.tags,
                                 card=card)

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

    def main_phase(self, reserve=0):
        """reserve: mana left unspent for Shilgengar's ultimate in
        `activations()`, which runs after this phase and after combat. Same
        mechanism as `lorehold.main_phase`'s miracle reserve, and for the same
        reason: a greedy main phase spends the mana an after-combat ability
        needs, and the ability then reads as a bad card rather than as one the
        casting policy never let itself use.

        `ult_reserve()` is read once, BEFORE the phase, so a plan that only
        becomes live because of a creature cast during this phase does not get
        its mana held back this turn. That understates the line slightly and
        is the safe direction: it can only ever fail to take the ultimate.
        """
        while True:
            units = available_mana(self)
            # TREASURES ARE PART OF THE POOL (queued item 13). Appended after
            # the real mana so `can_pay` reaches for a land first and a
            # Treasure only for what the lands cannot cover, and so the index
            # split below can tell which was which.
            n_real = len(units)
            n_treasure = self.spendable_treasures()
            pool = units + [self.ANY] * n_treasure
            if not self.commander_cast:
                ccost = dict(self.commander.cost)
                ccost["gen"] = ccost.get("gen", 0) + self.commander_tax
                if self.pay(ccost, count_mana_spent=sum(ccost.values())):
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
                pay = can_pay(c.cost, pool)
                # THE RESERVE COUNTS THE WHOLE POOL, Treasures included: what
                # it exists to protect is the three mana the ultimate needs
                # after combat, and a Treasure pays that as well as a land
                # does. Reading it off `units` alone would hold lands back
                # while a pile of Treasures sat unspent beside them, which is
                # the policy artefact §0t warned about rather than a cost.
                if pay is not None and len(pool) - len(pay) >= reserve:
                    options.append((c, pay))
            if not options:
                break
            card, pay = max(options, key=lambda it: (it[0].priority, it[0].mv))
            real = [i for i in pay if i < n_real]
            used = len(pay) - len(real)
            spend(self, real, units)
            if used:
                self.treasures -= used
                self.m["treasures_spent"] += used
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
                if not fodder or not self.pay({"gen": 1}, count_mana_spent=1):
                    break
                self.sacrifice(fodder[0], to_shilgengar=False)
                self.draw(2)

        # Priest of Fell Rites: {T}, pay 3 life, sac itself, sorcery-speed
        # reanimate. Unearth is not modelled (a one-shot value line; scope).
        if self.count("Priest of Fell Rites") and self.your_life > 10:
            pool = self.yard_creatures()
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
            basics = [c for c in self.library if c.name in ("Swamp", "Plains")]
            bauble = next((p for p in self.board
                          if p.card.name == "Wayfarer's Bauble"), None)
            if basics and bauble is not None and self.pay({"gen": 2},
                                                          count_mana_spent=2):
                self.board.remove(bauble)
                land = basics[0]
                self.library.remove(land)
                self.make_permanent(land, sick=False, tapped=True)

        self.aristocrats_step()
        self.ultimate_line()
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

        for p in attackers:
            p.tapped = True
        # One attack at the whole pod; `dmg` comes back bounded at what could
        # have mattered. Lifelink below still reads `power_of`, not this.
        dmg = OPP.combat_damage(self, attackers)
        self.m["damage"] += dmg
        self.m["combat_damage"] += dmg
        self.damage_by_turn.append(dmg)
        for p in attackers:
            if self.lifelink_of(p):
                self.gain_life(self.power_of(p))
        if self.result is None and self.m["turn_lethal"] == 99 and not OPP.living(self):
            self.m["turn_lethal"] = self.turn

    def _sun_titan_reanimate(self):
        pool = [c for c in self.graveyard
               if c.is_permanent and float(c.mv) <= 3
               and id(c) not in self.finality]
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
            pool = self.yard_creatures()
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
            pool = [c for c in self.graveyard if c.is_permanent and not c.is_land
                   and id(c) not in self.finality]
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
    g.main_phase(reserve=g.ult_reserve())
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
    # The BATTLEFIELD question, not the type line: a Planeswalker Grist and
    # an Impending Overlord are not creatures and their power is not board
    # power. Same predicate the wipes use; `pod_reads_battlefield_creatures`
    # restores the old reading here too.
    out["final_board_power"] = sum(g.power_of(p) for p in g.board
                                   if OPP.is_creature_now(g, p))
    out["test_card_resolved"] = 1 if (out["cast_test_card"] and
                                      not out["test_card_answered"]) else 0
    return out
