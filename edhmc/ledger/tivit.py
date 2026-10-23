"""tivit's ledger entries and swap-in catalog.

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

from edhmc.decks import tivit_v1
from edhmc.ledger.records import Change, Candidate, Simulated, Proposal


COMMITTED: list[Change] = []


MEASURED: list[Candidate] = [
    Candidate(
        deck='tivit',
        card='Venser, Visionary Traveler',
        measured='2026-09-29',
        win_rate="REAL SWAP -Tamiyo's Journal +Venser, Visionary Traveler, N=15,000 paired: +0.0067 +-0.0018 (significant) at T10 and +0.0115 +-0.0029 (significant) at T20.",
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. +0.40 blinks and +0.33 dilemmas a game at T20, Tivit carrying two counters. extra_turns FELL 0.012: Tamiyo's Journal's Clues were Time Sieve fuel.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='PARTLY: the -2 is blind (§4); the +1 with Tivit absent blinks nothing.',
        verdict="Significant at both horizons, half of Dyfed's T20 number.",
    ),
    Candidate(
        deck='tivit',
        card='Dyfed, the Guiding Hand',
        measured='2026-09-29',
        win_rate="REAL SWAP -Tamiyo's Journal +Dyfed, the Guiding Hand, N=15,000 paired: +0.0047 +-0.0017 (significant) at T10 and +0.0220 +-0.0032 (significant) at T20.",
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 0.84 Powerstones a game at T20, 1.54 Powerstone mana spent, +0.22 extra turns (the -1 untaps the Sieve 0.043 times, the -6 fetches it 0.10 times).",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='FLOOR: untapping anything but Time Sieve is not modelled.',
        verdict="Significant at both horizons; the strongest tivit card here, comparable to Anointed Procession's staged +0.0145 in a different slot (not a ranking, §0e).",
    ),
    Candidate(
        deck='tivit',
        card='Memnarch, the Warden',
        measured='2026-09-21',
        win_rate=("REAL SWAP -Tamiyo's Journal +Memnarch, the Warden, N=15,000 paired: "
            '+0.0099 +-0.0020 at T10 and +0.0167 +-0.0033 at T20, significant at '
            'both; damage T20 +1.52 +-0.19.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence='results/fra_batch2.txt (diagnostics/run_fra_batch2.py)',
        limits=("The cut, Tamiyo's Journal (+0.0006 +-0.0017), is INSIDE its own bar,"
            " so this is 'least supported cut', not 'measured bad'. STALE -- NOT "
            "RESTATED. This deck's baseline has MOVED since the measurement (§0z4"
            '4: four tivit priority moves adopted 2026-09-25; the table was rebui'
            "lt 2026-09-26, §0z60, this number was not); check_unchanged_decks 246b"
            '148 vs 2026-09-25 reports it MOVED on 8 of 8 metrics. Re-measure bef'
            'ore any head-to-head decision rests on it.'),
        verdict=('The strongest of the batch-2 four and significant at both horizons, '
            'on a baseline that has since moved.'),
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
    Candidate(
        deck='tivit',
        card='Treasure Vault',
        measured="2026-10-06",
        win_rate='-0.0007 +-0.0014 at T10, -0.0003 +-0.0018 at T20 against a Swamp',
        signal='dmg',
        rationale='An artifact land; {X}{X}, sacrifice: X Treasures.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Swamp. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: vault_activations +0.010, vault_x +0.035. §0z113.',
        limits='Every clause modelled. A POLICY: cracked at the end step for >= `vault_min_treasures` (4); 0.01 cracks a game. At vault_min_treasures=2: 0.03 cracks, +0.0005 +-0.0019 at T20.',
        verdict='A blank: tivit spends its mana, so the Vault is nearly always a colourless land in place of a coloured one.',
    ),
]


CHANGES: list[Change] = [
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
            "the deck actually gains, which is the number that decides it. "
            "RE-MEASURED 2026-09-17 ON THE POST-§0z30 BASELINE (§0z33, "
            "diagnostics/run_tivit_procession.py): the pod-order fix moved "
            "tivit's baseline +0.0647 at T20, so these numbers were restated "
            "rather than kept. Same N and seeds: real swap +0.0133 [+0.0105, "
            "+0.0160] at T10 and +0.0157 [+0.0115, +0.0201] at T20, against "
            "baselines of 0.1236 and 0.3915; candidate row +0.0325 +-0.0037. "
            "Every number moved UP by less than its bar, and the token "
            "mechanism is unchanged: artifacts_made +13.7 and treasures_made "
            "+7.0 a game at T20. The staging stands."),
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
        reverified="RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0087 +-0.0043 at T10 (significant), +0.0007 +-0.0049 at T20 -- INSIDE ITS BAR AT T20. THE STAGING NO LONGER HOLDS AT BOTH HORIZONS. KEPT BY THE OWNER, 2026-10-15 ('keep Anointed Procession for now'), on its T10 number; withdrawing it would move tivit's baseline and need a rebuild of its table (§0z27). The pod alone moved it -0.0026 +-0.0042 at T10 and -0.0079 +-0.0061 at T20 (POD_PRE_V4 at the same commit: +0.0113 / +0.0087, the T20 barely significant, as it was on 2026-10-07). A LAND CUT, which the harness flatters. Partly explained: POD_V4's games are 0.4 turns shorter, and the doubler's extra artifacts fall from 22.7 to 20.0 a game; not the response window (§0z143). results/restage_item26_20261015.txt (§0z143)." + 'RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0120 +-0.0040 at T10, +0.0081 +-0.0050 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + (
            "NOT RE-MEASURED, AND THIS CARD'S OWN PRIORITY IS ONE OF THE MOVES "
            "(2026-09-25, §0z44). The owner adopted tivit's four priority moves"
            ' -- Anointed Procession 8 -> 10 among them, with Mirkwood Bats 8 -'
            '> 10, Rhystic Study 9.5 -> 7.5 and Tempting Contract 6.5 -> 8.5 --'
            ' jointly +0.0225 / +0.0211 at T10 / T20. So the +0.0113 / +0.0145 '
            'above was measured at a priority now shown to be worth ~0.008 less'
            ', on a baseline that has since moved. It has not been restated. Th'
            'e tivit TABLE was rebuilt 2026-09-26 (§0z60); this swap was not. Re'
            '-measure before commit.'
            " RE-MEASURED 2026-09-26 ON THE REBUILT BASELINE (§0z63), after §0z44 moved its own priority to 10: +0.0145 +-0.0036 at T10, +0.0191 +-0.0052 at T20 -- larger than every earlier measurement. The staging stands. results/restage_20260926.txt."
        + ' ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0151 +-0.0036 at T10, +0.0181 +-0.0052 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81)."),
    ),
]


WITHDRAWN: list[Change] = []


SIMULATED: list[Simulated] = [
    Simulated(
        deck='tivit', remove="Tamiyo's Journal", add='Venser, Visionary Traveler',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=("REAL SWAP -Tamiyo's Journal +Venser, Visionary Traveler, N=15,000 paired: +0.0067 +-0.0018 (significant) at T10 and +0.0115 +-0.0029 (significant) at T20."),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0067 +-0.0018 * at T10 and +0.0115 +-0.0028 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='tivit', remove="Tamiyo's Journal", add='Dyfed, the Guiding Hand',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=("REAL SWAP -Tamiyo's Journal +Dyfed, the Guiding Hand, N=15,000 paired: +0.0047 +-0.0017 (significant) at T10 and +0.0220 +-0.0032 (significant) at T20."),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0047 +-0.0017 * at T10 and +0.0220 +-0.0031 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='tivit', remove="Tamiyo's Journal", add='Memnarch, the Warden',
        measured='2026-09-21', source='results/fra_batch2.txt',
        result=("REAL SWAP -Tamiyo's Journal +Memnarch, the Warden, N=15,000 paired: +0.0099 +-0.0020 at T10 and +0.0167 +-0.0033 at T20, significant at both; damage T20 +1.52 +-0.19."),
    ),
]


PROPOSED: list[Proposal] = [
    Proposal(
        deck='tivit', card='Venser, Visionary Traveler', cost='{3}{W}{U}',
        identity='WU', type_line='Legendary Planeswalker — Venser',
        oracle="Each nontoken creature you control that wasn't cast from your hand enters with two additional +1/+1 counters on it.\n+1: Exile up to one other target permanent you control. At the beginning of the next end step, return that card to the battlefield under its owner's control.\n−2: For each opponent, return up to one target nonland permanent that player controls to its owner's hand.\nVenser, Visionary Traveler can be your commander.",
        verified="2026-09-29",
        rationale='Its +1 on Tivit is a FRESH ETB EVERY TURN -- a dilemma a turn with no mana spent, taken after combat so Tivit still attacks. And Tivit is cast from the COMMAND ZONE, which is not the hand, so the static puts two counters on it every time it enters.',
        implement="DONE 2026-09-29. `tivit.walker_step` takes the +1 on Tivit after Time Sieve, and `end_step` returns it through `blink_tivit` (a dilemma); `venser_counters` sets Tivit's counters to two on every blink and on the cast. BLIND: the -2 bounces opponents' permanents, which are a count here (§4), and is never taken. FLOOR: the +1 with Tivit absent blinks nothing (other ETB creatures are not tried), and Magister of Worth's returns do not get the counters. Classify PARTLY_MODELLED at staging.",
        triage="LIVE",
        rejected="MEASURED 2026-09-29 and PROMOTED: the real swap against Tamiyo's Journal is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.",
    ),
    Proposal(
        deck='tivit', card='Dyfed, the Guiding Hand', cost='{3}{U}{U}',
        identity='U', type_line='Legendary Planeswalker — Dyfed',
        oracle='+1: Create two tapped Powerstone tokens. (They\'re artifacts with "{T}: Add {C}. This mana can\'t be spent to cast a nonartifact spell.")\n−X: Untap X target artifacts.\n−6: Search your library for an artifact card, put it onto the battlefield, then shuffle.\nDyfed, the Guiding Hand can be your commander.',
        verified="2026-09-29",
        rationale="TWO ARTIFACT TOKENS A TURN in the deck whose engine counts artifacts: Time Sieve's fuel, Marionette Master's and Disciple of the Vault's triggers, Mirkwood Bats on creation. The -X untaps a spent Time Sieve -- a second extra turn -- and the -6 fetches it.",
        implement="DONE 2026-09-29. Powerstones are a pile in `g.tokens` (so `artifact_count`, Cyberdrive and Time Sieve see them) but NOT in TOKEN_KINDS (Academy Manufactor's replacement does not make them). Their mana is offered only to artifact spells and activated abilities (`mana_units(g, powerstones=True)`), and they untap each turn. Anointed Procession doubles them -- the THIRD token path, said here as in the other two (§0z4). Policy: -1 to untap a tapped Time Sieve when five more artifacts can pay; -6 for Time Sieve (else the best artifact) when it is in neither play nor hand; +1 otherwise. FLOOR: untapping anything but the Sieve is not modelled. Classify SCRIPTED at staging.",
        triage="LIVE",
        rejected="MEASURED 2026-09-29 and PROMOTED: the real swap against Tamiyo's Journal is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.",
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
        deck='tivit', card='Treasure Vault',
        cost='', identity='',
        type_line='Artifact Land',
        oracle='{T}: Add {C}.\n{X}{X}, {T}, Sacrifice this land: Create X Treasure tokens.',
        verified='2026-10-06',
        rationale='Tivit wins through Treasures (Revel in Riches at ten, Mechanized Production at eight) and counts artifacts for Time Sieve; a land that becomes X Treasures and is an artifact land itself.',
        implement="New in tivit: end step on leftover mana, {X}{X}, {T}, sacrifice: X Treasures through tivit's own `make_token`, the rendmaw Vault policy (§0z68). An artifact land (`artifact_land` tag).",
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='tivit', card="Urza's Saga",
        cost='', identity='',
        type_line="Enchantment Land — Urza's Saga",
        oracle='(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)\nI — This Saga gains "{T}: Add {C}."\nII — This Saga gains "{2}, {T}: Create a 0/0 colorless Construct artifact creature token with \'This token gets +1/+1 for each artifact you control.\'"\nIII — Search your library for an artifact card with mana cost {0} or {1}, put it onto the battlefield, then shuffle.',
        verified='2026-10-06',
        rationale='A Construct gets +1/+1 for each artifact you control, and tivit controls fifty a game; chapter III tutors a {0}/{1} artifact (Sol Ring).',
        implement="LARGE: lore counters after the draw step, a chapter-II activation, a 0/0 Construct whose power is an artifact count, a chapter-III tutor and the Saga's sacrifice. tivit has saga lore (§0z83). Likely DEFERRED behind the others.",
        triage='DEFERRED',
        triage_note=('Needs Saga lore counters added after the draw step, a chapter-II activation creating a 0/0 Construct whose power counts artifacts, a chapter-III tutor for a {0}/{1} artifact, and the sacrifice after III. tivit has saga lore (§0z83) but none of the rest; measured after the cheaper lands.'),
    ),
    # STAR TREK, 2026-10-23 (the owner's set review). Oracle text from
    # api.scryfall.com the same day.
    Proposal(
        deck='tivit', card='Mr. Spock, Science Officer', cost='{2}{U}{U}',
        identity='U', type_line='Legendary Creature — Vulcan Human Scientist',
        oracle='If you would draw a card, draw two cards instead.',
        verified='2026-10-23',
        rationale="Every Clue Tivit's evidence votes make, Rhystic Study, Messenger Jays, Memnarch and the draw step all draw double. Card flow is what tivit's priority sweep said it wanted (§0z43: card draw above its token engines).",
        implement="TivitGame.draw: each card drawn is two while Spock is out (a replacement, so the draw step too); `spock_extra_draws`. DECKING IS REAL: the doubled mandatory draws can deck you and `drew_from_empty` charges it. tivit's optional draws (cracking a Clue, Rhystic Study) do not consult `draw_is_safe` today; with Spock out they do, at the doubled count (§0z42). Knob `spock_text`.",
        triage='LIVE',
    ),
]


# Added 2026-09-05 as a fourth deck. Nothing is staged yet: the list is the
# one in Tivit_Seller_of_Secrets_Commander_Deck_v1.xlsx, card for card.
CATALOG = (tivit_v1, {
    # 2026-09-16 batch (§0z26).
    "Anointed Procession": tivit_v1.ANOINTED_PROCESSION,
    "Urza, Lord High Artificer": tivit_v1.URZA_LORD_HIGH_ARTIFICER,
    "Sai, Master Thopterist": tivit_v1.SAI_MASTER_THOPTERIST,
    # REALITY FRACTURE, 2026-09-21 (preview text).
    "Memnarch, the Warden": tivit_v1.MEMNARCH_THE_WARDEN,
    # MYSTERY BOOSTER COMMANDER EDITION, 2026-09-29 (§0z74).
    "Venser, Visionary Traveler": tivit_v1.VENSER_VISIONARY_TRAVELER,
    "Dyfed, the Guiding Hand": tivit_v1.DYFED_THE_GUIDING_HAND,
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    "Treasure Vault": tivit_v1.TREASURE_VAULT,
    # STAR TREK, 2026-10-23 (the owner's set review).
    "Mr. Spock, Science Officer": tivit_v1.MR_SPOCK})
