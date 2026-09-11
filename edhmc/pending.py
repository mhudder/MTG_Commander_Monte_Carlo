"""
edhmc.pending — staged deck changes, not yet written to the spreadsheets.

The .xlsx files remain the system of record. This module holds changes that
have been decided but not yet applied to all three legs (deck module, .xlsx,
this ledger), so that:

  1. further A/B tests run against the CURRENT intended list rather than a
     stale baseline, and
  2. there is one place to read off the full pending diff when it is time to
     update the spreadsheets.

Usage:
    from edhmc.pending import build_pending, ledger
    deck, commander = build_pending("rendmaw")     # changes applied
    deck, commander = build_pending("rendmaw", apply_pending=False)  # original
    ledger()                                       # print the diff

To stage another change, append to CHANGES. To commit, update the spreadsheet
and the deck module, then move the entry to COMMITTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from edhmc.decks import (rendmaw_v12, lorehold_v16, karlov_v2, tivit_v1,
                         shilgengar_v1, azusa_v1)
from edhmc.experiment import _swap_many


@dataclass
class Change:
    deck: str
    remove: str
    add: str
    staged: str                 # date staged
    rationale: str
    evidence: str = ""
    notes: str = ""
    reverified: str = ""        # re-measured after an engine change


# ---------------------------------------------------------------------------
# Committed — reflected in BOTH the deck module and the .xlsx
# ---------------------------------------------------------------------------
COMMITTED: list[Change] = [
    Change(
        deck="lorehold",
        remove="Triumph of Saint Katherine",
        add="The Dawning Archaic",
        staged="2026-08-31",
        rationale=(
            "Weakest miracle hit in the deck replaced by its cheapest late-game "
            "haymaker. A 5/5 lifelink body is a poor payoff in a deck whose "
            "miracle targets are 7-12 MV spells, and its death trigger shuffles "
            "the top six cards of the library, which is where this deck keeps "
            "its resources."
        ),
        evidence=(
            "12,000 paired games, 14 turns, mixed pod: mv_cheated +2.46 "
            "[+2.28, +2.64]. Archaic's cost reduction leaves it at ~{2.45} "
            "effective, since the deck averages 8.5 instants/sorceries in the "
            "graveyard by turn 14."
        ),
        notes=(
            "Damage -0.52 and P(win) flat. Taken for the mana-cheat and "
            "top-end case, not for speed. This was the narrower, "
            "better-supported half of the four-card change originally "
            "considered; Molecule Man was NOT taken and Verge Rangers stays."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Monologue Tax",
        add="Arcane Bombardment",
        staged="2026-08-31",
        rationale=(
            "Bombardment reads 'your first instant or sorcery each turn', not "
            "each of YOUR turns. Lorehold's rummage opens a miracle window on "
            "all three opponents' turns, so a round can produce four triggers "
            "instead of one, and the exile pile accumulates so the Nth trigger "
            "copies all N cards."
        ),
        evidence=(
            "6,000 paired games vs the pending v16 list, 14 turns, mixed pod: "
            "mv_cheated +7.24 [+4.74, +10.05], damage +5.17 [+3.22, +7.43], "
            "win rate +0.01 [+0.00, +0.01]."
        ),
        notes=(
            "HIGH VARIANCE. Fires in only 7.9% of games; when it does it "
            "averages 13.2 free copies (max observed 136). Median damage barely "
            "moves while the mean jumps - the whole gain is in the top decile. "
            "Also strongly horizon-dependent: near zero at 10 turns, large at "
            "14+. Monologue Tax was modelled generously at 2 Treasures a round "
            "for three opponents and still lost."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Urabrask // The Great Work",
        add="Monastery Mentor",
        staged="2026-08-31",
        rationale=(
            "A body-count fix for a deck with only eleven creatures and a "
            "top-heavy curve. Nearly every spell here is noncreature, so Mentor "
            "converts the deck's existing spell density into a board."
        ),
        evidence=(
            "6,000 paired games vs the pending v16 list, 14 turns: damage +4.42 "
            "[+3.74, +5.12], combat damage +4.95, win rate +0.01 [+0.01, +0.02]. "
            "mv_cheated -0.14, i.e. it contributes bodies, not mana."
        ),
        notes=(
            "Urabrask was UNDER-modelled in earlier ablations - its 1 damage per "
            "instant/sorcery and its {R} mana ability were not implemented, which "
            "is why it scored near zero. Both are now in the engine; cutting it "
            "costs 0.53 spell damage. It lost anyway. Tension to watch: the deck "
            "runs eight board wipes, which kill your own Monks. The engine does "
            "not model your own wipes hitting your board, so Mentor is flattered "
            "here to an unknown degree."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Hidden Retreat",
        add="Double Vision",
        staged="2026-09-01",
        rationale=(
            "Same 'each turn' clause that makes Arcane Bombardment strong here: "
            "Lorehold's rummage opens a window on all three opponents' turns, so "
            "a round can produce four triggers instead of one. It copies the "
            "miracled spell too, so a ten-drop miracled for {2} becomes two. "
            "Hidden Retreat's cost is not mana but a CARD - putting one on top "
            "converts your next draw into something you already held."
        ),
        evidence=(
            "8,000 paired games, mixed pod: win rate +0.017 [+0.012, +0.021], "
            "mv_cheated +3.16 [+2.63, +3.68], damage +2.74 [+1.45, +4.03], "
            "cards drawn +0.79. Double Vision resolves in 17.2% of games on turn "
            "9.7 and averages 2.39 copies when it does; answered only 28.3% of "
            "the time, against 57% for Bombardment."
        ),
        notes=(
            "The copy is PUT ON THE STACK, not cast (ruling 2020-06-23), so it "
            "does NOT trigger Guttersnipe, Monastery Mentor or Bombardment - "
            "unlike Mastery's and Bombardment's copies, which are genuinely "
            "cast. That reduction is already priced in. Note also that roughly "
            "half the gain is Hidden Retreat being bad rather than Double Vision "
            "being good: against a same-cost blank, Double Vision's win-rate "
            "contribution does not clear its error bar."
        ),
    ),
    Change(
        deck="rendmaw",
        remove="Skullclamp",
        add="March of the World Ooze",
        staged="2026-08-31",
        rationale=(
            "Skullclamp has almost no fodder here: Rendmaw's Birds are 2/2, and "
            "the clamp makes them 3/1, so they live. It finds a legal "
            "1-toughness target on 0.35 turns per game. Cutting it was "
            "justified independently of the replacement."
        ),
        evidence=(
            "20,000 paired games, 10 turns, mixed pod: damage +2.85 "
            "[+2.64, +3.06], cards drawn -1.01 [-1.06, -0.96]."
        ),
        notes=(
            "The margin shrinks as the pod gets stronger: +5.86 damage at all "
            "bracket 2, +1.09 at all bracket 4, where it is close to a wash "
            "against the card-draw loss. March is also answered ~57% of the "
            "times you deploy it, against ~15% for Skullclamp. Worth "
            "revisiting if the regular pod is high-powered."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-03 on the oracle-corrected engine, because "
            "the original evidence predates that audit and both cards were "
            "touched by it. 6,000 paired games, mixed pod: at 10 turns damage "
            "+3.02 [+2.57, +3.48] and win rate +0.0077 [+0.0053, +0.0101]; at "
            "20 turns damage +2.79 [+2.17, +3.40] and win rate +0.0018 "
            "[-0.0041, +0.0077], i.e. inside its bar at the long horizon. "
            "Sign and rank survive the whole horizon range, and damage and "
            "cards drawn both land within a rounding error of the original "
            "(+2.85 and -1.01). The decision stands."
        ),
    ),
    Change(
        deck="karlov",
        remove="Swamp",
        add="Starscape Cleric",
        staged="2026-09-04",
        rationale=(
            "Marauding Blight-Priest's trigger word for word — 'whenever you "
            "gain life, each opponent loses 1 life' — at half the mana, on a "
            "two-power flier. This deck produces 16+ lifegain EVENTS a game "
            "and each one is 3 pod life, so the rate matters far more than the "
            "body. It out-damages every card in ablation_karlov.txt: +4.13 "
            "over a blank at 10 turns against Kambal's +3.64."
        ),
        evidence=(
            "Measured as the real 2-for-2 (this and Enduring Tenacity in, a "
            "Swamp and Whispersilk Cloak out), 6,000 paired games, mixed pod: "
            "win rate +0.0353 [+0.0297, +0.0413] at 10 turns and +0.0480 "
            "[+0.0400, +0.0558] at 20; damage +6.94 and +7.05. Alone against a "
            "blank of the same cost it is +4.13+-0.46 damage and +0.0118+-"
            "0.0035 win at 10 turns, both signals at both horizons."
        ),
        notes=(
            "FLOOR in two places. Flying is unmodelled anywhere in the engine "
            "(queued work item 1), and its Offspring cost is paid in only 25% "
            "of casts because the greedy main phase has usually spent the mana "
            "already. Its 'can't block' drawback is also unmodelled, but the "
            "engine never blocks with your creatures, so that costs it "
            "nothing it would otherwise have. The land cut is the real price: "
            "stranded_mv +1.85 at 10 turns. 37 lands -> 36."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, which is now the DEFAULT pod (combat_targeting='open', incidental_rate=1.0, clock_shift=2, archetypes on) and the first pod model in which your life total is load-bearing. Measured as the same 3-for-3, 6,000 paired games: win rate +0.0362 [+0.0300, +0.0425] at 10 turns and +0.0638 [+0.0550, +0.0727] at 20; damage +6.89 and +7.68. Against +0.0397 and +0.0617 on the old pod, and +0.0483 / +0.0773 on pod v2 without archetypes. Significant at both horizons on every pod tried. The package adds two blockers and a lifelinker to a deck that now takes real attacks, so it holds up precisely where the modelling got better. Decision stands."
        ),
    ),
    Change(
        deck="karlov",
        remove="Whispersilk Cloak",
        add="Enduring Tenacity",
        staged="2026-09-04",
        rationale=(
            "A FOURTH Exquisite Blood combo piece, which is the larger half of "
            "its value. Its trigger is Sanguine Bond's word for word ('whenever "
            "you gain life, target opponent loses that much life'), so it loops "
            "with Exquisite Blood unaided and with no mana; karlov.COMBO_LOOP "
            "was corrected to include it. It assembles the loop in 8.8% of the "
            "games it resolves. Whispersilk Cloak ablates to +0.32/+0.25 "
            "damage and -0.0007 win rate — inside its own bars, and three "
            "other shroud sources remain (Swiftfoot Boots, Mother of Runes, "
            "Lightning Greaves)."
        ),
        evidence=(
            "Against a blank of the same cost, 6,000 paired games: win rate "
            "+0.0195 [+0.0154, +0.0236] at 10 turns and +0.0217 [+0.0163, "
            "+0.0271] at 20; damage +2.74 and +2.48. That win rate would rank "
            "FOURTH in the whole deck, behind only Felidar Sovereign "
            "(+0.0587), Exquisite Blood (+0.0242) and Vito (+0.0228)."
        ),
        notes=(
            "This is the ADDITION measurement, so the redundancy with Sanguine "
            "Bond and Vito is already priced in — unlike leave-one-out, which "
            "understates every member of an interchangeable group. Its death "
            "trigger fires 0.60 times a game: it returns as a noncreature "
            "enchantment and keeps draining through a wrath."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, which is now the DEFAULT pod (combat_targeting='open', incidental_rate=1.0, clock_shift=2, archetypes on) and the first pod model in which your life total is load-bearing. Measured as the same 3-for-3, 6,000 paired games: win rate +0.0362 [+0.0300, +0.0425] at 10 turns and +0.0638 [+0.0550, +0.0727] at 20; damage +6.89 and +7.68. Against +0.0397 and +0.0617 on the old pod, and +0.0483 / +0.0773 on pod v2 without archetypes. Significant at both horizons on every pod tried. The package adds two blockers and a lifelinker to a deck that now takes real attacks, so it holds up precisely where the modelling got better. Decision stands."
        ),
    ),
    Change(
        deck="karlov",
        remove="Lightning Greaves",
        add="Exemplar of Light",
        staged="2026-09-04",
        rationale=(
            "Lightning Greaves is the worst card in the deck by win rate "
            "(-0.0040+-0.0029, signal 'both') and the only one whose damage is "
            "negative at both horizons. Cutting it still leaves Swiftfoot "
            "Boots and Mother of Runes as shroud sources for the commander. "
            "Exemplar of Light takes a +1/+1 counter per lifegain EVENT — 16.3 "
            "of them a game — and draws a card the first time each turn it "
            "gets one, so it is a threat and a draw engine off the same "
            "trigger the whole deck is built on."
        ),
        evidence=(
            "Measured as the real 3-for-3 alongside the two changes above "
            "(Swamp, Whispersilk Cloak and Lightning Greaves out; Starscape "
            "Cleric, Enduring Tenacity and Exemplar of Light in), 6,000 paired "
            "games: win rate +0.0397 [+0.0335, +0.0463] at 10 turns and "
            "+0.0617 [+0.0527, +0.0707] at 20, against +0.0353 and +0.0480 "
            "for the 2-for-2 without it. Damage +8.40 and +9.23. Alone against "
            "a blank of the same cost, +2.11+-0.47 damage and +0.0090+-0.0046 "
            "win rate at 20 turns."
        ),
        notes=(
            "COST, measured: this is the swap that strands mana. stranded_mv "
            "+5.56 at 10 turns for the 3-for-3 against +1.85 for the 2-for-2 "
            "— a four-drop replacing a two-drop on top of the Swamp already "
            "cut. Watch the curve if the deck starts stumbling. Its flying is "
            "unmodelled (queued work item 1), so the body is a floor."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, which is now the DEFAULT pod (combat_targeting='open', incidental_rate=1.0, clock_shift=2, archetypes on) and the first pod model in which your life total is load-bearing. Measured as the same 3-for-3, 6,000 paired games: win rate +0.0362 [+0.0300, +0.0425] at 10 turns and +0.0638 [+0.0550, +0.0727] at 20; damage +6.89 and +7.68. Against +0.0397 and +0.0617 on the old pod, and +0.0483 / +0.0773 on pod v2 without archetypes. Significant at both horizons on every pod tried. The package adds two blockers and a lifelinker to a deck that now takes real attacks, so it holds up precisely where the modelling got better. Decision stands."
        ),
    ),
    # -----------------------------------------------------------------------
    # AZUSA, committed 2026-09-10. TWO LEGS, not three: this deck has no
    # .xlsx, so `edhmc/decks/azusa_v1.py` IS the system of record and these
    # four are applied there. The fifth 2026-09-10 swap -- Perilous Forays
    # -> Ka-Zar of the Savage Land -- is deliberately LEFT STAGED and is
    # still in CHANGES below.
    # -----------------------------------------------------------------------
    Change(
        deck="azusa",
        remove="Sylvan Awakening",
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
]

# ---------------------------------------------------------------------------
# Staged — decided, not yet in the spreadsheets
# ---------------------------------------------------------------------------
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
    ),

    Change(
        deck="rendmaw",
        remove="Idol of Oblivion",
        add="Cauldron of Essence",
        staged="2026-09-04",
        rationale=(
            "Cauldron's drain half is The Meathook Massacre's text word for "
            "word — 'each opponent loses 1 life and you gain 1 life' — so it "
            "is 3 pod life per creature death in a deck that loses a dozen "
            "tokens a game: 12.4 drain damage per game it resolves. Its second "
            "half is a repeatable sac outlet AND recursion (0.55 reanimations "
            "a game), stocked mostly by the pod's own wraths, which is exactly "
            "when you want it. Idol of Oblivion is a noncreature artifact that "
            "ablates inside its own error bars, so cutting it costs no body."
        ),
        evidence=(
            "Measured as the real swap under POD v3 (the current default), "
            "6,000 paired games: win rate +0.0027 [+0.0007, +0.0048] at 10 "
            "turns and +0.0135 [+0.0088, +0.0182] at 20; damage +0.95 and "
            "+1.03. Significant on both metrics at both horizons."
        ),
        notes=(
            "THE CUT CHANGED, and this is the clearest thing the new pod model "
            "has produced. The original staging cut Ornithopter of Paradise, "
            "which measured fine on the old pod (+0.0025 / +0.0158) and then "
            "DECAYED as the model improved: v2 +0.0018 / +0.0155, v3 -0.0015 "
            "[-0.0037, +0.0007] / +0.0088. The mechanism is that Ornithopter "
            "is a 0/2 BODY as well as a dork and Cauldron is not a creature — "
            "under pod v3 creatures attack whoever cannot block, so a spare "
            "blocker is worth something the old pod priced at exactly zero. "
            "Controlled check, same card in, three different cuts, pod v3, "
            "20 turns: cutting the noncreature Idol +0.0135 [+0.0088, +0.0182]; "
            "cutting the 0/2 Ornithopter +0.0088 [+0.0038, +0.0138]; cutting "
            "the 1/2 Dockside Chef +0.0048 [+0.0000, +0.0097]. Monotonic in "
            "whether the cut was a body. "
            "COSTS, both measured and both real: Cauldron is one card type, so "
            "the swap still loses a commander trigger, and Idol is this deck's "
            "token-payoff draw engine — tokens_made -0.15. "
            "SEPARATELY: the engine models Blood Artist at 3x its real drain, "
            "which inflates the baseline Cauldron is measured alongside. "
            "Cauldron's 3.0 is the one of the two that is correct."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-09 on the post-combat-split engine "
            "(KNOWN_ISSUES.md §0v), because that change moved 16 of rendmaw's "
            "64 ablation rows and this swap's evidence predates it. Measured "
            "at the SAME N=6,000 and the same seeds as the original, so any "
            "difference is the engine and not the sample: win rate +0.0022 "
            "[+0.0007, +0.0038] at 10 turns and +0.0152 [+0.0107, +0.0198] at "
            "20, against the original +0.0027 [+0.0007, +0.0048] and +0.0135 "
            "[+0.0088, +0.0182]. Both horizons reproduce inside their own "
            "bars and both remain significant; the T20 point estimate rose "
            "slightly. Every mechanism counter kept its sign and rough "
            "magnitude too — damage +1.55, cards_drawn -0.26, tokens_made "
            "-0.16, stranded_mv +1.15 — so the predicted costs are still "
            "real and still outweighed. The decision stands. "
            "diagnostics/run_swaps_0904.py, results/staged_recheck_rendmaw.txt."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Penance",
        add="Caldera Pyremaw",
        staged="2026-09-05",
        rationale=(
            "Closes queued work item 3. THE CUT was decided long ago and is "
            "well supported; THE REPLACEMENT changed on 2026-09-05 from "
            "Galvanoth to Caldera Pyremaw, measured head to head. Penance is "
            "a FREE top-setter — the card on top IS the cost — and that is "
            "exactly the problem: it converts a draw step into re-drawing a "
            "card you already held, and only 26% of the time can you actually "
            "pay the {2} to miracle what it put there. The other 74% is "
            "straight card disadvantage. Caldera Pyremaw is a {3}{R}{R} 3/3 "
            "FLIER that puts a +1/+1 counter on itself and then deals damage "
            "equal to its power to an opponent on every instant or sorcery you "
            "cast — so the first trigger already hits for 4, and it scales "
            "with exactly the thing this deck does most."
        ),
        evidence=(
            "THREE-WAY, same cut, same seeds, 6,000 paired games each, pod v3 "
            "(run_fivedrop.py). Win rate at 10 / 20 turns: Caldera Pyremaw "
            "+0.0035 [+0.0012, +0.0060] / +0.0202 [+0.0150, +0.0257]; "
            "Galvanoth +0.0020 [-0.0002, +0.0043] / +0.0128 [+0.0078, "
            "+0.0180]; Radiant Scrollwielder +0.0015 [-0.0008, +0.0038] / "
            "+0.0125 [+0.0075, +0.0178]. Caldera is the only one of the three "
            "significant at BOTH horizons. "
            "HEAD TO HEAD, which is the number the decision rests on because "
            "three swaps against a common baseline have overlapping CIs and "
            "cannot be ranked against each other: -Galvanoth +Caldera Pyremaw "
            "is win rate +0.0028 [+0.0012, +0.0047] at 10 turns and +0.0093 "
            "[+0.0057, +0.0133] at 20, significant at both, damage +1.17. "
            "WHY CALDERA AND NOT THE OTHER TWO, from diag_fivedrop.py at "
            "n=4,000: all three arrive in about the same share of games "
            "(Galvanoth 13.9% on turn 9.6, Caldera 13.8% on turn 9.6, "
            "Scrollwielder 18.6% on turn 8.2), so the difference is not "
            "castability — it is what they do once they land. Per game it "
            "resolves: Galvanoth 0.68 free casts, Scrollwielder 2.20 paid "
            "casts, Caldera 14.5 pod damage. "
            "NOTE THE PROXY DISAGREES WITH THE OBJECTIVE AGAIN. Head to head, "
            "mv_cheated goes DOWN 1.35 while win rate goes UP — Caldera "
            "cheats no mana at all, it just deals damage. Follow win rate; "
            "this is the same shape as the top-setter finding below. "
            "GALVANOTH'S OWN NUMBERS REPRODUCED EXACTLY on the 2026-09-05 "
            "engine (+0.0020 / +0.0128, identical to the previous staging), "
            "so the ranking is a fact about the cards and not about the "
            "engine changes made the same day."
        ),
        notes=(
            "WHY THIS WAS NOT DECIDED CORRECTLY THE FIRST TIME. Caldera "
            "Pyremaw was already CANDIDATES_2026-09-04.md's 'clearest add of "
            "the seven' at +0.0123 +-0.0048, and it was UNDERSTATED: "
            "tag_flying.py walked only mod.build(), so module-level candidates "
            "were constructed with flying=False and a 3/3 FLIER was measured "
            "as a ground creature. Fixed 2026-09-05. Radiant Scrollwielder was "
            "understated in a different way — the engine read library[-1] when "
            "the card says 'exile an instant or sorcery at random FROM YOUR "
            "GRAVEYARD'. Fixing the zone tripled its firings (0.68 -> 2.20 per "
            "resolve) and did NOT make it a better card, because unlike "
            "Galvanoth it pays full price for every one of them: its "
            "mv_cheated gain is +0.61 against Galvanoth's +1.34. Its number is "
            "still a FLOOR — 'instant and sorcery spells you control have "
            "lifelink' is unmodelled — but it would have to be worth six "
            "points of win rate to matter, and it is not. "
            "MEASURED WITHOUT THE OTHER STAGED LOREHOLD CHANGE. The baseline "
            "is the v16 list, which still has Scroll Rack rather than "
            "Sunbird's Invocation. That is the same baseline Galvanoth was "
            "measured on, so the comparison is sound. "
            "MEASURED TOGETHER 2026-09-06 (queued item 0b, run_lorehold_pair.py, "
            "2x2 factorial, N=30,000 per cell, all four legs on one seed): THE "
            "TWO STAGED LOREHOLD CHANGES ADD. Interaction on win rate is "
            "+0.0000 +-0.0008 at T10 and +0.0022 +-0.0020 at T20 -- zero at the "
            "short horizon and, if anything, slightly SUPER-additive at the "
            "long one, which is the opposite of the concern. Caldera GIVEN "
            "Sunbird's is +0.0028 / +0.0216, Sunbird's GIVEN Caldera is "
            "+0.0019 / +0.0168, and both together are +0.0047 / +0.0362 against "
            "the v16 list. Each is worth its slot with the other already in. "
            "The two predicted costs are both REAL and both outweighed: "
            "stranded_mv compounds (+0.60 +-0.18 beyond additive) and the two "
            "cards do compete for miracles (-0.018 +-0.008 miracles_cast). "
            "CALDERA'S OWN NUMBER REPRODUCED (+0.0202 -> +0.0194 +-0.0024) AND "
            "SUNBIRD'S DID NOT (+0.0215 -> +0.0146 +-0.0028 at T20; +0.0077 -> "
            "+0.0019 at T10, disjoint bars). The obvious explanation was tested "
            "and is WRONG: both cuts are top-setters and the 2026-09-05 "
            "top-setter policy fixes made top-setters better, so cutting one "
            "should have got more expensive -- but Scroll Rack still ablates to "
            "-0.0093 +-0.0032 win at T20, essentially the -0.0100 it was on "
            "2026-09-04. The cut is as cheap as it was; the decay is in "
            "Sunbird's own contribution and is NOT yet attributed. Do not "
            "invent a mechanism for it. "
            "THE WIDER FINDING, which matters more than this one swap. The "
            "top-setter package RAISES mv_cheated AND LOSES GAMES — ablating "
            "Library of Leng, Penance and Sensei's Divining Top together is "
            "win rate -0.0190 [-0.0276, -0.0104] but mv_cheated +1.43 [+0.76, "
            "+2.10]. The deck's stated primary metric and its objective point "
            "in OPPOSITE directions for these cards, and the project's own "
            "rule is to follow win rate. Library of Leng itself is the least "
            "guilty of the three (mv_cheated +1.56, win rate inside its bar) "
            "and is NOT proposed for a cut, but the plan of setting up your "
            "own draws deserves a harder look than a single swap. "
            "READ THE SWAP HONESTLY: Galvanoth itself ablated to +0.25/+0.09 "
            "damage and +0.0002 win rate — INSIDE its bars, indistinguishable "
            "from a blank — so nearly all of ITS +0.0128 was Penance being bad "
            "rather than Galvanoth being good. Caldera Pyremaw is a different "
            "case: it beats Galvanoth by +0.0093 in a paired comparison where "
            "Penance is absent from BOTH branches, so that margin is the card "
            "and not the cut. Sensei's Divining Top is the next candidate on "
            "the top-setter logic: -0.0075 +-0.0058 win rate, signal 'win', a "
            "third top-setter."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-09 on the post-combat-split engine "
            "(KNOWN_ISSUES.md §0v). Re-run as the SAME 2x2 factorial at the "
            "same N=30,000 per cell and the same seeds as the 2026-09-06 "
            "measurement, so the two are directly comparable: Caldera alone "
            "+0.0179 +-0.0023 at T20 against the previous +0.0194 +-0.0024, "
            "and +0.0029 +-0.0011 at T10 against +0.0028. Caldera GIVEN "
            "Sunbird's is +0.0214 +-0.0026 against +0.0216 — the marginal "
            "figure the decision actually rests on, reproduced almost "
            "exactly. Every cell of the factorial landed inside its own "
            "previous bar. The cut target moved a little and in the expected "
            "direction: Penance ablates to -0.0079 +-0.0032 win at T20, still "
            "significantly worse than a blank. The decision stands. "
            "diagnostics/run_lorehold_pair.py, "
            "results/lorehold_pair_postsplit.txt."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Scroll Rack",
        add="Sunbird's Invocation",
        staged="2026-09-04",
        rationale=(
            "'Whenever you cast a spell FROM YOUR HAND, reveal the top X, X = "
            "that spell's mana value; you may cast a spell with mana value X "
            "or less from among them free.' X scaling off the triggering "
            "spell is what makes it a Lorehold card rather than a generic "
            "one: this curve tops out at twelve, so a big spell digs deep and "
            "can free-cast something big. Miracles DO trigger it (a miracled "
            "card is cast from hand); Galvanoth, Radiant Scrollwielder, The "
            "Dawning Archaic and Bombardment/Mastery copies do not. "
            "THE 'FIRES 3.6 TIMES A GAME' FIGURE THIS ENTRY USED TO QUOTE WAS "
            "A CONDITIONAL NUMBER PRINTED AS AN UNCONDITIONAL ONE, corrected "
            "2026-09-06. It is MV 6 and RESOLVES IN ONLY 13.0% OF GAMES. In "
            "the games where it does resolve: 6.06 triggers, 4.00 free casts, "
            "average free spell MV 3.77 -- so the old 3.6/MV-3.8 pair was the "
            "conditional figure and is roughly right as such. Unconditionally "
            "it is 0.79 triggers and 0.52 free casts a game. Both are worth "
            "reading (see experiment.analyse_conditional) but only the "
            "unconditional one is deckbuilding EV, and the entry read as if "
            "3.6 free spells arrived every game. `sunbird_triggers` and "
            "`sunbird_casts` are now separate counters -- the ability finding "
            "nothing is 34% of its firings, because off a two-drop it reveals "
            "two cards and needs an MV<=2 nonland among them."
        ),
        evidence=(
            "Measured as the real swap, 6,000 paired games: win rate +0.0077 "
            "[+0.0047, +0.0108] at 10 turns and +0.0215 [+0.0142, +0.0288] at "
            "20; mv_cheated +2.12 and +4.91; damage +2.14 and +4.20; cards "
            "drawn +0.68 and +0.90. Every metric significant at both horizons."
        ),
        notes=(
            "Scroll Rack is the cut because it is the deck's worst "
            "model-evaluated NON-WIPE card (-1.78 damage, -0.0100 win, signal "
            "'both'): paying {1} and a tap to set the top competes with the "
            "miracle payment itself. Penance is deliberately left alone — it "
            "is already earmarked for Galvanoth in the queued work. "
            "COST: replacing a two-drop with a six-drop, stranded_mv +4.28 at "
            "10 turns. The alternative cut of Improvisation Capstone strands "
            "LESS (-0.98) but wins less (+0.0045 / +0.0128), so this is the "
            "better of the two measured options."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-05 after the top-setter policy fixes and the Galvanoth ordering fix. 6,000 paired games: win rate +0.0010 [-0.0017, +0.0037] at 10 turns and +0.0193 [+0.0133, +0.0253] at 20; damage +1.17 and +3.02; mv_cheated +1.20 and +3.20. The 20-turn result has been stable and significant across every engine version tried (+0.0215, +0.0108, +0.0173, +0.0182, +0.0193); the 10-turn result has been inside its bar since evasion landed. A long-horizon call, and the best-supported of the three staged changes. Scroll Rack is a TOP-SETTER, and the top-setter plan is the weakest part of this deck's construction. "
            "RE-VERIFIED AGAIN 2026-09-09 on the post-combat-split engine "
            "(KNOWN_ISSUES.md §0v), same 2x2 factorial, same N=30,000 and "
            "seeds as 2026-09-06: Sunbird's alone +0.0152 +-0.0028 at T20 "
            "against the previous +0.0146 +-0.0028, and Sunbird's GIVEN "
            "Caldera +0.0186 +-0.0029 against +0.0168. The T10 figure is "
            "+0.0019 +-0.0013, unchanged and still marginal. The 2026-09-06 "
            "DECAY DID NOT CONTINUE — this is now the second engine in a row "
            "on which the T20 figure sits near +0.015, so whatever caused the "
            "one-off drop from +0.0215 is not an ongoing trend. It is still "
            "not ATTRIBUTED (queued item 0b-i); do not invent a mechanism for "
            "it. Scroll Rack still ablates to -0.0107 +-0.0032 at T20, so the "
            "cut is as cheap as it ever was. The decision stands. "
            "results/lorehold_pair_postsplit.txt."
        ),
    ),
]


DECKS = {
    # March of the World Ooze is COMMITTED as of v12, so it is in the deck
    # list itself and no longer a swap-in candidate.
    "rendmaw": (rendmaw_v12, {
        "Cauldron of Essence": rendmaw_v12.CAULDRON_OF_ESSENCE}),
    # The four 2026-08-31/09-01 Lorehold changes are COMMITTED as of v16, so
    # they are in the deck list itself and no longer swap-in candidates.
    "lorehold": (lorehold_v16, {
        "Molecule Man": lorehold_v16.MOLECULE_MAN,
        "Galvanoth": lorehold_v16.GALVANOTH,
        "Caldera Pyremaw": lorehold_v16.CALDERA_PYREMAW,
        "Radiant Scrollwielder": lorehold_v16.RADIANT_SCROLLWIELDER,
        "Hidden Retreat": lorehold_v16.HIDDEN_RETREAT,
        "Sunbird's Invocation": lorehold_v16.SUNBIRDS_INVOCATION}),
    # The three 2026-09-04 Karlov changes are COMMITTED as of v2, so they are
    # in the deck list itself and no longer swap-in candidates.
    "karlov": (karlov_v2, {}),
    # Added 2026-09-05 as a fourth deck. Nothing is staged yet: the list is the
    # one in Tivit_Seller_of_Secrets_Commander_Deck_v1.xlsx, card for card.
    "tivit": (tivit_v1, {
        "Anointed Procession": tivit_v1.ANOINTED_PROCESSION}),
    # Added 2026-09-07 as a fifth deck. Nothing is staged yet: the list is the
    # one in Shilgengar_Sire_of_Famine_Commander_Deck_v1.xlsx, card for card,
    # six mana values corrected against Scryfall (see shilgengar_v1.py's
    # module docstring). This deck has not been through ablation yet.
    "shilgengar": (shilgengar_v1, {}),
    # Added 2026-09-07 as a sixth deck. The submitted list was 99 cards; a
    # 21st Forest was added to reach 100 -- see azusa_v1.py's docstring.
    "azusa": (azusa_v1, {
        # Ancient Greenwarden, Greensleeves and Springheart Nantuko were here
        # until 2026-09-10 and are now COMMITTED as of azusa_v1.py, so they are
        # in the deck list itself and no longer swap-in candidates. Same for
        # Scene of the Crime. Ka-Zar is still STAGED, so it stays.
        "Conduit of Worlds": azusa_v1.CONDUIT_OF_WORLDS,
        "Cultivator Colossus": azusa_v1.CULTIVATOR_COLOSSUS,
        "Case of the Locked Hothouse": azusa_v1.CASE_OF_THE_LOCKED_HOTHOUSE,
        "Walk-In Closet // Forgotten Cellar": azusa_v1.WALK_IN_CLOSET,
        "Ka-Zar of the Savage Land": azusa_v1.KA_ZAR,
        "Cryptic Caves": azusa_v1.CRYPTIC_CAVES,
        "Horizon of Progress": azusa_v1.HORIZON_OF_PROGRESS,
        "The Hunter Maze": azusa_v1.THE_HUNTER_MAZE}),
}


def pending_for(deck_name: str) -> list[Change]:
    return [c for c in CHANGES if c.deck == deck_name]


def build_pending(deck_name: str, apply_pending: bool = True, up_to: int = None):
    """Build a deck with staged changes applied.

    apply_pending=False gives the original spreadsheet list. `up_to=n` applies
    only the first n staged changes, which is how an experiment run earlier in
    the sequence can be reproduced after later changes are staged on top.
    """
    module, catalog = DECKS[deck_name]
    deck, commander = module.build()
    if not apply_pending:
        return deck, commander
    changes = pending_for(deck_name)
    if up_to is not None:
        changes = changes[:up_to]
    if not changes:
        return deck, commander
    outs = [c.remove for c in changes]
    ins = []
    for c in changes:
        if c.add not in catalog:
            raise KeyError(f"{c.add} has no card definition in {deck_name}")
        ins.append(catalog[c.add])
    deck = _swap_many(deck, outs, ins)
    validate(deck, commander)
    return deck, commander


BASICS = {"Mountain", "Plains", "Forest", "Swamp", "Island", "Wastes"}


def validate(deck, commander) -> None:
    """Singleton and size checks. Basic lands are the legal exception."""
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    seen = {}
    for card in deck:
        if card.name in BASICS:
            continue
        seen[card.name] = seen.get(card.name, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    assert not dupes, f"singleton violation: {dupes}"
    assert commander.name not in seen, (
        f"{commander.name} appears in the 99 as well as the command zone")


def ledger(verbose: bool = True) -> None:
    print("=" * 78)
    print("PENDING DECK CHANGES — not yet written to the .xlsx files")
    print("=" * 78)
    if not CHANGES:
        print("  (none — every decided change is applied on all three legs)")
        for deck_name in sorted(DECKS):
            deck, cmd = build_pending(deck_name)
            print(f"  {deck_name:<10} -> {len(deck) + 1} cards, "
                  f"singleton-legal, commander distinct")
    for deck_name in sorted({c.deck for c in CHANGES}):
        rows = pending_for(deck_name)
        print(f"\n{deck_name.upper()}  ({len(rows)} change"
              f"{'s' if len(rows) != 1 else ''})")
        for c in rows:
            print(f"  - OUT  {c.remove}")
            print(f"  + IN   {c.add}")
            print(f"    staged {c.staged}")
            if verbose:
                print(f"    why    {c.rationale}")
                print(f"    data   {c.evidence}")
                if c.notes:
                    print(f"    note   {c.notes}")
        deck, cmd = build_pending(deck_name)
        print(f"    -> {len(deck) + 1} cards, singleton-legal, commander distinct")
    if COMMITTED:
        # Azusa has NO .xlsx, so for that deck "committed" is two legs -- the
        # module and this ledger -- and the module alone is the system of
        # record. Said in the output rather than only in CLAUDE.md, because
        # this print is what someone checks before believing a change is done.
        print("\nCOMMITTED (in the deck module AND the .xlsx -- except azusa, "
              "which has\n           no .xlsx: its module alone is the system "
              "of record)")
        for c in COMMITTED:
            print(f"  {c.deck}: -{c.remove} +{c.add} ({c.staged})")
            if verbose and c.reverified:
                print(f"    recheck {c.reverified}")


if __name__ == "__main__":
    ledger()
