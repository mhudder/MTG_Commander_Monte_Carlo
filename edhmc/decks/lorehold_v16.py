"""
Lorehold, the Historian v16 — deck definition.

    Lorehold, the Historian  {3}{R}{W}  5/5 Elder Dragon, flying haste
      Each instant and sorcery card in your hand has miracle {2}.
      At the beginning of each opponent's upkeep, you may discard a card.
      If you do, draw a card.

Costs are hand-authored and were verified card-by-card against Scryfall oracle
text on 2026-09-03; see ORACLE_AUDIT_LOREHOLD.md. Before that audit this
docstring claimed the real cost was always used — it was wrong for 20 cards,
so if a cost here disagrees with Scryfall now, Scryfall is right and this file
is a regression.
"""

from edhmc.engine import Card


def C(name, types, cost=None, p=0, t=0, script=None, priority=0.0, tags=(),
      threat=0.0, miracle=None, treasures=0, mana=None,
      pod_damage=0.0, tokens=(), discards=0, land_face=(), x_pips=0):
    """mana: (amount, "RWC") if the permanent taps for mana.
    pod_damage: direct damage dealt across the three opponents.
    tokens: (count, power, toughness) created on resolution."""
    ma = (mana[0], frozenset(mana[1])) if mana else None
    return Card(name=name, types=frozenset(types.split("/")), cost=cost or {},
                power=p, toughness=t, script=script, priority=priority,
                threat=threat, tags=frozenset(tags), mana_ability=ma,
                miracle_cost=miracle or {}, treasures=treasures,
                pod_damage=pod_damage, tokens=tokens, discards=discards,
                land_face=land_face, x_pips=x_pips)


def L(name, produces, tapped=False, types="Land", tags=()):
    return Card(name=name, types=frozenset(types.split("/")), is_land=True,
                produces=frozenset(produces), tapped=tapped,
                tags=frozenset(tags))


COMMANDER = C("Lorehold, the Historian", "Creature",
              {"gen": 3, "R": 1, "W": 1}, 5, 5, priority=10, threat=9.0)

# ---------------------------------------------------------------------------
# Artifacts (12)
# ---------------------------------------------------------------------------
ARTIFACTS = [
    C("Sol Ring", "Artifact", {"gen": 1}, priority=10, tags=("ramp",), threat=4.0,
      mana=(2, "C")),
    C("Arcane Signet", "Artifact", {"gen": 2}, priority=8, tags=("ramp",), mana=(1, "RWC")),
    C("Boros Signet", "Artifact", {"gen": 2}, priority=8, tags=("ramp",), mana=(1, "RWC")),
    C("Talisman of Conviction", "Artifact", {"gen": 2}, priority=8, tags=("ramp",),
      mana=(1, "RWC")),
    C("Ruby Medallion", "Artifact", {"gen": 2}, priority=9, tags=("ramp",), threat=6.0),
    C("Bender's Waterskin", "Artifact", {"gen": 3}, priority=7, tags=("ramp", "cross_turn"),
      threat=4.5, mana=(1, "RWC")),
    # "{T}: A player of your choice adds {C}" — colourless only, unlike
    # Bender's Waterskin, which really is any colour.
    C("Victory Chimes", "Artifact", {"gen": 3}, priority=7, tags=("ramp", "cross_turn"),
      threat=4.5, mana=(1, "C")),
    C("Sensei's Divining Top", "Artifact", {"gen": 1}, priority=9.5, threat=6.5),
    C("Scroll Rack", "Artifact", {"gen": 2}, priority=9.5, threat=7.5),
    C("Library of Leng", "Artifact", {"gen": 1}, priority=9.8, threat=7.0),
    C("Lightning Greaves", "Artifact", {"gen": 2}, priority=6, threat=4.0),
    C("Monument to Endurance", "Artifact", {"gen": 3}, priority=6, threat=5.0),
]

# ---------------------------------------------------------------------------
# Creatures (11 + commander)
# ---------------------------------------------------------------------------
CREATURES = [
    C("Mother of Runes", "Creature", {"W": 1}, 1, 1, priority=6, threat=6.0),
    C("Dragon's Rage Channeler", "Creature", {"R": 1}, 1, 1, priority=5, threat=3.5),
    # Reach; noncreature spells cost {1} less; 2 damage to EACH opponent on
    # every noncreature cast. A second Guttersnipe that also ramps.
    C("Longshot, Rebel Bowman", "Creature", {"gen": 3, "R": 1}, 3, 3,
      priority=8, threat=7.5, script="longshot"),
    C("Guttersnipe", "Creature", {"gen": 2, "R": 1}, 2, 2, priority=6, threat=6.5),
    C("Pinnacle Monk", "Creature", {"gen": 3, "R": 2}, 2, 2, priority=4,
      tags=("mdfc",), land_face=("R", True)),
    C("Verge Rangers", "Creature", {"gen": 2, "W": 1}, 3, 3, priority=7, threat=5.0),
    C("Hexing Squelcher", "Creature", {"gen": 1, "R": 1}, 2, 2, priority=4),
    C("Storm-Kiln Artist", "Creature", {"gen": 3, "R": 1}, 2, 2, priority=7, threat=7.0),
    C("Monastery Mentor", "Creature", {"gen": 2, "W": 1}, 2, 2,
      priority=8, threat=7.5, script="mentor"),
    C("The Dawning Archaic", "Creature", {"gen": 10}, 7, 7,
      priority=9.0, threat=8.5),
    C("Goliath Daydreamer", "Creature", {"gen": 2, "R": 2}, 4, 4, priority=4, threat=6.0),
]

# ---------------------------------------------------------------------------
# Enchantments (6)
# ---------------------------------------------------------------------------
ENCHANTMENTS = [
    C("Land Tax", "Enchantment", {"W": 1}, priority=7, threat=5.5),
    C("Artist's Talent", "Enchantment", {"gen": 1, "R": 1}, priority=9, threat=7.0),
    C("Double Vision", "Enchantment", {"gen": 3, "R": 2}, priority=9.0, threat=8.0),
    C("Penance", "Enchantment", {"gen": 2, "W": 1}, priority=8, threat=6.0),
    C("Arcane Bombardment", "Enchantment", {"gen": 4, "R": 2},
      priority=9.2, threat=8.5),
    C("Smothering Tithe", "Enchantment", {"gen": 3, "W": 1}, priority=9, threat=8.5),
]

# ---------------------------------------------------------------------------
# Instants (15)
# ---------------------------------------------------------------------------
INSTANTS = [
    C("Swords to Plowshares", "Instant", {"W": 1}, priority=2),
    C("Path to Exile", "Instant", {"W": 1}, priority=2),
    C("Enlightened Tutor", "Instant", {"W": 1}, priority=6, script="tutor"),
    C("Boros Charm", "Instant", {"R": 1, "W": 1}, priority=3, pod_damage=4.0),
    C("Thrill of Possibility", "Instant", {"gen": 1, "R": 1}, priority=3, script="draw2", discards=1),
    C("Sejiri Shelter", "Instant", {"gen": 1, "W": 1}, priority=1, tags=("mdfc",),
      land_face=("W", True)),
    C("Dawn's Truce", "Instant", {"gen": 1, "W": 1}, priority=2),
    C("Chaos Warp", "Instant", {"gen": 2, "R": 1}, priority=2),
    C("Generous Gift", "Instant", {"gen": 2, "W": 1}, priority=2),
    C("Big Score", "Instant", {"gen": 3, "R": 1}, priority=4, script="draw2_treasure", treasures=2, discards=1),
    C("Unexpected Windfall", "Instant", {"gen": 2, "R": 2}, priority=4,
      script="draw2_treasure", treasures=2, discards=1),
    C("Bolt Bend", "Instant", {"gen": 3, "R": 1}, priority=1),
    C("Invoke Calamity", "Instant", {"gen": 1, "R": 4}, priority=5, threat=6.0),
    C("Perch Protection", "Instant", {"gen": 4, "W": 2}, priority=3),
    # NOT a wipe: each opponent exiles their single greatest-power creature,
    # plus spell-mastery damage. Modelled as an edict, not a board sweep.
    C("Olórin's Searing Light", "Instant", {"gen": 2, "R": 1, "W": 1},
      priority=4, script="searing_light"),
]

# ---------------------------------------------------------------------------
# Sorceries (21)
# ---------------------------------------------------------------------------
SORCERIES = [
    C("Faithless Looting", "Sorcery", {"R": 1}, priority=3, script="draw2", discards=2),
    C("Gamble", "Sorcery", {"R": 1}, priority=3),
    C("Mizzix's Mastery", "Sorcery", {"gen": 3, "R": 1}, priority=7, threat=7.5,
      script="mastery"),   # overload {5}{R}{R}{R} handled in main_phase
    C("Borrowed Knowledge", "Sorcery", {"gen": 2, "R": 1, "W": 1}, priority=3, script="draw2"),
    C("Promise of Loyalty", "Sorcery", {"gen": 4, "W": 1}, priority=3, tags=("wipe",)),
    C("Reforge the Soul", "Sorcery", {"gen": 3, "R": 2}, priority=6, script="wheel",
      miracle={"gen": 1, "R": 1}),
    C("Ultima", "Sorcery", {"gen": 3, "W": 2}, priority=5, threat=6.0, tags=("wipe",)),
    C("Farewell", "Sorcery", {"gen": 4, "W": 2}, priority=4, tags=("wipe",)),
    C("Approach of the Second Sun", "Sorcery", {"gen": 6, "W": 1}, priority=6,
      threat=8.0, script="approach"),
    C("Emeria's Call", "Sorcery", {"gen": 4, "W": 3}, priority=5, tags=("mdfc",),
      tokens=(2, 4, 4), land_face=("W", True)),
    C("Hit the Mother Lode", "Sorcery", {"gen": 4, "R": 3}, priority=5,
      script="treasures", treasures=5),
    C("Improvisation Capstone", "Sorcery", {"gen": 5, "R": 2}, priority=5, threat=7.0),
    C("Restoration Seminar", "Sorcery", {"gen": 5, "W": 2}, priority=5, threat=7.5),
    C("Volcanic Vision", "Sorcery", {"gen": 5, "R": 2}, priority=4, threat=6.5),
    C("Ondu Inversion", "Sorcery", {"gen": 6, "W": 2}, priority=3, tags=("wipe", "mdfc",),
      land_face=("W", True)),
    C("Call Forth the Tempest", "Sorcery", {"gen": 5, "R": 3}, priority=4, threat=7.0),
    C("Blasphemous Act", "Sorcery", {"gen": 8, "R": 1}, priority=4, tags=("wipe",)),
    C("Soulfire Eruption", "Sorcery", {"gen": 6, "R": 3}, priority=6, threat=8.0,
      script="soulfire"),
    C("Apex of Power", "Sorcery", {"gen": 7, "R": 3}, priority=5, threat=8.5,
      script="draw4"),
    C("Storm Herd", "Sorcery", {"gen": 8, "W": 2}, priority=7, threat=8.5,
      script="storm_herd"),
    # {9}{C}{C}{C} — three TRUE colourless pips. A Boros deck pays those only
    # from Geier Reach, Mikokoro, Reliquary Tower, Slayers' Stronghold,
    # Sunhome and Battlefield Forge, so this strands far more than {10}{R}{R}.
    C("Rise of the Eldrazi", "Sorcery", {"gen": 9, "C": 3}, priority=7, threat=9.0,
      script="extra_turn"),
]

# ---------------------------------------------------------------------------
# Lands (34)
# ---------------------------------------------------------------------------
LANDS = (
    [L("Mountain", "R")] * 6 +
    [L("Plains", "W")] * 6 +
    [
        L("Command Tower", "RW"),
        L("Sacred Foundry", "RW"),
        L("Battlefield Forge", "RWC"),
        L("Clifftop Retreat", "RW"),
        L("Needleverge Pathway", "RW"),
        L("Rugged Prairie", "RW"),
        L("Sundown Pass", "RW"),
        L("Spectator Seating", "RW"),
        L("Cavern of Souls", "RW"),
        L("Plaza of Heroes", "RW"),
        L("Sunbaked Canyon", "RW"),
        L("Arid Mesa", "RW"),
        L("Prismatic Vista", "RW"),
        L("Fabled Passage", "RW", tapped=True),
        L("Boros Garrison", "RW", tapped=True, tags=("bounce",)),
        L("Elegant Parlor", "RW", tapped=True),
        L("Temple of Triumph", "RW", tapped=True),
        L("Geier Reach Sanitarium", "C"),
        L("Mikokoro, Center of the Sea", "C"),
        L("Reliquary Tower", "C"),
        L("Slayers' Stronghold", "C"),
        L("Sunhome, Fortress of the Legion", "C"),
    ]
)


def build():
    deck = ARTIFACTS + CREATURES + ENCHANTMENTS + INSTANTS + SORCERIES + LANDS
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER


# ---------------------------------------------------------------------------
# The candidates
# ---------------------------------------------------------------------------
# Land face: "as this enters, you may pay 3 life; if you don't, it enters
# tapped." Life is not tracked, so we assume the 3 life is always paid and it
# enters untapped — which FLATTERS the card. See the write-up.
DOUBLE_VISION = C("Double Vision", "Enchantment", {"gen": 3, "R": 2},
                  priority=9.0, threat=8.0)

GALVANOTH = C("Galvanoth", "Creature", {"gen": 3, "R": 2}, 3, 3,
              priority=8.5, threat=8.0, script="galvanoth")
# Upkeep: look at the top card; if it is an instant or sorcery, cast it FREE.
# Fires before the draw step, so the miracle window is still live afterwards.

RADIANT_SCROLLWIELDER = C("Radiant Scrollwielder", "Creature",
                          {"gen": 2, "R": 1, "W": 1}, 2, 4,
                          priority=7, threat=7.0, script="scrollwielder")
# Upkeep: exile the top card; if instant/sorcery you may cast it this turn,
# paying its cost with mana of any colour. Weaker than Galvanoth (not free).
# Its lifelink clause does nothing here -- life is not tracked.

GOLDSPAN_DRAGON = C("Goldspan Dragon", "Creature", {"gen": 3, "R": 2}, 4, 4,
                    priority=8, threat=8.5, script="goldspan")
# 4/4 flying haste; a Treasure on attack, and YOUR Treasures tap for two mana.

WITCH_ENCHANTER = C("Witch Enchanter // Witch-Blessed Meadow", "Creature",
                    {"gen": 3, "W": 1}, 2, 2, priority=3.5, threat=4.0,
                    land_face=("W", False))

MONASTERY_MENTOR = C("Monastery Mentor", "Creature", {"gen": 2, "W": 1}, 2, 2,
                     priority=8, threat=7.5, script="mentor")

ARCANE_BOMBARDMENT = C("Arcane Bombardment", "Enchantment", {"gen": 4, "R": 2},
                       priority=9.2, threat=8.5)

MOLECULE_MAN = C("Molecule Man", "Creature", {"gen": 6}, 5, 5,
                 priority=9.9, threat=9.5)

THE_DAWNING_ARCHAIC = C("The Dawning Archaic", "Creature", {"gen": 10}, 7, 7,
                        priority=9.0, threat=8.5)

# ---------------------------------------------------------------------------
# Notes on the spreadsheet
# ---------------------------------------------------------------------------
# - Sejiri Shelter, Emeria's Call and Ondu Inversion are modal double-faced
#   cards. The sheet counts them as spells, so the deck plays 34 lands but has
#   37 land-capable cards. They are tagged "mdfc" and counted as lands for
#   mulligan purposes only; the engine does not yet play their land halves.
# - Blasphemous Act and The Dawning Archaic both have cost reductions that the
#   engine applies in `reduce_cost`.
