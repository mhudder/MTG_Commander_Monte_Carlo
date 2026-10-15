"""shilgengar's ledger entries and swap-in catalog.

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

from edhmc.decks import shilgengar_v1
from edhmc.ledger.records import Change, Candidate, Simulated, Proposal


COMMITTED: list[Change] = []


MEASURED: list[Candidate] = [
    # MYSTERY BOOSTER COMMANDER EDITION, measured 2026-09-29 (§0z74).
    Candidate(
        deck='shilgengar',
        card='Selenia, the Cursed Heart',
        measured='2026-09-29',
        win_rate='REAL SWAP -Skullclamp +Selenia, the Cursed Heart, N=15,000 paired: +0.0015 +-0.0007 (significant) at T10 and +0.0206 +-0.0031 (significant) at T20.',
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. The largest shilgengar number of the batch after Pearl Collector, and the mechanism is the one argued: 0.10 curses a game at T20 (she is fed to Shilgengar or dies), +3.8 life from the doubler, +0.21 Blood.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits="FLOOR: Blood Artist / Zulaport / Vampiric Rites gains bypass gain_life, so the doubler misses them (§0z74). The cut Skullclamp is -0.0008 +-0.0013 in the table, inside its bar, so this swap is close to the card's own value.",
        verdict="Significant at both horizons and large at T20. A real candidate; the owner's call.",
    ),
    Candidate(
        deck='shilgengar',
        card='Seluma, Light of Aysen',
        measured='2026-09-29',
        win_rate='REAL SWAP -Skullclamp +Seluma, Light of Aysen, N=15,000 paired: +0.0007 +-0.0005 (significant) at T10 and +0.0091 +-0.0024 (significant) at T20.',
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 0.38 connections a game at T20 but only 0.059 Angels returned: the commander's mass reanimation keeps the graveyard empty of Angels, so most of the value is a 4/4 flier.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='The Rulebreaker clause is dead in the 99. Returns are rare for a reason the deck causes, not a defect.',
        verdict="Significant at both horizons, but a third of Selenia's or Pearl Collector's number in the same slot.",
    ),
    Candidate(
        deck='shilgengar',
        card='Thomil, the Destroyer',
        measured='2026-09-29',
        win_rate='REAL SWAP -Skullclamp +Thomil, the Destroyer, N=15,000 paired: +0.0003 +-0.0004 (inside its bar) at T10 and +0.0074 +-0.0024 (significant) at T20.',
        signal='win',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. 0.42 Zombies and 0.22 Lords a game at T20; the Lord's upkeep eats 0.36 creatures and deals 0.024 damage to you when it cannot.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits="FLOOR: the 0 ability is not modelled (the Lord's trample is since §0z92), and no opponent attacks a planeswalker (§4), so loyalty only rises.",
        verdict='T20 only; inside its bar at T10. A long-horizon card.',
    ),
    Candidate(
        deck='shilgengar',
        card='Pearl Collector',
        measured='2026-09-29',
        win_rate='REAL SWAP -Skullclamp +Pearl Collector, N=15,000 paired: +0.0012 +-0.0006 (significant) at T10 and +0.0229 +-0.0029 (significant) at T20.',
        signal='both',
        rationale="Mystery Booster Commander Edition (§0z74): implemented, pinned (tests/test_mbc.py) and measured 2026-09-29 against the deck's weakest MODEL-EVALUATED row. The largest number in the batch: +6.6 life a game at T20, 0.16 Mox Pearls and 0.31 perpetual-lifelink grants -- the sink is most of it, because this deck is full of big fliers.",
        evidence='results/mbc_batch.txt (diagnostics/run_mbc.py); smoke in results/mbc_smoke.txt',
        limits='PARTLY: deathtouch not modelled. Life-gained-this-turn misses the direct your_life writes named in §0z74.',
        verdict='Significant at both horizons, the strongest of the twelve at T20.',
    ),
    Candidate(
        deck='shilgengar',
        card='Lyra, Archangel of Dawn',
        measured='2026-09-21',
        win_rate=('REAL SWAP -Vampiric Rites +Lyra, Archangel of Dawn, N=15,000 paired:'
            ' +0.0025 +-0.0008 at T10 and +0.0121 +-0.0028 at T20, significant at'
            ' both; damage T20 +1.83 +-0.15.'),
        signal='both',
        rationale=('A Reality Fracture card (preview text; the set releases 2026-10-02),'
            ' implemented, pinned and measured in 2026-09-20/21. Recorded here on'
            ' 2026-09-25 because until then its number lived only in results/*.tx'
            "t -- the 'number with nobody's decision attached' this class exists "
            'to prevent.'),
        evidence='results/fra_batch2.txt (diagnostics/run_fra_batch2.py)',
        limits=('The only batch-2 cut that is genuinely negative: Vampiric Rites -0.0'
            '014 +-0.0011, signal both. CURRENT. The baseline has NOT moved since'
            ' this was measured: check_unchanged_decks 246b148 vs 2026-09-25 is B'
            'IT-IDENTICAL on all 8 metrics for this deck, which has no staged cha'
            'nges, so the module IS the measured list. This number describes the '
            'list as it is today.'),
        verdict=('Significant at both horizons against a cut whose own row is evidence'
            ', and CURRENT -- the cleanest of the eight. No rival has been measur'
            'ed for that slot. STAGED BY THE OWNER 2026-09-26 (§0z69): see CHANGES.'),
    ),
    Candidate(
        deck='shilgengar',
        card='Scoured Barrens',
        measured="2026-10-06",
        win_rate='-0.0001 +-0.0005 at T10, +0.0005 +-0.0019 at T20 against a Plains',
        signal='--',
        rationale="A tapped W/B dual that gains 1, through Shilgengar's `gain_life`.",
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Plains. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: land_lifegain +0.206, life_gained +0.211, lifegain_triggers +0.205. §0z113.',
        limits='Every clause modelled (the land hook is new, §0z113).',
        verdict='A blank.',
    ),
    Candidate(
        deck='shilgengar',
        card='Ancient Tomb',
        measured="2026-10-06",
        win_rate='+0.0012 +-0.0007 at T10, -0.0002 +-0.0028 at T20 against a Swamp',
        signal='--',
        rationale='{C}{C} from a land, for 2 damage a tap.',
        evidence='N=15,000 paired, seeds 5000.., staged list, one T20 game per seed with T10 read off it; the candidate in place of one Swamp. diagnostics/run_land_candidates.py, results/land_candidates_20261006.txt. Counters a game: life_gained -0.038, life_lost_to_own_cards +1.544, lifegain_triggers -0.020, tomb_damage +1.544. §0z113.',
        limits='Every clause modelled; 1.5 damage a game.',
        verdict='+0.0012 at T10 (significant, tiny) and nothing at T20. A blank in practice. OWNER DEFERRED 2026-10-06: a valid card, but outside the price range of the casual table the owner plays at -- a judgement about the table, not about the number.',
    ),
]


CHANGES: list[Change] = [
    # The owner's decision of 2026-09-26 (§0z69), re-measured the same day
    # on the engine it will be rebuilt on. Its sibling, -Blasphemous Act
    # +Goldspan Dragon, was WITHDRAWN 2026-10-05 (§0z105): see WITHDRAWN.
    Change(
        deck="shilgengar", remove="Vampiric Rites", add="Lyra, Archangel of Dawn",
        staged="2026-09-26",
        rationale=(
            "Measured 2026-09-21 in the Reality Fracture batch and recorded as "
            "the cleanest of its eight: significant at both horizons against a "
            "cut whose own row is genuinely negative. The owner staged it."),
        evidence=(
            "RE-MEASURED 2026-09-26 on the final §0z67 engine, N=15,000 "
            "paired: +0.0026 +-0.0008 at T10, +0.0123 +-0.0027 at T20 (the "
            "same on the engine without the aim). "
            "results/aim_vault_swaps_20260926.txt. First measured +0.0025 / "
            "+0.0121 (results/fra_batch2.txt)."),
        notes=(
            "PREVIEW TEXT. Lyra is a Reality Fracture card and the set "
            "releases 2026-10-02; the card was implemented from preview text. "
            "Re-fetch its oracle text from Scryfall on release, and re-measure "
            "if a word has changed, BEFORE this is committed."),
        reverified="RE-MEASURED 2026-10-15 ON POD_V4 (§0z140, queue item 26), in context, N=15,000 paired, python 3.13: +0.0042 +-0.0012 at T10, +0.0094 +-0.0032 at T20. Significant at both; the staging stands. The pod alone moved it -0.0001 +-0.0012 at T10 and -0.0052 +-0.0041 at T20 (POD_PRE_V4 at the same commit: +0.0043 / +0.0146). results/restage_item26_20261015.txt (§0z143)." + 'RE-MEASURED 2026-10-07 on the §0z118 engine (bd9e7ae, python 3.13), in context, N=15,000 paired: +0.0029 +-0.0009 at T10, +0.0141 +-0.0028 at T20. Significant at both; the staging stands. results/restage_20261007.txt. ' + "RE-MEASURED 2026-09-29 on the engine after §0z75-§0z80 (death look-back, finality, lifegain routing, Goldspan's target Treasure), N=15,000 paired, in context: +0.0026 +-0.0008 at T10, +0.0124 +-0.0028 at T20. Within its bar of the last measurement; the staging stands. results/restage_20260929.txt (§0z81).",
    ),
]


WITHDRAWN: list[Change] = []


SIMULATED: list[Simulated] = [
    Simulated(
        deck='shilgengar', remove='Skullclamp', add='Selenia, the Cursed Heart',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Skullclamp +Selenia, the Cursed Heart, N=15,000 paired: +0.0015 +-0.0007 (significant) at T10 and +0.0206 +-0.0031 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0015 +-0.0007 * at T10 and +0.0214 +-0.0031 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='shilgengar', remove='Skullclamp', add='Seluma, Light of Aysen',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Skullclamp +Seluma, Light of Aysen, N=15,000 paired: +0.0007 +-0.0005 (significant) at T10 and +0.0091 +-0.0024 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0006 +-0.0006 at T10 and +0.0087 +-0.0025 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='shilgengar', remove='Skullclamp', add='Thomil, the Destroyer',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Skullclamp +Thomil, the Destroyer, N=15,000 paired: +0.0003 +-0.0004 (inside its bar) at T10 and +0.0074 +-0.0024 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0002 +-0.0004 at T10 and +0.0078 +-0.0025 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
    Simulated(
        deck='shilgengar', remove='Skullclamp', add='Pearl Collector',
        measured='2026-09-29', source='results/mbc_batch.txt',
        result=('REAL SWAP -Skullclamp +Pearl Collector, N=15,000 paired: +0.0012 +-0.0006 (significant) at T10 and +0.0229 +-0.0029 (significant) at T20.'),
        notes=('RE-MEASURED 2026-09-29 on the engine after §0z75-§0z77, same cut and seeds: +0.0012 +-0.0006 * at T10 and +0.0230 +-0.0030 * at T20 (results/mbc_batch_20260929.txt). The row above is §0z74\'s.'),
    ),
]


PROPOSED: list[Proposal] = [
    # -----------------------------------------------------------------------
    # MYSTERY BOOSTER COMMANDER EDITION (Scryfall `mbc`), scanned 2026-09-29.
    # 80 cards; the set releases 2026-11-09 and every NEW card in it reads
    # `not_legal` in Commander on Scryfall (59 are legal in no format, ten only
    # in digital ones). THE OWNER'S TABLE PLAYS THEM (2026-09-29), which is a
    # decision about the table and not about the rules -- the same standing
    # the Reality Fracture previews had. Nine cards, twelve deck pairs, all
    # implemented and pinned on the day. §0z74.
    # -----------------------------------------------------------------------
    Proposal(
        deck='shilgengar', card='Selenia, the Cursed Heart', cost='{4}{W}{B}',
        identity='WB', type_line='Legendary Creature — Angel Warrior',
        oracle='Flying, lifelink\nIf you would gain life, you gain twice that much life instead.\nWhen Selenia dies, create a legendary black Aura Curse enchantment token named Selenia\'s Curse attached to target opponent. The token has enchant player and "If enchanted player would lose life, they lose twice that much life instead."',
        verified="2026-09-29",
        rationale="AN ANGEL WITH TOUGHNESS 5, in the deck whose commander turns an Angel's toughness into Blood: fed to Shilgengar she is five of the six Blood the mass reanimation needs, and her death is the curse, which doubles every point one opponent loses for the rest of the game. Her lifegain doubler feeds Resplendent Angel's five-life threshold and Speaker of the Heavens'. The ultimate returns her with a finality counter, so she curses once.",
        implement='DONE 2026-09-29. Modelled: flying (generated), lifelink, the doubler in `ShilgengarGame.gain_life` (amount, not events), and the curse through `opponents.curse_opponent` / `life_loss` -- one function read at every site an opponent loses life, so combat, drains and Massacre Wurm all double. The death trigger honours FINALITY (a returned Selenia is exiled, not killed). PARTLY: Blood Artist, Zulaport Cutthroat and Vampiric Rites write `your_life` directly instead of calling `gain_life`, so their gains are not doubled -- a pre-existing gap in this engine, named in §0z74. Classify SCRIPTED at staging. Pinned by tests/test_mbc.py.',
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Skullclamp is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='shilgengar', card='Seluma, Light of Aysen', cost='{4}{W}',
        identity='W', type_line='Legendary Creature — Angel Warrior',
        oracle='Rulebreaker — A deck with this commander can have Angel cards of any color identity and any basic land cards.\nFlying\nWhenever Seluma deals combat damage to a player, return target Angel creature card from your graveyard to the battlefield.',
        verified="2026-09-29",
        rationale="A 4/4 FLYING ANGEL whose combat damage is a reanimation -- the deck's recursion plan on an evasive body, and four Blood when it is fed to Shilgengar. It is also the commander of the owner's other list (spreadsheets/Seluma_Commander_Deck_v1.xlsx), so knowing what the body is worth in the 99 is worth knowing.",
        implement="DONE 2026-09-29. `opponents.combat_damage` now reports the attackers that CONNECTED to an engine that asks (`g.combat_hits`, §0z74) -- shilgengar asks, the other five do not and cannot move -- and each connecting Seluma returns the highest-MV Angel card from `yard_creatures()` (finality respected, pool recomputed per trigger). The RULEBREAKER clause works only in the command zone and is DEAD in the 99. SMOKE FOUND A BUG FIRST: before `tag_flying --write` Seluma attacked as a ground creature and connected on 12% of attacks (§0z29's shape); flying, it connects 0.35 times a game. Its returns are rare (0.035/game) because the commander's mass reanimation keeps the graveyard empty of Angels -- a real interaction, not a defect. Classify SCRIPTED at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Skullclamp is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='shilgengar', card='Thomil, the Destroyer', cost='{3}{B}{B}',
        identity='B', type_line='Legendary Planeswalker — Thomil',
        oracle='+2: Create a 2/2 black Zombie creature token.\n0: You may sacrifice a creature. If you do, add {B}{B}{B}.\n−5: Create a Lord of the Pit token. (It\'s a {4}{B}{B}{B} 7/7 Demon creature with flying, trample, and "At the beginning of your upkeep, sacrifice another creature. If you can\'t, this token deals 7 damage to you.")\nThomil, the Destroyer can be your commander.',
        verified="2026-09-29",
        rationale="A walker that makes a 2/2 body every turn and, once, a 7/7 flying trampler -- in the deck that already wants bodies to sacrifice for Blood, and whose aristocrats triggers see every death Lord of the Pit's upkeep forces.",
        implement="DONE 2026-09-29. `engine.thomil_step` (shared with rendmaw): +2 Zombie until loyalty and board allow the -5, then Lord of the Pit, whose mandatory upkeep sacrifice is `engine.lord_of_the_pit_upkeep` through the engine's own `sacrifice`. Loyalty from `engine.PLANESWALKER_LOYALTY`, azusa's convention. FLOOR: the 0 (sacrifice a creature, add {B}{B}{B}) is not taken, and Lord of the Pit's TRAMPLE was not modelled when this was written (it is since §0z92). No opponent attacks a planeswalker here (§4, azusa's note), so loyalty only goes up. Classify PARTLY_MODELLED ('the 0 and trample are not modelled') at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Skullclamp is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='shilgengar', card='Pearl Collector', cost='{2}{B}',
        identity='WB', type_line='Creature — Human Warlock',
        oracle='Deathtouch, Lifelink\nAt the beginning of your second main phase, if you gained 4 or more life this turn, conjure a card named Mox Pearl into your hand. This ability triggers only once.\n{2}{W}: Another target creature perpetually gains lifelink.',
        verified="2026-09-29",
        rationale="A three-mana lifelink body that turns a four-life turn into a free Mox and spends spare mana on permanent lifelink -- every lifelink attacker is a lifegain event for Righteous Valkyrie's threshold and Lyra's counters.",
        implement="DONE 2026-09-29. Lifelink on the body; `engine.pearl_collector_trigger` at the start of the postcombat main (once per object, reading `life_gained_this_turn`) conjures a fresh Mox Pearl card; `engine.pearl_collector_lifelink` is the {2}{W} sink, run after the second main phase so it only spends what nothing else wanted, keyed on the CARD's id because 'perpetually' follows the card. PARTLY: DEATHTOUCH is not modelled -- the pod's blocking is a chump count and this engine never blocks. The life-gained-this-turn count misses the direct `your_life` writes named under Selenia. Classify PARTLY_MODELLED at staging.",
        triage="LIVE",
        rejected='MEASURED 2026-09-29 and PROMOTED: the real swap against Skullclamp is a Candidate in MEASURED (§0z74). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='shilgengar', card='Scoured Barrens',
        cost='', identity='BW',
        type_line='Land',
        oracle='This land enters tapped.\nWhen this land enters, you gain 1 life.\n{T}: Add {W} or {B}.',
        verified='2026-10-06',
        rationale='Shilgengar routes lifegain through its finality and Blood counters (§0z75-§0z80); a tapped dual that gains 1.',
        implement="Fields only, if shilgengar's land path reads `lifegain` (to be checked by the twin test); otherwise one line in its land ETB.",
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
    Proposal(
        deck='shilgengar', card='Ancient Tomb',
        cost='', identity='',
        type_line='Land',
        oracle='{T}: Add {C}{C}. This land deals 2 damage to you.',
        verified='2026-10-06',
        rationale="Shilgengar's Angels cost six and seven; two mana from a land drop.",
        implement='The shared Ancient Tomb implementation.',
        triage='LIVE',
        rejected='MEASURED 2026-10-06 and PROMOTED: the Candidate in MEASURED carries the number (§0z113). Closed rather than deleted so the verified oracle text stays where it was written.',
    ),
]


# Added 2026-09-07 as a fifth deck. Nothing is staged yet: the list is the
# one in Shilgengar_Sire_of_Famine_Commander_Deck_v1.xlsx, card for card,
# six mana values corrected against Scryfall (see shilgengar_v1.py's
# module docstring). This deck has not been through ablation yet.
CATALOG = (shilgengar_v1, {
    # REALITY FRACTURE, 2026-09-21 (preview text). The first swap-in
    # candidate this deck has ever had catalogued.
    "Lyra, Archangel of Dawn": shilgengar_v1.LYRA_ARCHANGEL_OF_DAWN,
    # MYSTERY BOOSTER COMMANDER EDITION, 2026-09-29 (§0z74).
    "Selenia, the Cursed Heart": shilgengar_v1.SELENIA_THE_CURSED_HEART,
    "Seluma, Light of Aysen": shilgengar_v1.SELUMA_LIGHT_OF_AYSEN,
    "Thomil, the Destroyer": shilgengar_v1.THOMIL_THE_DESTROYER,
    "Pearl Collector": shilgengar_v1.PEARL_COLLECTOR,
    # LAND CANDIDATES, 2026-10-06 (§0z113).
    "Scoured Barrens": shilgengar_v1.SCOURED_BARRENS,
    "Ancient Tomb": shilgengar_v1.ANCIENT_TOMB})
