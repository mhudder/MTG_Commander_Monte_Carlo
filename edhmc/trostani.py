"""
edhmc.trostani — a tokens / populate / lifegain engine for Trostani,
Selesnya's Voice.

    Trostani, Selesnya's Voice  {G}{G}{W}{W}  2/5
      Whenever another creature you control enters, you gain life equal to
      that creature's toughness.
      {1}{G}{W}, {T}: Populate. (Create a token that's a copy of a creature
      token you control.)

Verified against Scryfall 2026-10-01, with every card in the list.

THE CENTRAL MODELLING FACT
--------------------------
Trostani's trigger reads the TOUGHNESS of what enters, and Soul of Eternity's
toughness IS YOUR LIFE TOTAL ("power and toughness are each equal to your life
total"). So a token copy of Soul of Eternity entering under Trostani DOUBLES
your life, and the next copy reads the doubled total. Every populate, every
Bramble Sovereign trigger, every Mimic Vat activation and every token doubler
on the table turns that into an exponent. That is the owner's thesis -- "Soul
of Eternity is one of the MVPs" -- and it is not a guess about the deck: it is
two clauses of oracle text meeting. The engine therefore evaluates toughness
AT EACH TRIGGER'S RESOLUTION (`creature_entered`), never once per batch: two
Soul tokens entering together take life L to 2L to 4L, not to 3L.

Copies of a CDA creature keep the CDA (CR 707.2: the ability is a copiable
value), so a Bramble Sovereign, populate, Mimic Vat, encore or myriad copy of
Soul is still */* = life. A copy whose effect NAMES a power and toughness does
not: God-Pharaoh's Gift's "except it's a 4/4 black Zombie" and Timeless
Witness's eternalize override the CDA (707.9d), and those tokens carry the
`fixed_pt` tag.

ONE TOKEN PATH (`create_tokens`), because a replacement effect said on one
path and not another is §0z4's trap and tivit needed Anointed Procession said
in three places. Every token this engine makes goes through it:

  * Queen Allenal: "those tokens plus a 1/1 white Soldier" -- creature tokens
    only. Applied FIRST, then the doublers double the Soldier too: the
    affected player orders replacement effects (616.1), and that is the order
    a pilot picks.
  * Parallel Lives, Anointed Procession, Mondrak and Primal Vigor each double
    the count. Primal Vigor is symmetric; its half that doubles the
    OPPONENTS' tokens is blind (§4) -- the pod has a creature count, not
    tokens.
  * `token_cap` (200 creature tokens on the battlefield) bounds the board.
    It is a guard on the simulator, not a claim about the card: a board of
    two hundred creature tokens has won, and the exponent above would
    otherwise build boards the size of a library each turn. Tokens past the
    cap are counted in `tokens_capped`. `life_cap` (1e9) does the same for
    life, for the same reason -- the doubling would otherwise reach float
    infinity and turn every later comparison into NaN.

THE LEGEND RULE (704.5j) is applied to copies, from the generated LEGENDARY
set: a copy of a legendary permanent that is already on the battlefield is
not made at all (the pilot would keep the original), so Bramble Sovereign
declines Trostani, King Darien, Queen Allenal and Mondrak.

POLICIES, SAID OUT LOUD -- every one is a knob in docs/KNOBS.md
----------------------------------------------------------------
  * Trostani does not attack while a creature token is on the battlefield
    (`trostani_attacks`): her {T} is a populate, and a 2/5 attacker is worth
    less than a copy of almost any token.
  * Karmic Guide's echo is DECLINED (`karmic_echo`): the body is a 2/2 and its
    value was the ETB; it goes to the graveyard, where Mimic Vat and God-
    Pharaoh's Gift can use it again.
  * Phyrexian Processor pays `processor_life` (PROCESSOR_LIFE) but never
    below `processor_floor` (12) life; with less than 4 to pay it is not
    activated. The owner's call (2026-10-01, §0z97): more than the first
    cut's 8, never below 12 -- it was 8 above a floor of 20.
  * Sylvan Library keeps an extra card for 4 life only while that leaves
    `library_life_floor` (20) life; the rest go back on top. The owner's
    call (2026-10-01, §0z97); it was 25.
  * Aetherflux Reservoir fires 50 only while it leaves `reservoir_floor` (15).
  * Shocklands pay 2 life while `shock_life_floor` (15) is kept.
  * Selesnya Eulogist exiles a creature card from an OPPONENT'S graveyard
    from pod turn 4 (`eulogist_opp_yard_turn`), one a round; the pod's
    graveyards are not modelled (§4), and a four-player table has creature
    cards in some graveyard by then. Otherwise it eats the least valuable
    creature card in yours.
  * Elspeth +1s every turn and takes the -7 at seven or more loyalty once
    you control `elspeth_ult_creatures` (5) creatures. Her -3 is never taken:
    it would destroy your own Soul tokens and the pod's board is a count.
  * Greater Good sacrifices a creature whose power the library can afford
    (draw_is_safe), at most once a turn, when the hand holds two cards or
    fewer; the three discards are the least useful cards.
  * With a Soul of Eternity token out, Trostani populates BEFORE the main
    phase (`populate_soul_first`); otherwise her populate is an after-combat
    sink.
  * Bramble Sovereign pays {1}{G} for every copy it can, mid-phase.
  * Luminarch Ascension rolls each opponent's turn against the share of its
    attack aimed at you (`luminarch_per_opponent`, see `luminarch_rolls`).
  * Dawn of Hope: "whenever you gain life, you may pay {2}". Triggers are
    banked as `dawn_pending` and paid from what mana is left at the next sink
    step, at most `dawn_draws_per_turn` (4) a turn. A pilot pays at the
    trigger; paying later from mana the main phase left is the approximation.

SEEDBORN MUSE. "Untap all permanents you control during each other player's
untap step" -- each opponent's turn is another round of every instant-speed
ability in the list (Trostani's populate, Eulogist, Luminarch's Angels,
Processor, King Darien, Dawn of Hope, the Reservoir). They are run, one round
per living opponent, BEFORE the pod's removal round (`seedborn_turns`), so
the tokens they make are exposed to that round's wipes. Creatures stay
summoning-sick until your next turn, exactly as the rules say, so a Trostani
cast this turn cannot populate on the opponents' turns.

THE TWO SHARED HOOKS THIS ENGINE ADDED (`opponents.py`, optional, discovered
by `getattr` -- no other engine defines them, so no other deck moves):

  * `before_wipe()` -- the pod's wrath is about to resolve. Selfless Spirit
    ("Sacrifice this creature: creatures you control gain indestructible
    until end of turn") or King Darien ("creature tokens you control gain
    hexproof and indestructible") is sacrificed in response.
  * `indestructible_granted(perm)` / `flying_granted(perm)` -- the grant
    above, read by `opponents.indestructible_of`, and Elspeth's emblem ("have
    flying"), read by `opponents.flying_of`. A grant lasts until the start of
    your next turn: the pod's three turns are one round here, so a Spirit
    sacrificed against the first opponent's wrath also covers the second's.
    That is an overstatement in the rare round with two wraths.

WHAT IS MODEL-BLIND (§4) -- see `KNOWN_BLIND['trostani']` in ablation.py
---------------------------------------------------------------------------
Swords to Plowshares, Path to Exile, Beast Within, Aura Shards, Acidic Slime's
ETB, Angel of Sanctions' ETB, Archon of Valor's Reach's choice, Sundering
Growth's destroy half, Cavern of Souls' uncounterable creatures and Yavimaya
Hollow's regeneration all need an opposing permanent, an opposing spell or a
replacement this model does not represent.
"""

from __future__ import annotations

import dataclasses

from edhmc.engine import (BaseGame, Board, Card, Permanent, Metrics,
                          Snapshots, finish, lookahead_pick, can_pay,
                          available_mana as shared_available_mana, spend,
                          engine_cfg, choose_mode, CRNStreams, crn_shuffle,
                          crn_random,
                          make_rng, seal_rng, enter_loyalty, walker_ready,
                          walker_dies_at_zero, fetch_basics,
                          sakura_tribe_elder, coloured_tap_life, draw_is_safe,
                          drew_from_empty, ManaUnits, BASIC_LANDS)
from edhmc import opponents as OPP
from edhmc.decks._evasion import FOREST, PLAINS, LEGENDARY

COMMANDER_NAME = "Trostani, Selesnya's Voice"


# ---------------------------------------------------------------------------
# Tokens this list makes from scratch. Module constants, never mutated: a
# token's CARD is shared by every token of that kind, in every game.
# ---------------------------------------------------------------------------

def token_card(name, p, t, colours, flying=False, lifelink=False,
               types=("Creature",)):
    return Card(name=name, types=frozenset(types), power=p, toughness=t,
                flying=flying, lifelink=lifelink,
                tags=frozenset({"token"} | {f"col_{c}" for c in colours}))


# Phyrexian Processor's life payment cap, set from the sweep in §0z97.
PROCESSOR_LIFE = 16

# Elspeth's +1, Queen Allenal's extra token, King Darien's activation.
SOLDIER = token_card("Soldier token", 1, 1, "W")
# Dawn of Hope's {3}{W}: "a 1/1 white Soldier creature token with lifelink".
LIFELINK_SOLDIER = token_card("Soldier token (lifelink)", 1, 1, "W",
                              lifelink=True)
# Luminarch Ascension: "a 4/4 white Angel creature token with flying".
ANGEL = token_card("Angel token", 4, 4, "W", flying=True)
# Wurmcoil Engine: "a 3/3 colorless Phyrexian Wurm artifact creature token
# with deathtouch and a 3/3 colorless Phyrexian Wurm artifact creature token
# with lifelink". Deathtouch is inert against a chump-blocking pod.
WURM_DEATHTOUCH = token_card("Phyrexian Wurm token (deathtouch)", 3, 3, "",
                             types=("Artifact", "Creature"))
WURM_LIFELINK = token_card("Phyrexian Wurm token (lifelink)", 3, 3, "",
                           lifelink=True, types=("Artifact", "Creature"))
_MINIONS: dict = {}


def minion(x: int) -> Card:
    """Phyrexian Processor: "an X/X black Phyrexian Minion creature token"."""
    if x not in _MINIONS:
        _MINIONS[x] = token_card("Phyrexian Minion token", x, x, "B")
    return _MINIONS[x]


def copy_card(card: Card, fixed=None, colours=None, no_cost=False) -> Card:
    """The CARD of a token copy: `card`'s copiable values (707.2) with the
    exceptions the copying effect names. A copy of a copy copies the
    exceptions too (707.9b), which is why they are written into the Card.

    `fixed` -- "except it's a 4/4" (God-Pharaoh's Gift, eternalize): the CDA
    is not copied (707.9d), marked `fixed_pt`. `colours` replaces the colour
    ("black Zombie"); `no_cost` is eternalize's and embalm's "with no mana
    cost"."""
    tags = set(card.tags) | {"copy"}
    kw = {}
    if fixed is not None:
        kw.update(power=fixed[0], toughness=fixed[1])
        tags.add("fixed_pt")
    if colours is not None:
        tags = {t for t in tags if not t.startswith("col_")}
        tags |= {f"col_{c}" for c in colours} or {"col_none"}
    if no_cost:
        kw["cost"] = {}
        kw["alt_costs"] = ()
    return dataclasses.replace(card, tags=frozenset(tags), **kw)


def colours_of(card: Card) -> frozenset:
    """A card's colours: a token's from its `col_` tags, a card's from its
    mana cost, hybrid spellings included (107.4e)."""
    marked = {t[4:] for t in card.tags if t.startswith("col_")}
    if marked or "token" in card.tags or "col_none" in card.tags:
        return frozenset(c for c in marked if c != "none")
    out = {c for c in "WUBRG" if card.cost.get(c)}
    for entry in card.alt_costs:
        if entry[1] == "hybrid":
            out |= {c for c in "WUBRG" if entry[0].get(c)}
    return frozenset(out)


# The cards whose ETB this engine resolves BY NAME (`TrostaniGame.etb`).
# A name set is a claim that rots (§0q): `check_name_tables` refuses one that
# names a card no Trostani list holds.
ETB_BY_NAME = ("Wood Elves", "Farhaven Elf", "Solemn Simulacrum",
               "Ulvenwald Hydra", "Eternal Witness", "Timeless Witness",
               "Karmic Guide", "Sun Titan")
# Copy effects a pilot always wants a second ETB of; ranks populate targets.
DEATH_BY_NAME = ("Wurmcoil Engine", "Solemn Simulacrum")


class TrostaniGame(BaseGame):
    def __init__(self, deck, commander, cfg, seed):
        # A PRIVATE copy (engine.engine_cfg): never stamp the caller's dict.
        self.cfg = cfg = engine_cfg(cfg)
        self.rng = make_rng(seed, cfg)
        # Mid-game randomness lives here, NOT on self.rng. §0z17.
        self.crn = CRNStreams(seed)
        self.library = list(deck)
        self.rng.shuffle(self.library)
        self.hand: list[Card] = []
        self.board: Board = Board()
        self.graveyard: list[Card] = []
        self.exile: list[Card] = []
        self.commander = commander
        self.commander_cast = False
        self.commander_tax = 0
        self.turn = 0
        self.land_drops = 1
        self.land_drops_used = 0
        self.spells_this_turn = 0
        self.in_draw_step = False
        # Which "turn" it is, for once-each-turn triggers: (your turn, 0) on
        # yours, (your turn, i) on the i-th opponent's (Seedborn Muse).
        self.turn_key = (0, 0)
        self.caretaker_turn: dict = {}        # id(Talent) -> turn_key it drew
        self.vat: dict = {}                   # id(Mimic Vat) -> imprinted Card
        self.hideaway: dict = {}              # id(Mosswort Bridge) -> Card
        self.processor_x: dict = {}           # id(Processor) -> life paid
        self.quest: dict = {}                 # id(Luminarch) -> quest counters
        self.echo_due: set = set()            # id(Karmic Guide) entered since upkeep
        self.hasty: set = set()               # ids that "gain haste" this turn
        self.exile_at_end: list = []          # Mimic Vat tokens
        self.sacrifice_at_end: list = []      # encore tokens
        self.blade_on = None                  # the creature Blade of Selves equips
        self.emblems = 0                      # Elspeth's -7
        self.team_indestructible = False      # Selfless Spirit, until your turn
        self.tokens_indestructible = False    # King Darien, until your turn
        self.dawn_pending = 0
        self.dawn_paid_turn = 0
        self.greater_good_turn = 0
        self.opp_yard_used = 0                # Eulogist's opposing targets
        self.seedborn_lost: set = set()       # id(opponent) whose turn cost you life
        self.life_at_pod_start = 0.0

        # Lightning Greaves on the commander: "shroud". Its equip is {0}, so
        # it lives on Trostani and is never moved for haste -- a FLOOR on the
        # card's haste half, named in PARTLY_MODELLED.
        cfg.setdefault("shroud_sources", ("Lightning Greaves",))
        cfg.setdefault("protection_cards", ())
        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = Metrics({
            "damage": 0.0, "combat_damage": 0.0, "drain_damage": 0.0,
            "cards_drawn": 0, "mana_spent": 0, "mana_floated": 0,
            "stranded_mv": 0, "turn_lethal": 99, "turn_won": 99,
            "removal_eaten": 0, "ae_removal_eaten": 0, "wipes_suffered": 0,
            "countered": 0, "protected": 0, "loss_route": 0, "win_route": 0,
            "cast_test_card": 0, "test_card_turn": 99,
            "test_card_answered": 0, "test_card_removed": 0,
            "test_card_countered": 0,
            "tokens_made": 0, "tokens_capped": 0, "populates": 0,
            "life_gained": 0.0, "lifegain_triggers": 0, "trostani_life": 0.0,
            "soul_tokens_made": 0,
        })
        self.damage_by_turn = []

    # -- characteristics ------------------------------------------------------

    def creatures(self):
        return [p for p in self.board if OPP.is_creature_now(self, p)]

    def base_pt(self, perm):
        c = perm.card
        if "fixed_pt" not in c.tags:
            if c.name == "Soul of Eternity":
                life = max(0.0, self.your_life)
                return life, life
            if c.name == "Ulvenwald Hydra":
                n = sum(1 for p in self.board if p.card.is_land)
                return n, n
            if c.name == "Queen Allenal of Ruadach":
                n = len(self.creatures())
                return n, n
        if perm.is_token:
            return perm.base_p, perm.base_t
        return c.power, c.toughness

    def anthem(self, perm):
        """+N/+N from statics: Mirari's Wake ("creatures you control"), King
        Darien ("OTHER creatures you control"), Caretaker's Talent at level 3
        ("creature TOKENS you control get +2/+2"), Elspeth's emblem."""
        if not perm.card.is_creature:
            return 0
        n = self.count("Mirari's Wake")
        n += self.count("King Darien XLVIII") - (
            1 if perm.card.name == "King Darien XLVIII" else 0)
        if perm.is_token:
            n += 2 * sum(1 for p in self.board
                         if p.card.name == "Caretaker's Talent" and p.level >= 3)
        n += 2 * self.emblems
        return n

    def power_of(self, perm):
        p, _ = self.base_pt(perm)
        return p + perm.counters + self.anthem(perm)

    def toughness_of(self, perm):
        _, t = self.base_pt(perm)
        return t + perm.counters + self.anthem(perm)

    # -- the protocol hooks opponents.py asks for (all optional) ------------

    def flying_granted(self, perm) -> bool:
        """Elspeth's emblem: "Creatures you control get +2/+2 and have
        flying." Read by `opponents.flying_of`."""
        return self.emblems > 0 and perm.card.is_creature

    def indestructible_granted(self, perm) -> bool:
        """Selfless Spirit's and King Darien's grants, read by
        `opponents.indestructible_of`."""
        if not perm.card.is_creature:
            return False
        return self.team_indestructible or (self.tokens_indestructible
                                            and perm.is_token)

    def before_wipe(self):
        """The pod's wrath is about to resolve. Selfless Spirit first: it
        covers every creature, King Darien only the tokens. Either is spent
        only when there is something worth saving -- `protect_min` (3)
        creatures besides the one sacrificed."""
        if not self.cfg.get("wipe_response", True):
            return
        if self.team_indestructible:
            return
        others = len(self.creatures()) - 1
        if others < self.cfg.get("protect_min", 3):
            return
        spirit = next((p for p in self.board
                       if p.card.name == "Selfless Spirit"), None)
        if spirit is not None:
            self.sacrifice(spirit)
            self.team_indestructible = True
            self.m["spirit_saves"] += 1
            return
        if self.tokens_indestructible:
            return
        darien = next((p for p in self.board
                       if p.card.name == "King Darien XLVIII"), None)
        tokens = sum(1 for p in self.board if p.is_token and p.card.is_creature)
        if darien is not None and tokens >= self.cfg.get("protect_min", 3):
            self.sacrifice(darien)
            self.tokens_indestructible = True
            self.m["darien_saves"] += 1

    # -- zones ------------------------------------------------------------

    def take(self, zone, card) -> bool:
        """Remove `card` from `zone` BY IDENTITY. `list.remove` compares Card
        dataclasses field by field, so it would take the first equal card,
        which for two Plains is harmless and for anything else is a lie."""
        for i, c in enumerate(zone):
            if c is card:
                zone.pop(i)
                return True
        return False

    def make_permanent(self, card, sick=True, tapped=False, is_token=False,
                       counters=0):
        perm = Permanent(card=card, sick=sick, tapped=tapped,
                         is_token=is_token, counters=counters,
                         base_p=card.power, base_t=card.toughness)
        enter_loyalty(perm)
        self.board.append(perm)
        return perm

    def draw(self, n=1):
        """Alhammarret's Archive: "If you would draw a card except the first
        one you draw in each of your draw steps, draw two cards instead."
        karlov's rule (`KarlovGame.draw`), said again for this list."""
        arch = self.count("Alhammarret's Archive")
        for _ in range(int(n)):
            per = 1
            if arch and not self.in_draw_step:
                per = 2 ** arch
            for _ in range(per):
                if not self.library:
                    drew_from_empty(self)
                    return
                self.hand.append(self.library.pop())
                self.m["cards_drawn"] += 1
            if per > 1:
                self.m["archive_extra_draws"] += per - 1
            self.in_draw_step = False

    def may_draw(self, n=1) -> bool:
        """An OPTIONAL draw (§0z42): declined when it would leave fewer than
        `decking_reserve` cards. Archive's doubling counts against it."""
        want = n * (2 ** self.count("Alhammarret's Archive"))
        if not draw_is_safe(self, want):
            self.m["draws_declined"] += 1
            return False
        self.draw(n)
        return True

    # -- life ---------------------------------------------------------------

    def gain_life(self, amount, source=""):
        """ONE lifegain EVENT. Alhammarret's Archive doubles the amount (a
        replacement, so the event count is unchanged); Dawn of Hope banks a
        trigger per event."""
        if amount <= 0:
            return
        for _ in range(self.count("Alhammarret's Archive")):
            amount *= 2
        cap = self.cfg.get("life_cap", 1e9)
        before = self.your_life
        self.your_life = min(cap, self.your_life + amount)
        gained = max(0.0, self.your_life - before)
        self.m["life_gained"] += gained
        self.m["lifegain_triggers"] += 1
        if source == "trostani":
            self.m["trostani_life"] += gained
        self.dawn_pending += self.count("Dawn of Hope")

    def lose_life(self, n):
        self.your_life -= n
        if self.your_life <= 0 and self.result is None:
            self.result = "loss"
            self.m["loss_route"] = 4      # paid life to zero

    # -- mana ---------------------------------------------------------------

    def available_mana(self):
        """The shared pool plus MIRARI'S WAKE: "Whenever you tap a land for
        mana, add one mana of any type that land produced." A doubler, so
        each extra unit carries the SAME owner and one tap covers both --
        azusa's Nissa pattern (§0z4). One extra per land per Wake, whatever
        the land makes (a Karoo's two is still one tap)."""
        units = shared_available_mana(self)
        k = self.count("Mirari's Wake")
        if not k:
            return units
        extra, owners, weights = [], [], []
        seen = set()
        for u, o, w in zip(units, units.owners, units.weights):
            if o is None or not o.card.is_land or id(o) in seen:
                continue
            seen.add(id(o))
            for _ in range(k):
                extra.append(u)
                owners.append(o)
                weights.append(w)
        return ManaUnits(list(units) + extra, units.owners + owners,
                         units.weights + weights, units.legacy, units.surplus)

    def pay_from(self, cost, units, idx):
        """Tap what `can_pay` chose, and charge Talisman of Unity's damage."""
        lost = coloured_tap_life(self, cost, idx, units)
        spend(self, idx, units)
        if lost:
            self.lose_life(lost)
            self.m["talisman_life"] += lost

    def pay(self, cost) -> bool:
        units = self.available_mana()
        idx = can_pay(cost, units)
        if idx is None:
            return False
        self.pay_from(cost, units, idx)
        return True

    def can_afford(self, cost) -> bool:
        return can_pay(cost, self.available_mana()) is not None

    def convoke_pool(self, units, precombat):
        """CHORD OF CALLING's convoke: "each creature you tap while casting
        this spell pays for {1} or one mana of that creature's color".
        Convoke is not a {T} ability, so a summoning-sick creature can pay.
        Precombat only the SICK ones are offered -- the rest are about to
        attack; after combat, every untapped creature. A mana creature is
        left to its mana ability, which the shared pool already counts."""
        extra, owners = [], []
        for p in self.board:
            if p.tapped or not OPP.is_creature_now(self, p):
                continue
            if p.card.mana_ability or p.card is self.commander:
                continue
            if precombat and not p.sick:
                continue
            extra.append(frozenset(colours_of(p.card) | {"C"}))
            owners.append(p)
        return ManaUnits(list(units) + extra, units.owners + owners,
                         units.weights + [(9, 0, 0)] * len(extra),
                         units.legacy, units.surplus)

    # -- tokens: the ONE path ----------------------------------------------

    def doublers(self) -> int:
        """Parallel Lives, Anointed Procession, Mondrak and Primal Vigor:
        each "twice that many". `count`, so a token copy of Mondrak would
        count -- the legend rule keeps there from being one."""
        return (self.count("Parallel Lives") + self.count("Anointed Procession")
                + self.count("Mondrak, Glory Dominus")
                + self.count("Primal Vigor"))

    def counter_doubler(self) -> int:
        """Primal Vigor's second clause: "+1/+1 counters ... twice that many"."""
        return 2 ** self.count("Primal Vigor")

    def add_counters(self, perm, n):
        perm.counters += n * self.counter_doubler()

    def create_tokens(self, card, n=1, sick=True, tapped=False, hasty=False,
                      batch=None):
        """Create `n` tokens of `card` under your control. Returns the new
        permanents. Every replacement on the number is applied here and
        nowhere else -- see the module docstring for the order.

        `batch`: a list to append the new permanents to INSTEAD of firing
        their enter triggers, for effects that create several kinds at once
        (Wurmcoil's two Wurms) -- the caller fires `entered` on the lot."""
        groups = [(card, n)]
        if card.is_creature and self.cfg.get("queen_soldier", True):
            q = self.count("Queen Allenal of Ruadach")
            if q:
                groups.append((SOLDIER, q))
                self.m["queen_soldiers"] += q
        mult = 2 ** self.doublers()
        cap = self.cfg.get("token_cap", 200)
        made = []
        on_board = sum(1 for p in self.board if p.is_token and p.card.is_creature)
        for c, k in groups:
            want = k * mult
            self.m["doubled_tokens"] += want - k
            for _ in range(want):
                if c.is_creature and on_board >= cap:
                    self.m["tokens_capped"] += 1
                    continue
                perm = self.make_permanent(c, sick=sick, tapped=tapped,
                                           is_token=True)
                if hasty:
                    self.hasty.add(id(perm))
                if c.is_creature:
                    on_board += 1
                if c.name == "Soul of Eternity":
                    self.m["soul_tokens_made"] += 1
                made.append(perm)
        self.m["tokens_made"] += len(made)
        if batch is not None:
            batch.extend(made)
        else:
            self.entered(made)
        return made

    def copy_token(self, card, n=1, **kw):
        """A token copy of `card`, refused by the legend rule when one of that
        name is already on the battlefield (704.5j)."""
        if card.name in LEGENDARY and self.has(card.name):
            self.m["legend_rule_declined"] += 1
            return []
        return self.create_tokens(card, n, **kw)

    def token_value(self, perm) -> float:
        """How much a populate copy of this token is worth, for choosing the
        target. Its body, plus a bonus for an ETB the copy repeats -- a token
        Karmic Guide or Timeless Witness copies its trigger. Soul of
        Eternity's power is your life, so it ranks itself."""
        v = self.power_of(perm) + self.toughness_of(perm) / 2.0
        if perm.card.name in ETB_BY_NAME:
            v += 3.0
        if perm.card.name in ("Nesting Dovehawk", "Selesnya Eulogist",
                              "Bramble Sovereign", "Seedborn Muse"):
            v += 3.0
        return v

    def populate_target(self):
        toks = [p for p in self.board
                if p.is_token and OPP.is_creature_now(self, p)]
        toks = [p for p in toks if not (p.card.name in LEGENDARY)]
        if not toks:
            return None
        return max(toks, key=self.token_value)

    def populate(self, why) -> bool:
        """Populate: "Create a token that's a copy of a creature token you
        control." The copy is of the best token by `token_value`."""
        tgt = self.populate_target()
        if tgt is None:
            self.m["populate_fizzled"] += 1
            return False
        self.m["populates"] += 1
        self.m[f"populate_{why}"] += 1
        self.copy_token(tgt.card)
        return True

    # -- entering --------------------------------------------------------

    def entered(self, perms):
        """Permanents that entered TOGETHER (603.6a: they see each other).
        Caretaker's Talent triggers once for the batch; every creature then
        resolves its own triggers, in order, reading the board as it is when
        each resolves (§0z19)."""
        if not perms:
            return
        if any(p.is_token for p in perms):
            for t in [p for p in self.board
                      if p.card.name == "Caretaker's Talent"]:
                if self.caretaker_turn.get(id(t)) != self.turn_key:
                    self.caretaker_turn[id(t)] = self.turn_key
                    # "draw a card" -- mandatory, not a may.
                    self.draw(1)
                    self.m["caretaker_draws"] += 1
        for p in perms:
            if p in self.board and p.card.is_creature:
                self.creature_entered(p)

    def creature_entered(self, perm):
        # TROSTANI: "Whenever ANOTHER creature you control enters, you gain
        # life equal to that creature's toughness." Read at resolution.
        for t in [p for p in self.board if p.card.name == COMMANDER_NAME
                  and p is not perm]:
            self.gain_life(self.toughness_of(perm), "trostani")
            self.m["trostani_triggers"] += 1
        # NESTING DOVEHAWK: "Whenever a creature TOKEN you control enters,
        # put a +1/+1 counter on this creature." Itself included.
        if perm.is_token:
            for d in [p for p in self.board if p.card.name == "Nesting Dovehawk"]:
                self.add_counters(d, 1)
                self.m["dovehawk_counters"] += 1
        # BRAMBLE SOVEREIGN: "Whenever another NONTOKEN creature enters, you
        # may pay {1}{G}. If you do, that creature's controller creates a
        # token that's a copy of that creature." Yours only -- the pod's
        # creatures are a count (§4).
        if not perm.is_token:
            for b in [p for p in self.board if p.card.name == "Bramble Sovereign"
                      and p is not perm]:
                if perm not in self.board:
                    break
                if perm.card.name in LEGENDARY:
                    break
                if self.pay({"gen": 1, "G": 1}):
                    self.m["bramble_copies"] += 1
                    self.copy_token(perm.card)
        # KARMIC GUIDE's echo is due at your next upkeep -- on a token copy
        # too, since echo is a copiable keyword.
        if perm.card.name == "Karmic Guide":
            self.echo_due.add(id(perm))
        self.etb(perm)

    def etb(self, perm):
        """ETBs resolved by name (ETB_BY_NAME). A token copy fires them too."""
        name = perm.card.name
        if name == "Wood Elves":
            # "search your library for a Forest card, put that card onto the
            # battlefield" -- untapped by the text; the land's own entry rule
            # (a shock, a tapped dual) still applies.
            self.fetch_land(lambda c: c.name in FOREST, from_effect=True)
        elif name in ("Farhaven Elf", "Solemn Simulacrum"):
            # "may search for a basic land card, put it onto the battlefield
            # tapped" -- the shared rule (§0z83).
            fetch_basics(self, 1)
        elif name == "Ulvenwald Hydra":
            self.fetch_land(lambda c: c.is_land and "fetch" not in c.tags,
                            from_effect=True, tapped=True)
        elif name == "Eternal Witness":
            self.regrow(optional=True)
        elif name == "Timeless Witness":
            self.regrow(optional=False)
        elif name == "Karmic Guide":
            # "return target creature card from your graveyard to the
            # battlefield"
            card = self.best_yard_creature()
            if card is not None:
                self.take(self.graveyard, card)
                self.m["karmic_returns"] += 1
                self.put_creature(card)
        elif name == "Sun Titan":
            self.sun_titan()

    def put_creature(self, card, tapped=False):
        """A creature CARD onto the battlefield from anywhere but the stack."""
        perm = self.make_permanent(card, sick=True, tapped=tapped)
        self.entered([perm])
        return perm

    # -- graveyard -------------------------------------------------------

    def best_yard_creature(self, pred=None):
        pool = [c for c in self.graveyard if c.is_creature
                and (pred is None or pred(c))]
        if not pool:
            return None
        return max(pool, key=lambda c: (c.priority, c.mv))

    def regrow(self, optional):
        """Eternal Witness / Timeless Witness: a card from the graveyard to
        hand -- the highest-priority nonland card, a land only if that is all
        there is (Gloomshrieker's pick, §0z83)."""
        if not self.graveyard:
            return
        best = max(self.graveyard,
                   key=lambda c: (not c.is_land, c.priority, c.mv))
        if optional and best.is_land and len(self.hand) > 3:
            return
        self.take(self.graveyard, best)
        self.hand.append(best)
        self.m["witness_returns"] += 1

    def sun_titan(self):
        """"Whenever this creature enters or attacks, you may return target
        permanent card with mana value 3 or less from your graveyard to the
        battlefield." A nonland pick first; a fetchland comes back and is
        cracked again."""
        pool = [c for c in self.graveyard if c.is_permanent and c.free_mv <= 3]
        if not pool:
            return
        best = max(pool, key=lambda c: (not c.is_land, c.priority, c.mv))
        self.take(self.graveyard, best)
        self.m["titan_returns"] += 1
        if best.is_land:
            self.enter_land(best, from_effect=True)
        else:
            self.enter_permanent(best)

    # -- dying -------------------------------------------------------------

    def on_creature_death(self, n=1, perm=None):
        """Fired for every creature death: the pod's removal and wipes (via
        `opponents.destroy`), your own wipe, and `sacrifice` below."""
        if perm is None:
            return
        name = perm.card.name
        if name == "Wurmcoil Engine":
            # "When this creature dies, create a 3/3 ... deathtouch and a 3/3
            # ... lifelink." Two creations, entering together.
            batch = []
            self.create_tokens(WURM_DEATHTOUCH, 1, batch=batch)
            self.create_tokens(WURM_LIFELINK, 1, batch=batch)
            self.entered(batch)
            self.m["wurmcoil_deaths"] += 1
        if name == "Solemn Simulacrum":
            if self.may_draw(1):
                self.m["solemn_draws"] += 1
        if self.blade_on is perm:
            self.blade_on = None

    def after_died(self, perm):
        """The dead creature's CARD is in the graveyard now. MIMIC VAT:
        "Whenever a nontoken creature dies, you may exile that card. If you
        do, return each other card exiled with this artifact to its owner's
        graveyard." Imprinted when the new card is worth more than what the
        Vat holds."""
        if perm.is_token:
            return
        for vat in [p for p in self.board if p.card.name == "Mimic Vat"]:
            held = self.vat.get(id(vat))
            if held is not None and (held.priority, held.mv) >= (
                    perm.card.priority, perm.card.mv):
                continue
            if not self.take(self.graveyard, perm.card):
                return
            if held is not None:
                self.graveyard.append(held)
            self.vat[id(vat)] = perm.card
            self.m["vat_imprints"] += 1
            return

    def sacrifice(self, perm):
        """A voluntary sacrifice -- Selfless Spirit, King Darien, Greater
        Good, Sakura-Tribe Elder, an encore token, a declined echo."""
        if perm not in self.board:
            return
        self.board.remove(perm)
        if perm.card is self.commander:
            self.commander_cast = False
            self.commander_tax += 2
        elif not perm.is_token:
            self.graveyard.append(perm.card)
        if perm.card.is_creature:
            self.m["creatures_sacrificed"] += 1
            self.on_creature_death(1, perm)
            if not perm.is_token:
                self.after_died(perm)

    # -- lands ---------------------------------------------------------------

    def land_enters_tapped(self, card, from_effect, tapped):
        """The land's OWN entry rule, whichever way it arrives."""
        if tapped or card.tapped:
            return True
        tags = card.tags
        if "shock" in tags:
            # "As this land enters, you may pay 2 life. If you don't, it
            # enters tapped."
            if self.your_life - 2 >= self.cfg.get("shock_life_floor", 15):
                self.lose_life(2)
                self.m["shock_life"] += 2
                return False
            return True
        lands = [p.card for p in self.board if p.card.is_land]
        if "check" in tags:
            # Sunpetal Grove: "unless you control a Forest or a Plains".
            return not any(c.name in FOREST or c.name in PLAINS for c in lands)
        if "battle" in tags:
            # Canopy Vista: "unless you control two or more basic lands".
            return sum(1 for c in lands if c.name in BASIC_LANDS) < 2
        if "reveal" in tags:
            # Fortified Village: "you may reveal a Forest or Plains card from
            # your hand. If you don't, this land enters tapped."
            return not any(c is not card and (c.name in FOREST or c.name in PLAINS)
                           for c in self.hand)
        return False

    def enter_land(self, card, from_effect=False, tapped=False):
        """A land onto the battlefield, by a land drop or by an effect, with
        its own entry rule and its own ETB."""
        t = self.land_enters_tapped(card, from_effect, tapped)
        perm = Permanent(card=card, tapped=t, sick=True,
                         base_p=card.power, base_t=card.toughness)
        self.board.append(perm)
        tags = card.tags
        if "gain1" in tags:
            self.gain_life(1)                      # Blossoming Sands
        if "scry1" in tags:
            self.scry1()                           # Temple of Plenty
        if "hideaway4" in tags:
            self.hideaway_etb(perm)                # Mosswort Bridge
        if "bounce" in tags:
            self.karoo_bounce(perm)                # Selesnya Sanctuary
        if "fetch" in tags and not t:
            self.crack_fetch(perm)
        return perm

    def scry1(self):
        """Scry 1: bottom a land once there are `scry_land_bottom` (5) lands
        out, a spell the deck cannot yet cast (two over the land count)
        while there are few."""
        if not self.library:
            return
        top = self.library[-1]
        lands = sum(1 for p in self.board if p.card.is_land)
        if (top.is_land and lands >= self.cfg.get("scry_land_bottom", 5)) or \
                (not top.is_land and top.mv > lands + 2):
            self.library.insert(0, self.library.pop())
            self.m["scry_bottomed"] += 1

    def hideaway_etb(self, perm):
        """Hideaway 4: "look at the top four cards of your library, exile one
        face down, then put the rest on the bottom in a random order." The
        pick is the most expensive spell -- it will be cast for free."""
        top = self.library[-4:]
        if not top:
            return
        pick = max(top, key=lambda c: (not c.is_land, c.mv, c.priority))
        rest = [c for c in top if c is not pick]
        del self.library[-len(top):]
        crn_shuffle(self, "hideaway", rest)
        self.library[:0] = rest
        self.hideaway[id(perm)] = pick
        self.m["hideaway_exiled"] += 1

    def karoo_bounce(self, perm):
        """Selesnya Sanctuary: "When this land enters, return a land you
        control to its owner's hand." Another land if there is one -- the
        least useful, a tapped basic first -- else itself."""
        others = [p for p in self.board if p.card.is_land and p is not perm]
        if not others:
            target = perm
        else:
            target = min(others, key=lambda p: (
                p.card.name not in BASIC_LANDS, not p.tapped,
                len(p.card.produces)))
        self.board.remove(target)
        self.hand.append(target.card)
        self.m["karoo_bounces"] += 1

    def crack_fetch(self, perm):
        """"{T}, Pay 1 life, Sacrifice this land: Search your library for a
        Forest or Plains card, put it onto the battlefield, then shuffle." --
        whichever halves the land names (its `fetch_` tags)."""
        kinds = []
        if "fetch_Forest" in perm.card.tags:
            kinds.append(FOREST)
        if "fetch_Plains" in perm.card.tags:
            kinds.append(PLAINS)
        pool = [c for c in self.library if c.is_land
                and any(c.name in k for k in kinds)]
        if not pool or perm.tapped:
            return
        # A pilot does not pay the last life point for a land: five games in
        # 2,000 ended that way before this guard (the pod's chip damage is an
        # expectation, so life can sit below 1 without being 0).
        if self.cfg.get("charge_life_costs", True) and self.your_life <= 1:
            return
        self.board.remove(perm)
        self.graveyard.append(perm.card)
        if self.cfg.get("charge_life_costs", True):
            self.lose_life(1)
        self.m["fetches_cracked"] += 1
        self.fetch_land(lambda c: any(c.name in k for k in kinds),
                        from_effect=True)

    def fetch_land(self, pred, from_effect=True, tapped=False, n=1):
        """Search for up to `n` lands matching `pred`, put them onto the
        battlefield, shuffle. The pick fixes the colour the board has least
        of, then prefers a land that will enter untapped."""
        got = 0
        for _ in range(n):
            pool = [c for c in self.library if c.is_land and pred(c)]
            if not pool:
                break
            have = {}
            for p in self.board:
                if p.card.is_land:
                    for col in p.card.produces:
                        have[col] = have.get(col, 0) + 1

            # Colours the board does not make yet, then entering untapped (a
            # shock counts as untapped while its 2 life can be paid), then
            # breadth, then the scarcer colour. A first version ranked the
            # scarcest colour first and a shock as tapped, so a Heath on an
            # empty board took a Forest over Temple Garden (test_trostani P).
            def score(c):
                new = sum(1 for col in c.produces if not have.get(col))
                untapped = not (tapped or self.land_enters_tapped_preview(c))
                need = min((have.get(col, 0) for col in c.produces), default=9)
                return (new, untapped, len(c.produces), -need)
            pick = max(pool, key=score)
            self.take(self.library, pick)
            self.enter_land(pick, from_effect=from_effect, tapped=tapped)
            got += 1
        crn_shuffle(self, "fetch_land", self.library)
        self.m["lands_fetched"] += got
        return got

    def land_step(self):
        """One land drop: the land that fixes a missing colour, then one that
        enters untapped. A fetchland is scored as the land it would find."""
        if self.land_drops_used >= self.land_drops:
            return
        lands = [c for c in self.hand if c.is_land]
        if not lands:
            return
        have = set()
        for p in self.board:
            if p.card.is_land:
                have |= p.card.produces

        def produces(c):
            if "fetch" in c.tags:
                return frozenset("WG")
            return c.produces

        def score(c):
            prod = produces(c)
            return (len(prod - have),
                    not self.land_enters_tapped_preview(c),
                    len(prod), c.name not in BASIC_LANDS)
        best = max(lands, key=score)
        self.take(self.hand, best)
        self.land_drops_used += 1
        self.m["lands_played"] += 1
        self.enter_land(best)

    def land_enters_tapped_preview(self, card):
        """`land_enters_tapped` without paying anything: a shock is assumed
        paid when it could be."""
        if card.tapped:
            return True
        if "shock" in card.tags:
            return self.your_life - 2 < self.cfg.get("shock_life_floor", 15)
        if card.tags & {"check", "battle", "reveal"}:
            return self.land_enters_tapped(card, False, False)
        return False

    # -- casting ---------------------------------------------------------------

    def tutor_pick(self, pool):
        """The best card for a tutor: highest priority, then mana value. The
        priority numbers ARE the deck's own statement of what matters most,
        and they put Soul of Eternity and Bramble Sovereign at the top."""
        if not pool:
            return None
        return max(pool, key=lambda c: (c.priority, c.mv))

    def x_plan(self, card, units):
        """Chord of Calling and Green Sun's Zenith: the best creature whose
        mana value X this pool affords. Returns (target, cost, pay) or None.
        A target below `tutor_floor` (6) priority is not worth the card."""
        if card.name == "Chord of Calling":
            base, pred = {"G": 3}, (lambda c: c.is_creature)
        else:
            base, pred = {"G": 1}, (lambda c: c.is_creature
                                    and "G" in colours_of(c))
        pool = sorted((c for c in self.library if pred(c)),
                      key=lambda c: (c.priority, c.mv), reverse=True)
        floor = self.cfg.get("tutor_floor", 6)
        for c in pool:
            if c.priority < floor:
                break
            cost = dict(base)
            x = int(c.free_mv)
            if x:
                cost["gen"] = x
            pay = can_pay(cost, units)
            if pay is not None:
                return c, cost, pay
        return None

    def on_cast(self, card):
        """"Whenever you cast a spell" -- Aetherflux Reservoir: "you gain 1
        life for each spell you've cast this turn"."""
        idx = self.spells_this_turn
        self.spells_this_turn += 1
        for _ in range(self.count("Aetherflux Reservoir")):
            self.gain_life(self.spells_this_turn)
            self.m["reservoir_gains"] += 1
        if card.name in self.cfg.get("watch", ()):
            self.m["cast_test_card"] = 1
            self.m["test_card_turn"] = min(self.m["test_card_turn"], self.turn)
        return idx

    def main_phase(self, precombat):
        while self.result is None:
            units = self.available_mana()
            if not self.commander_cast:
                ccost = dict(self.commander.cost)
                ccost["gen"] = ccost.get("gen", 0) + self.commander_tax
                idx = can_pay(ccost, units)
                if idx is not None:
                    self.pay_from(ccost, units, idx)
                    i = self.on_cast(self.commander)
                    if OPP.countered(self, self.commander, i):
                        self.m["countered"] += 1
                        self.commander_tax += 2
                        continue
                    self.commander_cast = True
                    perm = self.make_permanent(self.commander, sick=True)
                    self.entered([perm])
                    continue

            cpool = None
            if any(c.name == "Chord of Calling" for c in self.hand):
                cpool = self.convoke_pool(units, precombat)
            pool = cpool if cpool is not None else units
            options = []
            mode_cost = {}
            plans = {}
            for c in self.hand:
                if c.is_land:
                    continue
                if "wipe" in c.tags and not OPP.should_cast_own_wipe(self):
                    continue
                if c.name in ("Chord of Calling", "Green Sun's Zenith"):
                    plan = self.x_plan(c, pool if c.name == "Chord of Calling"
                                       else units)
                    if plan is None:
                        continue
                    plans[id(c)] = plan
                    options.append((c, plan[2]))
                    mode_cost[id(c)] = plan[1]
                    continue
                if not self.worth_casting(c):
                    continue
                _m = choose_mode(c, c.cost, units)
                if _m is None:
                    continue
                options.append((c, _m[2]))
                mode_cost[id(c)] = _m[0]
            if not options:
                break
            card, pay = lookahead_pick(
                self, options, pool, lambda it: (it[0].priority, it[0].mv),
                cost_of=lambda it: mode_cost[id(it[0])],
                pay_of=lambda it: it[1])
            self.pay_from(mode_cost[id(card)], pool, pay)
            self.take(self.hand, card)
            i = self.on_cast(card)
            if OPP.countered(self, card, i):
                self.m["countered"] += 1
                self.graveyard.append(card)
                if card.name in self.cfg.get("watch", ()):
                    self.m["test_card_answered"] += 1
                    self.m["test_card_countered"] += 1
                continue
            self.resolve(card, plans.get(id(card)))
            self.reservoir()

    def worth_casting(self, card) -> bool:
        """Cards the pilot holds rather than cast into nothing."""
        if card.name == "Sundering Growth":
            # Its populate is the half this model sees; with no token to copy
            # it is a removal spell aimed at the abstract pod.
            return self.populate_target() is not None
        if card.name == "Phyrexian Processor":
            return self.processor_payment() >= 4
        return True

    def processor_payment(self):
        pay = self.cfg.get("processor_life", PROCESSOR_LIFE)
        room = self.your_life - self.cfg.get("processor_floor", 12)
        return int(max(0, min(pay, room)))

    def resolve(self, card, plan=None):
        name = card.name
        if "wipe" in card.tags:
            OPP.resolve_own_wipe(self, spare_own="onesided" in card.tags,
                                 card=card)
        if name in ("Chord of Calling", "Green Sun's Zenith"):
            target = plan[0] if plan else None
            if target is not None and self.take(self.library, target):
                self.m["tutored_to_play"] += 1
                self.put_creature(target)
            crn_shuffle(self, "tutor", self.library)
            if name == "Green Sun's Zenith":
                # "Shuffle Green Sun's Zenith into its owner's library."
                self.library.append(card)
                crn_shuffle(self, "gsz", self.library)
            else:
                self.graveyard.append(card)
            return None
        if name in ("Worldly Tutor", "Eladamri's Call", "Enlightened Tutor",
                    "Congregation at Dawn"):
            self.tutor(card)
            self.graveyard.append(card)
            return None
        if name == "Skyshroud Claim":
            # "Search your library for up to two Forest cards, put them onto
            # the battlefield" -- untapped.
            self.fetch_land(lambda c: c.name in FOREST, n=2)
            self.graveyard.append(card)
            return None
        if name == "Sundering Growth":
            # "Destroy target artifact or enchantment, then populate." The
            # destroy is blind (§4); the populate is not.
            self.populate("sundering")
            self.graveyard.append(card)
            return None
        if not card.is_permanent:
            self.graveyard.append(card)
            return None
        return self.enter_permanent(card)

    def enter_permanent(self, card):
        """A nonland permanent card onto the battlefield -- cast, returned by
        Sun Titan, or played free off Mosswort Bridge."""
        perm = self.make_permanent(card, sick=True)
        name = card.name
        if name == "Phyrexian Processor":
            # "As this artifact enters, pay any amount of life."
            x = self.processor_payment()
            self.lose_life(x)
            self.processor_x[id(perm)] = x
            self.m["processor_life_paid"] += x
        elif name == "Luminarch Ascension":
            self.quest[id(perm)] = 0
        if card.is_creature:
            self.entered([perm])
        return perm

    def tutor(self, card):
        name = card.name
        lib = self.library
        if name == "Enlightened Tutor":
            pool = [c for c in lib if c.types & {"Artifact", "Enchantment"}]
        else:
            pool = [c for c in lib if c.is_creature]
        n = 3 if name == "Congregation at Dawn" else 1
        picks = []
        for _ in range(n):
            best = self.tutor_pick([c for c in pool
                                    if not any(c is p for p in picks)])
            if best is None:
                break
            picks.append(best)
        for c in picks:
            self.take(lib, c)
        crn_shuffle(self, "tutor", lib)
        if name == "Eladamri's Call":
            self.hand.extend(picks)
        else:
            # "put that card on top" -- the best is drawn first.
            for c in reversed(picks):
                lib.append(c)
        self.m["tutored"] += len(picks)

    # -- the instant- and sorcery-speed abilities ----------------------------

    def untapped(self, name, need_unsick=False):
        return [p for p in self.board if p.card.name == name and not p.tapped
                and not (need_unsick and p.sick)]

    def sinks(self, sorcery):
        """Spend what is left on the list's abilities, best first, until
        nothing is affordable. `sorcery` admits the sorcery-speed ones."""
        for _ in range(60):
            if self.result is not None:
                return
            if not self.one_sink(sorcery):
                break
            self.reservoir()
        self.dawn_pending = 0

    def one_sink(self, sorcery) -> bool:
        tgt = self.populate_target()
        if sorcery:
            for t in [p for p in self.board
                      if p.card.name == "Caretaker's Talent" and p.level == 1]:
                if tgt is not None and self.pay({"W": 1}):
                    # "When this Class becomes level 2, create a token that's a
                    # copy of target token you control."
                    t.level = 2
                    self.m["caretaker_levels"] += 1
                    self.copy_token(tgt.card)
                    return True
        # TROSTANI: {1}{G}{W}, {T}: Populate.
        if tgt is not None:
            for t in self.untapped(COMMANDER_NAME, need_unsick=True):
                if self.pay({"gen": 1, "G": 1, "W": 1}):
                    t.tapped = True
                    return self.populate("trostani")
            # SELESNYA EULOGIST: {2}{G}: exile target creature card from a
            # graveyard, then populate. No {T}: as often as there is mana and
            # a target.
            if self.has("Selesnya Eulogist") and self.eulogist_target() \
                    and self.pay({"gen": 2, "G": 1}):
                self.eulogist_exile()
                return self.populate("eulogist")
        # LUMINARCH ASCENSION: {1}{W}: a 4/4 flying Angel, with four or more
        # quest counters.
        for lum in [p for p in self.board if p.card.name == "Luminarch Ascension"]:
            if self.quest.get(id(lum), 0) >= 4 and self.pay({"gen": 1, "W": 1}):
                self.m["luminarch_angels"] += 1
                self.create_tokens(ANGEL, 1)
                return True
        # DAWN OF HOPE: pay {2} to draw, per lifegain trigger.
        if self.dawn_pending > 0 and self.dawn_paid_turn < self.cfg.get(
                "dawn_draws_per_turn", 4) and draw_is_safe(
                    self, 2 ** self.count("Alhammarret's Archive")):
            if self.pay({"gen": 2}):
                self.dawn_pending -= 1
                self.dawn_paid_turn += 1
                self.draw(1)
                self.m["dawn_draws"] += 1
                return True
        # PHYREXIAN PROCESSOR: {4}, {T}: an X/X Minion.
        for proc in self.untapped("Phyrexian Processor"):
            x = self.processor_x.get(id(proc), 0)
            if x >= 4 and self.pay({"gen": 4}):
                proc.tapped = True
                self.m["processor_tokens"] += 1
                self.create_tokens(minion(x), 1)
                return True
        # KING DARIEN: {3}{G}{W}: a +1/+1 counter on him and a 1/1 Soldier.
        for kd in [p for p in self.board if p.card.name == "King Darien XLVIII"]:
            if self.pay({"gen": 3, "G": 1, "W": 1}):
                self.add_counters(kd, 1)
                self.m["darien_activations"] += 1
                self.create_tokens(SOLDIER, 1)
                return True
        if sorcery:
            if self.sorcery_sink():
                return True
        # DAWN OF HOPE: {3}{W}: a 1/1 lifelink Soldier -- the last resort.
        if self.has("Dawn of Hope") and self.pay({"gen": 3, "W": 1}):
            self.m["dawn_soldiers"] += 1
            self.create_tokens(LIFELINK_SOLDIER, 1)
            return True
        # SCATTERED GROVES: cycling {2}, once the land drops are not short.
        groves = next((c for c in self.hand if "cycling2" in c.tags), None)
        if groves is not None and sum(1 for p in self.board
                                      if p.card.is_land) >= 6 \
                and draw_is_safe(self, 1) and self.pay({"gen": 2}):
            self.take(self.hand, groves)
            self.graveyard.append(groves)
            self.draw(1)
            self.m["cycled"] += 1
            return True
        return False

    def sorcery_sink(self) -> bool:
        # CARETAKER'S TALENT level 3: {3}{W}: creature tokens get +2/+2.
        toks = sum(1 for p in self.board if p.is_token and p.card.is_creature)
        for t in [p for p in self.board
                  if p.card.name == "Caretaker's Talent" and p.level == 2]:
            if toks >= 3 and self.pay({"gen": 3, "W": 1}):
                t.level = 3
                self.m["caretaker_levels"] += 1
                return True
        # ETERNALIZE {5}{G}{G}: a 4/4 black Zombie copy, no mana cost.
        tw = next((c for c in self.graveyard if c.name == "Timeless Witness"),
                  None)
        if tw is not None and len(self.graveyard) > 1 and self.pay(
                {"gen": 5, "G": 2}):
            self.take(self.graveyard, tw)
            self.exile.append(tw)
            self.m["eternalized"] += 1
            self.create_tokens(copy_card(tw, fixed=(4, 4), colours="B",
                                         no_cost=True), 1)
            return True
        # EMBALM {5}{W}: a white Zombie Angel copy, no mana cost.
        an = next((c for c in self.graveyard if c.name == "Angel of Sanctions"),
                  None)
        if an is not None and self.pay({"gen": 5, "W": 1}):
            self.take(self.graveyard, an)
            self.exile.append(an)
            self.m["embalmed"] += 1
            self.create_tokens(copy_card(an, colours="W", no_cost=True), 1)
            return True
        return False

    def eulogist_target(self) -> bool:
        if any(c.is_creature for c in self.graveyard):
            return True
        return self.opp_yard_available() > 0

    def opp_yard_available(self) -> int:
        start = self.cfg.get("eulogist_opp_yard_turn", 4)
        if start is None:
            return 0
        return max(0, OPP.pod_turn(self) - start + 1) - self.opp_yard_used

    def eulogist_exile(self):
        """An opposing creature card while one is assumed available, else the
        least valuable creature card in your own graveyard -- never Soul of
        Eternity, which encore wants."""
        if self.opp_yard_available() > 0:
            self.opp_yard_used += 1
            self.m["eulogist_opp_yard"] += 1
            return
        mine = [c for c in self.graveyard if c.is_creature]
        worst = min(mine, key=lambda c: (c.priority, c.mv))
        self.take(self.graveyard, worst)
        self.exile.append(worst)
        self.m["eulogist_own_yard"] += 1

    def precombat_actions(self):
        """Sorcery-speed actions taken BEFORE spells, because each is better
        than the average spell in hand when it is live."""
        self.populate_soul_first()
        # Untapped fetchlands left from an effect that put them in tapped.
        for p in [p for p in self.board if "fetch" in p.card.tags and not p.tapped]:
            self.crack_fetch(p)
        # MOSSWORT BRIDGE: {G}, {T}: play the hidden card free, "if creatures
        # you control have total power 10 or greater".
        for br in [p for p in self.board if p.card.name == "Mosswort Bridge"
                   and not p.tapped and id(p) in self.hideaway]:
            power = sum(max(0, self.power_of(p)) for p in self.creatures())
            if power < 10:
                continue
            br.tapped = True
            if not self.pay({"G": 1}):
                br.tapped = False
                continue
            card = self.hideaway.pop(id(br))
            self.m["hideaway_plays"] += 1
            if card.is_land:
                self.hand.append(card)
            else:
                i = self.on_cast(card)
                if OPP.countered(self, card, i):
                    self.m["countered"] += 1
                    self.graveyard.append(card)
                else:
                    self.resolve(card, self.free_plan(card))
        # ENCORE {7}{W}{W}: "For each opponent, create a token copy that
        # attacks that opponent this turn if able. They gain haste. Sacrifice
        # them at the beginning of the next end step."
        soul = next((c for c in self.graveyard if c.name == "Soul of Eternity"),
                    None)
        if soul is not None and self.pay({"gen": 7, "W": 2}):
            self.take(self.graveyard, soul)
            self.exile.append(soul)
            self.m["encores"] += 1
            made = self.create_tokens(soul, len(OPP.living(self)), hasty=True)
            self.sacrifice_at_end.extend(made)
        # MIMIC VAT: {3}, {T}: a token copy of the imprinted card, with haste;
        # exile it at the beginning of the next end step.
        for vat in self.untapped("Mimic Vat"):
            held = self.vat.get(id(vat))
            if held is None or held.name in LEGENDARY and self.has(held.name):
                continue
            if self.pay({"gen": 3}):
                vat.tapped = True
                self.m["vat_tokens"] += 1
                made = self.copy_token(held, hasty=True)
                self.exile_at_end.extend(made)
        # BLADE OF SELVES: equip {4} to the best attacker.
        self.equip_blade()
        # ELSPETH, SUN'S CHAMPION -- sorcery speed, once a turn.
        self.elspeth_step()

    def free_plan(self, card):
        """A free Chord or Zenith off Mosswort Bridge has X = 0."""
        if card.name not in ("Chord of Calling", "Green Sun's Zenith"):
            return None
        pool = [c for c in self.library if c.is_creature and c.free_mv == 0]
        best = self.tutor_pick(pool)
        return (best, {}, []) if best is not None else None

    def equip_blade(self):
        blade = next((p for p in self.board if p.card.name == "Blade of Selves"),
                     None)
        if blade is None:
            return
        cands = [p for p in self.creatures() if not p.sick
                 and p.card is not self.commander
                 and "Defender" not in p.card.tags]
        if not cands:
            return
        best = max(cands, key=self.power_of)
        cur = self.blade_on if self.blade_on in self.board else None
        if cur is best or self.power_of(best) < 4:
            return
        if cur is not None and self.power_of(cur) >= self.power_of(best):
            return
        if self.pay({"gen": 4}):
            self.blade_on = best
            self.m["blade_equips"] += 1

    def elspeth_step(self):
        for e in [p for p in self.board if p.card.name == "Elspeth, Sun's Champion"]:
            if not walker_ready(self, e):
                continue
            if (e.counters >= 7 and self.cfg.get("elspeth_ult", True)
                    and len(self.creatures()) >= self.cfg.get(
                        "elspeth_ult_creatures", 5)):
                # -7: "You get an emblem with 'Creatures you control get +2/+2
                # and have flying.'"
                e.counters -= 7
                self.emblems += 1
                self.m["elspeth_emblems"] += 1
                walker_dies_at_zero(self, e)
                continue
            # +1: "Create three 1/1 white Soldier creature tokens."
            e.counters += 1
            self.m["elspeth_plus"] += 1
            self.create_tokens(SOLDIER, 3)

    def reservoir(self):
        """AETHERFLUX RESERVOIR: "Pay 50 life: This artifact deals 50 damage
        to any target." Fired while it leaves `reservoir_floor` life."""
        if not self.has("Aetherflux Reservoir"):
            return
        floor = self.cfg.get("reservoir_floor", 15)
        while (self.result is None and OPP.living(self)
               and self.your_life - 50 >= floor):
            self.your_life -= 50
            dealt = OPP.damage_single(self, 50)
            self.m["damage"] += dealt
            self.m["drain_damage"] += dealt
            self.m["reservoir_shots"] += 1
            if self.damage_by_turn:
                self.damage_by_turn[-1] += dealt
            if not OPP.living(self) and self.result is None:
                self.result = "win"
            if self.result == "win":
                self.m["turn_won"] = min(self.m["turn_won"], self.turn)
                self.m["win_route"] = 4
                if self.m["turn_lethal"] == 99:
                    self.m["turn_lethal"] = self.turn

    def greater_good(self):
        """GREATER GOOD: "Sacrifice a creature: Draw cards equal to the
        sacrificed creature's power, then discard three cards." Once a turn,
        with two or fewer cards in hand, a body whose power the library can
        afford -- a token first, never the commander."""
        if not self.has("Greater Good") or self.greater_good_turn == self.turn:
            return
        if len(self.hand) > 2:
            return
        cands = [p for p in self.creatures() if p.card is not self.commander
                 and 3 <= self.power_of(p) <= 12
                 and draw_is_safe(self, int(self.power_of(p))
                                  * 2 ** self.count("Alhammarret's Archive"))]
        if not cands:
            return
        victim = min(cands, key=lambda p: (not p.is_token,
                                           -self.power_of(p)))
        n = int(self.power_of(victim))
        self.greater_good_turn = self.turn
        self.sacrifice(victim)
        self.draw(n)
        self.discard(3)
        self.m["greater_good_draws"] += n

    def discard(self, n):
        """The least useful cards: surplus lands once six are out, else the
        lowest-priority spells."""
        lands = sum(1 for p in self.board if p.card.is_land)
        for _ in range(min(n, len(self.hand))):
            worst = min(self.hand, key=lambda c: (
                (c.priority if not c.is_land else (9 if lands < 6 else -1)),
                c.mv))
            self.take(self.hand, worst)
            self.graveyard.append(worst)
            self.m["discarded"] += 1

    # -- the turn ----------------------------------------------------------

    def upkeep(self):
        # KARMIC GUIDE'S ECHO: pay {3}{W}{W} or sacrifice it.
        for p in [p for p in self.board if id(p) in self.echo_due]:
            self.echo_due.discard(id(p))
            if self.cfg.get("karmic_echo", "decline") == "pay" and \
                    self.pay({"gen": 3, "W": 2}):
                self.m["echo_paid"] += 1
                continue
            self.m["echo_declined"] += 1
            self.sacrifice(p)
        self.echo_due = {i for i in self.echo_due
                         if any(id(p) == i for p in self.board)}
        # GROWING RANKS: "At the beginning of your upkeep, populate."
        for _ in range(self.count("Growing Ranks")):
            self.populate("ranks")
        # DEFENSE OF THE HEART: "if an opponent controls three or more
        # creatures, sacrifice this enchantment, search your library for up
        # to two creature cards, put those cards onto the battlefield". The
        # pod's creature COUNT is exactly what this reads.
        for d in [p for p in self.board if p.card.name == "Defense of the Heart"]:
            if not any(o.creatures >= 3 for o in OPP.living(self)):
                break
            self.board.remove(d)
            self.graveyard.append(d.card)
            picks = []
            for _ in range(2):
                best = self.tutor_pick([c for c in self.library if c.is_creature
                                        and not any(c is q for q in picks)])
                if best is not None:
                    picks.append(best)
            perms = []
            # Bramble Sovereign first in the list so it is on the
            # battlefield as the other enters -- they enter TOGETHER and
            # see each other either way (603.6a).
            for c in picks:
                self.take(self.library, c)
                perms.append(self.make_permanent(c, sick=True))
            crn_shuffle(self, "defense", self.library)
            self.m["defense_fired"] += 1
            self.m["defense_creatures"] += len(perms)
            self.entered(perms)

    def draw_step(self):
        self.in_draw_step = True
        self.draw(1)
        self.in_draw_step = False
        # SYLVAN LIBRARY: "you may draw two additional cards. If you do,
        # choose two cards in your hand drawn this turn. For each of those
        # cards, pay 4 life or put the card on top of your library."
        if self.has("Sylvan Library") and self.result is None:
            before = len(self.hand)
            if not self.may_draw(2):
                return
            drawn = self.hand[before:]
            if len(drawn) < 2:
                return
            # The two worst cards of the turn's draws are the two chosen; the
            # better of them is kept first if the life allows.
            drawn.sort(key=lambda c: (c.priority if not c.is_land else 5, c.mv))
            chosen = drawn[:2]
            back = []
            kept = 0
            floor = self.cfg.get("library_life_floor", 20)
            for c in reversed(chosen):
                if self.your_life - 4 >= floor:
                    self.lose_life(4)
                    kept += 1
                    self.m["library_life_paid"] += 4
                else:
                    back.append(c)
            for c in back:
                self.take(self.hand, c)
                self.library.append(c)
            self.m["library_kept"] += kept

    def beginning_of_combat(self):
        # NESTING DOVEHAWK: "At the beginning of combat on your turn, populate."
        for _ in range(self.count("Nesting Dovehawk")):
            self.populate("dovehawk")
        # GOD-PHARAOH'S GIFT: "you may exile a creature card from your
        # graveyard. If you do, create a token that's a copy of that card,
        # except it's a 4/4 black Zombie. It gains haste until end of turn."
        for _ in range(self.count("God-Pharaoh's Gift")):
            pool = [c for c in self.graveyard if c.is_creature
                    and not (c.name in LEGENDARY and self.has(c.name))]
            if not pool:
                break
            best = max(pool, key=lambda c: (c.name in ETB_BY_NAME
                                            or c.name in DEATH_BY_NAME,
                                            c.priority, c.mv))
            self.take(self.graveyard, best)
            self.exile.append(best)
            self.m["gpg_tokens"] += 1
            self.create_tokens(copy_card(best, fixed=(4, 4), colours="B"), 1,
                               hasty=True)

    def attackers(self):
        out = []
        toks = any(p.is_token and p.card.is_creature for p in self.board)
        for p in self.creatures():
            if p.tapped or (p.sick and id(p) not in self.hasty):
                continue
            if self.power_of(p) <= 0:
                continue
            if p.card.name == "Sylvan Caryatid":       # Defender
                continue
            if p.card is self.commander and toks and not self.cfg.get(
                    "trostani_attacks", False):
                continue
            out.append(p)
        return out

    def combat(self):
        self.beginning_of_combat()
        if self.result is not None:
            return
        attackers = self.attackers()
        if not attackers:
            self.damage_by_turn.append(0.0)
            return
        # BLADE OF SELVES: myriad -- "for each opponent other than defending
        # player, you may create a token copy that's tapped and attacking
        # that player ... Exile the tokens at end of combat." The copies are
        # TOKENS ENTERING, so Trostani, the doublers and Caretaker's Talent
        # all see them; each joins the one attack the pod model declares.
        myriad = []
        if self.blade_on is not None and self.blade_on in attackers:
            n = max(0, len(OPP.living(self)) - 1)
            if n and not (self.blade_on.card.name in LEGENDARY):
                myriad = self.create_tokens(self.blade_on.card, n, sick=False,
                                            tapped=True)
                self.m["myriad_tokens"] += len(myriad)
        if any(p.card.name == "Sun Titan" for p in attackers):
            for _ in range(sum(1 for p in attackers
                               if p.card.name == "Sun Titan")):
                self.sun_titan()
        for p in attackers:
            p.tapped = True
        attackers = attackers + [p for p in myriad if p in self.board]
        self.combat_hits = []
        dmg = OPP.combat_damage(self, attackers)
        self.combat_hits = None
        self.m["damage"] += dmg
        self.m["combat_damage"] += dmg
        self.damage_by_turn.append(dmg)
        for p in attackers:
            if p.card.lifelink and p in self.board:
                self.gain_life(self.power_of(p))
        if self.result is None and self.m["turn_lethal"] == 99 \
                and not OPP.living(self):
            self.m["turn_lethal"] = self.turn
        for p in myriad:                       # "at end of combat"
            if p in self.board:
                self.board.remove(p)

    def end_step(self):
        for p in self.exile_at_end:            # Mimic Vat's tokens
            if p in self.board:
                self.board.remove(p)
        self.exile_at_end = []
        for p in self.sacrifice_at_end:        # encore's tokens
            self.sacrifice(p)
        self.sacrifice_at_end = []
        sakura_tribe_elder(self)

    def seedborn_turns(self):
        """SEEDBORN MUSE: untap everything on each opponent's turn and run the
        instant-speed abilities again. See the module docstring."""
        self.seedborn_lost = set()
        if not self.has("Seedborn Muse") or self.result is not None:
            return
        for i, opp in enumerate(OPP.living(self)):
            if self.result is not None:
                return
            self.turn_key = (self.turn, i + 1)
            for p in self.board:
                p.tapped = False
            self.dawn_paid_turn = 0
            self.m["seedborn_untaps"] += 1
            life = self.your_life
            self.sinks(sorcery=False)
            if self.your_life < life:          # Talisman, a Reservoir shot
                self.seedborn_lost.add(id(opp))
        self.turn_key = (self.turn, 0)

    def attack_share(self, i):
        """The share of opponent `i`'s swing aimed at you: THE SAME SELECTION
        `opponents.incidental_damage` makes -- `combat_targeting` picks the
        share, the monarch floors it. Written twice is §0u's shape, so
        `tests/test_trostani.py` T checks the two agree on random boards."""
        opp = self.opponents[i]
        others = [o for j, o in enumerate(self.opponents) if j != i and o.alive]
        if self.cfg.get("combat_targeting", "threat") == "open":
            share = OPP.combat_share(self, opp, others)
        else:
            share = OPP.your_share(self, opp, others)
        return OPP.monarch_attack_share(self, share)

    def luminarch_rolls(self):
        """Which opponents' turns will cost you no life this round -- for
        LUMINARCH ASCENSION's "if you didn't lose life this turn".

        The pod's chip damage is an EXPECTATION spread over every opponent
        with a creature (`incidental_damage`), so read literally it costs you
        life on every turn from the third, and the card never gets a counter
        (0.24 a game, measured 2026-10-01 -- the engine had made it a blank).
        At a table each opponent's attack goes at ONE player: it comes at you
        with probability `attack_share`, the very share the chip damage is
        weighted by. So each opponent's turn is rolled against that share
        (`crn_random`, one addressed stream per seat, §0z17), and only while a
        Luminarch is out. `luminarch_per_opponent=False` restores the
        round-level rule: any loss in the round, no counters at all."""
        if not self.has("Luminarch Ascension"):
            return None
        if not self.cfg.get("luminarch_per_opponent", True):
            return [(o, None) for o in self.opponents if o.alive]
        attacks = (OPP.pod_turn(self) >= self.cfg.get("first_attack_turn", 3)
                   and not OPP.protected_from_creatures(self))
        out = []
        for i, o in enumerate(self.opponents):
            if not o.alive:
                continue
            hit = (attacks and o.creatures > 0
                   and crn_random(self, f"luminarch{i}") < self.attack_share(i))
            out.append((o, not hit and id(o) not in self.seedborn_lost))
        return out

    def luminarch_counters(self, rolls, lost_in_round):
        """"At the beginning of each opponent's end step, if you didn't lose
        life this turn, you may put a quest counter on this enchantment." One
        counter per opponent whose turn cost you nothing (`luminarch_rolls`)
        and who is still in the game at its end step. A seat whose verdict is
        None -- the round-level rule -- earns one only in a round that cost no
        life at all."""
        if not rolls:
            return
        n = sum(1 for o, safe in rolls if o.alive and (
            safe if safe is not None else not lost_in_round))
        for lum in [p for p in self.board if p.card.name == "Luminarch Ascension"]:
            self.quest[id(lum)] = self.quest.get(id(lum), 0) + n
            self.m["quest_counters"] += n

    def populate_soul_first(self):
        """A Soul of Eternity token is the best populate target there is --
        each copy doubles your life, and every Soul already on the battlefield
        grows with it -- so with one out Trostani populates BEFORE the main
        phase spends her mana (`populate_soul_first`). Shilgengar's §0t lesson:
        a greedy main phase starves an ability that runs after it."""
        if not self.cfg.get("populate_soul_first", True):
            return
        tgt = self.populate_target()
        if tgt is None or tgt.card.name != "Soul of Eternity" \
                or "fixed_pt" in tgt.card.tags:
            return
        for t in self.untapped(COMMANDER_NAME, need_unsick=True):
            if self.pay({"gen": 1, "G": 1, "W": 1}):
                t.tapped = True
                self.populate("trostani_first")
                return


def take_turn(g):
    g.turn += 1
    g.turn_key = (g.turn, 0)
    g.spells_this_turn = 0
    g.dawn_paid_turn = 0
    g.hasty = set()
    g.team_indestructible = False
    g.tokens_indestructible = False
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.land_drops_used = 0

    g.upkeep()
    if g.result is not None:
        return
    g.draw_step()
    if g.result is not None:
        return
    g.land_step()
    g.precombat_actions()
    g.main_phase(precombat=True)
    if g.result is not None:
        return
    g.elspeth_step()          # a walker cast this phase activates this turn
    g.combat()
    if g.result is not None:
        return
    g.main_phase(precombat=False)
    if g.result is not None:
        return
    g.elspeth_step()
    g.sinks(sorcery=True)
    g.greater_good()
    g.end_step()

    g.m["mana_floated"] += len(g.available_mana())
    g.m["stranded_mv"] += sum(c.mv for c in g.hand if not c.is_land)

    if g.result is None:
        g.seedborn_turns()
    if g.result is None and g.cfg.get("opponents", True):
        rolls = g.luminarch_rolls()
        life = g.your_life
        OPP.pod_phase(g)           # one order for every engine, §0z30
        if g.result is None:
            g.luminarch_counters(rolls, g.your_life < life)


def simulate(deck, commander, cfg, seed):
    g = TrostaniGame(deck, commander, cfg, seed)
    g.opening_hand()
    # From here the game RNG must never be touched again. §0z17.
    seal_rng(g)
    snaps = Snapshots(cfg)                 # §0z93
    for i in range(cfg.get("turns", 20)):
        take_turn(g)
        if g.result is not None:
            break
        snaps.after_round(g, i + 1, finish)
    return snaps.attach(g, finish(g))


def check_name_tables():
    """Every card this engine names in a table is in a Trostani list (§0q).
    A name that is in none is a claim about a card nobody plays."""
    from edhmc.decks import discover_current_decks
    mod = discover_current_decks().get("trostani")
    if mod is None:
        return
    deck, cmd = mod.build()
    names = {c.name for c in deck} | {cmd.name}
    for attr in dir(mod):
        v = getattr(mod, attr)
        if type(v).__name__ == "Card":
            names.add(v.name)
    stale = (set(ETB_BY_NAME) | set(DEATH_BY_NAME)) - names
    if stale:
        raise ImportError(f"edhmc/trostani.py names cards no trostani list "
                          f"holds: {sorted(stale)} (§0q)")


check_name_tables()
