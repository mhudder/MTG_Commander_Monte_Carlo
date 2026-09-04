"""
edhmc.lorehold — a miracle/top-deck engine for Lorehold, the Historian.

The Rendmaw engine models a deck that wins by putting power on the board. This
deck does something structurally different, so it gets its own turn loop.

    Lorehold, the Historian  {3}{R}{W}  5/5 flying haste
      Each instant and sorcery card in your hand has miracle {2}.
      At the beginning of each OPPONENT'S upkeep, you may discard a card.
      If you do, draw a card.

The second ability is the engine, and it is the reason this deck needs a
different simulation. It creates three extra miracle windows per round, because
the card you draw on each opponent's upkeep is the first card you drew that
turn. With Library of Leng the discarded card goes on top of your library
instead of the graveyard, so you discard your ten-drop, draw it, and miracle it
for {2}. That loop is the deck.

PRIMARY METRIC: `mv_cheated` — total mana value cast minus mana actually paid.
Board presence and damage are not what this deck is for; converting a {2}
payment into a ten-mana sorcery is. Damage is still tracked as a secondary.

MIRACLE WINDOWS PER ROUND
    1  your draw step
    3  one per opponent's upkeep (requires Lorehold on the battlefield)
"""

from __future__ import annotations

import random

from edhmc.engine import Card, Permanent, can_pay, available_mana, spend, play_land
from edhmc import opponents as OPP

# Cards that can put a chosen card from hand onto the top of your library.
# (cost in generic mana to do it, roughly)
# Mana cost to put a card from hand on top. CORRECTED against oracle text:
# Penance and Hidden Retreat both take NO mana - putting the card on top IS the
# cost. Hidden Retreat is gated instead: it needs a legal target, an instant or
# sorcery on the stack, so it is only usable in response to one.
TOP_SETTERS = {
    "Scroll Rack": 1,           # {1}, T - real mana and a tap
    "Hidden Retreat": 0,        # free, but requires a target I/S on the stack
    "Penance": 0,               # free, does not target, unlimited
    "Library of Leng": 0,       # only via a discard, handled separately
}
GATED_SETTERS = {"Hidden Retreat"}


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class LoreholdGame:
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
        self.treasures = 0
        self.turn = 0
        self.land_drops = 1
        self.land_drops_used = 0
        self.spells_this_turn = 0
        self.float_mana = 0
        self.noncreature_this_turn = 0
        self.bombardment_fired_this_turn = False
        self.bombardment_exiled = []
        self.dv_fired_this_turn = False
        self.monument_used = set()
        self.last_paid = 0
        self.tutor_log = []
        self.made_token_this_turn = False
        self.beast_active = False

        cfg.setdefault("shroud_sources",
                       ("Lightning Greaves", "Mother of Runes", "Plaza of Heroes"))
        cfg.setdefault("protection_cards",
                       ("Dawn's Truce", "Boros Charm", "Perch Protection",
                        "Sejiri Shelter"))
        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = {
            "mv_cheated": 0.0,
            "miracles_cast": 0,
            "miracle_windows": 0,
            "miracle_hits": 0,
            "total_mv_cast": 0.0,
            "cards_drawn": 0,
            "spells_cast": 0,
            "mana_spent": 0,
            "mana_floated": 0,
            "damage": 0.0,
            "spell_damage": 0.0,
            "combat_damage": 0.0,
            "approach_casts": 0,
            "extra_turns": 0,
            "turn_won": 99,
            "free_casts": 0,
            "bombardment_copies": 0,
            "monument_triggers": 0,
            "mastery_copies": 0,
            "land_tax_fetches": 0,
            "upkeep_free_casts": 0,
            "double_vision_copies": 0,
            "own_wipes_cast": 0,
            "treasures_made": 0,
            "removal_eaten": 0,
            "ae_removal_eaten": 0,
            "wipes_suffered": 0,
            "countered": 0,
            "protected": 0,
            "stranded_mv": 0,
            "turn_lethal": 99,
            "cast_test_card": 0,
            "test_card_turn": 99,
            "test_card_answered": 0,
            "test_card_removed": 0,
            "test_card_countered": 0,
            "clamp_activations": 0,
            "fodder_turns": 0,
        }
        self.damage_by_turn = []

    # -- helpers ------------------------------------------------------------

    def has(self, name):
        return any(p.card.name == name for p in self.board)

    def play_card_trigger(self, card):
        """Lorehold has no play trigger; the hook exists for engine reuse."""
        return

    def make_tokens(self, *a, **k):
        return

    def power_of(self, perm):
        base = perm.card.power + perm.counters
        # Storm-Kiln Artist: "gets +1/+0 for each artifact you control." It
        # makes Treasures, so it scales off its own output.
        if perm.card.name == "Storm-Kiln Artist":
            base += (sum(1 for p in self.board if "Artifact" in p.card.types)
                     + self.treasures)
        return base

    def toughness_of(self, perm):
        return perm.card.toughness + perm.counters

    def draw_card(self):
        if not self.library:
            return None
        c = self.library.pop()
        self.m["cards_drawn"] += 1
        return c

    def opening_hand(self):
        for mulls in range(4):
            self.hand = [self.library.pop() for _ in range(7)]
            lands = sum(1 for c in self.hand if c.is_land or "mdfc" in c.tags)
            if 2 <= lands <= 5:
                break
            self.library.extend(self.hand)
            self.rng.shuffle(self.library)
            self.hand = []
        for _ in range(mulls):
            if self.hand:
                worst = max(self.hand, key=lambda c: (not c.is_land, c.mv))
                self.hand.remove(worst)
                self.library.insert(0, worst)


# ---------------------------------------------------------------------------
# Mana (treasures count as sources)
# ---------------------------------------------------------------------------

def mana_units(g):
    units = available_mana(g)
    per = 2 if g.has("Goldspan Dragon") else 1     # Treasures tap for two
    units.extend([frozenset({"R", "W", "C"})] * (g.treasures * per))
    return units


def pay(g, cost, units):
    idx = can_pay(cost, units)
    if idx is None:
        return None
    n = len(idx)
    per = 2 if g.has("Goldspan Dragon") else 1
    # spend treasures last, real mana first
    from_board = min(n, len(units) - g.treasures * per)
    if from_board > 0:
        spend(g, list(range(from_board)), units)
    used = n - from_board
    g.treasures -= -(-used // per)          # ceil: each Treasure gives `per`
    g.m["mana_spent"] += n
    return n


def reduce_cost(g, card, miracle=False):
    """Apply cost reduction. Returns a cost dict."""
    if miracle:
        cost = dict(card.miracle_cost)
    else:
        cost = dict(card.cost)
    red = 0
    if g.has("Ruby Medallion") and card.cost.get("R", 0) > 0:
        red += 1
    if g.has("Artist's Talent"):
        red += 1
    # Longshot, Rebel Bowman: "Noncreature spells you cast cost {1} less."
    if g.has("Longshot, Rebel Bowman") and "Creature" not in card.types:
        red += 1
    if card.name == "The Dawning Archaic":
        red += sum(1 for c in g.graveyard
                   if "Instant" in c.types or "Sorcery" in c.types)
    if card.name == "Blasphemous Act":
        red += min(9, sum(1 for p in g.board if p.card.is_creature) + 3)
    cost["gen"] = max(0, cost.get("gen", 0) - red)
    return cost


# ---------------------------------------------------------------------------
# Top-of-library manipulation
# ---------------------------------------------------------------------------

def miracle_value(g, card):
    """What is this card worth if we miracle it? = mana we would cheat."""
    if card.is_land:
        return -1.0
    if g.has("Molecule Man"):
        return float(card.mv)                     # everything is castable for {0}
    if "Instant" in card.types or "Sorcery" in card.types:
        return float(card.mv) - 2.0               # Lorehold's miracle {2}
    if card.miracle_cost:
        return float(card.mv) - sum(card.miracle_cost.values())
    return -1.0                                    # no miracle available


def set_top(g):
    """Put the best miracle target from hand on top of the library.

    Sensei's Divining Top only reorders the top three, so it is modelled
    separately from the hand-to-top effects.
    """
    units = mana_units(g)
    for name, cost in TOP_SETTERS.items():
        if name == "Library of Leng" or not g.has(name):
            continue
        if name in GATED_SETTERS:
            # only live while an opponent's instant or sorcery is on the stack
            if g.rng.random() > g.cfg.get("opp_instant_rate", 0.8):
                continue
        best = max(g.hand, key=lambda c: miracle_value(g, c), default=None)
        if best is None or miracle_value(g, best) <= 0:
            return
        # Only set the top if we can actually pay for the miracle when we draw
        # it. Without this the engine recycles the same uncastable card onto
        # the library every turn, consuming every draw step and starving itself
        # of new cards -- which is why a FREE top-setter was somehow reducing
        # the number of miracles cast.
        need = 0 if g.has("Molecule Man") else 2
        if g.has("Artist's Talent"):
            need = max(0, need - 1)
        if len(units) + g.treasures < need + cost:
            return
        # Only worth doing if the mana saved beats the cost of doing it AND
        # we can still afford the miracle afterwards. Firing these every turn
        # regardless of value is a large hidden tax on a deck that already
        # floats four mana a turn.
        gate = g.cfg.get("set_top_gate", 0.0)
        if cost > 0:
            if gate and miracle_value(g, best) - cost < gate:
                return
            if gate and len(units) < cost + 2:
                return
        if can_pay({"gen": cost}, units) is None:
            continue
        pay(g, {"gen": cost}, units)
        g.hand.remove(best)
        g.library.append(best)
        return


def sort_top_three(g):
    """Sensei's Divining Top: rearrange the top three, best miracle on top."""
    if not g.has("Sensei's Divining Top") or len(g.library) < 3:
        return
    top3 = [g.library.pop() for _ in range(3)]
    top3.sort(key=lambda c: miracle_value(g, c))     # best ends up last = on top
    g.library.extend(top3)


def verge_rangers_filter(g):
    """Play a land off the top when behind on lands.

    Worth modelling carefully: in a miracle deck the ramp is almost beside the
    point. The real effect is that it strips lands off the top of the library,
    so the card you actually draw is more often a live miracle target.
    """
    if not g.has("Verge Rangers") or g.land_drops_used >= g.land_drops:
        return
    my_lands = sum(1 for p in g.board if p.card.is_land)
    opp_lands = min(g.turn, 10)
    if opp_lands <= my_lands or not g.library:
        return
    top = g.library[-1]
    if not top.is_land:
        return
    g.library.pop()
    g.board.append(Permanent(card=top, tapped=top.tapped, sick=True))
    g.land_drops_used += 1


# ---------------------------------------------------------------------------
# Miracle window
# ---------------------------------------------------------------------------

def miracle_window(g, off_turn=False):
    """Draw the first card of a turn and try to miracle it."""
    sort_top_three(g)
    verge_rangers_filter(g)
    card = g.draw_card()
    if card is None:
        return
    g.m["miracle_windows"] += 1

    val = miracle_value(g, card)
    if val <= 0 or not (g.commander_cast or g.has("Molecule Man")
                        or card.miracle_cost):
        g.hand.append(card)
        return

    if g.has("Molecule Man"):
        mcost = {}
    elif card.miracle_cost and ("Instant" not in card.types
                                and "Sorcery" not in card.types):
        mcost = dict(card.miracle_cost)
    elif g.commander_cast:
        mcost = {"gen": 2}
    else:
        g.hand.append(card)
        return

    mcost = dict(mcost)
    red = 1 if g.has("Artist's Talent") else 0
    red += 1 if (g.has("Ruby Medallion") and card.cost.get("R", 0) > 0) else 0
    mcost["gen"] = max(0, mcost.get("gen", 0) - red)

    need = sum(mcost.values())
    if off_turn:
        if need > g.float_mana + g.treasures:
            g.hand.append(card)
            return
        units = [frozenset({"R", "W", "C"})] * (g.float_mana + g.treasures)
    else:
        units = mana_units(g)
        if can_pay(mcost, units) is None:
            g.hand.append(card)
            return

    idx = g.spells_this_turn
    g.spells_this_turn += 1
    if off_turn:
        paid = need
        from_float = min(need, g.float_mana)
        g.float_mana -= from_float
        g.treasures -= (need - from_float)
        g.m["mana_spent"] += need
    else:
        paid = pay(g, mcost, units)
    if OPP.countered(g, card, idx):
        g.m["countered"] += 1
        g.graveyard.append(card)
        if card.name in g.cfg.get("watch", ()):
            g.m["test_card_countered"] += 1
            g.m["test_card_answered"] += 1
        return

    g.m["miracles_cast"] += 1
    g.m["miracle_hits"] += 1
    resolve_spell(g, card, paid)


# ---------------------------------------------------------------------------
# Casting
# ---------------------------------------------------------------------------

def _draw_into_hand(g, n):
    for _ in range(n):
        c = g.draw_card()
        if c:
            g.hand.append(c)


def make_tokens(g, n, power, toughness, name="token"):
    for _ in range(int(n)):
        tok = Card(name=f"{name} token", types=frozenset({"Creature"}),
                   power=power, toughness=toughness)
        g.board.append(Permanent(card=tok, sick=True, is_token=True))


def deal_pod_damage(g, amount, each=True):
    """`each=True`: an 'each opponent loses N' effect; amount is the pod total."""
    if amount <= 0:
        return
    g.m["damage"] += amount
    g.m["spell_damage"] += amount
    if g.damage_by_turn:
        g.damage_by_turn[-1] += amount
    n = max(1, len(OPP.living(g)))
    if each:
        OPP.damage_each(g, amount / n)
    else:
        OPP.damage_single(g, amount)
    if g.result == "win" and g.m["turn_lethal"] == 99:
        g.m["turn_lethal"] = g.turn


# Monument to Endurance modes, in the order a pilot would take them. Each may
# be chosen only once per TURN — and Lorehold's rummage discards on each of the
# three opponents' turns, so the choice resets three extra times a round.
MONUMENT_MODES = ("draw", "drain", "treasure")


def discard_triggers(g, n=1):
    """Fire Monument to Endurance for n discards."""
    if not g.has("Monument to Endurance"):
        return
    order = g.cfg.get("monument_order", MONUMENT_MODES)
    for _ in range(n):
        mode = next((m for m in order if m not in g.monument_used), None)
        if mode is None:
            return                      # all three taken this turn
        g.monument_used.add(mode)
        g.m["monument_triggers"] += 1
        if mode == "draw":
            _draw_into_hand(g, 1)
        elif mode == "treasure":
            g.treasures += 1
            g.m["treasures_made"] += 1
        elif mode == "drain":
            deal_pod_damage(g, 9.0)     # each of 3 opponents loses 3


def on_cast_triggers(g, card, is_copy=False):
    """Everything that watches you cast a spell.

    Copies made by Arcane Bombardment are genuinely cast, so they set these off
    too — which is most of why the card snowballs in a deck like this.
    """
    inst_sorc = ("Instant" in card.types or "Sorcery" in card.types)

    if inst_sorc:
        # Guttersnipe: 2 damage to EACH opponent, so 6 a pop.
        deal_pod_damage(g, 6.0 * sum(1 for p in g.board
                                     if p.card.name == "Guttersnipe"))
        # Urabrask: 1 damage to ONE target opponent per instant/sorcery.
        deal_pod_damage(g, 1.0 * sum(1 for p in g.board
                                     if p.card.name.startswith("Urabrask")))

    if "Creature" not in card.types:
        g.noncreature_this_turn += 1
        # Longshot, Rebel Bowman: 2 damage to EACH opponent per noncreature
        # spell, so 6 a pop — a Guttersnipe on a wider trigger.
        deal_pod_damage(g, 6.0 * sum(1 for p in g.board
                                     if p.card.name == "Longshot, Rebel Bowman"))
        # Dragon's Rage Channeler: surveil 1. In a miracle deck the value is
        # binning a land off the top so the next draw is a live target.
        if g.has("Dragon's Rage Channeler") and g.library:
            top = g.library[-1]
            n_lands = sum(1 for p in g.board if p.card.is_land)
            if top.is_land and n_lands >= g.cfg.get("surveil_land_floor", 6):
                g.graveyard.append(g.library.pop())
        # Monastery Mentor: a 1/1 prowess Monk per noncreature spell.
        for _ in range(sum(1 for p in g.board
                           if p.card.name == "Monastery Mentor")):
            make_tokens(g, 1, 1, 1, "Monk")

    if inst_sorc and not is_copy:
        arcane_bombardment(g)
        double_vision(g, card)


def double_vision(g, card):
    """Whenever you cast your FIRST instant or sorcery each turn, copy it.

    Same "each turn" wording as Arcane Bombardment, so with Lorehold's rummage
    opening a window on all three opponents' turns a round can produce four
    triggers rather than one.

    Crucially the copy is PUT ON THE STACK, not cast (ruling 2020-06-23). So
    unlike Bombardment's and Mastery's copies -- which you genuinely cast -- it
    does NOT trigger Guttersnipe, Urabrask, Monastery Mentor or Bombardment.
    """
    if not g.has("Double Vision") or g.dv_fired_this_turn:
        return
    g.dv_fired_this_turn = True
    g.m["double_vision_copies"] += 1
    g.m["mv_cheated"] += card.mv
    g.m["total_mv_cast"] += card.mv
    apply_spell_effects(g, card, is_copy=True, was_cast=False)


def arcane_bombardment(g):
    """Whenever you cast your FIRST instant or sorcery each turn: exile one at
    random from the graveyard, then copy EVERY card exiled with it so far and
    cast the copies free.

    Two things make this strong here rather than merely good. It accumulates,
    so the Nth trigger yields N free spells. And it reads "each turn", not
    "each of your turns" — Lorehold's rummage gives a miracle window on all
    three opponents' turns, so a round can produce four triggers rather than
    one.
    """
    if not g.has("Arcane Bombardment") or g.bombardment_fired_this_turn:
        return
    g.bombardment_fired_this_turn = True

    pool = [c for c in g.graveyard
            if "Instant" in c.types or "Sorcery" in c.types]
    if pool:
        picked = pool[g.rng.randrange(len(pool))]
        g.graveyard.remove(picked)
        g.bombardment_exiled.append(picked)

    for card in list(g.bombardment_exiled):
        g.m["bombardment_copies"] += 1
        g.m["mv_cheated"] += card.free_mv
        g.m["total_mv_cast"] += card.free_mv
        g.m["spells_cast"] += 1
        apply_spell_effects(g, card, is_copy=True)


def apply_spell_effects(g, card, is_copy=False, was_cast=True):
    """The on-resolution half of a spell: damage, tokens, treasures, draw."""
    sc = card.script
    if sc in ("treasures", "draw2_treasure"):
        g.treasures += card.treasures
        g.m["treasures_made"] += card.treasures
    if sc in ("draw2", "draw2_treasure"):
        _draw_into_hand(g, 2)
    elif sc == "draw4":
        _draw_into_hand(g, 4)
    elif sc == "soulfire":
        for _ in range(3):
            if g.library:
                deal_pod_damage(g, float(g.library.pop().mv))
    elif sc == "searing_light":
        # "Each opponent exiles a creature with the greatest power among
        # creatures that player controls." An edict, NOT a board wipe — it was
        # tagged ("wipe", "onesided") and routed through resolve_own_wipe,
        # which is a different effect entirely.
        for o in OPP.living(g):
            o.creatures = max(0.0, o.creatures - 1)
        # Spell mastery: with 2+ instants/sorceries in the graveyard it also
        # deals damage equal to each exiled creature's power. The opponent
        # model has no per-creature power, so use the pod's average body.
        if sum(1 for c in g.graveyard
               if "Instant" in c.types or "Sorcery" in c.types) >= 2:
            deal_pod_damage(g, g.cfg.get("opp_avg_power", 2.5)
                            * len(OPP.living(g)))
    elif sc == "storm_herd":
        make_tokens(g, g.cfg.get("storm_herd_x", 40), 1, 1, "Pegasus")
    elif sc == "extra_turn":
        _draw_into_hand(g, 4)
        g.m["extra_turns"] += 1
    elif sc == "approach" and not is_copy:
        g.m["approach_casts"] += 1
        if g.m["approach_casts"] >= 2 and g.m["turn_won"] == 99:
            g.m["turn_won"] = g.turn
            g.result = "win"
    elif sc == "tutor" and not is_copy:
        # Enlightened Tutor: find an artifact or enchantment and put it ON TOP
        # of the library, not into hand. In this deck that also consumes the
        # next draw, which is why the choice is state-dependent rather than
        # just "take the best card".
        pool = [x for x in g.library
                if ("Artifact" in x.types or "Enchantment" in x.types)
                and not x.is_land]
        shortlist = g.cfg.get("tutor_targets", ())
        cands = [x for x in pool if x.name in shortlist] or pool
        if cands:
            if g.cfg.get("tutor_policy") == "random":
                pick = cands[g.rng.randrange(len(cands))]
            elif g.cfg.get("tutor_policy") == "adaptive":
                # Learned from 14,028 randomised tutor resolutions. The
                # commander's presence flips which target is correct: without
                # Lorehold you want the cards that work on their own; with it
                # you want the ones that scale off the extra miracle windows.
                if not g.commander_cast or g.turn <= 6:
                    order = ("Land Tax", "Monument to Endurance", "Sol Ring",
                             "Smothering Tithe", "Sensei's Divining Top",
                             "Library of Leng", "Arcane Bombardment")
                else:
                    order = ("Arcane Bombardment", "Sensei's Divining Top",
                             "Smothering Tithe", "Land Tax", "Sol Ring",
                             "Library of Leng", "Monument to Endurance")
                pick = min(cands, key=lambda x: (order.index(x.name)
                                                 if x.name in order else 99,
                                                 -x.mv))
            else:
                order = g.cfg.get("tutor_order", ())
                pick = min(cands, key=lambda x: (order.index(x.name)
                                                 if x.name in order else 99,
                                                 -x.mv))
            g.library.remove(pick)
            g.library.append(pick)          # on top
            g.tutor_log.append((g.turn, pick.name,
                                sum(1 for p in g.board if p.card.is_land),
                                len(g.hand), int(g.commander_cast)))
    elif sc == "mastery" and not is_copy:
        # Mizzix's Mastery. Base {3}{R} exiles and copies ONE instant/sorcery
        # from the graveyard; overload {5}{R}{R}{R} does it to every one.
        #
        # Overload is an alternative cost, and so is miracle, so the two cannot
        # be combined -- a Mastery miracled for {2} off Lorehold gets the
        # single-target mode only. Modelling it as always-overloaded (and at
        # the wrong overload cost) massively overstated the card.
        pool = [x for x in g.graveyard
                if "Instant" in x.types or "Sorcery" in x.types]
        if g.last_paid < 9 and pool:
            pool = [max(pool, key=lambda x: x.mv)]   # single target
        for x in pool:
            g.graveyard.remove(x)
            g.m["mastery_copies"] += 1
            g.m["mv_cheated"] += x.free_mv
            g.m["total_mv_cast"] += x.free_mv
            g.m["spells_cast"] += 1
            apply_spell_effects(g, x, is_copy=True)
    elif sc == "wheel" and not is_copy:
        discard_triggers(g, len(g.hand))
        g.graveyard.extend(g.hand)
        g.hand = []
        _draw_into_hand(g, 7)
    if "wipe" in card.tags:
        OPP.resolve_own_wipe(g, spare_own="onesided" in card.tags)
    if card.tokens:
        make_tokens(g, *card.tokens)
    deal_pod_damage(g, card.pod_damage)
    if card.discards and not is_copy:
        discard_triggers(g, card.discards)
    if is_copy and was_cast:
        on_cast_triggers(g, card, is_copy=True)


def resolve_spell(g, card, paid):
    g.last_paid = paid
    g.m["spells_cast"] += 1
    g.m["total_mv_cast"] += card.mv
    g.m["mv_cheated"] += max(0.0, card.mv - paid)
    if card.name in g.cfg.get("watch", ()):
        g.m["cast_test_card"] = 1
        g.m["test_card_turn"] = min(g.m["test_card_turn"], g.turn)

    apply_spell_effects(g, card)

    on_cast_triggers(g, card)

    if card.is_permanent:
        g.board.append(Permanent(card=card, sick=True))
    else:
        g.graveyard.append(card)

    # Storm-Kiln Artist: a Treasure per instant/sorcery
    if ("Instant" in card.types or "Sorcery" in card.types) and \
            g.has("Storm-Kiln Artist"):
        g.treasures += 1
        g.m["treasures_made"] += 1


def hold_for_miracle(g, card):
    """Should we decline to hardcast this and set it up for a miracle instead?

    Paying seven mana for a seven-drop when you could pay {2} for it is the
    single biggest mistake a naive policy makes in this deck. But holding only
    works if you can get the card back on top of your library - otherwise it
    rots in hand forever. So the rule is conditional on actually controlling a
    way to put it there.
    """
    if not (g.commander_cast or g.has("Molecule Man")):
        return False
    if len(g.hand) > g.cfg.get("hand_cap", 7):
        return False                       # hand is clogged, just cast it
    can_set_top = g.has("Library of Leng") or any(
        g.has(n) for n in TOP_SETTERS if n != "Library of Leng")
    if not can_set_top:
        return False
    if miracle_value(g, card) < g.cfg.get("hold_min_value", 3.0):
        return False
    return True


def main_phase(g, reserve=0):
    """reserve: mana left untapped for miracle windows on opponents' turns.

    This is not a detail. Lorehold's rummage creates three miracle windows per
    round on other players' turns, and your lands do not untap until your own
    untap step, so hitting them means deliberately not spending mana on your
    turn. It is a real cost, and it is exactly why the deck runs Victory Chimes
    and Bender's Waterskin, which untap on EVERY untap step.
    """
    while True:
        units = mana_units(g)

        if not g.commander_cast:
            ccost = dict(g.commander.cost)
            ccost["gen"] = ccost.get("gen", 0) + g.commander_tax
            if can_pay(ccost, units) is not None:
                idx = g.spells_this_turn
                g.spells_this_turn += 1
                pay(g, ccost, units)
                if OPP.countered(g, g.commander, idx):
                    g.m["countered"] += 1
                    g.commander_tax += 2
                    continue
                g.board.append(Permanent(card=g.commander, sick=False))
                g.commander_cast = True
                g.m["spells_cast"] += 1
                continue

        n_lands = sum(1 for p in g.board if p.card.is_land)
        options = []
        for c in g.hand:
            if c.is_land or hold_for_miracle(g, c):
                continue
            # Hold an MDFC for its land face while the mana base is short.
            if c.land_face and n_lands < g.cfg.get("mdfc_land_floor", 5):
                continue
            if "wipe" in c.tags and not OPP.should_cast_own_wipe(g):
                continue
            cost = reduce_cost(g, c)
            idx = can_pay(cost, units)
            if idx is not None and len(units) - len(idx) >= reserve:
                options.append((c, cost))
        if not options:
            break

        card, cost = max(options, key=lambda it: (it[0].priority, it[0].mv))
        if card.script == "mastery":
            over = {"gen": 5, "R": 3}
            if can_pay(over, units) is not None:
                cost = over        # overload if the mana is there
        idx = g.spells_this_turn
        g.spells_this_turn += 1
        paid = pay(g, cost, units)
        g.hand.remove(card)
        if OPP.countered(g, card, idx):
            g.m["countered"] += 1
            g.graveyard.append(card)
            if card.name in g.cfg.get("watch", ()):
                g.m["test_card_countered"] += 1
                g.m["test_card_answered"] += 1
            continue
        resolve_spell(g, card, paid)


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

def combat(g):
    attackers = [p for p in g.board
                 if p.card.is_creature and not p.tapped and not p.sick]

    # The Dawning Archaic: on attack, cast a free instant/sorcery from the yard
    if any(p.card.name == "The Dawning Archaic" for p in attackers):
        pool = [c for c in g.graveyard
                if "Instant" in c.types or "Sorcery" in c.types]
        if pool:
            best = max(pool, key=lambda c: c.free_mv)
            g.graveyard.remove(best)
            g.m["free_casts"] += 1
            g.m["mv_cheated"] += best.free_mv
            g.m["total_mv_cast"] += best.free_mv
            g.m["spells_cast"] += 1
            if best.script == "treasures":
                g.treasures += best.treasures
            if best.script == "soulfire":
                for _ in range(3):
                    if g.library:
                        deal_pod_damage(g, float(g.library.pop().mv))
            if best.tokens:
                make_tokens(g, *best.tokens)
            deal_pod_damage(g, best.pod_damage)
            n_snipe = sum(1 for p in g.board if p.card.name == "Guttersnipe")
            deal_pod_damage(g, 6.0 * n_snipe)

    if not attackers:
        g.damage_by_turn.append(0.0)
        return
    if any(p.card.name == "Goldspan Dragon" for p in attackers):
        g.treasures += 1
        g.m["treasures_made"] += 1
    prowess = sum(1 for p in attackers
                  if p.card.name in ("Monastery Mentor", "Monk token"))
    dmg = OPP.damage_through(g, attackers) + prowess * g.noncreature_this_turn
    for p in attackers:
        p.tapped = True
    g.m["damage"] += dmg
    g.m["combat_damage"] += dmg
    g.damage_by_turn.append(dmg)
    OPP.damage_single(g, dmg)
    if g.result == "win" and g.m["turn_lethal"] == 99:
        g.m["turn_lethal"] = g.turn


# ---------------------------------------------------------------------------
# Turn loop
# ---------------------------------------------------------------------------

def opponent_upkeep_windows(g):
    """Lorehold's rummage: three extra miracle windows per round."""
    if not g.commander_cast:
        return
    cross_turn = sum(1 for p in g.board if "cross_turn" in p.card.tags)
    for _ in g.opponents:
        g.float_mana += cross_turn      # these untap on every untap step
        if not g.hand:
            continue
        # Discard the worst card. Lands score lowest on miracle value, but
        # pitching a land you still need to hit your drops is a real mistake —
        # only treat lands as chaff once the mana base is developed.
        my_lands = sum(1 for p in g.board if p.card.is_land)
        pool = g.hand
        if my_lands < g.cfg.get("land_floor", 8):
            nonlands = [c for c in g.hand if not c.is_land]
            if nonlands:
                pool = nonlands
        worst = min(pool, key=lambda c: miracle_value(g, c))
        if g.has("Library of Leng"):
            # discard the BEST miracle target instead: it goes on top, and we
            # immediately draw it. This is the deck's core loop.
            best = max(g.hand, key=lambda c: miracle_value(g, c))
            if miracle_value(g, best) > 0:
                worst = best
                g.hand.remove(worst)
                g.library.append(worst)
            else:
                g.hand.remove(worst)
                g.graveyard.append(worst)
        else:
            g.hand.remove(worst)
            g.graveyard.append(worst)
        # Library of Leng redirects where the card goes, but it is still a
        # discard, so Monument to Endurance still triggers either way.
        g.monument_used = set()          # a new turn = the modes reset
        discard_triggers(g, 1)
        g.spells_this_turn = 0
        g.noncreature_this_turn = 0
        g.bombardment_fired_this_turn = False   # a new turn = a new trigger
        g.dv_fired_this_turn = False
        # A free top-setter can be used before EACH draw event, and Lorehold's
        # rummage supplies three extra ones per round on opponents' turns.
        set_top(g)
        miracle_window(g, off_turn=True)


def take_turn(g):
    g.turn += 1
    g.spells_this_turn = 0
    g.noncreature_this_turn = 0
    g.bombardment_fired_this_turn = False
    g.dv_fired_this_turn = False
    g.monument_used = set()
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.land_drops = 1
    g.land_drops_used = 0

    # Land Tax: if an opponent controls more lands, fetch up to three basic
    # Plains to hand. Two effects, both of which matter here: it fixes land
    # drops, and it fills the hand -- and an empty hand is what starves
    # Lorehold's rummage, which supplies three of the four miracle windows.
    if g.has("Land Tax"):
        my_lands = sum(1 for p in g.board if p.card.is_land)
        if my_lands < min(g.turn, 10):
            basics = [x for x in g.library if x.name == "Plains"][:3]
            for b in basics:
                g.library.remove(b)
                g.hand.append(b)
            g.m["land_tax_fetches"] += len(basics)

    # Smothering Tithe / Monologue Tax upkeep value
    if g.has("Smothering Tithe"):
        g.treasures += 2
        g.m["treasures_made"] += 2
    if g.has("Monologue Tax"):
        n = g.cfg.get("monologue_tax_rate", 2)   # 3 opponents, 2nd spell each
        g.treasures += n
        g.m["treasures_made"] += n

    for engine, free in (("Galvanoth", True), ("Radiant Scrollwielder", False)):
        if not g.has(engine) or not g.library:
            continue
        top = g.library[-1]
        if "Instant" not in top.types and "Sorcery" not in top.types:
            continue
        if free:
            g.library.pop()
            g.m["upkeep_free_casts"] += 1
            g.m["mv_cheated"] += top.free_mv
            resolve_spell(g, top, 0)
        else:
            units = mana_units(g)
            cost = reduce_cost(g, top)
            if can_pay(cost, units) is not None:
                g.library.pop()
                paid = pay(g, cost, units)
                g.m["upkeep_free_casts"] += 1
                resolve_spell(g, top, paid)

    set_top(g)
    miracle_window(g)          # your draw step
    play_land(g)
    main_phase(g, reserve=g.cfg.get("miracle_reserve", 2) if g.commander_cast else 0)
    combat(g)
    main_phase(g, reserve=g.cfg.get("miracle_reserve", 2) if g.commander_cast else 0)

    g.float_mana = len(mana_units(g))
    g.m["mana_floated"] += g.float_mana
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

    while g.m["extra_turns"] > 0:
        g.m["extra_turns"] -= 1
        for p in g.board:
            p.tapped = False
            p.sick = False
        g.spells_this_turn = 0
        miracle_window(g)
        main_phase(g)
        combat(g)

    opponent_upkeep_windows(g)


def simulate(deck, commander, cfg, seed):
    g = LoreholdGame(deck, commander, cfg, seed)
    g.opening_hand()
    for _ in range(cfg.get("turns", 10)):
        take_turn(g)
        if g.result is not None:
            break
    out = dict(g.m)
    out["result"] = g.result or "timeout"
    out["turns_played"] = g.turn
    out["opponents_killed"] = sum(1 for o in g.opponents if not o.alive)
    out["final_life"] = g.your_life
    out["damage_by_turn"] = g.damage_by_turn
    out["final_board_power"] = sum(g.power_of(p) for p in g.board
                                   if p.card.is_creature)
    out["miracle_rate"] = (out["miracle_hits"] / out["miracle_windows"]
                           if out["miracle_windows"] else 0.0)
    out["test_card_resolved"] = 1 if (out["cast_test_card"] and
                                      not out["test_card_answered"]) else 0
    out["won"] = 1 if g.result == "win" else 0
    out["lost"] = 1 if g.result == "loss" else 0
    out["tutor_log"] = g.tutor_log
    return out
