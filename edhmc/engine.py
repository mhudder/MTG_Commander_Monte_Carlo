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

import hashlib
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from edhmc import opponents as OPP
from edhmc.decks._evasion import FLYING_TOKENS, FOREST as _FOREST

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
    indestructible: bool = False
    haste: bool = False
    flying: bool = False      # set from decks/_evasion.py, never by hand
    x_pips: int = 0           # generic pips that are actually {X}
    # ((cost, "tag") | (cost, "tag", preference), ...) -- the OTHER ways this
    # card can be cast. See engine.choose_mode; KNOWN_ISSUES §1b.
    alt_costs: tuple = ()
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


class Board(list):
    """The battlefield, with an O(1) index from card name to count.

    PURELY A PERFORMANCE CHANGE. `Game.has(name)` was a linear scan over the
    board and it is the single hottest call in every one of the four engines —
    38% of total runtime in a Lorehold profile, 475,000 calls in 400 games,
    because almost every static ability in the project is expressed as
    `g.has("Some Card")` inside a loop.

    Safe because the battlefield is only ever `append`ed to and `remove`d from
    (checked across all four engines and opponents.py), and because a Card's
    `name` is never reassigned once built — nothing in edhmc mutates any Card
    field. The other list mutators are overridden anyway so that a future
    caller cannot silently desynchronise the index.

    `remove` keeps list semantics exactly: it removes the FIRST permanent equal
    to the argument, which for Permanent (an unhashable-but-eq dataclass) is
    identity-like in practice but not guaranteed, so the index is updated from
    the entry actually removed rather than from the argument.

    `names` is the index: {card name: how many are on the battlefield}. It is
    READ-ONLY to everyone but this class, and the four `Game.has` methods read
    it directly rather than through an accessor — `has` is called often enough
    that a second Python-level call is a measurable share of the saving.
    """

    __slots__ = ("names",)

    def __init__(self, iterable=()):
        super().__init__(iterable)
        self.names: dict[str, int] = {}
        for p in self:
            self._add(p)

    def _add(self, perm):
        n = perm.card.name
        self.names[n] = self.names.get(n, 0) + 1

    def _drop(self, perm):
        n = perm.card.name
        c = self.names.get(n, 0) - 1
        if c > 0:
            self.names[n] = c
        else:
            self.names.pop(n, None)

    # -- mutators ------------------------------------------------------------

    def append(self, perm):
        super().append(perm)
        self._add(perm)

    def remove(self, perm):
        i = super().index(perm)
        self._drop(super().__getitem__(i))
        super().__delitem__(i)

    def extend(self, it):
        for p in it:
            self.append(p)

    def insert(self, i, perm):
        super().insert(i, perm)
        self._add(perm)

    def pop(self, i=-1):
        p = super().pop(i)
        self._drop(p)
        return p

    def clear(self):
        super().clear()
        self.names.clear()

    def __setitem__(self, i, v):
        raise NotImplementedError("Board does not support item assignment")

    def __delitem__(self, i):
        raise NotImplementedError("Board does not support item deletion")

    def __iadd__(self, other):
        self.extend(other)
        return self

    def sort(self, *a, **k):
        # order-only, so the index is unaffected
        super().sort(*a, **k)


NEVER = 10 ** 9   # an `impending` that never arrives: see is_battlefield_creature


def devotion(g, color: str) -> int:
    """Devotion to `color`: that colour's pips among the mana costs of the
    permanents you control. Tokens have no mana cost and count for nothing.

    `karlov.devotion_white` is the same rule written for the Karlov engine,
    which passes Cards where this one has Permanents. The two are deliberately
    not merged for the reason given in `karlov.is_creature_now`'s docstring.
    """
    return sum(p.card.cost.get(color, 0) for p in g.board)


# Permanents whose creature-ness is CONDITIONAL ON BOARD STATE, with the clause
# that says so. Distinct from STACK_ONLY_CREATURES below, which is static and
# can therefore be stamped once at ETB; this has to be re-asked every time.
DEVOTION_CONDITIONAL_CREATURES = {
    "Erebos, Bleak-Hearted": (
        "B", 5,
        "As long as your devotion to black is less than five, "
        "Erebos isn't a creature."),
}


def is_battlefield_creature(g, p: Permanent) -> bool:
    """Creature-ness ON THE BATTLEFIELD, which is not the type line.

    `Card.types` is the type line as PLAYED, because that is what Rendmaw's
    "whenever you play a card with two or more card types" reads. Three cards in
    these lists are creatures on the stack or only sometimes, and the single
    `types` field cannot say so:

      Grist, the Hunger Tide  "As long as Grist ISN'T ON THE BATTLEFIELD, it's
                              a 1/1 Insect creature in addition to its other
                              types." So it triggers Rendmaw when cast and is a
                              bare Planeswalker afterwards -- it never attacks,
                              never taps for Enduring Vitality, and is not a
                              body for The Great Henge or Overwhelming
                              Stampede. Under March of the World Ooze the old
                              reading made it a 6/6 ATTACKER.
      Impending permanents    Overlord of the Hauntwoods cast for {1}{G}{G}
                              "isn't a creature until the last time counter is
                              removed" -- already modelled, and this is the
                              same question asked once for both.
      Erebos, Bleak-Hearted   "As long as your devotion to black is less than
                              five, Erebos isn't a creature." A {3}{B} 5/6 that
                              spent the early game as an ATTACKER it is not
                              allowed to be -- and a 6/6 one under March of the
                              World Ooze. Unlike the two above this is
                              CONDITIONAL ON BOARD STATE, so the `impending`
                              stamp cannot express it: devotion rises and falls
                              as permanents enter and die, and the question has
                              to be re-asked at every call site rather than
                              answered once at ETB.

    The NEVER stamp is applied at ETB and gated on
    cfg["battlefield_creature_types"], so every table measured before
    2026-09-05 reproduces with the flag off. The devotion clause is gated
    separately on cfg["devotion_creature_types"] -- two different errors that
    happen to be the same question, and a table measured before one of them
    must be able to turn just that one off. See KNOWN_ISSUES.
    """
    if not p.card.is_creature:
        return False
    if p.impending and g.turn < p.impending:
        return False
    cond = DEVOTION_CONDITIONAL_CREATURES.get(p.card.name)
    if cond is not None and g.cfg.get("devotion_creature_types", True):
        color, need, _clause = cond
        if devotion(g, color) < need:
            return False
    return True


# Creatures on the stack that are NOT creatures on the battlefield, with the
# clause that says so. Not a judgement call -- each is quoted oracle text.
STACK_ONLY_CREATURES = {
    "Grist, the Hunger Tide":
        "As long as Grist isn't on the battlefield, it's a 1/1 Insect creature",
}


# ----------------------------------------------------------------------------
# Common random numbers — the mid-game streams
# ----------------------------------------------------------------------------

def _substream_seed(seed: int, name: str) -> int:
    """A stable per-effect seed.

    `hash()` IS NOT USABLE HERE and the reason is not academic. Python salts
    string hashing per process unless PYTHONHASHSEED is set, and `ablation.py`
    runs its workers under `multiprocessing` — on Windows, SPAWNED
    interpreters, each with its own salt. A stream seeded from `hash(name)`
    would therefore produce different numbers in the parent and in every
    worker, and different numbers again on the next run: the cache would
    disagree with a fresh measurement for reasons no one could see. sha256 of
    the name is stable across processes, machines and runs.
    """
    h = hashlib.sha256(name.encode("utf-8")).digest()
    return (seed * 0x9E3779B1) ^ int.from_bytes(h[:8], "big")


class CRNStreams:
    """One independent, INDEX-ADDRESSED random stream per named effect.

    WHY THIS EXISTS (KNOWN_ISSUES §0z17, CLAUDE.md queued item 19). Common
    random numbers are the reason this project is affordable: deck A and deck B
    are the same list with one slot swapped, shuffled on the same seed, so the
    other ~97 cards are dealt identically and almost all variance cancels in
    the difference. That holds only while both branches CONSUME THE SAME RANDOM
    NUMBERS IN THE SAME ORDER.

    Eleven call sites in five files drew mid-game from the single game RNG.
    The moment two branches' boards diverged — one has Arasta out a turn
    earlier, one casts a spell the other cannot — they took a DIFFERENT NUMBER
    of draws, and from that point every later draw in both games read a
    different slot of the same sequence. The pairing was broken for the rest of
    the game. Measured before the fix: 17 of 400 seeds (4.2%) on one rendmaw
    swap, 46 of 300 (15.3%) on one lorehold swap, whose Sunbird's Invocation
    took 1,100 mid-game draws against the other branch's 132.

    THE FIX IS ADDRESSING RATHER THAN ORDERING. Each effect gets its own
    stream, and the Nth firing of that effect reads index N of it. Nothing any
    other effect does can shift it, so a divergence stays contained to the one
    effect that diverged instead of decorrelating the whole game. This is
    `azusa.shuffle_library`'s pre-rolled pattern — which was the only correct
    one in the project — generalised from shuffles to every draw and shared by
    all six engines rather than reimplemented per engine (§0u: the same rule
    written twice is written two different ways, six times over).

    WHAT IT DOES NOT AND CANNOT FIX. If an effect fires three times in branch A
    and four in branch B, the fourth read is a value A never saw. That is not a
    leak, it is the actual difference between the two decks, and it is confined
    to that effect's own stream. There is no scheme that removes it, because
    the branches genuinely did different things.

    Values are generated lazily and CACHED BY INDEX, never regenerated, so a
    stream is a growing list and index N is the same number for the life of the
    game no matter what order it is asked for.
    """

    __slots__ = ("seed", "_rolls", "_gens", "used")

    def __init__(self, seed: int):
        self.seed = seed
        self._rolls: dict[str, list[int]] = {}
        self._gens: dict[str, random.Random] = {}
        # How many times each effect has fired. Read by the CRN audit in
        # `tools/validate.py`, which compares these per seed across an A/B
        # pair -- that is the check the old A/A control structurally could not
        # perform, because an A/A pair cannot diverge.
        self.used: dict[str, int] = {}

    def _bits(self, name: str, i: int) -> int:
        rolls = self._rolls.get(name)
        if rolls is None:
            rolls = self._rolls[name] = []
            self._gens[name] = random.Random(_substream_seed(self.seed, name))
        gen = self._gens[name]
        while len(rolls) <= i:
            rolls.append(gen.getrandbits(32))
        return rolls[i]

    def _take(self, name: str) -> int:
        i = self.used.get(name, 0)
        self.used[name] = i + 1
        return self._bits(name, i)

    def random(self, name: str) -> float:
        """The next float in [0, 1) from this effect's own stream."""
        return self._take(name) / 4294967296.0

    def randrange(self, name: str, n: int) -> int:
        """The next index into a list of length n, from this effect's stream."""
        return int(self.random(name) * n) if n > 0 else 0

    def shuffle(self, name: str, seq: list) -> None:
        """Shuffle `seq` with this effect's Nth pre-rolled permutation."""
        random.Random(self._take(name)).shuffle(seq)

    def draws(self) -> int:
        """Total mid-game draws taken. The quantity §0z17 is measured in."""
        return sum(self.used.values())


# The three accessors every engine calls. They take the Game rather than the
# stream so that ONE knob can restore the old behaviour exactly at every site:
# `crn_streams=False` puts all eleven back on `g.rng` in the original order,
# which is how any number published before 2026-09-13 is reproduced.
class AuditRandom(random.Random):
    """A game RNG that counts what is drawn from it AFTER the opening hand.

    THE CHECK THE A/A CONTROL COULD NOT PERFORM. `tools/validate.py`'s control
    swaps a card for ITSELF, so the two branches never diverge, the call
    sequence is identical by construction, and every mid-game leak in the
    project passed it for months while printing `+0.00` on eighteen metrics.
    A check that cannot fail reads like assurance and is worse than none
    (§0z15, and this is that finding arriving in the one place it hurt most).

    What replaces it is not a cleverer A/A but a STRUCTURAL INVARIANT, which
    holds per game and needs no second branch to compare against: after the
    opening hand is decided, the game RNG is NEVER TOUCHED AGAIN. Every
    mid-game draw goes through `CRNStreams`, which is addressed rather than
    ordered and therefore cannot decorrelate. Nonzero here IS the §0z17 bug.

    Off unless `crn_audit` is set, so the production path pays nothing.
    """

    def __init__(self, seed):
        super().__init__(seed)
        self.sealed = False
        self.after_opening = 0

    def random(self):
        self.after_opening += self.sealed
        return super().random()

    def getrandbits(self, k):
        self.after_opening += self.sealed
        return super().getrandbits(k)

    def shuffle(self, seq):
        self.after_opening += self.sealed
        return super().shuffle(seq)

    def randrange(self, *a, **k):
        self.after_opening += self.sealed
        return super().randrange(*a, **k)


class Metrics(dict):
    """The per-game metrics dict: a counter that reads 0 for a name nobody
    has incremented yet, so `g.m["x"] += 1` never raises.

    WHY (M3 of the 2026-09-17 review). Each engine seeded `self.m` with a
    ~50-key literal and then incremented ~350 sites with `+=`. A site whose
    key was missing from the literal raised KeyError -- in a worker, twenty
    minutes into an ablation, on the one seed where the card fired. Four
    comments in `azusa.__init__` describe exactly that failure, and 35 sites
    in three files had grown a defensive `m.get(k, 0) + 1` instead, so the
    same operation was spelt two ways. The literals stay: they are the
    documented set of metrics and the reason `experiment.analyse` finds
    every METRICS key on both branches. This class is the safety net under
    them, and `simulate()` returns one too, so a metric only one branch ever
    touched reads 0 on the other instead of raising.

    A missing key is NOT inserted on read -- `"x" in m` stays False until
    something writes it -- so `dict(m)`, `json.dump(m)` and `m.keys()` are
    exactly what the game recorded.
    """
    __slots__ = ()

    def __missing__(self, key):
        return 0


def counts_as_land_in_hand(c) -> bool:
    """A land, or a modal double-faced card whose back is one. lorehold.py
    counted its MDFCs for the keep decision from the start; rendmaw,
    shilgengar and tivit carry MDFCs too (`land_face` is set on them) and
    did not, which was §0u's shape rather than a choice (§0z30)."""
    return c.is_land or bool(c.land_face)


def london_mulligan(g) -> None:
    """The opening hand, ONCE, for all six engines (§0z30).

    Draw seven; keep on 2-5 lands (MDFC backs count); otherwise shuffle the
    hand back and try again, up to three mulligans. THE FOURTH HAND IS KEPT
    WHATEVER IT HOLDS -- a pilot on their third mulligan keeps the next seven
    -- and then `mulls` cards go to the bottom, worst first (highest-MV
    nonland, crudely), which is the London rule.

    Six copies of this existed and they disagreed on exactly that last case:
    engine.py drew a FIFTH hand; lorehold.py cleared the hand and never
    redrew (0.11% of its games started with no cards); karlov, tivit,
    shilgengar and azusa neither cleared nor redrew, so the seven cards were
    in hand AND back in the library -- a 106-card deck, in 0.1-0.4% of games.
    CRN paired those games so the defect mostly cancelled in every A/B
    difference, which is how it survived; it is still a defect.

    `g.rng` is the ONLY randomness here and this is the last place it is
    allowed: `seal_rng` follows this call in every `simulate`. §0z17.
    """
    mulls = 0
    for mulls in range(4):
        g.hand = [g.library.pop() for _ in range(7)]
        lands = sum(1 for c in g.hand if counts_as_land_in_hand(c))
        if 2 <= lands <= 5 or mulls == 3:
            break
        g.library.extend(g.hand)
        g.rng.shuffle(g.library)
        g.hand = []
    for _ in range(mulls):
        if g.hand:
            worst = max(g.hand, key=lambda c: (not c.is_land, c.mv))
            g.hand.remove(worst)
            g.library.insert(0, worst)


def make_rng(seed: int, cfg: dict) -> random.Random:
    """The game RNG. A plain `Random` unless the CRN audit is switched on."""
    return AuditRandom(seed) if cfg.get("crn_audit") else random.Random(seed)


def seal_rng(g) -> None:
    """Called once, right after the opening hand: nothing may draw from
    `g.rng` from here on. See AuditRandom."""
    if isinstance(g.rng, AuditRandom):
        g.rng.sealed = True


def crn_random(g, name: str) -> float:
    if not g.cfg.get("crn_streams", True):
        return g.rng.random()
    return g.crn.random(name)


def crn_randrange(g, name: str, n: int) -> int:
    if not g.cfg.get("crn_streams", True):
        return g.rng.randrange(n)
    return g.crn.randrange(name, n)


def crn_shuffle(g, name: str, seq: list) -> None:
    if not g.cfg.get("crn_streams", True):
        g.rng.shuffle(seq)
        return
    g.crn.shuffle(name, seq)


# ----------------------------------------------------------------------------
# Mana
# ----------------------------------------------------------------------------

class ManaUnits(list):
    """A mana pool that remembers where each unit came from.

    A plain `list[frozenset]` is what every engine has passed around since the
    beginning, and it forgets the two things a correct payment needs: WHICH
    permanent produced each unit, and how much we would rather not tap it. So
    `can_pay` chose a colour-correct assignment and `spend` -- handed those
    exact indices -- used only their count. §0z8.

    Subclassing `list` rather than changing the signature of `available_mana`
    is what keeps all six engines' `units = available_mana(g)` call sites
    working untouched, and it degrades safely: `units + [something]` yields a
    pool whose extra entries have NO owner, which is exactly what a Treasure
    or Castle Garenbrig's restricted mana is -- the caller taps those itself.
    """
    __slots__ = ("owners", "weights", "legacy", "surplus")

    def __init__(self, units=(), owners=None, weights=None, legacy=False,
                 surplus=True):
        super().__init__(units)
        self.owners = list(owners) if owners is not None else [None] * len(self)
        self.weights = (list(weights) if weights is not None
                        else [(9, 0, 0)] * len(self))
        # `mana_colour_legacy` has to switch BOTH halves or it is not the old
        # behaviour: the scarcity rule in can_pay and the owner tapping in
        # spend. can_pay has no game to read a cfg from, so the flag rides on
        # the pool.
        self.legacy = legacy
        # False = honour the assignment but leave the CHOICE of
        # assignment exactly as it was. See §0z8.
        self.surplus = surplus

    # An appended unit is OWNERLESS -- nothing on the battlefield taps for a
    # Treasure or for Castle Garenbrig's restricted pool, the caller handles
    # those itself -- and carries the highest reluctance, so a tie is broken
    # toward spending REAL mana first. That is what every caller wants: a
    # Treasure is one-shot and a land is not.
    FOREIGN = (9, 0, 0)

    def __add__(self, other):
        return ManaUnits(list(self) + list(other),
                         self.owners + [None] * len(other),
                         self.weights + [self.FOREIGN] * len(other),
                         self.legacy, self.surplus)

    # THE PARALLEL LISTS MUST SURVIVE IN-PLACE MUTATION. `lorehold.main_phase`
    # does `units.extend(...)` to add its Treasures, which on a plain list is
    # unremarkable and here would leave `weights` shorter than `self` -- an
    # IndexError inside can_pay, and it fired the first time this ran. Every
    # mutator that can grow the pool pads the other two.
    def append(self, unit):
        super().append(unit)
        self.owners.append(None)
        self.weights.append(self.FOREIGN)

    def extend(self, units):
        for u in units:
            self.append(u)

    def __iadd__(self, other):
        self.extend(other)
        return self

    def insert(self, i, unit):
        super().insert(i, unit)
        self.owners.insert(i, None)
        self.weights.insert(i, self.FOREIGN)

    # ... and every mutator that can SHRINK it, for the same reason.
    # `engine.activations` pops consumed units out of the pool so its
    # Skullclamp loop cannot spend the same mana twice; a pop that moved only
    # `self` would leave every later index pointing at the wrong owner, which
    # is silent rather than loud.
    def pop(self, i=-1):
        self.owners.pop(i)
        self.weights.pop(i)
        return super().pop(i)

    def __delitem__(self, i):
        super().__delitem__(i)
        del self.owners[i]
        del self.weights[i]

    def remove(self, unit):
        self.__delitem__(super().index(unit))

    def clear(self):
        super().clear()
        self.owners.clear()
        self.weights.clear()


def can_pay(cost: dict, units: list[frozenset],
            weights: Optional[list] = None) -> Optional[list[int]]:
    """Greedy-with-fallback payment solver.

    `units` is a list of colour-sets, one entry per available mana. Returns the
    indices consumed, or None. Coloured pips are assigned before generic, and
    within a pip the most *constrained* source is spent first.

    SCARCITY, added 2026-09-11 (§0z8). Paying generic used to take "the least
    flexible leftovers", which is right about DUALS -- keep the flexible
    sources -- and blind about SCARCITY, because a Plains and an Island are
    both one colour and the tie therefore broke on board order. With one
    Plains and two Islands, paying {2} spent the Plains, and a white card in
    hand became uncastable for no reason anyone chose. Generic is now paid
    from the MOST PLENTIFUL colour first: for each candidate, score its rarest
    colour by how many units COULD PRODUCE IT AT THE START OF THIS PAYMENT,
    and spend the highest score first. That count is a snapshot on purpose and
    must not be decremented as picks are taken — see the note at the loop. No lookahead into the hand is needed -- "do not spend
    your last white source on a generic cost" is right whatever you hold.

    `weights` is an optional per-unit "reluctance to spend", used ONLY to
    break ties that colour and scarcity leave open. It is what preserves
    `spend`'s long-standing tap order -- lands before mana rocks before mana
    creatures, so a dork can still attack -- now that the assignment made here
    is the one actually tapped. Without it, honouring the assignment would
    silently discard that policy. `available_mana` supplies it.
    """
    # CAN THIS COST BE PAID AT ALL, asked before anything is built. A cost of
    # N mana needs N units however they are coloured, so a hand holding an
    # eight-drop on turn three answers this in one comparison instead of
    # building a candidate list per pip and discovering it at the generic
    # check. `main_phase` asks every card in hand on every pass of its casting
    # loop, so the unaffordable ones are the common case, not the rare one.
    # EXACT, not a heuristic: it can only reject costs the loops below would
    # also have rejected -- they never pay a pip from nothing.
    if sum(cost.values()) > len(units):
        return None

    remaining = list(range(len(units)))
    used: list[int] = []
    legacy = getattr(units, "legacy", False)
    if weights is None and not legacy:
        weights = getattr(units, "weights", None)
    # Tolerant of a short list as well as of none at all: a caller that built
    # its own pool gets the neutral weight rather than an IndexError, so a
    # missing weight degrades to the old tie-break instead of a crash.
    if weights:
        def w(i):
            return weights[i] if i < len(weights) else ManaUnits.FOREIGN
    else:
        def w(i):
            return 0

    # A SECOND UNIT FROM AN ALREADY-TAPPED PERMANENT IS FREE, and forgetting
    # that was the one real regression this change introduced. Crypt Ghast
    # makes a Swamp produce two units; Sol Ring, the bounce lands and Temple
    # of the False God do the same. The old count-based `spend` PACKED them
    # implicitly -- it decremented by the source's full amount, so one tap
    # covered two -- and honouring an assignment that had spread its picks
    # across two Swamps taps both and wastes a unit of each. Measured on
    # Karlov (the Crypt Ghast deck) at -1.69 mana a game before this.
    #
    # So selection is iterative rather than a single sort: a candidate whose
    # owner is ALREADY being tapped costs nothing extra and is taken first.
    owners = getattr(units, "owners", None)
    used_owners: set = set()

    def owner_free(i):
        if owners is None or i >= len(owners) or owners[i] is None:
            return 1
        return 0 if id(owners[i]) in used_owners else 1

    def take(i):
        remaining.remove(i)
        used.append(i)
        if owners is not None and i < len(owners) and owners[i] is not None:
            used_owners.add(id(owners[i]))

    # `len(units[i])` and `w(i)` are fixed for the whole call and both loops
    # below want them, so they are built once here rather than once per pip
    # per candidate. Pure hoisting: the tuples are the same tuples.
    lw = [(len(units[i]), w(i)) for i in range(len(units))]

    for color in ("W", "U", "B", "R", "G", "C"):
        need = cost.get(color, 0)
        for _ in range(need):
            cands = [i for i in remaining if color in units[i]]
            if not cands:
                return None
            # free mana first, then the least flexible source that works,
            # then the cheapest one to lose among those
            take(min(cands, key=lambda i: (owner_free(i), lw[i])))

    gen = cost.get("gen", 0)
    if gen > len(remaining):
        return None

    if legacy:
        # The pre-2026-09-11 generic rule: least flexible leftovers.
        remaining.sort(key=lambda i: len(units[i]))
        used.extend(remaining[:gen])
        return used

    if not getattr(units, "surplus", True):
        # Assignment-only mode: the old CHOICE, but still packed by owner so
        # a multi-unit source is not half-wasted.
        for _ in range(gen):
            best = min(remaining, key=lambda i: (owner_free(i), len(units[i])))
            take(best)
        return used

    # SURPLUS, NOT SCARCITY, and the difference was measured rather than
    # reasoned. Ranking by scarcity alone -- "spend the colour you have most
    # of" -- preserves the RAREST colour, which is wrong whenever the rare
    # colour is not the one the deck needs: on a Karlov list skewed toward
    # Swamps it hoarded the odd Plains and burned the black sources its own
    # {B}{B} costs wanted, and cost 0.0118 win rate at six lands skewed.
    #
    # What matters is supply RELATIVE TO DEMAND. `weights` carries, per unit,
    # how many coloured pips the cards in hand still want of its colours, so
    # surplus is supply minus that. Spend the biggest surplus first.
    supply: dict = {}
    for i in remaining:
        for c in units[i]:
            supply[c] = supply.get(c, 0) + 1

    # THE KEY IS ALMOST ALL CONSTANT, AND IT USED TO BE REBUILT PER PIP PER
    # UNIT. `supply` is a snapshot (see the note below), `len(units[i])` and
    # `w(i)` are fixed for the call, so the ONLY part of this key that changes
    # between picks is `owner_free(i)` -- which is 0 or 1. Building the rest
    # once per unit instead of once per unit per pip is what the loop below
    # does, and it is why `generic_key` no longer exists as a per-comparison
    # function.
    #
    # THIS IS A PURE SPEEDUP AND THE ORDERING IS UNCHANGED, which is the only
    # thing that could make it a behaviour change. `(owner_free, static)` and
    # the old `(owner_free, -surplus, len, w)` order identically -- tuple
    # comparison is lexicographic either way -- and a stable sort followed by
    # "first un-taken entry, preferring owner_free == 0" selects exactly what
    # repeated `min(remaining, key=...)` selected, including its tie-break:
    # `min` returns the FIRST minimal element in iteration order, `remaining`
    # is in increasing index order, and `sorted` is stable. Proved rather than
    # argued -- all six decks come back bit-identical against a HEAD worktree.
    # Two units with the SAME colour set have the same rarest-colour supply,
    # and a green deck's twenty Forests are all `frozenset({"G"})` -- the same
    # object, even. Memoising on the colour set turns one scan per unit into
    # one scan per DISTINCT colour set.
    rarest: dict = {}
    static: dict[int, tuple] = {}
    for i in remaining:
        src = units[i]
        have = rarest.get(src)
        if have is None:
            have = rarest[src] = min((supply[c] for c in src), default=0)
        n_colours, wi = lw[i]
        want = wi[1] if isinstance(wi, tuple) and len(wi) > 1 else 0
        static[i] = (-(have - want), n_colours, wi)

    # `supply` IS A SNAPSHOT OF THE START OF THIS PAYMENT, AND DELIBERATELY SO.
    # It is built once above and NOT decremented as picks are taken, which
    # reads like an oversight — `take` shrinks `remaining` on every pick, so
    # from the second pick on, `supply` counts units already spent.
    #
    # DECREMENTING IT IS A REGRESSION, measured rather than argued. One Plains
    # and three Mountains, paying {3}:
    #
    #   snapshot   W=1 R=3, W=1 R=3, W=1 R=3   -> Mountain, Mountain, Mountain
    #              the Plains survives.
    #   running    W=1 R=3, W=1 R=2, W=1 R=1   -> Mountain, Mountain, TIE
    #              and the tie falls through -surplus, len(units) and the
    #              weight to the order the lands happen to sit in. Board order
    #              decides it, which is the §0z8 defect coming back in the one
    #              function §0z8 exists to fix.
    #
    # The running count degrades exactly as the payment eats the plentiful
    # colour, so the last pip of a big generic cost is always the one at risk.
    # What the rank is FOR is "how replaceable is this unit across the whole
    # payment", and that question is asked once, about the position you are
    # paying from -- not re-asked against a pool you are halfway through
    # spending. `tests/test_mana_colour.py` pins both cases.
    order = sorted(remaining, key=static.__getitem__)
    taken: set = set()
    for _ in range(gen):
        first = pick = None
        for i in order:
            if i in taken:
                continue
            if first is None:
                first = i
            # All owner_free == 0 entries sort ahead of all owner_free == 1
            # entries, so the first one found IS the minimum; everything after
            # it can only be worse on the leading element of the key.
            if owner_free(i) == 0:
                pick = i
                break
        if pick is None:
            pick = first
        taken.add(pick)
        take(pick)
    return used


def castable_modes(card: Card, base_cost: dict):
    """Every way a card can be cast: (cost, tag, preference), printed first.

    KNOWN_ISSUES §1b — "cards can only have one cost" — is really TWO
    problems, and `alt_costs` only ever solved one of them.

    A card's alternatives are not all of a kind. Some are CHEAPER AND WORSE:
    Overlord of the Hauntwoods' Impending 4 deploys it for {1}{G}{G} instead
    of {3}{G}{G} and it is a noncreature enchantment for four turns. Some are
    just A DIFFERENT ROUTE to the same thing: Revitalizing Repast's hybrid pip
    is {B} or {G}, and neither is better. And some are DEARER AND BETTER:
    Mizzix's Mastery is {3}{R} to copy one instant or sorcery from the
    graveyard and {5}{R}{R}{R} to copy EVERY one.

    `alt_costs` was consulted only when the printed cost was unaffordable,
    which is right for the first two kinds and exactly backwards for the
    third. So overload could not be expressed at all and lived instead as a
    hand-written `if card.script == "mastery"` in `lorehold.main_phase`, with
    its cost typed out a second time -- the §0u shape, and precisely the
    "patching instances instead of closing the category" that §1b predicted.

    PREFERENCE closes it. Every mode carries one: the printed cost is 0.0, a
    two-tuple alternative defaults to **-1.0** (cheaper-and-worse, today's
    fallback behaviour, so nothing existing moves), and a dearer-and-better
    mode declares a positive one. The policy takes the best AFFORDABLE mode
    rather than the first one that fits.

    Ties break toward the CHEAPEST, which is what makes a hybrid pip work
    without any preference at all: {B} and {G} are both preference 0 and both
    cost one, so whichever the pool can actually pay wins.
    """
    modes = [(base_cost, None, 0.0)]
    for entry in card.alt_costs:
        cost, tag = entry[0], entry[1]
        pref = entry[2] if len(entry) > 2 else -1.0
        modes.append((cost, tag, pref))
    return modes


def choose_mode(card: Card, base_cost: dict, units):
    """The best affordable mode. Returns (cost, tag, pay_idx) or None.

    THE ONE PLACE THIS DECISION IS MADE, for all six engines. Before §0z20 it
    was made in `engine.main_phase` and nowhere else, so the other five
    engines silently ignored `alt_costs` -- a card with a second cost put into
    the Karlov or Tivit list would have been cast at its printed cost with no
    error and no way to notice. `check_alt_cost_coverage` now raises on that.
    """
    best = None
    for cost, tag, pref in castable_modes(card, base_cost):
        pay = can_pay(cost, units)
        if pay is None:
            continue
        key = (pref, -sum(cost.values()))
        if best is None or key > best[0]:
            best = (key, cost, tag, pay)
    return None if best is None else (best[1], best[2], best[3])


def engine_cfg(cfg: dict) -> dict:
    """A PRIVATE copy of the caller's cfg for an engine to stamp defaults into.

    Five of the six engines open with a block of `cfg.setdefault(...)` calls —
    `shroud_sources`, `protection_cards`, and their own knobs. Those ran
    against the CALLER'S dict, so a caller that built one cfg and handed it to
    several engines got the FIRST engine's defaults applied to all of them:
    construct a Lorehold game and then a Karlov one on the same dict, and
    Karlov silently ran with Lorehold's shroud sources and protection cards,
    because `setdefault` on an already-set key does nothing.

    NOTHING COMMITTED IS AFFECTED, and that was luck rather than design. Every
    tool in the repo builds a fresh cfg per deck — `compare_decks.run()` and
    `fit_pod.evaluate()` both construct theirs inside the per-deck loop, and
    `experiment.run_ab` does `dict(DEFAULT_CFG, **cfg)` on entry — so no table
    or cross-deck comparison ever shared one. It was a convention holding a
    latent bug still, and it was found by a verification script that shared a
    cfg across all six engines and got a different Karlov out of it.

    Stamping a copy also makes the mutation invisible from outside, which is
    what a caller passing a config dict is entitled to expect.
    """
    return dict(cfg)


# Sources that COST YOU LIFE when tapped for a COLOUR, with the clause that
# says so: (damage, the colours that hurt, oracle text). Quoted from
# api.scryfall.com, not from memory.
#
# Deliberately not a `Card` field, for the same reason
# DEVOTION_CONDITIONAL_CREATURES is not one: the cost is conditional on HOW the
# source was tapped, and a static flag cannot say "only when it made {R} or
# {W}". Talisman of Conviction's painless {C} mode is most of why it is played.
PAIN_ON_COLOURED_TAP = {
    "Talisman of Conviction": (
        1.0, frozenset({"R", "W"}),
        "{T}: Add {C}.  {T}: Add {R} or {W}. This artifact deals 1 damage "
        "to you."),
}


def pip_assignment(cost: dict, pay_idx: list[int]) -> list[tuple]:
    """Which COLOURED PIP each of `can_pay`'s chosen indices was spent on.

    `can_pay` takes the coloured pips first, in COLORS order, and appends the
    generic picks afterwards — true of all three of its branches (the default
    surplus rule, `legacy`, and `surplus=False`). So the pip an index covered
    is recoverable from the return value POSITIONALLY, with no change to
    `can_pay`'s signature and no second copy of its choice.

    Indices spent on GENERIC fall off the end of the zip and are not returned,
    which is exactly what the caller wants: a source with a drawback on its
    coloured mode was tapped for its painless one.
    """
    pips = [c for c in COLORS for _ in range(cost.get(c, 0))]
    return list(zip(pay_idx, pips))


def coloured_tap_life(g, cost: dict, pay_idx: list[int], units) -> float:
    """Life lost paying this cost, from sources that charge for a colour.

    THE STATED BLOCKER ON THIS WAS REMOVED BY §0z8 AND THE ISSUE WAS NEVER
    RE-READ. KNOWN_ISSUES §0i says Talisman of Conviction is still free and
    "cannot easily not be: `spend()` does not record which colour a source
    produced". That was true of the count-based payment. Since §0z8
    `available_mana` records each unit's OWNER and `can_pay` returns the exact
    indices it assigned, so the owner and the pip are both in hand at every
    payment site — and `pip_assignment` reads the pip off the existing return
    value rather than adding a second copy of the assignment.

    This is CLAUDE.md's standing finding 16b in its other direction: a policy
    written while a gap was open does not fix itself when the gap closes, and
    neither does a KNOWN_ISSUE that says something is hard.

    Gated on `charge_life_costs` — the knob §0z7 put Bitterblossom and
    Phyrexian Arena behind, because it is the same question about the same
    pod model.
    """
    # TWO SWITCHES, ON PURPOSE. `charge_life_costs` is the family flag §0z7
    # put Bitterblossom and Phyrexian Arena behind and PREDATES this fix, so
    # reverting this one through it would revert those too and no measurement
    # of this change alone would be possible. `talisman_coloured_tap` is this
    # change's own switch; the family flag still overrides it.
    if not g.cfg.get("charge_life_costs", True):
        return 0.0
    if not g.cfg.get("talisman_coloured_tap", True):
        return 0.0
    owners = getattr(units, "owners", None)
    if owners is None:
        return 0.0                     # a pool the caller built; no permanents
    lost = 0.0
    for i, pip in pip_assignment(cost, pay_idx):
        if i >= len(owners) or owners[i] is None:
            continue
        hurt = PAIN_ON_COLOURED_TAP.get(owners[i].card.name)
        if hurt is not None and pip in hurt[1]:
            lost += hurt[0]
    return lost


# ----------------------------------------------------------------------------
# Game state
# ----------------------------------------------------------------------------

class BaseGame:
    """What every engine's Game has in common, written ONCE (§0z32).

    Six engines, no base class, was structural fact 1 in ARCHITECTURE.md and
    the reason §0u, §0z7, §0z8 and §0z30 happened: a rule that lives in a
    method has six copies and the copies drift. This class holds the methods
    whose six copies were byte-identical or differed only by omission --
    `has`, `count`, `draw`, `deal_pod_damage` -- and `finish()` below holds
    the tail of `simulate()` that assembled the output dict six times.

    An engine's Game inherits this and keeps everything that is genuinely
    its own: `__init__` (each builds its own state), `power_of` (Angels,
    Urza's Construct, dynamic lands), `on_creature_death`, `make_permanent`,
    and karlov's `draw`, which overrides to model Alhammarret's Archive.

    Where the copies DIFFERED the union was taken and the difference was
    MEASURED, not argued (§0z32): over 400 staged-list games per deck, every
    numeric output key is identical except karlov's `turn_lethal`, which a
    drain win now stamps at the drain (as engine.py and tivit did) instead
    of at the next `not living` check. azusa's copy did not record
    `drain_damage`, and azusa has no pod-drain source, so nothing moved
    there. No table reads either key.
    """

    # THE MONARCH (2026-09-22). A designation, not a permanent, so it lives on
    # the game rather than the board. It is a CLASS attribute so all six
    # engines have it without six `__init__` edits -- the §0z30 lesson, which
    # is that a rule copied into six methods is a rule that drifts.
    #
    # The whole lifecycle is in `opponents.py` beside the damage path it is
    # tied to (`monarch_end_step`, and the pass check inside
    # `incidental_damage`), because who holds the crown is decided by the
    # pod's combat and nothing else.
    #
    # NOTHING GRANTS THIS YET. No card in any of the six lists makes you the
    # monarch, so `monarch` is False in every measured game and every code
    # path below it is unreached -- which is why this change moves no deck's
    # numbers. `monarch_start=True` drives it for tests and for measuring what
    # the crown is worth before a card exists. §0z12 is the reason that
    # distinction is written down rather than left to be discovered: a tag
    # nothing reads is not inert, it is a loaded gun, so the read side is
    # built and pinned FIRST and the cards come to a tested mechanism.
    monarch = False

    def has(self, name: str) -> bool:
        return name in self.board.names

    def count(self, name: str) -> int:
        return self.board.names.get(name, 0)

    def draw(self, n=1):
        for _ in range(int(n)):
            if not self.library:
                drew_from_empty(self)
                return
            self.hand.append(self.library.pop())
            self.m["cards_drawn"] += 1

    def opening_hand(self):
        london_mulligan(self)      # shared, §0z30; MDFC backs count as lands
        # `monarch_start` exists so the crown can be MEASURED before any card
        # grants it -- which is tier 2 of docs/TRIAGE.md, a count at low N,
        # and the only way to know what the mechanic is worth separately from
        # whatever card carries it. Applied here because this is the one hook
        # all six engines call exactly once per game; a per-engine `__init__`
        # edit would be six copies of one rule (§0z30). Default False, so no
        # measured game is touched.
        if self.cfg.get("monarch_start", False):
            self.monarch = True
            self.m["monarch_gained"] += 1

    def deal_pod_damage(self, amount: float, each: bool = True):
        """`each=True` means 'each opponent loses N' (amount is the pod total)."""
        if amount <= 0:
            return
        # BOUNDED: record what could have mattered, not what was asked for --
        # a drain for 50 into a player on 3 life is worth 3. The divisor is
        # the FULL POD, not the living count -- see OPP.pod_size.
        n = OPP.pod_size(self)
        dealt = (OPP.damage_each(self, amount / n) if each
                 else OPP.damage_single(self, amount))
        self.m["damage"] += dealt
        self.m["drain_damage"] += dealt
        if self.damage_by_turn:
            self.damage_by_turn[-1] += dealt
        if self.result == "win" and self.m["turn_lethal"] == 99:
            self.m["turn_lethal"] = self.turn


def drew_from_empty(g) -> None:
    """A draw was attempted from an EMPTY library: you lose (704.5b, 104.3c).

    QUEUED ITEM 17 (§0z42), and the one place the rule lives. Until 2026-09-22 every
    `draw` in six engines stopped silently at an empty library, so nothing in
    this project could lose to decking -- and every card that strips the
    library (Bolas's Citadel, Apex of Power, Discover) measured as a CEILING.
    Every draw path calls this: `BaseGame.draw`, karlov's Archive override,
    lorehold's `draw_card`. A path that pops the library WITHOUT drawing --
    exile, mill, reveal, "put it into your hand", a Citadel cast off the top
    -- does not call it, and must not: 704.5b is about DRAWING.

    TIMING. The rule is a state-based action, so the loss lands the next time
    SBAs are checked, not mid-resolution. It is recorded here at the moment
    of the draw with FIRST-RESULT-WINS semantics (the same `g.result is None`
    guard every other route uses), which is exact except for one case: a
    resolution that decks you AND then kills the last opponent is a DRAW at a
    real table (104.4a), and is scored here as a loss. Draws are not a result
    this project records; the case needs an empty library and a lethal in one
    resolution, and it is written down rather than modelled.

    `decking_loss=False` restores the old behaviour -- the draw stops, nothing
    is lost -- so what the rule is worth can be measured on the same seeds.
    `drew_from_empty` counts every attempt either way; `loss_route` 3 is a
    game this rule ended.
    """
    g.m["drew_from_empty"] += 1
    if g.cfg.get("decking_loss", True) and g.result is None:     # §0z42
        g.result = "loss"
        g.m["loss_route"] = 3          # decked: drew from an empty library


def draw_is_safe(g, n) -> bool:
    """A PILOT'S check before an OPTIONAL draw: would it leave fewer than
    `decking_reserve` cards in the library?

    THE OTHER HALF OF QUEUED ITEM 17 (§0z42), and the reason the rule alone is not
    the change. Once drawing from an empty library loses (`drew_from_empty`),
    a pilot that draws every card it is offered decks itself -- and measured
    on 2026-09-22 it did, in exactly the games it was WINNING: azusa's decked
    games had drawn 68 cards and held a board of six-figure power, lorehold's
    had cast 54 spells in a chain. A real pilot stops drawing before the last
    card. Asserting otherwise is a POLICY written as conservatism that says
    those games' draw engines kill them, which is the shape of every large
    correction in CLAUDE.md's table.

    ONLY WHERE THE CARD TEXT GIVES A CHOICE. A "may" draw, an activation the
    pilot can decline, a modal choice with a non-draw mode, a spell the pilot
    need not cast. A MANDATORY draw -- the draw step, Horn of Greed, a spell
    already on the stack -- is never guarded: the rule applies to it in full.
    Callers own that distinction; this answers only the arithmetic.

    `decking_reserve` (default 1) is the number of cards the pilot keeps back
    so the next draw step does not lose. It is a judgement and is said out
    loud as a knob; with `decking_loss=False` there is no rule and so no
    reason to hold back, and this returns True unconditionally -- which is
    what makes that knob restore the old behaviour exactly.
    `decking_pilot=False` keeps the rule and removes the caution: the naive
    pilot, so what the guard is worth can be measured apart from the rule.
    """
    # §0z42: both knobs off-switch the caution; the reserve is a judgement.
    if not (g.cfg.get("decking_loss", True)
            and g.cfg.get("decking_pilot", True)):
        return True
    return len(g.library) - n >= g.cfg.get("decking_reserve", 1)


def finish(g) -> "Metrics":
    """The output dict of a finished game -- the tail every `simulate()` had
    its own copy of (§0z32). An engine adds its own keys after this."""
    out = Metrics(g.m)      # reads 0 for a metric this game never touched
    # CRN instrumentation, read by tools/validate.py's audit. §0z17.
    out["crn_draws"] = g.crn.draws()
    out["rng_after_opening"] = getattr(g.rng, "after_opening", 0)
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


class Game(BaseGame):
    def __init__(self, deck: list[Card], commander: Card, cfg: dict,
                 rng: random.Random, seed_for_pod: int = 0):
        self.rng = rng
        # Mid-game randomness lives here, NOT on self.rng. See CRNStreams.
        self.crn = CRNStreams(seed_for_pod)
        self.cfg = cfg
        self.library = list(deck)
        self.rng.shuffle(self.library)
        self.hand: list[Card] = []
        self.board: Board = Board()
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
        self.m = Metrics({
            "damage": 0.0,
            "cards_drawn": 0,
            "mana_floated": 0,
            "mana_spent": 0,
            "rendmaw_triggers": 0,
            "attack_triggers": 0,      # Grave Titan / Overlord "or attacks"
            "tokens_made": 0,
            # 2026-09-16 proposals (§0z26). Counted so each card's
            # MECHANISM is readable directly -- a counter at zero is an
            # unimplemented or uncastable card, which win rate cannot
            # distinguish from a weak one.
            "mycoloth_devoured": 0, "mycoloth_saprolings": 0,
            "spells_cast": 0,
            # Reality Fracture, 2026-09-21 (preview text).
            "proft_gated": 0,
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
            "cauldron_reanimations": 0,
            "loss_route": 0,
            "wurmcoil_deaths": 0,
            "lifelinked": 0.0,
            "erebos_draws": 0,        # "another creature you control dies"
            "erebos_life_paid": 0,
            "erebos_creature_turns": 0,   # turns Erebos was devotion-live
        })
        self.damage_by_turn: list[float] = []
        self.made_token_this_turn = False
        self.beast_active = False
        self.stampede_bonus = 0
        self.creature_died_this_turn = False

    # -- library ops ---------------------------------------------------------

    # -- tokens --------------------------------------------------------------

    def make_tokens(self, n: int, p: int, t: int, subtype: str = "", tapped=False):
        if self.has("Primal Vigor"):
            n *= 2
        # PARALLEL LIVES: "If an effect would create one or more tokens under
        # your control, it creates twice that many of those tokens instead."
        # The same replacement as Primal Vigor without the symmetry -- Vigor
        # doubles for EVERY player, this one only for you. Stacking them is
        # x4, which is correct: two replacement effects each double, and the
        # order the player applies them in does not change the product.
        #
        # THE ONLY TOKEN PATH IN THIS ENGINE, checked rather than assumed --
        # unlike tivit.py, which has this method AND a module-level
        # make_token(), the §0z4 "a doubler must be said in BOTH places or it
        # does nothing" trap.
        if self.has("Parallel Lives"):
            n *= 2
        for _ in range(n):
            card = Card(name=f"{subtype or 'Token'} token",
                        types=frozenset({"Creature"}), power=p, toughness=t,
                        flying=subtype in FLYING_TOKENS)
            perm = Permanent(card=card, tapped=tapped, sick=True,
                             is_token=True, base_p=p, base_t=t)
            # Metallic Mimic: named Bird
            if subtype == "Bird" and self.has("Metallic Mimic"):
                perm.counters += 1
            self.board.append(perm)
            self.m["tokens_made"] += 1
        self.made_token_this_turn = True

    def on_creature_death(self, n: int = 1, perm: Optional[Permanent] = None):
        """Aristocrats drain. Each Blood Artist effect costs the pod 3 life per
        creature that dies (1 from each of three opponents).

        This is the Rendmaw analogue of the Guttersnipe hole in the Lorehold
        engine: in a deck that makes and loses a dozen tokens, a board wipe with
        Blood Artist out is thirty-plus damage that was going entirely
        uncounted.

        `perm` is the permanent that died, when the caller knows it — needed for
        leaves-the-battlefield triggers like Wurmcoil Engine's.
        """
        self.creature_died_this_turn = True

        # CORRECTED 2026-09-04 against oracle text. These three are not the
        # same effect and were all being paid 3 pod life per death:
        #
        #   Blood Artist          "TARGET PLAYER loses 1 life and you gain 1"
        #                         -> 1 damage to ONE opponent, +1 life. It was
        #                            being paid 3x its actual drain.
        #   The Meathook Massacre "each opponent loses 1 life"  (and the life
        #                         gain clause is for OPPONENTS' creatures
        #                         dying, not yours) -> 3 damage, NO life.
        #   Cauldron of Essence   "each opponent loses 1 life and you gain 1"
        #                         -> 3 damage AND +1 life.
        each_opp = sum(1 for p in self.board
                       if p.card.name in ("The Meathook Massacre",
                                          "Cauldron of Essence"))
        single = sum(1 for p in self.board if p.card.name == "Blood Artist")
        if each_opp:
            self.deal_pod_damage(3.0 * n * each_opp)
        if single:
            self.deal_pod_damage(1.0 * n * single, each=False)
        gainers = single + sum(1 for p in self.board
                               if p.card.name == "Cauldron of Essence")
        self.your_life += 1.0 * n * gainers

        # "When this creature dies, create a 3/3 deathtouch Wurm and a 3/3
        # lifelink Wurm." Only the real card, not its own tokens.
        if perm is not None and perm.card.name == "Wurmcoil Engine" \
                and not perm.is_token:
            self.make_tokens(2, 3, 3, "Wurm")
            self.m["wurmcoil_deaths"] += 1

        # Erebos, Bleak-Hearted: "Whenever ANOTHER creature you control dies,
        # you may pay 2 life. If you do, draw a card."
        #
        # No sacrifice and no mana -- it reads deaths that were going to happen
        # anyway, which in a deck that loses a dozen tokens a game is a real
        # draw engine. The engine used to give Erebos Dockside Chef's ability
        # instead (sacrifice a body to draw, once a turn), which is both a
        # different cost and a far worse card. See `activations`.
        #
        # "ANOTHER" is the same clause that cost Karlov three cards in §0h, so
        # a death Erebos was part of does not pay. It is indestructible and, at
        # devotion < 5, not a creature at all, so in practice it is never the
        # one that died -- the check is here so that stays true if either
        # changes.
        #
        # THE 2 LIFE IS A REAL COST AND THIS MODEL UNDERPRICES IT (§0i): life
        # loss is nearly free here, so declining is modelled only as a floor.
        # `erebos_life_floor` is a judgement call, said out loud. The number
        # this card scores is a CEILING for that reason.
        if self.cfg.get("erebos_death_draw", True) \
                and self.has("Erebos, Bleak-Hearted") \
                and not (perm is not None
                         and perm.card.name == "Erebos, Bleak-Hearted"):
            floor = self.cfg.get("erebos_life_floor", 10)
            for _ in range(int(n)):
                if self.your_life - 2 < floor:
                    break
                self.your_life -= 2
                self.draw(1)
                self.m["erebos_draws"] += 1
                self.m["erebos_life_paid"] += 2

    # -- P/T resolution ------------------------------------------------------

    def artifact_died(self, dead: Card):
        """A nontoken artifact you controlled reached the graveyard. §7/§0z19.

        Three cards in this list care, all verified against Scryfall
        2026-09-13, and they are NOT the same trigger:

            Myr Retriever  {2}  "When this creature dies, return ANOTHER
                                 target artifact card from your graveyard to
                                 your hand."
            Junk Diver     {3}  identical, plus flying
            Scrap Trawler  {3}  "Whenever this creature dies OR ANOTHER
                                 ARTIFACT YOU CONTROL is put into a graveyard
                                 from the battlefield, return to your hand
                                 target artifact card in your graveyard with
                                 LESSER mana value."

        The first two fire only on their OWN death. The Trawler also fires on
        every other artifact's, which is why it is checked separately and why
        its own death is checked by NAME -- it has already left the
        battlefield by the time this runs, so `has()` is False for it.

        LESSER, NOT LESSER-OR-EQUAL. Scrap Trawler returning another Scrap
        Trawler is the loop this clause exists to prevent, and `<` is the whole
        of the prevention.

        WHAT DOES NOT REACH HERE, said out loud rather than left implicit:
        `destroy()` only ever kills permanents that are creatures right now,
        so a NONCREATURE artifact -- Sol Ring, the signets, Idol of Oblivion --
        is never destroyed in this project and never triggers the Trawler.
        Its second clause is therefore live only for artifact CREATURES, which
        understates it. That is a limit of the pod model (§4), not of this
        function. Tokens do not reach the graveyard at all, so a sacrificed
        Treasure does not trigger it either.
        """
        if not self.cfg.get("artifact_recursion", True):
            return
        if "Artifact" not in dead.types:
            return

        # THE POOL IS RECOMPUTED PER TRIGGER, NOT SNAPSHOTTED ONCE. Both
        # triggers can fire on the same death -- a Myr Retriever dying while
        # Scrap Trawler is on the battlefield is two separate abilities -- and
        # the first one MOVES A CARD OUT OF THE GRAVEYARD. Built once, the
        # second trigger then selects a card that is already in hand and
        # `remove` raises. This is the identical defect the Invoke Calamity
        # implementation hit the same day (§0z19): a selection is a snapshot
        # and the zone is live.
        #
        # "ANOTHER target artifact card" excludes the card that just died,
        # which is already in the graveyard by the time this is called.
        def take(pred, tag):
            pool = [c for c in self.graveyard
                    if "Artifact" in c.types and c is not dead and pred(c)]
            if not pool:
                return
            best = max(pool, key=lambda c: c.mv)
            self.graveyard.remove(best)
            self.hand.append(best)
            self.m["artifacts_returned"] += 1
            self.m[tag] = self.m.get(tag, 0) + 1

        if dead.name in ("Myr Retriever", "Junk Diver"):
            take(lambda c: True, "retriever_returns")

        if dead.name == "Scrap Trawler" or self.has("Scrap Trawler"):
            take(lambda c: c.mv < dead.mv, "trawler_returns")

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

def tap_reluctance(g: Game, p: Permanent) -> tuple:
    """How much we would rather NOT tap this permanent for mana.

    The order `spend` has always used, lifted out so `can_pay` can break ties
    with it: a real pilot taps lands and non-creature rocks before dorks,
    because a creature tapped for mana in the precombat main phase cannot
    attack. Lands first, then rocks, then mana creatures (biggest last), then
    Enduring Vitality fodder.
    """
    c = p.card
    if c.is_land or c.name == "Everywhere token":
        return (0, 0)
    if c.mana_ability and not c.is_creature:
        return (1, 0)
    if c.mana_ability and c.is_creature:
        return (2, g.power_of(p))
    return (3, g.power_of(p))


def hand_colour_demand(g: Game) -> dict:
    """How many coloured pips of each colour the cards in hand still want.

    SCARCITY ALONE CANNOT BREAK A REAL TIE. With one Plains and two Mountains,
    paying {1}{R} spends a Mountain on the pip and then has to choose between
    the Plains and the last Mountain for the generic -- one unit of each, so
    the scarcity rule sees a tie and the choice falls back to board order. The
    tiebreak that exists in the real game is the HAND: if you are holding a
    white card, the Plains is the one to keep.

    Cheap, and available exactly where it is needed -- `available_mana` has
    the game, and the weights it builds are already plumbed through to
    `can_pay`. Lands in hand are skipped (they have no coloured pips) and so
    is the commander, which is not in hand.
    """
    demand: dict = {}
    for c in getattr(g, "hand", ()):
        if c.is_land:
            continue
        for color in ("W", "U", "B", "R", "G", "C"):
            n = c.cost.get(color, 0)
            if n:
                demand[color] = demand.get(color, 0) + n
    return demand


def available_mana(g: Game) -> list[frozenset]:
    """Enumerate one entry per point of mana available this turn.

    RETURNS A `ManaUnits`, which also carries WHICH PERMANENT PRODUCED EACH
    UNIT and how reluctant we are to tap it. Before 2026-09-11 that mapping
    was thrown away the moment this returned, so `can_pay` proved a
    colour-correct payment and `spend` then tapped a different set of
    permanents chosen by board order -- the engine made a payment it had not
    proved. See §0z8.

    It is still a `list[frozenset]` to every caller, so all six engines'
    existing `units = available_mana(g)` sites are untouched.
    """
    units: list[frozenset] = []
    owners: list = []
    weights: list = []
    any_color = frozenset({"B", "G", "C"})
    all_lands_any = g.has("Dryad of the Ilysian Grove")
    demand = hand_colour_demand(g)

    def add(src, n, owner):
        # (tap order, how badly the hand wants this source's colours, power).
        # Tap order stays PRIMARY -- a land is still spent before a mana
        # creature -- and the hand's demand breaks ties inside a tier, so the
        # last source of a colour something in hand needs is spent last.
        rank, power = tap_reluctance(g, owner)
        want = max((demand.get(c, 0) for c in src), default=0)
        units.extend([src] * n)
        owners.extend([owner] * n)
        weights.extend([(rank, want, power)] * n)

    for p in g.board:
        if p.tapped:
            continue
        c = p.card
        if c.is_land:
            src = any_color if all_lands_any else c.produces
            amt = 2 if "bounce" in c.tags else 1
            add(src, amt, p)
            # Crypt Ghast: "Whenever you tap a SWAMP for mana, add an
            # additional {B}." Swamp is a land subtype the Card model does not
            # carry, so the lands that actually have it are tagged "swamp" in
            # the deck module — for Karlov that is the basics plus Godless
            # Shrine, and NOT Tainted Field, Caves of Koilos, Fetid Heath or
            # the rest, which only produce black.
            if "swamp" in c.tags and g.has("Crypt Ghast"):
                add(frozenset({"B"}), 1, p)
        elif c.mana_ability:
            if c.is_creature and p.sick:
                continue
            amt, colors = c.mana_ability
            add(colors, amt, p)
        elif c.name == "Everywhere token":
            add(any_color, 1, p)

    # Enduring Vitality: creatures tap for mana of any colour
    if g.has("Enduring Vitality"):
        for p in g.board:
            if (is_battlefield_creature(g, p) and not p.tapped and not p.sick
                    and not p.card.mana_ability):
                add(any_color, 1, p)

    return ManaUnits(units, owners, weights,
                     legacy=g.cfg.get("mana_colour_legacy", False),
                     surplus=g.cfg.get("mana_surplus", True))


def cost_after_reduction(g: Game, card: Card) -> dict:
    cost = dict(card.cost)
    if "Artifact" in card.types and g.has("Foundry Inspector"):
        cost["gen"] = max(0, cost.get("gen", 0) - 1)
    if card.name == "The Great Henge":
        best = max([g.power_of(p) for p in g.board
                    if is_battlefield_creature(g, p)] or [0])
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


def altar_fodder(g: Game, units=None) -> list:
    """Creatures Ashnod's Altar is allowed to eat, in board order.

    ONE DEFINITION, TWO CALLERS, and that is deliberate. The Altar is now used
    for two different purposes -- manufacturing DEATHS for Blood Artist and
    The Meathook Massacre in `activations`, and manufacturing MANA in
    `main_phase` (§0z20) -- and "which creatures are expendable" is the same
    question in both. Written twice it would be answered two different ways
    within a month; §0u has six instances of exactly that on record.

    `altar_keep` (6) is the existing conservatism, unchanged: only genuine
    excess is fodder, because a token is a blocker and a Rendmaw trigger.

    NEVER EATS A SOURCE THE CURRENT PAYMENT IS COUNTING ON. When `units` is
    supplied, any creature that owns a unit in the pool is excluded -- with
    Enduring Vitality on the battlefield EVERY untapped creature taps for
    mana, so sacrificing one to pay for a spell could remove more mana than
    the Altar adds. Tapped creatures own no unit and stay eligible.
    """
    keep = g.cfg.get("altar_keep", 6)
    spare = [p for p in g.board if p.is_token and p.card.is_creature]
    if units is not None:
        busy = {id(o) for o in getattr(units, "owners", []) if o is not None}
        spare = [p for p in spare if id(p) not in busy]
    return spare[:max(0, len(spare) - keep)]


def altar_enable(g: Game, units, precombat: bool):
    """Ashnod's Altar: "Sacrifice a creature: Add {C}{C}." §3, closed §0z20.

    THE MANA USED TO ARRIVE AFTER THE MAIN PHASE AND SO COULD NOT BE SPENT.
    The Altar was activated in `activations()`, which runs after every casting
    decision has been taken, so the engine modelled the COST of sacrificing
    and none of the benefit -- and the card ablated slightly negative, which
    KNOWN_ISSUES §3 correctly refused to read as a finding about the card.

    THE POLICY IS "ONLY WHEN IT BUYS SOMETHING", which is both the right
    piloting decision and the conservative one: this is called only when
    NOTHING in hand is otherwise castable, and it sacrifices the FEWEST
    bodies that make the highest-priority stranded card castable. It will not
    eat a token speculatively, and it will not eat one to cast something it
    could already afford.

    Returns (card, pay_indices, alt_tag) with `units` EXTENDED IN PLACE, or
    None. Extending in place matters: `spend` is handed the same object, and
    the appended units are ownerless, which is exactly right -- nothing on the
    battlefield taps for them, the sacrifice already paid for them.
    """
    if not g.cfg.get("altar_mana", True) or not g.has("Ashnod's Altar"):
        return None
    fodder = altar_fodder(g, units)
    if not fodder:
        return None

    best = None
    for c in g.hand:
        if c.is_land:
            continue
        if precombat and "pump" not in c.tags:
            continue
        if "wipe" in c.tags and not OPP.should_cast_own_wipe(g):
            continue
        cost = cost_after_reduction(g, c)
        for k in range(1, len(fodder) + 1):
            if can_pay(cost, units + [frozenset({"C"})] * (2 * k)) is None:
                continue
            # Highest priority wins; among equals, the FEWEST sacrifices.
            key = (c.priority, -k)
            if best is None or key > best[0]:
                best = (key, c, k)
            break

    if best is None:
        return None
    _, card, k = best
    for perm in fodder[:k]:
        g.board.remove(perm)
        g.on_creature_death(1, perm)
        g.m["altar_sacrifices"] += 1
    for _ in range(2 * k):
        units.append(frozenset({"C"}))
    g.m["altar_mana_made"] += 2 * k

    # RE-DERIVED AGAINST THE REAL POOL, because the sacrifices just changed
    # the board and `cost_after_reduction` can read it. If it somehow no
    # longer pays, the mana stays in the pool for the next iteration rather
    # than being spent on a payment that was never proved.
    pay = can_pay(cost_after_reduction(g, card), units)
    if pay is None:
        g.m["altar_wasted"] += 1
        return None
    return (card, pay, None)


# Proft, Sinister Mastermind's Threshold count. A NAMED CONSTANT rather than
# a literal in the gate, so a mutation check can turn the rule off and prove
# the gate is what stops the card -- a check that cannot fail is worse than
# none, and the first version of that mutation set a flag nothing read.
PROFT_THRESHOLD = 7


def pool_after(units, pay_idx) -> "ManaUnits":
    """The pool a LATER cast this turn would see, once `pay_idx` is spent.

    `spend` taps each paid unit's OWNER, so every other unit that permanent
    offered goes with it -- a Sol Ring paying one of its two is tapped for
    both, as far as the next `available_mana` is concerned. An ownerless unit
    (a Treasure, Castle Garenbrig's pool, anything a caller appended) goes
    alone. That is the whole of the prediction; it is a read, and it taps
    nothing.
    """
    paid = set(pay_idx)
    owners = getattr(units, "owners", None)
    if owners is None or len(owners) != len(units):
        owners = [None] * len(units)
    gone = {id(owners[i]) for i in paid
            if i < len(owners) and owners[i] is not None}
    keep = [i for i in range(len(units)) if i not in paid
            and (owners[i] is None or id(owners[i]) not in gone)]
    weights = getattr(units, "weights", None) or [ManaUnits.FOREIGN] * len(units)
    return ManaUnits([units[i] for i in keep], [owners[i] for i in keep],
                     [weights[i] for i in keep],
                     getattr(units, "legacy", False),
                     getattr(units, "surplus", True))


def lookahead_pick(g, options, units, rank, cost_of, pay_of):
    """QUEUED ITEM 18 (§0z43): the greedy pick, unless casting it STRANDS a card that
    casting first would have kept.

    Every engine's `main_phase` casts `max(options, key=rank)` and never asks
    whether that payment makes another affordable card unaffordable. With
    `cast_lookahead` on, before the greedy pick G is cast this asks, for each
    other option O: is O affordable now, unaffordable once G is paid, and is G
    STILL affordable once O is paid? If so, casting O first casts BOTH, and
    greedy casts one. The highest-ranked such O is returned instead of G.

    IT NEVER DROPS THE GREEDY PICK. It only reorders, so G is still cast next
    iteration from the pool the prediction said would pay for it. That is a
    deliberate limit, and it is why this does NOT settle §0z8's own case:
    there, Voice of the Blessed {W}{W} and Lurrus {1}{W}{B} could not both be
    cast from the mana on the table, and `priority` ranks Voice higher -- so
    any policy that trusts `priority` casts Voice. Whether Lurrus is the
    better card is a claim about the PRIORITY NUMBERS (item 18's second half,
    that every deck's priorities were tuned while which land got tapped was
    arbitrary), and no lookahead can answer that by itself.

    One engine-specific thing each caller supplies: `cost_of(item)` is the
    cost dict that item would pay (its chosen MODE, §1b), and `pay_of(item)`
    its payment indices into `units`. Returns the item to cast; with the knob
    off it is exactly `max(options, key=rank)`, so the default path is the
    old path.
    """
    best = max(options, key=rank)
    # §0z43: off by default -- measured, not yet adopted
    if not g.cfg.get("cast_lookahead", False) or len(options) < 2:
        return best
    after_best = pool_after(units, pay_of(best))
    rescues = []
    for it in options:
        if it is best or it[0] is best[0]:
            continue
        if can_pay(cost_of(it), after_best) is not None:
            continue                    # not stranded: greedy casts both
        if can_pay(cost_of(best), pool_after(units, pay_of(it))) is not None:
            rescues.append(it)
    if not rescues:
        return best
    g.m["lookahead_reorders"] += 1
    return max(rescues, key=rank)


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
        mode_cost = {}          # what each option pays, for the lookahead
        for c in g.hand:
            if c.is_land:
                continue
            if precombat and "pump" not in c.tags:
                continue
            # do not wrath your own winning board
            if "wipe" in c.tags and not OPP.should_cast_own_wipe(g):
                continue
            # PROFT, SINISTER MASTERMIND (Reality Fracture, preview text
            # 2026-09-21): "Threshold -- You can't cast this spell unless there
            # are seven or more cards in your graveyard."
            #
            # A CASTABILITY RESTRICTION, NOT A COST. Rule 601.3 is why this is
            # a `continue` in the option filter rather than an adjustment in
            # `cost_after_reduction`: you may not begin to cast the spell at
            # all, so it is never an option and can never be the greedy
            # policy's pick. Modelled as a gate on `len(g.graveyard)`, which is
            # exactly what the card counts.
            #
            # Attached BY NAME, like Heliod and Traveling Chocobo before it
            # (§0z25), and deliberately NOT as a new name SET: one name in one
            # `if` is not the hand-maintained list §0q warns about.
            if (c.name == "Proft, Sinister Mastermind"
                    and len(g.graveyard) < PROFT_THRESHOLD):
                g.m["proft_gated"] += 1
                continue
            # ALTERNATIVE COSTS, through the shared chooser (§1b / §0z20).
            # A card is not one cost: Impending deploys Overlord of the
            # Hauntwoods for {1}{G}{G} instead of {3}{G}{G}, at the price of
            # it being a noncreature enchantment for four turns.
            mode = choose_mode(c, cost_after_reduction(g, c), units)
            if mode is not None:
                _cost, tag, pay = mode
                options.append((c, pay, tag))
                mode_cost[id(c)] = _cost
        if not options:
            # Nothing is castable on lands and rocks alone. THIS is where the
            # Altar belongs -- see altar_enable and KNOWN_ISSUES §3.
            picked = altar_enable(g, units, precombat)
            if picked is None:
                break
            options.append(picked)

        def rank(item):
            c = item[0]
            ramp_bonus = 3.0 if ("ramp" in c.tags and g.turn <= 5) else 0.0
            return (c.priority + ramp_bonus, c.mv)

        # An Altar-enabled pick has no mode cost to price, so the lookahead
        # sits that iteration out.
        if all(id(it[0]) in mode_cost for it in options):
            card, pay, alt_tag = lookahead_pick(
                g, options, units, rank,
                cost_of=lambda it: mode_cost[id(it[0])],
                pay_of=lambda it: it[1])
        else:
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
            OPP.resolve_own_wipe(g, spare_own="onesided" in card.tags, card=card)
        if alt_tag == "impending":
            # enters as a noncreature enchantment; the body arrives later
            g.m["impending_casts"] += 1
        if card.script == "repast":
            # Revitalizing Repast: "put a +1/+1 counter on target creature. It
            # gains indestructible until end of turn." The counter is permanent
            # and is modelled; the indestructible half is not, because this
            # engine cannot hold an instant up for a removal spell it does not
            # see coming. Its number is therefore a floor.
            targets = [p for p in g.board if p.card.is_creature]
            if targets:
                max(targets, key=g.power_of).counters += 1
        if card.script == "stampede":
            # +X/+X and trample until end of turn, X = greatest power you
            # control. In a deck that goes this wide it is a finisher, and the
            # engine was previously casting it for literally no effect.
            g.stampede_bonus += max([g.power_of(p) for p in g.board
                                     if is_battlefield_creature(g, p)] or [0])
        if "Creature" in card.types or "Artifact" in card.types or \
           "Enchantment" in card.types or "Planeswalker" in card.types:
            perm = Permanent(card=card, sick=True,
                             base_p=card.power, base_t=card.toughness)
            if alt_tag == "impending":
                perm.impending = g.turn + 4
            elif (card.name in STACK_ONLY_CREATURES
                  and g.cfg.get("battlefield_creature_types", True)):
                perm.impending = NEVER
            g.board.append(perm)
            run_etb(g, perm)
        else:
            g.graveyard.append(card)


def spend(g: Game, pay_idx: list[int], units: list[frozenset]):
    """Tap the sources that `can_pay` actually assigned.

    IT USED TO TAP BY COUNT, and that was the bug §0z8 is about. `pay_idx`
    names the exact units chosen -- colours and all -- and this function read
    only `len(pay_idx)`, then tapped that many permanents cheapest-to-lose
    first. So the engine PROVED one payment and MADE a different one, and
    which land actually got tapped was decided by board order: with a Plains
    listed before two Mountains, paying {2} tapped the Plains and a white card
    in hand stopped being castable. Reversing the board order reversed the
    answer.

    Now the owners recorded by `available_mana` are tapped directly. The
    long-standing tap ORDER is not lost -- it moved into `can_pay`, which
    breaks colour-and-scarcity ties with `tap_reluctance` so that lands are
    still assigned before rocks before mana creatures.

    FALLS BACK to the old behaviour when the owner list does not match the
    units it was handed -- a pool a caller built itself (azusa's Castle
    Garenbrig, shilgengar's Treasures) is only partly ours, and guessing would
    be worse than the rule this replaces.
    """
    n = len(pay_idx)
    g.m["mana_spent"] += n

    owners = getattr(units, "owners", None)
    if g.cfg.get("mana_colour_legacy", False):
        owners = None           # the pre-2026-09-11 rule, for §0z8's harness
    if owners is not None and len(owners) == len(units):
        for i in pay_idx:
            if i < len(owners) and owners[i] is not None:
                owners[i].tapped = True
        return

    def tap_cost(p: Permanent) -> tuple:
        return tap_reluctance(g, p)

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
        if c.is_land and "swamp" in c.tags and g.has("Crypt Ghast"):
            amt += 1              # the Swamp really did produce two mana
        # NISSA, WHO SHAKES THE WORLD, the Crypt Ghast rule for Forests
        # (2026-09-10, azusa candidate batch 3). A mana DOUBLER has to be said
        # in two places or it is not modelled at all: `azusa.available_mana`
        # offers the extra {G} per untapped Forest, and this says that ONE
        # Forest covers both units. Without it the pool is the right size and
        # the tapping is not -- paying {2} would tap two Forests to produce the
        # two mana one of them made, so the doubler would silently give the
        # deck nothing but a longer list.
        #
        # Guarded on a card that is in no other list -- checked, not assumed,
        # with tools/check_unchanged_decks.py -- so the other five engines
        # cannot reach this branch. FOREST is the generated subtype set, so a
        # Forest by any other name (Dryad Arbor, a shockland in another deck)
        # is covered and a green nonbasic that is not a Forest is not.
        if (c.is_land and c.name in _FOREST
                and g.has("Nissa, Who Shakes the World")):
            amt += 1
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
        make_everywhere(g)
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
    elif s == "mycoloth":
        # DEVOUR 2: "As this creature enters, you MAY sacrifice any number of
        # creatures. It enters with twice that many +1/+1 counters on it."
        #
        # THE SACRIFICE POLICY IS A JUDGEMENT CALL AND IS SAID OUT LOUD.
        # `mycoloth_devour` caps how many bodies it eats; the default eats
        # only TOKENS, never a real card, because trading a card for two
        # counters is a loss the pilot would not take.
        #
        # THIS IS EXACTLY THE SHAPE THAT COST 0.034 WIN RATE ON SHILGENGAR --
        # "would only ever sacrifice 1/1 tokens" was written as conservatism
        # and amounted to asserting the commander's ability does nothing. So
        # the cap is a KNOB and the default is not claimed to be optimal:
        # sweep `mycoloth_devour` before quoting this card's row, and note
        # that eating tokens in a deck whose payoffs COUNT tokens (Coat of
        # Arms, Overwhelming Stampede, Beastmaster Ascension) is a real cost
        # this policy pays and a wider sweep might refuse to.
        cap = g.cfg.get("mycoloth_devour", 4)
        fodder = [q for q in g.board
                  if q.is_token and q.card.is_creature and q is not perm]
        fodder.sort(key=lambda q: g.power_of(q))
        eaten = fodder[:cap]
        for q in eaten:
            g.board.remove(q)
            g.on_creature_death(1, q)
        perm.counters += 2 * len(eaten)
        g.m["mycoloth_devoured"] += len(eaten)
    elif s == "stampede":
        pass
    elif s == "draw1":
        g.draw(1)
    elif s == "draw2":
        g.draw(2)
    if g.has("The Great Henge") and is_battlefield_creature(g, perm) and not perm.is_token:
        g.draw(1)
        perm.counters += 1


def upkeep(g: Game):
    for p in list(g.board):
        s = p.card.script
        if s == "mycoloth":
            # "At the beginning of your upkeep, create a 1/1 green Saproling
            # creature token FOR EACH +1/+1 COUNTER on this creature." It
            # compounds only if it is fed again; a lone Mycoloth with zero
            # counters makes nothing, which is why the devour policy above is
            # the whole card rather than a detail.
            n = p.counters
            if n:
                g.make_tokens(n, 1, 1, "Saproling")
                g.m["mycoloth_saprolings"] += n
        elif s == "bitterblossom":
            # "At the beginning of your upkeep, create a 1/1 black Faerie
            # Rogue creature token with flying, AND YOU LOSE 1 LIFE."
            #
            # THE LIFE WAS FREE UNTIL 2026-09-10 (§0i, §0z7). Under pod v1 that
            # was defensible -- your life total was inert and 100% of losses
            # were an opponent's clock -- but pod v3 made life decide roughly a
            # third of them, and this card pays every upkeep from the turn it
            # lands, so it was the largest uncosted drawback in any list and
            # its +0.0205 (Rendmaw's #5 card) was a ceiling.
            #
            # Charged here rather than tracked as a counter, because
            # `opponents.incidental_damage` reads `your_life` at the end of
            # every turn and is where the loss check lives.
            g.make_tokens(1, 1, 1, "Faerie")
            if g.cfg.get("charge_life_costs", True):
                g.your_life -= 1
                g.m["life_lost_to_own_cards"] += 1
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
        if crn_random(g, "arasta") < g.cfg.get("opp_instant_rate", 0.8):
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

    # Cauldron of Essence: "{1}{B}{G}, {T}, Sacrifice a creature: return target
    # creature card from your graveyard to the battlefield. Sorcery speed."
    # A repeatable sac outlet *and* recursion, so it feeds its own drain half.
    # The graveyard here is stocked by opponents' removal and wipes (see
    # opponents.destroy), which is exactly when you want the ability.
    if g.has("Cauldron of Essence"):
        pool = [c for c in g.graveyard if c.is_creature]
        fodder = [p for p in g.board if p.card.is_creature
                  and p.card is not g.commander]
        if pool and fodder:
            pay = can_pay({"gen": 1, "B": 1, "G": 1}, units)
            if pay is not None:
                spend(g, pay, units)
                for i in sorted(pay, reverse=True):
                    units.pop(i)
                victim = min(fodder, key=lambda p: g.power_of(p))
                g.board.remove(victim)
                g.on_creature_death(1, victim)
                best = max(pool, key=lambda c: c.power)
                g.graveyard.remove(best)
                perm = Permanent(card=best, sick=True,
                                 base_p=best.power, base_t=best.toughness)
                g.board.append(perm)
                run_etb(g, perm)
                g.m["cauldron_reanimations"] += 1

    # Ashnod's Altar: sacrifice spare tokens for mana. Modelled conservatively
    # (only genuine excess) because the real value here is not the mana but the
    # deaths it manufactures for Blood Artist and The Meathook Massacre.
    # Only sacrifice when the deaths are actually worth something. The mana the
    # Altar produces arrives after the main phase in this engine and so cannot
    # be spent; modelling the cost without the benefit made it look like a bad
    # card, which was a bug in the model, not a finding about the card.
    if g.has("Ashnod's Altar") and (g.has("Blood Artist")
                                    or g.has("The Meathook Massacre")):
        # `altar_fodder` is the shared definition of "which creatures are
        # expendable", also used by main_phase's mana step (§0z20). Called
        # with no `units` here because this path is post-main and taps
        # nothing: the selection is identical to what this block did inline.
        for p in altar_fodder(g)[:2]:
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
        g.draw(1 + sum(1 for i in range(3)
                       if crn_random(g, f"deathreap{i}")
                       < g.cfg.get("opp_death_rate", 0.55)))

    # Dockside Chef: "{1}{B}, Sacrifice an artifact or creature: Draw a card."
    # Taken once a turn off the cheapest token, with `units` standing in for the
    # mana. Grim Backwoods is the same shape at {2}{B}{G}.
    #
    # EREBOS USED TO BE IN THIS CONDITION AND DOES NOT HAVE THIS ABILITY. Its
    # activated ability is "{1}{B}, Sacrifice another creature: TARGET CREATURE
    # GETS -2/-1 until end of turn" -- no card, and against an opponent board
    # that is a blocker count there is nothing to shrink, so that half is
    # model-blind. Its card draw is a TRIGGER, not an activation, and is handled
    # in `Game.on_creature_death`: it needs no sacrifice at all, which is a
    # different and much better card in a deck that loses a dozen tokens a game.
    # `erebos_death_draw=False` puts Erebos back in this condition, which is
    # what every table before 2026-09-06 was measured with.
    sackers = g.has("Dockside Chef") or (
        not g.cfg.get("erebos_death_draw", True)
        and g.has("Erebos, Bleak-Hearted"))
    if sackers and units:
        chaff = [p for p in g.board if p.is_token and not p.sick
                 and g.power_of(p) <= 2]
        if chaff:
            g.board.remove(chaff[0])
            g.on_creature_death(1)
            g.draw(1)


def attack_triggers(g: Game, attackers: list[Permanent]):
    """"Whenever this ... ENTERS OR ATTACKS" — the half that was missing.

    Two cards in the Rendmaw list read "enters or attacks" and only the ETB
    was modelled, so both were understated by everything after the turn they
    landed. Found in the 2026-09-05 oracle re-verification.

    The tokens are created AFTER attackers are chosen and are not themselves
    attacking, which is correct: an attack trigger resolves in the declare
    attackers step, long after the game has locked in who is swinging.

    Gated on cfg["attack_triggers"] so the tables measured before 2026-09-05
    stay reproducible.
    """
    if not g.cfg.get("attack_triggers", True):
        return
    for p in attackers:
        n = p.card.script
        if n == "grave_titan":
            # "Whenever this creature enters or attacks, create two 2/2 black
            # Zombie creature tokens."
            g.make_tokens(2, 2, 2, "Zombie")
            g.m["attack_triggers"] += 1
        elif n == "overlord":
            # "Whenever this permanent enters or attacks, create a tapped
            # colorless land token named Everywhere that is every basic land
            # type." An Overlord deployed for its IMPENDING cost is not a
            # creature yet, so it cannot attack and cannot reach this — which
            # is_battlefield_creature already enforces in the attacker filter.
            make_everywhere(g)
            g.m["attack_triggers"] += 1


def make_everywhere(g: Game):
    """Overlord of the Hauntwoods' land token.

    "Create a TAPPED colorless land token named Everywhere that is every basic
    land type." Two things were wrong before 2026-09-05: it entered UNTAPPED,
    handing you the mana a turn early, and only the ETB half ever made one.

    It is deliberately `is_land=False` with a name the mana code special-cases:
    it taps for any colour this deck needs, but must not count as a land for
    land-drop or mulligan purposes.

    The tapped half is gated separately from the attack half, because they are
    two different errors that happen to live on the same card: one gave you the
    mana a turn early, the other never gave you the second token at all.
    """
    # `is_token=True` because it IS one — "create a tapped colorless LAND
    # TOKEN named Everywhere". It defaulted to False, and the one place that
    # mattered was `opponents.spot_removal`, which targets
    # `not p.card.is_land and not p.is_token`: this permanent is deliberately
    # `is_land=False` (so it cannot be counted for land drops or mulligans),
    # so it read as a nonland nontoken and an opponent could spend a Doom
    # Blade on a land token. `destroy` also put it in the GRAVEYARD as a card,
    # which a token never becomes.
    #
    # `threat_of`'s token discount does not change anything here: the token
    # has no mana cost, so its derived threat was already 0.0.
    g.board.append(Permanent(
        card=Card(name="Everywhere token", types=frozenset({"Land"}),
                  is_land=False),
        tapped=g.cfg.get("everywhere_enters_tapped", True), sick=False,
        is_token=g.cfg.get("everywhere_is_token", True)))


def combat(g: Game):
    attackers = [p for p in g.board
                 if is_battlefield_creature(g, p) and not p.tapped and not p.sick]
    if not attackers:
        g.damage_by_turn.append(0.0)
        return
    g.beast_active = (g.has("Beastmaster Ascension") and len(attackers) >= 7)

    attack_triggers(g, attackers)

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

    # opponents block: chump the biggest attackers first. `scale` carries the
    # Coat of Arms term above into opponents.combat_damage, which applies it
    # per attacker so its assignment plan and its resolution agree.
    combat_scale = None
    if g.cfg.get("derived_blocking", True):
        combat_scale = dmg / max(1e-9, sum(g.power_of(p) for p in attackers))
    else:
        dmg *= (1.0 - g.cfg.get("block_rate", 0.30))

    # Lifelink, taken as the attacker's power: it pays out whether the damage
    # lands on a player or on a blocker.
    #
    # DO NOT read this as survivability. Measured 2026-09-04: 100% of losses in
    # all three decks are opponent CLOCKS (opponents.resolve_clocks), which are
    # threat-weighted and do not read your life total at all.
    #
    # And this is BY DESIGN, not a close race. With the clocks disabled
    # entirely, incidental_damage kills you in 0.4% of Rendmaw games and 0.6%
    # of Lorehold games by turn 20 (2.9% by turn 30, 0.0% for Karlov). The
    # opponents' board is a float capped at 7 that chips for
    # `creatures * 0.45 * your_share` — it was never calibrated to kill anyone.
    # The clock IS the abstraction standing in for "an opponent actually wins".
    #
    # So a lifelinking body's defensive value here is nil, and any card whose
    # whole job is a bigger life total is MODEL-BLIND.
    for p in attackers:
        if p.card.lifelink:
            g.your_life += g.power_of(p)
            g.m["lifelinked"] += g.power_of(p)

    for p in attackers:
        p.tapped = True
    # One attack at the whole pod; `dmg` comes back BOUNDED at what could have
    # mattered. When derived_blocking is off there is no blocking model to
    # divide, so the flat haircut above is passed through as a lump.
    if combat_scale is not None:
        dmg = OPP.combat_damage(g, attackers, scale=combat_scale)
    else:
        # derived_blocking=False is the legacy flat-haircut pod. It models no
        # blockers per defender, so there is nothing for the split to plan
        # against; it keeps the single swing, bounded by damage_single.
        dmg = OPP.damage_single(g, dmg)
    g.m["damage"] += dmg
    g.damage_by_turn.append(dmg)
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

    # Diagnostic only: how many of Erebos's turns on the battlefield it is
    # actually a creature for. The whole point of the devotion clause is that
    # this is well below the number of turns it is out.
    for p in g.board:
        if p.card.name in DEVOTION_CONDITIONAL_CREATURES \
                and is_battlefield_creature(g, p):
            g.m["erebos_creature_turns"] += 1

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
        OPP.pod_phase(g)           # one order for six engines, §0z30


def simulate(deck: list[Card], commander: Card, cfg: dict, seed: int) -> dict:
    rng = make_rng(seed, cfg)
    g = Game(deck, commander, cfg, rng, seed_for_pod=seed)
    g.opening_hand()
    # From here the game RNG must never be touched again. §0z17.
    seal_rng(g)
    for _ in range(cfg.get("turns", 10)):
        take_turn(g)
        if g.result is not None:
            break
    return finish(g)
