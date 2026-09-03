"""
edhmc.karlov — a lifegain/drain engine for Karlov of the Ghost Council.

    Karlov of the Ghost Council  {1}{W}{B}  2/2
      Whenever you gain life, put two +1/+1 counters on Karlov.
      Remove six +1/+1 counters: exile target creature.

THE CENTRAL MODELLING FACT
--------------------------
This deck counts TRIGGERS, not life. Gaining 1 life six times is six Karlov
triggers, twelve counters and six Voice of the Blessed counters; gaining 6 life
once is one trigger. Every payoff in the deck keys off the event, so the engine
tracks `gain_life()` calls as first-class and routes every one through a single
`on_lifegain` handler.

WHY THE OPPONENT MODEL MATTERS MORE HERE
----------------------------------------
The soul sisters (Soul Warden, Soul's Attendant, Suture Priest, Auriok Champion,
Daxos) trigger on EVERY creature entering, including opponents'. Authority of
the Consuls, Kambal and Sunscorch Regent trigger on opponents' actions outright.
So a large share of this deck's engine is driven by the opponents' board and
spell development, which `opponents.py` already models — opponent creature
growth per turn becomes a direct input rather than background detail.

WIN CONDITIONS (four, and they are the deck's identity)
-------------------------------------------------------
  1. Combat and incremental drain (the slow default).
  2. Exquisite Blood + any of Sanguine Bond / Vito / Vizkopa Guildmage — an
     infinite loop. Modelled as an immediate win when both halves are out.
  3. Aetherflux Reservoir — pay 50 life, deal 50 to a player.
  4. Felidar Sovereign — win at upkeep with 40 or more life.
"""

from __future__ import annotations

import random

from edhmc.engine import Card, Permanent, can_pay, available_mana, spend, play_land
from edhmc import opponents as OPP

COMBO_A = "Exquisite Blood"
COMBO_B = ("Sanguine Bond", "Vito, Thorn of the Dusk Rose", "Vizkopa Guildmage")


class KarlovGame:
    def __init__(self, deck, commander, cfg, seed):
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.library = list(deck)
        self.rng.shuffle(self.library)
        self.hand: list[Card] = []
        self.board: list[Permanent] = []
        self.graveyard: list[Card] = []
        self.commander = commander
        self.commander_cast = False
        self.commander_tax = 0
        self.karlov_counters = 0
        self.turn = 0
        self.land_drops = 1
        self.land_drops_used = 0
        self.spells_this_turn = 0
        self.made_token_this_turn = False
        self.beast_active = False
        self.stampede_bonus = 0
        self.creature_died_this_turn = False
        self.treasures = 0

        cfg.setdefault("shroud_sources",
                       ("Lightning Greaves", "Swiftfoot Boots",
                        "Whispersilk Cloak", "Mother of Runes"))
        cfg.setdefault("protection_cards", ("Mother of Runes",))
        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = {
            "damage": 0.0, "drain_damage": 0.0, "combat_damage": 0.0,
            "lifegain_triggers": 0, "life_gained": 0.0,
            "karlov_counters": 0, "cards_drawn": 0, "spells_cast": 0,
            "mana_spent": 0, "mana_floated": 0, "stranded_mv": 0,
            "turn_lethal": 99, "turn_won": 99, "combo_assembled": 0,
            "removal_eaten": 0, "ae_removal_eaten": 0, "wipes_suffered": 0,
            "countered": 0, "protected": 0, "win_route": 0,
            "cast_test_card": 0, "test_card_turn": 99,
            "test_card_answered": 0, "test_card_removed": 0,
            "test_card_countered": 0,
        }
        self.damage_by_turn = []

    # -- helpers -------------------------------------------------------------

    def has(self, name):
        return any(p.card.name == name for p in self.board)

    def count(self, name):
        return sum(1 for p in self.board if p.card.name == name)

    def power_of(self, perm):
        base = perm.card.power + perm.counters
        if perm.card is self.commander:
            base += self.karlov_counters
        return base

    def toughness_of(self, perm):
        return perm.card.toughness + perm.counters

    def play_card_trigger(self, card):
        return

    def make_tokens(self, n, p, t, subtype="", tapped=False):
        for _ in range(int(n)):
            tok = Card(name=f"{subtype or 'Token'} token",
                       types=frozenset({"Creature"}), power=p, toughness=t)
            self.board.append(Permanent(card=tok, tapped=tapped, sick=True,
                                        is_token=True))
            creature_entered(self, mine=True)

    def draw(self, n=1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())
                self.m["cards_drawn"] += 1

    def on_creature_death(self, n=1):
        self.creature_died_this_turn = True
        for _ in range(n):
            if self.has("Blood Artist"):
                drain(self, 1)
            if self.has("Elas il-Kor, Sadistic Pilgrim"):
                drain(self, 1)
            if self.has("Daxos, Blessed by the Sun"):
                gain_life(self, 1)
            if self.has("Syr Konrad, the Grim"):
                OPP.damage_each(self, 1)
                self.m["damage"] += 3

    def deal_pod_damage(self, amount, each=True):
        if amount <= 0:
            return
        self.m["damage"] += amount
        self.m["drain_damage"] += amount
        if self.damage_by_turn:
            self.damage_by_turn[-1] += amount
        n = max(1, len(OPP.living(self)))
        OPP.damage_each(self, amount / n) if each else OPP.damage_single(self, amount)

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



# ---------------------------------------------------------------------------
# The lifegain trigger — the heart of the deck
# ---------------------------------------------------------------------------

def gain_life(g, amount, _depth=0):
    """One lifegain EVENT. Amount matters for some payoffs, the event itself
    matters for more of them."""
    if amount <= 0 or _depth > 3:
        return
    g.your_life += amount
    g.m["life_gained"] += amount
    g.m["lifegain_triggers"] += 1

    if g.commander_cast:
        g.karlov_counters += 2
        g.m["karlov_counters"] = max(g.m["karlov_counters"], g.karlov_counters)

    for p in g.board:
        n = p.card.name
        if n == "Voice of the Blessed":
            p.counters += 1
        elif n == "Archangel of Thune":
            for q in g.board:
                if q.card.is_creature:
                    q.counters += 1
        elif n == "Cliffhaven Vampire":
            OPP.damage_single(g, amount)
            g.m["damage"] += amount
        elif n == "Marauding Blight-Priest":
            OPP.damage_each(g, 1)
            g.m["damage"] += len(OPP.living(g))
        elif n in ("Sanguine Bond", "Vito, Thorn of the Dusk Rose"):
            OPP.damage_single(g, amount)
            g.m["damage"] += amount
            # Exquisite Blood sees that loss of life and gains it back: loop.
            if g.has(COMBO_A) and g.result is None:
                g.result = "win"
                g.m["turn_won"] = g.turn
                g.m["win_route"] = 2
                return
    if g.has("Well of Lost Dreams"):
        g.draw(min(2, int(amount)))
    if g.has("Dawn of Hope"):
        g.draw(1) if g.rng.random() < 0.5 else None


def drain(g, amount):
    """Lose-life-and-gain-life: two events in one, and both matter."""
    OPP.damage_single(g, amount)
    g.m["damage"] += amount
    g.m["drain_damage"] += amount
    gain_life(g, amount)


def creature_entered(g, mine=True):
    """Soul sisters see EVERY creature enter, including the opponents'."""
    for _ in range(g.count("Soul Warden") + g.count("Soul's Attendant")
                   + g.count("Auriok Champion") + g.count("Daxos, Blessed by the Sun")):
        gain_life(g, 1)
    if g.has("Suture Priest"):
        gain_life(g, 1) if mine else drain(g, 1)
    if mine and g.has("Elas il-Kor, Sadistic Pilgrim"):
        gain_life(g, 1)
    if not mine and g.has("Authority of the Consuls"):
        gain_life(g, 1)


def opponent_activity(g):
    """Opponents' creatures entering and spells cast, which this deck taxes."""
    per_opp = g.cfg.get("opp_creatures_per_turn", 0.7)
    n_creatures = int(round(per_opp * len(OPP.living(g))))
    for _ in range(n_creatures):
        creature_entered(g, mine=False)

    spells = int(round(g.cfg.get("opp_spells_per_turn", 1.2) * len(OPP.living(g))))
    for _ in range(spells):
        if g.has("Kambal, Consul of Allocation") and g.rng.random() < 0.55:
            drain(g, 2)
        if g.has("Sunscorch Regent"):
            gain_life(g, 1)
        if g.has("Drana's Emissary"):
            pass
    if g.has("Blind Obedience"):
        drain(g, 1)


def upkeep(g):
    if g.has("Ajani's Mantra"):
        gain_life(g, 1)
    if g.has("Fountain of Renewal"):
        gain_life(g, 1)
    if g.has("Drana's Emissary"):
        drain(g, 1)
    if g.has("Phyrexian Arena"):
        g.draw(1)
    if g.has("Cosmos Elixir") and g.m["lifegain_triggers"] > 0:
        g.draw(1)
    if g.has("Land Tax"):
        basics = [x for x in g.library if x.name in ("Plains", "Swamp")][:3]
        for b in basics:
            g.library.remove(b)
            g.hand.append(b)
    # Felidar Sovereign: win at upkeep with 40+ life
    if g.has("Felidar Sovereign") and g.your_life >= 40 and g.result is None:
        g.result = "win"
        g.m["turn_won"] = g.turn
        g.m["win_route"] = 3
    # Aetherflux Reservoir: 50 life, deal 50
    if g.has("Aetherflux Reservoir") and g.your_life >= 51 and g.result is None:
        g.your_life -= 50
        OPP.damage_single(g, 50)
        g.m["damage"] += 50
        if g.result is None and len(OPP.living(g)) == 0:
            g.m["win_route"] = 4


def check_combo(g):
    if g.result is not None:
        return
    if g.has(COMBO_A) and any(g.has(x) for x in COMBO_B):
        g.m["combo_assembled"] = 1
        g.result = "win"
        g.m["turn_won"] = g.turn
        g.m["win_route"] = 2


# ---------------------------------------------------------------------------
# Casting and turn loop
# ---------------------------------------------------------------------------

def reduce_cost(g, card):
    return dict(card.cost)


def main_phase(g):
    while True:
        units = available_mana(g)
        if not g.commander_cast:
            ccost = dict(g.commander.cost)
            ccost["gen"] = ccost.get("gen", 0) + g.commander_tax
            if can_pay(ccost, units) is not None:
                idx = g.spells_this_turn
                g.spells_this_turn += 1
                spend(g, can_pay(ccost, units), units)
                g.m["mana_spent"] += sum(ccost.values())
                if OPP.countered(g, g.commander, idx):
                    g.m["countered"] += 1
                    g.commander_tax += 2
                    continue
                g.board.append(Permanent(card=g.commander, sick=True))
                g.commander_cast = True
                g.karlov_counters = 0
                creature_entered(g, mine=True)
                continue

        options = []
        for c in g.hand:
            if c.is_land:
                continue
            if "wipe" in c.tags and not OPP.should_cast_own_wipe(g):
                continue
            pay = can_pay(reduce_cost(g, c), units)
            if pay is not None:
                options.append((c, pay))
        if not options:
            break
        card, pay = max(options, key=lambda it: (it[0].priority, it[0].mv))
        spend(g, pay, units)
        g.m["mana_spent"] += len(pay)
        g.hand.remove(card)
        idx = g.spells_this_turn
        g.spells_this_turn += 1
        if OPP.countered(g, card, idx):
            g.m["countered"] += 1
            g.graveyard.append(card)
            if card.name in g.cfg.get("watch", ()):
                g.m["test_card_countered"] += 1
                g.m["test_card_answered"] += 1
            continue
        resolve(g, card)
        if g.result is not None:
            return


def resolve(g, card):
    g.m["spells_cast"] += 1
    if card.name in g.cfg.get("watch", ()):
        g.m["cast_test_card"] = 1
        g.m["test_card_turn"] = min(g.m["test_card_turn"], g.turn)

    if "wipe" in card.tags:
        OPP.resolve_own_wipe(g, spare_own="onesided" in card.tags)
    if card.lifegain:
        gain_life(g, card.lifegain)
    if card.drain:
        drain(g, card.drain)
    if card.script == "debt":
        # Debt to the Deathless: X=3 typical -> each opponent loses 2X
        for _ in range(len(OPP.living(g))):
            drain(g, 6)
    if card.script == "draw2":
        g.draw(2)

    if card.is_permanent:
        g.board.append(Permanent(card=card, sick=True))
        if card.is_creature:
            creature_entered(g, mine=True)
        check_combo(g)
    else:
        g.graveyard.append(card)


def combat(g):
    attackers = [p for p in g.board
                 if p.card.is_creature and not p.tapped and not p.sick]
    if not attackers:
        g.damage_by_turn.append(0.0)
        return
    dmg = OPP.damage_through(g, attackers)
    for p in attackers:
        p.tapped = True
    g.m["damage"] += dmg
    g.m["combat_damage"] += dmg
    g.damage_by_turn.append(dmg)
    OPP.damage_single(g, dmg)
    # Lifelink: Karlov triggers scale with the number of lifelinking bodies
    team_lifelink = (g.has("Sorin, Vengeful Bloodlord")
                     or g.has("Vault of the Archangel")
                     or g.has("Sorin, Solemn Visitor"))
    for p in attackers:
        if team_lifelink or p.card.lifelink:
            gain_life(g, g.power_of(p))
    if g.result is None and g.m["turn_lethal"] == 99 and not OPP.living(g):
        g.m["turn_lethal"] = g.turn


def take_turn(g):
    g.turn += 1
    g.spells_this_turn = 0
    g.creature_died_this_turn = False
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.land_drops = 1
    g.land_drops_used = 0

    upkeep(g)
    if g.result is not None:
        return
    g.draw(1)
    play_land(g)
    main_phase(g)
    if g.result is not None:
        return
    combat(g)
    main_phase(g)
    if g.result is not None:
        return

    g.m["mana_floated"] += len(available_mana(g))
    g.m["stranded_mv"] += sum(c.mv for c in g.hand if not c.is_land)

    if g.cfg.get("opponents", True):
        opponent_activity(g)
        watch = g.cfg.get("watch", ())
        before = {p.card.name for p in g.board if p.card.name in watch}
        OPP.opponents_act(g)
        after = {p.card.name for p in g.board if p.card.name in watch}
        for _ in before - after:
            g.m["test_card_answered"] += 1
            g.m["test_card_removed"] += 1
        OPP.incidental_damage(g)
        OPP.resolve_clocks(g)


def simulate(deck, commander, cfg, seed):
    g = KarlovGame(deck, commander, cfg, seed)
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
