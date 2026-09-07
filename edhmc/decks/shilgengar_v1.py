"""
Shilgengar, Sire of Famine v1 — deck definition.

    Shilgengar, Sire of Famine  {3}{B}{B}  6/6 flying
      Sacrifice another creature: Create a Blood token. If you sacrificed an
      Angel this way, create a number of Blood tokens equal to its toughness
      instead.
      {W/B}{W/B}{W/B}, Sacrifice six Blood tokens: Return each creature card
      from your graveyard to the battlefield with a finality counter on it.
      Those creatures are Vampires in addition to their other types.

Costs, P/T and keywords are hand-authored against Scryfall oracle text,
verified 2026-09-07 (see `edhmc.shilgengar`'s module docstring for the engine
side of that verification). Six spreadsheet mana values were wrong and are
corrected here, not there — the spreadsheet is source-of-record for the LIST,
not for a card's cost:

    Revel in Riches         sheet said 4, real cost is {4}{B}         (MV 5)
    Grim Haruspex           sheet said 4, real cost is {2}{B}         (MV 3)
    Herald of War           sheet said 4, real cost is {3}{W}{W}      (MV 5)
    Priest of Fell Rites    sheet said 3, real cost is {W}{B}         (MV 2)
    Vampiric Rites          sheet said 2, real cost is {B}            (MV 1)
    Malakir Rebirth         sheet's "2" is the LAND back face's MV, not
                            the spell's; the front face is {B} (MV 1)

THIS IS THE LEAST TUNED OF THE FIVE DECKS -- it is a starting spreadsheet, not
a list that has been through ablation. Treat every priority/threat number
below as a first guess, not a measurement. Nothing has been staged or
committed against it; `python ablation.py shilgengar <n> <turns>` is the next
step, same as it was for the other four.

Angels and Clerics are marked with `tags=("angel",)` / `("cleric",)` — see
`edhmc/shilgengar.py`'s module docstring for why `Card.types` cannot carry
this and what reads the tag.
"""

from edhmc.engine import Card
from edhmc.decks._evasion import FLYING, INDESTRUCTIBLE


def C(name, types, cost=None, p=0, t=0, script=None, priority=0.0, tags=(),
      threat=0.0, mana=None, lifelink=False, tapped=False, land_face=(),
      x_pips=0):
    ma = (mana[0], frozenset(mana[1])) if mana else None
    return Card(name=name, types=frozenset(types.split("/")), cost=cost or {},
                power=p, toughness=t, script=script, priority=priority,
                threat=threat, tags=frozenset(tags), mana_ability=ma,
                lifelink=lifelink, tapped=tapped, land_face=land_face,
                x_pips=x_pips,
                flying=name in FLYING,
                indestructible=name in INDESTRUCTIBLE)


def L(name, produces, tapped=False, types="Land", tags=()):
    return Card(name=name, types=frozenset(types.split("/")), is_land=True,
                produces=frozenset(produces), tapped=tapped,
                tags=frozenset(tags),
                indestructible=name in INDESTRUCTIBLE)


COMMANDER = C("Shilgengar, Sire of Famine", "Creature", {"gen": 3, "B": 2},
              6, 6, priority=10, threat=8.5)

# ---------------------------------------------------------------------------
# Massive Haymakers (bombs) — 22
# ---------------------------------------------------------------------------
HAYMAKERS = [
    C("Avacyn, Angel of Hope", "Creature", {"gen": 5, "W": 3}, 8, 8,
      priority=9, threat=9.5),
    C("Elesh Norn, Grand Cenobite", "Creature", {"gen": 5, "W": 2}, 4, 7,
      priority=8.5, threat=9.0, script="elesh_norn"),
    C("Serra's Emissary", "Creature", {"gen": 4, "W": 3}, 7, 7,
      priority=7, threat=8.5, tags=("angel",)),
    C("Archangel of Thune", "Creature", {"gen": 3, "W": 2}, 3, 4,
      priority=8.5, threat=8.0, tags=("angel",), lifelink=True),
    C("Kokusho, the Evening Star", "Creature", {"gen": 4, "B": 2}, 5, 5,
      priority=8, threat=8.5),
    C("Massacre Wurm", "Creature", {"gen": 3, "B": 3}, 6, 5,
      priority=7.5, threat=9.0, script="massacre_wurm"),
    C("Lyra Dawnbringer", "Creature", {"gen": 3, "W": 2}, 5, 5,
      priority=8, threat=8.0, tags=("angel",), lifelink=True),
    C("Reya Dawnbringer", "Creature", {"gen": 6, "W": 3}, 4, 6,
      priority=6, threat=8.0, tags=("angel",)),
    C("Angel of Serenity", "Creature", {"gen": 4, "W": 3}, 5, 6,
      priority=5.5, threat=7.5, tags=("angel",)),
    C("Angel of Suffering", "Creature", {"gen": 3, "B": 2}, 5, 3,
      priority=5, threat=6.5),
    C("Requiem Angel", "Creature", {"gen": 5, "W": 1}, 5, 5,
      priority=6.5, threat=7.0, tags=("angel",)),
    C("Emeria Shepherd", "Creature", {"gen": 5, "W": 2}, 4, 4,
      priority=6.5, threat=7.5, tags=("angel",), script="emeria_shepherd"),
    C("Sun Titan", "Creature", {"gen": 4, "W": 2}, 6, 6,
      priority=6.5, threat=7.5, script="sun_titan"),
    C("Angel of Despair", "Creature", {"gen": 3, "W": 2, "B": 2}, 5, 5,
      priority=5.5, threat=7.5, tags=("angel",)),
    C("Angel of the Ruins", "Artifact/Creature", {"gen": 5, "W": 2}, 5, 7,
      priority=5, threat=7.0, tags=("angel",)),
    C("Angelic Arbiter", "Creature", {"gen": 5, "W": 2}, 5, 6,
      priority=5.5, threat=8.0, tags=("angel",)),
    C("Twilight Shepherd", "Creature", {"gen": 3, "W": 3}, 5, 5,
      priority=5, threat=7.0, tags=("angel",)),
    C("Herald of War", "Creature", {"gen": 3, "W": 2}, 3, 3,
      priority=5.5, threat=6.0, tags=("angel",)),
]

# ---------------------------------------------------------------------------
# Support creatures — 12
# ---------------------------------------------------------------------------
SUPPORT = [
    C("Resplendent Angel", "Creature", {"gen": 1, "W": 2}, 3, 3,
      priority=8, threat=7.0, tags=("angel",)),
    C("Righteous Valkyrie", "Creature", {"gen": 2, "W": 1}, 2, 4,
      priority=8, threat=6.5, tags=("angel", "cleric")),
    C("Giada, Font of Hope", "Creature", {"gen": 1, "W": 1}, 2, 2,
      priority=7.5, threat=6.0, tags=("angel",)),
    C("Bloodghast", "Creature", {"B": 2}, 2, 1, priority=4, threat=4.0),
    C("Speaker of the Heavens", "Creature", {"W": 1}, 1, 1,
      priority=6, threat=4.0, tags=("cleric",), lifelink=True),
    C("Pitiless Plunderer", "Creature", {"gen": 3, "B": 1}, 1, 4,
      priority=7, threat=5.5),
    C("Blood Artist", "Creature", {"gen": 1, "B": 1}, 0, 1,
      priority=7.5, threat=6.0),
    C("Zulaport Cutthroat", "Creature", {"gen": 1, "B": 1}, 1, 1,
      priority=7.5, threat=6.0),
    C("Bishop of Wings", "Creature", {"W": 2}, 1, 4,
      priority=6.5, threat=5.0),
    C("Youthful Valkyrie", "Creature", {"gen": 1, "W": 1}, 1, 3,
      priority=5.5, threat=4.5, tags=("angel",)),
    C("Viscera Seer", "Creature", {"B": 1}, 1, 1, priority=7, threat=4.0),
    C("Cartel Aristocrat", "Creature", {"W": 1, "B": 1}, 2, 2,
      priority=6.5, threat=5.0),
    C("Priest of Fell Rites", "Creature", {"W": 1, "B": 1}, 2, 2,
      priority=6, threat=5.0),
    C("Voldaren Bloodcaster // Bloodbat Summoner", "Creature",
      {"gen": 1, "B": 1}, 2, 1, priority=6.5, threat=5.0),
]

# ---------------------------------------------------------------------------
# Top-deck / draw engines — 6
# ---------------------------------------------------------------------------
DRAW_ENGINES = [
    C("Black Market Connections", "Enchantment", {"gen": 2, "B": 1},
      priority=8, threat=6.5),
    C("Phyrexian Arena", "Enchantment", {"gen": 1, "B": 2},
      priority=7.5, threat=6.0),
    C("Midnight Reaper", "Creature", {"gen": 2, "B": 1}, 3, 2,
      priority=7, threat=6.0),
    C("Grim Haruspex", "Creature", {"gen": 2, "B": 1}, 3, 2,
      priority=7, threat=6.0),
    C("Dark Prophecy", "Enchantment", {"B": 3}, priority=6.5, threat=6.5),
    # "Equipment" is a subtype, not a card type -- the printed type line is
    # just Artifact.
    C("Skullclamp", "Artifact", {"gen": 1}, priority=7, threat=5.0),
    C("Vampiric Rites", "Enchantment", {"B": 1}, priority=6.5, threat=4.0),
]

# ---------------------------------------------------------------------------
# Cross-turn mana (Treasures) — 4
# ---------------------------------------------------------------------------
TREASURE = [
    C("Smothering Tithe", "Enchantment", {"gen": 3, "W": 1},
      priority=9, threat=7.5),
    C("Revel in Riches", "Enchantment", {"gen": 4, "B": 1},
      priority=5, threat=5.5),
]

# ---------------------------------------------------------------------------
# Mana accelerants — 7
# ---------------------------------------------------------------------------
ROCKS = [
    C("Sol Ring", "Artifact", {"gen": 1}, priority=10, threat=4.0, mana=(2, "C")),
    C("Arcane Signet", "Artifact", {"gen": 2}, priority=9, mana=(1, "WB")),
    C("Orzhov Signet", "Artifact", {"gen": 2}, priority=8.5, mana=(1, "WB")),
    C("Fellwar Stone", "Artifact", {"gen": 2}, priority=8, mana=(1, "WB")),
    C("Mind Stone", "Artifact", {"gen": 2}, priority=7.5, mana=(1, "C")),
    C("Marble Diamond", "Artifact", {"gen": 2}, priority=8, mana=(1, "W"),
      tapped=True),
    C("Talisman of Hierarchy", "Artifact", {"gen": 2}, priority=8, mana=(1, "WB")),
    C("Wayfarer's Bauble", "Artifact", {"gen": 1}, priority=6, threat=3.0),
]

# ---------------------------------------------------------------------------
# Interaction & protection — 14 (all MODEL-BLIND except the two protection
# spells and the two wraths; opponents' boards are a blocker count, so
# targeted removal has nothing to remove — same limitation as every other
# deck in this project)
# ---------------------------------------------------------------------------
INTERACTION = [
    C("Damn", "Sorcery", {"B": 2}, priority=3, tags=("wipe",)),
    C("Wrath of God", "Sorcery", {"gen": 2, "W": 2}, priority=3, tags=("wipe",)),
    C("Flawless Maneuver", "Instant", {"gen": 2, "W": 1}, priority=2, threat=4.0),
    C("Teferi's Protection", "Instant", {"gen": 2, "W": 1}, priority=2, threat=6.0),
    C("Path to Exile", "Instant", {"W": 1}, priority=3),
    C("Swords to Plowshares", "Instant", {"W": 1}, priority=3),
    C("Anguished Unmaking", "Instant", {"gen": 1, "W": 1, "B": 1}, priority=3),
    C("Generous Gift", "Instant", {"gen": 2, "W": 1}, priority=3),
    C("Despark", "Instant", {"W": 1, "B": 1}, priority=3),
    C("Vindicate", "Sorcery", {"gen": 1, "W": 1, "B": 1}, priority=3),
    C("Mortify", "Instant", {"gen": 1, "W": 1, "B": 1}, priority=3),
    C("Utter End", "Instant", {"gen": 2, "W": 1, "B": 1}, priority=3),
]

# ---------------------------------------------------------------------------
# Lands / MDFC spells — 4 (the front-face spell; the back face is a land,
# wired through `land_face` so `engine.play_land` can play either half)
# ---------------------------------------------------------------------------
MDFC_SPELLS = [
    C("Agadeem's Awakening // Agadeem, the Undercrypt", "Sorcery",
      {"gen": 2, "B": 3}, priority=1, threat=6.0, x_pips=2,
      land_face=("B", True)),
    C("Emeria's Call // Emeria, Shattered Skyclave", "Sorcery",
      {"gen": 4, "W": 3}, priority=6, threat=6.5, script="emeria_call",
      land_face=("W", True)),
    C("Malakir Rebirth // Malakir Mire", "Instant", {"B": 1}, priority=2,
      land_face=("B", True)),
]

# ---------------------------------------------------------------------------
# Lands — 39 nonbasic + 13 basic = 52. Check lands / horizon lands / bond
# lands are modelled as plain untapped duals, the same simplification every
# other deck in this project makes for the same card shapes (see
# `karlov_v2.py`'s Concealed Courtyard / Isolated Chapel / Fetid Heath).
# ---------------------------------------------------------------------------
LANDS = (
    [L("Swamp", "B")] * 8 + [L("Plains", "W")] * 5 +
    [
        L("Bloodstained Mire", "B"),
        L("Phyrexian Tower", "C"),
        L("Marsh Flats", "WB"),
        L("Silent Clearing", "WB"),
        L("Godless Shrine", "WB"),
        L("Fetid Heath", "WB"),
        L("Concealed Courtyard", "WB"),
        L("Shattered Sanctum", "WB"),
        L("Isolated Chapel", "WB"),
        L("Vault of Champions", "WB"),
        L("Castle Locthwain", "B"),
        L("Vault of the Archangel", "C"),
        L("Caves of Koilos", "WBC"),
        L("Castle Ardenvale", "W"),
        L("Shineshadow Snarl", "WB"),
        L("Tainted Field", "WB"),
        L("High Market", "C"),
        L("Command Tower", "WB"),
        L("Orzhov Basilica", "WB", tapped=True, tags=("bounce",)),
        L("Bojuka Bog", "B", tapped=True),
        L("Reliquary Tower", "C"),
        L("Brightclimb Pathway // Grimclimb Pathway", "WB"),
    ]
)


def build():
    deck = (HAYMAKERS + SUPPORT + DRAW_ENGINES + TREASURE + ROCKS
           + INTERACTION + MDFC_SPELLS + LANDS)
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER
