"""
edhmc.tivit — the Tivit, Seller of Secrets engine.

    Tivit, Seller of Secrets  {3}{W}{U}{B}  6/6 flying, ward {3}
      Council's dilemma — Whenever Tivit ENTERS OR DEALS COMBAT DAMAGE TO A
      PLAYER, each player votes for evidence or bribery. Evidence: investigate
      (a Clue). Bribery: a Treasure.
      While voting, you may vote an additional time.

WHAT THIS DECK ACTUALLY DOES, and therefore what the engine has to model:

  1. TIVIT MAKES ARTIFACTS ON A TRIGGER YOU CAN REPEAT. Every vote makes one,
     and there is no mode that makes none, so the pod cannot vote you out of
     it. In a four-player game that is five artifacts a trigger (your two
     votes plus three opponents').
  2. ACADEMY MANUFACTOR TRIPLES IT. "If you would create a Clue, Food, or
     Treasure token, instead create one of each" -- five votes become FIFTEEN
     artifacts, five of them Treasures.
  3. TREASURES PAY FOR THE BLINK THAT MAKES MORE TREASURES. Deadeye Navigator
     soulbound to Tivit is "{1}{U}: dilemma" -- two mana in, one dilemma out.
     The loop pays for itself when (your votes) x (token kinds) > 2, and Tivit
     alone is exactly 2 x 1 = 2: break even, and it stops. Either Academy
     Manufactor (x3 kinds) OR one extra-vote creature (3 votes) tips it. See
     deadeye_loop() for the measured numbers -- the two-route finding came out
     of the ablation and corrected what this file originally claimed.
  4. THE PILE CONVERTS. Time Sieve turns five artifacts into an extra turn;
     Marionette Master and Disciple of the Vault turn them into damage;
     Revel in Riches and Mechanized Production are outright alternate wins.

WHAT IS DELIBERATELY NOT MODELLED, so no one reads a zero as a verdict:

  * Opponents' permanents, as everywhere else in this project. Every targeted
    removal spell in the list ablates to ~0 for that reason and is in
    KNOWN_BLIND, not because the cards are bad.
  * The choice of WHICH permanent a vote exiles (Council's Judgment).
  * Ward {3}, Ghostly Prison and Propaganda as attack taxes -- the opponent
    model's combat is a share, not a set of declared attackers, so a tax on
    attacking cannot be expressed. Both Prisons are `fog`-tagged and blind.
  * Illusion of Choice's card draw is modelled; its vote control is the point
    and IS modelled (see voting.vote_control).

The vote model, and why its default is deliberately pessimistic, is in
edhmc/voting.py. Read that before trusting any number about a vote card.
"""

from __future__ import annotations

import random

from edhmc.engine import (BaseGame, finish, lookahead_pick, Metrics, london_mulligan, Board, Card, Permanent, can_pay, play_land,
                          engine_cfg, choose_mode,
                          CRNStreams, crn_random, crn_randrange,
                          crn_shuffle, make_rng, seal_rng,
                          enter_loyalty, walker_ready, walker_dies_at_zero)
from edhmc import opponents as OPP
from edhmc import voting as V

TOKEN_KINDS = ("Treasure", "Clue", "Food")


class TivitGame(BaseGame):
    def __init__(self, deck, commander, cfg, seed):
        # A PRIVATE copy: the cfg.setdefault block below stamps this
        # engine's defaults, and doing that to the CALLER'S dict let the
        # first engine constructed decide them for every later one.
        # See engine.engine_cfg.
        self.cfg = cfg = engine_cfg(cfg)
        self.rng = make_rng(seed, cfg)
        # Mid-game randomness lives here, NOT on self.rng. §0z17.
        self.crn = CRNStreams(seed)
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
        self.extra_turns = 0
        self.illusion_active = False
        self.ephemerate_rebound = 0     # turn on which the rebound copy casts
        self.deadeye_paired = False
        self.cyberdrive_turn = -1       # turn Cyberdrive Awakener entered
        self.result = None
        # Token piles. Ints rather than Permanents: none of them is a creature
        # and nothing in this deck reads an individual one.
        self.tokens = {k: 0 for k in TOKEN_KINDS}
        # POWERSTONES (Dyfed, §0z74) are a pile like the three above but NOT
        # one of TOKEN_KINDS: that tuple is Academy Manufactor's "one of each"
        # replacement, which a Powerstone is not part of. In `tokens` so that
        # `artifact_count`, Cyberdrive and Time Sieve's fuel all see them.
        self.tokens["Powerstone"] = 0
        self.powerstones_tapped = 0     # of the pile; they untap each turn
        self.venser_return = False      # Tivit is in exile until end step
        self.soldier_tokens = 0         # Lieutenants / Vault 11, real bodies
        self.saga_lore = {}             # id(Saga permanent) -> lore (§0z83)

        cfg.setdefault("shroud_sources", ("Lightning Greaves",))
        cfg.setdefault("protection_cards", ())
        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = Metrics({
            "damage": 0.0, "drain_damage": 0.0, "combat_damage": 0.0,
            "cards_drawn": 0, "spells_cast": 0,
            "mana_spent": 0, "mana_floated": 0, "stranded_mv": 0,
            "turn_lethal": 99, "turn_won": 99,
            "removal_eaten": 0, "ae_removal_eaten": 0, "wipes_suffered": 0,
            "countered": 0, "protected": 0,
            "cast_test_card": 0, "test_card_turn": 99,
            "test_card_answered": 0, "test_card_removed": 0,
            "test_card_countered": 0,
            # --- the vote ---
            "votes_cast": 0, "dilemmas": 0, "councils": 0, "councils_won": 0,
            "offers_taken": 0, "grudge_damage": 0.0, "unity_scrys": 0,
            "illusion_turns": 0,
            # --- the artifact engine ---
            "treasures_made": 0, "clues_made": 0, "food_made": 0,
            "artifacts_made": 0, "manufactor_extra": 0,
            # Reality Fracture, 2026-09-21 (preview text).
            "memnarch_draws": 0,
            "treasures_spent": 0, "clues_cracked": 0,
            "blinks": 0, "deadeye_activations": 0, "combo_iterations": 0,
            "tivit_triggers": 0, "extra_turns": 0,
            "sieve_activations": 0, "sieve_chain_max": 0, "sieve_real_fuel": 0,
            # `extra_turns` is turns GRANTED; these two are what was actually
            # taken and how many rounds the pod got. The gap between granted and
            # taken is what the discarded-chain bug used to throw away.
            "extra_turns_taken": 0, "pod_rounds": 0,
            # --- routes out ---
            "win_route": 0, "loss_route": 0,
            "token_drain": 0.0, "artifact_drain": 0.0,
        })
        self.damage_by_turn = []

    # -- helpers ------------------------------------------------------------

    # URZA'S CONSTRUCT: "This token gets +1/+1 for each artifact you control."
    # Its P/T is DYNAMIC and must be read live, never frozen at creation --
    # §0z3 is the record of what freezing one costs: Ka-Zar was measured as a
    # 16/16 instead of a 3/2 because a dynamic body went into the wrong set,
    # and every number in that batch had to be restated.
    URZA_CONSTRUCT = "Construct token"

    def power_of(self, perm):
        if perm.card.name == self.URZA_CONSTRUCT:
            return perm.card.power + perm.counters + self.artifact_count()
        return perm.card.power + perm.counters

    def toughness_of(self, perm):
        if perm.card.name == self.URZA_CONSTRUCT:
            return perm.card.toughness + perm.counters + self.artifact_count()
        return perm.card.toughness + perm.counters

    def artifact_count(self) -> int:
        """Everything Time Sieve, Marionette Master and Disciple of the Vault
        can actually see: token artifacts, artifact permanents, and the three
        ARTIFACT LANDS, which are artifacts as well as lands."""
        n = sum(self.tokens.values())
        for p in self.board:
            if "Artifact" in p.card.types:
                n += 1
        return n

    def make_tokens(self, n, p, t, subtype="", tapped=False, artifact=False):
        """Real creature tokens (Soldiers, Rabbits). NOT the artifact piles.

        `artifact` types the token as an Artifact Creature, which is what Sai's
        Thopters and Urza's Construct are. It matters beyond flavour:
        `artifact_count()` counts board permanents carrying the type, and Time
        Sieve, Marionette Master and Disciple of the Vault all read it.
        """
        n = int(n)
        # ANOINTED PROCESSION -- HALF OF IT. This engine has TWO token paths,
        # this one and the module-level make_token() for the Clue/Food/Treasure
        # piles, and the doubler has to be said in BOTH or it silently covers
        # only half the card. That is §0z4's exact finding about mana doublers
        # ("said in available_mana AND spend or it does nothing"), and tivit is
        # the one deck where the token version of the trap is live.
        if self.has("Anointed Procession"):
            n *= 2
        types = {"Creature", "Artifact"} if artifact else {"Creature"}
        for _ in range(n):
            tok = Card(name=f"{subtype or 'Token'} token",
                       types=frozenset(types), power=p, toughness=t)
            self.board.append(Permanent(card=tok, tapped=tapped, sick=True,
                                        is_token=True))
        self.soldier_tokens += n
        on_tokens_created(self, n)

    def on_creature_death(self, n=1, perm=None):
        pass                      # no death payoffs in this list

    def play_card_trigger(self, card):
        pass

    def win(self, route: int):
        if self.result is None:
            self.result = "win"
            self.m["turn_won"] = self.turn
            self.m["win_route"] = route


# WIN_ROUTE codes, so a table can say HOW the deck won and not just that it did.
ROUTE_COMBAT = 1
ROUTE_REVEL = 2          # Revel in Riches, ten Treasures
ROUTE_MECHANIZED = 3     # Mechanized Production, eight of a name
ROUTE_DRAIN = 4          # Marionette / Disciple / Mirkwood / Kambal
ROUTE_TORMENT = 5        # Torment of Hailfire
ROUTE_TIME_SIEVE = 6     # extra turns until the pod is dead


# ---------------------------------------------------------------------------
# Tokens — the artifact engine
# ---------------------------------------------------------------------------

def make_token(g, kind, n=1):
    """Create n tokens of `kind`, honouring Academy Manufactor.

    "If you would create a Clue, Food, or Treasure token, instead create one of
    each." It is a REPLACEMENT effect on the creation, so it applies once per
    token created, and it turns one token into three -- not three of the same
    kind. Every one of them is an artifact.
    """
    if n <= 0:
        return 0
    # ANOINTED PROCESSION -- THE OTHER HALF. See make_tokens above. It doubles
    # the tokens CREATED, and Academy Manufactor's replacement then applies to
    # each of them, so the two stack the way the rules stack two replacements.
    if g.has("Anointed Procession"):
        n *= 2
    kinds = TOKEN_KINDS if g.has("Academy Manufactor") else (kind,)
    if len(kinds) > 1:
        g.m["manufactor_extra"] += n * (len(kinds) - 1)
    made = 0
    for k in kinds:
        g.tokens[k] += n
        g.m[f"{k.lower()}s_made" if k != "Food" else "food_made"] += n
        made += n
    g.m["artifacts_made"] += made
    on_tokens_created(g, made)
    return made


def on_tokens_created(g, n):
    """Payoffs that read "whenever you create a token"."""
    if n <= 0:
        return
    per = 0.0
    if g.has("Mirkwood Bats"):
        per += 1.0                     # "each opponent loses 1"
    if g.has("Kambal, Profiteering Mayor"):
        per += 1.0                     # "each opponent loses 1 and you gain 1"
    if per:
        # `pod_size`, not `living`: this builds a POD TOTAL that
        # `deal_pod_damage` divides straight back down, so the two have to
        # agree or the knob restores a behaviour that never shipped.
        dmg = per * n * OPP.pod_size(g)
        g.deal_pod_damage(dmg)
        g.m["token_drain"] += dmg
        if g.result == "win":
            g.m["win_route"] = ROUTE_DRAIN


def sacrifice_tokens(g, kind, n) -> int:
    """Remove n tokens of `kind` and fire everything that reads a token or an
    artifact LEAVING the battlefield. Returns how many actually went."""
    n = min(n, g.tokens[kind])
    if n <= 0:
        return 0
    g.tokens[kind] -= n
    per = 0.0
    if g.has("Nadier's Nightblade"):
        per += 1.0                     # "whenever a token you control leaves"
    if g.has("Mirkwood Bats"):
        per += 1.0                     # "create OR sacrifice a token"
    per += disciple_share(g)
    if per:
        dmg = per * n * OPP.pod_size(g)          # see the Mirkwood site above
        g.deal_pod_damage(dmg)
        g.m["token_drain"] += dmg
    artifact_left_drain(g, n)
    if g.result == "win":
        g.m["win_route"] = ROUTE_DRAIN
    return n


def disciple_share(g) -> float:
    """Disciple of the Vault: "Whenever an artifact is put into a graveyard
    from the battlefield, you may have target opponent lose 1 life." ONE
    opponent loses 1, carried as its share of an each-opponent total: this
    `living` is the real count of players the damage will be spread over and
    is NOT the pod-total divisor, so it stays. One function for the token and
    the real-artifact paths (§0z71)."""
    if not g.has("Disciple of the Vault"):
        return 0.0
    return 1.0 / max(1, len(OPP.living(g)))


def artifact_left_drain(g, n) -> None:
    """Marionette Master: "Whenever an artifact you control is put into a
    graveyard from the battlefield, target opponent loses life equal to this
    creature's power" -- a single target, and the Master is a 1/3 with
    fabricate 3 taken as counters, so power 4.

    ONE FUNCTION for tokens AND real artifacts (§0z71): Time Sieve can now
    feed on a signet, and the Master reads that exactly as it reads a
    Treasure. Disciple of the Vault reads real artifacts too, but its share is
    folded into `sacrifice_tokens`' per-token sum with two token-only cards,
    so both paths read its share from `disciple_share`.
    """
    if g.has("Marionette Master"):
        power = 4.0
        dmg = power * n
        g.deal_pod_damage(dmg, each=False)
        g.m["artifact_drain"] += dmg


def sieve_real_fuel(g) -> list:
    """The REAL artifacts Time Sieve may eat, in the order it eats them (§0z71).

    `sieve_real_fuel` (the owner's two conditions, 2026-09-27):
      "never"  tokens only -- every table before §0z71.
      "cap"    also real artifacts of mana value <= `sieve_real_mv_cap` (2):
               Sol Ring, the signets, Lightning Greaves, the artifact lands.
      "combo"  the same, but ONLY while Tivit is on the battlefield -- the
               loop that rebuilds the pile next turn is live, so the pilot
               knows the next extra turn is coming.
    Never Time Sieve itself, never a creature. THE ORDER IS A JUDGEMENT:
    what taps for no mana first (Greaves), then rocks from least mana to
    most, then the artifact lands last -- a land is a land drop as well.
    """
    mode = g.cfg.get("sieve_real_fuel", "combo")
    if mode == "never":
        return []
    if mode == "combo" and not any(p.card is g.commander for p in g.board):
        return []
    cap = g.cfg.get("sieve_real_mv_cap", 2)
    pool = [p for p in g.board
            if "Artifact" in p.card.types and p.card.name != "Time Sieve"
            and not p.card.is_creature and not p.is_token
            and p.card.mv <= cap]
    return sorted(pool, key=lambda p: (p.card.is_land,
                                       (p.card.mana_ability or (0,))[0],
                                       p.card.mv))


def sacrifice_real_artifacts(g, perms) -> None:
    """Sacrifice real artifact permanents: to the graveyard, with every
    trigger that reads an artifact leaving (§0z71)."""
    for p in perms:
        g.board.remove(p)
        g.graveyard.append(p.card)
    n = len(perms)
    share = disciple_share(g)
    if n and share:
        dmg = share * n * OPP.pod_size(g)
        g.deal_pod_damage(dmg)
        g.m["token_drain"] += dmg
    artifact_left_drain(g, n)
    g.m["sieve_real_fuel"] += n
    if g.result == "win":
        g.m["win_route"] = ROUTE_DRAIN


# ---------------------------------------------------------------------------
# Mana
# ---------------------------------------------------------------------------

def untapped_powerstones(g) -> int:
    return max(0, g.tokens["Powerstone"] - g.powerstones_tapped)


def mana_units(g, powerstones: bool = False) -> list[frozenset]:
    """One entry per point of mana available, Treasures included.

    A Treasure is "{T}, Sacrifice: add one mana of any color", so it is a
    one-shot any-colour source. It is listed LAST so `can_pay`'s
    most-constrained-first rule spends real lands before burning Treasures --
    which matters, because a spent Treasure is an artifact that has left the
    battlefield and that is a payoff, not just a cost.
    """
    any_col = frozenset({"W", "U", "B", "C"})
    units = []
    for p in g.board:
        if p.tapped:
            continue
        c = p.card
        if c.is_land:
            units.append(frozenset(c.produces))
        elif c.mana_ability:
            amt, colors = c.mana_ability
            units.extend([colors] * amt)
    # POWERSTONES (Dyfed, §0z74): "{T}: Add {C}. This mana can't be spent to
    # cast a NONARTIFACT spell." So they are offered only to a payment that
    # says it may take them -- an artifact spell, or an activated ability --
    # and they sit BETWEEN the real mana and the Treasures, so `pay` can tell
    # the three apart. With no Powerstones this is the pool it always was.
    if powerstones:
        units.extend([frozenset({"C"})] * untapped_powerstones(g))
    units.extend([any_col] * g.tokens["Treasure"])
    return units


def pay(g, cost, powerstones: bool = False) -> bool:
    """Spend `cost` if affordable. Treasures are consumed last and their
    sacrifice fires the artifact-leaves payoffs. `powerstones` lets Dyfed's
    restricted mana pay too (an artifact spell or an ability, §0z74)."""
    units = mana_units(g, powerstones)
    idx = can_pay(cost, units)
    if idx is None:
        return False
    n_units = len(units)
    n_treasure = g.tokens["Treasure"]
    first_treasure = n_units - n_treasure
    used_treasures = sum(1 for i in idx if i >= first_treasure)
    n_stone = untapped_powerstones(g) if powerstones else 0
    first_stone = first_treasure - n_stone
    used_stones = sum(1 for i in idx if first_stone <= i < first_treasure)
    if used_stones:
        g.powerstones_tapped += used_stones
        g.m["powerstone_mana"] += used_stones

    # tap the real sources
    real = sorted(i for i in idx if i < first_stone)
    pos = 0
    for p in g.board:
        if p.tapped:
            continue
        c = p.card
        width = 1 if c.is_land else (c.mana_ability[0] if c.mana_ability else 0)
        if width == 0:
            continue
        if any(pos <= i < pos + width for i in real):
            p.tapped = True
        pos += width

    g.m["mana_spent"] += len(idx)
    if used_treasures:
        sacrifice_tokens(g, "Treasure", used_treasures)
        g.m["treasures_spent"] += used_treasures
    return True


def affordable(g, cost, powerstones: bool = False) -> bool:
    return can_pay(cost, mana_units(g, powerstones)) is not None


# ---------------------------------------------------------------------------
# The commander's dilemma
# ---------------------------------------------------------------------------

def tivit_dilemma(g):
    """"For each evidence vote, investigate. For each bribery vote, create a
    Treasure token."

    YOUR votes go to bribery: this deck wants mana far more than it wants
    Clues, because mana is what re-triggers the dilemma. An ADVERSARIAL pod
    votes evidence for the same reason -- denying Treasures is the only lever
    they have, and it is a weak one, because a Clue is still an artifact and
    every artifact payoff in the deck counts it.
    """
    if not g.has("Tivit, Seller of Secrets"):
        return
    mine, theirs = V.dilemma(g, "tivit")
    g.m["tivit_triggers"] += 1
    make_token(g, "Treasure", mine)
    make_token(g, "Clue", theirs)


def blink_tivit(g, source):
    """Exile and return Tivit: a fresh ETB, so a fresh dilemma."""
    if not g.has("Tivit, Seller of Secrets"):
        return False
    g.m["blinks"] += 1
    venser_counters(g)
    tivit_dilemma(g)
    return True


def venser_counters(g) -> None:
    """VENSER, VISIONARY TRAVELER (§0z74): "Each nontoken creature you
    control that wasn't cast from your hand enters with two additional +1/+1
    counters on it."

    Tivit re-entering from a blink was not cast at all, and Tivit cast from
    the COMMAND ZONE was not cast from the hand, so both get the counters.
    A blink here keeps the same Permanent (`blink_tivit` models the fresh ETB
    as a fresh dilemma, not a new object), so the counters are SET to two --
    a new object has only these -- rather than added. Only when Venser is out,
    so a game without him cannot move. NOT modelled: the other ways a creature
    enters uncast here (Magister of Worth's grace returns), which makes the
    static a floor."""
    if not g.has("Venser, Visionary Traveler"):
        return
    for p in g.board:
        if p.card is g.commander:
            p.counters = 2
            g.m["venser_counters"] += 2


def crack_clues(g, want=1) -> int:
    """"{2}, Sacrifice this artifact: Draw a card." Cracked only with spare
    mana, and the sacrifice is itself a payoff via Nadier's / Mirkwood /
    Marionette."""
    drawn = 0
    for _ in range(int(want)):
        if g.tokens["Clue"] <= 0 or not affordable(g, {"gen": 2}, True):
            break
        if not pay(g, {"gen": 2}, powerstones=True):   # an ability, §0z74
            break
        sacrifice_tokens(g, "Clue", 1)
        g.draw(1)
        g.m["clues_cracked"] += 1
        drawn += 1
    return drawn


# ---------------------------------------------------------------------------
# The combo: Deadeye Navigator + Tivit, priced honestly
# ---------------------------------------------------------------------------

def deadeye_loop(g):
    """"{1}{U}: Exile this creature, then return it." Soulbound to Tivit.

    Each activation costs TWO MANA and yields one dilemma. Your own votes buy
    Treasures; an adversarial pod's votes buy Clues. So the loop pays for
    itself exactly when

        (your votes) x (token kinds per vote) > 2

    and THERE ARE TWO INDEPENDENT ROUTES TO THAT, which is not what this
    docstring claimed when it was written. Measured directly, starting from a
    ten-Treasure pool with no lands (diag_tivit_combo.py, and the unit check
    in test_tivit_combo.py):

        Tivit + Deadeye alone        2 votes x 1 kind  = 2   1 iteration,
                                     10 Treasures -> 10. EXACTLY break even,
                                     and the loop stops on its own.
        + Academy Manufactor         2 votes x 3 kinds = 6   runs to the cap,
                                     10 -> 130.
        + Ballot Broker              3 votes x 1 kind  = 3   runs to the cap,
                                     10 -> 50.
        + Ballot Broker + Brago's    4 votes x 1 kind  = 4   10 -> 90.
        + Manufactor + Ballot        3 x 3             = 9   10 -> 170.

    SO THE EXTRA-VOTE CREATURES ARE COMBO PIECES, not merely vote-count cards.
    One of them alone turns the treadmill into an engine without Manufactor,
    which is worth knowing before cutting either as "just a body". The
    original framing here -- Manufactor or nothing -- was wrong, and the
    ablation is what found it.

    The cap is a modelling necessity, not a rules one. `combo_cap` iterations
    per activation window is treated as "arbitrarily large"; the deck then
    needs a payoff on the battlefield to convert it, and if it has none the
    pile just sits there -- which is the honest outcome and is worth being
    able to measure. Note `combo_iterations` ACCUMULATES ACROSS TURNS, so a
    value above the cap is several capped windows, not one.
    """
    if not (g.has("Deadeye Navigator") and g.has("Tivit, Seller of Secrets")):
        return
    cap = g.cfg.get("combo_cap", 40)
    n = 0
    while n < cap and affordable(g, {"gen": 1, "U": 1}, True):
        before = g.tokens["Treasure"]
        if not pay(g, {"gen": 1, "U": 1}, powerstones=True):   # §0z74
            break
        blink_tivit(g, "Deadeye Navigator")
        g.m["deadeye_activations"] += 1
        n += 1
        # Stop when it stops paying for itself: a treadmill drains the pool
        # and there is no reason to keep going once we are not gaining.
        if g.tokens["Treasure"] <= before and not g.has("Academy Manufactor"):
            break
    g.m["combo_iterations"] += n
    if n >= cap:
        convert_the_pile(g)


def convert_the_pile(g):
    """An arbitrarily large pile of artifacts only wins if something converts.

    Checked in the order a pilot would take: the two alternate wins first
    because they need no combat, then the drains, then extra turns.
    """
    if g.has("Revel in Riches") and g.tokens["Treasure"] >= 10:
        g.win(ROUTE_REVEL)
        return
    if g.has("Mechanized Production") and g.tokens["Treasure"] >= 8:
        g.win(ROUTE_MECHANIZED)
        return
    drains = ("Marionette Master", "Disciple of the Vault", "Mirkwood Bats",
              "Nadier's Nightblade", "Kambal, Profiteering Mayor")
    if any(g.has(x) for x in drains):
        # Sacrifice the pile. Each token leaving is a trigger.
        sacrifice_tokens(g, "Treasure", g.tokens["Treasure"])
        sacrifice_tokens(g, "Clue", g.tokens["Clue"])
        sacrifice_tokens(g, "Food", g.tokens["Food"])
        sacrifice_tokens(g, "Powerstone", g.tokens["Powerstone"])
        g.powerstones_tapped = 0
        if g.result != "win":
            return
        g.m["win_route"] = ROUTE_DRAIN
        return
    if g.has("Time Sieve"):
        g.extra_turns += 5
        g.m["extra_turns"] += 5


# ---------------------------------------------------------------------------
# Casting
# ---------------------------------------------------------------------------

def reduce_cost(g, card) -> dict:
    return dict(card.cost)


def main_phase(g):
    """Greedy: repeatedly cast the highest-priority affordable spell.

    Same policy as the other three engines. The one Tivit-specific rule is
    that the commander goes first once affordable -- every other card in the
    list is either a payoff for its trigger or a way to re-trigger it.
    """
    while True:
        if not g.commander_cast:
            ccost = dict(g.commander.cost)
            ccost["gen"] = ccost.get("gen", 0) + g.commander_tax
            if affordable(g, ccost):
                pay(g, ccost)
                idx = g.spells_this_turn
                g.spells_this_turn += 1
                if OPP.countered(g, g.commander, idx):
                    g.m["countered"] += 1
                    g.commander_tax += 2
                    continue
                g.board.append(Permanent(card=g.commander,
                                         sick=not g.has("Lightning Greaves")))
                venser_counters(g)       # cast from the command zone, §0z74
                g.commander_cast = True
                g.m["spells_cast"] += 1
                tivit_dilemma(g)               # the ETB half
                if g.result is not None:
                    return
                continue

        options = []
        units = mana_units(g)
        for c in g.hand:
            if c.is_land:
                continue
            if "wipe" in c.tags and not OPP.should_cast_own_wipe(g):
                continue
            # A ONE-SHOT blink with nothing to blink is a wasted card. The
            # permanent blinkers (Soulherder, Teleportation Circle, ...) are
            # engines worth deploying before the commander lands; an instant is
            # not. `blink_tivit` already refuses to do anything without Tivit on
            # the battlefield, so without this gate the greedy policy simply
            # threw the card away on turn one.
            if "blink" in c.tags and not c.is_permanent \
                    and not g.has("Tivit, Seller of Secrets"):
                continue
            # §1b: every way the card can be cast, not just the printed
            # cost. No card in this list declares one today; the point is
            # that one CAN, and check_alt_cost_coverage enforces it.
            # An ARTIFACT spell may also spend Powerstone mana (§0z74); the
            # pool is only different when a Powerstone is untapped.
            pool = (mana_units(g, True) if "Artifact" in c.types
                    and untapped_powerstones(g) else units)
            _m = choose_mode(c, reduce_cost(g, c), pool)
            if _m is not None:
                options.append((c, _m[2], _m[0]))
        if not options:
            return
        # item 18: greedy unless `cast_lookahead`. Tivit's own `pay` makes
        # the payment below; the one `choose_mode` proved is what the
        # lookahead reads, the same pool every option was priced against.
        card = lookahead_pick(
            g, options, units, lambda it: (it[0].priority, it[0].mv),
            cost_of=lambda it: it[2], pay_of=lambda it: it[1])[0]
        if not pay(g, reduce_cost(g, card),
                   powerstones="Artifact" in card.types):
            return
        g.hand.remove(card)
        idx = g.spells_this_turn
        g.spells_this_turn += 1
        if OPP.countered(g, card, idx):
            g.m["countered"] += 1
            g.graveyard.append(card)
            continue
        g.m["spells_cast"] += 1
        # SAI, MASTER THOPTERIST: "Whenever you cast an ARTIFACT SPELL, create
        # a 1/1 colorless Thopter artifact creature token with flying."
        # Hooked on the CAST, not the resolution, so a countered artifact
        # spell still makes the Thopter -- which is what the card says.
        if "Artifact" in card.types and g.has("Sai, Master Thopterist"):
            g.make_tokens(1, 1, 1, "Thopter", artifact=True)
            g.m["sai_thopters"] += 1
        if card.name in g.cfg.get("watch", ()):
            g.m["cast_test_card"] = 1
            g.m["test_card_turn"] = min(g.m["test_card_turn"], g.turn)
        resolve(g, card)
        if g.result is not None:
            return
        # Displacer Kitten: "whenever you cast a NONCREATURE spell, exile up to
        # one target nonland permanent you control, then return it." Pointed at
        # Tivit, that is a dilemma per noncreature spell.
        if g.has("Displacer Kitten") and "Creature" not in card.types:
            blink_tivit(g, "Displacer Kitten")
            if g.result is not None:
                return


def resolve(g, card):
    """Put a spell's effect on the board, or its permanent."""
    s = card.script

    if card.name == "Urza, Lord High Artificer":
        # "When Urza enters, create a 0/0 colorless Construct artifact creature
        # token with 'This token gets +1/+1 for each artifact you control.'"
        #
        # A FLOOR, AND THE MISSING HALVES ARE NAMED. Urza's other two abilities
        # are NOT modelled: "Tap an untapped artifact you control: Add {U}"
        # would make every artifact a mana source, and "{5}: shuffle, exile the
        # top card, play it free" is a repeatable free-cast engine. Both are
        # real and both are large, so this row is a LOWER BOUND on the card and
        # belongs in PARTLY_MODELLED -- a high score is evidence, a low score
        # is not. Implementing the body alone and calling the number the card
        # is the §0f failure this project has already paid for three times.
        g.make_tokens(1, 0, 0, "Construct", artifact=True)
        g.m["urza_constructs"] += 1
    if s == "illusion":
        # "You choose how each player votes this turn. Draw a card."
        g.illusion_active = True
        g.m["illusion_turns"] += 1
        g.draw(1)
    elif s == "tutor":
        _tutor(g, lambda c: True)
    elif s == "tutor_ench":
        _tutor(g, lambda c: "Enchantment" in c.types)
    elif s == "plea":
        # Will of the council: an extra turn, or draw three.
        if V.council(g):
            g.extra_turns += 1
            g.m["extra_turns"] += 1
        else:
            g.draw(3)
    elif s == "expropriate":
        # Council's dilemma: an extra turn per time vote, steal a permanent
        # per money vote. Stealing an opponent's permanent is not expressible
        # against a board that is a blocker count, so only the turns land --
        # this UNDERSTATES the card, which is why it is in KNOWN_BLIND.
        mine, _theirs = V.dilemma(g, "expropriate")
        g.extra_turns += mine
        g.m["extra_turns"] += mine
    elif s == "tyrants_choice":
        if not V.council(g):
            # A POD TOTAL, like every other deal_pod_damage caller: 4 life from
            # each of the pod's opponents. This used to scale by the LIVING
            # count, which cancelled the divisor `pod_size` has now fixed -- so
            # tivit was right and the other five engines were wrong.
            #
            # IT MULTIPLIES BY THE SAME `pod_size` THE DIVISOR USES, which is
            # what keeps `pod_damage_full_pod=False` an honest restoration:
            # numerator and divisor move together, so this site yields 4.0
            # apiece under BOTH settings and tivit reproduces bit-identically
            # either way. Writing `len(g.opponents)` here instead would have
            # made the knob restore a third behaviour that never shipped.
            g.deal_pod_damage(4.0 * OPP.pod_size(g))
    elif s == "capital_punishment":
        # Sacrifice and discard are both unmodelled against this opponent
        # model; only the vote payoffs (Grudge Keeper) actually land.
        V.dilemma(g, "capital")
    elif s == "trial" and g.cfg.get("saga_chapters", True):
        pass              # its vote is chapter IV, three draw steps away (§0z83)
    elif s in ("bite", "split_decision", "trial", "councils_judgment"):
        V.council(g)
    elif s == "magister":
        # "Will of the council — When this creature enters, starting with you,
        # each player votes for grace or condemnation. If grace gets more
        # votes, each player returns each creature card from their graveyard
        # to the battlefield. If condemnation gets more votes OR THE VOTE IS
        # TIED, destroy all creatures other than this creature."
        #
        # IT USED TO JUST VOTE AND THROW THE RESULT AWAY, sharing a branch
        # with four cards whose whole text is the vote. Neither mode existed.
        #
        # `tie_goes_to_you=True` because condemnation takes ties and
        # condemnation is what this deck wants: tivit's board is artifacts,
        # its creature count is low, and Magister survives its own wipe.
        #
        # NOT `tags=("wipe", "onesided")`, which is what it carried while the
        # tag did nothing: one-sided spares your WHOLE board, and the card
        # spares exactly one creature — itself. Resolving here, before the
        # permanent enters below, makes that exact rather than approximate.
        #
        # GRACE IS HALF MODELLED and understates: "EACH PLAYER returns each
        # creature card from their graveyard" is real for you and invisible
        # for a pod that has no graveyard (§4).
        if not g.cfg.get("tivit_sweepers", True):
            V.council(g)                 # the pre-fix branch: vote, discard it
        elif V.council(g, tie_goes_to_you=True):
            OPP.resolve_own_wipe(g, card=card)
            g.m["magister_wipes"] += 1
        else:
            for c in [x for x in g.graveyard if x.is_creature]:
                g.graveyard.remove(c)
                g.board.append(Permanent(card=c, sick=True))
                g.m["magister_returns"] += 1
    elif s == "shell_game":
        # "Starting with the next opponent in turn order, each player chooses
        # a creature YOU DON'T CONTROL. Destroy the chosen creatures."
        #
        # "You" is this card's controller, so EVERY choice comes off an
        # opponent's board — but it is one creature per player, not a board
        # wipe. It carried `tags=("wipe", "onesided")`, which would have
        # zeroed all three opponents' boards: up to 21 creature-equivalents
        # against the four the card actually kills. The tag was harmless while
        # nothing read it and would have become a 5x overstatement the moment
        # the branch below started working.
        #
        # Taken off the biggest board first, which is both what a pilot picks
        # and what the pod's own `creatures` float can express.
        picks = 1 + len(OPP.living(g)) if g.cfg.get("tivit_sweepers", True) else 0
        for _ in range(picks):
            fed = [o for o in OPP.living(g) if o.creatures >= 1.0]
            if not fed:
                break
            victim = max(fed, key=lambda o: o.creatures)
            victim.creatures -= 1.0
            g.m["shell_game_kills"] += 1
    elif s == "tempt_bunnies":
        n = V.tempting_offer(g)
        g.draw(n)
        g.make_tokens(n, 1, 1, "Rabbit")
    elif s == "vault11":
        # Chapter I only: "for each opponent, create a 1/1 Human Soldier".
        # Its two votes are chapters II and III, on later draw steps
        # (`saga_step`, §0z83). `saga_chapters=False` votes once, now -- the
        # engine before §0z83, which cast one vote the card does not have
        # at this point and dropped the second.
        if not g.cfg.get("saga_chapters", True):
            V.council(g)
        g.make_tokens(len(OPP.living(g)), 1, 1, "Soldier")
    elif s == "custodi":
        V.council(g)
        pool = [c for c in g.graveyard
                if c.types & {"Artifact", "Creature", "Enchantment"}]
        if pool:
            best = max(pool, key=lambda c: c.priority)
            g.graveyard.remove(best)
            g.hand.append(best)
    elif s == "lieutenants":
        _mine, theirs = V.dilemma(g, "lieutenants")
        g.make_tokens(theirs, 1, 1, "Soldier")
    elif s == "jays":
        _mine, theirs = V.dilemma(g, "jays")
        g.draw(theirs)
    elif s == "ephemerate":
        # "Exile target creature you control, then return it. REBOUND." One {W}
        # is two dilemmas, a turn apart.
        #
        # THIS BRANCH DID NOT EXIST until 2026-09-06, and its absence made the
        # card an exact blank: `main_phase` is greedy on priority, Ephemerate is
        # priority 8 for {W}, so it was always cast HERE -- fell through to the
        # graveyard having done nothing -- and left hand before `activations()`
        # could find it, which also meant the rebound was never armed. Both
        # hand-written Ephemerate paths were unreachable. Measured against a
        # blank of the same cost and priority it produced bit-identical games in
        # all 15,000 pairs. See KNOWN_ISSUES.md 0k.
        if blink_tivit(g, "Ephemerate"):
            g.ephemerate_rebound = g.turn + 1
    elif s == "torment":
        # "Repeat X times: each opponent loses 3 unless they sacrifice a
        # nonland permanent or discard." Against an opponent model with no
        # hand and no permanents the life is the ONLY branch that exists, so
        # this is a CEILING -- a real opponent pays with cards for a while.
        x = card.mv - 2
        # A POD TOTAL -- 3X from each of the pod's opponents. See the
        # Tyrant's Choice site above for why this reads `pod_size` and not
        # `living` or a bare `len(g.opponents)`.
        g.deal_pod_damage(3.0 * x * OPP.pod_size(g))
        if g.result == "win":
            g.m["win_route"] = ROUTE_TORMENT

    # THIS BRANCH DID NOT EXIST, AND FIVE CARDS WERE INERT BECAUSE OF IT.
    # `main_phase` has always gated casting a sweeper on
    # `OPP.should_cast_own_wipe`, so the tag was half-wired: the engine held
    # Damn, Farewell and Promise of Loyalty back until it was BEHIND on board
    # and then cast them for no effect at all. That is worse than a blank --
    # a blank does not wait for the worst moment to do nothing. The other four
    # engines have carried this one line since wipes were added (§5).
    #
    # It runs BEFORE the permanent enters, which is what lets Magister of
    # Worth's "destroy all creatures OTHER THAN THIS CREATURE" spare itself
    # without a special case: it is not on the battlefield yet.
    #
    # `tivit_sweepers=False` restores the whole pre-fix state -- this branch
    # gone, Magister voting and discarding the result, Shell Game inert --
    # which is what every tivit table published before this reproduces with.
    if "wipe" in card.tags and g.cfg.get("tivit_sweepers", True):
        OPP.resolve_own_wipe(g, spare_own="onesided" in card.tags, card=card)

    if card.is_permanent:
        perm = Permanent(card=card, sick=not card.haste)
        enter_loyalty(perm)          # Venser / Dyfed (§0z74)
        g.board.append(perm)
        if card.name in SAGA_CHAPTERS and g.cfg.get("saga_chapters", True):
            g.saga_lore[id(perm)] = 1        # "As this Saga enters ... add a
                                             #  lore counter": chapter I
        run_etb(g, perm)
    elif not card.is_land:
        g.graveyard.append(card)


# SAGAS WITH A VOTE (§0z83): "As this Saga enters and after your draw step,
# add a lore counter. Sacrifice after <final>." (Scryfall, 2026-09-29.)
# name -> (the chapters that vote, the final chapter). Only the votes are
# modelled; each card's other chapters need opposing creatures (§4), and its
# PARTLY reason in tools/ablation.py names them.
SAGA_CHAPTERS = {
    "Vault 11: Voter's Dilemma": ((2, 3), 3),
    "Trial of a Time Lord": ((4,), 4),
}


def saga_step(g):
    """After the draw step: a lore counter on each voting Saga, its chapter,
    and the sacrifice after its last. A Saga that left the battlefield
    early simply stops -- its id is dropped with it."""
    live = {id(p): p for p in g.board}
    for key in [k for k in g.saga_lore if k not in live]:
        del g.saga_lore[key]
    for key in list(g.saga_lore):
        perm = live[key]
        g.saga_lore[key] += 1
        chapter = g.saga_lore[key]
        votes, final = SAGA_CHAPTERS[perm.card.name]
        if chapter in votes:
            V.council(g)
            g.m["saga_votes"] += 1
            if g.result is not None:
                return
        if chapter >= final:
            g.board.remove(perm)
            g.graveyard.append(perm.card)
            del g.saga_lore[key]


def _tutor(g, pred):
    pool = [c for c in g.library if pred(c) and not c.is_land]
    if not pool:
        return
    best = max(pool, key=lambda c: c.priority)
    g.library.remove(best)
    g.hand.append(best)


def run_etb(g, perm):
    s = perm.card.script
    if s == "deadeye":
        # Soulbond pairs on entry with an unpaired creature; Tivit is the one
        # worth pairing with, and the pair is what grants the {1}{U} ability.
        g.deadeye_paired = g.has("Tivit, Seller of Secrets")
    elif s == "marionette":
        perm.counters += 3          # fabricate 3, taken as counters
    elif perm.card.name == "Memnarch, the Warden":
        # MEMNARCH, THE WARDEN (Reality Fracture, preview text 2026-09-21):
        # "{10} 8/9 Legendary Artifact Creature. Indestructible. When Memnarch
        # enters, create two 1/1 colorless MYR ARTIFACT creature tokens.
        # Whenever Memnarch attacks, draw a card for each artifact you control."
        #
        # `artifact=True` is load-bearing and not flavour: an artifact token is
        # counted by `artifact_count()`, which is what Time Sieve, Marionette
        # Master, Disciple of the Vault -- and Memnarch's own attack trigger --
        # all read. Two Myr that did not type as artifacts would be two bodies
        # instead of two pieces of this deck's engine.
        #
        # Its INDESTRUCTIBLE is not tagged here: that comes from Scryfall
        # through decks/_evasion.py, because hand-tagging a keyword biases the
        # whole table toward whatever got tagged.
        g.make_tokens(2, 1, 1, "Myr", artifact=True)
    elif s == "cyberdrive":
        # Its animation is an ETB, so record the turn; combat() applies the
        # burst only on that turn.
        g.cyberdrive_turn = g.turn


# ---------------------------------------------------------------------------
# Turn structure
# ---------------------------------------------------------------------------

def upkeep(g):
    # Ephemerate's rebound: "at the beginning of your NEXT upkeep, you may cast
    # this card from exile without paying its mana cost." One {W} is two
    # dilemmas, a turn apart.
    if g.ephemerate_rebound and g.turn >= g.ephemerate_rebound:
        g.ephemerate_rebound = 0
        blink_tivit(g, "Ephemerate")
        if g.result is not None:
            return

    if g.has("Tamiyo's Journal"):
        make_token(g, "Clue")
    if g.has("Havengul Laboratory // Havengul Mystery"):
        if affordable(g, {"gen": 4}) and pay(g, {"gen": 4}):
            make_token(g, "Clue")
    if g.has("Tempting Contract"):
        make_token(g, "Treasure", V.tempting_offer(g))
    if g.has("Master of Ceremonies"):
        # "Each opponent chooses money, friends, or secrets. For each player
        # who chose X, you AND that player each get X." You MATCH them, so it
        # is profit whichever way they go -- the same shape as the commander,
        # and the reason the card is worth a slot in a pod that hates you.
        n = len(OPP.living(g))
        pick = [crn_randrange(g, f"ceremonies{i}", 3) for i in range(n)]
        make_token(g, "Treasure", sum(1 for x in pick if x == 0))
        g.make_tokens(sum(1 for x in pick if x == 1), 1, 1, "Citizen")
        g.draw(sum(1 for x in pick if x == 2))
    if g.has("Monologue Tax"):
        # "Whenever an opponent casts their SECOND spell each turn, create a
        # Treasure." Taken as a per-round rate rather than tracked per
        # opponent -- the same abstraction lorehold.py uses for this card.
        make_token(g, "Treasure", g.cfg.get("monologue_tax_rate", 2))
    if g.has("Rhystic Study"):
        # "...unless that player pays {1}." Modelled as a flat rate, because
        # whether a table pays is a social fact this model has no way to see.
        g.draw(int(g.cfg.get("rhystic_rate", 1)))
    if g.has("Coercive Portal"):
        # Will of the council: draw, or sacrifice it and destroy all nonland
        # permanents. Ties go to HOMAGE, the draw -- which is the mode you
        # want, so this is one of the few councils where a tie is a win.
        if V.council(g, tie_goes_to_you=True):
            g.draw(1)
        else:
            OPP.resolve_own_wipe(g)
    if g.has("Mechanized Production"):
        make_token(g, "Treasure")
        if g.tokens["Treasure"] >= 8:
            g.win(ROUTE_MECHANIZED)
            return
    if g.has("Revel in Riches") and g.tokens["Treasure"] >= 10:
        g.win(ROUTE_REVEL)
        return


def end_step(g):
    """End-step blinks. Each is a fresh Tivit ETB, so a fresh dilemma."""
    # VENSER's +1: "At the beginning of the next end step, return that card to
    # the battlefield" (§0z74). Tivit went to exile in `walker_step`, AFTER
    # combat, so it attacked this turn and comes back now.
    if g.venser_return:
        g.venser_return = False
        blink_tivit(g, "Venser, Visionary Traveler")
        g.m["venser_blinks"] += 1
        if g.result is not None:
            return
    for name in ("Soulherder", "Teleportation Circle", "Conjurer's Closet"):
        if g.has(name):
            blink_tivit(g, name)
            if g.result is not None:
                return


def combat(g):
    attackers = [p for p in g.board
                 if p.card.is_creature and not p.tapped and not p.sick]
    if not attackers:
        g.damage_by_turn.append(0.0)
        return
    # MEMNARCH'S ATTACK TRIGGER: "Whenever Memnarch attacks, draw a card for
    # each artifact you control." It triggers on DECLARATION, not on damage, so
    # it fires here -- before `combat_damage` and regardless of what gets
    # through, which is the difference between this and the commander's own
    # "deals combat damage to a player" trigger at the bottom of this function.
    #
    # `artifact_count()` is the one place that question is answered, so the
    # draw counts token piles, artifact permanents and the three artifact lands
    # exactly as Time Sieve does. In a deck that makes 51-67 artifacts a game
    # this is a large number of cards. Until 2026-09-22 the draw was A CEILING
    # because `draw()` stopped at an empty library and recorded no loss;
    # it is a loss now (queued item 17, §0z42), and this draw is unguarded --
    # the trigger is not modelled as a choice, so a Memnarch that draws more
    # than the library holds decks you here exactly as it would at a table.
    for p in attackers:
        if p.card.name == "Memnarch, the Warden":
            n = g.artifact_count()
            g.draw(n)
            g.m["memnarch_draws"] += n
    raw = sum(g.power_of(p) for p in attackers)
    # Cyberdrive Awakener: "WHEN THIS CREATURE ENTERS, each noncreature
    # artifact you control becomes a 4/4 artifact creature until end of turn."
    #
    # THAT IS AN ETB TRIGGER, NOT A STATIC ABILITY, and it fires ONCE. This
    # read `g.has("Cyberdrive Awakener")` and applied the whole pile's worth
    # of power on EVERY combat for the rest of the game, which made it the
    # highest-scoring card in the first Tivit table (+0.0335 win) on an
    # effect the card does not have. `cyberdrive_turn` is the turn it entered.
    #
    # Still approximated, and in the generous direction: tokens created THIS
    # TURN have not been under your control since the turn began, so they are
    # summoning sick and cannot attack. Counting the whole pile overstates the
    # burst by however much of it Tivit made this turn -- which, on the turn
    # you would want to do this, is most of it. Treat the number as a ceiling.
    bonus = 0
    if g.has("Cyberdrive Awakener") and g.turn == getattr(
            g, "cyberdrive_turn", -1):
        bonus = 4 * sum(g.tokens.values())
    dmg = raw + bonus
    if g.cfg.get("derived_blocking", True):
        # One attack at the whole pod. This REPLACES an even `damage_each`
        # spread: dividing the swing equally is a split, but a naive one --
        # it cannot finish anybody, because the player on 3 life and the
        # player on 40 each got a third. `dmg` comes back bounded at what
        # could have mattered.
        dmg = OPP.combat_damage(g, attackers,
                                scale=(raw + bonus) / max(1e-9, raw))
    else:
        # Legacy flat-haircut pod: no per-defender blockers to plan against.
        dmg *= (1.0 - g.cfg.get("block_rate", 0.30))
        dmg = OPP.damage_each(g, dmg / max(1, len(OPP.living(g))))
    g.damage_by_turn.append(dmg)
    g.m["damage"] += dmg
    g.m["combat_damage"] += dmg
    if g.result == "win":
        if g.m["win_route"] == 0:
            g.m["win_route"] = ROUTE_COMBAT
            g.m["turn_lethal"] = g.turn
        return

    # "...OR DEALS COMBAT DAMAGE TO A PLAYER." The second half of the
    # commander's trigger, and the reason Lightning Greaves is in this deck:
    # haste is a whole extra dilemma on the turn Tivit lands.
    if dmg > 0 and any(p.card is g.commander for p in attackers):
        tivit_dilemma(g)


def activations(g):
    """Post-main sinks: the blink loop, Time Sieve, and Clues.

    EPHEMERATE USED TO BE CAST HERE and never was: `main_phase` runs twice
    before this and is greedy on priority, so it always took the card first.
    The cast now lives in `main_phase` like every other spell, gated on Tivit
    actually being on the battlefield, and the effect in `resolve()`. This
    block additionally gated on `commander_cast` rather than on Tivit being
    present, which would have thrown the card away after a wipe.
    """
    deadeye_loop(g)
    if g.result is not None:
        return

    time_sieve(g)
    if g.result is not None:
        return

    walker_step(g)                   # Dyfed / Venser, §0z74
    if g.result is not None:
        return

    crack_clues(g, 3)


def make_powerstones(g, n) -> int:
    """Dyfed's +1: "Create two TAPPED Powerstone tokens." Anointed
    Procession doubles them (the third token path, and it is said here as it
    is in the other two -- §0z4); Academy Manufactor does NOT, because a
    Powerstone is not a Clue, Food or Treasure. Every creation fires
    `on_tokens_created`, so Mirkwood Bats and Kambal see them."""
    if g.has("Anointed Procession"):
        n *= 2
    g.tokens["Powerstone"] += n
    g.powerstones_tapped += n            # they enter tapped
    g.m["powerstones_made"] += n
    g.m["artifacts_made"] += n
    on_tokens_created(g, n)
    return n


def walker_step(g) -> None:
    """Tivit's two walkers (§0z74), once each per turn, at sorcery speed
    in the postcombat main phase -- after Time Sieve has had its tap.

    DYFED, THE GUIDING HAND (loyalty 4). THE POLICY, SAID OUT LOUD:
      -1  untap a Time Sieve that was tapped this turn, when five more
          artifacts can pay for it: a SECOND extra turn. Taken first.
      -6  when loyalty allows and Time Sieve is neither in play nor in hand:
          it goes onto the battlefield (else the best artifact by priority).
      +1  otherwise: two tapped Powerstones.
    Untapping anything but the Sieve (a signet, the artifact lands) is not
    modelled -- a mana ability's worth -- which is a floor.

    VENSER, VISIONARY TRAVELER (loyalty 4): +1 on Tivit whenever Tivit is on
    the battlefield (it returns at end step, a fresh dilemma); +1 with no
    target otherwise. The -2 is BLIND (§4: the pod's permanents are a count)
    and never taken. Blinking another ETB creature when Tivit is absent is
    not modelled -- a floor."""
    for perm in [p for p in g.board if p.card.name == "Dyfed, the Guiding Hand"]:
        if not walker_ready(g, perm):
            continue
        sieve = next((p for p in g.board if p.card.name == "Time Sieve"), None)
        fuel = sum(g.tokens.values()) + len(sieve_real_fuel(g))
        in_hand = any(c.name == "Time Sieve" for c in g.hand)
        if sieve is not None and sieve.tapped and fuel >= 5 \
                and perm.counters >= 1:
            perm.counters -= 1
            sieve.tapped = False
            g.m["dyfed_untaps"] += 1
            walker_dies_at_zero(g, perm)
            time_sieve(g)
            if g.result is not None:
                return
            continue
        if perm.counters >= 6 and sieve is None and not in_hand:
            pool = [c for c in g.library if "Artifact" in c.types
                    and not c.is_land]
            if pool:
                pick = next((c for c in pool if c.name == "Time Sieve"),
                            max(pool, key=lambda c: c.priority))
                g.library.remove(pick)
                crn_shuffle(g, "dyfed_search", g.library)
                perm.counters -= 6
                g.m["dyfed_tutors"] += 1
                q = Permanent(card=pick, sick=not pick.haste)
                enter_loyalty(q)
                g.board.append(q)
                run_etb(g, q)
                walker_dies_at_zero(g, perm)
                continue
        perm.counters += 1
        make_powerstones(g, 2)
        if g.result is not None:
            return
    for perm in [p for p in g.board
                 if p.card.name == "Venser, Visionary Traveler"]:
        if not walker_ready(g, perm):
            continue
        perm.counters += 1
        if g.has("Tivit, Seller of Secrets") and not g.venser_return:
            g.venser_return = True
            g.m["venser_exiles"] += 1


def _sacrifice_five(g) -> bool:
    """Pay Time Sieve's "Sacrifice five artifacts" out of the token piles.

    Clues and Food go before Treasures: a Treasure is mana and the other two
    are not, so spending them first is what a pilot does. REAL artifacts
    make up a shortfall only, and only as `sieve_real_fuel` allows (§0z71):
    until then Sol Ring, the signets and the artifact lands were never fuel,
    the conservative direction item 8c named.
    """
    real = sieve_real_fuel(g)
    if sum(g.tokens.values()) + len(real) < 5:
        return False
    need = 5
    # Powerstones (§0z74) go after Clues and before Treasures: restricted
    # mana is worth less than any-colour mana, more than a Clue's {2} draw.
    # Tapped ones first -- a tapped Powerstone has already made its mana.
    for kind in ("Food", "Clue", "Powerstone", "Treasure"):
        gone = sacrifice_tokens(g, kind, min(need, g.tokens[kind]))
        if kind == "Powerstone":
            g.powerstones_tapped = max(0, g.powerstones_tapped - gone)
        need -= gone
        if need <= 0:
            return True
    # Short of five tokens: real artifacts, only as many as needed (§0z71).
    sacrifice_real_artifacts(g, real[:need])
    return True


def time_sieve(g):
    """Time Sieve: "{T}, Sacrifice five artifacts: Take an extra turn after
    this one."

    THE COST IS A TAP OF TIME SIEVE ITSELF, so the ability is ONCE PER TURN --
    and that is the whole card. This used to run up to `sieve_cap` (10) times in
    a single turn and, on reaching the cap, declare the game won. Neither half
    was right: ten activations a turn is nine more than the card allows, and the
    cap was almost never reachable anyway (it needs fifty tokens in one window),
    so what the card actually did in nearly every game was grant one or two
    extra turns that the engine then threw away or actively punished. See
    `simulate` for the other two halves of the bug.

    Once per turn is not a limitation on the loop -- it IS the loop. Time Sieve
    untaps every turn, including on the extra turn it just bought, so one
    activation per turn chained is unbounded:

        Tivit attacks -> dilemma -> 5 votes -> 5 artifact tokens
        -> sacrifice them to Time Sieve -> extra turn
        -> untap, Tivit attacks again -> repeat

    In a four-player game that is exactly five tokens for exactly five
    artifacts, with nothing to spare, which is why the pair is a two-card
    engine and neither half is anything without the other.

    Artifacts have no summoning sickness, so the {T} is live the turn Time Sieve
    lands; only `tapped` gates it.
    """
    if not g.has("Time Sieve"):
        return
    if not g.cfg.get("sieve_taps", True):
        # Pre-2026-09-06 behaviour, kept so the old tivit table reproduces.
        cap = g.cfg.get("sieve_cap", 10)
        taken = 0
        while taken < cap and _sacrifice_five(g):
            g.extra_turns += 1
            g.m["extra_turns"] += 1
            g.m["sieve_activations"] += 1
            taken += 1
            if g.result is not None:
                return
        if taken >= cap and g.result is None:
            g.win(ROUTE_TIME_SIEVE)
        return

    sieve = next((p for p in g.board
                  if p.card.name == "Time Sieve" and not p.tapped), None)
    if sieve is None:
        return
    if not _sacrifice_five(g):
        return
    sieve.tapped = True
    g.extra_turns += 1
    g.m["extra_turns"] += 1
    g.m["sieve_activations"] += 1


def take_turn(g, extra=False):
    g.turn += 1
    if extra:
        g.m["extra_turns_taken"] += 1
    g.spells_this_turn = 0
    g.illusion_active = False
    for p in g.board:
        p.tapped = False
        p.sick = False
    g.powerstones_tapped = 0            # the Powerstone pile untaps (§0z74)
    g.land_drops = 1
    g.land_drops_used = 0

    upkeep(g)
    if g.result is not None:
        return
    g.draw(1)
    saga_step(g)
    if g.result is not None:
        return
    play_land(g)
    main_phase(g)
    if g.result is not None:
        return
    combat(g)
    main_phase(g)
    if g.result is not None:
        return
    activations(g)
    if g.result is not None:
        return
    end_step(g)
    if g.result is not None:
        return

    g.m["mana_floated"] += len(mana_units(g))
    g.m["stranded_mv"] += sum(c.mv for c in g.hand if not c.is_land)

    # AN EXTRA TURN IS YOUR TURN, NOT A ROUND. This block is the three
    # opponents' whole turn cycle -- they develop a board, cast removal, chip
    # you for incidental damage and check their kill clocks. Running it at the
    # end of an EXTRA turn hands the pod a free extra round for every extra turn
    # you take, which is the opposite of what an extra turn does, and it made
    # every extra-turn card in the deck a liability: Time Sieve, Plea for Power
    # and Expropriate all paid a pod round for each turn they bought.
    #
    # `lorehold.take_turn` already had this right -- its extra turns run
    # untap/miracle/main/combat with no opponent block at all -- so the two
    # engines modelled the same concept in opposite directions.
    #
    # The pre-rolled opponent grid is indexed by `g.turn`, which still advances,
    # so CRN is unaffected: an opponent's clock is DELAYED by the turns you
    # took, not skipped, and it still resolves at most once when the pod next
    # gets a round.
    skip = extra and g.cfg.get("extra_turns_skip_opponents", True)
    if g.cfg.get("opponents", True) and not skip:
        g.m["pod_rounds"] += 1
        # One order for six engines (§0z30): damage, clocks, THEN removal.
        # This engine ran removal first until 2026-09-17.
        OPP.pod_phase(g)


def take_extra_turns(g, played, budget):
    """Spend `g.extra_turns`. Returns the new turn count against the horizon.

    Extra turns are REAL turns and still count against the horizon, so a deck
    cannot buy turns the other three engines do not get. That is a deliberate
    choice, and it is now the ONLY thing bounding the loop.

    THE CHAIN USED TO BE CUT. `g.extra_turns` was zeroed before the loop and
    never re-read, so an extra turn generated DURING an extra turn was silently
    discarded -- and one extra turn per real turn is exactly what Time Sieve
    grants, so the card's whole loop was truncated to a single step every time.
    Combined with the pod round each extra turn used to hand out (see
    `take_turn`), Time Sieve bought one turn and paid a full round of opponents
    for it.

    Chained, Tivit + Time Sieve is unbounded: Tivit's attack trigger is five
    votes in a four-player pod, which is exactly the five artifacts the Sieve
    eats, and the Sieve untaps on the turn it bought. `extra_turn_cap` applies to
    the LEGACY path only; here the horizon is the bound and `played < budget`
    guarantees termination.

    THIS LIVES IN A FUNCTION so `simulate`, `test_time_sieve.py` and
    `diag_time_sieve.py` cannot disagree about it. They each had their own copy
    of the loop for about an hour, and the test's copy silently failed to record
    `sieve_chain_max` -- which is a small version of exactly the bug this
    function exists to fix.
    """
    cfg = g.cfg
    if cfg.get("extra_turns_chain", True):
        chain = 0
        while g.extra_turns > 0 and played < budget and g.result is None:
            g.extra_turns -= 1
            take_turn(g, extra=True)
            played += 1
            chain += 1
    else:
        chain = min(g.extra_turns, cfg.get("extra_turn_cap", 5))
        for _ in range(chain):
            if played >= budget or g.result is not None:
                break
            take_turn(g, extra=True)
            played += 1
    g.extra_turns = 0
    g.m["sieve_chain_max"] = max(g.m["sieve_chain_max"], chain)
    return played


def simulate(deck, commander, cfg, seed):
    g = TivitGame(deck, commander, cfg, seed)
    g.opening_hand()
    # From here the game RNG must never be touched again. §0z17.
    seal_rng(g)
    budget = cfg.get("turns", 20)
    played = 0
    while played < budget and g.result is None:
        take_turn(g)
        played += 1
        if g.result is not None:
            break
        played = take_extra_turns(g, played, budget)

    out = finish(g)
    out["final_treasures"] = g.tokens["Treasure"]
    out["final_artifacts"] = g.artifact_count()
    return out
