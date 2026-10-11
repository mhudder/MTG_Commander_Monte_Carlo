"""karlov's ledger entries and swap-in catalog.

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

from edhmc.decks import karlov_v2
from edhmc.ledger.records import Change, Candidate, Simulated, Proposal


COMMITTED: list[Change] = [
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
]


MEASURED: list[Candidate] = [
    Candidate(
        deck='karlov',
        card='Selenia, the Cursed Heart',
        measured='2026-09-29',
        win_rate='REAL SWAP -Swiftfoot Boots +Selenia, the Cursed Heart, N=15,000 paired: +0.0039 +-0.0016 (significant) at T10 and +0.0160 +-0.0029 (significant) at T20.',
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. +5.8 life a game from the doubler at T20 and 0.05 curses (she dies only to the pod here -- karlov has no sacrifice policy).",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits="THE CUT IS NOT NEUTRAL: Swiftfoot Boots' own row is -0.0041 +-0.0022, significantly NEGATIVE, so part of this swap is the Boots leaving (§0z36). And the owner KEPT the Boots on 2026-09-26 for shroud this model cannot fully see.",
        verdict="Significant at both horizons, below Bloodthirsty Conqueror's +0.0401 against the same cut.",
    ),
    Candidate(
        deck='karlov',
        card='Pearl Collector',
        measured='2026-09-29',
        win_rate='REAL SWAP -Swiftfoot Boots +Pearl Collector, N=15,000 paired: +0.0100 +-0.0019 (significant) at T10 and +0.0197 +-0.0032 (significant) at T20.',
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. +0.65 lifegain events a game at T20 (lifelink combat), 0.14 Mox Pearls. Events are the axis every karlov payoff counts.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='PARTLY: deathtouch not modelled. The Boots cut is itself significantly negative (see Selenia), so the swap overstates the card by that much.',
        verdict="Significant at both horizons; the larger karlov number of the two, still well below the Conqueror's +0.0401 in the same slot.",
    ),
    Candidate(
        deck='karlov',
        card='Liliana the Faultless',
        measured='2026-09-21',
        win_rate=('REAL SWAP -Swiftfoot Boots +Liliana, N=15,000 paired: +0.0064 +-0.00'
            '17 at T10 and +0.0138 +-0.0029 at T20, significant at both. AND IT L'
            'OSES THE SLOT: Bloodthirsty Conqueror -> Liliana in that slot is -0.'
            '0238 +-0.0029 / -0.0250 +-0.0035, significant at both.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence='results/karlov_fra.txt (diagnostics/run_karlov_fra.py)',
        limits=("STALE -- NOT RESTATED. This deck's baseline has MOVED since the meas"
            'urement (§0z44: Felidar Sovereign and Sorin priority moves adopted 2'
            "026-09-25; and Voice of the Blessed's ten-counter indestructible, 20"
            '26-09-25); check_unchanged_decks 246b148 vs 2026-09-25 reports it MO'
            'VED on 8 of 8 metrics. Re-measure before any head-to-head decision r'
            'ests on it.'),
        verdict=('Beats the cut, loses the slot to the Conqueror by a margin far outsi'
            'de both bars. Not a contender for the Boots slot while the Conqueror'
            ' wants it.'),
    ),
    Candidate(
        deck='karlov',
        card='Edgar, Ancient Bloodlord',
        measured='2026-09-21',
        win_rate=('REAL SWAP -Swiftfoot Boots +Edgar, N=15,000 paired: +0.0033 +-0.0015'
            ' at T10 and +0.0095 +-0.0028 at T20, significant at both. AND IT LOS'
            'ES THE SLOT: Bloodthirsty Conqueror -> Edgar is -0.0273 +-0.0029 / -'
            '0.0300 +-0.0033, significant at both.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence='results/karlov_fra.txt (diagnostics/run_karlov_fra.py)',
        limits=("STALE -- NOT RESTATED. This deck's baseline has MOVED since the meas"
            'urement (§0z44: Felidar Sovereign and Sorin priority moves adopted 2'
            "026-09-25; and Voice of the Blessed's ten-counter indestructible, 20"
            '26-09-25); check_unchanged_decks 246b148 vs 2026-09-25 reports it MO'
            'VED on 8 of 8 metrics. Re-measure before any head-to-head decision r'
            'ests on it.'),
        verdict=('The weaker of the two karlov Reality Fracture cards, and it loses th'
            'e slot to the Conqueror by more than Liliana does.'),
    ),
    Candidate(
        deck="karlov",
        card="Ginger, Queen of Sweets",
        measured="2026-09-22",
        win_rate=("REAL SWAP -Swiftfoot Boots +Ginger, N=15,000 paired, same "
                  "seeds both legs, base = build_pending('karlov'): "
                  "+0.0052 +-0.0017 at T10 and +0.0186 +-0.0033 at T20, "
                  "significant at BOTH. Candidate row against a blank in the "
                  "same slot: +0.0059 +-0.0027 (results/candidates_karlov3.txt)."),
        signal="both",
        rationale=("The first card in this project to use the monarch "
                   "(§0z39). Chosen for karlov over the stronger raw fit in "
                   "tivit so the number could be ATTRIBUTED -- see the "
                   "Proposal."),
        evidence="results/karlov_ginger.txt, results/candidates_karlov3.txt",
        limits=(
            "A SIX-DROP FIRST AND A MONARCH CARD SECOND. P(resolves) is "
            "0.152 -- one game in six, the Bolas's Citadel shape (14.4%) -- "
            "and stranded_mv is +7.1, which is what a {6} costs a list that "
            "curves lower. THE CROWN IS HELD 1.03 TURNS conditional on "
            "resolving, exactly as §0z39 predicted for a card that arrives "
            "late: first_attack_turn is 3, so a card cast on turn 6 gets none "
            "of the free window that made monarch_start look like +0.10. The "
            "TOKENS are the bigger half: 2.96 Gingerbrutes per resolution "
            "against 1.03 monarch draws. "
            "FLOOR, two clauses: the Gingerbrute's '{1}: can't be blocked "
            "except by creatures with haste' is blind (§4 -- the opponents' "
            "blockers are a count with no haste to check), and Ginger's own "
            "'{2},{T}, Sacrifice: gain 6 life' is a deliberate policy "
            "omission. CEILING, one: the pod's three upkeeps are taken before "
            "pod_phase can take the crown, so the token count is generous by "
            "at most two in the round it changes hands. "
            "AND THE SACRIFICE CLAUSE NEVER FIRES -- gingerbrute_sacs is "
            "0.0000, not near zero. It is implemented and correct: a "
            "Gingerbrute has HASTE, so `combat` attacks with it the turn it "
            "arrives and taps it, and a tapped token cannot pay the {T} in "
            "its own sacrifice cost. That is the rules, but it is also the "
            "engine's attack-with-everything POLICY deciding the card's "
            "second channel is worth nothing, which is the shape of all four "
            "rows in CLAUDE.md's policy table. `gingerbrute_keep` therefore "
            "does nothing at any setting and was not swept."),
        verdict=(
            "A REAL CARD THAT LOSES ITS SLOT, and both halves are measured. "
            "Against the cut item 22 established it is +0.0186 +-0.0033 at "
            "T20, level with Alhammarret's Archive (+0.0168 +-0.0030, the "
            "same cut and the same staged baseline) and well below "
            "Bloodthirsty Conqueror (+0.0401 +-0.0037, measured on the "
            "pre-swap list). The ranking does not rest on comparing those "
            "three numbers, which §0e forbids: Conqueror -> Ginger IN THE "
            "SAME SLOT, paired on the same seeds, is -0.0247 +-0.0029 at T10 "
            "and -0.0210 +-0.0034 at T20, significant at both and the same "
            "size both times. The Boots are ONE slot and the Conqueror wants "
            "it more. NOT STAGED, and not because of doubt."),
    ),
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
        verdict=(
            "THE HOLD STANDS, AND THE CUT SIDE IS NO LONGER THE MISSING HALF "
            "(2026-09-20, §0z35). Queued item 22 asked whether karlov's three "
            "significantly-negative MODEL-EVALUATED rows are cuts or §0j "
            "artefacts, and diag_threat_blank answered it on the current "
            "staged list: Blood Artist's whole negative row is the blank's two "
            "hand-tuned constants (text alone +0.0024 +-0.0011, significantly "
            "POSITIVE -- NOT a cut candidate), while Mother of Runes "
            "(-0.0053 +-0.0021) and Swiftfoot Boots (-0.0044 +-0.0020) stay "
            "negative through every arm. Their bars overlap and §0e forbids "
            "ranking two leave-one-out rows against each other, so the "
            "tie-break is mechanism: cutting the Boots leaves both modelled "
            "protection channels standing, while cutting Mother of Runes "
            "closes try_protect() outright (`protection_cards` is a "
            "one-element tuple holding her alone) and takes the staged list's "
            "`shroud_sources` to one. SWIFTFOOT BOOTS IS KARLOV'S NAMED CUT "
            "for whatever is added next. It is recorded here because this is "
            "the deck's only unstaged Candidate and a cut with no add is half "
            "a swap -- it does NOT reopen this card, whose hold is about the "
            "five-mana artifact and not about the slot. Evidence: "
            "results/threat_blank_karlov_2026-09-20.txt. AND THE TIE-BREAK'S "
            "FIRST HALF IS GONE (§0z118, 2026-10-07): the try_protect channel "
            "was not her text -- she was DISCARDED FROM HAND to blank removal "
            "and wrath alike. Now she never attacks (the owner's rule) and "
            "her {T} makes one spot removal a round fizzle -- worth +0.0069 "
            "at T20 against never using her -- while a SHROUD (the Boots) "
            "redirects the removal, and karlov wins +0.0054 with no "
            "commander shroud at all. Re-read both rows after the rebuild "
            "before naming a cut on this evidence."),
    ),
    Candidate(
        deck='karlov',
        card='Scoured Barrens',
        measured="2026-10-06",
        win_rate='+0.0014 +-0.0018 at T10, +0.0009 +-0.0025 at T20 against a Plains',
        signal='--',
        rationale="A tapped W/B dual that gains 1 -- a lifegain EVENT for Karlov's triggers.",
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Plains. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: life_gained -0.011, life_lost_to_own_cards +0.002, lifegain_triggers +0.099. §0z113.',
        limits="Every clause modelled through karlov's land `lifegain` hook (Radiant Fountain's).",
        verdict='Inside its bar at both horizons. Karlov has its colours already (§0z112: duals are worth nothing over a basic past the critical mass), and one lifegain trigger a game is small.',
    ),
    Candidate(
        deck='karlov',
        card='Kabira Crossroads',
        measured="2026-10-06",
        win_rate='-0.0017 +-0.0017 at T10, -0.0017 +-0.0025 at T20 against a Plains',
        signal='dmg',
        rationale='A tapped Plains that gains 2.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Plains. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: life_gained +0.203, life_lost_to_own_cards -0.001, lifegain_triggers +0.084. §0z113.',
        limits="Every clause modelled. Not legendary, so not the Crossroads' bounce-and-replay trick -- which this engine has no way to do anyway.",
        verdict='Slightly NEGATIVE at T10 (significant) and inside at T20: entering tapped costs more than 2 life and a trigger are worth.',
    ),
    Candidate(
        deck='karlov',
        card='Ancient Tomb',
        measured="2026-10-06",
        win_rate='+0.0009 +-0.0022 at T10, -0.0050 +-0.0030 at T20 against a Swamp',
        signal='both',
        rationale='{C}{C} from a land, for 2 damage a tap.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Swamp. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: life_gained -0.514, life_lost_to_own_cards +1.201, lifegain_triggers -0.048, tomb_damage +1.223. §0z113.',
        limits='Every clause modelled: the damage is charged per tap (1.2 a game). Spent LAST among lands (`PAINFUL_RANK`).',
        verdict='Inside at T10, significantly NEGATIVE at T20: the life is a real cost in a deck whose objective is life, and colourless mana is worth little to its coloured costs. OWNER DEFERRED 2026-10-06: a valid card, but outside the price range of the casual table the owner plays at -- a judgement about the table, not about the number.',
    ),
]


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
            "(§0e). Damage is -1.46 / -2.57 and that is the MECHANISM, not a "
            "cost: the extra wins arrive by the combo route, which ends the "
            "game before the board deals damage. Combo wins 0.312 -> 0.375. "
            "RESTATED 2026-09-17 (§0z29): those figures were measured with "
            "the card as a GROUND creature -- decks/_evasion.py had not been "
            "regenerated after it was added. With flying, same N and seeds "
            "(diagnostics/run_karlov_conqueror.py): +0.0259 [+0.0233, "
            "+0.0287] at T10 and +0.0254 [+0.0218, +0.0291] at T20, and the "
            "candidate row +0.0331 +-0.0033. Flying is worth nothing "
            "measurable to this card; the staging rests on the trigger. "
            "AND THE CUT IS MODEL-BLIND (2026-09-17, §0z31's check): "
            "Soulmender is in KNOWN_BLIND for karlov -- its tap ability is "
            "not implemented, so it is a 1/1 body here -- and the "
            "'-0.0011 +-0.0011, significantly negative' row §0z27 called the "
            "cheapest cut was a blind row read as evidence. The head-to-head "
            "above therefore measures the Conqueror against a vanilla 1/1, "
            "and its +0.0254 is a CEILING by whatever '{T}: gain 1 life' in "
            "a deck of lifegain triggers is actually worth."),
        cut_unmeasured=(
            "Soulmender's row is blind and the swap is a ceiling, and it is "
            "staged anyway because the cut is a one-mana 1/1 whose tap "
            "ability is one lifegain EVENT a turn in a deck whose payoffs "
            "count events -- worth something, but the Conqueror's +0.0254 "
            "is nine times the bar, and a 1/1 tapping for one trigger a turn "
            "is not a 0.025 card. Judgement, said out loud; measure it if "
            "the engine ever models tap-for-life."),
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
        reverified='RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0447 +-0.0035 at T10, +0.0474 +-0.0038 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + "RE-MEASURED 2026-10-05 after §0z104 (the wipe gate asked at every optional cast site), in context, N=15,000 paired: +0.0418 +-0.0034 at T10, +0.0443 +-0.0038 at T20 (up from +0.0271 at T20 on 2026-09-29: the engine changes since, chiefly §0z90's general Exquisite Blood clause, which this second copy of the trigger shares). results/restage_20261005.txt. " + (
            'NOT RE-MEASURED -- THE BASELINE MOVED UNDER IT (2026-09-25, §0z44)'
            '. The owner adopted two karlov priority moves (Felidar Sovereign 7'
            ' -> 9, Sorin, Solemn Visitor 6 -> 8), jointly +0.0099 / +0.0091 at'
            ' T10 / T20, so the list this swap was measured against no longer e'
            'xists. The number above is on the OLD priorities and has not been '
            'restated. The karlov TABLE was rebuilt 2026-09-26 (§0z60); this SWA'
            'P was not, and still needs re-measuring on the new baseline before '
            'it is committed.'
            " RE-MEASURED 2026-09-26 ON THE REBUILT BASELINE (§0z63), in context (Citadel staged on both sides), N=15,000 paired: +0.0255 +-0.0028 at T10, +0.0266 +-0.0035 at T20. The staging stands. THE ALTERNATIVE CUT, measured the same run: -Swiftfoot Boots +Bloodthirsty Conqueror +0.0278 / +0.0341, and the two cuts compared directly (Boots minus Soulmender, same card) +0.0023 +-0.0038 at T10, +0.0075 +-0.0047 at T20 -- still the better cut at T20, by less than the +0.0125 measured on the old baseline. results/restage_20260926.txt."
            " THE OWNER DECIDED, 2026-09-26: SOULMENDER STAYS THE CUT. The Boots remain because in an interaction-heavy pod the shroud does real work that this model cannot fully see (the pod's removal is a roll against an abstract board, §4). A judgement about the owner's table outranking a +0.0075 +-0.0047 edge at T20 that is inside its bar at T10."
        + ' ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0251 +-0.0028 at T10, +0.0271 +-0.0034 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81)."),
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
            "**ITS NUMBER WAS CALLED A CEILING FOR QUEUED ITEM 17, AND THAT "
            "IS NOW MEASURED AND FALSE** (§0z42, 2026-09-22). Decking loses "
            "now, and on this staged list -- Citadel in -- the rule changed "
            "nothing: N=15,000 at each of T10 and T20, identical game for "
            "game on every metric with and without it. The dig stops at an "
            "unplayable land or at the life floor long before the library "
            "runs out. The number stands as measured. "
            "The sac-ten drain is implemented LETHAL-ONLY (ten nonland "
            "permanents, and only when every living opponent is at 10 or "
            "less), which is deliberately conservative and a floor on that "
            "half -- the model cannot value 'I am losing anyway'."
        ),
        reverified='RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0049 +-0.0030 at T10, +0.0131 +-0.0040 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + "RE-MEASURED 2026-10-05 after §0z104 (the wipe gate asked at every optional cast site), in context, N=15,000 paired: +0.0043 +-0.0031 at T10, +0.0193 +-0.0042 at T20; the Citadel's dig now stops at a wipe the gate refuses. results/restage_20261005.txt. " + (
            'NOT RE-MEASURED -- THE BASELINE MOVED UNDER IT (2026-09-25, §0z44)'
            '. The owner adopted two karlov priority moves (Felidar Sovereign 7'
            ' -> 9, Sorin, Solemn Visitor 6 -> 8), jointly +0.0099 / +0.0091 at'
            ' T10 / T20, so the list this swap was measured against no longer e'
            'xists. The number above is on the OLD priorities and has not been '
            'restated. The karlov TABLE was rebuilt 2026-09-26 (§0z60); this SWA'
            'P was not, and still needs re-measuring on the new baseline before '
            'it is committed.'
            " RE-MEASURED 2026-09-26 ON THE REBUILT BASELINE (§0z63), in context (Conqueror staged on both sides), N=15,000 paired: +0.0013 +-0.0029 at T10 (inside), +0.0147 +-0.0042 at T20. A long-horizon card, as before; the staging stands. results/restage_20260926.txt."
        + ' ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0015 +-0.0029 at T10, +0.0131 +-0.0042 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81)."),
    ),
]


WITHDRAWN: list[Change] = []


SIMULATED: list[Simulated] = [
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add='Selenia, the Cursed Heart',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Swiftfoot Boots +Selenia, the Cursed Heart, N=15,000 paired: +0.0039 +-0.0016 (significant) at T10 and +0.0160 +-0.0029 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0039 +-0.0017 * at T10 and +0.0159 +-0.0030 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add='Pearl Collector',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Swiftfoot Boots +Pearl Collector, N=15,000 paired: +0.0100 +-0.0019 (significant) at T10 and +0.0197 +-0.0032 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0099 +-0.0019 * at T10 and +0.0195 +-0.0031 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add='Liliana the Faultless',
        measured='2026-09-21', source='results/karlov_fra.txt',
        result=('REAL SWAP -Swiftfoot Boots +Liliana, N=15,000 paired: +0.0064 +-0.0017 at T10 and +0.0138 +-0.0029 at T20, significant at both. AND IT LOSES THE SLOT: Bloodthirsty Conqueror -> Liliana in that slot is -0.0238 +-0.0029 / -0.0250 +-0.0035, significant at both.'),
    ),
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add='Edgar, Ancient Bloodlord',
        measured='2026-09-21', source='results/karlov_fra.txt',
        result=('REAL SWAP -Swiftfoot Boots +Edgar, N=15,000 paired: +0.0033 +-0.0015 at T10 and +0.0095 +-0.0028 at T20, significant at both. AND IT LOSES THE SLOT: Bloodthirsty Conqueror -> Edgar is -0.0273 +-0.0029 / -0.0300 +-0.0033, significant at both.'),
    ),
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add='Ginger, Queen of Sweets',
        measured='2026-09-22', source='results/karlov_ginger.txt',
        result=("REAL SWAP -Swiftfoot Boots +Ginger, N=15,000 paired, same seeds both legs, base = build_pending('karlov'): +0.0052 +-0.0017 at T10 and +0.0186 +-0.0033 at T20, significant at BOTH. Candidate row against a blank in the same slot: +0.0059 +-0.0027 (results/candidates_karlov3.txt)."),
        notes=("RE-MEASURED 2026-10-01 AFTER §0z97 (losing the crown no longer ends the pod's chip round), same seeds both engines: +0.0045 +-0.0020 at T10 and +0.0137 +-0.0031 at T20, significant at both, against +0.0046 / +0.0142 on the old loop -- the fix itself moved the swap -0.0005 +-0.0003 at T20. The old loop now reads +0.0142 where 2026-09-22 read +0.0186: that gap is the engine changes in between, not the crown, and is not attributed further. It still loses the slot to Bloodthirsty Conqueror (results/monarch_restage_20261001.txt)."),
    ),
    # ---- head-to-heads recorded before the split, in other entries ----
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add='Bloodthirsty Conqueror',
        measured='2026-09-20', source='results/karlov_boots.txt',
        result=('+0.0299 +-0.0029 at T10 and +0.0401 +-0.0037 at T20, '
                'significant at both, on the pre-swap baseline (§0z36).'),
        notes=('The same card is STAGED against Soulmender instead: the owner '
               'kept the Boots on 2026-09-26 (queued item 20b).'),
    ),
    Simulated(
        deck='karlov', remove='Swiftfoot Boots', add="Alhammarret's Archive",
        measured='2026-09-20', source='results/karlov_boots.txt',
        result=('+0.0055 +-0.0016 at T10 and +0.0168 +-0.0030 at T20, '
                'significant at both, given the staging (§0z36).'),
        notes='HELD on the owner\'s playtest experience (queued item 20b).',
    ),
]


PROPOSED: list[Proposal] = [
    Proposal(
        deck='karlov', card='Selenia, the Cursed Heart', cost='{4}{W}{B}',
        identity='WB', type_line='Legendary Creature — Angel Warrior',
        oracle='Flying, lifelink\nIf you would gain life, you gain twice that much life instead.\nWhen Selenia dies, create a legendary black Aura Curse enchantment token named Selenia\'s Curse attached to target opponent. The token has enchant player and "If enchanted player would lose life, they lose twice that much life instead."',
        verified="2026-09-29",
        rationale="A THIRD copy of The Wind Crystal's replacement, on a flying lifelink body. The deck counts lifegain EVENTS, which the doubler does not add -- but Sanguine Bond, Vito, Well of Lost Dreams and the life thresholds (Serra Ascendant, Felidar Sovereign) all read the AMOUNT, and the curse doubles every drain into one opponent.",
        implement="DONE 2026-09-29. The doubler sits beside The Wind Crystal and Alhammarret's Archive in `karlov.gain_life`, stacking multiplicatively (616.1), counted as `selenia_extra_life`. The curse is `opponents.curse_opponent` from `on_creature_death`. This engine has no sacrifice policy, so she dies only to the pod's removal and wipes -- which makes the curse rarer here than in shilgengar (0.04/game against 0.12). Classify SCRIPTED at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Swiftfoot Boots is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='karlov', card='Pearl Collector', cost='{2}{B}',
        identity='WB', type_line='Creature — Human Warlock',
        oracle='Deathtouch, Lifelink\nAt the beginning of your second main phase, if you gained 4 or more life this turn, conjure a card named Mox Pearl into your hand. This ability triggers only once.\n{2}{W}: Another target creature perpetually gains lifelink.',
        verified="2026-09-29",
        rationale='Lifelink on a three-drop is a lifegain event every combat, which is the axis every payoff in this list counts, and karlov gains four life in a turn easily, so the Mox is close to guaranteed.',
        implement="DONE 2026-09-29. Same shared functions as shilgengar's: the trigger before the postcombat main, the {2}{W} sink after it (`karlov.pay_cost`, through `spend_lg` so Pristine Talisman still gains its life), and `perpetual_lifelink` read in `combat`'s lifelink test. PARTLY: deathtouch not modelled. Classify PARTLY_MODELLED at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Swiftfoot Boots is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck="karlov",
        card="Ginger, Queen of Sweets",
        cost="{6}",
        identity="",
        type_line="Legendary Artifact Creature — Food Noble",
        oracle=("When Ginger enters, you become the monarch.\n"
                "{2}, {T}, Sacrifice Ginger: You gain 6 life.\n"
                "At the beginning of each upkeep, if you're the monarch, "
                "create a Gingerbrute token. (It's a {1} 1/1 Food Golem "
                "artifact creature with haste, \"{1}: This token can't be "
                "blocked this turn except by creatures with haste,\" and "
                "\"{2}, {T}, Sacrifice this token: You gain 3 life.\")"),
        verified="2026-09-22",
        rationale=(
            "THE FIRST CARD IN THIS PROJECT THAT USES THE MONARCH, which "
            "§0z39 built and pinned before any card asked for it. Colour "
            "identity is EMPTY, so it is legal in all six lists and the deck "
            "is a choice rather than a constraint. It is proposed for karlov "
            "and NOT for tivit, which is the stronger raw fit -- there "
            "Gingerbrute is a FOOD, so it would trigger Academy Manufactor, "
            "be doubled by the staged Anointed Procession and feed Time Sieve "
            "(§0m) -- precisely because that is three interactions at once "
            "and §0z27 showed what redundancy does to a row: nobody could "
            "attribute the number to this card. In karlov the value "
            "decomposes into three things the engine measures separately: the "
            "crown's card at your end step, 1/1 HASTE bodies in a deck §0v "
            "made width worth something to, and a lifegain EVENT per "
            "Gingerbrute sacrificed -- events being what this deck's payoffs "
            "actually count. Every Gingerbrute entering is also a creature "
            "entering, which the soul sisters read."),
        implement=(
            "DONE 2026-09-22. Four hooks, none of them new machinery: the ETB "
            "calls opponents.become_monarch (§0z39, one implementation for "
            "all six engines); karlov.gingerbrute_tokens(g, n) runs at your "
            "upkeep with 1 and before pod_phase with 3, which is "
            "azusa.verdant_kraken_tokens' shape for 'each player's upkeep' "
            "rather than a second spelling of it (§0u); the token is built "
            "directly rather than through Game.make_tokens because HASTE "
            "needs sick=False and that helper forces sick=True, and widening "
            "its signature would put two cards on one hook (§0z28); "
            "gingerbrute_sacrifices runs at end step on spare mana, keyed to "
            "the gingerbrute_keep knob, routed through gain_life and "
            "on_creature_death. Counters: gingerbrutes_made, "
            "gingerbrute_sacs. Pinned by tests/test_ginger.py. Classified "
            "PARTLY MODELLED -- the token's unblockable activation is blind "
            "(§4: no blockers to check for haste) and Ginger's own sacrifice "
            "is a deliberate policy omission."),
        rejected=("MEASURED 2026-09-22 and PROMOTED: the real swap "
                  "-Swiftfoot Boots +Ginger is +0.0186 +-0.0033 at T20, and "
                  "Conqueror -> Ginger in that same slot is -0.0210 +-0.0034, "
                  "so the card is real and loses the slot. See the Candidate "
                  "entry; this Proposal is closed rather than deleted so the "
                  "verified oracle text stays where it was written."),
    ),
    # -----------------------------------------------------------------------
    # REALITY FRACTURE (Scryfall `fra`), scanned 2026-09-20. THE SET IS NOT
    # OUT -- it releases 2026-10-02, 372 of its 564 printings are spoiled, and
    # every new card in it reads `not_legal` in Commander for that reason
    # alone. The text below is PREVIEW text and can change before release, so
    # any number measured on it is a claim with a date. The project has been
    # doing this for a month without saying so: Enlightened Confidant is a
    # `fra` card, implemented in karlov.py and measured on 2026-09-04.
    # -----------------------------------------------------------------------
    Proposal(
        deck="karlov", card="Liliana the Faultless", cost="{W}",
        identity="W", type_line="Legendary Creature — Human Cleric",
        oracle=("Whenever another creature or planeswalker you control "
                "enters, you gain 1 life.\n"
                "{1}, {T}, Discard a card: Another target creature or "
                "planeswalker you control gains hexproof until end of turn."),
        verified="2026-09-20",
        rationale=(
            "A ONE-MANA LIFEGAIN-EVENT ENGINE, and the event is the axis this "
            "deck's payoffs count: Karlov's counters, Exemplar of Light, Voice "
            "of the Blessed and Vito all read the EVENT and not the amount. "
            "The deck runs 28 creatures, so this is Suture Priest's trigger "
            "one mana cheaper -- and Suture Priest ablates to +1.06 damage, "
            "the largest damage row in the list."),
        implement=("DONE 2026-09-20. One branch in `karlov.creature_entered` "
                   "beside Daxos, reading `others()` so the card's word "
                   "ANOTHER is honoured -- the clause five of this deck's six "
                   "enters-triggers ignored until 2026-09-05. FLOOR: the "
                   "hexproof activation is not modelled, because "
                   "single-target hexproof against an abstract pod answer is "
                   "`protection_cards` shaped and wiring it there would make "
                   "this a second Mother of Runes on a judgement rather than "
                   "a measurement. The planeswalker half is DEAD: this deck "
                   "holds none and this engine has no loyalty. Pinned by "
                   "tests/test_fra_karlov.py."),
        rejected=(
            'MEASURED 2026-09-21 and PROMOTED on 2026-09-25: the real-swap numb'
            'er is now a Candidate in MEASURED, with whether it still describes'
            ' the deck today. Closed rather than deleted so the verified oracle'
            ' text stays where it was written (§0z45).'
        ),
    ),
    Proposal(
        deck="karlov", card="Edgar, Ancient Bloodlord", cost="{W}{B}",
        identity="WB", type_line="Legendary Creature — Vampire Noble",
        oracle=("Whenever another creature or planeswalker you control dies, "
                "you gain 1 life.\n"
                "{2}, Sacrifice another creature or planeswalker: Put a "
                "+1/+1 counter on Edgar. He gains menace until end of turn."),
        verified="2026-09-20",
        rationale=(
            "TURNS THE POD'S WRATHS INTO A PILE OF LIFEGAIN EVENTS. This deck "
            "suffers real wipes (`wipes_suffered` is a counter for a reason) "
            "and every creature lost is currently a loss with no upside; with "
            "Edgar out, a four-creature wipe is four Karlov counters and four "
            "triggers for the payoffs above. Two mana for a 2/3 body."),
        implement=("DONE 2026-09-20. One branch at the top of "
                   "`KarlovGame.on_creature_death`, beside Enduring "
                   "Tenacity's. FLOOR: the sacrifice activation is not "
                   "modelled -- this engine has no sac-outlet policy and "
                   "menace is not blocked around here. NOTE ITS 'ANOTHER' IS "
                   "ENFORCED TWICE: `opponents.destroy` removes the permanent "
                   "BEFORE calling the hook, so `has()` is already false when "
                   "Edgar himself dies, and the name check is a second guard "
                   "on top of an ordering in shared code. The mutation in "
                   "tests/test_fra_karlov.py has to defeat both to model one "
                   "defect, and says so."),
        rejected=(
            'MEASURED 2026-09-21 and PROMOTED on 2026-09-25: the real-swap numb'
            'er is now a Candidate in MEASURED, with whether it still describes'
            ' the deck today. Closed rather than deleted so the verified oracle'
            ' text stays where it was written (§0z45).'
        ),
    ),
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
        deck='karlov', card='Scoured Barrens',
        cost='', identity='BW',
        type_line='Land',
        oracle='This land enters tapped.\nWhen this land enters, you gain 1 life.\n{T}: Add {W} or {B}.',
        verified='2026-10-06',
        rationale="Karlov's lifegain is counted in EVENTS (Karlov's counters, the drain loop); an ETB 'you gain 1 life' is one more event on a land drop, and karlov's duals are worth +0.0024 to +0.0038 over a Plains (§0z112).",
        implement='Fields only: `L("Scoured Barrens", "WB", tapped=True, lifegain=1)` -- karlov already fires a land\'s `lifegain` field as a lifegain event (Radiant Fountain, gain 2, identical to its twin in the land ablation). Every clause modelled.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='karlov', card='Kabira Crossroads',
        cost='', identity='W',
        type_line='Land',
        oracle='This land enters tapped.\nWhen this land enters, you gain 2 life.\n{T}: Add {W}.',
        verified='2026-10-06',
        rationale='As Scoured Barrens, gaining 2, on a mono-white land.',
        implement='Fields only: `L(..., "W", tapped=True, lifegain=2)`. Every clause modelled.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='karlov', card='Ancient Tomb',
        cost='', identity='',
        type_line='Land',
        oracle='{T}: Add {C}{C}. This land deals 2 damage to you.',
        verified='2026-10-06',
        rationale="Two mana from a land drop, in a deck whose top cards are six-drops (Bolas's Citadel, Felidar Sovereign); karlov gains enough life to pay 2 a tap.",
        implement="SHARED: `engine.available_mana` and `spend` must both read a land's mana_ability width (§0z4 -- said in both or it does nothing), and the 2 damage per tap is charged like a painland's. Every clause modelled; colourless only.",
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
]


# The three 2026-09-04 Karlov changes are COMMITTED as of v2, so they are
# in the deck list itself and no longer swap-in candidates. Bolas's
# Citadel (2026-09-12) is a candidate and NOT yet a deck member.
CATALOG = (karlov_v2, {
    # 2026-09-16 batch (§0z26), catalogued so a Change can name them.
    "Bloodthirsty Conqueror": karlov_v2.BLOODTHIRSTY_CONQUEROR,
    "Alhammarret's Archive": karlov_v2.ALHAMMARRETS_ARCHIVE,
    "Bolas's Citadel": karlov_v2.BOLASS_CITADEL,
    # REALITY FRACTURE, 2026-09-20 (preview text; releases 2026-10-02).
    "Liliana the Faultless": karlov_v2.LILIANA_THE_FAULTLESS,
    "Edgar, Ancient Bloodlord": karlov_v2.EDGAR_ANCIENT_BLOODLORD,
    # REALITY FRACTURE, 2026-09-22 -- the first card in this project that
    # uses the monarch (§0z39).
    "Ginger, Queen of Sweets": karlov_v2.GINGER_QUEEN_OF_SWEETS,
    # MYSTERY BOOSTER COMMANDER EDITION, 2026-09-29 (§0z74).
    "Selenia, the Cursed Heart": karlov_v2.SELENIA_THE_CURSED_HEART,
    "Pearl Collector": karlov_v2.PEARL_COLLECTOR,
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    "Scoured Barrens": karlov_v2.SCOURED_BARRENS,
    "Kabira Crossroads": karlov_v2.KABIRA_CROSSROADS,
    "Ancient Tomb": karlov_v2.ANCIENT_TOMB})
