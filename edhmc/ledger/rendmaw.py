"""rendmaw's ledger entries and swap-in catalog.

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

from edhmc.decks import rendmaw_v12
from edhmc.ledger.records import Change, Candidate, Simulated, Proposal


COMMITTED: list[Change] = [
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
]


MEASURED: list[Candidate] = [
    Candidate(
        deck='rendmaw',
        card='Davvol, Evincar of Rath',
        measured='2026-09-29',
        win_rate="REAL SWAP -Ashnod's Altar +Davvol, Evincar of Rath, N=15,000 paired: +0.0003 +-0.0009 (inside its bar) at T10 and -0.0051 +-0.0024 (significant) at T20.",
        signal='win',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 1.0 triggers a game at T20: 0.34 {B} spent, 0.66 lost at a step boundary, and a point of life each time. The bleeding outruns the mana.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits="Exact as modelled -- the mandatory life loss is the card's real price.",
        verdict="NEGATIVE AT T20 (-0.0051, significant) and inside its bar at T10. Loses to Ashnod's Altar, itself the weakest evaluated row. Not a fit for this list.",
    ),
    Candidate(
        deck='rendmaw',
        card='Thomil, the Destroyer',
        measured='2026-09-29',
        win_rate="REAL SWAP -Ashnod's Altar +Thomil, the Destroyer, N=15,000 paired: -0.0003 +-0.0009 (inside its bar) at T10 and +0.0059 +-0.0026 (significant) at T20.",
        signal='win',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 0.36 Zombies and 0.19 Lords a game at T20; 0.35 Lord sacrifices feed Blood Artist / Meathook.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='FLOOR: the 0 not modelled (trample is since §0z92); loyalty only rises (§4).',
        verdict='T20 only; inside its bar at T10.',
    ),
    # REALITY FRACTURE, recorded 2026-09-25 (§0z45).
    Candidate(
        deck='rendmaw',
        card='Proft, Sinister Mastermind',
        measured='2026-09-21',
        win_rate=("REAL SWAP -Ashnod's Altar +Proft, N=15,000 paired: +0.0005 +-0.0006 "
            'at T10 (inside its bar) and +0.0043 +-0.0018 at T20 (significant); d'
            'amage T20 +0.47 +-0.08.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence='results/fra_batch2.txt (diagnostics/run_fra_batch2.py)',
        limits=('A LONG-HORIZON CALL ONLY: significant at T20, inside its bar at T10.'
            ' Threshold gates a cast attempt 2.81 times a game (proft_gated), so '
            'it arrives late by design; 601.3 makes that a castability restrictio'
            'n, modelled as one. STALE -- NOT RESTATED, since later on 2026-09-2'
            '5: it was CURRENT when recorded (check_unchanged_decks 246b148 vs 20'
            "26-09-25 BIT-IDENTICAL), and then §0z47 moved rendmaw's baseline -- "
            "March of the World Ooze's Elephant and Arasta's Spider now fire on o"
            'pponent counterspells, +0.064 tokens a game. Small, and in a deck th'
            'at makes 9 tokens a game, but the number no longer describes the lis'
            't. Re-measure before a decision rests on it.'),
        verdict=('A small real card at T20 and nothing measurable at T10. The cut, Ash'
            "nod's Altar, was chosen as the deck's worst MODEL-EVALUATED row but "
            "sits inside its own bar, so this swap is 'least supported cut', not "
            "'bad card out'."),
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
        deck="rendmaw", card="Pitiless Plunderer", measured="2026-09-26",
        win_rate=("+0.0003 +-0.0006 at T10, +0.0014 +-0.0017 at T20 "
                  "(N=15,000 paired, candidate row in Pygmy Kavu's slot); "
                  "the real swap -Pygmy Kavu +Plunderer +0.0000 / +0.0012 "
                  "+-0.0019"),
        signal="--",
        rationale=("INSIDE ITS OWN BAR -- unmeasured, not measured as weak. "
                   "Proposed as a DIAGNOSTIC for Ashnod's Altar: is the Altar "
                   "a bad card or an unfuelled one? Answered: not by this "
                   "card. The Altar's row is -0.0017 +-0.0012 without the "
                   "Plunderer and -0.0012 +-0.0012 with it, and altar "
                   "sacrifices do not move (0.061 -> 0.059 a game at T20)."),
        evidence=("0.40 Treasures made and 0.32 spent a game at T20. "
                  "results/treasures_cmdr_20260926.txt "
                  "(diagnostics/run_treasures_cmdr.py), §0z64."),
        limits=("A FLOOR in one place: a wipe removes permanents one at a "
                "time, so creatures that die after the Plunderer in the same "
                "wipe do not pay, where the real trigger looks back. Treasures "
                "are only MANA here -- nothing in rendmaw reads an artifact "
                "count that a Treasure would feed. Measured with commander "
                "damage live (§0z65), which moves rendmaw by +0.0007."),
        verdict=("Not a card for this list on this evidence. The Treasure "
                 "engine it needed is built and pinned (tests/test_treasures.py) "
                 "and costs the committed list nothing, so the next "
                 "Treasure-maker for rendmaw is a measurement, not a project."),
    ),
    Candidate(
        deck='rendmaw',
        card="Gaea's Cradle",
        measured="2026-10-06",
        win_rate='+0.0053 +-0.0016 at T10, +0.0104 +-0.0032 at T20 against a Forest',
        signal='both',
        rationale="{G} per creature you control -- a token deck's mana land.",
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: cradle_mana +8.279, life_lost_to_own_cards +0.010, vault_activations +0.005. §0z113.',
        limits="Every clause modelled, in `available_mana` and in `spend`'s fallback (§0z4); 8.3 mana a game.",
        verdict='Significant at both horizons (+0.0053 / +0.0104) in place of a Forest. The best land candidate outside azusa. OWNER DEFERRED 2026-10-06: a valid card, but outside the price range of the casual table the owner plays at -- a judgement about the table, not about the number.',
    ),
    Candidate(
        deck='rendmaw',
        card='Ancient Tomb',
        measured="2026-10-06",
        win_rate='+0.0042 +-0.0016 at T10, -0.0049 +-0.0031 at T20 against a Forest',
        signal='both',
        rationale='{C}{C} from a land, for 2 damage a tap.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Forest. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: life_lost_to_own_cards +1.817, tomb_damage +1.823, vault_activations -0.001. §0z113.',
        limits='Every clause modelled; 1.8 damage a game.',
        verdict='SIGN CHANGE: +0.0042 at T10 and -0.0049 at T20, both significant. Fast mana early, and 1.8 life a game that costs the long games. Not a swap. OWNER DEFERRED 2026-10-06: a valid card, but outside the price range of the casual table the owner plays at -- a judgement about the table, not about the number.',
    ),
    # --- The owner's multi-type batch for rendmaw, 2026-10-10 (§0z125). Every card
    # is two card types; PART 2 of the diagnostic prices that half on its own.
    Candidate(
        deck="rendmaw", card='The Swarmweaver', measured="2026-10-10",
        win_rate='+0.0074 +-0.0025 at T20, +0.0036 +-0.0012 at T10',
        signal='both',
        rationale="Two flying Insects on a Scarecrow, and a delirium pump for the list's Insects and Spiders.",
        evidence="diagnostics/run_rendmaw_multitype.py, results/rendmaw_multitype_20261010.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pygmy Kavu's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates rendmaw3 --n=15000` (results/candidates_rendmaw3.txt). §0z125. swarmweaver_insects +0.41 a game, swarmweaver_pumped +0.31 (attackers pumped under delirium), tokens_made +0.39, damage +1.11 at T20. ITS TYPE LINE (vs itself as a one-type Creature, same slot): +0.0019 +-0.0015 at T20, +0.0022 +-0.0009 at T10 -- the Rendmaw trigger and the artifact half.",
        limits='A FLOOR: deathtouch is not modelled (§4).',
        verdict='Significant at both horizons; with Dalek Squadron the top of the batch -- a set, not a ranking (§0c).',
    ),
    Candidate(
        deck="rendmaw", card='Dalek Squadron', measured="2026-10-10",
        win_rate='+0.0071 +-0.0025 at T20, +0.0044 +-0.0012 at T10',
        signal='both',
        rationale='Menace, and myriad: one attacker becomes one per opponent.',
        evidence="diagnostics/run_rendmaw_multitype.py, results/rendmaw_multitype_20261010.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pygmy Kavu's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates rendmaw3 --n=15000` (results/candidates_rendmaw3.txt). §0z125. myriad_copies +0.76 a game, damage +2.13 -- the largest damage row of the five -- at T20. ITS TYPE LINE: +0.0027 +-0.0014 at T20, +0.0020 +-0.0008 at T10.",
        limits="A slight CEILING: the copies join the pod-wide split instead of one going at each other opponent (Furygale Flocking's caveat, §0z124).",
        verdict='Significant at both horizons; with The Swarmweaver the top of the batch.',
    ),
    Candidate(
        deck="rendmaw", card='Fire Navy Trebuchet', measured="2026-10-10",
        win_rate='+0.0050 +-0.0022 at T20, +0.0021 +-0.0010 at T10',
        signal='both',
        rationale='A 2/1 flier in every attack, sacrificed at the end step -- a death for the aristocrat payoffs.',
        evidence="diagnostics/run_rendmaw_multitype.py, results/rendmaw_multitype_20261010.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pygmy Kavu's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates rendmaw3 --n=15000` (results/candidates_rendmaw3.txt). §0z125. boulders_made +0.53 a game, every one sacrificed; drain_damage +0.10, tokens_made +0.60, cards_drawn +0.04 (Erebos) at T20. ITS TYPE LINE: +0.0023 +-0.0014 at T20, +0.0017 +-0.0008 at T10.",
        limits='Every clause that acts is modelled; reach is inert (your creatures never block, §4).',
        verdict='Significant at both horizons, smaller than the top two.',
    ),
    Candidate(
        deck="rendmaw", card='Wickerfolk Indomitable', measured="2026-10-10",
        win_rate='+0.0035 +-0.0020 at T20, +0.0015 +-0.0008 at T10',
        signal='both',
        rationale='A 4/3 that can be recast from the graveyard -- a repeatable Rendmaw trigger.',
        evidence="diagnostics/run_rendmaw_multitype.py, results/rendmaw_multitype_20261010.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pygmy Kavu's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates rendmaw3 --n=15000` (results/candidates_rendmaw3.txt). §0z125. wickerfolk_gy_casts +0.04 a game at T20 (0.08 life). THE GRAVEYARD CLAUSE ALONE (vs the card with `wickerfolk_gy` off): +0.0003 +-0.0010 at T20 -- inside its bar. THE KNOB: `wickerfolk_life_floor` 6 -> +0.0031, 14 -> +0.0034 at T20, the default 10 +0.0035: not load-bearing. ITS TYPE LINE: +0.0023 +-0.0015 at T20, +0.0017 +-0.0007 at T10.",
        limits='A FLOOR on the recast: the pilot never sacrifices Wickerfolk on purpose to recast it, and a Treasure or a nontoken body is never offered as the sacrifice. It returns only after the pod kills it, which is rare.',
        verdict='Significant at both horizons, but as a 4/3 for four that triggers Rendmaw: the clause it was picked for fires 0.04 times a game and is worth nothing measurable.',
    ),
    Candidate(
        deck="rendmaw", card='H.E.R.B.I.E., Lovable Robot', measured="2026-10-10",
        win_rate='+0.0013 +-0.0020 at T20, -0.0001 +-0.0009 at T10',
        signal='--',
        rationale="The owner's pick: a two-mana flying mana creature that triggers Rendmaw.",
        evidence="diagnostics/run_rendmaw_multitype.py, results/rendmaw_multitype_20261010.txt: N=15,000 paired, seeds 80000.., the staged list, the card in Pygmy Kavu's slot against a blank of its cost, one T20 game per seed with T10 read off it. The T20 row IS `python -m tools.candidates rendmaw3 --n=15000` (results/candidates_rendmaw3.txt). §0z125. herbie_surveils +0.07 a game at T20 (a land binned 0.01). ITS TYPE LINE: +0.0022 +-0.0013 at T20, +0.0007 +-0.0006 at T10 -- significant: the Rendmaw trigger is real, and the rest of the card (a {C} mana creature that taps instead of attacking) is worth no more than a two-mana 1/1 blank here.",
        limits="A FLOOR on fixing: '{1}, {T}: Add one mana of any color' is not modelled. The surveil is rare by construction -- the precombat main casts only pump.",
        verdict='INSIDE ITS BAR at both horizons: unmeasured, not bad. Its trigger half is significant on its own; the mana half is not visible in a list that already has eight two-mana rocks and mana creatures.',
    ),
]


CHANGES: list[Change] = []


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


SIMULATED: list[Simulated] = [
    Simulated(
        deck='rendmaw', remove="Ashnod's Altar", add='Davvol, Evincar of Rath',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=("REAL SWAP -Ashnod's Altar +Davvol, Evincar of Rath, N=15,000 paired: +0.0003 +-0.0009 (inside its bar) at T10 and -0.0051 +-0.0024 (significant) at T20."),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0003 +-0.0009 at T10 and -0.0054 +-0.0024 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='rendmaw', remove="Ashnod's Altar", add='Thomil, the Destroyer',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=("REAL SWAP -Ashnod's Altar +Thomil, the Destroyer, N=15,000 paired: -0.0003 +-0.0009 (inside its bar) at T10 and +0.0059 +-0.0026 (significant) at T20."),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: -0.0003 +-0.0009 at T10 and +0.0053 +-0.0026 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='rendmaw', remove="Ashnod's Altar", add='Proft, Sinister Mastermind',
        measured='2026-09-21', source='results/fra_batch2.txt',
        result=("REAL SWAP -Ashnod's Altar +Proft, N=15,000 paired: +0.0005 +-0.0006 at T10 (inside its bar) and +0.0043 +-0.0018 at T20 (significant); damage T20 +0.47 +-0.08."),
    ),
]


PROPOSED: list[Proposal] = [
    Proposal(
        deck='rendmaw', card='Davvol, Evincar of Rath', cost='{2}{B}{G}',
        identity='BG', type_line='Legendary Creature — Phyrexian Noble',
        oracle='Whenever another creature you control enters, you lose 1 life and add {B}.',
        verified="2026-09-29",
        rationale="A mana engine keyed on the deck's whole output -- every Bird, Saproling, Faerie and Spider is {B} -- with a MANDATORY life cost on every one of them, in the deck that makes the most tokens in the project. Whether the mana outruns the bleeding is exactly what this model can measure.",
        implement="DONE 2026-09-29. `engine.davvol_trigger` at every rendmaw site where a creature enters (make_tokens, a cast, the commander, Cauldron, Lord of the Pit); the {B} is floating mana (`davvol_float`, spent through a `DavvolMana` owner, the TreasureMana shape) that `empty_mana_pool` clears at every step boundary, so an upkeep token's {B} is lost before it can be used -- counted as `davvol_mana_lost`. The life is always charged. Classify SCRIPTED at staging.",
        triage="LIVE",
        rejected="MEASURED 2026-09-29 and PROMOTED: the real swap against Ashnod's Altar is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
    Proposal(
        deck='rendmaw', card='Thomil, the Destroyer', cost='{3}{B}{B}',
        identity='B', type_line='Legendary Planeswalker — Thomil',
        oracle='+2: Create a 2/2 black Zombie creature token.\n0: You may sacrifice a creature. If you do, add {B}{B}{B}.\n−5: Create a Lord of the Pit token. (It\'s a {4}{B}{B}{B} 7/7 Demon creature with flying, trample, and "At the beginning of your upkeep, sacrifice another creature. If you can\'t, this token deals 7 damage to you.")\nThomil, the Destroyer can be your commander.',
        verified="2026-09-29",
        rationale="Zombies are Blood Artist and Meathook fodder and Lord of the Pit's upkeep turns one of them a turn into a death trigger; rendmaw has the bodies to feed it.",
        implement="DONE 2026-09-29. `engine.thomil_step` with rendmaw's `make_tokens` for the Zombie and `rendmaw_token` for the Lord (Primal Vigor and Parallel Lives double both); the Lord's sacrifice is `rendmaw_sacrifice`, routed like Twitching Doll's. FLOOR: the 0 is not taken (the Lord's trample IS modelled since §0z92; it was not when this was written); loyalty only goes up (§4). Classify PARTLY_MODELLED at staging.",
        triage="LIVE",
        rejected="MEASURED 2026-09-29 and PROMOTED: the real swap against Ashnod's Altar is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.",
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
                   "§0z9 already corrected. -- WRONG ABOUT RENDMAW: §0z6 is "
                   "shilgengar's, and rendmaw had no Treasures at all, which "
                   "is why §0z26 abandoned the card. Built in §0z64 "
                   "(`engine.rendmaw_mana`) and MEASURED: see MEASURED."),
    ),
    Proposal(
        deck='rendmaw', card="Gaea's Cradle",
        cost='', identity='G',
        type_line='Legendary Land',
        oracle='{T}: Add {G} for each creature you control.',
        verified='2026-10-06',
        rationale="Rendmaw makes about twenty tokens a game; Cradle taps for {G} per creature, the deck's best possible mana land.",
        implement='SHARED primitive: a land whose mana is a count -- `available_mana` and `spend` must both read it (§0z4). Every clause modelled.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='rendmaw', card='Ancient Tomb',
        cost='', identity='',
        type_line='Land',
        oracle='{T}: Add {C}{C}. This land deals 2 damage to you.',
        verified='2026-10-06',
        rationale='Two colourless mana from a land drop in a deck whose spells are green-heavy (G 36, B 29 pips) -- the colour cost is the question.',
        implement='The shared Ancient Tomb implementation.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    # --- The owner, 2026-10-10: "new, possibly obscure cards for Rendmaw ...
    # two or more types that may fit the deck's themes (flying, token
    # generation, forced combat)", H.E.R.B.I.E. named regardless. A Scryfall
    # search (`id<=bg f:commander` and two card types on the face cast, 950
    # cards; 262 after a theme screen on the oracle text) was cut to twelve,
    # and the owner asked for the five recommended to be modelled. Every card
    # here is two card types, so every cast is a Rendmaw trigger. §0z125.
    Proposal(
        deck='rendmaw', card='H.E.R.B.I.E., Lovable Robot',
        cost='{2}', identity='',
        type_line='Legendary Artifact Creature — Robot Scout',
        oracle="Flying\nAt the beginning of combat on your turn, if you've cast a noncreature spell this turn, surveil 1.\n{T}: Add {C}.\n{1}, {T}: Add one mana of any color.",
        verified='2026-10-10',
        rationale=("The owner's pick. A turn-two Rendmaw trigger that is also a mana creature -- the Copper Myr "
                   "slot, with flying."),
        implement=("MODELLED: a 1/1 flier, and {T}: Add {C} as a mana creature (`mana=(1, 'C')`, summoning-sick "
                   "like every Myr). The surveil, at the beginning of combat if a noncreature spell was cast this "
                   "turn, bins a land off the top when six lands are out (`surveil_land_floor`, lorehold's Dragon's "
                   "Rage Channeler rule). NOT MODELLED: '{1}, {T}: Add one mana of any color' -- a filter, net zero "
                   "mana, that turns a colourless source into a coloured one; the payment solver has no way to "
                   "spend a unit to change another's colour. A FLOOR, and a small one in a two-colour list whose "
                   "lands make both. PARTLY MODELLED."),
        triage="LIVE",
        prepared="tests/test_rendmaw_multitype.py",
        rejected="MEASURED 2026-10-10 and PROMOTED: the Candidate in MEASURED carries the number (§0z125). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
    Proposal(
        deck='rendmaw', card='The Swarmweaver',
        cost='{2}{B}{G}', identity='BG',
        type_line='Legendary Artifact Creature — Scarecrow',
        oracle='When The Swarmweaver enters, create two 1/1 black and green Insect creature tokens with flying.\nDelirium — As long as there are four or more card types among cards in your graveyard, Insects and Spiders you control get +1/+1 and have deathtouch.',
        verified='2026-10-10',
        rationale=("Three bodies, two of them fliers, on a Scarecrow -- Rendmaw's own type. Delirium is easy in a "
                   "graveyard made of multi-type cards, and the list already has Insects and Spiders: Grist's and "
                   "Arasta's tokens, Haywire Mite, Twitching Doll, Arasta herself."),
        implement=("MODELLED: two 1/1 FLYING Insect tokens (a token-level flying flag: Grist's Insects do not "
                   "fly, so 'Insect' cannot join FLYING_TOKENS); +1/+1 to every Insect and Spider you control while "
                   "`opponents.delirium` holds, read in `power_of`/`toughness_of`. Subtypes come from Scryfall "
                   "(`_evasion.INSECT_SPIDER`, generated), tokens by their name. NOT MODELLED: deathtouch -- the "
                   "pod's blockers are a count with no toughness and your creatures never block (§4). PARTLY."),
        triage="LIVE",
        prepared="tests/test_rendmaw_multitype.py",
        rejected="MEASURED 2026-10-10 and PROMOTED: the Candidate in MEASURED carries the number (§0z125). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
    Proposal(
        deck='rendmaw', card='Wickerfolk Indomitable',
        cost='{3}{B}', identity='B',
        type_line='Artifact Creature — Scarecrow',
        oracle='You may cast this card from your graveyard by paying 2 life and sacrificing an artifact or creature in addition to paying its other costs.',
        verified='2026-10-10',
        rationale=("A repeatable Rendmaw trigger: every cast from the graveyard is a 'play', and the sacrifice can "
                   "be one of the Birds the trigger just made. A 4/3 body each time, and a death for Blood Artist "
                   "and the Meathook."),
        implement=("NEW TO THIS ENGINE: casting a card from the graveyard. `main_phase` offers it from the "
                   "graveyard with the additional costs: 2 life (charged, §0i) above `wickerfolk_life_floor` (10, a "
                   "judgement, erebos_life_floor's) and the sacrifice of a creature token (the smallest), else a "
                   "Treasure -- an artifact. A death, so `on_creature_death` fires. Every clause is modelled. THE "
                   "POLICY IS A FLOOR: the pilot never sacrifices Wickerfolk on purpose to recast it; it comes back "
                   "only after the pod kills it."),
        triage="LIVE",
        prepared="tests/test_rendmaw_multitype.py",
        rejected="MEASURED 2026-10-10 and PROMOTED: the Candidate in MEASURED carries the number (§0z125). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
    Proposal(
        deck='rendmaw', card='Fire Navy Trebuchet',
        cost='{2}{B}', identity='B',
        type_line='Artifact Creature — Wall',
        oracle="Defender, reach\nWhenever you attack, create a 2/1 colorless Construct artifact creature token with flying named Ballistic Boulder that's tapped and attacking. Sacrifice that token at the beginning of the next end step.",
        verified='2026-10-10',
        rationale=("Rendmaw's Birds are goaded, so this deck attacks every turn: a free 2/1 flier in every swing, "
                   "and a death at every end step for Blood Artist, the Meathook and Erebos."),
        implement=("MODELLED: 'whenever you attack' -- a 2/1 flying artifact creature token joins the attack "
                   "(`enters_attacking`), and is sacrificed at the end step (`boulder_end_step`), a death. DEFENDER "
                   "is new to this engine: read from Scryfall's keywords (`_evasion.DEFENDER`, generated) and "
                   "excluded from `combat`'s attackers. Reach is inert (your creatures never block, §4). Every "
                   "clause that acts is modelled."),
        triage="LIVE",
        prepared="tests/test_rendmaw_multitype.py",
        rejected="MEASURED 2026-10-10 and PROMOTED: the Candidate in MEASURED carries the number (§0z125). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
    Proposal(
        deck='rendmaw', card='Dalek Squadron',
        cost='{2}{B}', identity='B',
        type_line='Artifact Creature — Dalek',
        oracle="Menace\nMyriad (Whenever this creature attacks, for each opponent other than defending player, you may create a token copy that's tapped and attacking that player or a planeswalker they control. Exile the tokens at end of combat.)",
        verified='2026-10-10',
        rationale=("Forced combat pointed outward: one attacker becomes one per opponent, each with menace -- "
                   "Rendmaw's own evasion -- and the copies are tokens, which Primal Vigor doubles."),
        implement=("MODELLED: menace (generated MENACE, for the card and its copies, which share its name); "
                   "myriad -- one 3/3 menace token copy per living opponent but one, tapped and attacking, exiled "
                   "(no death) after combat damage. NOT MODELLED: 'attacking THAT player' -- the copies join the one "
                   "attack `combat_damage` splits across the pod rather than going one at each other opponent, so "
                   "the split is the pilot's (Furygale Flocking's caveat, §0z124), a slight CEILING. PARTLY."),
        triage="LIVE",
        prepared="tests/test_rendmaw_multitype.py",
        rejected="MEASURED 2026-10-10 and PROMOTED: the Candidate in MEASURED carries the number (§0z125). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
]


# March of the World Ooze is COMMITTED as of v12, so it is in the deck
# list itself and no longer a swap-in candidate.
CATALOG = (rendmaw_v12, {
    # 2026-09-16 batch (§0z26).
    "Parallel Lives": rendmaw_v12.PARALLEL_LIVES,
    "Mycoloth": rendmaw_v12.MYCOLOTH,
    "Cauldron of Essence": rendmaw_v12.CAULDRON_OF_ESSENCE,
    # §0z64: Treasures built, card measured.
    "Pitiless Plunderer": rendmaw_v12.PITILESS_PLUNDERER,
    # REALITY FRACTURE, 2026-09-21 (preview text).
    "Proft, Sinister Mastermind": rendmaw_v12.PROFT_SINISTER_MASTERMIND,
    # MYSTERY BOOSTER COMMANDER EDITION, 2026-09-29 (§0z74).
    "Davvol, Evincar of Rath": rendmaw_v12.DAVVOL_EVINCAR_OF_RATH,
    "Thomil, the Destroyer": rendmaw_v12.THOMIL_THE_DESTROYER,
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    "Gaea's Cradle": rendmaw_v12.GAEAS_CRADLE,
    "Ancient Tomb": rendmaw_v12.ANCIENT_TOMB,
    # The owner's multi-type batch, 2026-10-10 (§0z125).
    **{c.name: c for c in rendmaw_v12.BATCH_2026_10_10}})
