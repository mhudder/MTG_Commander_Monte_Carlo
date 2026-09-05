"""
edhmc.karlov — a lifegain/drain engine for Karlov of the Ghost Council.

    Karlov of the Ghost Council  {W}{B}  2/2
      Whenever you gain life, put two +1/+1 counters on Karlov.
      {W}{B}, Remove six +1/+1 counters: exile target creature.  [NOT MODELLED]

THE CENTRAL MODELLING FACT
--------------------------
This deck counts TRIGGERS, not life. Gaining 1 life six times is six Karlov
triggers, twelve counters and six Voice of the Blessed counters; gaining 6 life
once is one trigger. Every payoff in the deck keys off the event, so the engine
tracks `gain_life()` calls as first-class and routes every one through a single
`on_lifegain` handler.

WHY THE OPPONENT MODEL MATTERS MORE HERE
----------------------------------------
The true soul sisters — Soul Warden, Soul's Attendant and Auriok Champion —
trigger on EVERY creature entering, including opponents'. Daxos and Elas il-Kor
read "another creature YOU CONTROL", so they see only your side; Suture Priest
sees both but gains life only off yours. Authority of the Consuls, Kambal and
Sunscorch Regent trigger on opponents' actions outright.
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
# Cards that read "whenever you gain life, target opponent loses that much
# life". Each loops with Exquisite Blood on its own, with no mana required.
# Enduring Tenacity is word-for-word Sanguine Bond's trigger on a 4/3 body, so
# it is a fourth combo piece, not merely a drain engine.
COMBO_LOOP = ("Sanguine Bond", "Vito, Thorn of the Dusk Rose",
              "Enduring Tenacity")
COMBO_B = COMBO_LOOP + ("Vizkopa Guildmage",)


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
        self.energy = 0                      # Guide of Souls
        self.life_gained_this_turn = 0.0     # Enlightened Confidant
        self.exemplar_drew_this_turn = False  # Exemplar of Light, once a turn
        self.wind_crystal_used = False       # The Wind Crystal taps to activate

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
            "heliod_counters": 0, "heliod_animated": 0,
            "guide_triggers": 0, "guide_pumps": 0,
            "tenacity_returns": 0, "crystal_activations": 0,
            "crystal_doubled": 0.0, "offspring_paid": 0,
            "lifelink_grants": 0,
            "loss_route": 0,
            "extort_triggers": 0, "confidant_cards": 0,
            "confidant_life_lost": 0.0,
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
        # "As long as you have 30 or more life, this creature gets +5/+5 and
        # has flying." A 1/1 for {W} is a 6/6 for most of a game this deck wins.
        if perm.card.name == "Serra Ascendant" and self.your_life >= 30:
            base += 5
        return base

    def toughness_of(self, perm):
        base = perm.card.toughness + perm.counters
        if perm.card.name == "Serra Ascendant" and self.your_life >= 30:
            base += 5
        return base

    def play_card_trigger(self, card):
        """Lands with an ETB lifegain clause — Radiant Fountain's 2 life.

        `engine.play_land` routes lands through `run_etb`, which dispatches on
        `card.script` only and never reads `card.lifegain`, so without this
        hook the field is silently dropped and Radiant Fountain gains nothing.
        """
        if card.is_land and card.lifegain:
            gain_life(self, card.lifegain)

    def make_tokens(self, n, p, t, subtype="", tapped=False):
        for _ in range(int(n)):
            tok = Card(name=f"{subtype or 'Token'} token",
                       types=frozenset({"Creature"}), power=p, toughness=t)
            perm = Permanent(card=tok, tapped=tapped, sick=True, is_token=True)
            self.board.append(perm)
            creature_entered(self, mine=True, entering=perm)

    def draw(self, n=1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())
                self.m["cards_drawn"] += 1

    def on_creature_death(self, n=1, perm=None):
        self.creature_died_this_turn = True
        # Enduring Tenacity: "When this dies, IF IT WAS A CREATURE, return it to
        # the battlefield under its owner's control. It's an enchantment." So it
        # survives the first wrath, keeps its lifegain trigger, and can never do
        # it a second time — it is no longer a creature to die as one.
        if perm is not None and perm.card.name == "Enduring Tenacity" \
                and perm.card.is_creature:
            glimmer = Card(name="Enduring Tenacity",
                           types=frozenset({"Enchantment"}),
                           cost=dict(perm.card.cost),
                           priority=perm.card.priority,
                           threat=perm.card.threat)
            self.board.append(Permanent(card=glimmer, sick=False))
            self.m["tenacity_returns"] += 1
        for _ in range(n):
            # "target player loses 1 life and you gain 1 life" — a real drain.
            if self.has("Blood Artist"):
                drain(self, 1)
            # "each opponent loses 1 life" — and you gain NOTHING, so this is
            # not a drain() and must not manufacture a Karlov trigger.
            if self.has("Elas il-Kor, Sadistic Pilgrim"):
                OPP.damage_each(self, 1)
                self.m["damage"] += len(OPP.living(self))
                self.m["drain_damage"] += len(OPP.living(self))
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

def spend_lg(g, pay_idx, units):
    """`engine.spend`, plus the lifegain that tapping a mana rock can cause.

    Pristine Talisman is "{T}: Add {C}. You gain 1 life" — the life comes off
    the mana ability, not off resolution, so `Card.lifegain` (applied once in
    resolve()) cannot express it and the field sat at 0. Anything else in this
    deck with lifegain on its mana ability goes here too.
    """
    before = {id(p) for p in g.board
              if p.card.name in TAP_LIFEGAIN and not p.tapped}
    spend(g, pay_idx, units)
    for p in g.board:
        if p.card.name in TAP_LIFEGAIN and p.tapped and id(p) in before:
            gain_life(g, TAP_LIFEGAIN[p.card.name])


TAP_LIFEGAIN = {"Pristine Talisman": 1}


def pay_generic(g, want):
    """Pay up to `want` generic mana from whatever is untapped. Returns how
    much was actually paid.

    Several payoffs in this deck ("you may pay {2}", "you may pay {X}") were
    modelled as free. They are activated at instant speed off whatever mana is
    still open, so this spends greedily from the current pool rather than
    reserving anything.
    """
    paid = 0
    for _ in range(int(want)):
        units = available_mana(g)
        idx = can_pay({"gen": 1}, units)
        if idx is None:
            break
        spend_lg(g, idx, units)
        paid += 1
    return paid


def devotion_white(g):
    """Devotion to white: {W} pips among the mana costs of permanents you
    control. Karlov himself is {W}{B} and counts for one."""
    return sum(p.card.cost.get("W", 0) for p in g.board)


def is_creature_now(g, card):
    """Heliod is an Enchantment Creature that is NOT a creature while your
    devotion to white is less than five. Nothing else in this deck has a
    type-changing condition."""
    if not card.is_creature:
        return False
    if card.name == "Heliod, Sun-Crowned":
        return devotion_white(g) >= 5
    return True


def gain_life(g, amount, _depth=0):
    """One lifegain EVENT. Amount matters for some payoffs, the event itself
    matters for more of them."""
    if amount <= 0 or _depth > 3:
        return
    # The Wind Crystal: "If you would gain life, you gain twice that much life
    # instead." A replacement effect, so it doubles the AMOUNT and leaves the
    # number of EVENTS alone — which is the distinction this whole engine is
    # built around. Karlov still gets two counters, not four.
    if g.has("The Wind Crystal"):
        g.m["crystal_doubled"] += amount
        amount *= 2
    g.your_life += amount
    g.life_gained_this_turn += amount
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
            # "each opponent loses 1 life" — a flat 1 to EACH, not `amount` to
            # one. The old form understated small triggers 3x and overstated
            # large ones.
            OPP.damage_each(g, 1)
            g.m["damage"] += len(OPP.living(g))
        elif n in ("Marauding Blight-Priest", "Starscape Cleric"):
            # Starscape Cleric: "whenever you gain life, each opponent loses 1
            # life" — identical wording to Blight-Priest, and its Offspring
            # token has the same trigger, which is why the token is named the
            # same and this loop counts both.
            OPP.damage_each(g, 1)
            g.m["damage"] += len(OPP.living(g))
        elif n == "Heliod, Sun-Crowned":
            # "put a +1/+1 counter on target creature or enchantment you
            # control." Put it where it converts to damage: the biggest body.
            bodies = [q for q in g.board if is_creature_now(g, q.card)]
            if bodies:
                max(bodies, key=g.power_of).counters += 1
                g.m["heliod_counters"] += 1
        elif n == "Exemplar of Light":
            p.counters += 1
            # "Whenever you put one or more +1/+1 counters on this creature,
            # draw a card. This ability triggers only once each turn."
            if not g.exemplar_drew_this_turn:
                g.exemplar_drew_this_turn = True
                g.draw(1)
        elif n in COMBO_LOOP:
            OPP.damage_single(g, amount)
            g.m["damage"] += amount
            # Exquisite Blood sees that loss of life and gains it back: loop.
            if g.has(COMBO_A) and g.result is None:
                g.result = "win"
                g.m["turn_won"] = g.turn
                g.m["win_route"] = 2
                return
    # Both of these are "you MAY PAY" effects. They were free before, which is
    # why they rank so highly on the ablation table.
    if g.has("Well of Lost Dreams"):
        # "you may pay {X} ... draw X cards", X <= life gained.
        n = pay_generic(g, min(2, int(amount)))
        g.draw(n)
    if g.has("Dawn of Hope"):
        # "you may pay {2}. If you do, draw a card."
        if pay_generic(g, 2) == 2:
            g.draw(1)


def drain(g, amount):
    """Lose-life-and-gain-life: two events in one, and both matter."""
    OPP.damage_single(g, amount)
    g.m["damage"] += amount
    g.m["drain_damage"] += amount
    gain_life(g, amount)


def creature_entered(g, mine=True, entering=None):
    """Soul sisters see EVERY creature enter, including the opponents'.

    Daxos does NOT: his trigger reads "whenever another creature YOU CONTROL
    enters or dies", so he belongs with Elas il-Kor below, not with the sisters.

    `entering` is the permanent that just entered, where the caller knows it.
    It is used for the "ANOTHER creature you control" clauses, so that a card
    does not trigger off its own arrival.
    """
    # Guide of Souls: "Whenever another creature you control enters, you gain 1
    # life and get {E}." The energy is what pays for the attack trigger.
    if mine:
        guides = [q for q in g.board
                  if q.card.name == "Guide of Souls" and q is not entering]
        for _ in guides:
            gain_life(g, 1)
            g.energy += 1
            g.m["guide_triggers"] += 1
    for _ in range(g.count("Soul Warden") + g.count("Soul's Attendant")
                   + g.count("Auriok Champion")):
        gain_life(g, 1)
    if mine and g.has("Daxos, Blessed by the Sun"):
        gain_life(g, 1)
    if g.has("Suture Priest"):
        if mine:
            gain_life(g, 1)
        else:
            # "you may have that player lose 1 life" — no life gained, so this
            # is not a drain() and must not create a Karlov trigger.
            OPP.damage_single(g, 1)
            g.m["damage"] += 1
            g.m["drain_damage"] += 1
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
            # "put a +1/+1 counter on this creature AND you gain 1 life" — the
            # counter was missing, so a 4/3 that should grow all game did not.
            for p in g.board:
                if p.card.name == "Sunscorch Regent":
                    p.counters += 1
            gain_life(g, 1)


def upkeep(g):
    # Dark Confidant: "reveal the top card of your library and put that card
    # into your hand. You lose life equal to its mana value." The life is a
    # real cost here — this engine loses games on `your_life` — and it is NOT
    # a lifegain event, so it must not touch gain_life().
    for _ in range(g.count("Dark Confidant")):
        if not g.library:
            break
        top = g.library[-1]
        g.draw(1)
        g.your_life -= float(top.mv)
        g.m["confidant_life_lost"] += float(top.mv)
        if g.your_life <= 0 and g.result is None:
            g.result = "loss"
            return
    if g.has("Ajani's Mantra"):
        gain_life(g, 1)
    if g.has("Fountain of Renewal"):
        gain_life(g, 1)
    if g.has("Drana's Emissary"):
        # "EACH opponent loses 1 life and you gain 1 life" — drain() hit only
        # one, understating its pod damage 3x.
        n = len(OPP.living(g))
        OPP.damage_each(g, 1)
        g.m["damage"] += n
        g.m["drain_damage"] += n
        gain_life(g, 1)
    if g.has("Phyrexian Arena"):
        g.draw(1)
    if g.has("Land Tax"):
        # "if an opponent controls more lands than you" — the condition was
        # missing entirely, so this fetched three basics every upkeep.
        #
        # The opponent model tracks creatures and life but NOT lands, so the
        # best opponent's land count is approximated as one drop per turn,
        # plateauing once they stop hitting them. That is deliberately
        # generous to the condition (three opponents, only one needs to be
        # ahead), which keeps this a modelling assumption rather than a
        # silent buff. Tune with cfg["opp_land_plateau"].
        my_lands = sum(1 for p in g.board if p.card.is_land)
        opp_lands = min(g.turn, g.cfg.get("opp_land_plateau", 8))
        if opp_lands > my_lands:
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


def end_step(g):
    """Beginning of your end step."""
    # Cosmos Elixir: "draw a card if your life total is greater than your
    # starting life total. OTHERWISE, you gain 2 life." Previously this fired
    # in upkeep, keyed off lifegain_triggers > 0 rather than the life total,
    # and dropped the gain-2 branch — which is itself a Karlov trigger.
    if g.has("Cosmos Elixir"):
        if g.your_life > g.cfg.get("starting_life", 40):
            g.draw(1)
        else:
            gain_life(g, 2)

    # Enlightened Confidant: "at the beginning of your end step, IF YOU GAINED
    # LIFE THIS TURN, surveil 1. If you put a card with mana value less than or
    # equal to the amount of life you gained this turn into your graveyard this
    # way, put that card into your hand."
    #
    # Note what the threshold reads: the TOTAL life gained this turn, not one
    # trigger's worth. This deck gains in ones but gains often, so the gate is
    # usually 4-6 and covers most of the curve. Surveilling a card you cannot
    # pick up is left on top rather than binned — this engine has no top-deck
    # payoff to bin for, so throwing the card away would be a strictly worse
    # play than declining.
    for _ in range(g.count("Enlightened Confidant")):
        if g.life_gained_this_turn <= 0 or not g.library:
            break
        top = g.library[-1]
        if top.mv <= g.life_gained_this_turn:
            g.draw(1)
            g.m["confidant_cards"] += 1


def check_combo(g):
    if g.result is not None:
        return
    if not g.has(COMBO_A):
        return
    # Sanguine Bond and Vito loop with Exquisite Blood on their own. Vizkopa
    # Guildmage does NOT: its drain is an activated ability costing {1}{W}{B},
    # so it only assembles the loop if that mana is actually available.
    partner = any(g.has(x) for x in COMBO_LOOP)
    if not partner and g.has("Vizkopa Guildmage"):
        units = available_mana(g)
        if can_pay({"gen": 1, "W": 1, "B": 1}, units) is not None:
            partner = True
    if partner:
        g.m["combo_assembled"] = 1
        g.result = "win"
        g.m["turn_won"] = g.turn
        g.m["win_route"] = 2


# ---------------------------------------------------------------------------
# Casting and turn loop
# ---------------------------------------------------------------------------

def reduce_cost(g, card):
    cost = dict(card.cost)
    # The Wind Crystal: "White spells you cast cost {1} less to cast." Generic
    # only — a cost reduction can never pay a coloured pip, so {W}{W} stays
    # {W}{W} and this deck's one-drops get nothing.
    if g.has("The Wind Crystal") and card.cost.get("W", 0) > 0:
        cost["gen"] = max(0, cost.get("gen", 0) - 1)
    return cost


def main_phase(g):
    while True:
        units = available_mana(g)
        if not g.commander_cast:
            ccost = dict(g.commander.cost)
            ccost["gen"] = ccost.get("gen", 0) + g.commander_tax
            if can_pay(ccost, units) is not None:
                idx = g.spells_this_turn
                g.spells_this_turn += 1
                spend_lg(g, can_pay(ccost, units), units)
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
        spend_lg(g, pay, units)
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

    # Aetherflux Reservoir: "whenever you cast a spell, you gain 1 life for
    # each spell you've cast this turn." This is the card's actual engine and
    # was missing entirely — only the pay-50 kill was modelled.
    if g.has("Aetherflux Reservoir"):
        gain_life(g, g.spells_this_turn)

    # Extort: "whenever you cast a spell, you may pay {W/B}; if you do, each
    # opponent loses 1 life and you gain that much." Once per SOURCE per spell,
    # so two extorters on the battlefield is two triggers and two payments.
    for _ in range(g.count("Blind Obedience") + g.count("Crypt Ghast")):
        if pay_generic(g, 1) != 1:
            break
        n = len(OPP.living(g))
        OPP.damage_each(g, 1)
        g.m["damage"] += n
        g.m["drain_damage"] += n
        g.m["extort_triggers"] += 1
        gain_life(g, n)

    if "wipe" in card.tags:
        OPP.resolve_own_wipe(g, spare_own="onesided" in card.tags)
    if card.lifegain:
        gain_life(g, card.lifegain)
    if card.drain:
        drain(g, card.drain)
    if card.script == "debt":
        # "Each opponent loses two times X life. You gain life equal to the
        # life lost this way." With X=3 that is 6 per opponent, and the life
        # gain is ONE event for the total — not one event per opponent. The
        # old loop created three Karlov triggers where the card makes one.
        n = len(OPP.living(g))
        total = 6 * n
        OPP.damage_each(g, 6)
        g.m["damage"] += total
        g.m["drain_damage"] += total
        gain_life(g, total)
    if card.script == "draw2":
        g.draw(2)

    if card.is_permanent:
        perm = Permanent(card=card, sick=not card.haste)
        g.board.append(perm)
        if is_creature_now(g, card):
            creature_entered(g, mine=True, entering=perm)
        # Offspring {2}{B}: an additional cost paid as you cast, which creates a
        # 1/1 token copy on ETB. The copy has the same lifegain trigger, so it
        # carries the same name here and gain_life() counts both.
        if card.name == "Starscape Cleric":
            units = available_mana(g)
            idx = can_pay({"gen": 2, "B": 1}, units)
            if idx is not None:
                spend_lg(g, idx, units)
                g.m["mana_spent"] += 3
                tok = Card(name="Starscape Cleric",
                           types=frozenset({"Creature"}), power=1, toughness=1)
                tperm = Permanent(card=tok, sick=True, is_token=True)
                g.board.append(tperm)
                creature_entered(g, mine=True, entering=tperm)
                g.m["offspring_paid"] += 1
        check_combo(g)
    else:
        g.graveyard.append(card)


def combat(g):
    if g.has("Heliod, Sun-Crowned") and devotion_white(g) >= 5:
        g.m["heliod_animated"] += 1
    attackers = [p for p in g.board
                 if is_creature_now(g, p.card) and not p.tapped and not p.sick]
    if not attackers:
        g.damage_by_turn.append(0.0)
        return

    # Guide of Souls: "Whenever you attack, you may pay {E}{E}{E}. When you do,
    # put two +1/+1 counters and a flying counter on target attacking creature."
    # The flying counter is not modelled — nothing in damage_through reads
    # evasion — so this is the counters only, and a floor.
    if g.has("Guide of Souls") and g.energy >= 3:
        g.energy -= 3
        max(attackers, key=g.power_of).counters += 2
        g.m["guide_pumps"] += 1

    # The Wind Crystal: "{4}{W}{W}, {T}: Creatures you control gain flying and
    # lifelink until end of turn." Six mana at instant speed after the main
    # phase has already deployed, so it fires rarely — but when it does, every
    # attacker becomes a Karlov trigger.
    granted = set()
    if g.has("The Wind Crystal") and not g.wind_crystal_used:
        units = available_mana(g)
        idx = can_pay({"gen": 4, "W": 2}, units)
        if idx is not None:
            spend_lg(g, idx, units)
            g.m["mana_spent"] += 6
            g.wind_crystal_used = True
            g.m["crystal_activations"] += 1
            granted = {id(p) for p in attackers}

    # Heliod, Sun-Crowned: "{1}{W}: Another target creature gains lifelink until
    # end of turn." One activation per pass off whatever mana survived the main
    # phase; "another" excludes Heliod himself.
    if g.has("Heliod, Sun-Crowned") and not granted:
        others = [p for p in attackers if p.card.name != "Heliod, Sun-Crowned"]
        if others:
            units = available_mana(g)
            idx = can_pay({"gen": 1, "W": 1}, units)
            if idx is not None:
                spend_lg(g, idx, units)
                g.m["mana_spent"] += 2
                granted = {id(max(others, key=g.power_of))}
                g.m["lifelink_grants"] += 1

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
        if team_lifelink or p.card.lifelink or id(p) in granted:
            gain_life(g, g.power_of(p))
    if g.result is None and g.m["turn_lethal"] == 99 and not OPP.living(g):
        g.m["turn_lethal"] = g.turn


def take_turn(g):
    g.turn += 1
    g.spells_this_turn = 0
    g.creature_died_this_turn = False
    g.exemplar_drew_this_turn = False
    g.wind_crystal_used = False
    g.life_gained_this_turn = 0.0
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

    end_step(g)
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
