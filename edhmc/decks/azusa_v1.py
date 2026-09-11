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
# Creatures / Planeswalkers — 26 as of 2026-09-10 (was 25: -1 Nissa,
# Worldwaker, +3 Greenwarden / Greensleeves / Springheart). Dryad Arbor is a
# land-creature and is
# listed in LANDS instead, matching the spreadsheet's own placement of it
# among the land count)
# ---------------------------------------------------------------------------
CREATURES = [
    # CUT 2026-09-10 for Springheart Nantuko: Nissa, Worldwaker was +0.0079
    # +-0.0025, the DEAREST of the four animation cuts, and the swap still
    # measured +0.0118 +-0.0035 (§0y, §0z1). Her PLANESWALKERS entry stays in
    # edhmc/azusa.py -- the back face of Nissa, Vastwood Seer is still in the
    # deck and still needs the loyalty machinery.
    #
    # ADDED 2026-09-10, all three measured as real swaps at N=15,000 (§0y):
    C("Ancient Greenwarden", "Creature", {"gen": 4, "G": 2}, 5, 7,
      priority=8.5, threat=8.5),
    C("Greensleeves, Maro-Sorcerer", "Creature", {"gen": 3, "G": 2}, 0, 0,
      priority=8.5, threat=8.5),
    C("Springheart Nantuko", "Creature/Enchantment", {"gen": 1, "G": 1}, 1, 1,
      priority=7.0, threat=5.0),
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
# Sorceries — 12 as of 2026-09-10 (was 14: -Rude Awakening, -Sylvan Awakening)
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
    # CUT 2026-09-10 for Ancient Greenwarden and Greensleeves respectively:
    #   Rude Awakening    +0.0061 +-0.0026, replaced at +0.0271 +-0.0042
    #   Sylvan Awakening  +0.0052 +-0.0018, replaced at +0.0277 +-0.0043
    # The whole land-animation pillar was measured as nearly a blank in §0s --
    # 9.24 marginal damage a game in a deck whose damage runs into the
    # thousands -- and §0y measured its replacement from the other side. The
    # `rude_awakening` and `sylvan_awakening` scripts stay in edhmc/azusa.py:
    # they are still exercised by diag_azusa_animation.py, which is the
    # evidence for this cut.
    C("Seek the Horizon", "Sorcery", {"gen": 3, "G": 1}, priority=6,
      threat=4.0, script="seek_horizon"),
    C("Sylvan Scrying", "Sorcery", {"gen": 1, "G": 1}, priority=5.5,
      threat=4.0),
]

# ---------------------------------------------------------------------------
# Lands — 41 as of 2026-09-10: 20 nonbasic utility lands (+Scene of the Crime),
# Dryad Arbor (a land AND a creature), and 20 Forest (was 21; Scene of the
# Crime took a Forest slot -- §0z3). See the module docstring on the
# 99-vs-100 count.
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
    # ADDED 2026-09-10 for a Forest, taking the Forest count 21 -> 20 (§0z3).
    # "{2}, Sacrifice this land: Draw a card" -- with NO {T} in that cost,
    # which is why it beat three otherwise-cheaper sacrifice lands: the
    # binding constraint on this deck's utility lands is the TAP, not the
    # mana. Recurs with Crucible of Worlds, Ramunap Excavator and now Ancient
    # Greenwarden, so it converts the land drops this deck cannot otherwise
    # spend into cards. It taps for {C} here; its second ability makes any
    # colour and is modelled as the one that matters in mono-green.
    L("Scene of the Crime", "C", tapped=True, types="Artifact/Land"),
] + [L("Forest", "G")] * 20


def build():
    deck = CREATURES + ARTIFACTS + ENCHANTMENTS + INSTANTS + SORCERIES + LANDS
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    return deck, COMMANDER


# ---------------------------------------------------------------------------
# CANDIDATE ADDITIONS — nine cards submitted 2026-09-09. NOT in the deck.
#
# Module-level constants, like every other deck's candidates, and that is
# load-bearing rather than stylistic: `audit_cards.py` and `tag_flying.py`
# discover cards by walking the UPPERCASE attributes of each `<deck>_v<N>.py`
# module (see decks/__init__.py). A candidate defined anywhere else is checked
# against Scryfall by nothing and tagged by nothing — which is §0c exactly,
# where two fliers were measured as ground creatures because `tag_flying.py`
# walked `build()` only. A first draft of these lived in a separate
# `azusa_candidates.py` and was silently unaudited for that reason.
#
# Costs, types and P/T verified against Scryfall 2026-09-09, and re-verified
# by `python -m tools.audit_cards` on every run.
#
# WHAT IS AND IS NOT MODELLED. Read this before quoting any number: three of
# the nine are partly or wholly unmodelled, and their figures are FLOORS or
# blanks rather than evaluations.
#
#   Greensleeves            FULL. Landfall -> 3/3 Badger, the Rampaging
#                           Baloths shape. */* reads the land count.
#   Ancient Greenwarden     FULL, and the most invasive: lands from the
#                           graveyard, a 5/7 reach body, and the LANDFALL
#                           DOUBLER — every payoff in `land_entered` runs
#                           twice, because "that ability triggers an
#                           additional time" is the card.
#   Cultivator Colossus     FULL. The ETB land-loop is a real loop, bounded
#                           by lands in hand.
#   Case of the Locked      MOSTLY. Extra land drop, and the seven-land solve
#     Hothouse              gating top-of-library LAND access, checked at end
#                           step as printed. FLOOR: casting creatures and
#                           enchantments off the top is NOT modelled.
#   Conduit of Worlds       PARTIAL, FLOOR. Lands from the graveyard is real;
#                           the {T} recast-a-permanent ability is not — it
#                           costs your whole turn's casting, which the greedy
#                           policy cannot represent honestly.
#   Walk-In Closet //       PARTIAL, FLOOR, and §1b in its purest form: a Room
#     Forgotten Cellar      has two halves and two costs, and `Card` holds
#                           one. Modelled as the {2}{G} half only. Cost is MV
#                           3, NOT the MV 8 Scryfall reports — Scryfall sums
#                           both halves of a split card and nobody pays 8.
#   Springheart Nantuko     HEAVILY SIMPLIFIED, FLOOR. Modelled as the
#                           unattached mode: landfall -> a 1/1 Insect.
#                           Bestow, and the pay-{1}{G}-to-COPY-the-enchanted-
#                           creature mode that is the actual card, need an
#                           attachment relation the engine does not have.
#                           DO NOT read its row as a verdict on the card.
#   Burgeoning              MODEL-BLIND. It triggers on an OPPONENT playing a
#                           land. Opponents here are a creature count, a life
#                           total and a clock; they own no lands and play
#                           none, so there is no event to trigger on.
#   Constant Mists          MODEL-BLIND. A recurring fog. The engine has no
#                           way to spend a card on defence: `incidental_
#                           damage` is a flat per-turn life subtraction and
#                           `resolve_clocks` is threat-weighted and never
#                           reads combat at all.
#
# Priorities are set against this deck's own scale: commander 10, Sol Ring
# 9.5, Lotus Cobra 9, Courser 8.5, Avenger 8, Craterhoof 7.5.
# ---------------------------------------------------------------------------

# */* equal to lands you control -- defined 0/0 on purpose, with
# azusa.DYNAMIC_PT_LANDS supplying the real figure at every call site.
# azusa.check_dynamic_pt_coverage() raises at import if these two facts ever
# disagree, because the failure mode is a silent 0/0 that dies on arrival.
# COMMITTED to the deck 2026-09-10 -- these three are in CREATURES above and
# Scene of the Crime is in LANDS. The constants are KEPT because the harnesses
# that measured them (run_azusa_animation_swap.py, run_azusa_draw.py) still
# reference them by name, the same reason rendmaw_v12 keeps SKULLCLAMP and
# MARCH_OF_THE_WORLD_OOZE. They are NO LONGER in CANDIDATES_MODELLED, so
# candidates.py will refuse to measure them as additions (§0o).
GREENSLEEVES = C("Greensleeves, Maro-Sorcerer", "Creature",
                 {"gen": 3, "G": 2}, 0, 0, priority=8.5, threat=8.5)

ANCIENT_GREENWARDEN = C("Ancient Greenwarden", "Creature",
                        {"gen": 4, "G": 2}, 5, 7, priority=8.5, threat=8.5)

CULTIVATOR_COLOSSUS = C("Cultivator Colossus", "Creature",
                        {"gen": 4, "G": 3}, 0, 0, priority=8.0, threat=8.0)

CASE_OF_THE_LOCKED_HOTHOUSE = C("Case of the Locked Hothouse", "Enchantment",
                                {"gen": 3, "G": 1}, priority=8.5, threat=3.0)

CONDUIT_OF_WORLDS = C("Conduit of Worlds", "Artifact",
                      {"gen": 2, "G": 2}, priority=6.0, threat=2.0)

WALK_IN_CLOSET = C("Walk-In Closet // Forgotten Cellar", "Enchantment",
                   {"gen": 2, "G": 1}, priority=6.0, threat=2.0)

SPRINGHEART_NANTUKO = C("Springheart Nantuko", "Creature/Enchantment",
                        {"gen": 1, "G": 1}, 1, 1, priority=7.0, threat=5.0)

# The two the model cannot see. Defined anyway, so the harness can print them
# as explicitly MODEL-BLIND rather than omitting them -- an absent row and a
# zero row mean different things, and this project has been bitten twice by
# the second being read as the first.
BURGEONING = C("Burgeoning", "Enchantment", {"G": 1},
               priority=8.0, threat=2.0)

CONSTANT_MISTS = C("Constant Mists", "Instant", {"gen": 1, "G": 1},
                   priority=4.0, threat=1.0)

# Greensleeves, Ancient Greenwarden and Springheart Nantuko were here until
# 2026-09-10 and are now COMMITTED deck members; a card in the deck is not a
# candidate, and leaving it here is the §0o failure (measuring a second copy
# in a singleton-illegal 101-card list).
CANDIDATES_MODELLED = (CULTIVATOR_COLOSSUS, CASE_OF_THE_LOCKED_HOTHOUSE,
                       CONDUIT_OF_WORLDS, WALK_IN_CLOSET)
CANDIDATES_BLIND = (BURGEONING, CONSTANT_MISTS)


# ---------------------------------------------------------------------------
# CARD-DRAW CANDIDATES — 2026-09-10, second batch. NOT in the deck.
#
# Aimed at the deck's ONE measured weakness. The corrected table's finding is
# that this deck is CARD-limited, not drop-limited: it is granted 2.77 land
# drops a turn and uses 1.33 (48%), and 57.9% of turns end with an unused drop
# and NO land anywhere to play. Everything that scores well attacks the card
# constraint -- Horn of Greed +0.0419, Seer's Sundial +0.0293, Tireless
# Tracker +0.0281 -- and everything that adds a FOURTH land drop does not.
#
# Costs and P/T verified against Scryfall 2026-09-10.
#
#   Cryptic Caves       A LAND THAT SACRIFICES ITSELF TO DRAW, and in this
#                       deck that is repeatable rather than one-shot: Crucible
#                       of Worlds and Ramunap Excavator are already in the
#                       list (Ancient Greenwarden is staged), so it comes back
#                       from the graveyard, and replaying it is a landfall
#                       trigger on a drop that was going begging anyway. It
#                       converts the deck's most abundant resource into its
#                       scarcest. Swaps for a Forest, of which there are 21.
#
#   Ka-Zar of the       THE FOURTH TOP-OF-LIBRARY ENABLER. Courser (+0.0172),
#     Savage Land       Augur (+0.0208) and Oracle (+0.0211) are the shape
#                       that roughly doubled once land sequencing was fixed,
#                       because the top of the library is a card source that
#                       does not cost a draw. Ka-Zar is a fourth on a body,
#                       plus Zabu -- a 2/2 that takes a +1/+1 counter on every
#                       landfall. EXPECT REDUNDANCY: three of these are
#                       already in the list, and `top_access()` is a boolean.
#                       That is the Conduit-of-Worlds shape and it is the
#                       reason this is worth measuring rather than assuming.
# ---------------------------------------------------------------------------

CRYPTIC_CAVES = L("Cryptic Caves", "C")

KA_ZAR = C("Ka-Zar of the Savage Land", "Creature", {"gen": 4, "G": 1},
           3, 2, priority=8.0, threat=6.5)

# The other three self-sacrificing draw lands, added 2026-09-10 for review
# against Cryptic Caves. They differ ONLY in the cost of the draw, and those
# differences are the whole comparison -- see azusa.SAC_DRAW_LANDS.
#
#   Horizon of Progress   {1},{T},sac -- same as Caves but with NO land-count
#       condition, and it taps for any type a land you control could produce
#       (so {G} here) rather than {C}. FLOOR: its "{3},{T}: put a land from
#       hand onto the battlefield tapped" is NOT modelled -- it competes with
#       the sac for the same tap, and this deck's problem is that it has no
#       lands in hand, which is what that ability needs. Its "pay 1 life" is
#       also free in this model (§0i), a small overstatement.
#   Scene of the Crime    {2},sac with NO {T} IN THE COST, so it can be
#       cracked the turn it lands and while tapped -- which is what pays for
#       it entering tapped. Costs {2} rather than {1}.
#       An Artifact Land; the engine's own Bane of Progress wipe excludes
#       lands, so it survives a wipe it should legally die to. Noted, tiny.
#   The Hunter Maze       {1}{G},{T},sac. The dearest draw of the four, and
#       the only one that taps for {G} -- which is not nothing in a deck
#       running 13 colourless-only utility lands. Enters tapped.
HORIZON_OF_PROGRESS = L("Horizon of Progress", "G")
SCENE_OF_THE_CRIME = L("Scene of the Crime", "C", tapped=True,
                       types="Artifact/Land")
THE_HUNTER_MAZE = L("The Hunter Maze", "G", tapped=True)

# Scene of the Crime won this comparison and is COMMITTED (in LANDS above), so
# it leaves the candidate tuple. Ka-Zar remains STAGED, not committed, so it
# stays. Cryptic Caves, Horizon of Progress and The Hunter Maze lost and are
# kept as the provenance for that decision -- §0z3.
DRAW_CANDIDATES = (KA_ZAR, CRYPTIC_CAVES, HORIZON_OF_PROGRESS,
                   THE_HUNTER_MAZE)


# ---------------------------------------------------------------------------
# THIRD BATCH — seven cards submitted 2026-09-10. NOT in the deck.
#
# Costs, types, P/T and oracle text verified against Scryfall 2026-09-10, and
# two of the seven are NOT what they are usually remembered as:
#
#   Return of the Wildspeaker reads NON-HUMAN creatures, not creatures. The
#   deck's six Humans are Augur of Autumn, Azusa herself, Eternal Witness,
#   Tireless Tracker, Yavimaya Elder and the staged Ka-Zar -- all small, so the
#   DRAW mode is barely affected (the greatest power in this deck is never a
#   Human) and the PUMP mode misses six bodies. The set is generated into
#   decks/_evasion.py by tag_flying.py rather than written here; see §0q.
#
#   Castle Garenbrig's big ability is "{2}{G}{G}, {T}: Add six {G}", not the
#   four-mana version it is often quoted as. Net +2 mana, creature-spells only.
#
# WHAT IS AND IS NOT MODELLED. Read this before quoting any number.
#
#   The Great Henge        FULL. The cost reduction is the card -- {7}{G}{G}
#                          minus the greatest power you control, which in this
#                          deck is routinely 5-10 -- and it is implemented in
#                          azusa.cost_of() the same way engine.py already does
#                          it for the Rendmaw list. The nontoken-creature ETB
#                          draw fires from every zone a creature can enter
#                          from, and {T}: {G}{G} + 2 life is real, including
#                          the life, which this model does track.
#   Sapling Nursery        FULL on the two halves that matter: Affinity for
#                          Forests (20 Forests + Dryad Arbor) and the landfall
#                          3/4 reach Treefolk. FLOOR: the {1}{G} exile-for-
#                          indestructible ability is not modelled, and it is
#                          real wipe protection in a pod that wipes.
#   Nissa, Who Shakes      FULL, and the most invasive of the seven. The
#     the World            static Forest doubler needed a change to the shared
#                          `spend()` -- a Forest now taps for two -- which is
#                          the Crypt Ghast branch already there. +1 animates a
#                          land as a 3/3 vigilance haste and UNTAPS it, which
#                          is a ritual as well as a body; -8 puts every Forest
#                          left in the library onto the battlefield, which in
#                          this deck is a landfall detonation.
#   Return of the          MOSTLY. Both modes are implemented and the mode
#     Wildspeaker          CHOICE is a stated policy, not an optimiser -- see
#                          azusa.wildspeaker_mode(). FLOOR: it is an INSTANT
#                          and this engine has no instant speed, so it is cast
#                          in a main phase like a sorcery.
#   Finale of Devastation  MOSTLY, at a FIXED X of 6 -- the same convention
#                          Genesis Wave (6) and Animist's Awakening (4)
#                          already use here, and the reason its number is an
#                          approximation rather than a floor or a ceiling: a
#                          real pilot scales X to the mana available, which is
#                          a lot in this deck. Searching the GRAVEYARD as well
#                          as the library IS modelled; the X>=10 team pump is
#                          not.
#   War Room               FULL, and one of the very few cards in this project
#                          whose life payment is actually charged -- one life
#                          per draw, mono-green, and `your_life` is read at
#                          end of turn. Competes with itself for the tap: a
#                          War Room that draws produces no mana that turn.
#   Castle Garenbrig       FULL. Enters untapped only if you control a Forest,
#                          checked as the card says; the six {G} is a
#                          restricted pool that only creature spells may spend,
#                          which is why it is not simply +2 mana.
#
# Priorities are on this deck's own scale: commander 10, Sol Ring 10, Lotus
# Cobra 9, Craterhoof 9, Greenwarden 8.5, Courser 8, Avenger 8.5.
# ---------------------------------------------------------------------------

RETURN_OF_THE_WILDSPEAKER = C(
    "Return of the Wildspeaker", "Instant", {"gen": 4, "G": 1},
    priority=6.5, threat=0.0, script="return_wildspeaker")

# {X}{G}{G} modelled at X=6: cost {6}{G}{G}, tutoring a creature of mana value
# 6 or less. x_pips carries the X so audit_cards.py can reconcile the cost with
# Scryfall's cmc 2 (which is X=0), the same way Genesis Wave and Chord do.
FINALE_OF_DEVASTATION = C(
    "Finale of Devastation", "Sorcery", {"gen": 6, "G": 2},
    priority=7.5, threat=6.0, script="finale", x_pips=6)

# {7}{G}{G} PRINTED, and essentially never paid: "this spell costs {X} less to
# cast, where X is the greatest power among creatures you control". The cost
# here is the printed one and azusa.cost_of() applies the reduction, which is
# also how engine.py models it for the Rendmaw list. mana=(2, "G") is the
# "{T}: Add {G}{G}" half -- NOT modelled in rendmaw_v12, modelled here.
THE_GREAT_HENGE = C(
    "The Great Henge", "Artifact", {"gen": 7, "G": 2},
    priority=8.0, threat=7.0, tags=("Legendary",), mana=(2, "G"))

# {6}{G}{G} PRINTED, with Affinity for Forests. azusa.cost_of() subtracts the
# Forests you control, so in this list it is routinely a {G}{G} to {3}{G}{G}
# enchantment rather than an eight-drop.
SAPLING_NURSERY = C(
    "Sapling Nursery", "Enchantment", {"gen": 6, "G": 2},
    priority=8.0, threat=7.5)

NISSA_WHO_SHAKES_THE_WORLD = C(
    "Nissa, Who Shakes the World", "Planeswalker", {"gen": 3, "G": 2},
    priority=8.5, threat=8.0, tags=("Legendary",))

# "{3}, {T}, Pay life equal to the number of colors in your commanders' color
# identity: Draw a card." Mono-green, so one life.
WAR_ROOM = L("War Room", "C")

# "This land enters tapped unless you control a Forest" -- tapped=False here
# and the condition applied in azusa.land_step(), which is why audit_cards.py
# passes it (its `unless` rule) rather than flagging it.
CASTLE_GARENBRIG = L("Castle Garenbrig", "G")

BATCH3_CANDIDATES = (RETURN_OF_THE_WILDSPEAKER, FINALE_OF_DEVASTATION,
                     THE_GREAT_HENGE, SAPLING_NURSERY,
                     NISSA_WHO_SHAKES_THE_WORLD, WAR_ROOM, CASTLE_GARENBRIG)
