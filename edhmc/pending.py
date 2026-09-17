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

THE THREE STATES, which HANDOFF.md has always described and this module only
had structures for two of:

    MEASURED   a number and a confidence interval exist. NO decision. Names no
               cut. `MEASURED: list[Candidate]`, added 2026-09-10 -- before
               that this state lived in comments and in `results/` files that
               nothing reads, which is the state most easily lost, because a
               number with no decision attached looks like one somebody forgot
               to act on.
    STAGED     decided, with a cut named, and applied to this ledger only.
               `CHANGES: list[Change]`. `build_pending` applies these.
    COMMITTED  applied to all three legs -- deck module, .xlsx, this ledger --
               in ONE git commit. `COMMITTED: list[Change]`. Azusa has no
               .xlsx and is two legs.

Measured does NOT become staged by being good. It becomes staged by a
head-to-head against a specific cut, because everything in MEASURED shares a
baseline and a common baseline cannot rank two cards against each other (§0c).

To stage a change, append to CHANGES. To commit, update the spreadsheet and
the deck module, then move the entry to COMMITTED.

AND THE FOURTH STATE, added 2026-09-13:

    WITHDRAWN  was STAGED and has been UNSTAGED. `WITHDRAWN: list[Change]`,
               each carrying a `withdrawn` field saying when and why.
               `build_pending` does NOT apply these, so an unstaged change is
               out of every baseline the moment it moves here.

It exists because DELETING the entry was the alternative, and the entry is
where the evidence lives. A swap that was staged and then unstaged is not the
same thing as a swap nobody ever proposed: the next reader needs to know it was
considered, what it measured, and what took it off the list -- otherwise the
same card gets re-measured and re-staged from scratch. This is the ledger's
version of the `-old` entries CLAUDE.md keeps for its superseded findings.

A WITHDRAWN entry is NOT a refutation. Re-staging one is a matter of moving it
back to CHANGES with fresh evidence; the `withdrawn` field says what that
evidence would have to answer.
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
    withdrawn: str = ""         # set only on WITHDRAWN: when, and why


@dataclass
class Candidate:
    """A card that has been MEASURED and NOT decided on.

    HANDOFF.md has always described three states -- measured, staged,
    committed -- and this module only had structures for the last two, so the
    first one lived in comments and in `results/` files that nothing reads.
    That is the state most likely to be lost: a number with nobody's decision
    attached to it looks exactly like a number somebody forgot to act on.

    A Candidate is deliberately WEAKER than a Change. It names no cut, because
    choosing one is the decision this state has not taken; `ablation.py` scores
    the cut side and `candidates.py` scores the add side, and pairing them is a
    head-to-head run, not an inference (§0c). Promoting one means writing a
    Change with a `remove`, and that needs its own evidence.
    """
    deck: str
    card: str
    measured: str               # date measured
    win_rate: str               # the number, WITH its bar and its horizon
    signal: str                 # both / dmg / win / --
    rationale: str
    evidence: str = ""
    limits: str = ""            # floors, ceilings and modelling caveats
    verdict: str = ""           # what the number supports, and what it does not

    # --- SHORTLISTED: a REVIEW FLAG, and deliberately not a fourth state ----
    # "These three are worth a head-to-head" is a different claim from "this is
    # going in", and the whole point of the measured/staged split is that the
    # second one needs evidence the first does not have. A shortlisted
    # Candidate is still a Candidate: `build_pending` does not apply it, no
    # table contains it, and no deck list moves. What the flag buys is that the
    # shortlist stops living in a conversation -- the state this class was
    # written to rescue (see the docstring above).
    #
    # `proposed_cut` NAMES THE CUT THE HEAD-TO-HEAD SHOULD RUN, which a plain
    # Candidate deliberately does not. It is a PROPOSAL and the number attached
    # to this row is NOT evidence for it: an ablation row and a candidate row
    # share a baseline and therefore cannot be subtracted from one another
    # (§0c). `check_shortlist_is_answerable()` enforces what can be enforced --
    # that the named cut is really in the deck.
    shortlist: str = ""         # why it is shortlisted; empty = it is not
    proposed_cut: str = ""      # the cut a head-to-head should test it against


# ---------------------------------------------------------------------------
# Committed — reflected in BOTH the deck module and the .xlsx
# ---------------------------------------------------------------------------
@dataclass
class Proposal:
    """A card PROPOSED for testing: oracle text verified, nothing measured yet.

    THE FIFTH STATE, added 2026-09-16, and it exists for the same reason
    WITHDRAWN does -- the alternative was a chat message, and a chat message is
    the state most easily lost. A Proposal is WEAKER than a Candidate: a
    Candidate has a number and a confidence interval, a Proposal has only
    verified card text and an argument.

    WHY IT CARRIES THE ORACLE TEXT. `CLAUDE.md` forbids guessing oracle text,
    and this project's largest corrections all came from a card whose text the
    engine had wrong. A proposal made from memory is exactly that failure
    staged one step earlier, so the text here is copied from
    `api.scryfall.com` on `verified`, and `check_proposals` refuses an entry
    without it. If you cannot reach Scryfall, you cannot add a Proposal -- that
    is deliberate.

    `implement` is the honest estimate of ENGINE work, which is the real cost.
    The measurement is minutes; making the card behave like its text is not.
    """
    deck: str
    card: str
    cost: str                   # verified mana cost
    identity: str               # verified colour identity, "" for colourless
    type_line: str
    oracle: str                 # VERBATIM from Scryfall
    verified: str               # date the text above was fetched
    rationale: str              # why THIS deck, tied to a measured weakness
    implement: str              # engine work needed, and what it would move
    rejected: str = ""          # set if the proposal is dead, and why


# The commanders' colour identities, fetched from Scryfall 2026-09-16 rather
# than derived from cost pips -- a commander's identity includes its ability
# text, so the cost is not always the whole answer and deriving it would be a
# guess dressed as a derivation.
DECK_IDENTITY = {
    "karlov": set("BW"), "rendmaw": set("BG"), "lorehold": set("RW"),
    "tivit": set("BUW"), "azusa": set("G"), "shilgengar": set("BW"),
}


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
# Measured — a number exists, NO decision has been taken
# ---------------------------------------------------------------------------
# Nothing in this list is staged, and nothing in it names a cut. Read a row as
# "this card was measured at this value in this slot", never as "this card is
# going in". Promotion to CHANGES needs a head-to-head against a specific cut,
# because everything here shares one baseline and therefore cannot be ranked
# against anything else measured the same way (§0c).
# ---------------------------------------------------------------------------
MEASURED: list[Candidate] = [
    # ---- 2026-09-16, the §0z26 batch. Ten proposals implemented and measured
    # at N=15,000 paired, T20, each in its own deck's established victim slot
    # (tivit's is a basic Plains -- see tools/candidates.py for why).
    Candidate(
        deck="karlov", card="Bloodthirsty Conqueror", measured="2026-09-16",
        win_rate="+0.0328 +-0.0033 at T20 (N=15,000 paired)", signal="both",
        rationale=(
            "A SECOND EXQUISITE BLOOD ON A BODY -- word for word the same "
            "trigger. It is a redundancy card for the combo the deck already "
            "wins with, and the combo-win counter moves 0.312 -> 0.375."),
        evidence=("damage -2.20 +-0.21, and the NEGATIVE damage is the "
                  "mechanism rather than a flaw: the extra wins arrive by the "
                  "combo route, which ends the game before the board deals "
                  "damage. The standing proxy-versus-objective split, and the "
                  "rule is follow win rate."),
        limits=(
            "A FLOOR, and the reason is §0u rather than §4. The engine models "
            "Exquisite Blood's text as a COMBO DETECTOR, not as the "
            "continuous 'gain life whenever an opponent loses life' it "
            "actually is -- so this card inherits that limit exactly. "
            "Implementing the general trigger for the new card and not the old "
            "one would have made a strictly-worse card measure strictly "
            "better. REDUNDANT BY DESIGN: ablate it together with Exquisite "
            "Blood and the three loop partners, never alone."),
    ),
    Candidate(
        deck="tivit", card="Anointed Procession", measured="2026-09-16",
        win_rate="+0.0291 +-0.0034 at T20 (N=15,000 paired)", signal="both",
        rationale=(
            "Doubles BOTH token streams: artifacts_made 51.3 -> 67.1 and "
            "treasures_made 22.9 -> 31.2 a game. Academy Manufactor, "
            "Marionette Master, Disciple of the Vault and Time Sieve all read "
            "those piles, so one card feeds four payoffs."),
        evidence="damage +0.85 +-0.21, P(deploy) 0.249.",
        limits=(
            "MEASURED AGAINST A BASIC PLAINS, not a named cut, so both legs "
            "run 35 lands rather than 36 -- read it as value over a blank in a "
            "LAND slot. WATCH TIME SIEVE (§0m): it eats only TOKEN artifacts, "
            "so doubling the token stream makes the extra-turn loop easier and "
            "`sieve_cap` stops being decorative."),
    ),
    Candidate(
        deck="rendmaw", card="Parallel Lives", measured="2026-09-16",
        win_rate="+0.0157 +-0.0026 at T20 (N=15,000 paired)", signal="both",
        rationale=("Primal Vigor without the symmetry -- Vigor doubles for "
                   "every player, this only for you. tokens_made 8.98 -> "
                   "10.13 a game."),
        evidence="damage +1.45 +-0.14, P(deploy) 0.203.",
        limits=("Stacks multiplicatively with Primal Vigor, which is already "
                "in the list, so the pair is worth more than the sum -- "
                "leave-one-out understates both. Ablate them together. "
                "HELD, NOT STAGED, 2026-09-16: the deck's owner reads four "
                "mana for a do-nothing enchantment as expensive, and that is "
                "a cost this model systematically under-charges -- a card "
                "that affects no board until the NEXT token is made is "
                "exactly the kind the engine flatters, because nothing here "
                "punishes a wasted turn. P(deploy) is 0.203, so four games in "
                "five it never resolves at all. If it is revisited, measure "
                "the REAL swap against a named cut rather than this "
                "candidate-vs-blank row, and consider ablating it beside "
                "Primal Vigor to see what the pair is worth."),
    ),
    Candidate(
        deck="karlov", card="Alhammarret's Archive", measured="2026-09-16",
        win_rate="+0.0129 +-0.0024 at T20 (N=15,000 paired)", signal="both",
        rationale=("Doubles life gained (4.88 a game) and every draw except "
                   "the draw step's first (0.40 a game)."),
        evidence="damage +0.56 +-0.10, P(deploy) 0.160.",
        limits=(
            "THE DRAW HALF IS NEARLY INERT HERE and the counter says so: 0.40 "
            "extra draws a game, because most of karlov's draws ARE the draw "
            "step and the card explicitly exempts it. Nearly all the value is "
            "the lifegain doubler. It doubles the AMOUNT, never the EVENT "
            "COUNT, so Karlov's own counter still gets two per trigger -- the "
            "distinction this engine is built around. "
            "NOT STAGED, AND THE REASON IS PLAYTEST EVIDENCE THE MODEL CANNOT "
            "SEE. The deck's owner has run this card at real tables and "
            "reports it did not deliver: at five mana it needs to be "
            "high-impact, and the card draw does not trigger often enough. "
            "THE MODEL AGREES ON THE MECHANISM AND THAT CONVERGENCE IS THE "
            "POINT -- 0.40 extra draws a game is the same complaint stated as "
            "a counter, arrived at independently. Where they differ is the "
            "VERDICT: the engine scores +0.0129 on the lifegain doubler "
            "alone, and it cannot price what a five-mana do-nothing artifact "
            "costs at a real table, because opponents here hold no removal to "
            "aim at it and no tempo to punish it (§4). Treat the row as a "
            "measurement of the lifegain half in isolation, which is what it "
            "is, and the table result as the better guide to the whole card."),
    ),
    Candidate(
        deck="lorehold", card="Past in Flames", measured="2026-09-16",
        win_rate="+0.0102 +-0.0038 at T20 (N=15,000 paired)", signal="both",
        rationale=("Extends §0z19's finding that lorehold's graveyard is a "
                   "resource. 0.56 flashback casts a game at full price."),
        evidence="damage +0.28 +-0.18, mv_cheated +1.02 +-0.27, P(deploy) 0.322.",
        limits=("NOT a free-cast card -- flashback costs full price, so it is "
                "bounded by leftover mana rather than by a card cap, and with "
                "an empty graveyard it does nothing. `flashback_cap` (6) has "
                "never been swept."),
    ),
    Candidate(
        deck="lorehold", card="Jeska's Will", measured="2026-09-16",
        win_rate="+0.0074 +-0.0043 at T20 (N=15,000 paired)", signal="both",
        rationale=("Mode 2 only: exile the top three and cast what the mana "
                   "affords. 0.31 casts and 0.44 cards stranded a game."),
        evidence="damage +0.57 +-0.24, mv_cheated +0.63 +-0.33, P(deploy) 0.345.",
        limits=(
            "A HARD FLOOR AND THE BIGGEST ONE IN THIS BATCH. Mode 1 -- 'add "
            "{R} for each card in target opponent's hand' -- counts a hand the "
            "pod does not have (§4), exactly Borrowed Knowledge's limit "
            "(§0z14). At a real table that mode is most of the card and "
            "routinely adds four to seven red mana. PARTLY_MODELLED: a high "
            "score is evidence, a low score is not."),
    ),
    Candidate(
        deck="rendmaw", card="Mycoloth", measured="2026-09-16",
        win_rate="+0.0069 +-0.0023 at T20 (N=15,000 paired)", signal="both",
        rationale=("Devours 0.28 tokens and makes 1.29 saprolings a game."),
        evidence="damage +0.43 +-0.11, P(deploy) 0.161.",
        limits=(
            "THE DEVOUR POLICY IS A KNOB AND IT IS NOT CLAIMED TO BE OPTIMAL. "
            "`mycoloth_devour` (4) eats only TOKENS, never a real card. That "
            "is the SAME SHAPE that cost 0.034 win rate on shilgengar, where "
            "'would only ever sacrifice 1/1 tokens' was written as "
            "conservatism and amounted to asserting the commander does "
            "nothing. Sweep the knob before quoting this row -- and note that "
            "eating tokens in a deck whose payoffs COUNT tokens (Coat of Arms, "
            "Overwhelming Stampede) is a real cost this policy pays."),
    ),
    Candidate(
        deck="tivit", card="Urza, Lord High Artificer", measured="2026-09-16",
        win_rate="+0.0034 +-0.0025 at T20 (N=15,000 paired)", signal="--",
        rationale=("INSIDE ITS OWN BAR -- unmeasured, not measured as weak. "
                   "0.17 Constructs a game."),
        evidence="damage +0.54 +-0.15, P(deploy) 0.195.",
        limits=(
            "A FLOOR WITH TWO NAMED HALVES MISSING, and they are the big "
            "ones: 'Tap an untapped artifact you control: Add {U}' would make "
            "every artifact a mana source in a deck that makes 51 artifact "
            "tokens a game, and '{5}: exile the top card, play it free' is a "
            "repeatable free-cast engine. Only the Construct is modelled -- "
            "with a DYNAMIC P/T read live, which is the §0z3 trap handled. "
            "PARTLY_MODELLED. Do not read this row as evidence about Urza."),
    ),
    Candidate(
        deck="tivit", card="Sai, Master Thopterist", measured="2026-09-16",
        win_rate="+0.0003 +-0.0022 at T20 (N=15,000 paired)", signal="--",
        rationale=(
            "A BLANK, and the mechanism explains it: 0.155 Thopters a game. "
            "Sai triggers on CASTING AN ARTIFACT SPELL, and almost every "
            "artifact this deck produces is a TOKEN it creates rather than a "
            "spell it casts -- 51 artifacts made a game, and the trigger sees "
            "essentially none of them. The deck's artifact density is an "
            "illusion from this card's point of view."),
        evidence="damage +0.14 +-0.13, P(deploy) 0.220.",
        limits=("Fully implemented, so this IS evidence about the card in "
                "this list. It would be a different row in a deck that casts "
                "artifacts from hand."),
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
            "NOT A STAGING: §0c, it needs a head-to-head against a named cut, "
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
                "cutting any of them -- pass a list of names to ablate()."),
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
            "an INSTANT and this engine casts it at sorcery speed."
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
            "against a pod that wipes."
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
    # ranked against each other beyond their bars (§0c). §0z21.
    Candidate(
        deck="azusa",
        card="Traveling Chocobo",
        measured="2026-09-13",
        win_rate="+0.0291 +-0.0040 at T20 (damage +2.64 +-0.26)",
        signal="both",
        rationale=(
            "A SECOND ANCIENT GREENWARDEN for the half this deck cares about: "
            "'if a land or Bird you control entering causes a triggered "
            "ability of a permanent you control to trigger, that ability "
            "triggers an additional time' is Greenwarden's sentence with Bird "
            "added, and the two STACK -- one land fires every payoff three "
            "times. Measured: landfall_ability_resolutions +13.84 per "
            "resolution against landfall_triggers +0.90, and tokens_made +243 "
            "per resolution, which is Scute Swarm compounding. It also plays "
            "lands off the top of the library, a FIFTH source of that boolean."
        ),
        evidence=(
            "N=15,000 paired, T20, in the Sylvan Library slot. "
            "tools/candidates.py azusa4; "
            "results/candidates_azusa_batch4_T20.txt. Mechanisms in "
            "results/azusa_batch4_mechanisms.txt. §0z21."
        ),
        limits=(
            "FLOOR, and a small one: 'cast Bird spells from the top of your "
            "library' is worth nothing in a list whose only Bird is this card. "
            "Answered by the pod 12.7% of the time. The top-of-library half is "
            "REDUNDANT with Courser, Augur, Oracle and the staged Ka-Zar -- "
            "that redundancy is already priced in here, because all four are "
            "in the list this was measured against."
        ),
        verdict=(
            "Would rank 8th of 44 model-evaluated cards by win rate, inside "
            "the bars of Rampaging Baloths, Tireless Tracker, Ancient "
            "Greenwarden and Nissa, Vastwood Seer. It is INSIDE Nissa, "
            "Resurgent Animist's bar too (0.0006 apart against +-0.0040), so "
            "the two are a SET and not a ranking."
        ),
        shortlist=(
            "is here: highest of the six, and the one whose mechanism this "
            "deck is built to exploit -- a second doubler in a list holding "
            "Scute Swarm, Rampaging Baloths, Avenger and Greensleeves. "
            "SHORTLISTED 2026-09-14 for review, NOT decided."
        ),
        proposed_cut="Yavimaya Elder",
    ),
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
            "N=15,000 paired, T20, same run as Traveling Chocobo above. §0z21."
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
            "measurement of the swap (§0c)."
        ),
        shortlist=(
            "is here: statistically tied with Traveling Chocobo at the top of "
            "the batch, and it attacks the deck's OWN measured weakness -- "
            "this list is card-limited, not mana-limited, and this is the only "
            "one of the six that adds a card every turn. "
            "SHORTLISTED 2026-09-14 for review, NOT decided."
        ),
        proposed_cut="Wayward Swordtooth",
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
            "a late-game card in a deck whose games end around turn 12."
        ),
        shortlist=(
            "is here: third of the six and the only one that is not competing "
            "for a cheap slot -- it is a TOP-END card, so it can be reviewed "
            "against the expensive rows rather than against the deck's "
            "two- and three-drops. Its +0.0188 is also the most robust number "
            "of the three, with the tightest bar. "
            "SHORTLISTED 2026-09-14 for review, NOT decided."
        ),
        proposed_cut="Kozilek, Butcher of Truth",
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
]

# ---------------------------------------------------------------------------
# Staged — decided, not yet in the spreadsheets
# ---------------------------------------------------------------------------
CHANGES: list[Change] = [
    Change(
        deck="karlov", remove="Soulmender", add="Bloodthirsty Conqueror",
        staged="2026-09-16",
        rationale=(
            "A SECOND EXQUISITE BLOOD ON A 5/5 FLYING DEATHTOUCH BODY -- word "
            "for word the same trigger, so it is redundancy on the package "
            "this deck actually wins with (the three loop partners ablate to "
            "+0.0513 as a GROUP). The cut is the cheapest in the list: "
            "Soulmender ablates to -0.0011 +-0.0011, signal `win`, which is "
            "SIGNIFICANTLY NEGATIVE -- a 1/1 that gains one life per trigger "
            "in a deck whose payoffs count events and whose curve wants more."),
        evidence=(
            "THE REAL SWAP, not the candidate-vs-blank row. N=15,000 paired, "
            "same seeds both legs: win rate +0.0257 [+0.0229, +0.0285] at "
            "T10 and +0.0247 [+0.0212, +0.0282] at T20, significant at BOTH "
            "horizons, against baselines of 0.1226 and 0.3486. The §0z26 "
            "candidate row was +0.0328 +-0.0033 against a blank in the freed "
            "slot; the swap is smaller because it also pays for losing "
            "Soulmender, and the swap is the number the decision rests on "
            "(§0c). Damage is -1.46 / -2.57 and that is the MECHANISM, not a "
            "cost: the extra wins arrive by the combo route, which ends the "
            "game before the board deals damage. Combo wins 0.312 -> 0.375. "
            "RESTATED 2026-09-17 (§0z29): those figures were measured with "
            "the card as a GROUND creature -- decks/_evasion.py had not been "
            "regenerated after it was added. With flying, same N and seeds "
            "(diagnostics/run_karlov_conqueror.py): +0.0259 [+0.0233, "
            "+0.0287] at T10 and +0.0254 [+0.0218, +0.0291] at T20, and the "
            "candidate row +0.0331 +-0.0033. Flying is worth nothing "
            "measurable to this card; the staging rests on the trigger."),
        notes=(
            "A FLOOR, for §0u's reason rather than §4's. This engine models "
            "Exquisite Blood's text as a COMBO DETECTOR and not as the "
            "continuous 'gain life whenever an opponent loses life' it is, "
            "and the new card inherits that treatment exactly -- giving the "
            "new card the general trigger and not the old one would have made "
            "a strictly-worse card measure strictly better. Both cards are "
            "understated by the same amount. REDUNDANT BY DESIGN: ablate it "
            "with Exquisite Blood and the loop partners, never alone. "
            "MEASURED ON THE STAGED LIST, which is the right baseline and is "
            "said out loud because §0p showed two staged lorehold changes can "
            "interact: `build_pending('karlov')` already applies -Swamp "
            "+Bolas's Citadel, so this swap was measured with the Citadel IN. "
            "The two cut different cards and neither touches the other's "
            "mechanism, but they have not been measured as a 2x2 and that is "
            "the check §0p exists for if both are committed together."),
    ),
    Change(
        deck="tivit", remove="Plains", add="Anointed Procession",
        staged="2026-09-16",
        rationale=(
            "Doubles BOTH token streams -- artifacts_made 51.3 -> 67.1 and "
            "treasures_made 22.9 -> 31.2 a game -- and Academy Manufactor, "
            "Marionette Master, Disciple of the Vault and Time Sieve all read "
            "those piles, so one card feeds four payoffs. "
            "THE CUT IS A BASIC PLAINS AND THAT IS A DELIBERATE CHOICE, not a "
            "failure to find a better one: tivit has NO weak nonland row. Its "
            "worst MODEL-EVALUATED card is Tamiyo's Journal at +0.0015 "
            "+-0.0017, inside its own bar, so naming a spell as the cut would "
            "assert a verdict the table does not support. 36 lands -> 35."),
        evidence=(
            "THE REAL SWAP, N=15,000 paired, same seeds both legs: win rate "
            "+0.0113 [+0.0087, +0.0139] at T10 and +0.0145 [+0.0105, +0.0185] "
            "at T20, significant at BOTH horizons, against baselines of "
            "0.1083 and 0.3265. THE CANDIDATE ROW WAS +0.0291 +-0.0034 and "
            "the swap is HALF that -- the difference is the land. Read the "
            "+0.0291 as value over a blank in a freed slot and this as what "
            "the deck actually gains, which is the number that decides it."),
        notes=(
            "WATCH TIME SIEVE (§0m): it eats only TOKEN artifacts, so "
            "doubling the token stream makes the extra-turn loop materially "
            "easier and `sieve_cap` stops being decorative. Extra turns "
            "measured essentially flat here (0.505 -> 0.485 in the mechanism "
            "run), so the loop is not what is driving the win rate -- but "
            "that is the knob to sweep before committing. "
            "GOING TO 35 LANDS IS THE REAL RISK and it is not visible in "
            "this number: the model's mulligan and land-drop behaviour is "
            "simpler than a real pilot's, so a land cut is the kind of change "
            "this harness flatters. Committing needs the .xlsx and the module "
            "to move with the ledger -- tivit has all three legs."),
    ),

    Change(
        deck="karlov",
        remove="Swamp",
        add="Bolas's Citadel",
        staged="2026-09-12",
        rationale=(
            "{3}{B}{B}{B} Legendary Artifact: 'You may play lands and cast "
            "spells from the top of your library. If you cast a spell this "
            "way, pay life equal to its mana value rather than pay its mana "
            "cost.' THIS IS THE DECK THAT CAN AFFORD IT -- karlov gains 55.9 "
            "life a game and its life-share of losses is the lowest of the "
            "three measured (0.20), so life here is a RESOURCE rather than a "
            "clock, and since §0z7/§0i it is a real one that gets charged. "
            "The cut is a SWAMP, 36 lands -> 35, which is the same shape as "
            "the committed v2 change (-Swamp +Starscape Cleric, 37 -> 36). "
            "NOTE THIS DECK WAS NEVER MISSING THE CARD: it is in neither the "
            "v1 nor the v2 spreadsheet nor any module, and both spreadsheets "
            "are exactly 100 cards whose v1->v2 difference is precisely the "
            "three committed swaps. This is a deckbuilding addition, not a "
            "restored omission."
        ),
        evidence=(
            "Measured as the REAL SWAP at the project's swap convention -- "
            "N=6,000 paired games, default seeds, both horizons "
            "(diagnostics/run_citadel.py, results/citadel.txt): win rate "
            "**+0.0163 [+0.0097, +0.0230] at 20 turns** and +0.0047 [+0.0003, "
            "+0.0088] at 10, both significant against a +-0.0025 noise floor. "
            "Damage +0.87 and lifegain_triggers +0.37, both significant, so "
            "the proxies agree with the objective here rather than fighting "
            "it. It assembles the combo more often too: combo_assembled "
            "+0.0067, i.e. 6.5% of games against 5.8%. "
            "THE COST IS MANA AND IT IS REAL: stranded_mv +5.4, the same "
            "shape the v2 land cut produced (+5.56). "
            "WHAT LIMITS IT IS NOT LIFE. It resolves in only 14.4% of games "
            "at T20 -- a six-drop with triple black -- and spends just 2.28 "
            "life a game, about 14 per resolution. Sweeping "
            "`citadel_life_floor` from 10 to 1, a tenfold change, moves win "
            "rate +0.0113 -> +0.0127 at T20, inside each other's bars. THE "
            "KNOB IS NOT LOAD-BEARING, which is said out loud because "
            "CLAUDE.md requires it and because the answer is unusually clean: "
            "the binding constraints are the resolution rate and the LAND ON "
            "TOP, not the life total."
        ),
        notes=(
            "THE PILOTING ORDER WAS WORTH MORE THAN ANY MECHANICAL DETAIL, "
            "which is finding 16b's shape arriving before the bug rather than "
            "after it. A land on top of the library that you cannot play "
            "STOPS THE DIG -- you may not skip past it -- and in a 35-land "
            "list that is roughly every third card. Playing the hand's land "
            "first and then digging is the naive order and it leaves the top "
            "land in place: measured that way the swap is +0.0113 [+0.0048, "
            "+0.0178] at T20. Spending the land drop on the TOP land instead "
            "(`citadel_land_step`) takes it to +0.0163 [+0.0097, +0.0230]. "
            "The two win-rate intervals OVERLAP, so that half is directional "
            "rather than proved; the MECHANISM is not ambiguous -- lands "
            "played off the top go 0.054 -> 0.134 a game, up 148%. "
            "results/citadel_naive_land_order.txt keeps the naive numbers. "
            "**ITS NUMBER IS A CEILING AND QUEUED ITEM 17 IS WHY.** The "
            "Citadel is exactly the card that makes 'nothing in this project "
            "loses to decking' live: it strips the library from the top, "
            "draw() stops at empty and no loss is recorded. At a table, "
            "emptying your library is how this card kills you. "
            "The sac-ten drain is implemented LETHAL-ONLY (ten nonland "
            "permanents, and only when every living opponent is at 10 or "
            "less), which is deliberately conservative and a floor on that "
            "half -- the model cannot value 'I am losing anyway'."
        ),
    ),

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


# ---------------------------------------------------------------------------
# Withdrawn — was staged, and has been UNSTAGED
# ---------------------------------------------------------------------------
# NOT applied by `build_pending`, so nothing here is in any baseline.
# Kept in full because the entry is where the evidence lives, and a swap
# that was considered and dropped is a different fact from one nobody
# ever proposed. See the module docstring.
WITHDRAWN: list[Change] = [
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
            "diagnostics/run_swaps_0904.py, results/staged_recheck_rendmaw.txt. "
            "\n\n"
            "RE-MEASURED 2026-09-12 on the §0z9–§0z15 engine, AND THIS ONE DID "
            "NOT REPRODUCE. Same N=6,000, same seeds, same harness, so the "
            "engine is again the only thing that changed: win rate "
            "+0.0000 [-0.0010, +0.0010] at 10 turns — DEAD ZERO AND NO LONGER "
            "SIGNIFICANT, against +0.0027 and +0.0022 before — and "
            "+0.0055 [+0.0015, +0.0095] at 20, still significant but roughly "
            "a THIRD of the +0.0152 recorded above and outside that interval "
            "entirely. The mechanism is §0z9: `deal_pod_damage` divided a "
            "full-pod total by the number of opponents still LIVING, so every "
            "drain was inflated by up to 3x exactly in the endgame, and "
            "Cauldron's death trigger is one of the six copies it hit "
            "(engine.on_creature_death). Note what the `notes` field above "
            "says — 'the engine models Blood Artist at 3x its real drain… "
            "Cauldron's 3.0 is the one of the two that is correct'. That was "
            "true of the NUMERATOR and the bug was in the DIVISOR, so the "
            "sentence was right and the conclusion drawn from it was not. "
            "The costs are unchanged and are now the larger half of the "
            "picture: cards_drawn -0.22, tokens_made -0.16, rendmaw_triggers "
            "-0.10, stranded_mv +1.34. The ablation row moved with it, "
            "+0.0159 ±0.0026 -> +0.0082 ±0.0023. "
            "**THE SWAP IS NOT REFUTED — it is still positive and significant "
            "at T20 against a ±0.0018 noise floor — BUT ITS RECORDED VALUE "
            "WAS ~3x AND THE DECISION IS NOT RE-AFFIRMED HERE.** It is worth "
            "nothing at all at the ten-turn horizon, which is where the games "
            "actually end (~T12). Re-read it before committing."
        ),
        withdrawn=(
            "UNSTAGED 2026-09-13. NOT REFUTED AND NOT REJECTED — unstaged "
            "because the decision was taken on evidence that no longer "
            "describes this engine, and a staged change is a DECISION rather "
            "than a number. The 2026-09-04 staging rested on +0.0135 at T20 "
            "and +0.0027 at T10, both significant; on the §0z9 engine the same "
            "N and the same seeds give +0.0055 [+0.0015, +0.0095] at T20 and "
            "+0.0000 [-0.0010, +0.0010] at T10. The T10 figure is the one that "
            "decides it: games in this model end around T12, so a swap worth "
            "dead zero at ten turns is worth approximately nothing where it "
            "would actually be played. "
            "WHAT RE-STAGING WOULD HAVE TO ANSWER, so the next reader does not "
            "start over: (1) is +0.0055 at T20 worth a slot, given the swap "
            "also costs cards_drawn -0.22, tokens_made -0.16, "
            "rendmaw_triggers -0.10 and stranded_mv +1.34, all still real; "
            "(2) is Idol of Oblivion still the right cut, given its own row "
            "and Cauldron's both moved in the §0z9 regeneration; and (3) is "
            "there a better use of the slot, which was never asked because "
            "this swap was staged before the deck's table was last rebuilt. "
            "The evidence above is kept in full and is still valid AS "
            "MEASUREMENT -- what changed is the engine it was measured on and "
            "the conclusion drawn from it, not the arithmetic."
        ),
    ),
]


# ---------------------------------------------------------------------------
# PROPOSED, 2026-09-16. Oracle text fetched from api.scryfall.com the same day
# and pasted verbatim. NOTHING HERE IS MEASURED -- these are arguments with
# verified card text attached, and the next step for each is a
# `tools/candidates.py` batch entry, not a staging.
#
# The two rejected entries are KEPT rather than deleted, for WITHDRAWN's
# reason: a proposal that was considered and found illegal is not the same
# thing as one nobody thought of, and without the record the same two cards get
# proposed again. Both were caught by the colour-identity check below, which is
# why that check exists.
# ---------------------------------------------------------------------------
PROPOSED: list[Proposal] = [
    Proposal(
        deck="karlov", card="Heliod, Sun-Crowned", cost="{2}{W}", identity="W",
        type_line="Legendary Enchantment Creature — God",
        oracle=("Indestructible\n"
                "As long as your devotion to white is less than five, Heliod "
                "isn't a creature.\n"
                "Whenever you gain life, put a +1/+1 counter on target "
                "creature or enchantment you control.\n"
                "{1}{W}: Another target creature gains lifelink until end of "
                "turn."),
        verified="2026-09-16",
        rationale=("Karlov's commander counts lifegain EVENTS, not points, and "
                   "the list already runs Soul Warden, Soul's Attendant, "
                   "Suture Priest, Auriok Champion and Starscape Cleric to "
                   "generate them. This is another payoff per event rather "
                   "than another source, which is the half the deck is "
                   "thinner on."),
        implement=("ALREADY IMPLEMENTED IN FULL -- karlov.py carries the "
                   "devotion gate, the lifegain trigger and the lifelink "
                   "activation. Nothing to build."),
        rejected=("ALREADY MEASURED, and this proposal should not have been "
                  "written. It is in the `karlov1` batch of "
                  "tools/candidates.py and `results/candidates_karlov.txt` "
                  "records +0.0008 +-0.0024 at T10 and +0.0050 +-0.0045 at "
                  "T20, N=6,000 -- INSIDE ITS BARS at both horizons. The card "
                  "is implemented faithfully, so that is evidence about the "
                  "card rather than about the engine. Re-measuring it at "
                  "N=15,000 is defensible (the T20 bar is wide); proposing it "
                  "as a new idea is not."),
    ),
    Proposal(
        deck="karlov", card="Bloodthirsty Conqueror", cost="{3}{B}{B}",
        identity="B", type_line="Creature — Vampire Knight",
        oracle=("Flying, deathtouch\n"
                "Whenever an opponent loses life, you gain that much life. "
                "(Damage causes loss of life.)"),
        verified="2026-09-16",
        rationale=("Turns every drain into a lifegain EVENT, feeding the "
                   "Exquisite Blood / Sanguine Bond / Vito package that "
                   "ablates to +0.0513 as a GROUP. Leave-one-out understates "
                   "every member of that group, so this should be measured "
                   "with them, not against a blank."),
        implement=("LOW-MEDIUM. §0z9 already routes 'each opponent loses N' "
                   "through the corrected pod divisor, so the hook exists. "
                   "Watch that it does not re-enter the drain loop -- this is "
                   "a lifegain trigger ON life loss, and karlov already has "
                   "two cards that close that loop."),
    ),
    Proposal(
        deck="karlov", card="Alhammarret's Archive", cost="{5}", identity="",
        type_line="Legendary Artifact",
        oracle=("If you would gain life, you gain twice that much life "
                "instead.\n"
                "If you would draw a card except the first one you draw in "
                "each of your draw steps, draw two cards instead."),
        verified="2026-09-16",
        rationale=("Doubles life gained and cards drawn; Well of Lost Dreams "
                   "and Aetherflux Reservoir are both already in the list and "
                   "both read the AMOUNT rather than the event count."),
        implement=("MEDIUM, and it is the §0z4 trap: a doubler has to be said "
                   "in EVERY path that reads the quantity or it does nothing. "
                   "Grep for life_gained and cards_drawn before claiming it "
                   "works, and note it does NOT double Karlov's own counter, "
                   "which counts events."),
    ),
    Proposal(
        deck="rendmaw", card="Parallel Lives", cost="{3}{G}", identity="G",
        type_line="Enchantment",
        oracle=("If an effect would create one or more tokens under your "
                "control, it creates twice that many of those tokens "
                "instead."),
        verified="2026-09-16",
        rationale=("A clean one-sided token doubler. The list already runs "
                   "Primal Vigor, which doubles for EVERY player -- this is "
                   "the same effect without the symmetry, and §0v made going "
                   "wide actually pay."),
        implement="LOW. `tokens_made` exists and the copy path is §0z5's.",
    ),
    Proposal(
        deck="rendmaw", card="Mycoloth", cost="{3}{G}{G}", identity="G",
        type_line="Creature — Fungus",
        oracle=("Devour 2 (As this creature enters, you may sacrifice any "
                "number of creatures. It enters with twice that many +1/+1 "
                "counters on it.)\n"
                "At the beginning of your upkeep, create a 1/1 green Saproling "
                "creature token for each +1/+1 counter on this creature."),
        verified="2026-09-16",
        rationale=("Mass token generation on a board §0v rewards for width. "
                   "Feeds Coat of Arms and Overwhelming Stampede, both "
                   "already present."),
        implement=("MEDIUM. Devour is a sacrifice-at-ETB the engine has no "
                   "generic path for, and the upkeep trigger scales off "
                   "counters. Read §0z12 first: making a dormant sacrifice "
                   "path live has already turned two cards instantly wrong."),
    ),
    Proposal(
        deck="rendmaw", card="Pitiless Plunderer", cost="{3}{B}", identity="B",
        type_line="Creature — Human Pirate",
        oracle=("Whenever another creature you control dies, create a "
                "Treasure token. (It's an artifact with \"{T}, Sacrifice this "
                "token: Add one mana of any color.\")"),
        verified="2026-09-16",
        rationale=("DIAGNOSTIC, not merely additive. Ashnod's Altar is "
                   "rendmaw's one significantly-negative MODEL-EVALUATED row "
                   "(-0.0013 +-0.0012) and it got there by being IMPLEMENTED "
                   "in §0z20, not neglected. This tests whether the Altar is "
                   "a bad card or an unfuelled one."),
        implement=("LOW. Treasures have been real mana since §0z6 and the "
                   "creature-death hook is `engine.on_creature_death`, which "
                   "§0z9 already corrected."),
    ),
    Proposal(
        deck="lorehold", card="Underworld Breach", cost="{1}{R}", identity="R",
        type_line="Enchantment",
        oracle=("Each nonland card in your graveyard has escape. The escape "
                "cost is equal to the card's mana cost plus exile three other "
                "cards from your graveyard. (You may cast cards from your "
                "graveyard for their escape cost.)\n"
                "At the beginning of the end step, sacrifice this "
                "enchantment."),
        verified="2026-09-16",
        rationale=("§0z19 turned lorehold's graveyard into a resource and "
                   "EVERY rummage spell and big spell rose with it -- "
                   "Faithless Looting +0.0055, Thrill of Possibility +0.0050, "
                   "Hit the Mother Lode +0.0052. This is the most direct "
                   "extension of that finding available."),
        implement=("ALREADY IMPLEMENTED IN FULL -- `lorehold.underworld_breach` "
                   "is a real escape loop and `breach_cap` is the knob that "
                   "bounds it. Nothing to build."),
        rejected=("ALREADY MEASURED, and this proposal should not have been "
                  "written. It is in the `lorehold1` batch and "
                  "`results/candidates_lorehold.txt` records +0.0015 +-0.0019 "
                  "at T10 and +0.0067 +-0.0052 at T20, N=6,000 -- INSIDE ITS "
                  "BARS at both. The escape loop is implemented, so that is "
                  "evidence about the card. `breach_cap` (4) is the knob its "
                  "evaluation rests on and has never been swept."),
    ),
    Proposal(
        deck="lorehold", card="Jeska's Will", cost="{2}{R}", identity="R",
        type_line="Sorcery",
        oracle=("Choose one. If you control a commander as you cast this "
                "spell, you may choose both instead.\n"
                "• Add {R} for each card in target opponent's hand.\n"
                "• Exile the top three cards of your library. You may play "
                "them this turn."),
        verified="2026-09-16",
        rationale=("Mana burst into the big spells §0z19 showed now pay off. "
                   "Mode 2 is fully modelled; the commander clause makes both "
                   "modes available, which §0z20 gave the engine a way to "
                   "express."),
        implement=("MEDIUM, and mode 1 is PARTLY_MODELLED by construction: it "
                   "counts an OPPONENT'S HAND, which the pod does not have "
                   "(§4). That is the identical limit §0z14 recorded for "
                   "Borrowed Knowledge -- so this card's row is a FLOOR and "
                   "must be classified accordingly, not as MODEL-EVALUATED."),
    ),
    Proposal(
        deck="lorehold", card="Past in Flames", cost="{3}{R}", identity="R",
        type_line="Sorcery",
        oracle=("Each instant and sorcery card in your graveyard gains "
                "flashback until end of turn. The flashback cost is equal to "
                "its mana cost.\n"
                "Flashback {4}{R} (You may cast this card from your graveyard "
                "for its flashback cost. Then exile it.)"),
        verified="2026-09-16",
        rationale=("The same graveyard-as-resource axis as Underworld Breach, "
                   "one-shot and cheaper to model. Worth measuring ALONGSIDE "
                   "Breach rather than against it -- they are interchangeable "
                   "enough that leave-one-out will understate both."),
        implement=("LOW-MEDIUM. §0z19 built the recursion path for six cards "
                   "already; this is that path applied to a whole card type."),
    ),
    Proposal(
        deck="tivit", card="Anointed Procession", cost="{3}{W}", identity="W",
        type_line="Enchantment",
        oracle=("If an effect would create one or more tokens under your "
                "control, it creates twice that many of those tokens "
                "instead."),
        verified="2026-09-16",
        rationale=("Tivit's own trigger makes artifact tokens, and the list "
                   "runs Academy Manufactor, Marionette Master, Disciple of "
                   "the Vault and Time Sieve to convert them. Doubling the "
                   "token stream feeds all four at once."),
        implement=("LOW for the tokens. WATCH TIME SIEVE: §0m records that it "
                   "eats only TOKEN artifacts, so doubling tokens makes the "
                   "extra-turn loop materially easier and `sieve_cap` stops "
                   "being decorative."),
    ),
    Proposal(
        deck="tivit", card="Urza, Lord High Artificer", cost="{2}{U}{U}",
        identity="U", type_line="Legendary Creature — Human Artificer",
        oracle=("When Urza enters, create a 0/0 colorless Construct artifact "
                "creature token with \"This token gets +1/+1 for each artifact "
                "you control.\"\n"
                "Tap an untapped artifact you control: Add {U}.\n"
                "{5}: Shuffle your library, then exile the top card. Until end "
                "of turn, you may play that card without paying its mana "
                "cost."),
        verified="2026-09-16",
        rationale=("Converts the artifact-token pile into mana and into a "
                   "body that scales with it -- the deck's two best-scoring "
                   "axes joined."),
        implement=("MEDIUM-HIGH. The Construct's P/T is DYNAMIC, which is "
                   "`DYNAMIC_PT_LANDS`' shape and the exact place §0z3 got a "
                   "card measured as a 16/16 instead of a 3/2. "
                   "`check_dynamic_pt_coverage()` must cover it."),
    ),
    Proposal(
        deck="tivit", card="Sai, Master Thopterist", cost="{2}{U}",
        identity="U", type_line="Legendary Creature — Human Artificer",
        oracle=("Whenever you cast an artifact spell, create a 1/1 colorless "
                "Thopter artifact creature token with flying.\n"
                "{1}{U}, Sacrifice two artifacts: Draw a card."),
        verified="2026-09-16",
        rationale=("The list is dense with artifacts (four signets, Sol Ring, "
                   "Academy Manufactor, Coercive Portal and more), so the "
                   "trigger fires often. Flying matters: `flier_block_share` "
                   "is 0.30, so evasive tokens are worth more than ground "
                   "ones in this model."),
        implement=("LOW. Token creation and the generated FLYING set are both "
                   "existing machinery -- but the tag must come from "
                   "`tag_flying.py`, never by hand (§0n)."),
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
]


DECKS = {
    # March of the World Ooze is COMMITTED as of v12, so it is in the deck
    # list itself and no longer a swap-in candidate.
    "rendmaw": (rendmaw_v12, {
        # 2026-09-16 batch (§0z26).
        "Parallel Lives": rendmaw_v12.PARALLEL_LIVES,
        "Mycoloth": rendmaw_v12.MYCOLOTH,
        "Cauldron of Essence": rendmaw_v12.CAULDRON_OF_ESSENCE}),
    # The four 2026-08-31/09-01 Lorehold changes are COMMITTED as of v16, so
    # they are in the deck list itself and no longer swap-in candidates.
    "lorehold": (lorehold_v16, {
        # 2026-09-16 batch (§0z26).
        "Jeska's Will": lorehold_v16.JESKAS_WILL,
        "Past in Flames": lorehold_v16.PAST_IN_FLAMES,
        "Molecule Man": lorehold_v16.MOLECULE_MAN,
        "Galvanoth": lorehold_v16.GALVANOTH,
        "Caldera Pyremaw": lorehold_v16.CALDERA_PYREMAW,
        "Radiant Scrollwielder": lorehold_v16.RADIANT_SCROLLWIELDER,
        "Hidden Retreat": lorehold_v16.HIDDEN_RETREAT,
        "Sunbird's Invocation": lorehold_v16.SUNBIRDS_INVOCATION}),
    # The three 2026-09-04 Karlov changes are COMMITTED as of v2, so they are
    # in the deck list itself and no longer swap-in candidates. Bolas's
    # Citadel (2026-09-12) is a candidate and NOT yet a deck member.
    "karlov": (karlov_v2, {
        # 2026-09-16 batch (§0z26), catalogued so a Change can name them.
        "Bloodthirsty Conqueror": karlov_v2.BLOODTHIRSTY_CONQUEROR,
        "Alhammarret's Archive": karlov_v2.ALHAMMARRETS_ARCHIVE,
        "Bolas's Citadel": karlov_v2.BOLASS_CITADEL}),
    # Added 2026-09-05 as a fourth deck. Nothing is staged yet: the list is the
    # one in Tivit_Seller_of_Secrets_Commander_Deck_v1.xlsx, card for card.
    "tivit": (tivit_v1, {
        # 2026-09-16 batch (§0z26).
        "Anointed Procession": tivit_v1.ANOINTED_PROCESSION,
        "Urza, Lord High Artificer": tivit_v1.URZA_LORD_HIGH_ARTIFICER,
        "Sai, Master Thopterist": tivit_v1.SAI_MASTER_THOPTERIST}),
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
        "Zuran Orb": azusa_v1.ZURAN_ORB}),
}


def check_proposals(strict: bool = True):
    """Every live PROPOSED entry is colour-legal, verified, and not already in.

    THREE CHECKS, AND THE FIRST ONE HAS ALREADY FIRED IN ANGER. Two azusa
    proposals -- Felidar Retreat (W) and Omnath, Locus of Rage (GR) -- were
    written from memory into a MONO-GREEN deck. They are kept in PROPOSED with
    `rejected` set, which is what this check demands of a dead entry.

      1. COLOUR IDENTITY must fit the commander's. A proposal that cannot be
         cast is not a weak idea, it is not an idea.
      2. ORACLE TEXT AND A VERIFIED DATE must be present. `CLAUDE.md` forbids
         guessing oracle text, and a proposal made from memory is that failure
         one step earlier. No Scryfall, no Proposal.
      3. NOT ALREADY IN THE DECK -- §0o in the ledger rather than the harness.

    A rejected entry is exempt from 1 and 3 and still bound by 2: the record of
    WHY it was rejected is worth nothing if the text it was rejected on is not
    there to check.
    """
    for pr in PROPOSED:
        if not pr.oracle.strip() or not pr.verified.strip():
            raise AssertionError(
                f"edhmc/pending.py: PROPOSED {pr.card!r} has no verified "
                f"oracle text. Fetch it from api.scryfall.com and set "
                f"`verified`; do not write card text from memory.")
        if pr.rejected:
            continue
        ident = set(pr.identity)
        allowed = DECK_IDENTITY[pr.deck]
        if not ident <= allowed:
            raise AssertionError(
                f"edhmc/pending.py: PROPOSED {pr.card!r} has colour identity "
                f"{''.join(sorted(ident)) or 'C'} but {pr.deck} is "
                f"{''.join(sorted(allowed))}. It cannot be cast in that deck. "
                f"Either remove it or set `rejected` with the reason.")
        if strict:
            module, _catalog = DECKS[pr.deck]
            deck, _ = module.build()
            if any(card.name == pr.card for card in deck):
                raise AssertionError(
                    f"edhmc/pending.py: PROPOSED {pr.card!r} is ALREADY IN "
                    f"{pr.deck}, so it describes an addition that cannot "
                    f"happen (§0o).")


def check_measured_are_promotable():
    """Every MEASURED card must be in its deck's catalog, and must NOT already
    be in the deck.

    Both halves are the §0q rule applied to this file. A Candidate naming a
    card the catalog does not hold cannot be promoted to a Change without an
    edit nobody will remember is needed -- the row would sit here looking
    actionable and fail the moment it was acted on. And a Candidate naming a
    card that has since been COMMITTED is the §0o failure in the ledger rather
    than in the harness: a measured row for a card already in the list reads
    as an available add and is not one.
    """
    for c in MEASURED:
        module, catalog = DECKS[c.deck]
        if c.card not in catalog:
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} is MEASURED for {c.deck} but is "
                f"not in DECKS[{c.deck!r}]'s catalog, so no Change could name "
                f"it. Add the Card to the catalog.")
        deck, _ = module.build()
        if any(card.name == c.card for card in deck):
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} is MEASURED for {c.deck} but is "
                f"ALREADY IN the list, so the row describes an addition that "
                f"cannot happen. Move it out of MEASURED -- it is committed.")


def check_shortlist_is_answerable():
    """A shortlisted Candidate names a cut, and that cut is really in the deck.

    The flag exists to survive being read months later, so the two ways it can
    silently stop meaning anything are both checked:

      * SHORTLISTED WITH NO CUT NAMED is the state this flag was invented to
        replace. "These are the good ones" without a cut is exactly the
        conversation that gets lost, and §0c is why naming the cut matters: a
        candidate row and an ablation row share a baseline, so the pair CANNOT
        be subtracted to get the swap -- somebody has to run it.
      * A CUT THAT LEFT THE DECK. Proposed cuts age badly: the list moves
        (four azusa cards were committed on 2026-09-10 and Perilous Forays is
        cut by a staged change), and a proposal naming a card that is no longer
        there reads as actionable and is not. Same shape as §0o.

    WHAT THIS DOES NOT CHECK, said out loud (§0z15): that the proposed cut is
    not MODEL-BLIND or PARTLY_MODELLED -- which is the trap that has already
    cost this project two withdrawn swaps (§0z, §0z2). Those categories live in
    `tools/ablation.py`. Until 2026-09-17 that module read `sys.argv` at
    import and could not be imported from here; it can be now (M4 of that
    day's review), and wiring this check up is the open follow-up. The rule
    is stated in each entry's own text instead, and it is the first thing to
    check by hand when acting on one.
    """
    for c in MEASURED:
        if not c.shortlist:
            if c.proposed_cut:
                raise AssertionError(
                    f"edhmc/pending.py: {c.card!r} names a proposed cut but is "
                    f"not shortlisted, so nothing prints it and the proposal "
                    f"is invisible. Set `shortlist`, or drop `proposed_cut`.")
            continue
        if not c.proposed_cut:
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} is SHORTLISTED for {c.deck} "
                f"with no `proposed_cut`. A shortlist without a named cut is "
                f"the conversation this flag exists to replace -- name the cut "
                f"the head-to-head should run, or clear the flag.")
        module, _ = DECKS[c.deck]
        deck, _cmd = module.build()
        staged_out = {ch.remove for ch in CHANGES if ch.deck == c.deck}
        if not any(card.name == c.proposed_cut for card in deck):
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} proposes cutting "
                f"{c.proposed_cut!r}, which is NOT IN the {c.deck} list, so "
                f"the head-to-head could not be run as written.")
        if c.proposed_cut in staged_out:
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} proposes cutting "
                f"{c.proposed_cut!r}, which a STAGED change already removes. "
                f"Two changes cannot cut the same card; pick another target.")


def check_withdrawn_are_explained():
    """Every WITHDRAWN entry states WHY, and is in exactly one of the lists.

    Written in the same change that added the list, and mutation-checked, for
    the reason §0q gives: a state with no check is a claim nobody verifies.
    The two failures it exists to catch are the two this state makes possible.

    An UNEXPLAINED withdrawal is the worse of them. The entry keeps its full
    original evidence -- rationale, data, every recheck -- so an entry with an
    empty `withdrawn` reads exactly like a well-supported staged change that
    somebody moved by accident, and the next reader's correct response to it
    would be to move it back. The reason is the only field that distinguishes
    "we decided against this" from "this fell out of the list".

    A card in BOTH lists is the §0z16 shape pointed at the ledger: one card,
    two states, and each list internally consistent. `build_pending` would
    apply it and this file would simultaneously say it applies to nothing.
    """
    for c in WITHDRAWN:
        if not c.withdrawn.strip():
            raise AssertionError(
                f"edhmc/pending.py: -{c.remove} +{c.add} ({c.deck}) is "
                f"WITHDRAWN with no `withdrawn` reason. An entry that keeps "
                f"its evidence and drops its reason is indistinguishable from "
                f"one unstaged by mistake. Say when, and why.")
        clash = [s for s in CHANGES
                 if s.deck == c.deck and s.add == c.add and s.remove == c.remove]
        if clash:
            raise AssertionError(
                f"edhmc/pending.py: -{c.remove} +{c.add} ({c.deck}) is in "
                f"CHANGES and WITHDRAWN at once, so the ledger both applies it "
                f"to every baseline and says it is in none. Delete one.")


def check_alt_cost_coverage():
    """Every card with a second cost sits in a deck whose engine reads them.

    §1b, closed 2026-09-13 (§0z20). `Card.alt_costs` existed for a year and
    `engine.main_phase` was the ONLY reader, so Overlord of the Hauntwoods'
    Impending worked in Rendmaw and the identical field on a card put into
    Karlov, Tivit, Shilgengar or Azusa would have been silently ignored --
    cast at its printed cost, no error, no way to notice. That is §0q's
    failure mode with the claim living in a DATA FIELD instead of a name set:
    setting `alt_costs` looks like it does something everywhere.

    All six engines now go through `engine.choose_mode`, and this is the check
    that says so. It is derived, not hand-maintained: the reader set is read
    off the engines' source, so an engine that stops calling `choose_mode`
    fails here rather than quietly dropping a cost.
    """
    import inspect
    from edhmc import engine, lorehold, karlov, tivit, shilgengar, azusa
    engines = {"rendmaw": engine, "lorehold": lorehold, "karlov": karlov,
               "tivit": tivit, "shilgengar": shilgengar, "azusa": azusa}
    readers = {name for name, mod in engines.items()
               if "choose_mode(" in inspect.getsource(mod)}
    missing = set(engines) - readers
    if missing:
        raise AssertionError(
            f"edhmc/pending.py: {sorted(missing)} do not call "
            f"engine.choose_mode, so any card with `alt_costs` in those decks "
            f"would be cast at its printed cost silently. §1b / §0z20.")

    for deck_name, (module, _catalog) in DECKS.items():
        deck, commander = module.build()
        for card in list(deck) + [commander]:
            if card.alt_costs and deck_name not in readers:
                raise AssertionError(
                    f"edhmc/pending.py: {card.name!r} declares alt_costs but "
                    f"the {deck_name} engine does not read them.")
            for entry in card.alt_costs:
                if len(entry) not in (2, 3):
                    raise AssertionError(
                        f"edhmc/pending.py: {card.name!r} has a malformed "
                        f"alt_costs entry {entry!r}; expected (cost, tag) or "
                        f"(cost, tag, preference).")


check_proposals()


check_measured_are_promotable()
check_shortlist_is_answerable()
check_withdrawn_are_explained()
check_alt_cost_coverage()


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


def print_proposals() -> None:
    """PROPOSED, grouped by deck. Printed last because it is the weakest state:
    verified card text and an argument, with no number attached to any of it."""
    live = [p for p in PROPOSED if not p.rejected]
    dead = [p for p in PROPOSED if p.rejected]
    print("\n" + "=" * 78)
    print(f"PROPOSED — oracle text verified, NOTHING MEASURED ({len(live)} live)")
    print("=" * 78)
    print("  Next step for each is a tools/candidates.py batch entry, not a")
    print("  staging. A Proposal has no confidence interval; a Candidate does.")
    for deck_name in sorted({p.deck for p in live}):
        rows = [p for p in live if p.deck == deck_name]
        print(f"\n{deck_name.upper()}  ({len(rows)})")
        for pr in rows:
            print(f"  + {pr.card}  {pr.cost}  [{pr.identity or 'C'}]")
            print(f"    {pr.type_line}")
            for line in pr.oracle.split("\n"):
                print(f"    | {line}")
            print(f"    why    {pr.rationale}")
            print(f"    build  {pr.implement}")
            print(f"    text verified {pr.verified} from api.scryfall.com")
    if dead:
        print(f"\nREJECTED ({len(dead)}) — kept so they are not proposed again")
        for pr in dead:
            print(f"  x {pr.card} ({pr.deck}): {pr.rejected}")


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
                # PRINTED FOR STAGED ENTRIES SINCE 2026-09-13, and it was the
                # only field of a Change this function did not show. A
                # `reverified` is written precisely when an engine change has
                # re-run the swap, so it is the field most likely to CONTRADICT
                # the `data` line above it -- and the rendmaw entry proved the
                # cost: its 2026-09-12 recheck said the evidence had collapsed
                # to a third, and `python -m edhmc.pending`, which HANDOFF.md
                # calls the only trustworthy statement of what is staged,
                # printed the original figures and not the retraction.
                if c.reverified:
                    print(f"    recheck {c.reverified}")
        deck, cmd = build_pending(deck_name)
        print(f"    -> {len(deck) + 1} cards, singleton-legal, commander distinct")
    if MEASURED:
        # PRINTED UNDER ITS OWN HEADING AND BELOW THE STAGED ONES, because the
        # single most useful thing this section can do is not be mistaken for
        # the section above it. A measured card is a number; a staged card is
        # a decision.
        print("\n" + "=" * 78)
        print("MEASURED — a number exists, NOTHING HAS BEEN DECIDED")
        print("=" * 78)
        print("  Not staged. No cut named. Promoting one of these needs a "
              "head-to-head\n  against a specific cut: everything here shares "
              "one baseline, so these\n  rows cannot be ranked against each "
              "other or against anything else (§0c).")
        for deck_name in sorted({c.deck for c in MEASURED}):
            rows = [c for c in MEASURED if c.deck == deck_name]
            print(f"\n{deck_name.upper()}  ({len(rows)} measured, 0 staged "
                  f"from this batch)")
            # SHORTLISTED ROWS FIRST, and marked, because the one thing a
            # reader wants from this section is which of thirteen numbers
            # somebody has actually looked at. Still Candidates: the marker
            # says a head-to-head is proposed, not that anything is staged.
            rows.sort(key=lambda c: (not c.shortlist, c.card))
            for c in rows:
                print(f"  {'>>' if c.shortlist else ' ?'}  {c.card}"
                      + ("   [SHORTLISTED — head-to-head proposed, NOT staged]"
                         if c.shortlist else ""))
                print(f"     win    {c.win_rate}   signal {c.signal}")
                print(f"     measured {c.measured}")
                if c.shortlist:
                    print(f"     cut?   proposed head-to-head: "
                          f"-{c.proposed_cut} +{c.card}")
                    print(f"     why it {c.shortlist}")
                if verbose:
                    print(f"     why    {c.rationale}")
                    print(f"     data   {c.evidence}")
                    if c.limits:
                        print(f"     limits {c.limits}")
                    if c.verdict:
                        print(f"     read   {c.verdict}")

    if WITHDRAWN:
        # PRINTED, not silently dropped. The whole reason this list exists is
        # that an unstaged change leaves no trace anywhere else: it is out of
        # CHANGES, so `build_pending` ignores it, so no run and no table can
        # ever mention it again. A reader who does not see it here will
        # re-measure the card from scratch, which is the cost this heading
        # exists to avoid.
        print("\n" + "=" * 78)
        print("WITHDRAWN — was staged, has been UNSTAGED, is in NO baseline")
        print("=" * 78)
        print("  Not refuted unless the entry says so. `build_pending` does "
              "not apply these,\n  so nothing below is in any deck, any run "
              "or any table. Each entry's\n  `why not` says what re-staging "
              "it would have to answer.")
        for c in WITHDRAWN:
            print(f"\n{c.deck.upper()}")
            print(f"  - OUT  {c.remove}")
            print(f"  + IN   {c.add}")
            print(f"    staged {c.staged}, then unstaged")
            if verbose:
                print(f"    why    {c.rationale}")
                print(f"    data   {c.evidence}")
                if c.notes:
                    print(f"    note   {c.notes}")
                if c.reverified:
                    print(f"    recheck {c.reverified}")
            print(f"    why not {c.withdrawn}")

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
    print_proposals()
