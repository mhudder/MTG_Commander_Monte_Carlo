"""
Azusa, Lost but Seeking v1 — deck definition.

    Azusa, Lost but Seeking  {2}{G}  1/2
      You may play two additional lands on each of your turns.

Costs verified against Scryfall 2026-09-07. Two of the submitted list's mana
values were wrong and are corrected here, not in the source table:

    Avenger of Zendikar   given as MV 8, real cost is {5}{G}{G}  (MV 7)
    Lotus Cobra           given as MV 3, real cost is {1}{G}     (MV 2)

**THE SUBMITTED LIST WAS 99 CARDS, NOT 100.** Counted programmatically before
writing this file: 79 named cards at quantity 1 plus 20 Forest = 99. This
file adds a 21st Forest to reach the legal 100 — the least invasive fix, and
flagged here rather than silently applied. If a different 100th card was
intended, swap it in for one Forest.

THIS IS THE LEAST TUNED OF THE SIX DECKS -- a first-pass list, not one that
has been through ablation. See `edhmc.azusa`'s module docstring for what the
engine implements, what it approximates, and what it leaves MODEL-BLIND
(mostly: land destruction and removal aimed at opponents, since this project
tracks no opponent land or permanent objects at all, only an aggregate
creature count and a life total — the same limitation every other deck in
this project has for removal).

X-spells are modelled at a fixed, hardcoded X rather than a dynamic one — the
same convention `Debt to the Deathless` (Karlov) and `Torment of Hailfire`
(Tivit) already use. Said once here rather than at each card.
"""

from edhmc.engine import Card
from edhmc.decks._evasion import FLYING, INDESTRUCTIBLE


def C(name, types, cost=None, p=0, t=0, script=None, priority=0.0, tags=(),
      threat=0.0, mana=None, tapped=False, haste=False, x_pips=0):
    return Card(name=name, types=frozenset(types.split("/")), cost=cost or {},
                power=p, toughness=t, script=script, priority=priority,
                threat=threat, tags=frozenset(tags),
                mana_ability=(mana[0], frozenset(mana[1])) if mana else None,
                tapped=tapped, haste=haste, x_pips=x_pips,
                flying=name in FLYING,
                indestructible=name in INDESTRUCTIBLE)


def L(name, produces, tapped=False, types="Land", script=None, p=0, t=0):
    return Card(name=name, types=frozenset(types.split("/")), is_land=True,
                produces=frozenset(produces), tapped=tapped, script=script,
                power=p, toughness=t,
                indestructible=name in INDESTRUCTIBLE)


COMMANDER = C("Azusa, Lost but Seeking", "Creature", {"gen": 2, "G": 1},
              1, 2, priority=10, threat=8.0)

# ---------------------------------------------------------------------------
# Creatures / Planeswalkers — 25 (Dryad Arbor is a land-creature and is
# listed in LANDS instead, matching the spreadsheet's own placement of it
# among the land count)
# ---------------------------------------------------------------------------
CREATURES = [
    C("Nissa, Worldwaker", "Planeswalker", {"gen": 3, "G": 2}, 0, 0,
      priority=6, threat=8.0, tags=("Legendary",)),
    C("Augur of Autumn", "Creature", {"gen": 1, "G": 2}, 2, 3,
      priority=8, threat=6.0),
    C("Ashaya, Soul of the Wild", "Creature", {"gen": 3, "G": 2}, 0, 0,
      priority=7, threat=8.0, tags=("Legendary",)),
    C("Avenger of Zendikar", "Creature", {"gen": 5, "G": 2}, 5, 5,
      priority=8.5, threat=9.0),
    C("Bane of Progress", "Creature", {"gen": 4, "G": 2}, 2, 2,
      priority=5, threat=7.0),
    C("Courser of Kruphix", "Creature/Enchantment", {"gen": 1, "G": 2}, 2, 4,
      priority=8, threat=6.0),
    C("Craterhoof Behemoth", "Creature", {"gen": 5, "G": 3}, 5, 5,
      priority=9, threat=9.0, haste=True),
    C("Eternal Witness", "Creature", {"gen": 1, "G": 2}, 2, 1,
      priority=7, threat=5.0),
    C("Kozilek, Butcher of Truth", "Creature", {"gen": 10}, 12, 12,
      priority=7, threat=9.5, tags=("Legendary",)),
    C("Lotus Cobra", "Creature", {"gen": 1, "G": 1}, 2, 1,
      priority=9, threat=6.5),
    C("Nissa, Vastwood Seer // Nissa, Sage Animist", "Creature",
      {"gen": 2, "G": 1}, 2, 2, priority=7.5, threat=6.5, tags=("Legendary",)),
    C("Oracle of Mul Daya", "Creature", {"gen": 3, "G": 1}, 2, 2,
      priority=8.5, threat=7.5),
    C("Quirion Ranger", "Creature", {"G": 1}, 1, 1, priority=4, threat=3.5),
    C("Rampaging Baloths", "Creature", {"gen": 4, "G": 2}, 6, 6,
      priority=8, threat=8.0),
    C("Ramunap Excavator", "Creature", {"gen": 2, "G": 1}, 2, 3,
      priority=7.5, threat=5.5),
    C("Scute Swarm", "Creature", {"gen": 2, "G": 1}, 1, 1,
      priority=8, threat=6.0),
    C("Terastodon", "Creature", {"gen": 6, "G": 2}, 9, 9,
      priority=6, threat=8.5),
    C("Tireless Provisioner", "Creature", {"gen": 2, "G": 1}, 3, 2,
      priority=8, threat=6.5),
    C("Tireless Tracker", "Creature", {"gen": 2, "G": 1}, 3, 2,
      priority=8, threat=6.5),
    C("Titania, Protector of Argoth", "Creature", {"gen": 3, "G": 2}, 5, 3,
      priority=7.5, threat=7.5, tags=("Legendary",)),
    C("Ulamog, the Infinite Gyre", "Creature", {"gen": 11}, 10, 10,
      priority=7, threat=9.5, tags=("Legendary",)),
    C("Wayward Swordtooth", "Creature", {"gen": 2, "G": 1}, 5, 5,
      priority=6, threat=6.0),
    C("Woodland Bellower", "Creature", {"gen": 4, "G": 2}, 6, 5,
      priority=6.5, threat=7.0),
    C("Yavimaya Elder", "Creature", {"gen": 1, "G": 2}, 2, 1,
      priority=6, threat=4.5),
]

# ---------------------------------------------------------------------------
# Artifacts — 8
# ---------------------------------------------------------------------------
ARTIFACTS = [
    C("Sol Ring", "Artifact", {"gen": 1}, priority=10, threat=4.0, mana=(2, "C")),
    C("Oblivion Stone", "Artifact", {"gen": 3}, priority=2, threat=6.0),
    C("Horn of Greed", "Artifact", {"gen": 3}, priority=7, threat=5.0),
    C("Crucible of Worlds", "Artifact", {"gen": 3}, priority=6.5, threat=6.0),
    C("Seer's Sundial", "Artifact", {"gen": 4}, priority=6, threat=5.0),
    C("Storm Cauldron", "Artifact", {"gen": 5}, priority=3, threat=6.5),
    C("Mind's Eye", "Artifact", {"gen": 5}, priority=3, threat=5.5),
    C("Memory Jar", "Artifact", {"gen": 5}, priority=3, threat=5.0),
]

# ---------------------------------------------------------------------------
# Enchantments — 6
# ---------------------------------------------------------------------------
ENCHANTMENTS = [
    C("Sylvan Library", "Enchantment", {"gen": 1, "G": 1}, priority=3, threat=6.0),
    C("Exploration", "Enchantment", {"G": 1}, priority=9, threat=6.0),
    C("Hall of Gemstone", "Enchantment", {"gen": 1, "G": 2}, priority=2, threat=3.0),
    C("Greater Good", "Enchantment", {"gen": 2, "G": 2}, priority=3, threat=6.0),
    C("Perilous Forays", "Enchantment", {"gen": 3, "G": 2}, priority=6.5, threat=6.0),
    C("Abundance", "Enchantment", {"gen": 2, "G": 2}, priority=3, threat=5.0),
]

# ---------------------------------------------------------------------------
# Instants — 6
# ---------------------------------------------------------------------------
INSTANTS = [
    C("Crop Rotation", "Instant", {"G": 1}, priority=2, threat=3.0),
    C("Krosan Grip", "Instant", {"gen": 2, "G": 1}, priority=3),
    C("Realms Uncharted", "Instant", {"gen": 2, "G": 1}, priority=6,
      script="realms_uncharted"),
    C("Beast Within", "Instant", {"gen": 2, "G": 1}, priority=3),
    C("Chord of Calling", "Instant", {"gen": 4, "G": 3}, priority=7,
      threat=6.0, script="chord_of_calling", x_pips=4),
    C("Momentous Fall", "Instant", {"gen": 2, "G": 2}, priority=5,
      threat=5.0, script="momentous_fall"),
]

# ---------------------------------------------------------------------------
# Sorceries — 14
# ---------------------------------------------------------------------------
SORCERIES = [
    C("Animist's Awakening", "Sorcery", {"gen": 4, "G": 1}, priority=6,
      threat=5.0, script="animist", x_pips=4),
    C("Cultivate", "Sorcery", {"gen": 2, "G": 1}, priority=8, threat=4.0,
      script="cultivate"),
    C("Genesis Wave", "Sorcery", {"gen": 6, "G": 3}, priority=8.5,
      threat=7.5, script="genesis_wave", x_pips=6),
    C("Green Sun's Zenith", "Sorcery", {"gen": 3, "G": 1}, priority=7,
      threat=5.0, script="green_sun", x_pips=3),
    C("Harmonize", "Sorcery", {"gen": 2, "G": 2}, priority=6.5, threat=5.5,
      script="draw3"),
    C("Journey of Discovery", "Sorcery", {"gen": 2, "G": 1}, priority=6,
      threat=4.0, script="journey_of_discovery"),
    C("Kodama's Reach", "Sorcery", {"gen": 2, "G": 1}, priority=8,
      threat=4.0, script="cultivate"),
    C("Life from the Loam", "Sorcery", {"gen": 1, "G": 1}, priority=5,
      threat=4.0, script="loam"),
    C("Nylea's Intervention", "Sorcery", {"gen": 3, "G": 2}, priority=5.5,
      threat=4.0, script="nylea_land", x_pips=3),
    C("Regrowth", "Sorcery", {"gen": 1, "G": 1}, priority=6, threat=4.0,
      script="regrowth1"),
    C("Rude Awakening", "Sorcery", {"gen": 4, "G": 1}, priority=7,
      threat=6.0, script="rude_awakening"),
    C("Seek the Horizon", "Sorcery", {"gen": 3, "G": 1}, priority=6,
      threat=4.0, script="seek_horizon"),
    C("Sylvan Awakening", "Sorcery", {"gen": 2, "G": 1}, priority=7,
      threat=6.5, script="sylvan_awakening"),
    C("Sylvan Scrying", "Sorcery", {"gen": 1, "G": 1}, priority=5.5,
      threat=4.0),
]

# ---------------------------------------------------------------------------
# Lands — 40: 19 nonbasic utility lands, Dryad Arbor (a land AND a creature),
# and 21 Forest (see the module docstring on the 99-vs-100 count).
# ---------------------------------------------------------------------------
LANDS = [
    L("Dryad Arbor", "G", types="Land/Creature", p=1, t=1),
    L("Buried Ruin", "C"),
    L("Cavern of Souls", "G"),
    L("Crystal Vein", "C"),
    L("Dust Bowl", "C"),
    L("Eldrazi Temple", "C"),
    L("Eye of Ugin", ""),   # no mana ability on the current oracle text
    L("Ghost Quarter", "C"),
    L("Homeward Path", "C"),
    L("Nykthos, Shrine to Nyx", "G"),
    L("Petrified Field", "C"),
    L("Reliquary Tower", "C"),
    L("Scavenger Grounds", "C"),
    L("Strip Mine", "C"),
    L("Tectonic Edge", "C"),
    L("Temple of the False God", "C"),
    # The three fetches have NO plain mana ability of their own -- only the
    # sac-to-search one -- so `produces` is empty; `land_step` cracks them
    # for a Forest the instant they are played (see `crack_fetch`), so they
    # never sit on the battlefield untapped anyway.
    L("Terramorphic Expanse", "", script="fetch"),
    L("Wasteland", "C"),
    L("Windswept Heath", "", script="fetch"),
    L("Wooded Foothills", "", script="fetch"),
] + [L("Forest", "G")] * 21


def build():
    deck = CREATURES + ARTIFACTS + ENCHANTMENTS + INSTANTS + SORCERIES + LANDS
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER
