"""
Rendmaw, Creaking Nest v12 — deck definition.

Costs are hand-authored (the spreadsheet only stores mana *value*, which cannot
express colour screw — and colour screw is exactly the kind of thing a Monte
Carlo run is good at surfacing). Format:

    C(name, "types", cost, power, toughness, script=..., priority=..., tags=...)

cost keys: "gen" generic, plus W/U/B/R/G/C for coloured/true-colourless pips.
priority: casting preference when several spells are affordable (higher first).
"""

from edhmc.engine import Card


def C(name, types, cost=None, p=0, t=0, script=None, priority=0.0, tags=(),
      threat=0.0, mana=None, pod_damage=0.0, land_face=(), x_pips=0,
      alt_costs=(), lifelink=False):
    """mana: (amount, "BGC") if the permanent taps for mana.
    pod_damage: drain/burn dealt across the three opponents.
    threat: how badly opponents want it dead (0 = derive from power/MV).

    This is the knob that decides what eats the pod's removal. Anything that
    would make a table say "we have to deal with that" belongs above ~7.
    """
    ma = (mana[0], frozenset(mana[1])) if mana else None
    return Card(name=name,
                types=frozenset(types.split("/")),
                cost=cost or {},
                power=p, toughness=t,
                script=script, priority=priority, mana_ability=ma,
                threat=threat, tags=frozenset(tags), pod_damage=pod_damage,
                land_face=land_face, x_pips=x_pips,
                alt_costs=alt_costs, lifelink=lifelink)


def L(name, produces, tapped=False, types="Land", script=None, tags=(), p=0, t=0):
    return Card(name=name, types=frozenset(types.split("/")),
                is_land=True, produces=frozenset(produces),
                tapped=tapped, script=script, tags=frozenset(tags), power=p, toughness=t)


COMMANDER = C("Rendmaw, Creaking Nest", "Artifact/Creature",
              {"gen": 3, "B": 1, "G": 1}, 5, 5, priority=9, threat=9.0)

# --------------------------------------------------------------------------
# Nonland cards (63)
# --------------------------------------------------------------------------
NONLANDS = [
    # --- mana ---
    C("Sol Ring", "Artifact", {"gen": 1}, priority=10, tags=("ramp",), threat=4.0, mana=(2, "C")),
    C("Arcane Signet", "Artifact", {"gen": 2}, priority=8, tags=("ramp",), mana=(1, "BGC")),
    C("Golgari Signet", "Artifact", {"gen": 2}, priority=8, tags=("ramp",), mana=(1, "BGC")),
    C("Copper Myr", "Artifact/Creature", {"gen": 2}, 1, 1, priority=7, tags=("ramp",), mana=(1, "G")),
    C("Leaden Myr", "Artifact/Creature", {"gen": 2}, 1, 1, priority=7, tags=("ramp",), mana=(1, "B")),
    C("Palladium Myr", "Artifact/Creature", {"gen": 3}, 2, 2, priority=7, tags=("ramp",), mana=(2, "C")),
    C("Ornithopter of Paradise", "Artifact/Creature", {"gen": 2}, 0, 2, priority=7, tags=("ramp",), mana=(1, "BGC")),
    # Taps for one mana of ANY colour, not just colourless.
    C("Twitching Doll", "Artifact/Creature", {"gen": 1, "G": 1}, 2, 2, priority=6, tags=("ramp",), mana=(1, "BGC")),
    C("Dryad of the Ilysian Grove", "Enchantment/Creature", {"gen": 2, "G": 1}, 2, 4,
      priority=9, tags=("ramp",), threat=5.5),
    C("Sakura-Tribe Elder", "Creature", {"gen": 1, "G": 1}, 1, 1, priority=5, tags=("ramp",)),
    C("Burnished Hart", "Artifact/Creature", {"gen": 3}, 2, 2, priority=5, tags=("ramp",)),
    C("Solemn Simulacrum", "Artifact/Creature", {"gen": 4}, 2, 2, script="draw1", priority=5,
      tags=("ramp",)),
    C("Overlord of the Hauntwoods", "Enchantment/Creature", {"gen": 3, "G": 2}, 6, 5,
      script="overlord", priority=7, tags=("ramp",), threat=7.5,
      alt_costs=(({"gen": 1, "G": 2}, "impending"),)),
    C("Enduring Vitality", "Enchantment/Creature", {"gen": 1, "G": 2}, 3, 3,
      priority=8, tags=("ramp",), threat=7.0),
    C("The Great Henge", "Artifact", {"gen": 7, "G": 2}, priority=8, tags=("ramp",), threat=9.5),

    # --- token engines ---
    C("Bitterblossom", "Kindred/Enchantment", {"gen": 1, "B": 1}, script="bitterblossom",
      priority=9, threat=6.5),
    C("Ophiomancer", "Creature", {"gen": 2, "B": 1}, 2, 2, script="ophiomancer", priority=8, threat=5.5),
    C("Tendershoot Dryad", "Creature", {"gen": 4, "G": 1}, 2, 2, script="tendershoot", priority=6, threat=6.5),
    C("Grist, the Hunger Tide", "Planeswalker/Creature", {"gen": 1, "B": 1, "G": 1},
      script="grist", priority=8, threat=6.5),
    C("Grave Titan", "Creature", {"gen": 4, "B": 2}, 6, 6, script="grave_titan", priority=7, threat=8.5),
    C("Arasta of the Endless Web", "Enchantment/Creature", {"gen": 2, "G": 2}, 3, 5, priority=5, threat=4.0),
    C("Filigree Familiar", "Artifact/Creature", {"gen": 3}, 2, 2, priority=4),
    C("Woe Strider", "Creature", {"gen": 2, "B": 1}, 3, 2, script="woe_strider", priority=5),
    C("Dockside Chef", "Enchantment/Creature", {"B": 1}, 1, 2, priority=5),

    # --- token payoffs / anthems ---
    # Creatures you control have base P/T 6/6 and are Oozes. The Elephant
    # trigger ("whenever an opponent casts a spell, if it's not their turn")
    # is still unmodelled — KNOWN_ISSUES 1a — so its numbers are a floor.
    C("March of the World Ooze", "Enchantment", {"gen": 3, "G": 3},
      priority=8, tags=("pump",), threat=9.0),
    C("Metallic Mimic", "Artifact/Creature", {"gen": 2}, 2, 1, priority=7, threat=5.0),
    C("Idol of Oblivion", "Artifact", {"gen": 2}, priority=7, threat=5.0),
    C("Primal Vigor", "Enchantment", {"gen": 4, "G": 1}, priority=7, threat=8.5),
    C("Ohran Frostfang", "Creature", {"gen": 3, "G": 2}, 2, 6, priority=7, threat=7.0),
    C("Verdurous Gearhulk", "Artifact/Creature", {"gen": 3, "G": 2}, 4, 4,
      script="gearhulk", priority=6, tags=("pump",)),
    C("Beastmaster Ascension", "Enchantment", {"gen": 2, "G": 1}, priority=4, tags=("pump",), threat=6.0),
    C("Coat of Arms", "Artifact", {"gen": 5}, priority=5, tags=("pump",), threat=8.0),
    C("Overwhelming Stampede", "Sorcery", {"gen": 3, "G": 2}, priority=6,
      tags=("pump",), script="stampede"),
    C("Steel Overseer", "Artifact/Creature", {"gen": 2}, 1, 1, priority=6, threat=5.5),
    C("Roaming Throne", "Artifact/Creature", {"gen": 4}, 4, 4, priority=8, threat=6.0),

    # --- aristocrats / draw ---
    C("Blood Artist", "Creature", {"gen": 1, "B": 1}, 0, 1, priority=6, threat=5.5),
    C("Erebos, Bleak-Hearted", "Enchantment/Creature", {"gen": 3, "B": 1}, 5, 6, priority=6, threat=6.0),
    C("The Meathook Massacre", "Enchantment", {"gen": 2, "B": 2}, priority=4, threat=6.5,
      x_pips=2),
    C("Midnight Reaper", "Creature", {"gen": 2, "B": 1}, 3, 2, priority=5, threat=4.5),
    C("Deathreap Ritual", "Enchantment", {"gen": 2, "B": 1, "G": 1}, priority=5, threat=4.5),
    C("Whip of Erebos", "Artifact/Enchantment", {"gen": 2, "B": 2}, priority=4, threat=5.0),
    C("Village Rites", "Instant", {"B": 1}, priority=1),
    C("Reap", "Instant", {"gen": 1, "G": 1}, priority=1),
    C("Shigeki, Jukai Visionary", "Enchantment/Creature", {"gen": 1, "G": 1}, 1, 3, priority=5),
    C("Gloomshrieker", "Enchantment/Creature", {"gen": 1, "B": 1, "G": 1}, 2, 1, priority=5),
    C("Pygmy Kavu", "Creature", {"gen": 3, "G": 1}, 1, 2, priority=2),
    C("Ashnod's Altar", "Artifact", {"gen": 3}, priority=5, threat=4.5),

    # --- artifacts matter ---
    C("Foundry Inspector", "Artifact/Creature", {"gen": 3}, 3, 2, priority=6),
    C("Junk Diver", "Artifact/Creature", {"gen": 3}, 1, 1, priority=4),
    C("Myr Retriever", "Artifact/Creature", {"gen": 2}, 1, 1, priority=4),
    C("Scrap Trawler", "Artifact/Creature", {"gen": 3}, 3, 2, priority=4),
    C("Biotransference", "Enchantment", {"gen": 2, "B": 2}, priority=5, threat=6.0),

    # --- interaction (goldfish: bodies + Rendmaw triggers only) ---
    C("Haywire Mite", "Artifact/Creature", {"gen": 1}, 1, 1, priority=3),
    C("Massacre Wurm", "Creature", {"gen": 3, "B": 3}, 6, 5, priority=4, threat=6.0, tags=("wipe", "onesided",)),
    C("Bow of Nylea", "Artifact/Enchantment", {"gen": 1, "G": 2}, priority=3),
    C("Lignify", "Kindred/Enchantment", {"gen": 1, "G": 1}, priority=2),
    C("Nameless Inversion", "Kindred/Instant", {"gen": 1, "B": 1}, priority=2),
    C("Assassin's Trophy", "Instant", {"B": 1, "G": 1}, priority=2),
    C("Beast Within", "Instant", {"gen": 2, "G": 1}, priority=2),
    # Kindred Instant — TWO card types, so it triggers Rendmaw.
    C("Eyeblight's Ending", "Kindred/Instant", {"gen": 2, "B": 1}, priority=2),
    C("Heroic Intervention", "Instant", {"gen": 1, "G": 1}, priority=2),
    C("Culling Ritual", "Sorcery", {"gen": 2, "B": 1, "G": 1}, priority=1, tags=("wipe",)),
    C("Toxic Deluge", "Sorcery", {"gen": 2, "B": 1}, priority=1, tags=("wipe",)),
    # MDFC: {2}{B}{B} instant on the front, Hagra Broodpit (tapped, taps for B)
    # on the back. The engine now plays whichever face it needs.
    C("Hagra Mauling", "Instant", {"gen": 2, "B": 2}, priority=2,
      land_face=("B", True)),
]

# --------------------------------------------------------------------------
# Lands (36)
# --------------------------------------------------------------------------
LANDS = (
    [L("Forest", "G")] * 7 +
    [L("Swamp", "B")] * 6 +
    [
        L("Command Tower", "BG"),
        L("Overgrown Tomb", "BG"),
        L("Llanowar Wastes", "BGC"),
        L("Darkbore Pathway", "BG"),
        L("Deathcap Glade", "BG"),
        L("Necroblossom Snarl", "BG"),
        L("Cavern of Souls", "BG"),
        L("Tainted Wood", "BG"),
        L("Golgari Rot Farm", "BG", tapped=True, tags=("bounce",)),
        L("Woodland Chasm", "BG", tapped=True),
        L("Darkmoss Bridge", "BG", tapped=True, types="Artifact/Land"),
        L("Bojuka Bog", "B", tapped=True),
        L("Witch's Cottage", "B", tapped=True),
        L("Castle Locthwain", "B"),
        L("Khalni Garden", "G", tapped=True, script="khalni_garden"),
        L("Grim Backwoods", "C"),
        L("High Market", "C"),
        L("Darksteel Citadel", "C", types="Artifact/Land"),
        L("Treasure Vault", "C", types="Artifact/Land"),
        L("Vault of Whispers", "B", types="Artifact/Land"),
        L("Tree of Tales", "G", types="Artifact/Land"),
        L("Dryad Arbor", "G", types="Land/Creature", p=1, t=1),
    ]
)


def build():
    deck = [c for c in NONLANDS] + [c for c in LANDS]
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER


# --------------------------------------------------------------------------
# The candidate swap
# --------------------------------------------------------------------------
NOXIOUS_GEARHULK = C("Noxious Gearhulk", "Artifact/Creature",
                     {"gen": 4, "B": 2}, 5, 4, priority=6, threat=7.0)
# Artifact Creature -> 2 card types -> triggers Rendmaw. ETB removal is not
# modelled (opponents' boards are a blocker count).

BABA_LYSAGA = C("Baba Lysaga, Night Witch", "Creature",
                {"gen": 1, "B": 1, "G": 1}, 3, 3, priority=8, threat=7.5,
                script="baba")
# {T}, Sac up to three permanents: if 3+ CARD TYPES among them, each opponent
# loses 3, gain 3, draw 3. This deck is built out of multi-type permanents.

EZURIS_PREDATION = C("Ezuri's Predation", "Sorcery", {"gen": 5, "G": 3},
                     priority=6, threat=8.0, script="predation")

MARCH_OF_THE_WORLD_OOZE = C("March of the World Ooze", "Enchantment",
                            {"gen": 3, "G": 3}, priority=8, tags=("pump",), threat=9.0)
# In the deck as of v12. Kept here so run_swap.py still resolves.

# Cut in v12, kept so validate.py can still measure CRN on the same real
# comparison it always has (now run in the other direction: March -> Clamp).
SKULLCLAMP = C("Skullclamp", "Artifact", {"gen": 1}, priority=9, threat=2.5)


# ---------------------------------------------------------------------------
# 2026-09-04 candidates
# ---------------------------------------------------------------------------
# "Whenever a creature you control dies, each opponent loses 1 life and you
# gain 1 life." — a Meathook Massacre drain half on a 3-mana artifact, plus
# "{1}{B}{G}, {T}, Sacrifice a creature: return target creature card from your
# graveyard to the battlefield. Activate only as a sorcery."
# ONE card type, so it does NOT trigger Rendmaw.
CAULDRON_OF_ESSENCE = C("Cauldron of Essence", "Artifact",
                        {"gen": 1, "B": 1, "G": 1}, priority=7, threat=6.5)

# MDFC. Front: {B/G} instant, "+1/+1 counter on target creature, it gains
# indestructible until end of turn". Back: Old-Growth Grove, a tapped BG land.
# The hybrid pip is expressed as {B} with a {G} alternative cost, which is what
# hybrid actually is for a payment solver. One card type on the front face, so
# no Rendmaw trigger.
REVITALIZING_REPAST = C("Revitalizing Repast", "Instant", {"B": 1},
                        priority=2, script="repast",
                        alt_costs=(({"G": 1}, "hybrid"),),
                        land_face=("BG", True))

# {6} 6/6 deathtouch lifelink; dies -> a 3/3 deathtouch Wurm and a 3/3 lifelink
# Wurm. Artifact Creature = TWO card types, so it triggers Rendmaw.
# Deathtouch is not modelled (this engine only prices it for Ohran Frostfang,
# as a blocker deterrent), so this is a floor.
WURMCOIL_ENGINE = C("Wurmcoil Engine", "Artifact/Creature", {"gen": 6}, 6, 6,
                    priority=7, threat=8.0, lifelink=True)
