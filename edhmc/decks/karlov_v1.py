"""
Karlov of the Ghost Council v1 — deck definition.

    Karlov of the Ghost Council  {1}{W}{B}  2/2
      Whenever you gain life, put two +1/+1 counters on Karlov.
      Remove six +1/+1 counters from Karlov: exile target creature.

Costs are hand-authored and were verified against Scryfall oracle text on
2026-09-03; see ORACLE_AUDIT_KARLOV.md.

NOTE: the spreadsheet previously "corrected" Damn and Fracture to MV 3. Both
are MV 2 ({B}{B} and {W}{B}); the correction was the error and has been undone
on both legs. Damn's wrath mode is its overload cost {2}{W}{W}, MV 4 — which is
neither 2 nor 3, and is why it is modelled as the removal spell it is cast as.
"""

from edhmc.engine import Card


def C(name, types, cost=None, p=0, t=0, script=None, priority=0.0, tags=(),
      threat=0.0, mana=None, lifegain=0.0, drain=0.0, lifelink=False, x_pips=0):
    ma = (mana[0], frozenset(mana[1])) if mana else None
    return Card(name=name, types=frozenset(types.split("/")), cost=cost or {},
                power=p, toughness=t, script=script, priority=priority,
                threat=threat, tags=frozenset(tags), mana_ability=ma,
                lifegain=lifegain, drain=drain, lifelink=lifelink, x_pips=x_pips)


def L(name, produces, tapped=False, types="Land", lifegain=0.0):
    return Card(name=name, types=frozenset(types.split("/")), is_land=True,
                produces=frozenset(produces), tapped=tapped, lifegain=lifegain)


COMMANDER = C("Karlov of the Ghost Council", "Creature",
              {"W": 1, "B": 1}, 2, 2, priority=10, threat=9.0)

CREATURES = [
    C("Soul Warden", "Creature", {"W": 1}, 1, 1, priority=9.5, threat=6.5),
    C("Soul's Attendant", "Creature", {"W": 1}, 1, 1, priority=9.5, threat=6.5),
    C("Soulmender", "Creature", {"W": 1}, 1, 1, priority=6, threat=4.0),
    C("Mother of Runes", "Creature", {"W": 1}, 1, 1, priority=8, threat=6.0),
    C("Serra Ascendant", "Creature", {"W": 1}, 1, 1, priority=8, threat=7.0,
      lifelink=True),
    C("Elas il-Kor, Sadistic Pilgrim", "Creature", {"W": 1, "B": 1}, 2, 2,
      priority=8, threat=7.0),
    C("Vizkopa Guildmage", "Creature", {"W": 1, "B": 1}, 2, 2, priority=8,
      threat=7.5),
    C("Blood Artist", "Creature", {"gen": 1, "B": 1}, 0, 1, priority=8, threat=7.0),
    C("Suture Priest", "Creature", {"gen": 1, "W": 1}, 1, 1, priority=8.5, threat=6.5),
    C("Auriok Champion", "Creature", {"W": 2}, 1, 1, priority=9, threat=7.0),
    # Daxos's toughness is his devotion to white, not a fixed 1. 4 is this
    # list's typical white devotion once the early drops are down.
    C("Daxos, Blessed by the Sun", "Enchantment/Creature", {"W": 2}, 2, 4,
      priority=8, threat=6.0),
    C("Voice of the Blessed", "Creature", {"W": 2}, 2, 2, priority=7,
      threat=7.0),
    C("Cliffhaven Vampire", "Creature", {"gen": 2, "W": 1, "B": 1}, 2, 4,
      priority=7.5, threat=7.5),
    C("Drana's Emissary", "Creature", {"gen": 1, "W": 1, "B": 1}, 2, 2,
      priority=7, threat=6.5),
    C("Marauding Blight-Priest", "Creature", {"gen": 2, "B": 1}, 3, 2,
      priority=7.5, threat=7.5),
    C("Kambal, Consul of Allocation", "Creature", {"gen": 1, "W": 1, "B": 1}, 2, 3,
      priority=7.5, threat=7.0),
    C("Lurrus of the Dream-Den", "Creature", {"gen": 1, "W": 1, "B": 1}, 3, 2,
      priority=6, threat=6.0, lifelink=True),
    C("Vito, Thorn of the Dusk Rose", "Creature", {"gen": 2, "B": 1}, 1, 3,
      priority=9, threat=8.5),
    C("Ranger of Eos", "Creature", {"gen": 3, "W": 1}, 3, 2, priority=6,
      threat=5.5, script="draw2"),
    C("Kalitas, Traitor of Ghet", "Creature", {"gen": 2, "B": 2}, 3, 4,
      priority=7, threat=7.5, lifelink=True),
    C("Sunscorch Regent", "Creature", {"gen": 3, "W": 2}, 4, 3, priority=6,
      threat=7.0),
    C("Archangel of Thune", "Creature", {"gen": 3, "W": 2}, 3, 4, priority=8.5,
      threat=8.5, lifelink=True),
    C("Syr Konrad, the Grim", "Creature", {"gen": 3, "B": 2}, 5, 4, priority=6,
      threat=7.0),
    C("Felidar Sovereign", "Creature", {"gen": 4, "W": 2}, 4, 6, priority=7,
      threat=8.0, lifelink=True),
    C("Sun Titan", "Creature", {"gen": 4, "W": 2}, 6, 6, priority=5, threat=7.0),
]

PLANESWALKERS = [
    C("Sorin, Solemn Visitor", "Planeswalker", {"gen": 2, "W": 1, "B": 1},
      priority=6, threat=7.0),
    C("Sorin, Vengeful Bloodlord", "Planeswalker", {"gen": 2, "W": 1, "B": 1},
      priority=7, threat=7.5),
]

ARTIFACTS = [
    C("Sensei's Divining Top", "Artifact", {"gen": 1}, priority=6, threat=5.5),
    C("Fountain of Renewal", "Artifact", {"gen": 1}, priority=7, threat=5.0),
    C("Sol Ring", "Artifact", {"gen": 1}, priority=10, threat=4.0, mana=(2, "C")),
    C("Orzhov Signet", "Artifact", {"gen": 2}, priority=8, mana=(1, "WBC")),
    C("Swiftfoot Boots", "Artifact", {"gen": 2}, priority=6, threat=4.5),
    C("Lightning Greaves", "Artifact", {"gen": 2}, priority=6, threat=4.5),
    C("Umezawa's Jitte", "Artifact", {"gen": 2}, priority=6, threat=7.0),
    C("Pristine Talisman", "Artifact", {"gen": 3}, priority=7, threat=5.0,
      mana=(1, "C"), lifegain=0),
    C("Whispersilk Cloak", "Artifact", {"gen": 3}, priority=5, threat=4.5),
    C("Cosmos Elixir", "Artifact", {"gen": 4}, priority=6, threat=6.0),
    C("Well of Lost Dreams", "Artifact", {"gen": 4}, priority=7.5, threat=7.5),
    C("Aetherflux Reservoir", "Artifact", {"gen": 4}, priority=7, threat=8.5),
]

ENCHANTMENTS = [
    C("Phyrexian Reclamation", "Enchantment", {"B": 1}, priority=5, threat=4.5),
    C("Authority of the Consuls", "Enchantment", {"W": 1}, priority=8, threat=6.0),
    C("Land Tax", "Enchantment", {"W": 1}, priority=7, threat=5.5),
    C("Dawn of Hope", "Enchantment", {"gen": 1, "W": 1}, priority=6.5, threat=6.0),
    C("Ajani's Mantra", "Enchantment", {"gen": 1, "W": 1}, priority=7, threat=4.5),
    C("Blind Obedience", "Enchantment", {"gen": 1, "W": 1}, priority=7.5, threat=6.0),
    C("Necropotence", "Enchantment", {"B": 3}, priority=8, threat=8.0,
      script="draw2"),
    C("Phyrexian Arena", "Enchantment", {"gen": 1, "B": 2}, priority=7, threat=6.5),
    C("Exquisite Blood", "Enchantment", {"gen": 4, "B": 1}, priority=9.5, threat=9.0),
    C("Sanguine Bond", "Enchantment", {"gen": 3, "B": 2}, priority=9.5, threat=9.0),
]

SPELLS = [
    C("Swords to Plowshares", "Instant", {"W": 1}, priority=3),
    C("Path to Exile", "Instant", {"W": 1}, priority=3),
    C("Enlightened Tutor", "Instant", {"W": 1}, priority=6),
    C("Anguished Unmaking", "Instant", {"gen": 1, "W": 1, "B": 1}, priority=3),
    C("Benevolent Offering", "Instant", {"gen": 3, "W": 1}, priority=4,
      lifegain=4),
    C("Fracture", "Instant", {"W": 1, "B": 1}, priority=3),
    C("Return to Dust", "Instant", {"gen": 2, "W": 2}, priority=3),
    # {B}{B} as cast; the wrath is its overload cost {2}{W}{W}, not modelled.
    C("Damn", "Sorcery", {"B": 2}, priority=3, tags=("wipe",)),
    C("Toxic Deluge", "Sorcery", {"gen": 2, "B": 1}, priority=3, tags=("wipe",)),
    # {X}{W}{W}{B}{B} with X=3, so gen:3 IS the X and each opponent loses 2X=6.
    C("Debt to the Deathless", "Sorcery", {"gen": 3, "W": 2, "B": 2},
      priority=7, threat=8.0, script="debt", x_pips=3),
    C("Austere Command", "Sorcery", {"gen": 4, "W": 2}, priority=3, tags=("wipe",)),
    C("Farewell", "Sorcery", {"gen": 4, "W": 2}, priority=3, tags=("wipe",)),
    C("Damnation", "Sorcery", {"gen": 2, "B": 2}, priority=3, tags=("wipe",)),
]

LANDS = (
    [L("Plains", "W")] * 7 + [L("Swamp", "B")] * 11 +
    [
        L("Barren Moor", "B", tapped=True),
        L("Radiant Fountain", "C", lifegain=2),
        L("Tainted Field", "WB"),
        L("Secluded Steppe", "W", tapped=True),
        L("Opal Palace", "C"),
        L("Cavern of Souls", "WB"),
        L("Rogue's Passage", "C"),
        L("Temple of the False God", "C"),
        L("Caves of Koilos", "WBC"),
        L("Command Tower", "WB"),
        L("Bojuka Bog", "B", tapped=True),
        L("Reliquary Tower", "C"),
        L("Temple of Silence", "WB", tapped=True),
        L("Vault of the Archangel", "C"),
        L("Concealed Courtyard", "WB"),
        L("Isolated Chapel", "WB"),
        L("Fetid Heath", "WB"),
        L("Shizo, Death's Storehouse", "B"),
        L("Godless Shrine", "WB"),
    ]
)


def build():
    deck = CREATURES + PLANESWALKERS + ARTIFACTS + ENCHANTMENTS + SPELLS + LANDS
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER
