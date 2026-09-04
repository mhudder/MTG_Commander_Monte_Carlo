"""
edhmc.engine — a Monte Carlo "goldfish+" engine for Commander decks.

Scope, stated honestly:
  MODELLED   shuffling, mulligans, land drops, tapped/untapped lands, colour
             requirements (incl. {C}), mana rocks/dorks, cost reduction,
             a greedy casting policy, card draw, token generation, static
             anthems / P-T setters, per-turn engine activations, and combat
             damage against an unblocking pod.
  NOT MODELLED  opponents' removal, counterspells, blockers, board wipes,
             politics, stack interaction, or your own tutoring/decision
             skill. Damage numbers are therefore upper bounds. Use the
             *paired difference* between two configurations, never the
             absolute value.

The engine is deliberately card-agnostic: a card is a bag of attributes plus
an optional scripted hook. ~30 cards in a 100-card deck actually need scripts;
the rest are correctly handled as "a body with a mana cost and a type line".
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from edhmc import opponents as OPP

COLORS = ("W", "U", "B", "R", "G", "C")


# ----------------------------------------------------------------------------
# Card model
# ----------------------------------------------------------------------------

@dataclass
class Card:
    name: str
    types: frozenset          # {"Artifact","Creature"} etc. — drives Rendmaw
    cost: dict = field(default_factory=dict)   # {"G":2, "B":1, "C":1, "gen":3}
    power: int = 0
    toughness: int = 0
    # land data
    is_land: bool = False
    produces: frozenset = frozenset()   # colours this land can tap for
    tapped: bool = False                # enters tapped
    # nonland mana ability
    mana_ability: Optional[tuple] = None  # (amount, frozenset(colors))
    # scripted behaviour
    script: Optional[str] = None
    miracle_cost: dict = field(default_factory=dict)  # printed miracle cost
    treasures: int = 0
    pod_damage: float = 0.0   # direct damage to the 3-opponent pod
    discards: int = 0         # cards discarded as part of casting it
    land_face: tuple = ()     # MDFC: (produces, enters_tapped) for the back
    lifegain: float = 0.0     # life gained on resolution
    drain: float = 0.0        # each opponent loses N and you gain N
    lifelink: bool = False
    x_pips: int = 0           # generic pips that are actually {X}
    alt_costs: tuple = ()     # ((cost_dict, "tag"), ...) modal / alternative costs
    tokens: tuple = ()        # (count, power, toughness) made on resolution
    priority: float = 0.0     # higher = cast sooner when both are affordable
    threat: float = 0.0       # how badly opponents want it gone (0 = derive it)
    tags: frozenset = frozenset()

    @property
    def mv(self) -> int:
        return sum(v for k, v in self.cost.items())

    @property
    def free_mv(self) -> float:
        """Mana value when copied or cast without paying its cost.

        X is 0 everywhere but the stack, so {X}{B}{B} has MV 2 in the
        graveyard -- not 0, and not its cast value either. `x_pips` records how
        much of `cost` stands in for {X}.

        Note what does NOT belong here. Toxic Deluge is {2}{B} and Culling
        Ritual is {2}{B}{G}; their X is a life payment and a count of destroyed
        permanents, not part of the mana cost, so their mana value is fixed at
        3 and 4. Scryfall says so directly for Toxic Deluge: "you'll still
        choose a value for X and pay X life. This is because it doesn't have
        {X} in its mana cost."
        """
        return float(max(0, self.mv - self.x_pips))

    @property
    def multitype(self) -> bool:
        return len(self.types) >= 2

    @property
    def is_creature(self) -> bool:
        return "Creature" in self.types

    @property
    def is_permanent(self) -> bool:
        return bool(self.types & {"Creature", "Artifact", "Enchantment",
                                  "Planeswalker", "Land", "Battle"})


@dataclass
class Permanent:
    card: Card
    tapped: bool = False
    sick: bool = True
    counters: int = 0
    is_token: bool = False
    impending: int = 0        # turn on which it becomes a creature
    base_p: int = 0
    base_t: int = 1


# ----------------------------------------------------------------------------
# Mana
# ----------------------------------------------------------------------------

def can_pay(cost: dict, units: list[frozenset]) -> Optional[list[int]]:
    """Greedy-with-fallback payment solver.

    `units` is a list of colour-sets, one entry per available mana. Returns the
    indices consumed, or None. Coloured pips are assigned before generic, and
    within a pip the most *constrained* source is spent first, which is optimal
    for the small, low-conflict pools a two-colour deck produces.
    """
    remaining = list(range(len(units)))
    used: list[int] = []

    for color in ("W", "U", "B", "R", "G", "C"):
        need = cost.get(color, 0)
        for _ in range(need):
            cands = [i for i in remaining if color in units[i]]
            if not cands:
                return None
            # spend the least flexible source that works
            best = min(cands, key=lambda i: len(units[i]))
            remaining.remove(best)
            used.append(best)

    gen = cost.get("gen", 0)
    if gen > len(remaining):
        return None
    # pay generic with the least flexible leftovers
    remaining.sort(key=lambda i: len(units[i]))
    used.extend(remaining[:gen])
    return used


# ----------------------------------------------------------------------------
# Game state
# ----------------------------------------------------------------------------

class Game:
    def __init__(self, deck: list[Card], commander: Card, cfg: dict,
                 rng: random.Random, seed_for_pod: int = 0):
        self.rng = rng
        self.cfg = cfg
        self.library = list(deck)
        self.rng.shuffle(self.library)
        self.hand: list[Card] = []
        self.board: list[Permanent] = []
        self.graveyard: list[Card] = []
        self.commander = commander
        self.commander_cast = False
        self.commander_tax = 0

        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed_for_pod)
        OPP.init_life(self)
        self.spells_this_turn = 0

        self.turn = 0
        self.land_drops = 1
        self.land_drops_used = 0

        # metrics
        self.m = {
            "damage": 0.0,
            "cards_drawn": 0,
            "mana_floated": 0,
            "mana_spent": 0,
            "rendmaw_triggers": 0,
            "tokens_made": 0,
            "spells_cast": 0,
            "turn_lethal": 99,
            "stranded_mv": 0,      # mana value sitting uncastable in hand
            "clamp_activations": 0,
            "fodder_turns": 0,
            "cast_test_card": 0,
            "test_card_turn": 99,
            "removal_eaten": 0,
            "ae_removal_eaten": 0,
            "wipes_suffered": 0,
            "drain_damage": 0.0,
            "baba_activations": 0,
            "impending_casts": 0,
            "own_wipes_cast": 0,
            "countered": 0,
            "protected": 0,
            "test_card_answered": 0,
            "test_card_removed": 0,
            "test_card_countered": 0,
        }
        self.damage_by_turn: list[float] = []
        self.made_token_this_turn = False
        self.beast_active = False
        self.stampede_bonus = 0
        self.creature_died_this_turn = False

    # -- library ops ---------------------------------------------------------

    def draw(self, n=1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())
                self.m["cards_drawn"] += 1

    def opening_hand(self):
        """London mulligan to 7, keeping on a 2-5 land heuristic."""
        for mulls in range(4):
            self.hand = [self.library.pop() for _ in range(7)]
            lands = sum(1 for c in self.hand if c.is_land)
            if 2 <= lands <= 5:
                break
            self.library.extend(self.hand)
            self.rng.shuffle(self.library)
            self.hand = []
        else:
            self.hand = [self.library.pop() for _ in range(7)]
        # bottom `mulls` cards (worst = highest MV nonland, crudely)
        for _ in range(mulls):
            if self.hand:
                worst = max(self.hand, key=lambda c: (not c.is_land, c.mv))
                self.hand.remove(worst)
                self.library.insert(0, worst)

    # -- tokens --------------------------------------------------------------

    def make_tokens(self, n: int, p: int, t: int, subtype: str = "", tapped=False):
        if self.has("Primal Vigor"):
            n *= 2
        for _ in range(n):
            card = Card(name=f"{subtype or 'Token'} token",
                        types=frozenset({"Creature"}), power=p, toughness=t)
            perm = Permanent(card=card, tapped=tapped, sick=True,
                             is_token=True, base_p=p, base_t=t)
            # Metallic Mimic: named Bird
            if subtype == "Bird" and self.has("Metallic Mimic"):
                perm.counters += 1
            self.board.append(perm)
            self.m["tokens_made"] += 1
        self.made_token_this_turn = True

    def has(self, name: str) -> bool:
        return any(p.card.name == name for p in self.board)

    # -- non-combat damage ---------------------------------------------------

    def deal_pod_damage(self, amount: float, each: bool = True):
        """`each=True` means 'each opponent loses N' (amount is the pod total)."""
        if amount <= 0:
            return
        self.m["damage"] += amount
        self.m["drain_damage"] += amount
        if self.damage_by_turn:
            self.damage_by_turn[-1] += amount
        n = max(1, len(OPP.living(self)))
        if each:
            OPP.damage_each(self, amount / n)
        else:
            OPP.damage_single(self, amount)
        if self.result == "win" and self.m["turn_lethal"] == 99:
            self.m["turn_lethal"] = self.turn

    def on_creature_death(self, n: int = 1):
        self.creature_died_this_turn = True
        """Aristocrats drain. Each Blood Artist effect costs the pod 3 life per
        creature that dies (1 from each of three opponents).

        This is the Rendmaw analogue of the Guttersnipe hole in the Lorehold
        engine: in a deck that makes and loses a dozen tokens, a board wipe with
        Blood Artist out is thirty-plus damage that was going entirely
        uncounted.
        """
        _ = n
        drainers = sum(1 for p in self.board
                       if p.card.name in ("Blood Artist",
                                          "The Meathook Massacre"))
        if drainers:
            self.deal_pod_damage(3.0 * n * drainers)

    # -- P/T resolution ------------------------------------------------------

    def power_of(self, perm: Permanent) -> int:
        if self.has("March of the World Ooze"):
            base = 6
        else:
            base = perm.base_p if perm.is_token else perm.card.power
        p = base + perm.counters + self.stampede_bonus
        if self.has("Beastmaster Ascension") and self.beast_active:
            p += 5
        return p

    def toughness_of(self, perm: Permanent) -> int:
        if self.has("March of the World Ooze"):
            base = 6
        else:
            base = perm.base_t if perm.is_token else perm.card.toughness
        return base + perm.counters

    # -- Rendmaw -------------------------------------------------------------

    def play_card_trigger(self, card: Card):
        """`Play` = cast a spell or play a land. 2+ card types -> Bird.

        "EACH PLAYER creates a tapped 2/2 black Bird with flying. The tokens
        are goaded for the rest of the game." Both halves matter: the
        opponents' Birds are extra blockers against you, and because you are
        the goader they are forced to swing at each other rather than at you
        (see opponents.goaded_combat).

        Your own Birds are goaded too, but `combat()` already attacks with
        everything that can, so that half needs no separate handling.
        """
        if not card.multitype:
            return
        n = 1 + sum(1 for p in self.board if p.card.name == "Roaming Throne")
        if not self.commander_cast:
            return                     # no Rendmaw on the battlefield, no trigger
        self.m["rendmaw_triggers"] += n
        self.make_tokens(n, 2, 2, "Bird", tapped=True)
        self.give_opponents_birds(n)

    def give_opponents_birds(self, n: int):
        # Primal Vigor is symmetric — "if one or more tokens WOULD BE CREATED,
        # twice that many of those tokens are created instead" applies to
        # every player, not just you. make_tokens() already doubles yours.
        if self.has("Primal Vigor"):
            n *= 2
        for o in OPP.living(self):
            o.goaded_birds += n


# ----------------------------------------------------------------------------
# Turn loop
# ----------------------------------------------------------------------------

def available_mana(g: Game) -> list[frozenset]:
    """Enumerate one entry per point of mana available this turn."""
    units: list[frozenset] = []
    any_color = frozenset({"B", "G", "C"})
    all_lands_any = g.has("Dryad of the Ilysian Grove")

    for p in g.board:
        if p.tapped:
            continue
        c = p.card
        if c.is_land:
            src = any_color if all_lands_any else c.produces
            amt = 2 if "bounce" in c.tags else 1
            units.extend([src] * amt)
        elif c.mana_ability:
            if c.is_creature and p.sick:
                continue
            amt, colors = c.mana_ability
            units.extend([colors] * amt)
        elif c.name == "Everywhere token":
            units.append(any_color)

    # Enduring Vitality: creatures tap for mana of any colour
    if g.has("Enduring Vitality"):
        for p in g.board:
            if p.card.is_creature and not p.tapped and not p.sick and not p.card.mana_ability:
                units.append(any_color)
    return units


def cost_after_reduction(g: Game, card: Card) -> dict:
    cost = dict(card.cost)
    if "Artifact" in card.types and g.has("Foundry Inspector"):
        cost["gen"] = max(0, cost.get("gen", 0) - 1)
    if card.name == "The Great Henge":
        best = max([g.power_of(p) for p in g.board if p.card.is_creature] or [0])
        cost["gen"] = max(0, cost.get("gen", 0) - best)
    return cost


def play_land(g: Game):
    """Prefer an untapped land that fixes a colour we are short on."""
    if g.land_drops_used >= g.land_drops:
        return
    lands = [c for c in g.hand if c.is_land]
    mdfc = [c for c in g.hand if c.land_face and not c.is_land]
    if mdfc and len(lands) == 0:
        # No real land in hand: the back face is why you play these.
        lands = mdfc
    elif mdfc and sum(1 for p in g.board if p.card.is_land) < g.cfg.get("mdfc_land_floor", 5):
        lands = lands + mdfc
    if not lands:
        return
    have = set()
    for p in g.board:
        if p.card.is_land:
            have |= p.card.produces

    def face(c: Card):
        if c.is_land:
            return c.produces, c.tapped
        return frozenset(c.land_face[0]), c.land_face[1]

    def score(c: Card):
        prod, tapped = face(c)
        return (len(prod - have), not tapped, len(prod), c.multitype)

    best = max(lands, key=score)
    g.hand.remove(best)
    prod, tapped = face(best)
    if not best.is_land:                      # played as its land face
        best = Card(name=best.name + " (land)", types=frozenset({"Land"}),
                    is_land=True, produces=prod, tapped=tapped)
    perm = Permanent(card=best, tapped=tapped, sick=True,
                     base_p=best.power, base_t=best.toughness)
    g.board.append(perm)
    g.land_drops_used += 1
    g.play_card_trigger(best)
    run_etb(g, perm)


def main_phase(g: Game, precombat: bool = False):
    """Greedy: repeatedly cast the highest-priority affordable spell.

    In the precombat main we only deploy effects that raise *this turn's*
    damage (anthems, pump, P/T setters). Everything else waits for the
    postcombat main so it does not tap creatures out of the attack. Rendmaw
    Birds enter tapped and summoning sick, so there is almost never a reason
    to deploy a body before combat.
    """
    while True:
        units = available_mana(g)

        # commander first once affordable
        if not g.commander_cast and not precombat:
            ccost = dict(g.commander.cost)
            ccost["gen"] = ccost.get("gen", 0) + g.commander_tax
            pay = can_pay(ccost, units)
            if pay is not None:
                spend(g, pay, units)
                idx = g.spells_this_turn
                g.spells_this_turn += 1
                if OPP.countered(g, g.commander, idx):
                    g.m["countered"] += 1
                    g.commander_tax += 2
                    continue
                perm = Permanent(card=g.commander, sick=True)
                g.board.append(perm)
                g.commander_cast = True
                g.m["spells_cast"] += 1
                g.make_tokens(1, 2, 2, "Bird", tapped=True)   # ETB
                g.give_opponents_birds(1)                     # each player
                continue

        options = []
        for c in g.hand:
            if c.is_land:
                continue
            if precombat and "pump" not in c.tags:
                continue
            # do not wrath your own winning board
            if "wipe" in c.tags and not OPP.should_cast_own_wipe(g):
                continue
            pay = can_pay(cost_after_reduction(g, c), units)
            if pay is not None:
                options.append((c, pay, None))
                continue
            # ALTERNATIVE COSTS. A card is not one cost: Impending deploys
            # Overlord of the Hauntwoods for {1}{G}{G} instead of {3}{G}{G},
            # at the price of it being a noncreature enchantment for four
            # turns. Without this the engine only sees the full cost.
            for alt_cost, tag in c.alt_costs:
                alt = can_pay(alt_cost, units)
                if alt is not None:
                    options.append((c, alt, tag))
                    break
        if not options:
            break

        def rank(item):
            c = item[0]
            ramp_bonus = 3.0 if ("ramp" in c.tags and g.turn <= 5) else 0.0
            return (c.priority + ramp_bonus, c.mv)

        card, pay, alt_tag = max(options, key=rank)
        spend(g, pay, units)
        g.hand.remove(card)

        idx = g.spells_this_turn
        g.spells_this_turn += 1
        if OPP.countered(g, card, idx):
            g.m["countered"] += 1
            g.graveyard.append(card)
            if card.name in g.cfg.get("watch", ()):
                g.m["test_card_answered"] += 1
                g.m["test_card_countered"] += 1
            continue

        g.m["spells_cast"] += 1
        if card.name in g.cfg.get("watch", ()):
            g.m["cast_test_card"] = 1
            g.m["test_card_turn"] = min(g.m["test_card_turn"], g.turn)
        g.play_card_trigger(card)

        if "wipe" in card.tags:
            OPP.resolve_own_wipe(g, spare_own="onesided" in card.tags)
        if alt_tag == "impending":
            # enters as a noncreature enchantment; the body arrives later
            g.m["impending_casts"] += 1
        if card.script == "stampede":
            # +X/+X and trample until end of turn, X = greatest power you
            # control. In a deck that goes this wide it is a finisher, and the
            # engine was previously casting it for literally no effect.
            g.stampede_bonus += max([g.power_of(p) for p in g.board
                                     if p.card.is_creature] or [0])
        if "Creature" in card.types or "Artifact" in card.types or \
           "Enchantment" in card.types or "Planeswalker" in card.types:
            perm = Permanent(card=card, sick=True,
                             base_p=card.power, base_t=card.toughness)
            if alt_tag == "impending":
                perm.impending = g.turn + 4
            g.board.append(perm)
            run_etb(g, perm)
        else:
            g.graveyard.append(card)


def spend(g: Game, pay_idx: list[int], units: list[frozenset]):
    """Mark sources tapped, cheapest-to-lose first.

    Tapping order matters: a creature tapped for mana in the precombat main
    phase cannot attack. A real pilot taps lands and non-creature rocks before
    dorks, and only taps the team via Enduring Vitality as a last resort. Order
    by "combat value we give up".
    """
    n = len(pay_idx)
    g.m["mana_spent"] += n

    def tap_cost(p: Permanent) -> tuple:
        c = p.card
        if c.is_land or c.name == "Everywhere token":
            return (0, 0)
        if c.mana_ability and not c.is_creature:
            return (1, 0)
        if c.mana_ability and c.is_creature:
            return (2, g.power_of(p))
        return (3, g.power_of(p))       # Enduring Vitality fodder

    sources = []
    for p in g.board:
        if p.tapped:
            continue
        c = p.card
        usable = (c.is_land or c.name == "Everywhere token"
                  or (c.mana_ability and not (c.is_creature and p.sick))
                  or (g.has("Enduring Vitality") and c.is_creature and not p.sick))
        if usable:
            sources.append(p)
    sources.sort(key=tap_cost)

    left = n
    for p in sources:
        if left <= 0:
            break
        c = p.card
        amt = 2 if "bounce" in c.tags else (c.mana_ability[0] if c.mana_ability else 1)
        p.tapped = True
        left -= amt


# ----------------------------------------------------------------------------
# Scripted card hooks
# ----------------------------------------------------------------------------

def run_etb(g: Game, perm: Permanent):
    s = perm.card.script
    if s == "khalni_garden":
        g.make_tokens(1, 0, 1, "Plant")
    elif s == "woe_strider":
        g.make_tokens(1, 0, 1, "Goat")
    elif s == "grave_titan":
        g.make_tokens(2, 2, 2, "Zombie")
    elif s == "overlord":
        g.board.append(Permanent(card=Card(name="Everywhere token",
                                           types=frozenset({"Land"}), is_land=False),
                                 tapped=False, sick=False))
    elif s == "gearhulk":
        for p in g.board:
            if p.card.is_creature:
                p.counters += 4
                break
    elif s == "predation":
        # A 4/4 for each creature the target opponent controls, and each token
        # fights one of them. Sized off the pod's own board development.
        n = int(max(1, min(o.creatures for o in g.opponents)))
        g.make_tokens(n, 4, 4, "Horror")
        for o in g.opponents[:1]:
            o.creatures = max(0.0, o.creatures - n)
    elif s == "stampede":
        pass
    elif s == "draw1":
        g.draw(1)
    elif s == "draw2":
        g.draw(2)
    if g.has("The Great Henge") and perm.card.is_creature and not perm.is_token:
        g.draw(1)
        perm.counters += 1


def upkeep(g: Game):
    for p in list(g.board):
        s = p.card.script
        if s == "bitterblossom":
            g.make_tokens(1, 1, 1, "Faerie")
        elif s == "ophiomancer":
            if not any(x.is_token and x.card.name.startswith("Snake") for x in g.board):
                g.make_tokens(1, 1, 1, "Snake")
        elif s == "tendershoot":
            # "At the beginning of EACH upkeep, create a 1/1 Saproling." That
            # is one per player per round, not one per round — this loop runs
            # only on your turn, so it stands in for the whole round.
            # Ascend then gives Saprolings +2/+2; it does NOT double the count,
            # which is what the old `2 if >=10 else 1` was doing.
            n_upkeeps = 1 + len(OPP.living(g))
            g.make_tokens(n_upkeeps, 1, 1, "Saproling")
            if len(g.board) >= 10:            # city's blessing
                for q in g.board:
                    if q.is_token and q.card.name.startswith("Saproling"):
                        q.counters = max(q.counters, 2)
        elif s == "grist":
            g.make_tokens(1, 1, 1, "Insect")
    # Arasta: opponents cast instants/sorceries at some rate
    if g.has("Arasta of the Endless Web"):
        if g.rng.random() < g.cfg.get("opp_instant_rate", 0.8):
            g.make_tokens(1, 1, 2, "Spider")


def activations(g: Game):
    """Post-main engine activations that consume leftover mana."""
    units = available_mana(g)

    # Skullclamp: {1} equip a 1-toughness creature -> it dies -> draw 2.
    if g.has("Skullclamp"):
        if any(p.card.is_creature and g.toughness_of(p) == 1 for p in g.board):
            g.m["fodder_turns"] += 1
        for _ in range(g.cfg.get("clamp_cap", 4)):
            fodder = [p for p in g.board
                      if p.card.is_creature and g.toughness_of(p) == 1]
            if not fodder or not units:
                break
            pay = can_pay({"gen": 1}, units)
            if pay is None:
                break
            for i in sorted(pay, reverse=True):
                units.pop(i)
            g.m["clamp_activations"] += 1
            victim = min(fodder, key=lambda p: g.power_of(p))
            g.board.remove(victim)
            g.on_creature_death(1)
            g.draw(2)
            spend(g, [0], [frozenset({"C"})])

    # Idol of Oblivion: tap to draw if you made a token
    if g.has("Idol of Oblivion") and g.made_token_this_turn:
        g.draw(1)

    # Steel Overseer: +1/+1 counter on each artifact creature
    if g.has("Steel Overseer"):
        for p in g.board:
            if "Artifact" in p.card.types and p.card.is_creature:
                p.counters += 1

    # Baba Lysaga: {T}, sac up to three permanents. Needs 3+ CARD TYPES among
    # them -- which is exactly what this deck is made of, so the check is
    # whether three distinct type-sets are available, not just three bodies.
    if g.has("Baba Lysaga, Night Witch"):
        fodder = [p for p in g.board
                  if not p.card.is_land and p.card is not g.commander
                  and p.card.name != "Baba Lysaga, Night Witch"]
        chosen, seen = [], set()
        for p in sorted(fodder, key=lambda p: (p.is_token is False,
                                               g.power_of(p))):
            new = p.card.types - seen
            if new or len(chosen) < 3:
                chosen.append(p)
                seen |= p.card.types
            if len(chosen) == 3:
                break
        if len(seen) >= 3 and len(chosen) == 3:
            for p in chosen:
                g.board.remove(p)
                if p.card.is_creature:
                    g.on_creature_death(1)
            g.deal_pod_damage(9.0)      # each of 3 opponents loses 3
            g.draw(3)
            g.m["baba_activations"] += 1

    # Ashnod's Altar: sacrifice spare tokens for mana. Modelled conservatively
    # (only genuine excess) because the real value here is not the mana but the
    # deaths it manufactures for Blood Artist and The Meathook Massacre.
    # Only sacrifice when the deaths are actually worth something. The mana the
    # Altar produces arrives after the main phase in this engine and so cannot
    # be spent; modelling the cost without the benefit made it look like a bad
    # card, which was a bug in the model, not a finding about the card.
    if g.has("Ashnod's Altar") and (g.has("Blood Artist")
                                    or g.has("The Meathook Massacre")):
        spare = [p for p in g.board if p.is_token and p.card.is_creature]
        for p in spare[:max(0, len(spare) - g.cfg.get("altar_keep", 6))][:2]:
            g.board.remove(p)
            g.on_creature_death(1)

    # Village Rites: sacrifice a creature, draw two.
    if any(c.name == "Village Rites" for c in g.hand) and units:
        chaff = [p for p in g.board if p.is_token and p.card.is_creature]
        if chaff:
            g.hand.remove(next(c for c in g.hand if c.name == "Village Rites"))
            g.board.remove(chaff[0])
            g.on_creature_death(1)
            g.draw(2)

    # Deathreap Ritual: a card at EACH end step where a creature died. Four
    # end steps a round in a four-player game, and creatures die constantly.
    if g.has("Deathreap Ritual") and g.creature_died_this_turn:
        g.draw(1 + sum(1 for _ in range(3)
                       if g.rng.random() < g.cfg.get("opp_death_rate", 0.55)))

    # Erebos / Dockside Chef / Grim Backwoods style sac-for-card, once/turn
    if (g.has("Erebos, Bleak-Hearted") or g.has("Dockside Chef")) and units:
        chaff = [p for p in g.board if p.is_token and not p.sick
                 and g.power_of(p) <= 2]
        if chaff:
            g.board.remove(chaff[0])
            g.on_creature_death(1)
            g.draw(1)


def combat(g: Game):
    attackers = [p for p in g.board
                 if p.card.is_creature and not p.tapped and not p.sick
                 and not (p.impending and g.turn < p.impending)]
    if not attackers:
        g.damage_by_turn.append(0.0)
        return
    g.beast_active = (g.has("Beastmaster Ascension") and len(attackers) >= 7)

    dmg = sum(g.power_of(p) for p in attackers)

    # Coat of Arms: "+1/+1 for each other creature ON THE BATTLEFIELD that
    # shares a type" — the opponents' Rendmaw Birds count too, so each of your
    # Birds is pumped by (your other Birds + every Bird they were handed).
    # Note this is symmetric: their Birds get the same bonus, which
    # goaded_combat does not currently price in.
    if g.has("Coat of Arms"):
        birds = sum(1 for p in attackers if "Bird" in p.card.name)
        opp_birds = sum(o.goaded_birds for o in OPP.living(g))
        dmg += birds * max(0, birds - 1 + opp_birds)

    # Ohran Frostfang: draw on connect
    if g.has("Ohran Frostfang"):
        g.draw(min(len(attackers), 5))

    # opponents block: chump the biggest attackers first
    if g.cfg.get("derived_blocking", True):
        scale = dmg / max(1e-9, sum(g.power_of(p) for p in attackers))
        dmg = OPP.damage_through(g, attackers) * scale
    else:
        dmg *= (1.0 - g.cfg.get("block_rate", 0.30))

    for p in attackers:
        p.tapped = True
    g.m["damage"] += dmg
    g.damage_by_turn.append(dmg)
    OPP.damage_single(g, dmg)
    if g.result == "win" and g.m["turn_lethal"] == 99:
        g.m["turn_lethal"] = g.turn


def take_turn(g: Game):
    g.turn += 1
    g.spells_this_turn = 0
    g.made_token_this_turn = False
    g.beast_active = False
    g.stampede_bonus = 0
    g.creature_died_this_turn = False
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.land_drops = 1 + (1 if g.has("Dryad of the Ilysian Grove") else 0)
    g.land_drops_used = 0

    upkeep(g)
    if g.turn > 1 or g.cfg.get("on_the_draw", True):
        g.draw(1)

    play_land(g)
    main_phase(g, precombat=True)   # anthems / pump only
    combat(g)
    activations(g)                  # Skullclamp, Idol, sac outlets
    play_land(g)                    # second drop (Dryad) once we know our needs
    main_phase(g)                   # deploy the rest postcombat

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
        for n in before - after:
            g.m["test_card_answered"] += 1
            g.m["test_card_removed"] += 1


def simulate(deck: list[Card], commander: Card, cfg: dict, seed: int) -> dict:
    rng = random.Random(seed)
    g = Game(deck, commander, cfg, rng, seed_for_pod=seed)
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
    out["final_board_power"] = sum(g.power_of(p) for p in g.board if p.card.is_creature)
    out["won"] = 1 if g.result == "win" else 0
    out["lost"] = 1 if g.result == "loss" else 0
    out["test_card_resolved"] = 1 if (out["cast_test_card"] and
                                      not out["test_card_answered"]) else 0
    return out
