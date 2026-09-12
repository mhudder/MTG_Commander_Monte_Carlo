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

import bisect
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

# ---------------------------------------------------------------------------
# Archetypes (2026-09-04) — heterogeneity, NOT a recalibration
# ---------------------------------------------------------------------------
# A bracket says how POWERFUL an opponent is. It says nothing about what KIND
# of deck they are, and that is what decides whether your life total is under
# pressure. Three bracket-3 control decks and three bracket-3 aggro decks are
# the same pod to the old model and completely different games to play.
#
# THE DISCIPLINE HERE. Every multiplier below is normalised so its WEIGHTED
# MEAN across archetypes is exactly 1 (and the clock offset exactly 0). The
# average pod is therefore identical to the no-archetype pod BY CONSTRUCTION,
# and anything that moves in the results is variance between pods rather than
# the pod quietly getting harder or easier. That matters: it means archetypes
# can be adopted without silently re-baselining the calibration the rest of the
# project rests on.
#
# The raw numbers are judgement, not measurement — no survey data on the EDH
# archetype mix was found. They are knobs: cfg["archetype_weights"] overrides
# the mix. What is NOT a judgement call is the normalisation, which is what
# keeps them honest.
ARCHETYPE_WEIGHTS = {"aggro": 0.25, "midrange": 0.40, "control": 0.25,
                     "combo": 0.10}

_ARCHETYPES_RAW = {
    # board  = creature development rate       power = damage per creature
    # spot/ae/wipe/counter = interaction density    clock = turns of offset
    "aggro":    dict(board=1.45, power=1.35, spot=0.65, ae=0.60, wipe=0.40,
                     counter=0.35, clock=+1.0),
    "midrange": dict(board=1.00, power=1.00, spot=1.00, ae=1.00, wipe=1.00,
                     counter=1.00, clock=0.0),
    "control":  dict(board=0.55, power=0.80, spot=1.55, ae=1.60, wipe=1.90,
                     counter=1.90, clock=+3.0),
    "combo":    dict(board=0.45, power=0.70, spot=0.75, ae=0.80, wipe=0.70,
                     counter=1.30, clock=-3.0),
}


def _normalise(raw, weights):
    """Scale each multiplier so its weighted mean is exactly 1 (clock: 0)."""
    out = {a: dict(v) for a, v in raw.items()}
    for k in next(iter(raw.values())):
        mean = sum(weights[a] * raw[a][k] for a in raw)
        for a in out:
            if k == "clock":
                out[a][k] = raw[a][k] - mean
            else:
                out[a][k] = raw[a][k] / mean if mean else 1.0
    return out


ARCHETYPES = _normalise(_ARCHETYPES_RAW, ARCHETYPE_WEIGHTS)


def pick_archetype(roll: float, weights=None) -> str:
    """Choose an archetype from a single pre-rolled uniform, so CRN survives."""
    w = weights or ARCHETYPE_WEIGHTS
    acc = 0.0
    for name, weight in w.items():
        acc += weight
        if roll < acc:
            return name
    return list(w)[-1]


N_SLOTS = 8          # random slots per opponent per turn
N_COUNTER_SLOTS = 10  # spells we might cast in one turn


@dataclass
class Opponent:
    bracket: int
    has_blue: bool
    # None = archetypes disabled, and then `p` is the bare bracket dict, byte
    # for byte what it was before this existed.
    archetype: object = None
    creatures: float = 0.0
    counters_left: int = 0
    life: float = 40.0
    kill_turn: int = 99
    alive: bool = True
    clock_fired: bool = False
    # Rendmaw gives EVERY player a goaded 2/2 flying Bird on each trigger.
    # Kept separate from `creatures` so the natural-board cap in
    # opponents_act() cannot silently clip them away.
    goaded_birds: float = 0.0

    _pcache: object = None

    @property
    def p(self) -> dict:
        """Bracket crossed with archetype. Memoised — this is a hot path."""
        if self._pcache is None:
            base = BRACKETS[self.bracket]
            if self.archetype is None:
                self._pcache = dict(base, power=1.0)
            else:
                mult = ARCHETYPES[self.archetype]
                d = dict(base)
                for k in ("spot", "ae", "wipe", "counter", "board"):
                    d[k] = base[k] * mult[k]
                d["power"] = mult["power"]
                self._pcache = d
        return self._pcache


def make_pod(cfg: dict, seed: int) -> tuple[list[Opponent], list, list]:
    """Build the pod and pre-roll every random number it will ever need."""
    r = random.Random(seed ^ 0x5EED)          # dedicated stream
    brackets = cfg.get("pod_brackets", (2, 3, 4))
    # `clock_shift` pushes every opponent's kill turn later. The clock is a
    # deus ex machina — it eliminates a player regardless of the board — so it
    # is the thing you give back when you make combat carry real damage.
    # Raising incidental_rate WITHOUT this just stacks a second kill mechanism
    # on top of the first and craters every deck's win rate.
    shift = cfg.get("clock_shift", 0)
    # Only consume randomness when archetypes are ON, so the disabled path
    # draws the identical stream it always did and old numbers reproduce.
    use_arch = cfg.get("archetypes", False)
    arch_weights = cfg.get("archetype_weights") or ARCHETYPE_WEIGHTS
    opps = []
    for b in brackets:
        blue = r.random() < BRACKETS[b]["blue"]
        arch = pick_archetype(r.random(), arch_weights) if use_arch else None
        lo, hi = BRACKETS[b]["clock"]
        off = int(round(ARCHETYPES[arch]["clock"])) if arch else 0
        lo, hi = lo + shift + off, hi + shift + off
        opps.append(Opponent(
            bracket=b, has_blue=blue, archetype=arch,
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

def is_creature_now(g, perm) -> bool:
    """Is this permanent a creature ON THE BATTLEFIELD right now?

    `opponents.py` asked `perm.card.is_creature` — the TYPE LINE AS PLAYED —
    at every site below, and `engine.is_battlefield_creature` exists precisely
    because those are not the same question. Three cards in the rendmaw list
    are creature cards that are not creatures on the battlefield, and rendmaw
    also holds the two sweepers, so every one of them was live:

        Grist, the Hunger Tide      "As long as Grist ISN'T ON THE BATTLEFIELD,
                                    it's a 1/1 Insect creature" — a bare
                                    Planeswalker once it lands, and it was
                                    dying to every Wrath in the game.
        Overlord of the Hauntwoods  deployed for its Impending cost, it "isn't
                                    a creature until the last time counter is
                                    removed" — and it was being wrathed during
                                    the four turns it is an enchantment.
        Erebos, Bleak-Hearted       not a creature below devotion 5.

    The engine's combat step has always used `is_battlefield_creature` for its
    attacker filter. `opponents.py` never adopted it, so a permanent could be
    too-not-a-creature to attack and creature enough to die to a board wipe.

    IT NARROWS AND NEVER BROADENS, deliberately. The `card.is_creature` guard
    comes first, so this can only ever REMOVE a permanent from a victim list —
    it cannot add one. That matters for azusa, whose module docstring states as
    a deliberate fact that `spot_removal` and `board_wipe` "both exclude lands,
    so nothing the pod does can kill an animated land". An animated land really
    is a creature and really should die to a Wrath, and `azusa.counts_as_creature`
    already knows it — but that is the BROADENING half of the same question,
    it is inert today (all three of azusa's animation cards were cut on
    2026-09-10, §0y), and folding it in here would silently reverse a
    documented decision. Left open on purpose, said out loud.

    `pod_reads_battlefield_creatures=False` restores the type-line reading and
    is what any table published before this reproduces with. It is a NEW knob
    rather than a reuse of `battlefield_creature_types`, which was tempting and
    wrong: that one gates the NEVER *stamp* applied at ETB, and it does not
    gate the `impending` clause or the devotion clause at all — so flipping it
    would have restored some of the old behaviour and not the rest, which is
    worse than no switch. One correction, one knob.

    The import is deferred because `engine` imports this module, not the other
    way round. It is a `sys.modules` lookup after the first call, and this is
    not one of the hot paths — `has()` is.
    """
    if not perm.card.is_creature:
        return False
    if not g.cfg.get("pod_reads_battlefield_creatures", True):
        return True                      # the pre-fix reading: the type line
    from edhmc.engine import is_battlefield_creature
    return is_battlefield_creature(g, perm)


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
    power = sum(g.power_of(p) for p in g.board if is_creature_now(g, p))
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
    if destroy(g, victim, rolls[7]):
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
            if destroy(g, p, rolls[7]):
                g.m["ae_removal_eaten"] += 1
    else:
        victim = max(targets, key=lambda p: threat_of(g, p))
        if destroy(g, victim, rolls[7]):
            g.m["ae_removal_eaten"] += 1


def board_wipe(g, opp, rolls):
    """Wraths scale with how wide the table's biggest board has gotten."""
    if g.turn < g.cfg.get("first_wipe_turn", 5):
        return
    n = sum(1 for p in g.board if is_creature_now(g, p))
    width_mult = 1.0 + min(0.75, max(0, n - 4) * 0.08)
    if rolls[2] >= opp.p["wipe"] * width_mult:
        return
    if try_protect(g, rolls[5]):
        return
    for p in [p for p in g.board if is_creature_now(g, p)]:
        destroy(g, p, rolls[7])
    for o in g.opponents:
        o.creatures = 0.0
        o.goaded_birds = 0.0          # a wrath kills the Birds too
    g.m["wipes_suffered"] += 1


# Cards that grant indestructible to OTHER permanents you control, for as
# long as they are on the battlefield -- not a static per-card tag (that would
# say the GRANTED permanent is always indestructible, which tag_flying.py's
# generated set deliberately refuses to claim) and not "until end of turn"
# either, so it does not fit `try_protect`'s one-shot shape. Checked by name
# here, the same way `flying_of` special-cases three conditional fliers.
GRANTS_INDESTRUCTIBLE = {"Avacyn, Angel of Hope"}


# YOUR OWN SWEEPERS, classified by whether INDESTRUCTIBLE stops them. Each
# entry quotes the clause that decides it -- not a judgement call, and not
# guessed: every line below was read from `api.scryfall.com` on 2026-09-11.
#
# The opponents' interaction is a generic "answer" and is priced statistically
# by `destroy_share`, because the model does not know whether a given opponent
# held a Doom Blade or a Swords. YOUR OWN wipe is a named card whose text is
# right there, so pricing it by the same coin flip would be modelling as
# unknown something the deck list states.
#
# CHECKED, not merely asserted -- see check_wipe_coverage(). A `wipe`-tagged
# card in a deck that is in neither set raises, because the failure mode is a
# card silently taking the wrong branch. §0q.
WIPE_IGNORES_INDESTRUCTIBLE = {
    "Toxic Deluge":
        "All creatures get -X/-X until end of turn.",
    "Farewell":
        "Choose one or more - Exile all artifacts. - Exile all creatures. ...",
    "Promise of Loyalty":
        "Each player puts a vow counter on a creature they control and "
        "SACRIFICES the rest.",
    "Massacre Wurm":
        "creatures your opponents control get -2/-2 until end of turn.",
}

WIPE_DESTROYS = {
    "Damn": "Overload {2}{W}{W} ... Destroy target creature -> each creature.",
    "Damnation": "Destroy all creatures. They can't be regenerated.",
    "Wrath of God": "Destroy all creatures. They can't be regenerated.",
    "Austere Command": "Choose two - ... Destroy all creatures with mana value "
                       "3 or less. - Destroy all creatures with mana value 4 "
                       "or greater.",
    "Ultima": "Destroy all artifacts and creatures. End the turn.",
    "Ondu Inversion": "Destroy all nonland permanents.",
    "Culling Ritual": "Destroy each nonland permanent with mana value 2 or "
                      "less.",
    # DAMAGE, not destruction -- and indestructible survives damage just as it
    # survives "destroy", so this belongs on this side of the split. It is the
    # one entry here whose clause does not contain the word.
    "Blasphemous Act": "Blasphemous Act deals 13 damage to each creature.",
    "Sadistic Shell Game": "each player chooses a creature you don't control. "
                           "DESTROY the chosen creatures.",
    "Magister of Worth": "If condemnation gets more votes or the vote is tied, "
                         "DESTROY all creatures other than this creature.",
    "Coercive Portal": "If carnage gets more votes, sacrifice this artifact "
                       "and DESTROY all nonland permanents.",
}


def check_wipe_coverage(decks):
    """Every `wipe`-tagged card must be classified ON PURPOSE.

    `decks` is {name: [Card, ...]}. The two sets above decide which branch a
    sweeper takes in `resolve_own_wipe`, and a card in neither would silently
    take the destroys-branch and be wrong for exactly the cards that most need
    it right -- an exile or a -X/-X wipe that the model lets an indestructible
    creature walk away from.

    This is the §0q rule applied in the same change that introduces the set:
    a hand-maintained name set is a claim, so it gets a check, and the check is
    proved to fail (see tests/test_own_wipe.py --mutate).

    A name in a set that is in no deck is stale rather than dangerous, so it
    is reported and not raised on -- `Coercive Portal` is not `wipe`-tagged at
    all (it is a permanent with a script that calls `resolve_own_wipe`), so it
    is expected to show up there.
    """
    tagged = {c.name for deck in decks.values() for c in deck
              if "wipe" in c.tags}
    both = WIPE_IGNORES_INDESTRUCTIBLE.keys() & WIPE_DESTROYS.keys()
    if both:
        raise SystemExit(
            f"\n{len(both)} sweeper(s) are in BOTH wipe sets, so which branch "
            f"they take depends on lookup order:\n"
            + "".join(f"    {n}\n" for n in sorted(both))
            + "A sweeper either gets around indestructible or it does not.")
    unclassified = tagged - WIPE_IGNORES_INDESTRUCTIBLE.keys() - WIPE_DESTROYS.keys()
    if unclassified:
        raise SystemExit(
            f"\n{len(unclassified)} `wipe`-tagged card(s) are in neither "
            f"WIPE_IGNORES_INDESTRUCTIBLE nor WIPE_DESTROYS:\n"
            + "".join(f"    {n}\n" for n in sorted(unclassified))
            + "Read the oracle text and add it to one, WITH THE CLAUSE. A "
              "destroy effect is stopped by indestructible; exile, sacrifice "
              "and -X/-X are not, and damage IS. Do not guess -- "
              "api.scryfall.com is the source of truth.")
    no_clause = [n for n, why in
                 list(WIPE_IGNORES_INDESTRUCTIBLE.items()) + list(WIPE_DESTROYS.items())
                 if not (why or "").strip()]
    if no_clause:
        raise SystemExit(
            f"\n{len(no_clause)} sweeper(s) are classified with no clause:\n"
            + "".join(f"    {n}\n" for n in sorted(no_clause))
            + "The quoted clause IS the evidence. Without it the entry is an "
              "assertion that the next reader cannot check.")
    stale = ((WIPE_IGNORES_INDESTRUCTIBLE.keys() | WIPE_DESTROYS.keys())
             - tagged - {"Coercive Portal"})
    return sorted(stale)


def wipe_destroys(card) -> bool:
    """Does this sweeper destroy, in the sense indestructible cares about?

    None/unknown defaults to True -- a destroy effect -- because that is what
    the overwhelming majority of sweepers are and it is the conservative branch
    (it lets something survive rather than killing something it should not).
    `check_wipe_coverage` is what stops that default from being reached by a
    real card.
    """
    if card is None:
        return True
    return card.name not in WIPE_IGNORES_INDESTRUCTIBLE


def destroy(g, perm, roll=None, destroys=None):
    """Remove a permanent the pod answered.

    `roll` is one of that opponent's pre-rolled numbers, supplied only so that
    INDESTRUCTIBLE can mean something. The opponent model does not distinguish
    a Swords to Plowshares from a Doom Blade — everything is a generic "answer"
    — so indestructible is priced statistically: `destroy_share` is the fraction
    of an EDH pod's interaction that is literally "destroy target permanent"
    (Doom Blade, Naturalize, most wraths) as opposed to exile, bounce, -X/-X or
    an edict, which an indestructible permanent does not survive.

    0.60 is an assumption, not a measurement. It is a knob, and a card whose
    evaluation swings on it should be reported with that said out loud.
    Callers that pass no roll destroy unconditionally.

    `destroys` OVERRIDES that coin flip with knowledge. It is for effects whose
    source is a named card in your own list rather than an abstract opponent
    answer, where the text is known and pricing it statistically would be
    modelling as unknown something that is written down:

        True    a destruction effect; indestructible ALWAYS saves.
        False   exile, sacrifice or -X/-X; indestructible NEVER saves.
        None    an anonymous answer; priced by `roll` against `destroy_share`.

    Only `resolve_own_wipe` passes it; every opponent-sourced call still takes
    the None path it always did.
    """
    if perm not in g.board:
        return False
    granted = (any(g.has(n) for n in GRANTS_INDESTRUCTIBLE)
              and perm.card.name not in GRANTS_INDESTRUCTIBLE)
    hardy = perm.card.indestructible or granted
    if destroys is not None:
        if hardy and destroys:
            return False
    elif hardy and roll is not None \
            and roll < g.cfg.get("destroy_share", 0.60):
        return False
    g.board.remove(perm)
    if is_creature_now(g, perm) and hasattr(g, "on_creature_death"):
        g.on_creature_death(1, perm)
    if perm.card is g.commander:
        g.commander_cast = False          # back to the command zone
        g.commander_tax += 2
    elif not perm.is_token:
        g.graveyard.append(perm.card)
    return True


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
    goaded_combat(g)


def goaded_combat(g):
    """Rendmaw's Birds are goaded, and YOU are the goader.

    Goad reads "attacks each combat if able and attacks a player other than
    you if able", where "you" is the player who applied it. So every Bird an
    opponent controls is forced to swing at one of the OTHER opponents — never
    at Rendmaw's controller. The pod grinds itself down, which is the half of
    the card that pays you back for handing out free 2/2s.

    Blocking is deliberately light: the Birds fly, and most of what the
    opponent model abstracts into `creatures` does not. `goad_block_share`
    is the fraction of a defender's board assumed able to catch a flier.
    """
    birds = [o for o in living(g) if o.goaded_birds > 0]
    if not birds:
        return
    share = g.cfg.get("goad_block_share", 0.30)
    for att in birds:
        targets = [o for o in living(g) if o is not att]
        if not targets:
            continue
        victim = min(targets, key=lambda o: o.life)
        blocked = min(att.goaded_birds, (victim.creatures + victim.goaded_birds) * share)
        through = max(0.0, att.goaded_birds - blocked)
        victim.life -= 2.0 * through          # 2/2 bodies
    _check_eliminations(g)


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

def flying_of(g, perm) -> bool:
    """Does this permanent have flying RIGHT NOW?

    Unconditional flying is a static tag generated from Scryfall's keywords
    array by `tag_flying.py`. The three conditional fliers in the three decks
    cannot be a tag and live here instead — their flying comes and goes with
    the game state, which is the whole reason they are worth modelling.
    """
    c = perm.card
    if c.flying:
        return True
    n = c.name
    if n == "Serra Ascendant":
        # "As long as you have 30 or more life ... has flying." Same threshold
        # already used for its +5/+5 in KarlovGame.power_of.
        return getattr(g, "your_life", 0.0) >= 30
    if n == "Voice of the Blessed":
        # "As long as this creature has four or more +1/+1 counters on it, it
        # has flying and vigilance."
        return perm.counters >= 4
    if n == "Dragon's Rage Channeler":
        # "Delirium — ... has flying as long as there are four or more card
        # types among cards in your graveyard."
        return len({t for card in g.graveyard for t in card.types}) >= 4
    return False


def _blocker_counts(g, defender):
    """How many of `defender`'s creatures block, and how many can catch a flier.

    Split out of `damage_through` 2026-09-08 so that `combat_damage`'s
    assignment step reads the SAME numbers the resolution step will, rather
    than a second copy that can drift from it. That drift is the exact failure
    KNOWN_ISSUES.md 0u is about — three copies of the miracle discount that had
    quietly stopped agreeing.
    """
    share = g.cfg.get("block_share", 0.60)
    fshare = g.cfg.get("flier_block_share", 0.30)
    n_block = int((defender.creatures + defender.goaded_birds) * share)
    n_fly = int((defender.goaded_birds + defender.creatures * fshare) * share)
    if g.has("Ohran Frostfang"):
        # deathtouch attackers make blocking miserable; fewer opponents do it
        n_block = int(n_block * 0.5)
        n_fly = int(n_fly * 0.5)
    return n_block, min(n_fly, n_block)


def damage_through(g, attackers: list, defender=None) -> float:
    """Opponents chump-block your biggest attackers first — and CANNOT block
    your fliers with most of their board.

    Two things make this non-neutral between the cards under test. A small
    number of very large creatures loses far more to chump blocks than a wide
    board of small ones, because a 1/1 blocking a 6/6 eats six damage while a
    1/1 blocking a 2/2 eats two. And evasion sidesteps the whole mechanism:
    until 2026-09-04 there was no evasion term of any kind, so a 2/2 flier and
    a 2/2 ground creature were identical to the model.

    `flier_block_share` is the fraction of an abstract board assumed able to
    catch a flier — fliers plus reach. Rendmaw's goaded Birds are counted in
    full instead of by that share, because they demonstrably fly: the card
    says "2/2 black Bird creature token with flying".

    `defender` names whose blockers to count. The default of None keeps the
    original meaning — the weakest board at the table — which is right for a
    single undivided swing and is what every caller outside `combat_damage`
    still wants.
    """
    if not attackers:
        return 0.0
    # In a four-player game you send the swarm at whoever is least able to
    # stop it, so the relevant blocker count is the *weakest* opponent's board,
    # not the table's total. Some of their creatures are also tapped from
    # attacking someone else.
    if defender is None:
        defender = min(g.opponents, key=lambda o: o.creatures + o.goaded_birds)
    n_block, n_fly = _blocker_counts(g, defender)

    fly_p, ground_p = [], []
    for p in attackers:
        (fly_p if flying_of(g, p) else ground_p).append(g.power_of(p))
    fly_p.sort(reverse=True)
    ground_p.sort(reverse=True)

    # A defender spends its flying-capable blockers on the biggest fliers, then
    # anything left over on the ground; ground-only blockers can never touch a
    # flier no matter how big it is.
    blocked_fly = min(n_fly, len(fly_p))
    spare = n_fly - blocked_fly
    blocked_ground = min((n_block - n_fly) + spare, len(ground_p))
    return float(sum(fly_p[blocked_fly:]) + sum(ground_p[blocked_ground:]))



# ---------------------------------------------------------------------------
# Life totals and the four-player race
# ---------------------------------------------------------------------------

def init_life(g):
    g.your_life = float(g.cfg.get("starting_life", 40))
    g.result = None            # "win" | "loss" | None (game still running)


def living(g):
    return [o for o in g.opponents if o.alive and o.life > 0]


def pod_size(g) -> int:
    """How many opponents an 'each opponent loses N' POD TOTAL was quoted for.

    `deal_pod_damage(amount, each=True)` takes a pod total and divides it to get
    the per-opponent figure. It used to divide by the number of opponents still
    LIVING, and every caller writes its total for a full pod -- `9.0` with the
    comment "each of 3 opponents loses 3", `6.0` for Guttersnipe's 2 apiece. So
    the divisor shrank as the pod did while the numerator did not, and an
    effect that reads "each opponent loses 1" dealt 1.5 apiece with two players
    left and 3 with one:

        The Meathook Massacre, one creature dying
          3 opponents alive -> each lost 1.0     correct
          2 opponents alive -> each lost 1.5     oracle text says 1.0
          1 opponent  alive -> each lost 3.0     oracle text says 1.0

    The bias runs one way and it runs in the endgame, which is exactly where
    drain converts into a win. It hit Meathook and Cauldron of Essence
    (`engine.on_creature_death`), Baba Lysaga, Guttersnipe, Longshot and
    Tyrant's Choice.

    `tivit.py` was already right and got there differently -- its two call
    sites multiplied by `len(living(g))` before calling, which cancelled the
    divisor. That is the §0u drift shape again: the same rule, six copies of
    the function, and two call sites quietly compensating for what the other
    four did not. Those two now pass a full-pod total like everybody else.

    DERIVED, not the literal 3: `g.opponents` never shrinks -- elimination sets
    `alive`, it does not remove the opponent -- so this is the pod as built and
    stays correct if `pod_brackets` is ever given a different length.

    `pod_damage_full_pod=False` restores the living-count divisor, which is
    what every table published before this reproduces with.
    """
    if not g.cfg.get("pod_damage_full_pod", True):
        return max(1, len(living(g)))
    return max(1, len(g.opponents))


def damage_each(g, n) -> float:
    """'Each opponent loses N' effects.

    RETURNS THE DAMAGE THAT COULD HAVE MATTERED, not the damage dealt: a drain
    for 50 into a player on 3 life is worth 3, and the other 47 is meaningless.
    Every caller records the return value in `m["damage"]` rather than the
    number it asked for, which is what makes the damage metric bounded. See
    `combat_damage` for the measurement that forced this.
    """
    if n <= 0:
        return 0.0
    dealt = 0.0
    for o in living(g):
        dealt += min(n, max(0.0, o.life))
        o.life -= n
    _check_eliminations(g)
    return dealt


def damage_single(g, n) -> float:
    """Focused damage - combat, or a single-target burn spell. Goes at the
    opponent closest to dying, which is what a real pilot does.

    Returns the damage that could have mattered — see `damage_each`.
    """
    if n <= 0:
        return 0.0
    alive = living(g)
    if not alive:
        return 0.0
    target = min(alive, key=lambda o: o.life)
    dealt = min(n, max(0.0, target.life))
    target.life -= n
    _check_eliminations(g)
    return dealt


def _check_eliminations(g):
    for o in g.opponents:
        if o.alive and o.life <= 0:
            o.alive = False
            o.creatures = 0.0
    if not living(g) and g.result is None:
        g.result = "win"


def combat_damage(g, attackers: list, scale: float = 1.0,
                  bonus: float = 0.0) -> float:
    """One attack declared at the WHOLE POD, split across defenders.

    RETURNS THE DAMAGE THAT COULD HAVE MATTERED — the sum over defenders of
    min(dealt, that defender's life) — because damage past lethal is
    meaningless and, in a deck that can go arbitrarily wide, it is nearly all
    of the number. Measured on azusa before this: mean raw damage 4,379 against
    a MEDIAN of 67, ten games in three thousand carrying 69% of the total, and
    98.5% of the mean sitting past the pod's 120 combined life. That is not a
    heavy tail on a usable metric, it is a different quantity wearing its name.

    `scale` and `bonus` carry the two shapes the engines' own combat steps add
    on top of raw power, so that each keeps its existing arithmetic:
      scale   a multiplier on damage that got through (engine.py's Coat of Arms
              term, tivit.py's Cyberdrive burst) -- applied per attacker, so
              the assignment plan sees the same numbers the resolution does.
      bonus   a flat lump added to the swing (lorehold.py's prowess). It is not
              per-attacker, so it is credited to the FIRST group only -- the
              player closest to dying, where the old undivided swing put it.

    THE BUG THIS EXISTS TO FIX (2026-09-08). Every engine's combat did
    `damage_single(g, damage_through(g, attackers))`, which sends the entire
    swing at one player. Measured on azusa: 491 swings of 120+ damage — the
    pod's whole combined life total — and every single one killed EXACTLY ONE
    opponent while a mean of 1.82 were still alive. The largest single hit was
    933,017 damage and killed one player. A board that deals 933,017 was worth
    precisely as much as a board that deals 41, so the deck's entire payoff
    (go arbitrarily wide) was capped at one kill a turn when you need three.

    Two things were incoherent about the old path even for one defender:
    `damage_through` counted the WEAKEST opponent's blockers while
    `damage_single` applied the result to the LOWEST-LIFE opponent's life, and
    those are not usually the same player. Here each chunk is blocked by the
    player it is actually assigned to.

    THE ASSIGNMENT RULE IS A PILOT'S, NOT AN OPTIMISER'S. A real pilot does not
    assign exactly lethal — they assign extra, so that if the defender removes
    the biggest attacker in the assignment the swing still kills. So a defender
    is only taken on when the assignment is lethal WITHOUT its largest
    unblocked attacker. That is deliberately conservative: it kills fewer
    players per turn than a perfect-information split would, which is the
    point. Nothing here reads whether the opponent actually holds removal.

    WHY THE RULE IS EXACT RATHER THAN A SEARCH. Assign the k SMALLEST
    attackers: blockers eat the b biggest of them (`damage_through` chump-blocks
    from the top), so the m = k - b smallest get through. "Lethal without the
    largest of those" is

        (sum of the m that get through) - (the largest of them) >= life

    and a sum minus its own largest term IS the prefix one shorter, so the
    whole condition collapses to `prefix_sum(m-1) >= life` — one binary search
    over a prefix-sum array. That matters: azusa boards reach thousands of
    creatures and an O(n^2) incremental scan would dominate the runtime.

    Smallest-first is also the right play, not merely the cheap one: chump
    blocks eat your biggest attackers, so feeding a 5,000-power Craterhoofed
    creature to a 1/1 block wastes it. Small bodies secure a kill for the least
    power spent, leaving more for the next player.

    APPROXIMATION, SAID OUT LOUD: the closed form above ignores the fly/ground
    split, so the plan can misjudge a defender who blocks fliers and ground
    separately. It is EXACT for an all-ground or all-flying attack (azusa is
    all-ground, so it is exact there) and a slight misjudgement otherwise —
    which resolves as a defender surviving at 1 life, a pilot's error rather
    than a rules error. Resolution always uses the real `damage_through`.

    `cfg["combat_split"]` DEFAULTS TO TRUE as of 2026-09-08 and all six engines
    route their combat through here. Setting it False restores the old
    one-player swing exactly, which is what `run_combat_split.py` measures
    against and the only way to reproduce a table published before that date.

    `m["combat_kills"]` IS NOT `out["opponents_killed"]`, AND IT USED TO SHARE
    ITS NAME (renamed 2026-09-11). Two different quantities:

        m["combat_kills"]        opponents YOUR ATTACK killed — counted here
        out["opponents_killed"]  opponents not alive AT ALL, from any cause,
                                 which includes the ones eliminated by another
                                 opponent's clock in `resolve_clocks`

    Both were written to `m["opponents_killed"]`, and every engine's
    `simulate()` overwrites that key with the second meaning on the way out —
    so the counter written here was dead weight, and the metric reported in
    `experiment.METRICS` has always been the any-cause one. Reading it as "how
    often did my board close a game" was wrong, and in a pod whose clocks
    eliminate players on their own it was wrong by a lot.

    THE RENAME CHANGES NO NUMBER. Nothing reads either key as a decision input
    — both are purely observational — so `out["opponents_killed"]` keeps the
    meaning every committed table was measured with, and `combat_kills` is
    newly available rather than newly different. No regeneration.
    """
    if not attackers:
        return 0.0
    if not g.cfg.get("combat_split", True):
        # `combat_defender` isolates a SECOND defect that the split necessarily
        # fixes as a side effect, so that the two can be measured apart rather
        # than reported as one number. Default "weakest" keeps the old
        # behaviour: damage_through picks `min(g.opponents, ...)`, which ranges
        # over ALL opponents INCLUDING DEAD ONES -- and a dead opponent has
        # creatures = 0.0, so from the first elimination onward the old path
        # faces NO BLOCKERS AT ALL for the rest of the game, while applying the
        # result to whoever is closest to dying. Those are two different
        # players. "target" counts the blockers of the player actually being
        # hit, which is the coherent single-swing version.
        target = min(living(g), key=lambda o: o.life, default=None)
        if g.cfg.get("combat_defender", "weakest") == "target" and target is not None:
            dmg = damage_through(g, attackers, defender=target)
        else:
            dmg = damage_through(g, attackers)
        dmg = dmg * scale + bonus
        # The counters below are recorded on BOTH paths, so an A/B has them on
        # each leg rather than only on the new one. Purely observational -- no
        # RNG is consumed and no decision reads them.
        was = len(living(g))
        dealt = damage_single(g, dmg)
        g.m["raw_damage"] = g.m.get("raw_damage", 0.0) + dmg
        g.m["combat_kills"] = (g.m.get("combat_kills", 0)
                               + was - len(living(g)))
        g.m["attack_targets"] = g.m.get("attack_targets", 0) + (1 if dmg > 0 else 0)
        return dealt

    alive = sorted(living(g), key=lambda o: o.life)
    if not alive:
        return 0.0

    # Ascending power, with prefix sums, so the test above is O(log n).
    # `scale` multiplies each attacker here rather than the total afterwards,
    # so the plan is drawn on the same numbers the resolution will produce.
    pool = sorted(attackers, key=g.power_of)
    pre = [0.0]
    for p in pool:
        pre.append(pre[-1] + g.power_of(p) * scale)
    n = len(pool)

    plan, i = [], 0
    for slot, opp in enumerate(alive):
        if i >= n:
            break
        b, _ = _blocker_counts(g, opp)
        # The flat `bonus` lands on the first group, so that group needs that
        # much less out of the attackers themselves.
        need = opp.life - (bonus if slot == 0 else 0.0)
        if need <= 0:
            plan.append([opp, i, i])       # the lump alone is lethal
            continue
        # smallest j with pre[j] - pre[i] >= need; j is the index one PAST the
        # last attacker that has to connect, so m - 1 = j - i and k = m + b.
        j = bisect.bisect_left(pre, pre[i] + need, i, n + 1)
        k = (j - i) + 1 + b
        if j > n or i + k > n:
            # Cannot secure this one. Chip them with everything left, which is
            # where the old undivided swing went anyway.
            plan.append([opp, i, n])
            i = n
            break
        plan.append([opp, i, i + k])
        i += k
    if i < n and plan:
        # Every living opponent is already covered and there is still board
        # left over. It has to attack somebody; pile it on the last group.
        plan[-1][2] = n

    before_alive = len(living(g))
    effective, raw = 0.0, 0.0
    for slot, (opp, lo, hi) in enumerate(plan):
        dealt = damage_through(g, pool[lo:hi], defender=opp) * scale
        if slot == 0:
            dealt += bonus
        if dealt <= 0:
            continue
        # THE RETURNED NUMBER IS THE BOUNDED ONE. Damage past a player's life
        # total is meaningless, and in this deck it is nearly the whole figure,
        # so `m["damage"]` is fed from here rather than from `raw`.
        effective += min(dealt, max(0.0, opp.life))
        raw += dealt
        opp.life -= dealt
    # Combat damage is simultaneous: everything lands, then deaths are checked.
    _check_eliminations(g)
    g.m["raw_damage"] = g.m.get("raw_damage", 0.0) + raw
    g.m["combat_kills"] = (g.m.get("combat_kills", 0)
                           + before_alive - len(living(g)))
    g.m["attack_targets"] = g.m.get("attack_targets", 0) + len(plan)
    return effective


def your_creatures(g) -> int:
    """How many creatures you control RIGHT NOW, for the blocker count.

    Most of the time that is just the creature cards on your battlefield. The
    exception is an engine where something else is temporarily a creature —
    `azusa` animates its lands, and a board of twenty 2/2 lands is twenty
    blockers whether or not the cards say "Creature" on them. An engine
    declares that by defining `counts_as_creature`; the five that do not get the
    identical count they always got, which is why this is discovered with
    `hasattr` rather than added to every engine (the same way
    `on_creature_death` is discovered by `destroy`).
    """
    ask = getattr(g, "counts_as_creature", None)
    if ask is None:
        return sum(1 for p in g.board if is_creature_now(g, p))
    return sum(1 for p in g.board if ask(p))


def combat_share(g, opp, others) -> float:
    """P(this opponent's ATTACK comes at you) — the inverse of `your_share`.

    `your_share` is threat-weighted and correct for REMOVAL: the scarier your
    board, the more of the pod's answers point at you. Combat works the other
    way round. Creatures swing at the player who cannot block them, and a wide
    board is a deterrent, not a magnet. Using `your_share` for both meant the
    model charged you combat damage for developing — exactly backwards.

    Each attacker picks among the three other players, weighted by how open
    each is: weight = 1 / (1 + blockers). With an empty board against opponents
    holding five each you eat ~75% of the pod's attacks; with a board of seven
    you drop to ~27%, just under the neutral 1/3.
    """
    mine = your_creatures(g)
    w_you = 1.0 / (1.0 + mine)
    total = w_you + sum(1.0 / (1.0 + o.creatures) for o in others)
    return w_you / total if total > 0 else 0.0


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
    mode = g.cfg.get("combat_targeting", "threat")
    for i, opp in enumerate(g.opponents):
        if not opp.alive:
            continue
        others = [o for j, o in enumerate(g.opponents) if j != i and o.alive]
        share = (combat_share(g, opp, others) if mode == "open"
                 else your_share(g, opp, others))
        # An aggro deck's creatures hit harder than a control deck's.
        g.your_life -= opp.creatures * rate * share * opp.p.get("power", 1.0)
    if g.your_life <= 0 and g.result is None:
        g.result = "loss"
        g.m["loss_route"] = 1          # ground down on life


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
            g.m["loss_route"] = 2      # an opponent's clock picked YOU
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
    mine = sum(1 for p in g.board if is_creature_now(g, p))
    theirs = sum(o.creatures for o in living(g))
    return theirs > mine * g.cfg.get("wipe_threshold", 1.4) + 1


def resolve_own_wipe(g, spare_own=False, card=None):
    """Your sweeper resolves. It kills THEIR board and, unless it is one-sided,
    yours too — which the engine previously ignored entirely.

    IT USED TO IGNORE INDESTRUCTIBLE, and the pod's wipe never did. This path
    called `g.board.remove(p)` directly while `board_wipe` went through
    `destroy()`, so the same sweeper effect obeyed two different rules
    depending on which side of the table cast it — the §0u drift shape again,
    in the one place where the asymmetry favours nobody.

    LIVE IN TWO OF THE SIX LISTS, counted from the BUILT decks rather than by
    grepping the modules (`karlov_v2.HELIOD_SUN_CROWNED` is a candidate, not a
    deck member, and reading it as one is how this was first miscounted):

        shilgengar  Avacyn, Angel of Hope + Damn + Wrath of God
        rendmaw     Erebos, Bleak-Hearted + Culling Ritual

    Avacyn is the sharp case, because she grants indestructible to everything
    you control and your own Wrath was ignoring the grant outright. The other
    four lists hold either no indestructible permanent or no destroy-wipe, so
    the fix is inert in them today — and would stop being inert the moment
    Heliod is staged into karlov, which is why this is derived per game rather
    than hard-coded.

    `card` is the sweeper being cast, so the branch is taken from ITS oracle
    text rather than from `destroy_share`'s coin flip — see `wipe_destroys` and
    WIPE_IGNORES_INDESTRUCTIBLE. Coercive Portal's upkeep mode passes none and
    gets the destroys-branch default, which is what its text says.

    NOTE WHAT THIS MAKES TRUE, because it reads like a regression and is not:
    with Avacyn on the battlefield, shilgengar's Damn and Wrath of God are now
    blanks. That is the card doing its job. `main_phase` is greedy and will
    still cast one (queued item 18), which is a POLICY gap, not this one.

    `own_wipe_indestructible=False` restores the old kill-everything path, and
    is what any table published before 2026-09-11 reproduces with.
    """
    for o in living(g):
        o.creatures = 0.0
    if spare_own:
        return
    destroys = wipe_destroys(card)
    honour = g.cfg.get("own_wipe_indestructible", True)
    for p in [p for p in g.board if is_creature_now(g, p)]:
        # FIXED 2026-09-04. Your own sweeper used to remove the commander from
        # the battlefield WITHOUT returning it to the command zone, so
        # `commander_cast` stayed True and it was never recast again.
        # destroy() always got this right; this path never did. Measured cost
        # of the bug, value of a wrath over a blank at 20 turns: Farewell
        # -2.05 -> -0.98 damage, Karlov's Damn -0.0107 -> -0.0032 win rate. It
        # was worth about a point of damage on every self-wipe and it hit
        # Lorehold hardest, where the commander IS the engine.
        # destroy() now carries that rule for this path too, so the knob is
        # applied by restoring what it changed rather than by a second copy.
        was_commander = p.card is g.commander
        cast_before, tax_before = g.commander_cast, g.commander_tax
        if not destroy(g, p, destroys=destroys if honour else False):
            g.m["own_wipe_survivors"] = g.m.get("own_wipe_survivors", 0) + 1
            continue
        # `own_wipe_commander_returns=False` restores the pre-2026-09-04
        # behaviour, which destroy() does not have a flag for because no
        # opponent-sourced removal ever needed one.
        if was_commander and not g.cfg.get("own_wipe_commander_returns", True):
            g.commander_cast, g.commander_tax = cast_before, tax_before
    g.m["own_wipes_cast"] = g.m.get("own_wipes_cast", 0) + 1
