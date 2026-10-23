"""azusa's ledger entries and swap-in catalog.

DATA ONLY. `edhmc/pending.py` gathers these lists from every deck's
module (in `edhmc/registry.py`'s order) and holds the logic and the
checks; `docs/LEDGER_STATES.md` defines the states. Split out of
`pending.py` on 2026-10-11 so that editing one deck's entries does not
mean paging through every deck's. ORDER WITHIN A LIST IS MEANINGFUL:
`build_pending` applies CHANGES in this order, and the cache fingerprint
hashes it. Every entry here must name this deck; the package refuses one
that does not (`edhmc/ledger/__init__.py`).
"""

from __future__ import annotations

from edhmc.decks import azusa_v1
from edhmc.ledger.records import Change, Candidate, Simulated, Proposal


COMMITTED: list[Change] = [
    # -----------------------------------------------------------------------
    # AZUSA, committed 2026-09-10. TWO LEGS, not three: this deck has no
    # .xlsx, so `edhmc/decks/azusa_v1.py` IS the system of record and these
    # four are applied there. The fifth 2026-09-10 swap -- Perilous Forays
    # -> Ka-Zar of the Savage Land -- is deliberately LEFT STAGED and is
    # still in CHANGES below.
    # -----------------------------------------------------------------------
    Change(
        deck="azusa",
        remove="Oblivion Stone",
        add="Ancient Greenwarden",
        staged="2026-09-10",
        rationale=(
            "THE BEST SINGLE CARD OF THE NINE EVALUATED, and half its value "
            "is a clause nothing else in the deck duplicates. Ancient "
            "Greenwarden is {4}{G}{G} for a 5/7 reach body, 'you may play "
            "lands from your graveyard', AND 'if a land entering causes a "
            "triggered ability of a permanent you control to trigger, that "
            "ability triggers an additional time'. Measured over a blank at "
            "N=15,000 it is +0.0290 +-0.0041 win at T20, which would place it "
            "around fourth in the deck. "
            "THE HALVES WERE MEASURED APART, because +0.029 credited to the "
            "wrong one is a wrong deckbuilding conclusion: graveyard lands "
            "plus the body is +0.0170 +-0.0060 and THE DOUBLER ALONE is "
            "+0.0138 +-0.0044, almost exactly additive. The doubler's "
            "mechanism is CARD DRAW, not damage -- +1.09 cards a game, "
            "because what it mostly doubles is Horn of Greed and Seer's "
            "Sundial. That lands on this deck's standing finding that it is "
            "CARD-limited rather than drop-limited. "
            "THE CUT is the weakest of the land-animation genre. KNOWN_ISSUES "
            "§0s already found that pillar is nearly a blank -- the animation "
            "is worth 9.24 marginal damage a game in a deck whose damage runs "
            "into the thousands, i.e. it sells this deck the one thing it "
            "already has most of."
        ),
        evidence=(
            "Measured as the REAL SWAP, not value-over-a-blank, at N=15,000 "
            "paired with every leg on the same seed "
            "(run_azusa_animation_swap.py). This swap alone: win rate "
            "+0.0249 +-0.0030 at T10 and +0.0277 +-0.0043 at T20, both "
            "significant. As part of the staged package (P3B, all three swaps "
            "together): +0.0382 +-0.0040 at T10 and +0.0421 +-0.0058 at T20, "
            "and the package is ADDITIVE -- interaction +0.0002 +-0.0033 at "
            "T10. Greenwarden's value barely depends on which animation slot "
            "it takes: its four measured cut targets span +0.0235 to +0.0277 "
            "against bars of +-0.004, which is itself the cleanest statement "
            "that the incumbent genre is interchangeable with a blank."
        ),
        notes=(
            "THE CUT WAS MOVED BY THE OWNER ON 2026-09-30 (§0z88): Oblivion "
            "Stone goes instead of Sylvan Awakening, which returns to the "
            "list. The rationale and evidence above were written and measured "
            "against SYLVAN AWAKENING as the cut; they are kept as they were. "
            "THE MOVE ITSELF, paired on the staged list at N=15,000 "
            "(diagnostics/run_greenwarden_cut.py): Sylvan Awakening in "
            "Oblivion Stone's slot is -0.0003 +-0.0013 at T10 and +0.0033 "
            "+-0.0024 at T20. Oblivion Stone is KNOWN_BLIND -- its "
            "fate-counter wipe is not played -- so that is Sylvan Awakening "
            "against a blank, and it says nothing about what the Stone does "
            "at a real table (§0z88). "
            "KNOWN_ISSUES §0x (the candidate batch), §0y (the head-to-head), "
            "§0z (what the model does NOT see). "
            "AZUSA HAS NO .xlsx, so this is a TWO-LEG change -- the module "
            "and this ledger -- not three. "
            "WHY THE PACKAGE CUTS NISSA, WORLDWAKER AND NOT ASHAYA: an "
            "earlier version cut Ashaya, Soul of the Wild, whose ablation row "
            "is the weakest of the four at +0.0011. That cut was WITHDRAWN on "
            "2026-09-10 because Ashaya's main clause is unimplemented (§0z) "
            "and its row is therefore not evidence about the card. The "
            "Ashaya-preserving package measures +0.0421 +-0.0058 against the "
            "Ashaya-cutting one at +0.0434 +-0.0057 -- inside each other's "
            "bars, so keeping it costs nothing measurable and removes a real "
            "risk."
        ),
    ),
    Change(
        deck="azusa",
        remove="Rude Awakening",
        add="Greensleeves, Maro-Sorcerer",
        staged="2026-09-10",
        rationale=(
            "A {3}{G}{G} */* equal to your land count that makes a 3/3 "
            "BADGER on every landfall -- the Rampaging Baloths shape, in a "
            "deck where Baloths is already a top-three card at +0.0303. "
            "+0.0143 +-0.0033 over a blank at T20. "
            "IT SCORES WITH NEGATIVE LAND COUNTERS, and that is the "
            "mechanism rather than a problem: landfall_triggers, lands_played "
            "and cards_drawn all go slightly DOWN while win rate and damage "
            "go up, because the games end sooner. Same shape the table "
            "already records for Avenger of Zendikar (-6.1 damage at T20, "
            "+0.0249 win) and Ulamog. It is not a land card; it converts "
            "landfall into BODIES. "
            "AND §0v IS WHY THAT IS WORTH MORE THAN IT USED TO BE: since "
            "combat is declared at the whole pod, tokens are not damage, they "
            "are WIDTH, and width is extra opponents killed. Rude Awakening "
            "is the reverse -- it concentrates power into animated lands, "
            "which is the board shape the combat model stopped rewarding."
        ),
        evidence=(
            "Real swap, N=15,000 paired, same seeds: win rate +0.0070 "
            "+-0.0021 at T10 and +0.0121 +-0.0036 at T20, significant at "
            "both. In the staged package (P3B): +0.0382 / +0.0421, additive. "
            "Greensleeves beats every cut target it was tried against "
            "(+0.0092 to +0.0128 at T20 across the four)."
        ),
        notes=(
            "Rude Awakening is modelled with BOTH its modes and its entwine "
            "as of §0s, so this cut is against a fully-implemented card -- "
            "which is exactly the check that failed for Ashaya. Its own "
            "ablation row is +0.0061 +-0.0026. "
            "THE PACKAGE'S MECHANISM, T20: lands_animated -7.76, "
            "animated_damage -7.14, against tokens_made +37.92, "
            "landfall_triggers +1.35 and cards_drawn +0.98. You give up "
            "roughly seven animated damage a game and receive thirty-eight "
            "tokens. That is §0s confirmed from the replacement side."
        ),
    ),
    Change(
        deck="azusa",
        remove="Nissa, Worldwaker",
        add="Springheart Nantuko",
        staged="2026-09-10",
        rationale=(
            "{1}{G} for a 1/1 with Bestow {1}{G} and 'Landfall -- whenever a "
            "land you control enters, you may pay {1}{G} if this permanent is "
            "attached to a creature you control. If you do, create a token "
            "that's a COPY of that creature. If you didn't, create a 1/1 "
            "Insect.' Bestow costs exactly what the creature mode costs, so "
            "choosing is free and the card is a build-around. "
            "IT COPIES A LANDFALL PAYOFF EVERY LAND DROP. Bestowed on Lotus "
            "Cobra that is another mana per landfall, compounding; on "
            "Tireless Provisioner another Treasure; on Scute Swarm it doubles "
            "the doubling."
        ),
        evidence=(
            "Real swap, N=15,000 paired, same seeds as the other two "
            "(run_azusa_animation_swap.py): win rate +0.0060 +-0.0022 at T10 "
            "and +0.0118 +-0.0035 at T20, significant at both. As part of the "
            "staged package (P3C): +0.0398 +-0.0040 at T10 and +0.0499 "
            "+-0.0058 at T20, damage +5.81. "
            "IT IS DOUBLE THE CARD IT REPLACED IN THIS SLOT: Conduit of "
            "Worlds measures +0.0059 +-0.0035 in the identical swap, against "
            "Springheart's +0.0118 +-0.0035, on the same seeds. The package "
            "moves +0.0421 -> +0.0499 at T20."
        ),
        notes=(
            "THIS SLOT HELD CONDUIT OF WORLDS FOR ONE DAY. Conduit was staged "
            "2026-09-10 with an explicit note -- 'if one of the three is "
            "dropped, drop this one' -- because it is a FOURTH 'play lands "
            "from your graveyard' effect alongside Ancient Greenwarden, "
            "Crucible of Worlds and Ramunap Excavator, and the package "
            "carrying it was sub-additive (-0.0037). That note named "
            "Springheart as the leading alternative and said it was unmeasured "
            "in this slot. It has now been measured, and it wins. "
            "WHAT CHANGED IS THE MODEL, NOT THE CARD. Springheart's bestow "
            "and copy mode was UNIMPLEMENTED until 2026-09-10 (§0z1), so its "
            "earlier +0.0105 was the unattached 1/1-Insect floor. "
            "Implementing it -- which first required converting every landfall "
            "payoff from a boolean `has()` to a counting `count()`, or every "
            "copy would have been inert -- moved it to +0.0141 over a blank. "
            "THE NUMBER IS STILL A FLOOR, in two known ways. The engine "
            "bestows only onto a ranked list of landfall payoffs, never onto "
            "an arbitrary body; and a token copy does NOT re-trigger the "
            "host's ETB, so copying Avenger of Zendikar or Craterhoof "
            "Behemoth is scored as a bare body. Both are conservative. "
            "IT IS ALSO RARE: springheart_bestowed fires in 16.2% of games "
            "and it averages 1.07 copies a game. The combo is real, modelled, "
            "and uncommon -- which is why this is +0.012 and not +0.05. "
            "THE CUT is unchanged: Nissa, Worldwaker's abilities ARE modelled "
            "as of §0s, so this is a cut against a real card at +0.0079 "
            "+-0.0025 -- the dearest of the four animation cuts."
        ),
    ),
    Change(
        deck="azusa",
        remove="Forest",
        add="Scene of the Crime",
        staged="2026-09-10",
        rationale=(
            "'This land enters tapped. {T}: Add {C}. {T}, Tap an untapped "
            "creature you control: Add one mana of any color. {2}, Sacrifice "
            "this land: Draw a card.' An Artifact Land -- Clue. "
            "A land that eats itself for a card is one-shot in most decks and "
            "REPEATABLE here: Crucible of Worlds and Ramunap Excavator are in "
            "the list and Ancient Greenwarden is staged, so it comes back "
            "from the graveyard, and replaying it is a landfall trigger on a "
            "land drop that was going begging anyway -- this deck is granted "
            "2.77 drops a turn and uses 1.33. It converts the deck's most "
            "abundant resource into its scarcest, which is the deck's one "
            "measured weakness. "
            "IT IS THE ONE OF THE TWO STAGED CARDS THAT ACTUALLY ADDRESSES "
            "THAT WEAKNESS: cards_drawn +0.53 +-0.10 against Ka-Zar's +0.18 "
            "on a baseline of 20.1."
        ),
        evidence=(
            "BEST OF FOUR, measured head to head in the same Forest slot on "
            "the same seeds, N=15,000 paired (run_azusa_draw.py), T20 win "
            "rate: Scene of the Crime +0.0096 +-0.0038; Horizon of Progress "
            "+0.0081 +-0.0030; Cryptic Caves +0.0068 +-0.0032; The Hunter "
            "Maze +0.0039 +-0.0032. At T10: +0.0049, +0.0041, +0.0034, "
            "+0.0020. Every one significant at both horizons. "
            "THE WIN-RATE GAP OVER CRYPTIC CAVES IS INSIDE THE BARS (+0.0028 "
            "against +-0.0038), so this is NOT a clean ranking on the "
            "objective. The MECHANISM counters are decisive and all point the "
            "same way: it cracks 0.39 times a game against 0.21, draws +0.53 "
            "cards against +0.26, and adds +0.33 landfall triggers against "
            "+0.17 -- every one of those gaps far outside its own bar."
        ),
        notes=(
            "WHY IT WINS IS THE USEFUL PART, AND IT IS NOT THE MANA COST. "
            "Scene of the Crime is the DEAREST of the four to activate ({2} "
            "against {1}) and it ENTERS TAPPED, and it still wins, because "
            "its sacrifice ability has NO {T} IN THE COST. Every other one "
            "must be untapped to crack, and in this deck lands are tapped for "
            "mana during the main phase, so by the time activations() runs "
            "after combat they usually cannot. **The binding constraint on a "
            "sacrifice-land is the TAP, not the mana.** That is why The "
            "Hunter Maze is worst of the four: {1}{G} AND {T} AND enters "
            "tapped, taxed three ways. "
            "COSTS, both real: entering tapped shows up as stranded_mv +3.22, "
            "the highest of the four; and it is an ARTIFACT land, which the "
            "engine's own Bane of Progress wipe spares because that wipe "
            "excludes lands -- legally it should die to it. Both small, both "
            "recorded. "
            "SMALL BECAUSE IT IS RARE, NOT BECAUSE IT IS WEAK: one land in a "
            "41-land deck, which has to be drawn before it does anything. "
            "Singleton forbids the second and third copy that would scale it. "
            "The cut is a Forest, of which there are 21, so the swap costs "
            "close to nothing -- which is the argument for it at this size. "
            "THE ACTIVATION POLICY IS A HAND-SET KNOB, NOT A MEASURED "
            "OPTIMUM: it cracks with a graveyard-recursion effect out, or at "
            "six or more lands. `cryptic_caves_min_lands` is the knob (named "
            "for the first card to use it; it now governs all four) and it "
            "has NOT been swept. §0z2, §0z3. "
            "THIS SLOT HELD CRYPTIC CAVES for a few hours, staged before the "
            "other three had been measured. That entry said it would be "
            "replaced rather than supplemented if one of them won. One did."
        ),
    ),
    # COMMITTED 2026-09-22 to edhmc/decks/azusa_v1.py, into Yavimaya Elder's
    # EXACT list position, so the committed list is index-for-index the one
    # the 2026-09-22 rebuilt table was measured against (§0z42). Azusa has
    # no .xlsx: its module is the system of record, so this is two legs.
    # Its MEASURED row -- a 2026-09-13 candidate row of +0.0291 +-0.0040 at
    # T20 against a blank -- was removed on commit, as check_measured_are_
    # promotable requires and as all four earlier azusa commits did. The
    # number the decision rests on is the head-to-head below (§0e).
    Change(
        deck="azusa", remove="Yavimaya Elder", add="Traveling Chocobo",
        staged="2026-09-22",
        rationale=(
            "A SECOND ANCIENT GREENWARDEN for the half this deck cares about: "
            "'if a land or Bird you control entering causes a triggered "
            "ability of a permanent you control to trigger, that ability "
            "triggers an additional time', and the two STACK -- one land fires "
            "every payoff three times. It also plays lands off the top of the "
            "library, a fifth source of that boolean. THE CUT IS THE OWNER'S "
            "(2026-09-20): Yavimaya Elder ablates to +0.0023 +-0.0023, inside "
            "its own bar, and is MODEL-EVALUATED -- its death trigger and its "
            "sacrifice-draw are both in azusa.py -- so its row is evidence "
            "and not a blind card read as one (§0z36). Staged on the owner's "
            "instruction of 2026-09-22, after §0z37 had broken the tie with "
            "Nissa, Resurgent Animist in this card's favour -- A RANKING THAT "
            "DID NOT SURVIVE THE SAME DAY'S HORN OF GREED FIX (§0z41; see the "
            "evidence). The two are MEASURED EQUAL again, so the choice is the "
            "owner's preference and this staging rests on it, not on a "
            "measured edge."),
        evidence=(
            "RE-MEASURED 2026-09-22 ON THE §0z41/§0z42 ENGINE (Horn of Greed "
            "no longer tripled by this card and Greenwarden; decking loses), "
            "same N, seeds and base (diagnostics/run_azusa_head2head.py, "
            "results/azusa_head2head_0z41.txt): THE REAL SWAP is win rate "
            "+0.0173 [+0.0145, +0.0201] at T10 and +0.0222 [+0.0181, "
            "+0.0263] at T20, significant at BOTH horizons, against baselines "
            "of 0.1570 and 0.3780. cards_drawn +0.44 / +0.62, down from "
            "+0.80 / +1.07 -- about 40% of this card's extra cards were Horn "
            "of Greed being tripled. AND THE RANKING IS GONE: Chocobo -> "
            "Nissa, Resurgent Animist in this slot is -0.0017 [-0.0046, "
            "+0.0013] at T10 and -0.0027 [-0.0069, +0.0013] at T20, inside the "
            "bar at both, point estimates still in this card's favour. Nissa's "
            "own swap barely moved (+0.0155 / +0.0195). The two buy different "
            "things -- Nissa +0.19 landfall_triggers and 2.1 LESS stranded "
            "mana, this card +0.25 cards and +0.67 life at T20 -- in amounts "
            "the harness cannot separate. SUPERSEDED FIGURES FOLLOW. "
            "THE REAL SWAP on the post-§0z37 engine, N=15,000 paired, same "
            "seeds both legs, base = build_pending('azusa') with Ka-Zar "
            "applied (diagnostics/run_azusa_head2head.py, "
            "results/azusa_head2head.txt): win rate +0.0213 [+0.0183, "
            "+0.0241] at T10 and +0.0257 [+0.0215, +0.0297] at T20, "
            "significant at BOTH horizons, against baselines of 0.1597 and "
            "0.3829. Damage +2.17 / +2.11, cards_drawn +0.80 / +1.07, "
            "final_life +1.55 / +2.76, stranded_mv +2.12 / +3.00. AND THE "
            "RANKING §0e says a common baseline cannot give: Chocobo -> Nissa, "
            "Resurgent Animist in this one slot, paired on the same seeds, is "
            "-0.0056 +-0.0029 at T10 and -0.0056 +-0.0040 at T20 -- this card "
            "was the better of the two at both horizons ON THAT ENGINE. The "
            "pre-§0z37 figures "
            "(+0.0253 / +0.0265, and a measured tie with Nissa) are "
            "SUPERSEDED: the tie was floating landfall mana never being "
            "consumed (§0z35, §0z37)."),
        notes=(
            "FLOOR, and a small one: 'cast Bird spells from the top of your "
            "library' is worth nothing in a list whose only Bird is this card. "
            "Its top-of-library half is REDUNDANT with Courser, Augur, Oracle "
            "and the staged Ka-Zar, and that is priced in -- all four are in "
            "the list it was measured against. REDUNDANT WITH ANCIENT "
            "GREENWARDEN BY DESIGN (§0z27): after this lands, Greenwarden's "
            "row is understated, and the two must be ablated as a group before "
            "either is read as a cut. STAGING REWRITES build_pending('azusa'), "
            "which is the third row of CLAUDE.md's cache table -- the azusa "
            "ablation table is rebuilt in the same change, never cleared with "
            "--verified. AZUSA HAS NO .xlsx: committing this is two legs, the "
            "module and this ledger."),
    ),
    # COMMITTED 2026-10-03 to edhmc/decks/azusa_v1.py, into Wayward
    # Swordtooth's EXACT list position, so the committed list is index-for-
    # index the one the head-to-head measured. Azusa has no .xlsx: two legs.
    # Its MEASURED row (+0.0363 +-0.0042 at T20 against a blank) and its
    # SIMULATED head-to-head moved here on commit (check_measured_are_
    # promotable; check_simulated rule 3). The azusa table is rebuilt in the
    # same change, since this rewrites the list every cached row was measured
    # against.
    Change(
        deck="azusa", remove="Wayward Swordtooth", add="Mole Man, Moloid Master",
        staged="2026-10-03",
        rationale=(
            "THE OWNER'S DECISION (2026-10-03), on §0z101's evidence. "
            "'You may play lands from your graveyard' plus a 1/1 Moloid per "
            "landfall: a second Crucible of Worlds on a token maker, and the "
            "only one of batch 6's seven landfall payoffs that adds land "
            "SUPPLY -- 3.83 lands a game from the graveyard, lands_played "
            "+0.62 -- which is the constraint §0z99 named (the deck is short of "
            "lands to play, not of permission). THE CUT IS THE OWNER'S: "
            "Wayward Swordtooth ablated to +0.0032 +-0.0030, inside its bar, "
            "and the swap and the blank row agree to 0.004 for every card in "
            "the batch because the cut is worth nothing. Exploration stays: "
            "the owner expects its extra drop to grow with land recursion, and "
            "the rebuilt table re-measures it with Mole Man in the list."),
        evidence="REAL SWAP -Wayward Swordtooth +Mole Man, Moloid Master, N=15,000 paired: +0.0275 +-0.0031 (significant) at T10 and +0.0352 +-0.0041 (significant) at T20; damage +3.29 +-0.28. THE ONLY ONE OF THE SEVEN THAT RAISES lands_played (+0.37) despite cutting a land drop: 3.83 lands a game from the graveyard, most of them fetch lands replayed and cracked again. A second Crucible of Worlds on a body that makes a Moloid per landfall -- and the graveyard half is a boolean shared with Crucible, Ramunap and Greenwarden, so this number includes the games where it duplicates them.",
    ),
    # COMMITTED 2026-10-03 to edhmc/decks/azusa_v1.py, into Life from the
    # Loam's EXACT list position. Two legs (azusa has no .xlsx). Its MEASURED
    # row and its SIMULATED head-to-head moved here on commit. The azusa table
    # is rebuilt in the same change.
    Change(
        deck="azusa", remove="Life from the Loam", add="Mossborn Hydra",
        staged="2026-10-03",
        rationale=(
            "THE OWNER'S DECISION (2026-10-03). 'Trample. This creature enters "
            "with a +1/+1 counter on it. Landfall -- double the number of "
            "+1/+1 counters on this creature': 4.1 doublings a game on a "
            "trampler, so the counters get through the chump blocks that "
            "blunt the deck's other big bodies (§0z92). THE CUT IS THE "
            "OWNER'S, proposed after Titania was ruled out: Loam ablated to "
            "+0.0039 +-0.0024 with Mole Man, Crucible, Ramunap and Greenwarden "
            "in the list (§0z102). Loam is real land supply -- cutting it costs "
            "0.60 lands played a game -- and the Hydra more than pays for it. "
            "PAIRED IN THIS SLOT AGAINST NISSA, RESURGENT ANIMIST, the other "
            "card proposed for it: Nissa minus Hydra -0.0112 +-0.0030 at T10, "
            "-0.0065 +-0.0038 at T20 (results/azusa_slot_loam_20261003.txt)."),
        evidence="REAL SWAP -Life from the Loam +Mossborn Hydra, N=15,000 paired, on the list WITH Mole Man (§0z102): +0.0213 +-0.0032 (significant) at T10 and +0.0201 +-0.0042 (significant) at T20; damage +2.46 +-0.28.",
    ),
]


MEASURED: list[Candidate] = [
    # AZUSA BATCH 6 (§0z101), measured 2026-10-03: value over a blank in the
    # Sylvan Library slot (azusa3/4/5's), results/candidates_azusa_batch6_T20.txt.
    # The real swaps against Wayward Swordtooth are SIMULATED entries.
    Candidate(
        deck='azusa', card='Elfsworn Giant', measured='2026-10-03',
        win_rate='+0.0083 +-0.0031 at T20 (N=15,000 paired)', signal='both',
        rationale='A token per landfall on a 5/3, the Rampaging Baloths shape at 1/1.',
        evidence='damage +1.15 +-0.19, P(deploy) 0.266, 4.0 Elf Warriors a game. REAL SWAP for Wayward Swordtooth (SIMULATED, below): +0.0033 / +0.0121.',
        limits='REACH is not modelled (blockers are a count, §4): the row is the body and the tokens.',
        verdict='The weakest token maker in the batch: 1/1s are the thinnest landfall payoff, and Chocobo Racetrack in the same slot is more than three times the row.',
    ),
    Candidate(
        deck='azusa', card='Chocobo Racetrack', measured='2026-10-03',
        win_rate='+0.0283 +-0.0035 at T20 (N=15,000 paired)', signal='both',
        rationale="Zendikar's Roil with tokens that grow: each Bird +1/+0 per later land that turn.",
        evidence='damage +2.77 +-0.23, P(deploy) 0.271, 3.6 Birds and 39.7 Bird pumps a game. REAL SWAP for Wayward Swordtooth (SIMULATED, below): +0.0134 / +0.0276.',
        verdict="A member of the batch's top set (with Mole Man, Mossborn Hydra and Glacier Godmaw); the Roil anchor in the same slot is +0.0179, so the Birds' own trigger is worth about +0.010.",
    ),
    Candidate(
        deck='azusa', card='Dancing from Dark to Dawn', measured='2026-10-03',
        win_rate="+0.0251 +-0.0035 at T20 (N=15,000 paired), counter_target='spread'", signal='both',
        rationale="Zendikar's Roil plus MV counters on a creature for every creature spell cast.",
        evidence='damage +2.81 +-0.22, P(deploy) 0.271, 3.9 Bears and 5.0 cast-trigger counters a game. REAL SWAP for Wayward Swordtooth (SIMULATED, below): +0.0078 / +0.0245 under spread (focus: +0.0066 / +0.0206).',
        limits="The row READS A POLICY: where the counters go is `counter_target`, 'spread' by default since §0z101 (spread minus focus +0.0039 +-0.0015 at T20).",
        verdict='Roil-plus: +0.007 over the Roil anchor in the same slot, which is the cast trigger.',
    ),
    Candidate(
        deck='azusa', card='Bristly Bill, Spine Sower', measured='2026-10-03',
        win_rate="+0.0069 +-0.0030 at T20 (N=15,000 paired), counter_target='spread'", signal='both',
        rationale="A counter per landfall and a repeatable doubling of every creature's counters.",
        evidence='damage +0.87 +-0.18, P(deploy) 0.298, 4.0 landfall counters and 0.6 doublings a game. REAL SWAP for Wayward Swordtooth (SIMULATED, below): +0.0098 / +0.0113 under spread; under focus +0.0011 / +0.0009, INSIDE ITS BAR.',
        limits="The row READS A POLICY and the policy was most of the gap: spread minus focus +0.0105 +-0.0021 at T20 (results/counter_spread.txt), the owner's prediction. The doubling is mostly OVERKILL -- it fires on boards that have already won (unbounded damage balloons, bounded damage barely moves) -- and concentrated counters die together to removal and wipes.",
        verdict='The weakest row of the seven even spread: a +1/+1 counter per land is a smaller rate than a body per land in a model that rewards width (§0v). Not a cut list; a decision against Swordtooth like the others.',
    ),
    Candidate(
        deck='azusa', card='Glacier Godmaw', measured='2026-10-03',
        win_rate='+0.0243 +-0.0038 at T20 (N=15,000 paired)', signal='both',
        rationale='A repeatable Craterhoof: team +1/+1 and HASTE per landfall, and a Lander token.',
        evidence='damage +2.49 +-0.23, P(deploy) 0.258, 17 summoning-sick creatures a game attack because of its haste; 0.14 Landers cracked. REAL SWAP for Wayward Swordtooth (SIMULATED, below): +0.0228 / +0.0265.',
        limits='VIGILANCE is not modelled and cannot matter (tapped creatures still count as blockers). A seven-drop: the lowest P(deploy) of the seven.',
        verdict="Top set. The haste is the card -- this turn's landfall tokens attack the turn they are made.",
    ),
    Candidate(
        deck='azusa',
        card='Autumn Willow, Harmony',
        measured='2026-09-29',
        win_rate='REAL SWAP -Titania, Protector of Argoth +Autumn Willow, Harmony, N=15,000 paired: +0.0047 +-0.0020 (significant) at T10 and +0.0024 +-0.0031 (inside its bar) at T20.',
        signal='win',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 0.26 Dryads and 0.96 extra {G} a game at T20, +0.57 landfall triggers.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits="PARTLY: hexproof not modelled. Titania's own row is +0.0030 +-0.0030, a live card, so this is a close trade.",
        verdict='Significant at T10, INSIDE ITS BAR at T20. Not a clear upgrade on Titania.',
    ),
    Candidate(
        deck='azusa',
        card='Verdant Kraken',
        measured='2026-09-21',
        win_rate=('REAL SWAP -Yavimaya Elder +Verdant Kraken, N=15,000 paired: +0.0163 '
            '+-0.0024 at T10 and +0.0265 +-0.0037 at T20, significant at both. Ag'
            'ainst the Chocobo in the same slot: -0.0049 +-0.0029 at T10 (signifi'
            'cant) and +0.0007 +-0.0042 at T20 (inside its bar).'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence=('results/azusa_fra.txt (diagnostics/run_azusa_fra.py), measured on th'
            'e §0z37-fixed engine'),
        limits=('THE CUT IT WAS MEASURED AGAINST NO LONGER EXISTS: Traveling Chocobo '
            "was COMMITTED into Yavimaya Elder's slot on 2026-09-22, so the -Yavi"
            'maya Elder number describes a list that is gone, and the live questi'
            "on is the Chocobo comparison. STALE -- NOT RESTATED. This deck's bas"
            'eline has MOVED since the measurement (§0z41 Horn of Greed, §0z42 de'
            'cking, and the Chocobo committed into this slot); check_unchanged_de'
            'cks 246b148 vs 2026-09-25 reports it MOVED on 8 of 8 metrics. Re-mea'
            'sure before any head-to-head decision rests on it.'),
        verdict=('Loses to the committed Chocobo at T10 and ties at T20, so it does no'
            't displace it. The Chocobo holds the slot on the evidence that exist'
            's.'),
    ),
    Candidate(
        deck='azusa',
        card='Simulacrum Shaper',
        measured='2026-09-21',
        win_rate=('REAL SWAP -Yavimaya Elder +Simulacrum Shaper, N=15,000 paired: +0.00'
            '40 +-0.0019 at T10 and +0.0035 +-0.0033 at T20, significant at both.'
            ' Against the Chocobo in the same slot: -0.0173 +-0.0027 / -0.0223 +-'
            '0.0040, significant at both.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence=('results/azusa_fra.txt (diagnostics/run_azusa_fra.py), measured on th'
            'e §0z37-fixed engine'),
        limits=('THE CUT IT WAS MEASURED AGAINST NO LONGER EXISTS: the Chocobo was co'
            "mmitted into Yavimaya Elder's slot on 2026-09-22. STALE -- NOT RESTA"
            "TED. This deck's baseline has MOVED since the measurement (§0z41 Hor"
            'n of Greed, §0z42 decking, and the Chocobo committed into this slot)'
            '; check_unchanged_decks 246b148 vs 2026-09-25 reports it MOVED on 8 '
            'of 8 metrics. Re-measure before any head-to-head decision rests on i'
            't.'),
        verdict=('Barely beats the old cut and loses to the committed Chocobo decisive'
            'ly at both horizons. Not a contender.'),
    ),
    # ---- 2026-09-16, batch 5 (§0z25). Same Sylvan Library slot as batches 3
    # and 4, so these rows sit on one scale with those thirteen.
    Candidate(
        deck="azusa", card="Guardian Project", measured="2026-09-16",
        win_rate="+0.0279 +-0.0036 at T20 (N=15,000 paired) -- CORRECTED "
                 "2026-09-17, §0z28; the 2026-09-16 figure of +0.0481 +-0.0042 "
                 "was measured with the card drawing twice", signal="both",
        rationale=(
            "A MEMBER OF THE DECK'S TOP CANDIDATE SET, not its first: inside "
            "the bars of Traveling Chocobo (+0.0291) and Nissa Resurgent "
            "Animist (+0.0285). Still the purest attack on the CARD constraint "
            "that §0z4 and §0z21 both identified. The 2026-09-16 number was "
            "measured on code where The Great Henge's draw had been swallowed "
            "into this card's branch (§0z28), so it drew two cards per "
            "creature; the corrected row is 42% smaller."),
        evidence=(
            "diagnostics/run_guardian_henge.py, results/guardian_henge.txt: "
            "damage +2.13 +-0.23, cards_drawn +2.53 +-0.14, "
            "guardian_project_draws 2.76/game, henge_draws 0.00, "
            "landfall_triggers +0.91 +-0.08, lands_played +0.43 +-0.04, "
            "P(deploy) 0.315. The counters now cross-check: cards_drawn is "
            "within a cascade of the card's OWN counter and the other card's "
            "counter is zero. The §0z25 'upper bound' compared "
            "guardian_project_draws to eligible ETBs and could not see a "
            "draw credited to henge_draws -- check cards_drawn against the "
            "SUM of every draw counter, not against one."),
        limits=(
            "THE NAME CLAUSE IS INERT IN A SINGLETON LIST and that is why the "
            "two counts are equal. 'If it doesn't have the same name as "
            "another creature you control or a creature card in your "
            "graveyard' can only ever SUPPRESS a draw, and in a 100-card "
            "singleton deck whose copies are all TOKENS there is nothing for "
            "it to suppress. Read this number as 'draw a card whenever a "
            "nontoken creature enters', which is what the card is here. "
            "A CEILING for queued item 17's reason -- nothing in this project "
            "loses to decking -- though at ~26 cards drawn from a 99-card "
            "library that gap is not close to binding. "
            "(ITEM 17 CLOSED 2026-09-22, §0z42: decking loses now and "
            "Guardian Project's draw is mandatory, so this row predates the "
            "rule and a staging would re-measure it.) "
            "NOT A STAGING: §0e, it needs a head-to-head against a named cut, "
            "and it shares the Sylvan Library baseline with thirteen others."),
    ),
    Candidate(
        deck="azusa", card="Zendikar's Roil", measured="2026-09-16",
        win_rate="+0.0133 +-0.0029 at T20 (N=15,000 paired)", signal="both",
        rationale=(
            "A second Rampaging Baloths on a deck averaging 23 landfall "
            "triggers a game. Mid-table: it would rank around Springheart "
            "Nantuko and the staged Ka-Zar."),
        evidence=("damage +1.67 +-0.17, P(deploy) 0.283. landfall_triggers "
                  "-0.21 and cards_drawn -0.24, both small and NEGATIVE -- it "
                  "adds bodies, not engine, and costs a card slot that was "
                  "drawing."),
        limits=("DELIBERATELY REDUNDANT with Rampaging Baloths and Scute "
                "Swarm. Leave-one-out understates every member of an "
                "interchangeable set, so ablate the three together before "
                "cutting any of them -- pass a list of names to ablate(). "
                "THIS ROW IS A FLOOR (§0z101): the card was missing from "
                "azusa.LAND_ENABLERS when it was measured, so it was cast "
                "after the turn's land drops. RE-MEASURED 2026-10-03 in the "
                "same slot: +0.0179 +-0.0033 at T20 "
                "(results/candidates_azusa_batch6_T20.txt), and the fix alone "
                "is +0.0053 +-0.0024, paired (results/roil_enabler.txt)."),
    ),
    Candidate(
        deck="azusa",
        card="The Great Henge",
        measured="2026-09-10",
        win_rate="+0.0217 +-0.0034 at T20 (damage +1.85 +-0.21)",
        signal="both",
        rationale=(
            "THE COST REDUCTION IS THE CARD. {7}{G}{G} minus the greatest "
            "power you control, which in this list is routinely 5-10 and is "
            "the land count whenever Ashaya or Greensleeves is out -- so it "
            "resolves in 28.1% of games on turn 9.3, the rate of a four-drop "
            "rather than a nine-drop. What it then does is draw: 7.65 cards "
            "per resolution off 'whenever a nontoken creature you control "
            "enters', plus 1.46 life from tapping it at end of turn."
        ),
        evidence=(
            "N=15,000 paired, T20, value over a replacement-level slot in the "
            "Sylvan Library slot. tools/candidates.py azusa3; "
            "results/candidates_azusa_batch3_T20.txt. Mechanisms in "
            "results/azusa_batch3_mechanisms.txt. §0z4."
        ),
        limits=(
            "The ETB is hooked in make_permanent rather than resolve, so it "
            "fires for TUTORED creatures too, which is correct and is queued "
            "item 16 from the other side. Answered by the pod 7.5% of the time."
        ),
        verdict=(
            "Clears the realistic cut bar (Titania +0.0015, Yavimaya Elder "
            "+0.0027, Life from the Loam +0.0045) comfortably. It is INSIDE "
            "the bars of Nissa, Wildspeaker and Sapling Nursery, so it is a "
            "member of a set of four and not the best of them."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Nissa, Who Shakes the World",
        measured="2026-09-10",
        win_rate="+0.0215 +-0.0036 at T20 (damage +2.40 +-0.25, highest of the seven)",
        signal="both",
        rationale=(
            "A MANA CARD THAT PASSES, and the exception that proves the "
            "batch's rule. The static doubler is worth +19.95 mana spent per "
            "resolution across 21 Forests, and what the deck converts that "
            "into is LANDFALL: +3.59 triggers a resolution, plus an ultimate "
            "that fires in 41% of the games she resolves in and puts every "
            "Forest left in the library onto the battlefield at once."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z4."
        ),
        limits=(
            "Needed a change to the SHARED engine.spend -- one Forest covers "
            "two units, the Crypt Ghast branch already there -- because a "
            "doubler implemented only in the mana pool taps two Forests to "
            "make the two mana one of them made. check_unchanged_decks.py "
            "reports all six decks bit-identical. Her emblem cannot matter "
            "(nothing in this pod kills lands) and the +1's vigilance is "
            "inert in an engine that never blocks; both are floors, both tiny."
        ),
        verdict=(
            "Same set as The Great Henge. Note she is NOT a land-drop card: "
            "lands_played goes DOWN 0.16. She is mana and landfall."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Return of the Wildspeaker",
        measured="2026-09-10",
        win_rate="+0.0197 +-0.0033 at T20 (damage +1.83 +-0.20)",
        signal="both",
        rationale=(
            "Instant-speed draw in the deck whose one measured weakness is "
            "cards. The DRAW mode is chosen essentially always -- 0.10 pumps "
            "per resolution -- because the pump only wins when it kills "
            "somebody the raw attack would not."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z4."
        ),
        limits=(
            "ITS NUMBER IS A CEILING AND THIS IS THE ONE TO READ BEFORE "
            "ACTING ON IT. The card ASKS FOR 30.0 CARDS a resolution and "
            "RECEIVES 7.8, because the greatest power among non-Human "
            "creatures on a Craterhoof-pumped Scute Swarm board runs into the "
            "hundreds -- and `draw()` stops at an empty library while NOTHING "
            "IN THIS PROJECT LOSES TO DECKING. Median ask 9, mean 40, 9% of "
            "resolutions ask for 50+. At a table those are the games you win "
            "on the spot or lose on the next draw step; here the tail is "
            "free. Queued item 17. Also a floor in the other direction: it is "
            "an INSTANT and this engine casts it at sorcery speed. "
            "ITEM 17 CLOSED 2026-09-22 (§0z42): the tail is no longer free -- "
            "a draw from an empty library loses -- and the mode is now chosen "
            "like a pilot would, PUMP whenever the draw would empty the "
            "library. This row was measured before either, so it is stale in "
            "both directions and must be re-measured before any staging."
        ),
        verdict=(
            "Good on the median case -- nine cards for five mana is good on "
            "its own -- and the measured figure is not the median case. If "
            "one of the four is to be discounted, it is this one."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Sapling Nursery",
        measured="2026-09-10",
        win_rate="+0.0170 +-0.0034 at T20 (damage +2.14 +-0.23)",
        signal="both",
        rationale=(
            "Affinity for Forests makes an eight-drop a {G}{G} to {3}{G}{G} "
            "enchantment in a list with 21 Forests, and landfall then makes a "
            "3/4 reach Treefolk per land -- the Rampaging Baloths shape, "
            "doubled by Ancient Greenwarden."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z4."
        ),
        limits=(
            "IT MAKES THE DECK'S BEST CARD WORSE, which no leave-one-out "
            "table can see. landfall_triggers -0.87 and tokens_made -11.55 "
            "per resolution -- its own Treefolk are counted in that, so Scute "
            "Swarm is making ~14 fewer Insects. The mechanism is sequencing: "
            "even reduced, the Nursery costs mana and a turn, and against an "
            "exponential payoff a small delay compounds. FLOOR: the {1}{G} "
            "exile-for-indestructible is not modelled and is real protection "
            "against a pod that wipes. RE-MEASURED 2026-10-03 in the same "
            "slot as an anchor for azusa batch 6 (§0z101): +0.0189 +-0.0036 "
            "at T20, inside this row's bar "
            "(results/candidates_azusa_batch6_T20.txt)."
        ),
        verdict=(
            "Still worth its slot on the objective. Worth knowing that the "
            "cost is paid by Scute Swarm rather than by the slot it takes."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Finale of Devastation",
        measured="2026-09-10",
        win_rate="+0.0073 +-0.0025 at T20 (damage +0.76 +-0.14)",
        signal="both",
        rationale=(
            "A creature tutor straight to the battlefield, from the library "
            "AND the graveyard -- and 35% of its targets do come from the "
            "yard, which is the real difference from Green Sun's Zenith."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z4."
        ),
        limits=(
            "X IS FIXED AT 6, the convention Genesis Wave (6) and Animist's "
            "Awakening (4) already use, so this is an APPROXIMATION rather "
            "than a floor or a ceiling: a real pilot scales X to the mana, "
            "and this deck has a lot of it. The X>=10 team pump is not "
            "modelled at all."
        ),
        verdict=(
            "The likeliest reason it scores here is REDUNDANCY, not weakness: "
            "Green Sun's Zenith (+0.0166), Woodland Bellower (+0.0119) and "
            "Chord of Calling (+0.0097) already tutor creatures, and a fourth "
            "finds what the first three did. Same shape as Ka-Zar being a "
            "fourth top-of-library enabler. Clears the cut bar, but only "
            "against the weakest rows, and the fixed X is load-bearing."
        ),
    ),
    Candidate(
        deck="azusa",
        card="War Room",
        measured="2026-09-10",
        win_rate="+0.0052 +-0.0031 at T20 (damage +0.51 +-0.18)",
        signal="both",
        rationale=(
            "A colourless land that draws, repeatably, for {3} and a tap and "
            "one life -- mono-green, so the life cost is one. 0.91 draws a "
            "game. Measured against a FOREST, which is the slot it takes."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z4."
        ),
        limits=(
            "Its life payment is REAL and charged, which makes it one of the "
            "few life costs in this project that is not free (§0i) -- and "
            "final_life still goes UP +0.74, because the cards end games "
            "sooner than the life costs. A 14th colourless-only land in a "
            "deck with {G}{G} costs is a real cost and the engine does model "
            "it."
        ),
        verdict=(
            "DIRECTLY COMPARABLE to the §0z3 sac-lands, which were measured "
            "in the same Forest slot: Scene of the Crime +0.0096 (committed), "
            "Horizon of Progress +0.0081, Cryptic Caves +0.0068, War Room "
            "+0.0052, The Hunter Maze +0.0039. It is repeatable where they "
            "are one-shot and it still lands fourth, for §0z3's reason -- "
            "{3} AND a tap is the dearest activation of the five, so it fires "
            "least. The tap is the binding constraint."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Castle Garenbrig",
        measured="2026-09-10",
        win_rate="-0.0029 +-0.0032 at T20 (damage +0.03 +-0.19)",
        signal="--",
        rationale=(
            "'{2}{G}{G}, {T}: Add six {G}' -- six, not the four it is usually "
            "remembered as -- spendable only on creature spells."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z4."
        ),
        limits=(
            "FULLY MODELLED, including the restricted pool and the "
            "enters-tapped-unless-you-control-a-Forest condition. This is not "
            "an unmeasured card."
        ),
        verdict=(
            "THE ONLY ROW OF THE SEVEN INSIDE ITS OWN BAR, and the mechanism "
            "says why rather than leaving it to noise: it activates 0.81 "
            "times a game, spends 3.72 of the six {G} it makes, and "
            "mana_spent goes DOWN 9.68 per resolution. This deck is "
            "CARD-limited, not mana-limited -- 2.77 land drops granted a turn "
            "against 1.33 used -- so more mana buys nothing. Do not add it, "
            "and note the number is a measurement rather than a blank: the "
            "card works and the deck does not want it."
        ),
    ),
    # --- 2026-09-13 fourth batch, six cards. Measured in the SAME Sylvan
    # Library slot as the seven above and at the same N and horizon, so the
    # thirteen rows are on one scale -- which is also why none of them can be
    # ranked against each other beyond their bars (§0e). §0z21.
    Candidate(
        deck="azusa",
        card="Nissa, Resurgent Animist",
        measured="2026-09-13",
        win_rate="+0.0285 +-0.0041 at T20 (damage +2.65 +-0.28)",
        signal="both",
        rationale=(
            "A RITUAL THAT ALSO DRAWS. 'Landfall -- whenever a land you "
            "control enters, add one mana of any color' is +19.75 mana per "
            "resolution in a deck making three land drops a turn; the reveal "
            "adds +1.52 cards per resolution. Note the doubler interaction "
            "the rules give for free: 'the SECOND TIME this ability has "
            "RESOLVED this turn' means that with Greenwarden or Chocobo out "
            "the first land already gets there."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as Traveling Chocobo above. §0z21. "
            "HEAD-TO-HEAD 2026-09-20 (§0z35, "
            "diagnostics/run_azusa_head2head.py, "
            "results/azusa_head2head.txt): the REAL SWAP "
            "-Yavimaya Elder +Nissa, Resurgent Animist -- the SAME CUT the "
            "owner chose for Chocobo, not the Wayward Swordtooth named below "
            "-- is +0.0280 [+0.0249, +0.0312] at T10 and "
            "+0.0266 [+0.0223, +0.0309] at T20. Against Chocobo's +0.0253 / "
            "+0.0265 in the identical slot, and directly paired against it, "
            "the two are indistinguishable (see the verdict)."
        ),
        limits=(
            "THE REVEAL IS NARROWER THAN IT READS: the second resolution and "
            "ONLY the second, so a three-drop turn is three mana and ONE card, "
            "not three cards. It whiffs 0.17 times per resolution -- the deck "
            "holds ten Elf or Elemental cards, generated into "
            "decks/_evasion.py from Scryfall rather than typed by hand. "
            "'Any color' is offered as any colour and is {G} in practice. "
            "Answered by the pod 12.5% of the time."
        ),
        verdict=(
            "Would rank 8th of 44 by win rate, in a set with Traveling "
            "Chocobo and four committed cards. Both clear the deck's cut bar "
            "-- Yavimaya Elder +0.0023, Wayward Swordtooth +0.0038, Titania "
            "+0.0050 -- by a wide margin. The proposed cut below is a "
            "PROPOSAL: pairing two rows that share a baseline is not a "
            "measurement of the swap (§0e). "
            "MEASURED EQUAL WITH TRAVELING CHOCOBO, 2026-09-20 (§0z35): a "
            "direct paired A/B in Yavimaya Elder's slot returns "
            "+0.0001 [-0.0039, +0.0041] at T20 in Nissa's favour. THE TWO BUY "
            "DIFFERENT THINGS IN EQUAL AMOUNTS, which is why the win rates "
            "agree and the mechanism counters do not: against Chocobo, Nissa "
            "is +0.27 landfall_triggers and 6.5 LESS stranded mana a game "
            "(it ramps), while Chocobo is +0.57 cards_drawn and +9.0 "
            "final_life. Pick on which of those the list wants; the harness "
            "cannot choose."
        ),
        shortlist=(
            "is here: statistically tied with Traveling Chocobo at the top of "
            "the batch, and it attacks the deck's OWN measured weakness -- "
            "this list is card-limited, not mana-limited, and this is the only "
            "one of the six that adds a card every turn. "
            "SHORTLISTED 2026-09-14 for review, NOT decided. THE PROPOSED "
            "CUT MOVED 2026-10-03: it was Wayward Swordtooth, which the owner "
            "committed out for Mole Man (§0z101). Titania, Protector of "
            "Argoth is the next MODEL-EVALUATED row at the bottom of the table "
            "(+0.0015 +-0.0031, inside its bar) once Exploration -- which the "
            "owner is keeping -- is set aside. Still a proposal, never "
            "measured as a swap. MOVED AGAIN THE SAME DAY: THE OWNER WILL NOT "
            "CUT TITANIA (2026-10-03). Life from the Loam is the next "
            "MODEL-EVALUATED row at the bottom (+0.0039 +-0.0024) with Titania "
            "and Exploration both kept, and it shares Mole Man's graveyard-land "
            "role (§0z102). A proposal only. MEASURED THE SAME DAY: in "
            "Loam's slot Nissa is +0.0101 / +0.0136 as a swap and LOSES the "
            "slot to Mossborn Hydra, -0.0112 +-0.0030 / -0.0065 +-0.0038, "
            "paired (SIMULATED, below). AND THE OWNER COMMITTED THE HYDRA "
            "THERE (2026-10-03), so the proposal moved a third time, to "
            "Sylvan Awakening: the next MODEL-EVALUATED row at the bottom "
            "(+0.0049 +-0.0015) with Titania and Exploration kept. A proposal "
            "only; Nissa has now lost one measured slot."
        ),
        proposed_cut="Sylvan Awakening",
    ),
    Candidate(
        deck="azusa",
        card="Awaken the Woods",
        measured="2026-09-13",
        win_rate="+0.0188 +-0.0029 at T20 (damage +1.71 +-0.18)",
        signal="both",
        rationale=(
            "'Create X 1/1 green Forest Dryad LAND CREATURE tokens.' They are "
            "lands, so X of them entering is X landfall triggers off one card "
            "(+6.90 per resolution at X=6); they are Forests, so they tap for "
            "{G} (305.6) and count for Sapling Nursery and Nissa Who Shakes "
            "the World; and they are creatures, so they die to the pod's "
            "wraths and are summoning sick for their own mana ability (302.6)."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above, at the project's fixed-X "
            "convention X=6. §0z21."
        ),
        limits=(
            "X IS FIXED and that is an approximation, not a floor or a "
            "ceiling -- a real pilot scales X to the mana. Swept as the WHOLE "
            "CARD (cost and effect together) at n=4,000: X=3 +0.0163, X=4 "
            "+0.0222, X=6 +0.0215, so X IS NOT LOAD-BEARING between 4 and 6 -- "
            "a bigger X buys landfall and costs deploy rate, and the two "
            "cancel. X=8 could not be measured at all: see §0z21's "
            "`can_pay` performance cliff."
        ),
        verdict=(
            "Would rank 14th of 44, inside the bars of Courser of Kruphix, "
            "Augur of Autumn, Animist's Awakening and Lotus Cobra. An "
            "eight-drop that resolves in 27.4% of games on turn 9.7, so it is "
            "a late-game card in a deck whose games end around turn 12. "
            "SHORTLIST WITHDRAWN BY THE OWNER, 2026-10-08, for now: it was "
            "shortlisted 2026-09-14 against Kozilek, Butcher of Truth, and "
            "the §0z119 rebuild put Kozilek at +0.0116 +-0.0020 (T10) and "
            "+0.0268 +-0.0035 (T20) -- sixth in azusa at T20, up from "
            "+0.0077 once its cast draw was modelled (§0z114). The head-to-head "
            "was never run. Not refuted: the +0.0188 row above stands, and "
            "re-shortlisting it means naming a different cut."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Expedition Map",
        measured="2026-09-13",
        win_rate="+0.0133 +-0.0033 at T20 (damage +1.44 +-0.23)",
        signal="both",
        rationale=(
            "Three mana and the card itself for one land in hand, which is a "
            "rate that has to be justified by WHICH land. Here it is a FETCH: "
            "two landfall triggers and a land in the graveyard for Titania. "
            "Measured, fetches_cracked +1.25 and landfall_triggers +2.69 per "
            "resolution against 0.48 activations -- the gap is Crucible and "
            "Ramunap Excavator replaying the fetch it found."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z21."
        ),
        limits=(
            "FLOOR. The lands a pilot actually wants a tutor for -- Strip "
            "Mine, Wasteland, Ghost Quarter, Homeward Path -- are all "
            "MODEL-BLIND (§4), so the engine fetches the best MODELLED land "
            "and the card's real ceiling is not measured here. The policy "
            "(crack it only when a land drop or an empty hand can use the "
            "land) is stated in azusa.expedition_map_step."
        ),
        verdict=(
            "Would rank 25th of 44 -- mid-table, comfortably clear of the cut "
            "bar, and the honest reading is that it is a FLOOR that already "
            "clears it."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Zuran Orb",
        measured="2026-09-13",
        win_rate="+0.0124 +-0.0025 at T20 (damage +1.11 +-0.16)",
        signal="both",
        rationale=(
            "A free sacrifice outlet in a deck that wants lands in the "
            "GRAVEYARD: 3.20 lands sacrificed per resolution, each one a "
            "Titania Elemental and two life, and each one replayable while "
            "Crucible, Ramunap Excavator or Ancient Greenwarden is out -- "
            "which is another land drop and another landfall on a drop that "
            "was going begging (this deck uses 1.33 of 2.77 granted)."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z21."
        ),
        limits=(
            "FLOOR, and the missing half is WHY THE CARD IS PLAYED: it is an "
            "instant-speed outlet held up against land destruction and lethal "
            "damage, and this engine has no instant speed, no opponent land "
            "destruction and no stack to respond on. Its Ashaya interaction "
            "(creature-lands are lands you could sacrifice to it) is "
            "deliberately not offered. NEITHER KNOB IS LOAD-BEARING: "
            "zuran_keep 4/6/8 gives +0.0143/+0.0112/+0.0118 and "
            "zuran_life_floor 1/8/15 gives +0.0092/+0.0112/+0.0097, all "
            "inside each other's bars (n=4,000)."
        ),
        verdict=(
            "Would rank 26th of 44, and it is the cheapest row in the deck at "
            "MV 0. A floor that clears the cut bar on the half of the card "
            "this model can see."
        ),
    ),
    Candidate(
        deck="azusa",
        card="Archdruid's Charm",
        measured="2026-09-13",
        win_rate="+0.0082 +-0.0035 at T20 (damage +0.87 +-0.23)",
        signal="both",
        rationale=(
            "{G}{G}{G} instant, and only its first mode exists in this model: "
            "search for a creature or land, the land going to the BATTLEFIELD "
            "tapped -- a landfall trigger that costs no land drop -- and the "
            "creature only to HAND."
        ),
        evidence=(
            "N=15,000 paired, T20, same run as above. §0z21."
        ),
        limits=(
            "PARTLY MODELLED, and the weakest-supported row of the six. Modes "
            "2 and 3 (fight-removal, exile an artifact or enchantment) are "
            "MODEL-BLIND under §4 and mode 1 fetches a Forest rather than a "
            "blind utility land, so this is a FLOOR twice over; it is also an "
            "INSTANT cast at sorcery speed. AND ITS NUMBER RESTS ON A POLICY: "
            "archdruid_mode 'creature' measures +0.0130 +-0.0072 against "
            "'land' +0.0057 and the 'auto' default +0.0077 (n=4,000). The "
            "bars overlap, but the creature mode came out ahead twice and "
            "'auto' takes the land on essentially every board here."
        ),
        verdict=(
            "Would rank 37th of 44 -- above the cut bar, but only just, and "
            "on a floor. IF THIS IS EVER STAGED, RE-MEASURE THE MODE FIRST: "
            "the gap between the two pure strategies is about as large as the "
            "card's whole score."
        ),
    ),
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    Candidate(
        deck='azusa',
        card='Verdant Catacombs',
        measured="2026-10-06",
        win_rate='+0.0165 +-0.0035 at T10, +0.0188 +-0.0047 at T20 against a Forest',
        signal='both',
        rationale='A true fetch: the land drop is two landfall triggers and thins a Forest.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked +0.694, life_gained +0.184. §0z113.',
        limits="CEILING: the 1 life a true fetch pays is NOT charged (`crack_fetch`'s docstring; §0z112 lists fetches with the painlands). Only Forests are fetched -- the list has no other basic type.",
        verdict='The largest land candidate measured, significant at both horizons, in place of a Forest. Evolving Wilds and Fabled Passage, which pay no life, measure within the bar of it, so the uncharged life is not what the row is made of.',
    ),
    Candidate(
        deck='azusa',
        card='Misty Rainforest',
        measured="2026-10-06",
        win_rate='+0.0165 +-0.0035 at T10, +0.0188 +-0.0047 at T20 against a Forest',
        signal='both',
        rationale='Identical to Verdant Catacombs in this engine: same fields, same `fetch` script, the 1 life uncharged.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked +0.694, life_gained +0.184. §0z113.',
        limits="NOT RUN SEPARATELY: its games are identical to Verdant Catacombs' (the N=200 smoke run printed three equal rows), so this is Verdant's number. Same ceiling.",
        verdict='As Verdant Catacombs. A second or third fetch is NOT measured: each row is ONE fetch for ONE Forest, and leave-one-out says nothing about stacking them.',
    ),
    Candidate(
        deck='azusa',
        card='Prismatic Vista',
        measured="2026-10-06",
        win_rate='+0.0165 +-0.0035 at T10, +0.0188 +-0.0047 at T20 against a Forest',
        signal='both',
        rationale='Identical to Verdant Catacombs in this engine: same fields, same `fetch` script, the 1 life uncharged.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked +0.694, life_gained +0.184. §0z113.',
        limits='NOT RUN SEPARATELY, as Misty Rainforest. Same ceiling.',
        verdict='As Verdant Catacombs; the same caveat on stacking.',
    ),
    Candidate(
        deck='azusa',
        card='Evolving Wilds',
        measured="2026-10-06",
        win_rate='+0.0127 +-0.0034 at T10, +0.0165 +-0.0046 at T20 against a Forest',
        signal='both',
        rationale='A fetch that pays no life; the Forest enters tapped.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked +0.683, life_gained +0.086. §0z113.',
        limits='Every clause modelled -- no life cost exists to leave out.',
        verdict='Significant at both horizons, inside the bar of the true fetches: the tapped Forest costs little in a deck with extra land drops. The cleanest number of the three fetch kinds.',
    ),
    Candidate(
        deck='azusa',
        card='Fabled Passage',
        measured="2026-10-06",
        win_rate='+0.0153 +-0.0035 at T10, +0.0176 +-0.0046 at T20 against a Forest',
        signal='both',
        rationale='Evolving Wilds that untaps the Forest at four lands.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked +0.680, life_gained +0.193. §0z113.',
        limits='Every clause modelled.',
        verdict='Significant at both horizons, between Evolving Wilds and the true fetches -- and with no life cost to leave out, the best-supported row of the set.',
    ),
    Candidate(
        deck='azusa',
        card='Myriad Landscape',
        measured="2026-10-06",
        win_rate='+0.0011 +-0.0023 at T10, +0.0031 +-0.0036 at T20 against a Forest',
        signal='--',
        rationale='Enters tapped; {2}, sacrifice: two tapped Forests, two landfalls.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked -0.100, life_gained -0.078, myriad_cracked +0.129. §0z113.',
        limits='Every clause modelled. A POLICY: cracked after combat on spare mana, while a Forest is left (0.13 cracks a game).',
        verdict='Inside its bar at both horizons. Entering tapped and costing {2} later is about what two delayed landfalls are worth here.',
    ),
    Candidate(
        deck='azusa',
        card='Field of the Dead',
        measured="2026-10-06",
        win_rate='+0.0033 +-0.0024 at T10, +0.0098 +-0.0036 at T20 against a Forest',
        signal='both',
        rationale='Enters tapped; a 2/2 Zombie per landfall at seven differently named lands.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: fetches_cracked -0.095, field_zombies +2.967, life_gained -0.178. §0z113.',
        limits='Every clause modelled. 2.97 Zombies a game. Name diversity is read from the list as built: azusa has 21 Forests, so seven names come from its nonbasics.',
        verdict="Significant at both horizons (+0.0098 at T20) but half the fetches'. Damage +0.79 at T20 says the Zombies attack.",
    ),
]


CHANGES: list[Change] = [
    # -----------------------------------------------------------------------
    # AZUSA, staged 2026-09-10. Three swaps, measured together as one package
    # (`P3B` in run_azusa_animation_swap.py) as well as individually. They are
    # listed separately here because the ledger's unit is a swap, but THE
    # EVIDENCE IS THE PACKAGE -- each entry carries the package figure and
    # says so.
    # -----------------------------------------------------------------------

    Change(
        deck="azusa",
        remove="Perilous Forays",
        add="Ka-Zar of the Savage Land",
        staged="2026-09-10",
        rationale=(
            "{4}{G} 3/2. 'You may look at the top card of your library any "
            "time. You may play lands from the top of your library. When "
            "Ka-Zar enters, create Zabu, a legendary 2/2 green Cat with "
            "Landfall -- put a +1/+1 counter on Zabu.' "
            "IT WAS PICKED AS A CARD-ADVANTAGE CARD AND IT IS NOT ONE, which "
            "is the most useful thing measured about it. `cards_drawn` is "
            "+0.08 +-0.09 -- FLAT, inside its own bar. What it actually does "
            "is lands_from_library +0.34 and damage +2.53. The redundancy "
            "predicted before the run is real: top_access() is a BOOLEAN and "
            "Courser, Augur and Oracle are already in the list, so a fourth "
            "top-of-library enabler adds only the lands the other three "
            "missed. The card earns its slot as a BODY THAT GROWS -- Zabu "
            "takes a counter on every landfall in a deck averaging 21 of them "
            "-- in a deck that §0v made reward width. Staged for what it "
            "does, not for why it was chosen."
        ),
        evidence=(
            "Real swap against the STAGED list (build_pending('azusa'), i.e. "
            "the three 2026-09-10 animation swaps applied and the draw cards "
            "deliberately absent), N=15,000 paired, same seeds, "
            "run_azusa_draw.py: win rate +0.0060 +-0.0022 at T10 and +0.0141 "
            "+-0.0034 at T20, significant at both. With the draw land "
            "alongside: +0.0201 +-0.0044 at T20, additive (interaction "
            "-0.0008). "
            "THESE ARE THE CORRECTED FIGURES. A first run reported +0.0153 / "
            "+0.0253 and was WRONG: Ka-Zar had been added to "
            "azusa.DYNAMIC_PT_LANDS instead of LAND_ENABLERS by a patch whose "
            "anchor matched both sets, so its printed 3/2 was discarded and "
            "replaced by the land count -- it was measured as a 16/16. The "
            "inflation was about +0.001, so the decision survives, but the "
            "numbers are restated rather than kept. check_dynamic_pt_coverage() "
            "now raises on any card in that set not defined 0/0, and that "
            "check was mutation-tested against this exact bug. §0z3."
        ),
        notes=(
            "THE CUT IS DELIBERATELY NOT THE BEST-SCORING ONE. Ka-Zar "
            "measures +0.0253 +-0.0040 in the Bane of Progress slot against "
            "+0.0153 here -- a full point of win rate from the cut alone -- "
            "AND THAT CUT MUST NOT BE TAKEN. Bane of Progress is in "
            "SCRIPTED_AZUSA and printed under MODEL-EVALUATED, but the engine "
            "models its board wipe destroying only YOUR OWN artifacts and "
            "enchantments, because opponents own no permanent objects (§4). "
            "Its -0.0041 is a one-sided wipe with the sided-ness removed, not "
            "a bad card. It is the same trap as Ashaya (§0z) and worse, "
            "because it is the only significantly NEGATIVE row in the deck "
            "and therefore looks like the obvious cut. §0z2. "
            "Perilous Forays is signal `--` (+0.0012 +-0.0016) and is fully "
            "implemented in azusa.activations(), so cutting it is safe in the "
            "way cutting Bane is not."
        ),
        reverified="RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0049 +-0.0026 at T10, +0.0067 +-0.0033 at T20. Significant at both; the staging stands. The pod alone moved it -0.0006 +-0.0025 at T10 and -0.0054 +-0.0043 at T20 (POD_PRE_V4 at the same commit: +0.0055 / +0.0121). results/restage_item26_20261015.txt (§0z143)." + 'RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0037 +-0.0023 at T10, +0.0115 +-0.0034 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + (
            "RE-MEASURED 2026-09-26 (§0z63), N=15,000 paired: +0.0033 +-0.0022 at T10, +0.0133 +-0.0035 at T20. The staging stands. results/restage_20260926.txt."
        + ' ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0034 +-0.0022 at T10, +0.0130 +-0.0035 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81)."),
    ),
    Change(
        deck="azusa",
        remove="Forest",
        add="Fabled Passage",
        staged="2026-10-06",
        rationale=(
            "'{T}, Sacrifice this land: Search your library for a basic land "
            "card, put it onto the battlefield tapped, then shuffle. Then if "
            "you control four or more lands, untap that land.' Two landfall "
            "triggers from one land drop in a landfall deck, a Forest thinned "
            "from the library, and a land in the graveyard for the recursion "
            "package -- for no life."
        ),
        evidence="N=15,000 paired, seeds 5000.., the staged list on the engine with Eye of Ugin's tutor and Kozilek's cast draw (§0z114), one T20 game per seed with T10 read off it. diagnostics/run_eye_of_ugin.py, results/eye_of_ugin_20261006.txt. THE PAIR, measured as one change (both Changes applied, the first two Forests in list order): +0.0257 +-0.0048 at T10 and +0.0237 +-0.0061 at T20, damage +1.93, fetches_cracked +1.23 and landfall_triggers +1.70 a game. Alone: Fabled Passage +0.0157 +-0.0036 / +0.0179 +-0.0047, Evolving Wilds +0.0126 +-0.0035 / +0.0158 +-0.0047. The pair is SUBADDITIVE at T20 (+0.0237 against +0.0337 summed) -- the second fetch is worth less than the first -- and is still significant at both horizons. §0z113 measured each alone on the old engine at the same size.",
        reverified="RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0072 +-0.0040 at T10, +0.0091 +-0.0049 at T20 alone; the pair (both fetches) +0.0157 +-0.0052 / +0.0191 +-0.0062. Significant at both; the staging stands. The pod's move is inside its bar: -0.0017 / -0.0025 alone, -0.0007 / +0.0001 for the pair. results/restage_item26_20261015.txt (§0z143)." + ("RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0138 +-0.0036 at T10, +0.0117 +-0.0048 at T20 alone; the pair (both fetches) +0.0257 +-0.0047 / +0.0257 +-0.0061. Significant at both; the staging stands. results/restage_20261007.txt."),
        notes="THE OWNER'S CHOICE, 2026-10-06, of the two fetches that pay no life -- every clause of both is modelled, so neither row is a ceiling, unlike the true fetches (whose 1 life the engine does not charge). Verdant Catacombs, Misty Rainforest and Prismatic Vista measured inside the same bar and were not chosen. A BASIC-LAND CUT, but land for land: the land count is unchanged at 100 cards, so the 'harness flatters land cuts' caveat (a land cut that lowers the count) does not apply. Forests 20 -> 18 after both. Gaea's Cradle and Ancient Tomb were deferred by the owner the same day on price, not on the number.",
    ),
    Change(
        deck="azusa",
        remove="Forest",
        add="Evolving Wilds",
        staged="2026-10-06",
        rationale=(
            "'{T}, Sacrifice this land: Search your library for a basic land "
            "card, put it onto the battlefield tapped, then shuffle.' Fabled "
            "Passage without the untap: the same two landfalls for no life."
        ),
        evidence="N=15,000 paired, seeds 5000.., the staged list on the engine with Eye of Ugin's tutor and Kozilek's cast draw (§0z114), one T20 game per seed with T10 read off it. diagnostics/run_eye_of_ugin.py, results/eye_of_ugin_20261006.txt. THE PAIR, measured as one change (both Changes applied, the first two Forests in list order): +0.0257 +-0.0048 at T10 and +0.0237 +-0.0061 at T20, damage +1.93, fetches_cracked +1.23 and landfall_triggers +1.70 a game. Alone: Fabled Passage +0.0157 +-0.0036 / +0.0179 +-0.0047, Evolving Wilds +0.0126 +-0.0035 / +0.0158 +-0.0047. The pair is SUBADDITIVE at T20 (+0.0237 against +0.0337 summed) -- the second fetch is worth less than the first -- and is still significant at both horizons. §0z113 measured each alone on the old engine at the same size.",
        reverified="RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0071 +-0.0041 at T10, +0.0105 +-0.0050 at T20 alone; the pair (both fetches) +0.0157 +-0.0052 / +0.0191 +-0.0062. Significant at both; the staging stands. The pod's move is inside its bar: +0.0011 / +0.0054 alone, -0.0007 / +0.0001 for the pair. results/restage_item26_20261015.txt (§0z143)." + ("RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0079 +-0.0037 at T10, +0.0063 +-0.0049 at T20 alone; the pair (both fetches) +0.0257 +-0.0047 / +0.0257 +-0.0061. Significant at both; the staging stands. results/restage_20261007.txt."),
        notes="THE OWNER'S CHOICE, 2026-10-06, of the two fetches that pay no life -- every clause of both is modelled, so neither row is a ceiling, unlike the true fetches (whose 1 life the engine does not charge). Verdant Catacombs, Misty Rainforest and Prismatic Vista measured inside the same bar and were not chosen. A BASIC-LAND CUT, but land for land: the land count is unchanged at 100 cards, so the 'harness flatters land cuts' caveat (a land cut that lowers the count) does not apply. Forests 20 -> 18 after both. Gaea's Cradle and Ancient Tomb were deferred by the owner the same day on price, not on the number.",
    ),
]


WITHDRAWN: list[Change] = []


SIMULATED: list[Simulated] = [
    Simulated(
        deck='azusa', remove='Titania, Protector of Argoth', add='Autumn Willow, Harmony',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Titania, Protector of Argoth +Autumn Willow, Harmony, N=15,000 paired: +0.0047 +-0.0020 (significant) at T10 and +0.0024 +-0.0031 (inside its bar) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0046 +-0.0019 * at T10 and +0.0016 +-0.0031 at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s. THE OWNER WILL NOT CUT TITANIA (2026-10-03): this head-to-head stands as a measurement, and its cut is not available.'),
    ),
    Simulated(
        deck='azusa', remove='Yavimaya Elder', add='Verdant Kraken',
        measured='2026-09-21', source='results/azusa_fra.txt',
        result=('REAL SWAP -Yavimaya Elder +Verdant Kraken, N=15,000 paired: +0.0163 +-0.0024 at T10 and +0.0265 +-0.0037 at T20, significant at both. Against the Chocobo in the same slot: -0.0049 +-0.0029 at T10 (significant) and +0.0007 +-0.0042 at T20 (inside its bar).'),
    ),
    Simulated(
        deck='azusa', remove='Yavimaya Elder', add='Simulacrum Shaper',
        measured='2026-09-21', source='results/azusa_fra.txt',
        result=('REAL SWAP -Yavimaya Elder +Simulacrum Shaper, N=15,000 paired: +0.0040 +-0.0019 at T10 and +0.0035 +-0.0033 at T20, significant at both. Against the Chocobo in the same slot: -0.0173 +-0.0027 / -0.0223 +-0.0040, significant at both.'),
    ),
    # AZUSA BATCH 6 (§0z101), 2026-10-03. The real swap against the OWNER'S
    # NAMED CUT, Wayward Swordtooth, N=15,000 paired, seeds 5000.., T10 read off
    # the T20 game. All seven cut the same card, so these rows share a baseline
    # and §0e forbids ranking them by their bars; each is a decision against
    # Swordtooth, and none is taken.
    Simulated(
        deck='azusa', remove='Wayward Swordtooth', add='Elfsworn Giant',
        measured='2026-10-03', source='results/azusa_batch6_h2h.txt',
        result='REAL SWAP -Wayward Swordtooth +Elfsworn Giant, N=15,000 paired: +0.0033 +-0.0023 (significant) at T10 and +0.0121 +-0.0035 (significant) at T20; damage +0.95 +-0.21.',
        notes='4.0 Elf Warriors a game. 1/1s are the thinnest payoff of the seven: the same slot, cards and seeds give Chocobo Racetrack more than twice the T20 number.',
    ),
    Simulated(
        deck='azusa', remove='Wayward Swordtooth', add='Chocobo Racetrack',
        measured='2026-10-03', source='results/azusa_batch6_h2h.txt',
        result='REAL SWAP -Wayward Swordtooth +Chocobo Racetrack, N=15,000 paired: +0.0134 +-0.0026 (significant) at T10 and +0.0276 +-0.0038 (significant) at T20; damage +2.15 +-0.24.',
        notes="3.6 Birds and 39.7 Bird pumps a game: each Bird's own landfall trigger is most of the card. Zendikar's Roil with tokens that grow.",
    ),
    Simulated(
        deck='azusa', remove='Wayward Swordtooth', add='Dancing from Dark to Dawn',
        measured='2026-10-03', source='results/counter_spread.txt',
        result="REAL SWAP -Wayward Swordtooth +Dancing from Dark to Dawn, N=15,000 paired: +0.0078 +-0.0024 (significant) at T10 and +0.0245 +-0.0038 (significant) at T20 under counter_target='spread', the default.",
        notes="3.9 Bears and 5.0 cast-trigger counters a game. Under the first policy, 'focus', it was +0.0066 +-0.0024 / +0.0206 +-0.0037 (results/azusa_batch6_h2h.txt); spread minus focus is +0.0039 +-0.0015 at T20, paired on the same seeds.",
    ),
    Simulated(
        deck='azusa', remove='Wayward Swordtooth', add='Mossborn Hydra',
        measured='2026-10-03', source='results/azusa_batch6_h2h.txt',
        result='REAL SWAP -Wayward Swordtooth +Mossborn Hydra, N=15,000 paired: +0.0315 +-0.0031 (significant) at T10 and +0.0304 +-0.0039 (significant) at T20; damage +3.06 +-0.25.',
        notes='4.2 doublings a game. The strongest T10 row of the seven for a three-drop: it is a trampler, so the counters it doubles get through the chump blocks that blunt the other big bodies.',
    ),
    Simulated(
        deck='azusa', remove='Life from the Loam', add='Nissa, Resurgent Animist',
        measured='2026-10-03', source='results/azusa_slot_loam_20261003.txt',
        result='REAL SWAP -Life from the Loam +Nissa, Resurgent Animist, N=15,000 paired, on the list WITH Mole Man (§0z102): +0.0101 +-0.0030 (significant) at T10 and +0.0136 +-0.0041 (significant) at T20; damage +1.32 +-0.28.',
        notes=('AND IT LOSES THE SLOT TO MOSSBORN HYDRA, measured directly (diagnostics/run_slot_pair.py, three legs on one seed set): Nissa minus Hydra in Loam\'s slot is -0.0112 +-0.0030 at T10 and -0.0065 +-0.0038 at T20, significant at both. '
               'Nissa keeps more of what Loam did -- +0.39 lands played, +1.05 landfall triggers and +1.19 cards a game over the Hydra -- and still loses, because the Hydra turns the lands the deck has into damage (+1.13 a game over Nissa). 5.45 Animist rituals and 0.54 cards found a game.'),
    ),
    Simulated(
        deck='azusa', remove='Wayward Swordtooth', add='Bristly Bill, Spine Sower',
        measured='2026-10-03', source='results/counter_spread.txt',
        result="REAL SWAP -Wayward Swordtooth +Bristly Bill, Spine Sower, N=15,000 paired: +0.0098 +-0.0024 (significant) at T10 and +0.0113 +-0.0035 (significant) at T20 under counter_target='spread', the default.",
        notes="Under the first policy, 'focus' (counters on an evasive or the biggest creature), it was +0.0011 +-0.0023 / +0.0009 +-0.0035, INSIDE ITS BAR (results/azusa_batch6_h2h.txt). The owner predicted the fix: one huge creature does little without evasion, and the pod chump-blocks the biggest attackers. Spread minus focus is +0.0105 +-0.0021 at T20, paired, with the same number of counters placed (4.0 against 4.2 a game) -- the policy, not the card, was the gap.",
    ),
    Simulated(
        deck='azusa', remove='Wayward Swordtooth', add='Glacier Godmaw',
        measured='2026-10-03', source='results/azusa_batch6_h2h.txt',
        result='REAL SWAP -Wayward Swordtooth +Glacier Godmaw, N=15,000 paired: +0.0228 +-0.0030 (significant) at T10 and +0.0265 +-0.0042 (significant) at T20; damage +2.34 +-0.26.',
        notes='17 summoning-sick creatures a game attack because of its haste -- the landfall tokens made this turn. The Lander is a footnote (0.14 cracked a game). A seven-drop, so P(cast) is the lowest of the seven (0.260).',
    ),
]


PROPOSED: list[Proposal] = [
    Proposal(
        deck='azusa', card='Autumn Willow, Harmony', cost='{3}{G}{G}',
        identity='G', type_line='Legendary Creature — Avatar',
        oracle="Hexproof\nWhen Autumn Willow enters, create a 1/1 green Forest Dryad land creature token. (It's affected by summoning sickness.)\nWhenever you tap a land creature for mana, add an additional {G}.",
        verified="2026-09-29",
        rationale='Its ETB is a Forest Dryad LAND token -- a landfall trigger on the turn it lands -- and its static is a mana doubler for every land creature: Dryad Arbor, the Dryad tokens, animated lands, and with Ashaya out every nontoken creature in the deck.',
        implement="DONE 2026-09-29. The token is Awaken the Woods' (`azusa.forest_dryad_tokens`, one definition now for both cards); the extra {G} is offered in `azusa.available_mana` at all three places a land creature taps (as a land, as an Ashaya dork, as an Ashaya Forest) with the SAME owner so one tap covers both, and in `engine.spend`'s count fallback -- a doubler said in both places (§0z4). `willow_taps` is counted at the tap, not where the unit is offered. PARTLY: HEXPROOF is not modelled -- the pod's spot removal targets it like any creature. Classify PARTLY_MODELLED at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Titania, Protector of Argoth is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck="azusa", card="Verdant Kraken", cost="{4}{G}{G}{G}",
        identity="G", type_line="Creature — Plant Kraken",
        oracle=("At the beginning of each player's upkeep, you create a 3/3 "
                "green Forest Tentacle land creature token. (It has "
                "\"{T}: Add {G}.\" It's affected by summoning sickness until "
                "your next turn.)"),
        verified="2026-09-20",
        rationale=(
            "FOUR LANDFALL TRIGGERS A ROUND off one card, in the deck whose "
            "every payoff reads `land_entered`. The token has all four of the "
            "properties that make Awaken the Woods' token the card it is: it "
            "is a LAND (a landfall trigger each), a FOREST (taps for {G}, and "
            "counts for Sapling Nursery's affinity and Nissa Who Shakes the "
            "World's doubler), a CREATURE (dies to the pod's wraths, and adds "
            "board threat that draws removal at you) and SICK until your next "
            "turn. The difference from Awaken is that this is a RATE, not a "
            "one-off -- and three of the four arrive on turns that are not "
            "yours, which is why it had to be wired at the pod's block too."),
        implement=("DONE 2026-09-20. `azusa.verdant_kraken_tokens(upkeeps)` "
                   "reuses awaken_the_woods' four properties rather than "
                   "restating them (§0u); called with 1 at your upkeep in "
                   "take_turn and with 3 immediately before OPP.pod_phase, so "
                   "the pod's tokens exist while the pod acts. Pinned by "
                   "tests/test_fra_azusa.py."),
        rejected=(
            'MEASURED 2026-09-21 and PROMOTED on 2026-09-25: the real-swap numb'
            'er is now a Candidate in MEASURED, with whether it still describes'
            ' the deck today. Closed rather than deleted so the verified oracle'
            ' text stays where it was written (§0z45).'
        ),
    ),
    Proposal(
        deck="azusa", card="Simulacrum Shaper", cost="{1}{G}{G}",
        identity="G", type_line="Creature — Elf Druid",
        oracle=("When this creature enters, you may search your library for a "
                "basic land card, put that card onto the battlefield tapped, "
                "then shuffle.\n"
                "When this creature dies, draw a card."),
        verified="2026-09-20",
        rationale=(
            "A three-mana body that ramps AND replaces itself. The ETB is a "
            "landfall trigger on the turn it lands, which is this deck's whole "
            "engine, and the land arrives TAPPED so it is a trigger and a free "
            "land drop rather than a ritual. The death trigger is what makes "
            "it more than a worse Wood Elves in a pod that wraths."),
        implement=("DONE 2026-09-20. ETB in `make_permanent` in ITS OWN `if` "
                   "beside The Great Henge and Guardian Project -- §0z28 is "
                   "the finding that says why that matters -- and the death "
                   "trigger in `on_creature_death` beside Yavimaya Elder's, "
                   "outside the `for _ in range(n)` loop because one permanent "
                   "triggers once. Pinned by tests/test_fra_azusa.py."),
        rejected=(
            'MEASURED 2026-09-21 and PROMOTED on 2026-09-25: the real-swap numb'
            'er is now a Candidate in MEASURED, with whether it still describes'
            ' the deck today. Closed rather than deleted so the verified oracle'
            ' text stays where it was written (§0z45).'
        ),
    ),
    Proposal(
        deck="azusa", card="Guardian Project", cost="{3}{G}", identity="G",
        type_line="Enchantment",
        oracle=("Whenever a nontoken creature you control enters, if it "
                "doesn't have the same name as another creature you control "
                "or a creature card in your graveyard, draw a card."),
        verified="2026-09-16",
        rationale=("§0z4 and §0z21's standing finding is that every card "
                   "attacking azusa's CARD constraint passed and the one pure "
                   "MANA card failed. This is a card-advantage engine, and "
                   "§0z18 made NONTOKEN CREATURES ENTERING fire 6.65 times a "
                   "resolution through Ashaya -- so the trigger condition is "
                   "one the engine now models richly."),
        implement=("LOW-MEDIUM. The nontoken-ETB hook is exactly what §0z18 "
                   "built. The same-name clause needs a real check against "
                   "battlefield AND graveyard, and Scute Swarm's copies are "
                   "TOKENS, so they must not trigger it."),
        rejected='MEASURED 2026-09-16 and PROMOTED to MEASURED: +0.0279 +-0.0036 win rate at T20, N=15,000, Sylvan Library slot -- CORRECTED from +0.0481 in §0z28, which is where the §0z25 number went wrong. See the Candidate entry.',
    ),
    Proposal(
        deck="azusa", card="Splendid Reclamation", cost="{3}{G}", identity="G",
        type_line="Sorcery",
        oracle="Return all land cards from your graveyard to the battlefield tapped.",
        verified="2026-09-16",
        rationale=("A landfall burst that reads the deck's OWN graveyard-land "
                   "package: Life from the Loam, Ramunap Excavator, Crucible "
                   "of Worlds and Titania are all already in the list, and "
                   "Titania reads land deaths directly (§0z18). Each returned "
                   "land is a separate landfall trigger into Scute Swarm."),
        implement=("LOW-MEDIUM. Landfall is the best-modelled mechanism in "
                   "this engine. The lands enter TAPPED, which matters: §0z3 "
                   "found the TAP was the binding constraint on the "
                   "sacrifice-lands, not the mana."),
        rejected="MEASURED 2026-09-16: -0.0013 +-0.0022 at T20 -- INSIDE ITS BAR, a blank. The mechanism explains it and the proposal's own rationale was BACKWARDS: max lands in the graveyard across a whole game is 1.1, because Life from the Loam, Ramunap Excavator and Crucible of Worlds recycle them straight back out. Those cards COMPETE with this one for the same resource rather than feeding it. Not refuted as a card, refuted as a fit for THIS list.",
    ),
    Proposal(
        deck="azusa", card="Zendikar's Roil", cost="{3}{G}{G}", identity="G",
        type_line="Enchantment",
        oracle=("Landfall — Whenever a land you control enters, create a 2/2 "
                "green Elemental creature token."),
        verified="2026-09-16",
        rationale=("A second Rampaging Baloths on a deck averaging 21 landfall "
                   "triggers a game. Deliberately REDUNDANT with Baloths and "
                   "Scute Swarm, so ablate the three together -- "
                   "leave-one-out understates every member of an "
                   "interchangeable set."),
        implement="LOW. Landfall token payoffs are existing machinery.",
        rejected='MEASURED 2026-09-16 and PROMOTED: +0.0133 +-0.0029 at T20 (§0z25).',
    ),
    # -----------------------------------------------------------------------
    # AZUSA BATCH 6, 2026-10-03: seven LANDFALL PAYOFFS, picked by the owner
    # from a Scryfall scan of every Commander-legal card with landfall-type text
    # in mono-green identity (91 cards, 15 already known to the repo). The
    # question is §0z100's: the landfall group's returns diminish by about 0.8
    # a copy, so is a further payoff still worth a slot? Oracle text fetched
    # from api.scryfall.com the same day. The owner's named cut for the
    # head-to-heads is Wayward Swordtooth (2026-10-03).
    # -----------------------------------------------------------------------
    Proposal(
        deck='azusa', card='Elfsworn Giant', cost='{3}{G}{G}',
        identity='G', type_line='Creature — Giant',
        oracle='Reach (This creature can block creatures with flying.)\nLandfall — Whenever a land you control enters, create a 1/1 green Elf Warrior creature token.',
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale="A token per landfall on a 5/3 body: the Rampaging Baloths shape at 1/1, one mana cheaper. The closest-in-shape card to the landfall group whose returns curve §0z100 measured (each further copy about 0.8 of the last), so it is the cleanest test of whether that curve's extrapolated fifth copy (+0.029 at T20) is real for a card that is not Scute Swarm.",
        implement="LOW. One `make_tokens` line in `_landfall_payoffs`, the Baloths pattern. REACH IS NOT MODELLED -- this engine's blockers are a count, not a defence that reads reach -- so the body is a 5/3. A Springheart host (nonlegendary landfall payoff).",
    ),
    Proposal(
        deck='azusa', card='Chocobo Racetrack', cost='{3}{G}{G}',
        identity='G', type_line='Artifact',
        oracle='Landfall — Whenever a land you control enters, create a 2/2 green Bird creature token with "Whenever a land you control enters, this token gets +1/+0 until end of turn."',
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale="Zendikar's Roil (+0.0133 +-0.0029, §0z25) with tokens that grow: every Bird gets +1/+0 for each LATER land that turn, so on a three-drop turn the first Bird attacks as a 4/2. The deck averages three landfall triggers a turn, which is exactly what the token's own trigger reads.",
        implement='LOW-MEDIUM. The token maker is the Roil line. Each Bird token carries its OWN landfall trigger, so the +1/+0 is applied per Bird that was on the battlefield WHEN the land entered (a snapshot -- a Bird made by this land does not see it, §0z19), doubled by Greenwarden and Traveling Chocobo like any landfall trigger. Until end of turn, reset with the turn.',
    ),
    Proposal(
        deck='azusa', card='Dancing from Dark to Dawn', cost='{3}{G}{G}',
        identity='G', type_line='Enchantment',
        oracle="Whenever you cast a creature spell, put X +1/+1 counters on target creature you control, where X is that spell's mana value.\nLandfall — Whenever a land you control enters, create a 2/2 green Bear creature token.",
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale="Zendikar's Roil with a second engine attached: every creature SPELL puts counters equal to its mana value on a creature you control. This list casts Ulamog and Kozilek (MV 11 and 10) and averages several creature spells a game, so the cast trigger is large on its own.",
        implement="MEDIUM. Landfall half: a 2/2 Bear per landfall, the Roil line. Cast half: a hook at the two places a creature SPELL is cast (the commander, and the main-phase loop including Augur of Autumn's top-of-library cast) -- NOT on Chord, Green Sun's Zenith, Finale or Genesis Wave, which put a creature onto the battlefield without casting it. The trigger fires on CAST, so a countered spell still triggers. Target policy shared with Bristly Bill (`counter_target`).",
    ),
    Proposal(
        deck='azusa', card='Mole Man, Moloid Master', cost='{2}{G}',
        identity='G', type_line='Legendary Creature — Human Villain',
        oracle='You may play lands from your graveyard.\nLandfall — Whenever a land you control enters, create a 1/1 green Minion creature token named Moloid with "Whenever this token attacks, you may mill a card."',
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale="Three mana for a token per landfall AND 'play lands from your graveyard' -- the half §0z99 said the deck is short of: it lacks LANDS to play, not permission. The graveyard clause duplicates Crucible of Worlds and Ramunap Excavator (a boolean), so expect that half to add only the games neither is out.",
        implement="LOW-MEDIUM. Graveyard access joins the existing boolean in `playable_lands`. Landfall: a 1/1 Moloid token. 'Whenever this token attacks, you MAY mill a card' is modelled as a POLICY: mill only while graveyard-land access is live and a land drop is still unused this turn, so a milled land can be played in the second land step; never below a library floor (decking is a loss, §0z42). Legendary, so not a Springheart host.",
    ),
    Proposal(
        deck='azusa', card='Mossborn Hydra', cost='{2}{G}',
        identity='G', type_line='Creature — Elemental Hydra',
        oracle="Trample (This creature can deal excess combat damage to the player or planeswalker it's attacking.)\nThis creature enters with a +1/+1 counter on it.\nLandfall — Whenever a land you control enters, double the number of +1/+1 counters on this creature.",
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale='A three-drop trampler whose counters DOUBLE on every landfall: 1, 2, 4 on the turn after it lands, 16 or more by the next. Greenwarden and Traveling Chocobo each add a doubling. It is the one candidate whose value is exponential in landfall rather than linear, so it tests a different part of the curve.',
        implement="LOW. 'Enters with a +1/+1 counter' is applied in `make_permanent`, so tutors, Genesis Wave and Springheart copies all get it (defined 0/0, so `check_dynamic_pt_coverage` must learn the enters-with-counters set). Trample is generated from Scryfall. Doubling is ordered AFTER every counter-placing trigger of the same land (Bristly Bill's), as a pilot stacks it. A runaway cap on the counter count is a guard, not a rule. The pod's threat-weighted removal will meet it, which is a real cost the model sees.",
    ),
    Proposal(
        deck='azusa', card='Bristly Bill, Spine Sower', cost='{1}{G}',
        identity='G', type_line='Legendary Creature — Plant Druid',
        oracle='Landfall — Whenever a land you control enters, put a +1/+1 counter on target creature.\n{3}{G}{G}: Double the number of +1/+1 counters on each creature you control.',
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale="A two-drop that turns every landfall into a +1/+1 counter, and a five-mana activation that DOUBLES the counters on every creature you control -- Avenger's Plants already carry one per landfall. The activation is a mana sink in a deck that measurably strands mana late (stranded_mv, mana_floated).",
        implement='MEDIUM. Landfall: one counter on a creature you control, chosen by `counter_target` (a stated policy: Mossborn Hydra first, then an evasive creature, then the highest power). Activation: before combat, with mana the main phase left, while your creatures carry at least `bristly_min_counters` counters (a knob, default 2). FIXES A GAP IT DEPENDS ON: `power_of` discarded +1/+1 counters on the */* cards (Greensleeves, Ashaya, Cultivator Colossus); a counter now adds. Legendary, so not a Springheart host.',
    ),
    Proposal(
        deck='azusa', card='Glacier Godmaw', cost='{5}{G}{G}',
        identity='G', type_line='Creature — Leviathan',
        oracle='Trample\nWhen this creature enters, create a Lander token. (It\'s an artifact with "{2}, {T}, Sacrifice this token: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.")\nLandfall — Whenever a land you control enters, creatures you control get +1/+1 and gain vigilance and haste until end of turn.',
        verified="2026-10-03",
        triage="LIVE",
        prepared="tests/test_azusa_batch6.py",
        rejected="MEASURED 2026-10-03 and PROMOTED: a Candidate in MEASURED and the real swap against Wayward Swordtooth in SIMULATED (§0z101). Closed rather than deleted so the verified oracle text stays where it was written.",
        rationale="A repeatable Craterhoof for this deck: every landfall gives the whole team +1/+1 and HASTE until end of turn, so the Beasts, Badgers, Insects and Plants made by this turn's land drops attack the turn they are made. Its ETB Lander token is a further land (and a further landfall) for {2}.",
        implement="MEDIUM-HIGH, and it builds two pieces the engine lacks: per-permanent until-end-of-turn pumps and haste (an id-keyed map, safe since §0z100's hold), read by `power_of` and by `combat`'s summoning-sickness check; and the Lander token, an artifact cracked BEFORE combat for {2} (a basic onto the battlefield tapped, then shuffle -- through the CRN stream). The pump is ordered LAST among the land's triggers, so tokens made by the same land get it. VIGILANCE IS NOT MODELLED and cannot matter here: `opponents.your_creatures` counts tapped blockers too. Trample is generated.",
    ),
    # ---- REJECTED, kept so they are not proposed again -------------------
    Proposal(
        deck="azusa", card="Felidar Retreat", cost="{3}{W}", identity="W",
        type_line="Enchantment",
        oracle=("Landfall — Whenever a land you control enters, choose one —\n"
                "• Create a 2/2 white Cat Beast creature token.\n"
                "• Put a +1/+1 counter on each creature you control. Those "
                "creatures gain vigilance until end of turn."),
        verified="2026-09-16",
        rationale="Landfall token/counter payoff; mechanically a good fit.",
        implement="n/a",
        rejected=("ILLEGAL. Colour identity W, and Azusa is mono-GREEN. "
                  "Proposed from memory before the identity was checked, and "
                  "caught by `check_proposals`. This is why that check "
                  "exists."),
    ),
    Proposal(
        deck="azusa", card="Omnath, Locus of Rage", cost="{3}{R}{R}{G}{G}",
        identity="GR", type_line="Legendary Creature — Elemental",
        oracle=("Landfall — Whenever a land you control enters, create a 5/5 "
                "red and green Elemental creature token.\n"
                "Whenever Omnath or another Elemental you control dies, Omnath "
                "deals 3 damage to any target."),
        verified="2026-09-16",
        rationale="The strongest landfall token payoff in the colour pair.",
        implement="n/a",
        rejected=("ILLEGAL. Colour identity GR, and Azusa is mono-GREEN. Same "
                  "failure as Felidar Retreat, same run."),
    ),
    # LAND CANDIDATES, 2026-10-06 (§0z113): the owner asked for lands that would
    # help each deck except trostani, after the land ablation (§0z112). Oracle
    # text from api.scryfall.com the same day.
    Proposal(
        deck='azusa', card='Verdant Catacombs',
        cost='', identity='',
        type_line='Land',
        oracle='{T}, Pay 1 life, Sacrifice this land: Search your library for a Swamp or Forest card, put it onto the battlefield, then shuffle.',
        verified='2026-10-06',
        rationale="A fetch for a Forest is two landfall triggers, and azusa's three fetches are its best land rows in the land ablation (§0z112): Windswept Heath +0.0196, Wooded Foothills +0.0161, Terramorphic +0.0154 at T20, each against a Forest.",
        implement='Defined as `L(..., script="fetch")`: azusa.crack_fetch already fetches a Forest for any land with that script. The 1 life is NOT charged -- the same CEILING as the deck\'s two true fetches today.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='azusa', card='Misty Rainforest',
        cost='', identity='',
        type_line='Land',
        oracle='{T}, Pay 1 life, Sacrifice this land: Search your library for a Forest or Island card, put it onto the battlefield, then shuffle.',
        verified='2026-10-06',
        rationale='As Verdant Catacombs: a second true fetch for a Forest, two landfalls (§0z112).',
        implement='`script="fetch"`, nothing else. Its 1 life is uncharged, a CEILING, as for the deck\'s own fetches.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='azusa', card='Prismatic Vista',
        cost='', identity='',
        type_line='Land',
        oracle='{T}, Pay 1 life, Sacrifice this land: Search your library for a basic land card, put it onto the battlefield, then shuffle.',
        verified='2026-10-06',
        rationale='As Verdant Catacombs: any basic is a Forest in a mono-green list, two landfalls (§0z112).',
        implement='`script="fetch"`. 1 life uncharged, a CEILING.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='azusa', card='Evolving Wilds',
        cost='', identity='',
        type_line='Land',
        oracle='{T}, Sacrifice this land: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.',
        verified='2026-10-06',
        rationale="Terramorphic Expanse's twin, and Terramorphic is +0.0154 at T20 against a Forest (§0z112): two landfalls, the Forest tapped.",
        implement='The fetched land enters TAPPED: azusa.crack_fetch decided that by the name Terramorphic Expanse, so it reads a `fetch_tapped` tag now for both. No life cost: exact.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='azusa', card='Fabled Passage',
        cost='', identity='',
        type_line='Land',
        oracle='{T}, Sacrifice this land: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle. Then if you control four or more lands, untap that land.',
        verified='2026-10-06',
        rationale='Two landfalls like every fetch, and from the fourth land on the Forest arrives untapped -- a free Evolving Wilds that grows into a true fetch (§0z112).',
        implement='crack_fetch: tapped, then untapped when you control four or more lands (`fetch_untap4`). No life cost: exact.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='azusa', card='Myriad Landscape',
        cost='', identity='',
        type_line='Land',
        oracle='This land enters tapped.\n{T}: Add {C}.\n{2}, {T}, Sacrifice this land: Search your library for up to two basic land cards that share a land type, put them onto the battlefield tapped, then shuffle.',
        verified='2026-10-06',
        rationale="THREE landfalls from one land drop (itself, then two Forests), at the price of {2} and tempo; azusa's fetches are its best land rows (§0z112).",
        implement='New script `myriad`: enters tapped, taps for {C}; at the end step on leftover mana, {2}, {T}, sacrifice: two Forests from the library, tapped, two landfall triggers. Every clause modelled.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='azusa', card='Field of the Dead',
        cost='', identity='',
        type_line='Land',
        oracle='This land enters tapped.\n{T}: Add {C}.\nWhenever this land or another land you control enters, if you control seven or more lands with different names, create a 2/2 black Zombie creature token.',
        verified='2026-10-06',
        rationale='A landfall TOKEN engine in a landfall deck with 21 nonbasic lands of distinct names: seven names is reached early, and every land after that is a 2/2 body.',
        implement="New: in azusa's land-entered hook, if Field of the Dead is on the battlefield and you control lands with seven or more different names, create a 2/2 black Zombie. Enters tapped, taps for {C}. Every clause modelled.",
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    # STAR TREK, 2026-10-23 (the owner's set review). Oracle text from
    # api.scryfall.com the same day.
    Proposal(
        deck='azusa', card='Captain Pike, Fullness of Time', cost='{1}{G}{G}',
        identity='G', type_line='Legendary Creature — Human Officer Scout',
        oracle="Strange new worlds — Captain Pike's power and toughness are each equal to the number of differently named lands you control.\nYou may look at the top card of your library any time.\nYou may play lands from the top of your library.",
        verified='2026-10-23',
        rationale="Top-of-library land plays for three mana, the zone grant Courser of Kruphix, Augur of Autumn and Oracle of Mul Daya are already paid for -- with Azusa's three drops a turn, each land off the top is a card the hand keeps. The body scales with the deck's spread of land names.",
        implement="azusa.top_access gains Pike (and LAND_ENABLERS, so he deploys before the drops). The */* is a new name set, DYNAMIC_PT_NAMED_LANDS, read by power_of/toughness_of from `named_land_count` (distinct names among lands and Ashaya's creature-lands) and covered by check_dynamic_pt_coverage. 'Look at the top card any time' is information the pilot already acts on. Redundant with the four top-access cards in the list: leave-one-out will understate it (§0z27).",
        triage='LIVE',
    ),
]


# Added 2026-09-07 as a sixth deck. The submitted list was 99 cards; a
# 21st Forest was added to reach 100 -- see azusa_v1.py's docstring.
CATALOG = (azusa_v1, {
    # Ancient Greenwarden, Greensleeves and Springheart Nantuko were here
    # until 2026-09-10 and are now COMMITTED as of azusa_v1.py, so they are
    # in the deck list itself and no longer swap-in candidates. Same for
    # Scene of the Crime. Ka-Zar is still STAGED, so it stays.
    # 2026-09-16 batch 5 (§0z25), measured and catalogued so a
    # Change can name them without a later edit nobody remembers.
    "Guardian Project": azusa_v1.GUARDIAN_PROJECT,
    "Zendikar's Roil": azusa_v1.ZENDIKARS_ROIL,
    "Splendid Reclamation": azusa_v1.SPLENDID_RECLAMATION,
    "Conduit of Worlds": azusa_v1.CONDUIT_OF_WORLDS,
    "Cultivator Colossus": azusa_v1.CULTIVATOR_COLOSSUS,
    "Case of the Locked Hothouse": azusa_v1.CASE_OF_THE_LOCKED_HOTHOUSE,
    "Walk-In Closet // Forgotten Cellar": azusa_v1.WALK_IN_CLOSET,
    "Ka-Zar of the Savage Land": azusa_v1.KA_ZAR,
    "Cryptic Caves": azusa_v1.CRYPTIC_CAVES,
    "Horizon of Progress": azusa_v1.HORIZON_OF_PROGRESS,
    "The Hunter Maze": azusa_v1.THE_HUNTER_MAZE,
    # 2026-09-10 third batch (§0z4). MEASURED, NOT STAGED -- they are here
    # so that a Change naming one can be written the day somebody decides
    # to, and being in this catalog is not a decision: the four cards
    # above it that lost their comparisons are still here too.
    "Return of the Wildspeaker": azusa_v1.RETURN_OF_THE_WILDSPEAKER,
    "Finale of Devastation": azusa_v1.FINALE_OF_DEVASTATION,
    "The Great Henge": azusa_v1.THE_GREAT_HENGE,
    "Sapling Nursery": azusa_v1.SAPLING_NURSERY,
    "Nissa, Who Shakes the World": azusa_v1.NISSA_WHO_SHAKES_THE_WORLD,
    "War Room": azusa_v1.WAR_ROOM,
    "Castle Garenbrig": azusa_v1.CASTLE_GARENBRIG,
    # 2026-09-13 fourth batch (§0z21). Same status as the seven above:
    # MEASURED, NOT STAGED, listed here only so a Change naming one can be
    # written the day somebody decides to.
    "Nissa, Resurgent Animist": azusa_v1.NISSA_RESURGENT_ANIMIST,
    "Traveling Chocobo": azusa_v1.TRAVELING_CHOCOBO,
    "Archdruid's Charm": azusa_v1.ARCHDRUIDS_CHARM,
    "Awaken the Woods": azusa_v1.AWAKEN_THE_WOODS,
    "Expedition Map": azusa_v1.EXPEDITION_MAP,
    "Zuran Orb": azusa_v1.ZURAN_ORB,
    # REALITY FRACTURE, 2026-09-20 (preview text; the set releases
    # 2026-10-02). Implemented and pinned, measured against the cut §0z35
    # established for this deck.
    "Verdant Kraken": azusa_v1.VERDANT_KRAKEN,
    "Simulacrum Shaper": azusa_v1.SIMULACRUM_SHAPER,
    # MYSTERY BOOSTER COMMANDER EDITION, 2026-09-29 (§0z74).
    "Autumn Willow, Harmony": azusa_v1.AUTUMN_WILLOW_HARMONY,
    # 2026-10-03 sixth batch (§0z101): seven landfall payoffs, catalogued
    # so a head-to-head Change can name them.
    "Elfsworn Giant": azusa_v1.ELFSWORN_GIANT,
    "Chocobo Racetrack": azusa_v1.CHOCOBO_RACETRACK,
    "Dancing from Dark to Dawn": azusa_v1.DANCING_FROM_DARK_TO_DAWN,
    "Mole Man, Moloid Master": azusa_v1.MOLE_MAN,
    "Mossborn Hydra": azusa_v1.MOSSBORN_HYDRA,
    "Bristly Bill, Spine Sower": azusa_v1.BRISTLY_BILL,
    "Glacier Godmaw": azusa_v1.GLACIER_GODMAW,
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    **{c.name: c for c in azusa_v1.LAND_CANDIDATES},
    # STAR TREK, 2026-10-23 (the owner's set review).
    "Captain Pike, Fullness of Time": azusa_v1.CAPTAIN_PIKE})
