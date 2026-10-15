"""lorehold's ledger entries and swap-in catalog.

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

from edhmc.decks import lorehold_v17
from edhmc.ledger.records import Change, Candidate, Simulated, Proposal


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
    # COMMITTED 2026-10-10 to edhmc/decks/lorehold_v17.py and
    # Lorehold_Commander_Deck_Final_v17.xlsx, each into its cut's EXACT list
    # position. Their MEASURED rows moved here on commit (the candidate rows:
    # Furygale +0.0556 +-0.0046, Profound Journey +0.0210 +-0.0031 at T20, over
    # a blank, §0z124). -Boros Charm +Immolating Gyre, staged the same day,
    # is NOT committed: the owner's call.
    Change(
        deck="lorehold", remove='Verge Rangers', add='Furygale Flocking',
        staged="2026-10-10",
        rationale="STAGED BY THE OWNER 2026-10-10, the first of three cuts named in order, paired with the batch's strongest card. Six 3/3 flying hasty attackers for {2} or nothing: the card's own reduction applies to the miracle cost (601.2f) and Lorehold's rummage fills the graveyard that pays it (§0z124). The cut was the owner's: a MODEL-EVALUATED creature whose row was +0.0021 +-0.0028 at T20, inside its bar.",
        evidence="REAL SWAP -Verge Rangers +Furygale Flocking, N=15,000 paired, seeds 5000.., the staged list (with -Ruby Medallion +Prisoner's Dilemma): +0.0287 +-0.0035 (significant) at T10 and +0.0455 +-0.0049 (significant) at T20. results/lorehold_big_spells_h2h_20261010.txt (diagnostics/run_lorehold_big_spells.py --h2h).",
        notes="A slight CEILING on the add: 'attack THAT opponent' is not modelled -- the six join the pod-wide split. THE THREE TOGETHER (§0p), the package staged 2026-10-10, against the same base: +0.0471 +-0.0046 at T10 and +0.0773 +-0.0064 at T20 (results/lorehold_big_spells_package_20261010.txt) -- additive at T10 (+0.0469 summed), somewhat below the sum at T20 (+0.0847): three cards competing for the same miracle windows. REBUILD: staging changes `build_pending`, so lorehold's cache stays SUSPECT until its table is rebuilt (§0z27) -- the rebuild already deferred for Prisoner's Dilemma covers this too. §0z124.",
    ),
    Change(
        deck="lorehold", remove='Lightning Greaves', add='Profound Journey',
        staged="2026-10-10",
        rationale="STAGED BY THE OWNER 2026-10-10, the second cut. Two reanimations for one card -- a miracle is cast from hand, so rebound applies -- and what comes back is the engine the pod destroyed: Arcane Bombardment, Library of Leng, Sunbird's Invocation, The Dawning Archaic (§0z124). The cut was the owner's: +0.0033 +-0.0025 at T20.",
        evidence="REAL SWAP -Lightning Greaves +Profound Journey, N=15,000 paired, seeds 5000.., the staged list (with -Ruby Medallion +Prisoner's Dilemma): +0.0147 +-0.0028 (significant) at T10 and +0.0225 +-0.0042 (significant) at T20. results/lorehold_big_spells_h2h_20261010.txt (diagnostics/run_lorehold_big_spells.py --h2h).",
        notes="THE CUT IS PROTECTION, which this model sees only in part: Greaves is a shroud source (`shroud_sources`), and the pod's removal is a roll against an abstract board (§4) -- the reason the owner kept Swiftfoot Boots in karlov. So the swap may be a CEILING. THE THREE TOGETHER (§0p), the package staged 2026-10-10, against the same base: +0.0471 +-0.0046 at T10 and +0.0773 +-0.0064 at T20 (results/lorehold_big_spells_package_20261010.txt) -- additive at T10 (+0.0469 summed), somewhat below the sum at T20 (+0.0847): three cards competing for the same miracle windows. REBUILD: staging changes `build_pending`, so lorehold's cache stays SUSPECT until its table is rebuilt (§0z27) -- the rebuild already deferred for Prisoner's Dilemma covers this too. §0z124.",
    ),
]


MEASURED: list[Candidate] = [
    Candidate(
        deck='lorehold',
        card='Chief Magistrate of Mercadia',
        measured='2026-09-29',
        win_rate='REAL SWAP -Lightning Greaves +Chief Magistrate of Mercadia, N=15,000 paired: -0.0009 +-0.0020 (inside its bar) at T10 and +0.0068 +-0.0035 (significant) at T20.',
        signal='win',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 0.11 crowns a game at T20 and 0.12 monarch draws -- the crown is lost almost at once on lorehold's thin board, so the token copies are rare (0.086).",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='The copy clause is capped at `magistrate_token_cap` (512), never reached here.',
        verdict='T20 only; inside its bar at T10.',
    ),
    Candidate(
        deck='lorehold',
        card='Stingcaster Mage',
        measured='2026-09-21',
        win_rate=('REAL SWAP -Lightning Greaves +Stingcaster Mage, N=15,000 paired: +0.'
            '0017 +-0.0017 at T10 (inside its bar) and +0.0107 +-0.0036 at T20 (s'
            'ignificant); damage T20 +0.78 +-0.18.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence='results/fra_batch2.txt (diagnostics/run_fra_batch2.py)',
        limits=('IT FIRES RARELY: 0.18 casts a game, 0.1775 of them exiled, so most o'
            'f this swap is the Greaves cut plus a 2/1 haste body rather than the'
            ' flashback. Measured on the §0z38-fixed flashback path. STALE -- NOT'
            " RESTATED. This deck's baseline has MOVED since the measurement (§0z"
            '42: decking now loses and the pilot holds a decking reserve, which m'
            'oved lorehold); check_unchanged_decks 246b148 vs 2026-09-25 reports '
            'it MOVED on 8 of 8 metrics. Re-measure before any head-to-head decis'
            'ion rests on it.'),
        verdict=('Long-horizon only, and the mechanism does not explain the win rate o'
            'n its own -- read it as a body-and-cut number, not a flashback numbe'
            'r.'),
    ),
    # QUEUED ITEM 0c, answered 2026-09-25 (§0z53).
    Candidate(
        deck='lorehold',
        card='Goldspan Dragon',
        measured='2026-09-25',
        win_rate=('REAL SWAPS, N=15,000 paired, on the staged list after §0z49/§0z50: '
            '-Blasphemous Act +Goldspan +0.0106 +-0.0020 at T10 and +0.0162 +-0.0044 at '
            'T20 (significant at both); -Lightning Greaves +Goldspan +0.0005 +-0.0014 / '
            '+0.0084 +-0.0034 (T20 only); Goldspan in Caldera Pyremaw\'s slot -0.0039 '
            '+-0.0012 / -0.0108 +-0.0027 (Caldera is better).'),
        signal='both',
        rationale=('Queued item 0c: its leave-one-out row was significant at all three '
            'horizons in 2026-09-06, and §0e says a standalone row is not a staging. '
            'These are the head-to-heads it asked for, against the two cuts that '
            'history named and against the card holding the five-drop slot.'),
        evidence='results/text_fixes.txt (diagnostics/run_text_fixes.py)',
        limits=('THE BETTER SWAP CUTS A PARTLY-MODELLED CARD. Blasphemous Act is a '
            'symmetric wipe: its cost to you is modelled faithfully, the benefit '
            '(the opponents\' boards) is an abstract creature count, so the model '
            'half-sees the card this swap removes -- §0z36 says that can err in '
            'either direction. Lorehold\'s baseline moved twice on 2026-09-25 '
            '(§0z48, §0z49) and these were measured after both -- but before '
            '§0z54/§0z55 moved it again by +0.08. RE-MEASURED 2026-09-26 on the '
            'rebuilt baseline (§0z63): -Blasphemous Act +Goldspan +0.0143 +-0.0026 '
            '/ +0.0119 +-0.0047 (still significant at both horizons, smaller at '
            'T20); -Lightning Greaves +Goldspan +0.0011 +-0.0018 / +0.0064 +-0.0037 '
            '(T20 only); in Caldera\'s slot -0.0030 / -0.0087 (Caldera still '
            'better). results/restage_20260926.txt.' ' RE-MEASURED AGAIN AFTER §0z62: -Blasphemous Act +Goldspan +0.0135 +-0.0025 / +0.0165 +-0.0045; -Lightning Greaves +Goldspan +0.0002 +-0.0018 / +0.0048 +-0.0036; in Caldera\'s slot -0.0029 / -0.0091. CURRENT. results/restage_20260926.txt.'),
        verdict=('Not a replacement for Caldera. A real candidate for Blasphemous '
            'Act\'s slot, significant at both horizons, with the cut\'s blind half '
            'said out loud. STAGED BY THE OWNER 2026-09-26 (§0z69); WITHDRAWN BY '
            'THE OWNER 2026-10-05 after §0z104 put it inside its bar at T20 '
            '(§0z105): see WITHDRAWN. Blasphemous Act stays.'),
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
        deck='lorehold',
        card='Ancient Tomb',
        measured="2026-10-06",
        win_rate='+0.0083 +-0.0025 at T10, +0.0027 +-0.0035 at T20 against a Mountain',
        signal='dmg',
        rationale='{C}{C} from a land, for 2 damage a tap.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Mountain. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: life_lost_to_own_cards +1.015, tomb_damage +1.006. §0z113.',
        limits='Every clause modelled; 1.0 damage a game.',
        verdict='Significant at T10 (+0.0083) and inside at T20: the fast mana matters early and the life is paid back later. A T10-only signal; not enough for a swap on its own. OWNER DEFERRED 2026-10-06: a valid card, but outside the price range of the casual table the owner plays at -- a judgement about the table, not about the number.',
    ),
    Candidate(
        deck='lorehold',
        card='Command Beacon',
        measured="2026-10-06",
        win_rate='+0.0003 +-0.0013 at T10, -0.0006 +-0.0023 at T20 against a Mountain',
        signal='--',
        rationale='Returns the commander to hand, so its next cast pays no tax.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Mountain. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: beacon_tax_saved +0.430, beacon_used +0.101, life_lost_to_own_cards +0.004. §0z113.',
        limits='Every clause modelled. A POLICY: sacrificed at tax >= `beacon_min_tax` (4), only when the commander can be cast at once; 0.10 uses a game. At beacon_min_tax=2: 0.16 uses, -0.0018 +-0.0028 at T20 -- no better.',
        verdict='A blank: the commander dies twice in too few games for the tax to matter.',
    ),
    Candidate(
        deck="lorehold", card='Searing Wind', measured="2026-10-09",
        win_rate='+0.0054 +-0.0016 at T20, +0.0025 +-0.0009 at T10',
        signal="both",
        rationale="Ten damage to one opponent for {2}, at instant speed in the opponents' upkeep windows.",
        evidence="diagnostics/run_lorehold_big_spells.py, results/lorehold_big_spells_20261009.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pinnacle Monk's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates lorehold4 --n=15000` (results/candidates_lorehold4.txt), reproduced to the last digit. §0z124. searing_wind_resolved +0.21 a game, spell_damage +1.56 at T20; P(cast) 0.167.",
        limits="Every modelled clause; 'any target''s creature half is §4 and unused.",
        verdict="Significant at both horizons and small: ten damage once a game in a deck that already wins on spells. The owner's 'fair' -- a real card, not a staple here.",
    ),
    Candidate(
        deck="lorehold", card='Explosive Welcome', measured="2026-10-09",
        win_rate='+0.0038 +-0.0016 at T20, +0.0018 +-0.0008 at T10',
        signal="both",
        rationale='Eight damage split over two opponents and {R}{R}{R}, for {2}.',
        evidence="diagnostics/run_lorehold_big_spells.py, results/lorehold_big_spells_20261009.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pinnacle Monk's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates lorehold4 --n=15000` (results/candidates_lorehold4.txt), reproduced to the last digit. §0z124. welcome_resolved +0.21, welcome_mana_added +0.16 (the red mana survives only a main-phase resolution, 500.4) at T20. AGAINST SEARING WIND IN THE SAME SLOT, paired: -0.0017 +-0.0018 at T20, -0.0009 +-0.0010 at T10 -- inside the bar; damage -0.14 +-0.06 (significant).",
        limits='Every modelled clause. With one opponent left the 3 has no player to hit (§4).',
        verdict="The owner's 'weaker Searing Wind' is right by MECHANISM (less damage, significantly) and unresolved by win rate: the paired difference is inside its bar at both horizons.",
    ),
    Candidate(
        deck="lorehold", card="Gideon's Phalanx", measured="2026-10-09",
        win_rate='+0.0106 +-0.0024 at T20, +0.0033 +-0.0012 at T10',
        signal="both",
        rationale='Four 2/2s for {2} at instant speed, in a creature-sparse list.',
        evidence="diagnostics/run_lorehold_big_spells.py, results/lorehold_big_spells_20261009.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pinnacle Monk's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates lorehold4 --n=15000` (results/candidates_lorehold4.txt), reproduced to the last digit. §0z124. phalanx_knights +0.84 a game, combat_damage +1.65 at T20; spell mastery would have applied on 0.20 casts a game. AGAINST FURYGALE FLOCKING IN THE SAME SLOT, paired: -0.0423 +-0.0044 at T20, -0.0295 +-0.0032 at T10.",
        limits="A FLOOR: spell mastery's indestructible is not modelled (it matters only in response to a wrath, which no miracle window overlaps). Vigilance is inert in this pod.",
        verdict="Significant at both horizons, and the owner's 'weaker than Flocking' is measured: four times smaller, paired, outside every bar.",
    ),
    Candidate(
        deck="lorehold", card="Raphael's Technique", measured="2026-10-09",
        win_rate='+0.0191 +-0.0035 at T20, +0.0089 +-0.0024 at T10',
        signal="both",
        rationale='A second wheel, at instant speed.',
        evidence="diagnostics/run_lorehold_big_spells.py, results/lorehold_big_spells_20261009.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pinnacle Monk's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates lorehold4 --n=15000` (results/candidates_lorehold4.txt), reproduced to the last digit. §0z124. wheel_casts +0.22, cards_drawn +2.07, mv_cheated +1.30 at T20. As a REAL SWAP for Reforge the Soul (SIMULATED): -0.0031 +-0.0022 at T20, -0.0026 +-0.0014 at T10, both significant.",
        limits="PARTLY: Sneak is not modelled, and the pilot always wheels ('may'). The opponents' half is §4.",
        verdict="A good card over a blank and a worse one than Reforge the Soul, measured: the owner's call holds. Reforge's own miracle {1}{R} is a cast Lorehold's {2} does not need to be on the battlefield for.",
    ),
    Candidate(
        deck="lorehold", card='Immolating Gyre', measured="2026-10-09",
        win_rate='+0.0189 +-0.0026 at T20, +0.0045 +-0.0013 at T10 (`gyre_full_x` 6)',
        signal="both",
        rationale="A one-sided sweeper whose X is the graveyard Lorehold's rummage fills.",
        evidence="diagnostics/run_lorehold_big_spells.py, results/lorehold_big_spells_20261009.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pinnacle Monk's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates lorehold4 --n=15000` (results/candidates_lorehold4.txt), reproduced to the last digit. §0z124. gyre_resolved +0.18 a game, X averaging 8 at resolution, 1.17 pod creatures killed a game, combat_damage +1.20 at T20. THE KNOB: gyre_full_x 3 -> +0.0218 +-0.0027, 12 -> +0.0131 +-0.0023 at T20; significant at every setting.",
        limits="THE KNOB IS A JUDGEMENT: the pod's creatures have no toughness (§4), so X kills min(1, X / gyre_full_x) of each board. Planeswalkers are §4.",
        verdict="The owner asked how strong it is: significant at both horizons and at every setting of the knob that prices it, with X large enough (about 8) that it is usually a full one-sided wipe. A long-horizon card -- most of its value is at T20, when the pod's boards have grown. STAGED 2026-10-10 against Boros Charm (CHANGES); the other head-to-heads are in SIMULATED.",
    ),
]


CHANGES: list[Change] = [
    Change(
        deck="lorehold", remove='Boros Charm', add='Immolating Gyre',
        staged="2026-10-10",
        rationale="STAGED BY THE OWNER 2026-10-10, the third cut. A one-sided sweeper whose X is the graveyard Lorehold fills, usually a full wipe of the pod's boards (§0z124). The cut was the owner's: +0.0019 +-0.0016 at T20.",
        evidence="REAL SWAP -Boros Charm +Immolating Gyre, N=15,000 paired, seeds 5000.., the staged list (with -Ruby Medallion +Prisoner's Dilemma): +0.0035 +-0.0021 (significant) at T10 and +0.0167 +-0.0035 (significant) at T20. results/lorehold_big_spells_h2h_20261010.txt (diagnostics/run_lorehold_big_spells.py --h2h).",
        notes="TWO CAVEATS ON THE CUT, both making the swap a CEILING: Boros Charm's damage mode is spread as 4/3 to each opponent instead of 4 to one (a known engine defect, queued separately), so its row is understated; and its indestructible mode is a protection spell (`PROTECTION`), which the pod's abstract removal sees only in part. THE ADD RESTS ON A KNOB: `gyre_full_x` (6), a judgement about the pod's toughness -- over a blank the row held from +0.0131 to +0.0218 across 3..12. THE THREE TOGETHER (§0p), the package staged 2026-10-10, against the same base: +0.0471 +-0.0046 at T10 and +0.0773 +-0.0064 at T20 (results/lorehold_big_spells_package_20261010.txt) -- additive at T10 (+0.0469 summed), somewhat below the sum at T20 (+0.0847): three cards competing for the same miracle windows. REBUILD: staging changes `build_pending`, so lorehold's cache stays SUSPECT until its table is rebuilt (§0z27) -- the rebuild already deferred for Prisoner's Dilemma covers this too. §0z124.",
        reverified="RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0049 +-0.0027 at T10, +0.0191 +-0.0037 at T20. Significant at both; the staging stands. The pod alone moved it +0.0053 +-0.0047 at T20 (POD_PRE_V4 at the same commit: +0.0137): an answer, which POD_V4 lets hit route pieces and kill bodies. `gyre_full_x` (6) still prices it: under `pod_bodies` it is the top of the bodies' toughness range. results/restage_lorehold_20261015.txt (§0z142).",
    ),
    Change(
        deck="lorehold", remove="Ruby Medallion", add="Prisoner's Dilemma",
        staged="2026-10-09",
        rationale=(
            "STAGED BY THE OWNER 2026-10-09. A miracle for {2} off Lorehold that "
            "deals 8 to each opponent when they play the dominant strategy, and "
            "casts itself again from the graveyard for {5}{R}{R} (§0z122). The "
            "cut is a MODEL-EVALUATED card whose text is modelled faithfully "
            "and which seldom matters here: Ruby is out for 2.0 miracle windows "
            "a game and makes 0.022 miracles a game possible that full price "
            "would not (§0z123)."),
        evidence=(
            "REAL SWAP -Ruby Medallion +Prisoner's Dilemma, N=15,000 paired, seeds 5000.., "
            "the staged list with native flashback on: 'snitch' +0.0125 +-0.0028 "
            "(significant) at T10 and +0.0295 +-0.0044 (significant) at T20; "
            "'silence' +0.0045 +-0.0025 (significant) at T10 and +0.0103 +-0.0040 "
            "(significant) at T20. results/prisoners_dilemma_ruby.txt "
            "(diagnostics/run_prisoners_dilemma.py --cuts=\"Ruby Medallion\")."),
        notes=(
            "THE KNOB IS THE CARD: `dilemma_choice` ('snitch' default, the only "
            "equilibrium; 'silence' the floor). REBUILD DEFERRED BY THE OWNER: "
            "staging changes `build_pending`, so lorehold's cache is SUSPECT "
            "until its table is rebuilt -- `check_docs` fails on it knowingly "
            "until then, and nothing but a rebuild clears it (§0z27). The "
            "other head-to-heads, against Soulfire Eruption (+0.0262 at T20) "
            "and Enlightened Tutor (+0.0332, a ceiling since §0z123), stay in "
            "SIMULATED. Not committed: the deck module and the .xlsx are "
            "untouched."),
        reverified=(
            "RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, "
            "N=15,000 paired, python 3.13, 'snitch': +0.0158 +-0.0034 at T10, "
            "+0.0201 +-0.0044 at T20. Significant at both; the staging stands. "
            "Below the staged +0.0295 at T20 by more than a bar, but neither "
            "half alone is: the pod moved it -0.0051 +-0.0056 (POD_PRE_V4 at "
            "the same commit: +0.0252), and the list it is measured in gained "
            "Furygale Flocking, Profound Journey and Immolating Gyre since. "
            "results/restage_lorehold_20261015.txt (§0z142)."),
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
        reverified='RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0173 +-0.0031 at T10, +0.0261 +-0.0040 at T20. Significant at both; the staging stands. The pod alone moved it -0.0053 +-0.0049 at T20 (the same arms on POD_PRE_V4 at the same commit: +0.0314) -- a slow engine piece, as item 26 predicted. results/restage_lorehold_20261015.txt (§0z142). ' + 'RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0104 +-0.0023 at T10, +0.0246 +-0.0037 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + 'RE-MEASURED 2026-10-05 after §0z104 (the wipe gate asked at every optional cast site), in context, N=15,000 paired: +0.0083 +-0.0025 at T10, +0.0269 +-0.0038 at T20. results/restage_20261005.txt. ' + (
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
            "results/lorehold_pair_postsplit.txt. "
            "RE-VERIFIED 2026-09-25 AFTER §0z48, which matters to THIS card "
            "specifically: Artist's Talent's level 3 adds 2 to every Pyremaw "
            "hit. Same factorial, N=30,000, same seeds, run on BOTH sides of "
            "the change: Caldera GIVEN Sunbird's +0.0240 +-0.0027 at HEAD "
            "6a0e786 and +0.0217 +-0.0027 after -- inside its bar, and still "
            "the largest cell. Penance ablates to -0.0062 +-0.0034 at T20. "
            "The decision stands. results/lorehold_pair_artist.txt. "
            "AND AGAIN AFTER §0z49 (Storm Herd's X, which moved lorehold's "
            "baseline -0.0271): Caldera GIVEN Sunbird's +0.0231 +-0.0026. "
            "Radiant Scrollwielder in this slot WITH its lifelink (§0z50) is "
            "-0.0085 +-0.0034 against Caldera, so the five-drop decision "
            "stands with that clause in. results/lorehold_pair_stormherd.txt, "
            "results/text_fixes.txt. AND AGAIN AFTER §0z54/§0z55 (one free-cast "
            "path; Approach's second cast -- lorehold's baseline +0.08): "
            "Caldera GIVEN Sunbird's +0.0249 +-0.0028 at T20, +0.0056 "
            "+-0.0015 at T10. Larger, and the decision stands. "
            "results/lorehold_pair_approach.txt."
            " AND AGAIN AFTER §0z62 (the pod turns on you once Approach has resolved): Caldera GIVEN Sunbird's +0.0053 +-0.0015 at T10, +0.0226 +-0.0027 at T20. The decision stands. results/lorehold_pair_knownwin.txt."
        + ' ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0077 +-0.0024 at T10, +0.0239 +-0.0038 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81)."),
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
        reverified='RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0130 +-0.0035 at T10, +0.0222 +-0.0045 at T20. Significant at both; the staging stands. The pod alone moved it -0.0105 +-0.0055 at T20, the largest of the four (POD_PRE_V4 at the same commit: +0.0327) -- a slow engine piece, as item 26 predicted. results/restage_lorehold_20261015.txt (§0z142). ' + 'RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0073 +-0.0025 at T10, +0.0231 +-0.0041 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + 'RE-MEASURED 2026-10-05 after §0z104 (the wipe gate asked at every optional cast site), in context, N=15,000 paired: +0.0051 +-0.0027 at T10, +0.0233 +-0.0042 at T20. results/restage_20261005.txt. ' + (
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
            "results/lorehold_pair_postsplit.txt. "
            "RE-VERIFIED 2026-09-25 AFTER §0z48 (Artist's Talent's levels), "
            "same factorial on both sides of the change: Sunbird's GIVEN "
            "Caldera +0.0161 +-0.0030 at HEAD 6a0e786 and +0.0150 +-0.0031 "
            "after, inside its bar; significant, and the decision stands. "
            "BUT SUNBIRD'S ALONE HAS DROPPED AGAIN, and not because of "
            "§0z48: +0.0152 on 2026-09-09, +0.0109 +-0.0029 at HEAD before "
            "the change, +0.0102 after. Roughly one bar, between two "
            "unpaired engines, so marginal -- and unattributed (queued item "
            "0b-i). Scroll Rack ablates to -0.0075 +-0.0034 at T20. "
            "results/lorehold_pair_artist.txt. AND AGAIN AFTER §0z49 (Storm "
            "Herd's X): Sunbird's GIVEN Caldera +0.0164 +-0.0029, alone "
            "+0.0118 +-0.0028. results/lorehold_pair_stormherd.txt. AND AGAIN "
            "AFTER §0z54/§0z55: GIVEN Caldera +0.0170 +-0.0032 at T20 and "
            "+0.0026 +-0.0017 at T10 -- significant at T10 for the first time. "
            "The decay queued as 0b-i is closed by §0z59: no single cause, "
            "net -0.0034 +-0.0035 since 2026-09-09. "
            "results/lorehold_pair_approach.txt."
            " AND AGAIN AFTER §0z62: Sunbird's GIVEN Caldera +0.0023 +-0.0017 at T10, +0.0153 +-0.0031 at T20. The decision stands. results/lorehold_pair_knownwin.txt."
        + ' ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0031 +-0.0026 at T10, +0.0173 +-0.0043 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81)."),
    ),
]


WITHDRAWN: list[Change] = [
    Change(
        deck="lorehold", remove="Blasphemous Act", add="Goldspan Dragon",
        staged="2026-09-26",
        rationale=(
            "Queued item 0c. Goldspan beats both cuts history named and loses "
            "only to Caldera Pyremaw for Caldera's own slot; the Act is the "
            "better of the two cuts, significant at both horizons in every "
            "measurement since §0z53. The owner staged it."),
        evidence=(
            "RE-MEASURED 2026-09-26 on the final §0z67 engine (commander "
            "damage, the aimed commander, the aware defender, known_win_focus "
            "0.8), N=15,000 paired, in context: +0.0129 +-0.0026 at T10, "
            "+0.0137 +-0.0046 at T20. On the engine without the aim: +0.0132 / "
            "+0.0137. results/aim_vault_swaps_20260926.txt "
            "(diagnostics/run_aim_vault_swaps.py). History: §0z53 +0.0162 at "
            "T20, §0z63 +0.0119, after §0z62 +0.0165."),
        cut_unmeasured=(
            "Blasphemous Act is PARTLY MODELLED -- a symmetric wipe whose cost "
            "to you is faithful and whose BENEFIT (the opponents' boards) is "
            "an abstract creature count. The head-to-head is therefore "
            "uncertain in the Act's favour by whatever the real wipe does "
            "that the count does not. Staged anyway on the owner's judgement "
            "that the Act does not do more at their table than the model "
            "credits; said out loud here, as §0z31 requires."),
        reverified="RE-MEASURED 2026-10-05 after §0z104 (the wipe gate asked at every optional cast site), in context, N=15,000 paired: +0.0105 +-0.0026 at T10 and +0.0015 +-0.0042 at T20 -- INSIDE ITS BAR AT T20. Attributed: the same run with wipe_gate_all_casts=False gives +0.0130 / +0.0131, so the gate alone moved this swap by about 0.012 at T20 -- Blasphemous Act was over-firing like the other wipes, and cutting it looked better than it is. THE STAGING RESTS ON NUMBERS THE FIX HAS OVERTAKEN; it is the owner's to keep or withdraw. results/restage_20261005.txt. " + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0129 +-0.0026 at T10, +0.0134 +-0.0046 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81).",
        withdrawn=(
            "WITHDRAWN BY THE OWNER 2026-10-05 (§0z105): Blasphemous Act stays. "
            "Not refuted -- the swap is still +0.0105 +-0.0026 at T10 -- but "
            "the T20 number the staging rested on (+0.0137 at staging, +0.0134 "
            "at §0z81) is +0.0015 +-0.0042 once the wipe gate is asked at every "
            "optional cast site (§0z104), inside its bar. About 0.012 of the old "
            "edge was the Act misfiring by miracle and free cast on boards the "
            "pilot was winning, so cutting it looked better than it was. The "
            "owner keeps the sweeper. WHAT RE-STAGING WOULD HAVE TO ANSWER: a "
            "T20 head-to-head significant on the gated engine, and the Act's "
            "unmodelled half (the real opposing boards) said out loud again."),
    ),
]


SIMULATED: list[Simulated] = [
    Simulated(
        deck='lorehold', remove='Lightning Greaves', add='Chief Magistrate of Mercadia',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Lightning Greaves +Chief Magistrate of Mercadia, N=15,000 paired: -0.0009 +-0.0020 (inside its bar) at T10 and +0.0068 +-0.0035 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: -0.0010 +-0.0020 at T10 and +0.0070 +-0.0035 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s. '
               'RE-MEASURED 2026-10-01 AFTER §0z97 (losing the crown no longer ends the pod\'s chip round, so the games you were monarch in are charged in full), seeds 1234.., both engines on the same seeds: +0.0001 +-0.0021 at T10 and +0.0064 +-0.0036 * at T20, against +0.0003 / +0.0077 on the old loop -- the fix itself moved the swap -0.0013 +-0.0006 at T20. Still significant at T20 only (results/monarch_restage_20261001.txt).'),
    ),
    Simulated(
        deck='lorehold', remove='Lightning Greaves', add='Stingcaster Mage',
        measured='2026-09-21', source='results/fra_batch2.txt',
        result=('REAL SWAP -Lightning Greaves +Stingcaster Mage, N=15,000 paired: +0.0017 +-0.0017 at T10 (inside its bar) and +0.0107 +-0.0036 at T20 (significant); damage T20 +0.78 +-0.18.'),
    ),
    Simulated(
        deck='lorehold', remove='Lightning Greaves', add='Goldspan Dragon',
        measured='2026-09-26', source='results/restage_20260926.txt',
        result=('+0.0002 +-0.0018 at T10 and +0.0048 +-0.0036 at T20 (T20 '
                'only), re-measured after §0z62.'),
        notes=('Goldspan was staged against Blasphemous Act instead (§0z69) '
               'and WITHDRAWN 2026-10-05 (§0z105); '
               'in Caldera Pyremaw\'s slot it loses, -0.0091 at T20.'),
    ),
    Simulated(
        deck='lorehold', remove='Soulfire Eruption', add="Prisoner's Dilemma",
        measured='2026-10-09', source='results/prisoners_dilemma.txt',
        result=("REAL SWAP -Soulfire Eruption +Prisoner's Dilemma, N=15,000 paired, seeds 5000..: 'snitch' +0.0117 +-0.0026 (significant) at T10 and +0.0262 +-0.0041 (significant) at T20; 'silence' +0.0039 +-0.0023 (significant) at T10 and +0.0092 +-0.0037 (significant) at T20."),
        notes=("The like-for-like cut: a red damage sorcery (+0.0041 +-0.0028 in the table, MODEL-EVALUATED). Both legs on the staged list with native flashback on (Faithless Looting's included). The knob is `dilemma_choice`; §0z122."),
    ),
    Simulated(
        deck='lorehold', remove='Enlightened Tutor', add="Prisoner's Dilemma",
        measured='2026-10-09', source='results/prisoners_dilemma.txt',
        result=("REAL SWAP -Enlightened Tutor +Prisoner's Dilemma, N=15,000 paired, seeds 5000..: 'snitch' +0.0155 +-0.0029 (significant) at T10 and +0.0332 +-0.0045 (significant) at T20; 'silence' +0.0082 +-0.0027 (significant) at T10 and +0.0157 +-0.0043 (significant) at T20."),
        notes=("The lowest win-rate MODEL-EVALUATED row when measured (-0.0025 +-0.0034, signal dmg) -- and PARTLY MODELLED since 2026-10-09 by the owner's call (§0z123): its table-facing choice is not modelled, so this swap is a CEILING. Both legs on the staged list with native flashback on (Faithless Looting's included). The knob is `dilemma_choice`; §0z122."),
    ),    Simulated(
        deck='lorehold', remove='Reforge the Soul', add="Raphael's Technique",
        measured='2026-10-09', source='results/lorehold_big_spells_20261009.txt',
        result=("REAL SWAP -Reforge the Soul +Raphael's Technique, N=15,000 paired, seeds 80000..: -0.0026 +-0.0014 (significant) at T10 and -0.0031 +-0.0022 (significant) at T20."),
        notes=("The owner's comparison ('a weaker Reforge the Soul'), measured: the same wheel, and Reforge has its own miracle {1}{R} that needs no Lorehold on the battlefield. Raphael's Sneak is not modelled (PARTLY). A comparison, not a proposal -- nobody suggested cutting Reforge. §0z124."),
    ),    Simulated(
        deck='lorehold', remove='Verge Rangers', add='Profound Journey',
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result='REAL SWAP -Verge Rangers +Profound Journey, N=15,000 paired, seeds 5000..: +0.0123 +-0.0030 (significant) at T10 and +0.0155 +-0.0043 (significant) at T20.',
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Verge Rangers', add="Raphael's Technique",
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result="REAL SWAP -Verge Rangers +Raphael's Technique, N=15,000 paired, seeds 5000..: +0.0050 +-0.0030 (significant) at T10 and +0.0116 +-0.0044 (significant) at T20.",
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Verge Rangers', add='Immolating Gyre',
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result='REAL SWAP -Verge Rangers +Immolating Gyre, N=15,000 paired, seeds 5000..: +0.0027 +-0.0025 (significant) at T10 and +0.0129 +-0.0041 (significant) at T20.',
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Lightning Greaves', add='Furygale Flocking',
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result='REAL SWAP -Lightning Greaves +Furygale Flocking, N=15,000 paired, seeds 5000..: +0.0303 +-0.0033 (significant) at T10 and +0.0493 +-0.0049 (significant) at T20.',
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Lightning Greaves', add="Raphael's Technique",
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result="REAL SWAP -Lightning Greaves +Raphael's Technique, N=15,000 paired, seeds 5000..: +0.0087 +-0.0028 (significant) at T10 and +0.0190 +-0.0044 (significant) at T20.",
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Lightning Greaves', add='Immolating Gyre',
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result='REAL SWAP -Lightning Greaves +Immolating Gyre, N=15,000 paired, seeds 5000..: +0.0029 +-0.0023 (significant) at T10 and +0.0149 +-0.0039 (significant) at T20.',
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Boros Charm', add='Furygale Flocking',
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result='REAL SWAP -Boros Charm +Furygale Flocking, N=15,000 paired, seeds 5000..: +0.0291 +-0.0033 (significant) at T10 and +0.0459 +-0.0047 (significant) at T20.',
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Boros Charm', add='Profound Journey',
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result='REAL SWAP -Boros Charm +Profound Journey, N=15,000 paired, seeds 5000..: +0.0152 +-0.0027 (significant) at T10 and +0.0224 +-0.0039 (significant) at T20.',
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
    Simulated(
        deck='lorehold', remove='Boros Charm', add="Raphael's Technique",
        measured='2026-10-10', source='results/lorehold_big_spells_h2h_20261010.txt',
        result="REAL SWAP -Boros Charm +Raphael's Technique, N=15,000 paired, seeds 5000..: +0.0091 +-0.0027 (significant) at T10 and +0.0194 +-0.0041 (significant) at T20.",
        notes=("One of the twelve pairings of the owner's three cuts with the four contenders kept after §0z124; the owner staged -Verge Rangers +Furygale Flocking, -Lightning Greaves +Profound Journey and -Boros Charm +Immolating Gyre (CHANGES). Measured on the staged list before those three were staged. §0z124."),
    ),
]


PROPOSED: list[Proposal] = [
    Proposal(
        deck='lorehold', card='Chief Magistrate of Mercadia', cost='{4}{R}{W}',
        identity='WR', type_line='Legendary Creature — Human Noble',
        oracle="When Chief Magistrate of Mercadia enters, you become the monarch.\nAt the beginning of your upkeep, create a 2/1 red Goblin creature token with haste. Then if you're the monarch, for each creature token you control, create a token that's a copy of it.",
        verified="2026-09-29",
        rationale="THE MONARCH (§0z39) and a hasty Goblin every upkeep, and while the crown is held the upkeep DOUBLES every creature token -- Storm Herd's Pegasi, Monastery Mentor's Monks, Emeria's Call's Angels.",
        implement="DONE 2026-09-29. ETB `opponents.become_monarch`; `lorehold.magistrate_upkeep` makes the Goblin then copies each creature token (copiable values only: a Goblin copy has haste, a Monk copy is still a 'Monk token' for the Mentor's prowess), bounded by `magistrate_token_cap` (512), a guard on the simulator rather than a claim about the card. SMOKE: the crown is taken back almost at once -- 0.127 monarch draws per 0.12 crowns gained -- because lorehold's board is thin and the pod's combat takes it (§0z39's `monarch_attack_floor`). Classify SCRIPTED at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Lightning Greaves is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
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
        deck='lorehold', card='Ancient Tomb',
        cost='', identity='',
        type_line='Land',
        oracle='{T}: Add {C}{C}. This land deals 2 damage to you.',
        verified='2026-10-06',
        rationale="Lorehold's top cards are expensive -- Apex of Power ten, Approach of the Second Sun seven -- and its duals are worth nothing over a Mountain (§0z112): mana, not colours, is what it lacks.",
        implement="The shared Ancient Tomb implementation (see karlov's proposal).",
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card='Command Beacon',
        cost='', identity='',
        type_line='Land',
        oracle='{T}: Add {C}.\n{T}, Sacrifice this land: Put your commander into your hand from the command zone.',
        verified='2026-10-06',
        rationale="Lorehold's commander IS its engine (the miracle discount), and each recast after removal costs two more; the Beacon returns it to hand with no tax.",
        implement="New: in lorehold's main phase, when the commander is in the command zone and its tax is at least the Beacon's opportunity cost (a knob), sacrifice the Beacon and put the commander into hand. Taps for {C} otherwise.",
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card="Prisoner's Dilemma",
        cost='{3}{R}{R}', identity='R',
        type_line='Sorcery',
        oracle="Each opponent secretly chooses silence or snitch, then the choices are revealed. If each opponent chose silence, Prisoner's Dilemma deals 4 damage to each of them. If each opponent chose snitch, Prisoner's Dilemma deals 8 damage to each of them. Otherwise, Prisoner's Dilemma deals 12 damage to each opponent who chose silence.\nFlashback {5}{R}{R}",
        verified='2026-10-09',
        rationale=("The owner's proposal (2026-10-09). A sorcery is a miracle for {2} off Lorehold, and a discarded one is not lost: "
                   "the rummage feeds the graveyard and flashback casts it from there. Snitch strictly dominates for every opponent "
                   "(0 < 4 when the others stay silent, 8 < 12 when they snitch), so the equilibrium is 8 to each opponent -- 24 "
                   "damage to the table, against Soulfire Eruption's single-target +0.0041 row."),
        implement=("Every clause is modelled. The CHOICE is the opponents', and it is a knob, `dilemma_choice`: 'snitch' (each "
                   "plays the dominant strategy: 8 each) or 'silence' (the table colludes: 4 each, the floor). A mixed reveal (12 to "
                   "each silent player) is not a setting. Damage through `deal_pod_damage`, one hit per opponent (Artist's Talent, "
                   "Scrollwielder's lifelink). FLASHBACK IS NEW TO THIS ENGINE: a native flashback cost, read from Scryfall by "
                   "`tag_flying` into `_evasion.FLASHBACK` rather than typed, cast from the graveyard in the main phase and exiled "
                   "(702.34a)."),
        triage='LIVE',
        prepared='tests/test_prisoners_dilemma.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number, and SIMULATED the two head-to-heads (§0z122). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    # THE OWNER'S SECOND BATCH, 2026-10-09: high-mana-value Boros instants and
    # sorceries, found by a Scryfall search (`(t:instant or t:sorcery) id<=rw
    # mv>=6 f:commander`) and picked by the owner from a shortlist. Lorehold
    # gives each a miracle cost of {2}, so the printed cost is mostly the
    # hardcast fallback and the effect is what is being bought.
    Proposal(
        deck='lorehold', card='Furygale Flocking',
        cost='{8}{R}{R}', identity='R',
        type_line='Sorcery',
        oracle='This spell costs {1} less to cast for each instant and sorcery card in your graveyard.\nFor each opponent, create two 3/3 blue and red Elemental creature tokens with flying that attack that opponent this turn if able. They gain haste until end of turn.',
        verified='2026-10-09',
        rationale=("The owner's pick ('excellent'). The cost reduction applies to an alternative cost (601.2f), so with two "
                   "instants or sorceries in the graveyard -- Lorehold's rummage puts one there every opponent's upkeep -- "
                   "the miracle {2} is free, and the card is six 3/3 flying attackers with haste in a creature-sparse list."),
        implement=("MODELLED: the reduction, in ONE function read by both `reduce_cost` (hardcast) and `miracle_reduction` "
                   "(the miracle, and so every miracle decision); two tokens per LIVING opponent, 3/3 flying (from this card's "
                   "text -- `FLYING_TOKENS` is keyed by subtype and azusa's Elementals do not fly), unsick on the turn they are "
                   "made. NOT MODELLED: 'attack THAT opponent' -- the tokens join the one attack `combat_damage` splits across "
                   "the pod, so each pair is not pinned to its own defender. Made on an opponent's upkeep they cannot attack "
                   "that turn, which is the rules, and attack on yours."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card='Searing Wind',
        cost='{8}{R}', identity='R',
        type_line='Instant',
        oracle='Searing Wind deals 10 damage to any target.',
        verified='2026-10-09',
        rationale=("The owner: 'fair'. Ten damage for {2} at instant speed, in any of the three windows on opponents' "
                   "upkeeps -- reach for a deck whose damage is mostly spells."),
        implement=("MODELLED: 10 damage to ONE opponent, the one closest to dying (`OPP.damage_single`), one hit "
                   "(Artist's Talent's +2, Scrollwielder's lifelink). 'Any target' also allows a creature or planeswalker, "
                   "which the pod does not have as objects (§4) -- unused, a floor of no size worth naming."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card='Explosive Welcome',
        cost='{7}{R}', identity='R',
        type_line='Instant',
        oracle='Explosive Welcome deals 5 damage to any target and 3 damage to any other target. Add {R}{R}{R}.',
        verified='2026-10-09',
        rationale=("The owner: 'a weaker Searing Wind'. Measured beside it so the gap is a number: eight damage split two "
                   "ways against ten to one player, and three red mana."),
        implement=("MODELLED: 5 and 3 to two DIFFERENT opponents, the two closest to dying, the 3 on the lower when 3 kills "
                   "it; with one opponent left the 3 has no player to hit (a creature, §4). The {R}{R}{R} empties between "
                   "steps (500.4), so it is added only when the spell resolves in a MAIN PHASE -- a hardcast or a free cast "
                   "there -- and is lost from a miracle in the draw step or an opponent's upkeep, which is almost always."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card="Gideon's Phalanx",
        cost='{5}{W}{W}', identity='W',
        type_line='Instant',
        oracle='Create four 2/2 white Knight creature tokens with vigilance.\nSpell mastery — If there are two or more instant and/or sorcery cards in your graveyard, creatures you control gain indestructible until end of turn.',
        verified='2026-10-09',
        rationale=("The owner: 'weaker than Flocking usually, but might help fix the deck being creature-sparse'. Eight "
                   "power for {2} at instant speed, so the Knights made on an opponent's upkeep attack on your turn."),
        implement=("MODELLED: four 2/2 Knight tokens. INERT HERE, said rather than built: vigilance (nothing in this pod "
                   "reads whether your creatures are tapped). NOT MODELLED: spell mastery's indestructible -- it matters "
                   "only cast in response to a wrath, and the pod's removal is a round at the end of your turn that no "
                   "miracle window overlaps; using it as a protection spell needs a PROTECTION entry that pays seven mana, "
                   "which `try_protect` cannot express. PARTLY MODELLED: the row is a floor."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card="Raphael's Technique",
        cost='{4}{R}{R}', identity='R',
        type_line='Instant',
        oracle='Sneak {2}{R} (You may cast this spell for {2}{R} if you also return an unblocked attacker you control to hand during the declare blockers step.)\nEach player may discard their hand and draw seven cards.',
        verified='2026-10-09',
        rationale=("The owner: 'a weaker Reforge the Soul'. A second wheel; measured so 'weaker' has a size."),
        implement=("MODELLED: the existing `wheel` script, Reforge the Soul's: discard the hand to the graveyard (Monument "
                   "fires), draw seven, declined when seven would deck you. The opponents' half is blind (no hands, §4). "
                   "NOT MODELLED: Sneak, an alternative cost that returns an unblocked attacker -- in this list usually the "
                   "commander, whose recast costs more than the sneak saves. And 'may': the pilot always wheels, as "
                   "Reforge's text forces. PARTLY MODELLED for Sneak."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card='Immolating Gyre',
        cost='{4}{R}{R}', identity='R',
        type_line='Sorcery',
        oracle="Immolating Gyre deals X damage to each creature and planeswalker you don't control, where X is the number of instant and sorcery cards in your graveyard.",
        verified='2026-10-09',
        rationale=("The owner: 'not sure how strong it is, interested to model'. A ONE-SIDED sweeper whose size is the "
                   "graveyard Lorehold's rummage fills -- a catch-up card that costs this list nothing."),
        implement=("MODELLED: X read on resolution; the pod's creatures die in the share `min(1, X / gyre_full_x)` -- THE "
                   "KNOB, a judgement: the pod's creatures are a count with no toughness (§4), so `gyre_full_x` (6) is the X "
                   "at which every one of them dies, with toughness spread evenly below it. Routed through `resolve_own_wipe` "
                   "(one-sided, so yours are spared) and the wipe gate, which prices the same share. Damage, so it is in "
                   "WIPE_DESTROYS. NOT MODELLED: planeswalkers (§4)."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='lorehold', card='Profound Journey',
        cost='{5}{W}{W}', identity='W',
        type_line='Sorcery',
        oracle="Return target permanent card from your graveyard to the battlefield.\nRebound (If you cast this spell from your hand, exile it as it resolves. At the beginning of your next upkeep, you may cast this card from exile without paying its mana cost.)",
        verified='2026-10-09',
        rationale=("The owner: 'a weaker Restoration Seminar'. Two reanimations for one card when it is cast from hand -- "
                   "and a miracle IS cast from hand."),
        implement=("NEW TO THIS ENGINE: reanimation and rebound. The best permanent card in the graveyard (by priority, a "
                   "land only when nothing else is there) enters through the same path a cast permanent does, its ETBs "
                   "included. Rebound is read from Scryfall's keywords (`_evasion.REBOUND`), exiles the card when cast from "
                   "hand and casts it free at your next upkeep. No legal target, no cast. NOTE: Restoration Seminar, the card "
                   "the owner compares it to, is KNOWN_BLIND in this engine -- unimplemented -- so the two cannot be compared "
                   "here until it is."),
        triage='LIVE',
        prepared='tests/test_lorehold_big_spells.py',
        rejected='MEASURED 2026-10-09 and PROMOTED: the Candidate in MEASURED carries the number (§0z124). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
]


# The four 2026-08-31/09-01 Lorehold changes are COMMITTED as of v16, so
# they are in the deck list itself and no longer swap-in candidates.
CATALOG = (lorehold_v17, {
    # 2026-09-16 batch (§0z26).
    "Jeska's Will": lorehold_v17.JESKAS_WILL,
    "Past in Flames": lorehold_v17.PAST_IN_FLAMES,
    "Molecule Man": lorehold_v17.MOLECULE_MAN,
    "Galvanoth": lorehold_v17.GALVANOTH,
    "Caldera Pyremaw": lorehold_v17.CALDERA_PYREMAW,
    "Radiant Scrollwielder": lorehold_v17.RADIANT_SCROLLWIELDER,
    "Hidden Retreat": lorehold_v17.HIDDEN_RETREAT,
    "Sunbird's Invocation": lorehold_v17.SUNBIRDS_INVOCATION,
    # REALITY FRACTURE, 2026-09-21 (preview text).
    "Stingcaster Mage": lorehold_v17.STINGCASTER_MAGE,
    # Queued item 0c's head-to-heads, 2026-09-25 (§0z53).
    "Goldspan Dragon": lorehold_v17.GOLDSPAN_DRAGON,
    # MYSTERY BOOSTER COMMANDER EDITION, 2026-09-29 (§0z74).
    "Chief Magistrate of Mercadia": lorehold_v17.CHIEF_MAGISTRATE_OF_MERCADIA,
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    "Ancient Tomb": lorehold_v17.ANCIENT_TOMB,
    "Command Beacon": lorehold_v17.COMMAND_BEACON,
    # The owner's proposal, 2026-10-09.
    "Prisoner's Dilemma": lorehold_v17.PRISONERS_DILEMMA,
    # The owner's second batch, 2026-10-09. Furygale Flocking and
    # Profound Journey are COMMITTED in v17 (in the list itself, so no
    # longer swap-in candidates); the two cuts are catalogued so a
    # re-measure can name them.
    **{c.name: c for c in lorehold_v17.BATCH_2026_10_09_SPELLS
       if c.name not in ("Furygale Flocking", "Profound Journey")},
    "Verge Rangers": lorehold_v17.VERGE_RANGERS,
    "Lightning Greaves": lorehold_v17.LIGHTNING_GREAVES})
