"""
Tivit, Seller of Secrets v1 — deck definition.

    Tivit, Seller of Secrets  {3}{W}{U}{B}  6/6 Sphinx Rogue, flying, ward {3}
      Council's dilemma — Whenever Tivit enters OR DEALS COMBAT DAMAGE TO A
      PLAYER, starting with you, each player votes for evidence or bribery.
      For each evidence vote, investigate. For each bribery vote, create a
      Treasure token.
      While voting, you may vote an additional time.

THE COMMANDER'S DILEMMA HAS NO BAD OUTCOME. Both halves make an artifact, so
an adversarial pod cannot vote to deny you — they only choose WHICH artifact.
That is unusual and it is why the vote model below can be pessimistic about
opponents without making the deck look bad: pessimism costs Tivit nothing and
costs the *will of the council* cards a great deal.

Costs, types, power/toughness and colour identity were generated directly from
Scryfall (see build_tivit_xlsx.py, which builds the .xlsx from the same fetch)
and are checked by `python audit_cards.py`. Nothing here is hand-typed from
memory.

The deck's engine is artifacts: Tivit makes them, Academy Manufactor triples
them, Treasures pay for blinks that make more, and Time Sieve turns five of
them into an extra turn. See edhmc/tivit.py.
"""

from edhmc.engine import Card
from edhmc.decks._evasion import FLYING


def C(name, types, cost=None, p=0, t=0, script=None, priority=0.0, tags=(),
      threat=0.0, mana=None, treasures=0, x_pips=0, haste=False,
      land_face=()):
    """mana: (amount, "WUBC") if the permanent taps for mana.
    tags: "vote" marks a card that CASTS a vote — the Dashboard category and
    the engine's vote hook agree on that set."""
    ma = (mana[0], frozenset(mana[1])) if mana else None
    return Card(name=name, types=frozenset(types.split("/")), cost=cost or {},
                power=p, toughness=t, script=script, priority=priority,
                threat=threat, tags=frozenset(tags), mana_ability=ma,
                treasures=treasures, x_pips=x_pips, haste=haste,
                land_face=land_face, flying=name in FLYING)


def L(name, produces, tapped=False, types="Land", tags=(), script=None):
    """tags: "artifact_land" is what Time Sieve, Disciple of the Vault and
    Marionette Master actually read — an artifact that happens to be a land.
    The type line carries it too, but the engine's artifact count is a tag
    lookup, so both must agree."""
    return Card(name=name, types=frozenset(types.split("/")), is_land=True,
                produces=frozenset(produces), tapped=tapped,
                tags=frozenset(tags), script=script)


COMMANDER = C("Tivit, Seller of Secrets", "Creature",
              {"gen": 3, "W": 1, "U": 1, "B": 1}, 6, 6,
              priority=10, threat=9.5, script="tivit")

# ---------------------------------------------------------------------------
# Voting & Council's Dilemma (19)
# ---------------------------------------------------------------------------
VOTING = [
    # "You choose how each player votes this turn. Draw a card." Total control
    # of one vote — including Tivit's, though Tivit's is already all upside.
    C("Illusion of Choice", "Instant", {"U": 1}, priority=6, threat=5.0,
      script="illusion", tags=("vote_control",)),
    # "Whenever players finish voting, each opponent who voted for a choice you
    # didn't vote for loses 2 life."
    C("Grudge Keeper", "Creature", {"gen": 1, "B": 1}, 2, 1,
      priority=7, threat=6.5, tags=("vote_payoff",)),
    C("Split Decision", "Instant", {"gen": 1, "U": 1}, priority=4, threat=4.0,
      script="split_decision", tags=("vote",)),
    # {1}{B}: each opponent sacrifices a creature, or each loses 4 life.
    C("Tyrant's Choice", "Sorcery", {"gen": 1, "B": 1}, priority=5,
      script="tyrants_choice", tags=("vote",)),
    # "While voting, you may vote an additional time."
    C("Ballot Broker", "Creature", {"gen": 2, "W": 1}, 2, 3, priority=8,
      threat=6.0, tags=("extra_vote",)),
    # "While voting, you get an additional vote."
    C("Brago's Representative", "Creature", {"gen": 2, "W": 1}, 1, 4,
      priority=8, threat=6.0, tags=("extra_vote",)),
    C("Tempt with Bunnies", "Sorcery", {"gen": 2, "W": 1}, priority=5,
      threat=5.0, script="tempt_bunnies", tags=("vote",)),
    C("Trial of a Time Lord", "Enchantment", {"gen": 1, "W": 2}, priority=5,
      threat=6.0, script="trial", tags=("vote",)),
    C("Bite of the Black Rose", "Sorcery", {"gen": 3, "B": 1}, priority=4,
      script="bite", tags=("vote",)),
    # "At the beginning of your upkeep ... draw a card, or destroy all nonland
    # permanents." With vote control it draws until you want the wrath.
    C("Coercive Portal", "Artifact", {"gen": 4}, priority=6, threat=6.5,
      script="coercive_portal", tags=("vote",)),
    C("Master of Ceremonies", "Creature", {"gen": 3, "W": 1}, 3, 4,
      priority=7.5, threat=7.0, script="master_of_ceremonies"),
    C("Plea for Power", "Sorcery", {"gen": 3, "U": 1}, priority=7, threat=7.0,
      script="plea", tags=("vote",)),
    C("Tempting Contract", "Artifact", {"gen": 4}, priority=6.5, threat=6.0,
      script="tempting_contract"),
    C("Vault 11: Voter's Dilemma", "Enchantment", {"gen": 2, "W": 1, "B": 1},
      priority=5, threat=6.0, script="vault11", tags=("vote",)),
    C("Custodi Squire", "Creature", {"gen": 4, "W": 1}, 3, 3, priority=5,
      threat=5.0, script="custodi", tags=("vote",)),
    C("Lieutenants of the Guard", "Creature", {"gen": 4, "W": 1}, 2, 2,
      priority=4.5, threat=5.0, script="lieutenants", tags=("vote",)),
    C("Messenger Jays", "Creature", {"gen": 4, "U": 1}, 2, 1, priority=4.5,
      threat=4.5, script="jays", tags=("vote",)),
    C("Capital Punishment", "Sorcery", {"gen": 4, "B": 2}, priority=4,
      script="capital_punishment", tags=("vote",)),
    # The top end: an extra turn per time vote, steal a permanent per money
    # vote. Tivit's second vote makes it lopsided.
    C("Expropriate", "Sorcery", {"gen": 7, "U": 2}, priority=7.5, threat=9.5,
      script="expropriate", tags=("vote",)),
]

# ---------------------------------------------------------------------------
# Blink & Reuse (6) — the engine that turns one dilemma into many
# ---------------------------------------------------------------------------
BLINK = [
    # "Exile target creature you control, then return it." REBOUND casts it a
    # second time from exile on your next upkeep, so one {W} is two dilemmas.
    C("Ephemerate", "Instant", {"W": 1}, priority=8, script="ephemerate",
      tags=("blink",)),
    C("Soulherder", "Creature", {"gen": 1, "W": 1, "U": 1}, 1, 1,
      priority=9, threat=7.5, script="soulherder", tags=("blink",)),
    # "Whenever you cast a NONCREATURE spell, exile up to one target nonland
    # permanent you control, then return it." A dilemma per noncreature spell.
    C("Displacer Kitten", "Creature", {"gen": 3, "U": 1}, 2, 2, priority=9,
      threat=8.0, script="kitten", tags=("blink",)),
    # End-step blink of an ARTIFACT or creature, so it also rebuys Tamiyo's
    # Journal and Coercive Portal.
    C("Teleportation Circle", "Enchantment", {"gen": 3, "W": 1}, priority=7.5,
      threat=6.5, script="teleport_circle", tags=("blink",)),
    C("Conjurer's Closet", "Artifact", {"gen": 5}, priority=7, threat=6.0,
      script="closet", tags=("blink",)),
    # Soulbond to Tivit: {1}{U} per dilemma, repeatable. With Academy
    # Manufactor a blink makes five Treasures for two mana, which is the
    # deck's actual infinite.
    C("Deadeye Navigator", "Creature", {"gen": 4, "U": 2}, 5, 5, priority=9.5,
      threat=8.5, script="deadeye", tags=("blink",)),
]

# ---------------------------------------------------------------------------
# Token & Artifact Payoffs (10)
# ---------------------------------------------------------------------------
PAYOFFS = [
    C("Disciple of the Vault", "Creature", {"B": 1}, 1, 1, priority=7,
      threat=6.5, tags=("artifact_drain",)),
    # {T}, sac five artifacts: take an extra turn.
    C("Time Sieve", "Artifact", {"U": 1, "B": 1}, priority=9, threat=8.5,
      script="time_sieve"),
    # "If you would create a Clue, Food, or Treasure token, instead create one
    # of each." Triples every token this deck makes.
    C("Academy Manufactor", "Artifact/Creature", {"gen": 3}, 1, 3,
      priority=9.5, threat=8.0),
    C("Kambal, Profiteering Mayor", "Creature",
      {"gen": 1, "W": 1, "B": 1}, 2, 4, priority=9, threat=8.0,
      tags=("token_drain",)),
    C("Nadier's Nightblade", "Creature", {"gen": 2, "B": 1}, 1, 3, priority=7,
      threat=6.5, tags=("token_leave_drain",)),
    C("Mechanized Production", "Enchantment", {"gen": 2, "U": 2}, priority=6,
      threat=7.5, script="mechanized"),
    C("Mirkwood Bats", "Creature", {"gen": 3, "B": 1}, 2, 3, priority=8,
      threat=7.5, tags=("token_drain", "token_leave_drain")),
    C("Revel in Riches", "Enchantment", {"gen": 4, "B": 1}, priority=7,
      threat=8.0, script="revel"),
    C("Cyberdrive Awakener", "Artifact/Creature", {"gen": 5, "U": 1}, 4, 4,
      priority=6, threat=7.5, script="cyberdrive"),
    # Fabricate 3, then each artifact leaving drains for its power.
    C("Marionette Master", "Creature", {"gen": 4, "B": 2}, 1, 3, priority=8,
      threat=8.0, script="marionette", tags=("artifact_drain",)),
]

# ---------------------------------------------------------------------------
# Card Advantage (4)
# ---------------------------------------------------------------------------
DRAW = [
    C("Demonic Tutor", "Sorcery", {"gen": 1, "B": 1}, priority=7,
      script="tutor"),
    C("Idyllic Tutor", "Sorcery", {"gen": 2, "W": 1}, priority=6,
      script="tutor_ench"),
    C("Rhystic Study", "Enchantment", {"gen": 2, "U": 1}, priority=9.5,
      threat=8.5, script="rhystic"),
    C("Tamiyo's Journal", "Artifact", {"gen": 5}, priority=6.5, threat=6.0,
      script="journal"),
]

# ---------------------------------------------------------------------------
# Ramp & Fixing (7)
# ---------------------------------------------------------------------------
RAMP = [
    C("Sol Ring", "Artifact", {"gen": 1}, priority=10, threat=4.0,
      mana=(2, "C"), tags=("ramp",)),
    C("Arcane Signet", "Artifact", {"gen": 2}, priority=8, mana=(1, "WUBC"),
      tags=("ramp",)),
    C("Azorius Signet", "Artifact", {"gen": 2}, priority=8, mana=(1, "WUC"),
      tags=("ramp",)),
    C("Dimir Signet", "Artifact", {"gen": 2}, priority=8, mana=(1, "UBC"),
      tags=("ramp",)),
    C("Orzhov Signet", "Artifact", {"gen": 2}, priority=8, mana=(1, "WBC"),
      tags=("ramp",)),
    C("Model of Unity", "Artifact", {"gen": 3}, priority=7, threat=5.0,
      mana=(1, "WUBC"), tags=("ramp", "vote_payoff")),
    C("Monologue Tax", "Enchantment", {"gen": 2, "W": 1}, priority=7.5,
      threat=6.0, script="monologue_tax", tags=("ramp",)),
]

# ---------------------------------------------------------------------------
# Removal & Interaction (15)
# ---------------------------------------------------------------------------
REMOVAL = [
    C("An Offer You Can't Refuse", "Instant", {"U": 1}, priority=2),
    C("Path to Exile", "Instant", {"W": 1}, priority=2),
    C("Swords to Plowshares", "Instant", {"W": 1}, priority=2),
    C("Counterspell", "Instant", {"U": 2}, priority=2),
    C("Damn", "Sorcery", {"B": 2}, priority=3, tags=("wipe",)),
    C("Dovin's Veto", "Instant", {"W": 1, "U": 1}, priority=2),
    C("Muddle the Mixture", "Instant", {"U": 2}, priority=2),
    # {X}{B}{B}; the X is real and is paid from Treasures. x_pips records how
    # much of `gen` stands in for X — here the modelled X is 6, which is what
    # a resolved Tivit plus Academy Manufactor can pay for.
    C("Torment of Hailfire", "Sorcery", {"gen": 6, "B": 2}, priority=8.5,
      threat=9.0, script="torment", x_pips=6),
    C("Council's Judgment", "Sorcery", {"gen": 1, "W": 2}, priority=3,
      tags=("vote",), script="councils_judgment"),
    C("Trap the Trespassers", "Instant", {"gen": 2, "U": 1}, priority=2,
      tags=("vote",)),
    C("Void Rend", "Instant", {"W": 1, "U": 1, "B": 1}, priority=2),
    C("Promise of Loyalty", "Sorcery", {"gen": 4, "W": 1}, priority=3,
      tags=("wipe",)),
    C("Sadistic Shell Game", "Sorcery", {"gen": 4, "B": 1}, priority=3,
      tags=("wipe", "onesided")),
    C("Farewell", "Sorcery", {"gen": 4, "W": 2}, priority=3, tags=("wipe",)),
    C("Magister of Worth", "Creature", {"gen": 4, "W": 1, "B": 1}, 4, 4,
      priority=4, threat=6.0, tags=("wipe", "onesided", "vote"),
      script="magister"),
]

# ---------------------------------------------------------------------------
# Protection & Taxation (3)
# ---------------------------------------------------------------------------
PROTECTION = [
    # Haste is real here: Tivit's SECOND dilemma is on combat damage, so
    # Greaves is a whole extra vote the turn Tivit lands.
    C("Lightning Greaves", "Artifact", {"gen": 2}, priority=8, threat=4.0,
      script="greaves"),
    C("Ghostly Prison", "Enchantment", {"gen": 2, "W": 1}, priority=6,
      threat=5.5, tags=("fog",)),
    C("Propaganda", "Enchantment", {"gen": 2, "U": 1}, priority=6, threat=5.5,
      tags=("fog",)),
]

# ---------------------------------------------------------------------------
# Lands (35)
# ---------------------------------------------------------------------------
LANDS = (
    [L("Plains", "W")] * 6 + [L("Island", "U")] * 5 + [L("Swamp", "B")] * 5 +
    [
        L("Command Tower", "WUB"),
        L("Arcane Sanctum", "WUB", tapped=True),
        L("Raffine's Tower", "WUB", tapped=True),
        L("Exotic Orchard", "WUB"),
        L("Godless Shrine", "WB"),
        L("Hallowed Fountain", "WU"),
        L("Watery Grave", "UB"),
        L("Prairie Stream", "WU"),
        L("Sunken Hollow", "UB"),
        L("Sea of Clouds", "WU"),
        L("Vault of Champions", "WB"),
        # ARTIFACT LANDS. They are live artifacts for Time Sieve, Disciple of
        # the Vault and Marionette Master, which is why they carry the tag as
        # well as the type line.
        L("Ancient Den", "W", types="Artifact/Land", tags=("artifact_land",)),
        L("Seat of the Synod", "U", types="Artifact/Land",
          tags=("artifact_land",)),
        L("Vault of Whispers", "B", types="Artifact/Land",
          tags=("artifact_land",)),
        L("Archway of Innovation", "U", tapped=True),
        # "{4}, {T}: Investigate." A Clue source that is also a land.
        L("Havengul Laboratory // Havengul Mystery", "BC",
          script="havengul"),
        L("Bojuka Bog", "B", tapped=True),
        L("Reliquary Tower", "C"),
        L("Rogue's Passage", "C", script="rogues_passage"),
    ]
)


def build():
    deck = (VOTING + BLINK + PAYOFFS + DRAW + RAMP + REMOVAL + PROTECTION
            + LANDS)
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER


# ---------------------------------------------------------------------------
# Candidates — not in the deck. Kept here so candidates.py can resolve them.
# ---------------------------------------------------------------------------
# {2}: "Whenever you create one or more tokens, create an additional token of
# each of those kinds." The second Academy Manufactor effect.
ANOINTED_PROCESSION = C("Anointed Procession", "Enchantment",
                        {"gen": 3, "W": 1}, priority=8.5, threat=7.5)
