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

from edhmc.engine import (Board, Card, Permanent, can_pay, play_land)
from edhmc import opponents as OPP
from edhmc import voting as V

TOKEN_KINDS = ("Treasure", "Clue", "Food")


class TivitGame:
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
        self.extra_turns = 0
        self.illusion_active = False
        self.ephemerate_rebound = 0     # turn on which the rebound copy casts
        self.deadeye_paired = False
        self.cyberdrive_turn = -1       # turn Cyberdrive Awakener entered
        self.result = None
        # Token piles. Ints rather than Permanents: none of them is a creature
        # and nothing in this deck reads an individual one.
        self.tokens = {k: 0 for k in TOKEN_KINDS}
        self.soldier_tokens = 0         # Lieutenants / Vault 11, real bodies

        cfg.setdefault("shroud_sources", ("Lightning Greaves",))
        cfg.setdefault("protection_cards", ())
        self.opponents, self.opp_rolls, self.counter_rolls = OPP.make_pod(cfg, seed)
        OPP.init_life(self)

        self.m = {
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
            "treasures_spent": 0, "clues_cracked": 0,
            "blinks": 0, "deadeye_activations": 0, "combo_iterations": 0,
            "tivit_triggers": 0, "extra_turns": 0,
            "sieve_activations": 0, "sieve_chain_max": 0,
            # `extra_turns` is turns GRANTED; these two are what was actually
            # taken and how many rounds the pod got. The gap between granted and
            # taken is what the discarded-chain bug used to throw away.
            "extra_turns_taken": 0, "pod_rounds": 0,
            # --- routes out ---
            "win_route": 0, "loss_route": 0,
            "token_drain": 0.0, "artifact_drain": 0.0,
        }
        self.damage_by_turn = []

    # -- helpers ------------------------------------------------------------

    def has(self, name):
        return name in self.board.names

    def count(self, name):
        return self.board.names.get(name, 0)

    def power_of(self, perm):
        return perm.card.power + perm.counters

    def toughness_of(self, perm):
        return perm.card.toughness + perm.counters

    def draw(self, n=1):
        for _ in range(int(n)):
            if self.library:
                self.hand.append(self.library.pop())
                self.m["cards_drawn"] += 1

    def artifact_count(self) -> int:
        """Everything Time Sieve, Marionette Master and Disciple of the Vault
        can actually see: token artifacts, artifact permanents, and the three
        ARTIFACT LANDS, which are artifacts as well as lands."""
        n = sum(self.tokens.values())
        for p in self.board:
            if "Artifact" in p.card.types:
                n += 1
        return n

    def make_tokens(self, n, p, t, subtype="", tapped=False):
        """Real creature tokens (Soldiers, Rabbits). NOT the artifact piles."""
        for _ in range(int(n)):
            tok = Card(name=f"{subtype or 'Token'} token",
                       types=frozenset({"Creature"}), power=p, toughness=t)
            self.board.append(Permanent(card=tok, tapped=tapped, sick=True,
                                        is_token=True))
        self.soldier_tokens += int(n)
        on_tokens_created(self, int(n))

    def deal_pod_damage(self, amount, each=True):
        if amount <= 0:
            return
        # BOUNDED: record what could have mattered, not what was asked for.
        n = max(1, len(OPP.living(self)))
        amount = (OPP.damage_each(self, amount / n) if each
                  else OPP.damage_single(self, amount))
        self.m["damage"] += amount
        self.m["drain_damage"] += amount
        if self.damage_by_turn:
            self.damage_by_turn[-1] += amount
        if self.result == "win" and self.m["turn_lethal"] == 99:
            self.m["turn_lethal"] = self.turn

    def on_creature_death(self, n=1, perm=None):
        pass                      # no death payoffs in this list

    def play_card_trigger(self, card):
        pass

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
        dmg = per * n * len(OPP.living(g))
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
    if g.has("Disciple of the Vault"):
        per += 1.0 / max(1, len(OPP.living(g)))   # ONE opponent loses 1
    if per:
        dmg = per * n * len(OPP.living(g))
        g.deal_pod_damage(dmg)
        g.m["token_drain"] += dmg
    if g.has("Marionette Master"):
        # "target opponent loses life equal to this creature's power" -- a
        # single target, and the Master is a 1/3 with fabricate 3 taken as
        # counters, so power 4.
        power = 4.0
        dmg = power * n
        g.deal_pod_damage(dmg, each=False)
        g.m["artifact_drain"] += dmg
    if g.result == "win":
        g.m["win_route"] = ROUTE_DRAIN
    return n


# ---------------------------------------------------------------------------
# Mana
# ---------------------------------------------------------------------------

def mana_units(g) -> list[frozenset]:
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
    units.extend([any_col] * g.tokens["Treasure"])
    return units


def pay(g, cost) -> bool:
    """Spend `cost` if affordable. Treasures are consumed last and their
    sacrifice fires the artifact-leaves payoffs."""
    units = mana_units(g)
    idx = can_pay(cost, units)
    if idx is None:
        return False
    n_units = len(units)
    n_treasure = g.tokens["Treasure"]
    first_treasure = n_units - n_treasure
    used_treasures = sum(1 for i in idx if i >= first_treasure)

    # tap the real sources
    real = sorted(i for i in idx if i < first_treasure)
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


def affordable(g, cost) -> bool:
    return can_pay(cost, mana_units(g)) is not None


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
    tivit_dilemma(g)
    return True


def crack_clues(g, want=1) -> int:
    """"{2}, Sacrifice this artifact: Draw a card." Cracked only with spare
    mana, and the sacrifice is itself a payoff via Nadier's / Mirkwood /
    Marionette."""
    drawn = 0
    for _ in range(int(want)):
        if g.tokens["Clue"] <= 0 or not affordable(g, {"gen": 2}):
            break
        if not pay(g, {"gen": 2}):
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
    while n < cap and affordable(g, {"gen": 1, "U": 1}):
        before = g.tokens["Treasure"]
        if not pay(g, {"gen": 1, "U": 1}):
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
                g.commander_cast = True
                g.m["spells_cast"] += 1
                tivit_dilemma(g)               # the ETB half
                if g.result is not None:
                    return
                continue

        options = []
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
            if affordable(g, reduce_cost(g, c)):
                options.append(c)
        if not options:
            return
        card = max(options, key=lambda c: (c.priority, c.mv))
        if not pay(g, reduce_cost(g, card)):
            return
        g.hand.remove(card)
        idx = g.spells_this_turn
        g.spells_this_turn += 1
        if OPP.countered(g, card, idx):
            g.m["countered"] += 1
            g.graveyard.append(card)
            continue
        g.m["spells_cast"] += 1
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
            g.deal_pod_damage(4.0 * len(OPP.living(g)))
    elif s == "capital_punishment":
        # Sacrifice and discard are both unmodelled against this opponent
        # model; only the vote payoffs (Grudge Keeper) actually land.
        V.dilemma(g, "capital")
    elif s in ("bite", "split_decision", "trial", "councils_judgment",
               "magister"):
        V.council(g)
    elif s == "tempt_bunnies":
        n = V.tempting_offer(g)
        g.draw(n)
        g.make_tokens(n, 1, 1, "Rabbit")
    elif s == "vault11":
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
        g.deal_pod_damage(3.0 * x * len(OPP.living(g)))
        if g.result == "win":
            g.m["win_route"] = ROUTE_TORMENT

    if card.is_permanent:
        perm = Permanent(card=card, sick=not card.haste)
        g.board.append(perm)
        run_etb(g, perm)
    elif not card.is_land:
        g.graveyard.append(card)


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
        pick = [g.rng.randrange(3) for _ in range(n)]
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

    crack_clues(g, 3)


def _sacrifice_five(g) -> bool:
    """Pay Time Sieve's "Sacrifice five artifacts" out of the token piles.

    Clues and Food go before Treasures: a Treasure is mana and the other two
    are not, so spending them first is what a pilot does. Only TOKENS are
    eaten, never the real artifacts `artifact_count()` can see -- Sol Ring, the
    signets and the three artifact lands are legal fuel and a pilot would not
    feed them to a loop that has to run again next turn. That is the
    conservative direction and is said out loud rather than fixed.
    """
    if sum(g.tokens.values()) < 5:
        return False
    need = 5
    for kind in ("Food", "Clue", "Treasure"):
        need -= sacrifice_tokens(g, kind, min(need, g.tokens[kind]))
        if need <= 0:
            return True
    return need <= 0


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
        watch = g.cfg.get("watch", ())
        before = {p.card.name for p in g.board if p.card.name in watch}
        OPP.opponents_act(g)
        after = {p.card.name for p in g.board if p.card.name in watch}
        for _ in before - after:
            g.m["test_card_answered"] += 1
            g.m["test_card_removed"] += 1
        OPP.incidental_damage(g)
        OPP.resolve_clocks(g)


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
    budget = cfg.get("turns", 20)
    played = 0
    while played < budget and g.result is None:
        take_turn(g)
        played += 1
        if g.result is not None:
            break
        played = take_extra_turns(g, played, budget)

    out = dict(g.m)
    out["damage_by_turn"] = g.damage_by_turn
    out["result"] = g.result or "timeout"
    out["turns_played"] = g.turn
    out["won"] = 1 if g.result == "win" else 0
    out["lost"] = 1 if g.result == "loss" else 0
    out["final_life"] = g.your_life
    out["opponents_killed"] = sum(1 for o in g.opponents if not o.alive)
    out["final_board_power"] = sum(g.power_of(p) for p in g.board
                                   if p.card.is_creature)
    out["final_treasures"] = g.tokens["Treasure"]
    out["final_artifacts"] = g.artifact_count()
    out["test_card_resolved"] = 1 if (out["cast_test_card"] and
                                      not out["test_card_answered"]) else 0
    return out
