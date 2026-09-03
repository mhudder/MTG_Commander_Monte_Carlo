"""
edhmc.opponents — a three-opponent interaction model.

Replaces the previous flat `block_rate` haircut with modelled opponents who
hold removal, counterspells, and board wipes, and who block.

DESIGN NOTE ON RANDOMNESS
-------------------------
Opponent decisions must not break common random numbers. If the opponents drew
from the game RNG, deck A and deck B would consume a different number of
draws as soon as their boards diverged, and every subsequent roll would
decorrelate — destroying the variance reduction that makes a one-card swap
measurable at all.

So opponents get their own RNG stream, seeded identically for A and B, and the
entire game's worth of rolls is pre-generated into a fixed grid at setup. Slot
(turn, opponent, k) holds the same number in both branches no matter how the
boards differ. The opponents therefore "draw the same hands" in A and B, and
only *respond* differently.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Per-opponent, per-turn probabilities, once that opponent has mana (turn >= 3).
# Calibration target for a mixed pod over turns 3-10: roughly 4 spot removal
# spells and ~1 board wipe reaching the table per game, which is what a
# 10-turn game of mixed-bracket Commander tends to produce.
# `clock` is the turn range in which this opponent threatens to eliminate a
# player. Calibrated from bracket descriptions and then corrected against the
# pod actually being played: the top seat here behaves like a 3.5, not a true
# bracket 4, so its clock is 8-12 rather than 7-10.
BRACKETS = {
    2: dict(spot=0.10, ae=0.030, wipe=0.015, blue=0.40, counter=0.06,
            counters_held=1, board=0.8, clock=(13, 18)),
    3: dict(spot=0.16, ae=0.060, wipe=0.025, blue=0.50, counter=0.13,
            counters_held=1, board=1.0, clock=(10, 14)),
    4: dict(spot=0.24, ae=0.100, wipe=0.040, blue=0.60, counter=0.22,
            counters_held=2, board=1.2, clock=(8, 12)),
}

N_SLOTS = 8          # random slots per opponent per turn
N_COUNTER_SLOTS = 10  # spells we might cast in one turn


@dataclass
class Opponent:
    bracket: int
    has_blue: bool
    creatures: float = 0.0
    counters_left: int = 0
    life: float = 40.0
    kill_turn: int = 99
    alive: bool = True
    clock_fired: bool = False

    @property
    def p(self) -> dict:
        return BRACKETS[self.bracket]


def make_pod(cfg: dict, seed: int) -> tuple[list[Opponent], list, list]:
    """Build the pod and pre-roll every random number it will ever need."""
    r = random.Random(seed ^ 0x5EED)          # dedicated stream
    brackets = cfg.get("pod_brackets", (2, 3, 4))
    opps = []
    for b in brackets:
        blue = r.random() < BRACKETS[b]["blue"]
        lo, hi = BRACKETS[b]["clock"]
        opps.append(Opponent(
            bracket=b, has_blue=blue,
            counters_left=BRACKETS[b]["counters_held"] if blue else 0,
            life=float(cfg.get("starting_life", 40)),
            # drawn from the dedicated pre-rolled stream so decks A and B face
            # identical opponents no matter how their own boards diverge
            kill_turn=r.randint(lo, hi)))

    turns = cfg.get("turns", 10) + 2
    rolls = [[[r.random() for _ in range(N_SLOTS)] for _ in opps]
             for _ in range(turns)]
    counter_rolls = [[[r.random() for _ in opps] for _ in range(N_COUNTER_SLOTS)]
                     for _ in range(turns)]
    return opps, rolls, counter_rolls


# ---------------------------------------------------------------------------
# Threat assessment
# ---------------------------------------------------------------------------

def threat_of(g, perm) -> float:
    """How badly an opponent wants this specific permanent gone."""
    c = perm.card
    if c.threat:
        base = float(c.threat)
    elif c.is_creature:
        base = g.power_of(perm) * 0.8
    else:
        base = c.mv * 0.5
    if perm.is_token:
        base *= 0.15          # nobody spends a card on a 2/2 Bird token
    return base


def board_threat(g) -> float:
    """Your total threat level, as the table perceives it."""
    power = sum(g.power_of(p) for p in g.board if p.card.is_creature)
    engines = sum(threat_of(g, p) for p in g.board if not p.is_token
                  and not p.card.is_land)
    return power + engines


def opponent_threat(opp: Opponent, turn: int) -> float:
    """A generic opponent's perceived threat level, for target selection."""
    return 4.0 * turn * opp.p["board"]


def your_share(g, opp: Opponent, others: list[Opponent]) -> float:
    """P(this opponent's removal points at you rather than a rival).

    Threat-weighted: the more board you have relative to the rest of the table,
    the more of the pod's interaction you eat. This is the mechanism by which
    a card that makes your board scarier also makes it a bigger target.
    """
    mine = board_threat(g)
    theirs = sum(opponent_threat(o, g.turn) for o in others)
    if mine + theirs <= 0:
        return 0.0
    return mine / (mine + theirs)


# ---------------------------------------------------------------------------
# Protection
# ---------------------------------------------------------------------------

def commander_shrouded(g) -> bool:
    """Equipment/abilities that make the commander an illegal target.

    Lightning Greaves and Mother of Runes do not blank a removal spell once —
    they take the commander off the table as a target for as long as they are
    around. Without this, a five-mana commander in a deck built to protect it
    gets destroyed on repeat and the whole engine never runs.
    """
    return any(g.has(n) for n in g.cfg.get("shroud_sources", ()))


def try_protect(g, roll: float) -> bool:
    """A protection spell held up from hand to blank one event."""
    names = g.cfg.get("protection_cards", ("Heroic Intervention",))
    hi = next((c for c in g.hand if c.name in names), None)
    if hi is None:
        return False
    lands = sum(1 for p in g.board if p.card.is_land)
    if lands < 4:
        return False                      # not enough mana to hold it up
    if roll >= g.cfg.get("hold_up_rate", 0.60):
        return False                      # you tapped out instead
    g.hand.remove(hi)
    g.graveyard.append(hi)
    g.m["protected"] += 1
    return True


# ---------------------------------------------------------------------------
# Interaction events
# ---------------------------------------------------------------------------

def spot_removal(g, opp, others, rolls):
    if rolls[0] >= opp.p["spot"]:
        return
    if rolls[3] >= your_share(g, opp, others):
        return                            # aimed at a rival instead
    targets = [p for p in g.board
               if not p.card.is_land and not p.is_token]
    if commander_shrouded(g):
        targets = [p for p in targets if p.card is not g.commander]
    if not targets:
        return
    if try_protect(g, rolls[5]):
        return
    victim = max(targets, key=lambda p: threat_of(g, p))
    destroy(g, victim)
    g.m["removal_eaten"] += 1


def ae_removal(g, opp, others, rolls):
    """Naturalize / Vandalblast effects, plus the occasional sweeper."""
    if rolls[1] >= opp.p["ae"]:
        return
    if rolls[3] >= your_share(g, opp, others):
        return
    targets = [p for p in g.board
               if ("Artifact" in p.card.types or "Enchantment" in p.card.types)
               and not p.card.is_land and not p.is_token]
    if not targets:
        return
    if try_protect(g, rolls[5]):
        return
    sweeper = (opp.bracket >= 3 and rolls[4] < 0.20)
    if sweeper:
        for p in list(targets):
            destroy(g, p)
        g.m["ae_removal_eaten"] += len(targets)
    else:
        victim = max(targets, key=lambda p: threat_of(g, p))
        destroy(g, victim)
        g.m["ae_removal_eaten"] += 1


def board_wipe(g, opp, rolls):
    """Wraths scale with how wide the table's biggest board has gotten."""
    if g.turn < g.cfg.get("first_wipe_turn", 5):
        return
    n = sum(1 for p in g.board if p.card.is_creature)
    width_mult = 1.0 + min(0.75, max(0, n - 4) * 0.08)
    if rolls[2] >= opp.p["wipe"] * width_mult:
        return
    if try_protect(g, rolls[5]):
        return
    for p in [p for p in g.board if p.card.is_creature]:
        destroy(g, p)
    for o in g.opponents:
        o.creatures = 0.0
    g.m["wipes_suffered"] += 1


def destroy(g, perm):
    if perm not in g.board:
        return
    g.board.remove(perm)
    if perm.card.is_creature and hasattr(g, "on_creature_death"):
        g.on_creature_death(1)
    if perm.card is g.commander:
        g.commander_cast = False          # back to the command zone
        g.commander_tax += 2
    elif not perm.is_token:
        g.graveyard.append(perm.card)


def opponents_act(g):
    """One full round of the three opponents' turns."""
    rolls_t = g.opp_rolls[min(g.turn, len(g.opp_rolls) - 1)]
    for i, opp in enumerate(g.opponents):
        opp.creatures = min(7.0, opp.creatures + 0.7 * opp.p["board"])
        if g.turn < 3:
            continue
        others = [o for j, o in enumerate(g.opponents) if j != i]
        r = rolls_t[i]
        board_wipe(g, opp, r)
        spot_removal(g, opp, others, r)
        ae_removal(g, opp, others, r)


# ---------------------------------------------------------------------------
# Counterspells
# ---------------------------------------------------------------------------

def countered(g, card, spell_index: int) -> bool:
    """Checked as the spell goes on the stack.

    Weighted by the spell's threat and by how many blue opponents are sitting
    behind untapped mana. A turn-8 six-drop is a very different proposition
    from a turn-2 one-drop, which is most of why this matters here.
    """
    if g.turn < 3 or spell_index >= N_COUNTER_SLOTS:
        return False
    threat = float(card.threat) if card.threat else max(card.power * 0.8, card.mv * 0.5)
    if threat < g.cfg.get("counter_threshold", 4.0):
        return False

    rolls = g.counter_rolls[min(g.turn, len(g.counter_rolls) - 1)][spell_index]
    mana_gate = min(1.0, (g.turn - 2) / 4.0)
    for i, opp in enumerate(g.opponents):
        if opp.counters_left <= 0:
            continue
        p = opp.p["counter"] * mana_gate * min(1.0, threat / 9.0)
        if rolls[i] < p:
            opp.counters_left -= 1      # counterspells are a finite resource
            return True
    return False


# ---------------------------------------------------------------------------
# Blocking
# ---------------------------------------------------------------------------

def damage_through(g, attackers: list) -> float:
    """Opponents chump-block your biggest attackers first.

    This replaces the old flat 30% haircut and is not neutral between the two
    cards under test: a small number of very large creatures loses far more to
    chump blocks than a wide board of small ones does, because a 1/1 blocking a
    6/6 eats six damage while a 1/1 blocking a 2/2 eats two.
    """
    if not attackers:
        return 0.0
    # In a four-player game you send the swarm at whoever is least able to
    # stop it, so the relevant blocker count is the *weakest* opponent's board,
    # not the table's total. Some of their creatures are also tapped from
    # attacking someone else.
    weakest = min(o.creatures for o in g.opponents)
    n_block = int(weakest * g.cfg.get("block_share", 0.60))

    powers = sorted((g.power_of(p) for p in attackers), reverse=True)
    if g.has("Ohran Frostfang"):
        # deathtouch attackers make blocking miserable; fewer opponents do it
        n_block = int(n_block * 0.5)
    return float(sum(powers[n_block:]))



# ---------------------------------------------------------------------------
# Life totals and the four-player race
# ---------------------------------------------------------------------------

def init_life(g):
    g.your_life = float(g.cfg.get("starting_life", 40))
    g.result = None            # "win" | "loss" | None (game still running)


def living(g):
    return [o for o in g.opponents if o.alive and o.life > 0]


def damage_each(g, n):
    """'Each opponent loses N' effects."""
    if n <= 0:
        return
    for o in living(g):
        o.life -= n
    _check_eliminations(g)


def damage_single(g, n):
    """Focused damage - combat, or a single-target burn spell. Goes at the
    opponent closest to dying, which is what a real pilot does."""
    if n <= 0:
        return
    alive = living(g)
    if not alive:
        return
    min(alive, key=lambda o: o.life).life -= n
    _check_eliminations(g)


def _check_eliminations(g):
    for o in g.opponents:
        if o.alive and o.life <= 0:
            o.alive = False
            o.creatures = 0.0
    if not living(g) and g.result is None:
        g.result = "win"


def incidental_damage(g):
    """Opponents chip away at you every turn, not just when a clock resolves.

    Without this your life total only ever goes up, which silently inflates
    anything that keys off a high life total — Felidar Sovereign, Aetherflux
    Reservoir, Serra Ascendant — and removes any cost from paying life. The
    share aimed at you is threat-weighted, same as removal and the clocks.
    """
    if g.result is not None or g.turn < g.cfg.get("first_attack_turn", 3):
        return
    rate = g.cfg.get("incidental_rate", 0.45)
    for i, opp in enumerate(g.opponents):
        if not opp.alive:
            continue
        others = [o for j, o in enumerate(g.opponents) if j != i and o.alive]
        share = your_share(g, opp, others)
        g.your_life -= opp.creatures * rate * share
    if g.your_life <= 0 and g.result is None:
        g.result = "loss"


def resolve_clocks(g):
    """Each opponent's own clock. When it comes due, that opponent eliminates
    somebody - and who it is, is THREAT-WEIGHTED. Being the strongest board at
    the table is what draws the kill, which is the same logic already governing
    removal, and it means being ahead carries a real cost."""
    if g.result is not None:
        return
    rolls_t = g.opp_rolls[min(g.turn, len(g.opp_rolls) - 1)]
    for i, opp in enumerate(g.opponents):
        if (not opp.alive or opp.clock_fired or g.turn < opp.kill_turn
                or g.result is not None):
            continue
        opp.clock_fired = True      # a clock resolves once, not every turn
        others = [o for j, o in enumerate(g.opponents) if j != i and o.alive]
        share = your_share(g, opp, others)
        if rolls_t[i][6] < share:
            g.result = "loss"          # you were the biggest threat
            g.your_life = 0.0
            return
        if others:
            victim = max(others, key=lambda o: opponent_threat(o, g.turn))
            victim.alive = False
            victim.life = 0.0
            victim.creatures = 0.0
            # An opponent who just eliminated somebody has not stopped being a
            # problem. Re-arm their clock so surviving one resolution does not
            # make you safe for the rest of the game.
            opp.clock_fired = False
            opp.kill_turn = g.turn + g.cfg.get("clock_rearm", 4)
    _check_eliminations(g)



def should_cast_own_wipe(g) -> bool:
    """Would a real pilot fire their own sweeper right now?

    A wrath is a catch-up card. You cast it when you are behind on board, not
    when you are ahead — and a greedy "cast the biggest thing you can afford"
    policy will happily nuke its own winning position. So gate it on the board
    state: only sweep when the table's creature count meaningfully exceeds
    yours.
    """
    mine = sum(1 for p in g.board if p.card.is_creature)
    theirs = sum(o.creatures for o in living(g))
    return theirs > mine * g.cfg.get("wipe_threshold", 1.4) + 1


def resolve_own_wipe(g, spare_own=False):
    """Your sweeper resolves. It kills THEIR board and, unless it is one-sided,
    yours too — which the engine previously ignored entirely."""
    for o in living(g):
        o.creatures = 0.0
    if spare_own:
        return
    for p in [p for p in g.board if p.card.is_creature]:
        g.board.remove(p)
        if hasattr(g, "on_creature_death"):
            g.on_creature_death(1)
    g.m["own_wipes_cast"] = g.m.get("own_wipes_cast", 0) + 1
