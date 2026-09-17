#!/usr/bin/env python3
"""Record what code each committed ablation cache was produced by.

WHY THIS EXISTS. `ablation.py` keys its cache on deck, horizons and N -- NOT on
the version of the code that produced it. That is a documented hazard in this
repo: a full cache means `todo` is empty and the run silently REPRINTS OLD
NUMBERS instead of measuring anything. While the caches were gitignored the
hazard was bounded, because a fresh clone had no cache to go stale. Committing
them removes that safety net, so the provenance has to be written down.

The fingerprint is a hash of the SOURCE FILES that can change a simulation
result. If it differs from the value recorded here, the cache is stale for that
deck and must be deleted before resuming -- `./regen_tables.sh` does that by
default.

    python cache_manifest.py            # print the current state
    python cache_manifest.py --write    # regenerate ABLATION_CACHES.md
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import sys

from edhmc.registry import DECKS

OUT = "docs/ABLATION_CACHES.md"
CACHE_DIR = os.path.join("results", "caches")

# The modules whose behaviour a cached number depends on. opponents.py and
# experiment.py are shared, so a change to either invalidates every deck.
# decks/_evasion.py is GENERATED and shared: it is where every Card gets its
# `flying` and `indestructible`, so regenerating it changes combat for any
# deck whose cards gained a tag. It was NOT here until 2026-09-17, when a
# regeneration gave Bloodthirsty Conqueror the flying it had always had and
# no fingerprint moved (§0z29) -- a behaviour change the provenance scheme
# could not see.
SHARED = ["edhmc/opponents.py", "edhmc/experiment.py", "edhmc/engine.py",
          "edhmc/decks/_evasion.py", "ablation.py"]

# Files that have MOVED on disk since the fingerprint scheme was introduced,
# keyed by the name the hash still uses. `fingerprint()` hashes the KEY as well
# as the content, so without this the 2026-09-09 reorganisation would have
# marked all fourteen caches stale without one measured number changing --
# which is the same "a check that cries wolf is worse than no check" failure
# the newline normalisation below exists to prevent. A rename is not a
# behaviour change, and the fingerprint must not claim it is.
MOVED = {"ablation.py": os.path.join("tools", "ablation.py")}
# Derived from edhmc/registry.py (§0z32): the engine file, its extras
# (voting.py for tivit) and the CURRENT deck module, spelt exactly as this
# dict used to type them, so deriving them moved no fingerprint. A new deck
# version (`karlov_v3.py`) changes its fingerprint by construction, which is
# right: the cache was measured on the list the old module built.
PER_DECK = {name: spec.fingerprint_files for name, spec in DECKS.items()}
# engine.py is Rendmaw's engine AND the shared primitives, so it is in SHARED
# and does not repeat under rendmaw.

# Hand-recorded, because it is a fact about how a run was performed rather than
# about the files. Keep it honest: say when a cache was resumed across a code
# change and why that was safe.
#
# KEYED BY CACHE FILE NAME, not by deck. A deck can have more than one live
# cache -- the same list measured at two sample sizes -- and their provenance is
# NOT the same fact. Keying this by deck printed one note under two headings,
# which is precisely the "a label that is not checked is a claim" failure the
# SCRIPTED_* sets have already produced twice in this repo. A bare deck name is
# still accepted as a fallback so an unrecorded cache degrades to the deck's
# note rather than to nothing.
_REGEN_2026_09_06 = (
    " RE-DERIVED FROM AN EMPTY CACHE 2026-09-06 under the runtime work "
    "(indexed battlefield, shared baseline, parallel cards) and reproduced "
    "this file BIT FOR BIT -- every value, and the printed table byte for "
    "byte. The fingerprint below moved because those files changed; the "
    "numbers did not. That re-derivation IS the evidence, which is why it was "
    "done on all four decks rather than argued from the diff.")

NOTES = {
    "ablation_cache_lorehold_10-20_n6000.json": (
        "Regenerated 2026-09-05 for the deck change (-Penance +Caldera "
        "Pyremaw). RESUMED ACROSS commit 1710205 at 19/65 cards. That commit "
        "changed engine.attack_triggers, make_everywhere and "
        "karlov.creature_entered -- none of which lorehold.py can reach: it "
        "has its own combat() and imports only Card, Permanent, can_pay, "
        "available_mana, spend and play_land. Verified empirically at the "
        "time: the Lorehold validate.py baseline was unchanged at "
        "mv_cheated 23.26 / miracles 3.01 / damage 59.72."
        + _REGEN_2026_09_06 +
        " The resume above is therefore no longer load-bearing: this cache "
        "now has a from-empty provenance on one version of the code."),
    "ablation_cache_rendmaw_10-20_n6000.json": (
        "Regenerated from an EMPTY cache 2026-09-05 after commit 1710205, so "
        "it carries the Grist fix, the 'enters or attacks' triggers and "
        "Overlord's tapped token. No resume across a code change."
        + _REGEN_2026_09_06),
    "ablation_cache_karlov_10-20_n6000.json": (
        "Regenerated from an EMPTY cache 2026-09-05 after commit 1710205, so "
        "it carries the 'another creature you control' fix. No resume across "
        "a code change."
        + _REGEN_2026_09_06),
    "ablation_cache_tivit_10-20_n2000.json": (
        "First table for this deck, 2026-09-05, after the Cyberdrive Awakener "
        "ETB fix (6d40609). N=2000 rather than 6000 -- noise floor ~0.015 win "
        "rate, NOT comparable row-for-row with the other three."
        + _REGEN_2026_09_06 +
        " SUPERSEDED 2026-09-06 by the n15000 cache; kept because it is the "
        "provenance for every tivit number quoted before that date."),
}

# The N=15000 tables, 2026-09-06. Same code, same seeds, more of them.
_N15000 = (
    "Measured from an EMPTY cache 2026-09-06 on the same code as the n{old} "
    "cache above -- no engine or deck change, only sample size. Seeds "
    "5000..19999, so the first {old} pairs ARE the previous cache's games and "
    "the difference is the {extra} added on the end. The observed CI ratio is "
    "{ratio}, against 1/sqrt(N) predicting {pred}: the variance is clean and "
    "there is no floor underneath it. NO CARD THAT WAS ALREADY SIGNIFICANT ON "
    "WIN RATE CHANGED SIGN, in any of the four decks, which is the check that "
    "matters -- it says the smaller tables were not reporting noise as "
    "findings. This is the current table.")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000.json":
        _N15000.format(old=old, extra=15000 - old, ratio=ratio, pred=pred)
        + " SUPERSEDED the same day by the _medblank cache: it was measured "
          "against the OLD ablation blank (priority 0.5). Kept as the "
          "provenance for every number quoted from it, and NOT resumable -- "
          "the cache key now carries the blank mode for that reason."
    for d, old, ratio, pred in (
        ("karlov", 6000, "0.64", "0.63"),
        ("rendmaw", 6000, "0.64", "0.63"),
        ("lorehold", 6000, "0.63", "0.63"),
        ("tivit", 2000, "0.39", "0.37"),
    )
})

# The 2026-09-06 Erebos and extra-turn work changed engine.py, which is in
# SHARED, so ALL FOUR fingerprints moved. Only two decks' numbers did, and that
# was checked rather than argued: karlov.py and lorehold.py have their own Game
# classes and import only Board, Card, Permanent, can_pay, available_mana, spend
# and play_land from engine.py -- none of which was touched. The check was a
# worktree at the previous commit running the same baselines on the same seeds.
_KARLOV_LOREHOLD_UNTOUCHED = (
    " STILL CURRENT after the 2026-09-06 Erebos and extra-turn work "
    "(KNOWN_ISSUES.md 0l, 0m), which changed engine.py and therefore moved "
    "this fingerprint. The numbers did not move: this engine has its own Game "
    "class and imports only the mana and card primitives from engine.py, none "
    "of which changed. VERIFIED, not argued -- a git worktree at the previous "
    "commit ran this deck's baseline on the same seeds at both horizons and "
    "every metric was BIT-IDENTICAL. Two decks failed that check (rendmaw and "
    "tivit) and were regenerated, which is what makes the pass meaningful.")

_LOREHOLD_SUNBIRD_COUNTER = (
    " The lorehold fingerprint moved a SECOND time on 2026-09-06, for the "
    "`sunbird_triggers` counter added while closing queued item 0b "
    "(KNOWN_ISSUES.md 0p): the ledger justified Sunbird's Invocation with a "
    "CONDITIONAL firing rate printed as an unconditional one, and separating "
    "triggers from successful free casts is what showed it. METRIC ONLY -- one "
    "dict key and one increment, no branch reads it -- and checked the same way: "
    "all four decks' baselines bit-identical across the change. Cache current.")

# The blank fix, 2026-09-06 (second regeneration of the day).
_MEDBLANK = (
    "CURRENT TABLE. Measured from an EMPTY cache 2026-09-06 after the ablation "
    "BLANK was fixed: it was built at priority 0.5, below the minimum priority "
    "of every deck, so `main_phase` -- which is greedy on priority -- cast it "
    "only when nothing else was affordable. That is a dead card, not a "
    "replacement-level one, and the tempo difference was charged to whichever "
    "card was under test. The blank is now cast at the deck's median nonland "
    "priority ({prio}) via experiment.repl_priority(). threat and the 1/1 body "
    "are deliberately unchanged -- see KNOWN_ISSUES.md 0j for why those are "
    "NOT the same bug. Scores rise almost everywhere, which is the expected "
    "direction: the blank now costs mana, so the blanked deck is worse. "
    "52 of 256 cards moved by more than their own old CI half-width.{extra}")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        _MEDBLANK.format(prio=prio, extra=extra)
    for d, prio, extra in (
        ("karlov", "7.0", _KARLOV_LOREHOLD_UNTOUCHED),
        ("lorehold", "5.0",
         _KARLOV_LOREHOLD_UNTOUCHED + _LOREHOLD_SUNBIRD_COUNTER),
        ("rendmaw", "5.0",
         " REGENERATED AGAIN FROM AN EMPTY CACHE 2026-09-06 (third time that "
         "day) for the EREBOS correction, KNOWN_ISSUES.md 0l: Erebos, "
         "Bleak-Hearted was a creature on the battlefield regardless of "
         "devotion to black, it had been given Dockside Chef's activated "
         "ability instead of its own death trigger, and it was never tagged "
         "indestructible. The deck's baseline win rate moves -0.0018 at T10, "
         "but ZERO of 64 cards moved by more than their own old CI half-width "
         "-- the only row that changed materially is Erebos's own (+0.0054 "
         "-> +0.0033 win, damage +0.61/+0.64 -> -0.18/+0.05, both -> FLIP). "
         "So this cache differs from the one before it almost entirely in one "
         "row, and that is the check that says the correction did not disturb "
         "the ranking."),
        ("tivit", "6.5",
         " ALSO carries the Ephemerate fix (KNOWN_ISSUES.md 0k): its handler "
         "was unreachable, so the card measured as an exact blank."
         " REGENERATED AGAIN FROM AN EMPTY CACHE 2026-09-06 (third time that "
         "day) for the EXTRA-TURN correction, KNOWN_ISSUES.md 0m: an extra "
         "turn ran the opponents' whole round at the end of it, extra turns "
         "generated during an extra turn were discarded, and Time Sieve "
         "activated up to ten times a turn when its cost is a tap of itself. "
         "Ten of 64 cards moved by more than their own old CI half-width and "
         "TIME SIEVE IS THE ONLY SIGN FLIP: -0.0025 +-0.0026 (`dmg`, "
         "negative) -> +0.0344 +-0.0034 (`both`), which makes it joint-best "
         "in the deck with Sol Ring rather than a cut candidate. Expropriate "
         "went from a proved blank (-0.0004 +-0.0008) to +0.0127 +-0.0022. "
         "The five drains all came DOWN slightly, which is arithmetic and not "
         "a finding: the deck's baseline win rate rose 0.343 -> 0.397, so any "
         "one card is a smaller share of it."),
    )
})

# 2026-09-07: the two new decks' FIRST tables. These are baselines, not
# regenerations -- there is no earlier table to compare them against, which is
# the one check the four older decks always have and these two do not.
NOTES.update({
    "ablation_cache_shilgengar_10-20_n15000_medblank.json": (
        "FIRST TABLE for this deck, 2026-09-07, measured from an empty cache "
        "at the common N=15000 so it is comparable row-for-row with the other "
        "five. Noise floor +-0.0019 win rate; baseline win rate 0.209 at T20. "
        "READ THE SACRIFICE ROWS WITH THE ENGINE'S POLICY IN MIND: "
        "`shilgengar.aristocrats_step` only ever sacrifices worthless 1/1 "
        "Spirit TOKENS, never a real card, so the whole aristocrats package "
        "(Blood Artist, Vampiric Rites, Viscera Seer, Skullclamp, Pitiless "
        "Plunderer) is measured with its engine deliberately starved -- it "
        "scores 0 to -0.0019 win rate, and that is a fact about the policy at "
        "least as much as about the cards. The commander's six-Blood "
        "reanimation ULTIMATE FIRED ZERO TIMES in 3,000 baseline games "
        "(blood_made averages 0.13 a game against the 6 it needs). "
        "Re-measured after `shilgengar_ultimate` was reordered to empty the "
        "graveyard before resolving ETB triggers, and the regenerated table "
        "is BYTE-IDENTICAL to the one before it, which is the evidence that "
        "the reorder was behaviour-neutral rather than the claim that it was."),
    "ablation_cache_azusa_10-20_n15000_medblank.json": (
        "FIRST TABLE for this deck, 2026-09-07, from an empty cache at the "
        "common N=15000. Noise floor +-0.0022 win rate; baseline win rate "
        "0.205 at T20. THE DAMAGE COLUMNS ARE UNUSABLE HERE and that is the "
        "first thing to know about this table -- Scute Swarm's landfall "
        "doubling gives this deck a damage distribution with a far heavier "
        "tail than any other, so the CIs run to +-278 against point estimates "
        "of the same order, and 13 rows carry a FLIP signal that is pure "
        "damage noise rather than a horizon effect. Win rate is an order of "
        "magnitude tighter and is the only column to read, exactly as it is "
        "for tivit. Measured AFTER the Genesis Wave crash fix: `wave()` "
        "removed cards from the library one at a time while `land_entered` "
        "could fire Seer's Sundial, which draws, which pops the library out "
        "from under the loop. The first full-size run died on it; the cards "
        "now all leave the library before any ETB resolves, which is also "
        "what the card actually does. "
        "SUPERSEDED THE SAME DAY by the land-sequencing rewrite -- that table "
        "is void and this note is kept as its provenance. See below."),
})

NOTES.update({
    "ablation_cache_azusa_10-20_n15000_medblank.json": (
        "CURRENT TABLE. Regenerated from an empty cache 2026-09-07 after the "
        "LAND-SEQUENCING REWRITE, which moved the deck's baseline win rate "
        "0.205 -> 0.279 at T20 and therefore voided the table measured hours "
        "earlier the same day. The engine had four defects in one place: "
        "land_step ran ONCE before any spell resolved, and picked lands with "
        "max(options, key=mv) -- a constant key, since every land has mana "
        "value 0, so it always took the first option and playable_lands "
        "builds the hand first. Lands are now chosen by ZONE (library -> "
        "graveyard -> hand), the enabler main phase runs before AND between "
        "land drops, a second land_step runs after combat, and a cracked "
        "fetch shuffles -- which makes the Crucible/Courser reroll line real. "
        "WHAT THIS DID TO THE RANKING: the ZONE enablers roughly doubled "
        "(Augur +0.0065 -> +0.0144, Oracle +0.0077 -> +0.0143, Ramunap "
        "Excavator +0.0074 -> +0.0131, Crucible +0.0060 -> +0.0101, Courser "
        "+0.0117 -> +0.0177) and Horn of Greed nearly doubled to +0.0289, "
        "while the drop-COUNT enablers did NOT move (Exploration +0.0021 -> "
        "+0.0023, still inside its bar; Wayward Swordtooth +0.0056 -> "
        "+0.0030). That half-retracts the earlier 'the payoffs beat the "
        "enablers' finding and replaces it with a sharper one: the deck is "
        "LAND-SUPPLY limited, not land-DROP limited -- it is granted 2.77 "
        "drops a turn and uses 1.33, and on 57.9% of turns it has an unused "
        "drop and no land anywhere it may legally play from. "
        "THE MID-GAME SHUFFLE DOES NOT BREAK CRN: its seeds are pre-rolled "
        "from a dedicated stream and indexed by shuffle count, so the Nth "
        "shuffle applies the same permutation in both branches. A/A is still "
        "+0.00 and a real swap still measures CRN at 6.5-24.7x."),
})


# 2026-09-07, LATER THE SAME DAY: both new decks' first tables turned out to be
# measuring a policy rather than a card, and both were regenerated. The notes
# above are kept as the provenance of the numbers quoted from them.
NOTES.update({
    "ablation_cache_shilgengar_10-20_n15000_medblank.json": (
        "CURRENT TABLE. Regenerated from an empty cache 2026-09-07 after the "
        "SACRIFICE POLICY FIX, KNOWN_ISSUES.md 0r. The engine would only ever "
        "sacrifice 1/1 Spirit tokens, and Spirit tokens only exist once an "
        "Angel has already died, so the commander's own ability was starved "
        "by construction: blood_made averaged 0.10 a game and the six-Blood "
        "ultimate FIRED ZERO TIMES IN 3,000 GAMES. It now feeds real Angels "
        "to the ability whenever that completes the ultimate in the same "
        "turn -- which is arithmetic and not a pilot's judgement call, "
        "because the ultimate returns the Angel it was paid with, so the "
        "sacrifice is a loan. Separately, main_phase now holds {3} back for "
        "the ability, which activations() runs after and could therefore "
        "never afford. Deck win rate 0.208 -> 0.242; the two halves are "
        "+0.0267 and +0.0075 and together +0.0343 +-0.0079. "
        "WHAT MOVED IN THE TABLE, which is the check that the fix is real: "
        "10 of 64 rows moved by more than their own OLD CI half-width and "
        "ZERO of the already-significant rows flipped sign. The movers are "
        "the cards whose text the mechanism reads -- Righteous Valkyrie "
        "(+0.0086 -> +0.0130, 2.0x its old bar) and Elesh Norn (+0.0059 -> "
        "+0.0083) because +2/+2 on an Angel is literally +2 Blood when you "
        "sacrifice it; Bishop of Wings (2.2x) and Requiem Angel because they "
        "make Spirit tokens off deaths that now happen; Blood Artist and "
        "Zulaport Cutthroat because their triggers now fire. Reya Dawnbringer "
        "went DOWN (+0.0074 -> +0.0045): she reanimates one creature a turn "
        "out of a graveyard the ultimate now empties, and finality counters "
        "keep what it returned out of her pool. "
        "NOT MOVED, and worth reading as a finding rather than an omission: "
        "the sac OUTLETS are still flat to negative (Viscera Seer -0.0005, "
        "Skullclamp -0.0013, Vampiric Rites -0.0016, Cartel Aristocrat "
        "+0.0011). The commander is the only sacrifice outlet this deck "
        "needs, so the redundant ones buy nothing -- which is a statement "
        "about the cards, where the old table's version of it was a "
        "statement about the policy."),
    "ablation_cache_azusa_10-20_n15000_medblank.json": (
        "CURRENT TABLE. Regenerated from an empty cache 2026-09-07 after the "
        "LAND-ANIMATION AND PLANESWALKER work, KNOWN_ISSUES.md 0s -- the "
        "SECOND regeneration of this deck that day, after the land-sequencing "
        "rewrite noted above. Four fixes: land animations are real continuous "
        "effects with the animated set captured AT RESOLUTION and per-card "
        "durations (Sylvan Awakening lasts until your next turn, so its lands "
        "block during the pod's round; Rude Awakening's mode and Nissa's +1 "
        "do not); an animated land that attacks is now TAPPED, so it cannot "
        "also pay for the postcombat main phase; Rude Awakening's animate "
        "mode and its entwine existed nowhere at all; and both Nissas had no "
        "activated abilities, Nissa Vastwood Seer never even transforming. "
        "THE RESULT IS THAT THE ANIMATION IS NEARLY A BLANK AND THE "
        "PLANESWALKERS ARE NOT: of the +0.0217 +-0.0071 total, "
        "+0.0210 +-0.0068 is the two Nissas and all three animation fixes "
        "together sit inside their own bars. That is now a measurement rather "
        "than an absence -- the animation is worth 9.24 marginal damage a "
        "game in a deck whose damage runs to the thousands, because Scute "
        "Swarm dwarfs it, while the Nissas are worth +1.29 landfall triggers "
        "and +0.36 lands played, which is what a CARD-limited deck actually "
        "wants. "
        "ALSO IN THIS CACHE, with no flag because it is unobservable unless a "
        "land is a creature: lands now enter summoning sick, so Dryad Arbor "
        "can no longer attack the turn it is played. And Nissa, Worldwaker "
        "MOVED FROM KNOWN_BLIND TO SCRIPTED_AZUSA -- her old entry read "
        "'nothing in this project tracks loyalty', which stopped being true. "
        "THE DAMAGE COLUMNS ARE STILL UNUSABLE for the reason the previous "
        "note gives; read win rate only."),
})

# 2026-09-08: three copies of "the miracle discount" had drifted apart.
NOTES.update({
    "ablation_cache_lorehold_10-20_n15000_medblank.json": (
        "CURRENT TABLE. Regenerated from an empty cache 2026-09-08 after "
        "KNOWN_ISSUES.md 0u: Ruby Medallion ('red spells cost {1} less') and "
        "Longshot, Rebel Bowman ('noncreature spells cost {1} less') were "
        "applied inconsistently across THREE separate copies of the miracle "
        "discount -- miracle_value (Molecule Man only), miracle_need (+ "
        "Artist's Talent), and miracle_window's real payment (+ Ruby "
        "Medallion) -- so Longshot never discounted a miracle at all despite "
        "every miracled card being noncreature by definition, and Ruby "
        "Medallion discounted the real payment but not the affordability "
        "gates that decide whether to attempt one. Consolidated into one "
        "function, miracle_reduction(g, card), that every consumer now "
        "reads; the two call sites with a specific card in scope (set_top, "
        "Library of Leng's redirect) pass it through, and Library of Leng's "
        "gate had to be REORDERED since it used to check affordability "
        "before the card it was checking against existed. "
        "MEASURED (run_miracle_reducer_fix.py, N=15,000, paired, same seeds, "
        "only the fix differs): miracles_cast +0.107 +-0.012, leng_to_top "
        "+0.024 +-0.007, leng_miracled +0.018 +-0.005, all significant; win "
        "rate -0.0012 +-0.0023, inside its bar. Both cards need to be drawn, "
        "kept on the battlefield AND match a specific card's colour or type "
        "at the moment a miracle is decided -- rare enough in a 99-card deck "
        "that the aggregate win rate cannot resolve it at this N even though "
        "the mechanism counters that fire on every relevant turn clearly "
        "can. "
        "ZERO OF 64 SHARED ROWS MOVED BY MORE THAN THEIR OWN OLD CI "
        "HALF-WIDTH, and zero already-significant rows flipped sign -- "
        "including Ruby Medallion's own (0.0009 -> 0.0007) and Longshot's "
        "(0.0205 -> 0.0214), both comfortably inside their bars. "
        "Leave-one-out ablation measures a card's presence or absence, and "
        "both cards already carried their existing discounts either way in "
        "the old code. What changed is a DECISION (which card to hold, "
        "whether a gate believes a miracle is affordable), visible in the "
        "paired harness above well before it would register in a per-card "
        "table at this N."),
})

# 2026-09-10: PARTLY MODELLED. `ablation.py` is in SHARED, so adding the third
# category moved ALL SIX fingerprints -- and it is a RENDERING change: it moves
# five rows between headings and prints a reason under each, and touches
# nothing that decides a simulated game.
#
# This is exactly the case the MOVED dict above exists for, one level up. A
# fingerprint that cries wolf teaches people to resume across changes that
# DID matter, so the claim "no number moved" is not argued here, it is
# demonstrated: both affected tables were re-rendered from their existing
# caches and diffed row by row.
_PARTLY_MODELLED = (
    " FINGERPRINT MOVED 2026-09-10, NUMBERS DID NOT. `ablation.py` gained the "
    "PARTLY MODELLED category (queued items 14/14b, KNOWN_ISSUES §0z4): five "
    "cards that the engine implements only in part -- Ashaya and Bane of "
    "Progress on azusa, Apex of Power, Hit the Mother Lode and Borrowed "
    "Knowledge on lorehold -- moved out of MODEL-EVALUATED, where a low score "
    "reads as evidence against the card, into a third table where it does "
    "not. DEMONSTRATED RATHER THAN ARGUED: both tables were re-rendered from "
    "THIS CACHE and diffed against the committed ones -- 58 of 58 azusa rows "
    "and 65 of 65 lorehold rows identical to the digit, no row added or "
    "lost. THIS CACHE IS CURRENT AND RESUMABLE.")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        NOTES.get(f"ablation_cache_{d}_10-20_n15000_medblank.json", "")
        + _PARTLY_MODELLED
    for d in ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
})

# 2026-09-10, LATER: FOUR CACHES REGENERATED FROM EMPTY for four engine
# changes closing four queued items. The two that were NOT regenerated are the
# evidence that the four that were needed to be: `check_unchanged_decks.py`
# against a worktree at HEAD reports lorehold and tivit BIT-IDENTICAL on all 8
# metrics while rendmaw, karlov, shilgengar and azusa moved.
_REGEN_2026_09_10 = {
    "azusa": (
        " REGENERATED FROM AN EMPTY CACHE 2026-09-10 for QUEUED ITEM 16 "
        "(§0z5): a token copy now re-triggers the host's ETB, the legend rule "
        "kills a copy of a legendary host, and SPRINGHEART_HOSTS was re-ranked "
        "for a world where copies have ETBs. Baseline win rate 0.3874 -> "
        "0.3898. ZERO OF 58 ROWS moved by more than their own old CI "
        "half-width and none flipped sign -- Springheart's own row went "
        "+0.0123 -> +0.0136, still `both`. A small, surgical change, and the "
        "table is keyed on it."),
    "shilgengar": (
        " REGENERATED FROM AN EMPTY CACHE 2026-09-10 for QUEUED ITEM 13 "
        "(§0z6): Treasures are spent as mana at every payment site, and "
        "`ult_reserve()` returns 0 when they already cover the ultimate. "
        "Baseline damage 52.04 -> 53.73, ultimates +9.4%, blood +9.1%; win "
        "rate +0.0021 and INSIDE its bar (p=0.15) -- the §0u shape, where the "
        "mechanism counters are decisive and the objective cannot resolve it. "
        "EXACTLY ONE ROW moved beyond its own old bar and it is the one the "
        "change predicted: REVEL IN RICHES +0.0081 -> +0.0025 against a "
        "±0.0021 bar, because a Treasure spent on mana is a Treasure not "
        "counted toward its ten. The pilot's fix (hoard while Revel is out) "
        "was implemented, measured at -0.0013 p=0.16, and NOT shipped; the "
        "lower row is the card's honest value. The three Treasure-makers all "
        "rose as predicted: Smothering Tithe +0.0049 -> +0.0069, Wayfarer's "
        "Bauble +0.0040 -> +0.0047, Pitiless Plunderer -0.0004 -> +0.0002."),
    "rendmaw": (
        " REGENERATED FROM AN EMPTY CACHE 2026-09-10 for §0i / QUEUED ITEM 10 "
        "(§0z7): Bitterblossom now pays the 1 life it has always said it "
        "pays. Deck win rate -0.0049 [-0.0061, -0.0038], p=1.2e-16. EXACTLY "
        "ONE ROW moved beyond its own old bar and it is Bitterblossom's: "
        "+0.0187 -> +0.0120 against a ±0.0029 bar, still signal `both` and "
        "still a good card. §0i called its old number a ceiling and it was, "
        "by about a quarter."),
    "karlov": (
        " REGENERATED FROM AN EMPTY CACHE 2026-09-10 for §0i / QUEUED ITEM 10 "
        "(§0z7): Phyrexian Arena now pays its 1 life -- which "
        "edhmc/shilgengar.py was ALREADY charging for the identical card, the "
        "§0u drift shape again. Deck win rate -0.0015 [-0.0022, -0.0007], "
        "p=1e-04. ZERO rows moved beyond their own bars; the Arena's own went "
        "+0.0171 -> +0.0149, inside its ±0.0029."),
}

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        NOTES.get(f"ablation_cache_{d}_10-20_n15000_medblank.json", "") + note
    for d, note in _REGEN_2026_09_10.items()
})

# 2026-09-11: ALL SIX REGENERATED for the colour-payment fix (§0z8). This one
# touches `can_pay`, `available_mana` and `spend` -- the three primitives every
# engine shares -- so there is no "unchanged deck" to check against this time,
# and all six caches were rebuilt from empty rather than argued about.
_COLOUR_2026_09_11 = (
    " REGENERATED FROM AN EMPTY CACHE 2026-09-11 for the COLOUR-PAYMENT FIX "
    "(§0z8): `can_pay` returned a colour-correct assignment and `spend` used "
    "only its COUNT, so the engine proved one payment and made another and "
    "BOARD ORDER decided which land was tapped. `available_mana` now returns a "
    "ManaUnits carrying each unit's owner, `spend` taps the owners it was "
    "given, the old tap order (lands before rocks before dorks) moved into "
    "can_pay as a tie-break, generic is paid from the largest SURPLUS of "
    "supply over what the hand wants, and a second unit off an already-tapped "
    "permanent is taken first because it is free. "
    "ACROSS ALL 377 ROWS IN THE SIX TABLES, TEN MOVED BEYOND THEIR OWN OLD CI "
    "HALF-WIDTH AND NONE FLIPPED SIGN. The clearest single move is the one the "
    "mechanism predicts: SOL RING +0.0077 -> +0.0121 in lorehold, because two "
    "colourless units off one tap are exactly what a correct assignment spends "
    "on generic while the lands cover the coloured pips. Win rate across the "
    "six lists is a wash; this shipped as correctness, not as a win-rate play. "
    "`mana_colour_legacy=True` reproduces every number published before "
    "2026-09-11.")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        NOTES.get(f"ablation_cache_{d}_10-20_n15000_medblank.json", "")
        + _COLOUR_2026_09_11
    for d in ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
})

# AZUSA'S FINGERPRINT MOVED FOR TWO REASONS ON 2026-09-10 AND ONLY ONE OF THEM
# IS THE RENDERER. Said separately, because "the fingerprint moved but it was
# only the table layout" would be FALSE for this deck, and a note that is true
# of five caches and false of the sixth is the kind of thing that gets a real
# staleness waved through.
NOTES["ablation_cache_azusa_10-20_n15000_medblank.json"] += (
    " SECOND REASON, AZUSA ONLY: `edhmc/azusa.py` grew the implementations for "
    "the seven candidates of §0z4 -- two dynamic costs, Nissa's Forest "
    "doubler, a restricted mana pool, a landfall payoff, two land abilities "
    "and both Wildspeaker modes -- and `edhmc/engine.py` gained the matching "
    "Forest branch in `spend`. EVERY ONE of those paths is guarded on a card "
    "that is NOT in this list, so none of them can execute in a run of this "
    "deck, and that is checked rather than asserted: "
    "`tools/check_unchanged_decks.py` against a worktree at HEAD reports ALL "
    "SIX decks bit-identical on all 8 metrics, azusa included, run twice -- "
    "once mid-change and once with the final code. `tools/validate.py` is "
    "+0.00 on all 18 metrics across all six engines. THIS CACHE IS CURRENT. "
    "The day that stops being true will be the day one of those cards is "
    "COMMITTED to the list, and then the table is void and needs a full "
    "regeneration, not a resume.")


def staged_signature(deck: str) -> str:
    """The deck's STAGED SWAPS, in the form the fingerprint hashes them.

    THE LIST IS AN INPUT TO EVERY CACHED NUMBER AND IT WAS NOT FINGERPRINTED.
    `ablation.py` builds its baseline with `build_pending(DECK)`, which applies
    this deck's entries in `edhmc/pending.py`'s CHANGES -- so staging a swap,
    unstaging one, or changing which card a staged swap cuts silently replaces
    the list every cached row was measured against. Nothing in SHARED or
    PER_DECK covers that, so the fingerprint declared such a cache CURRENT.
    Found 2026-09-13, when unstaging the rendmaw Cauldron swap changed that
    deck's baseline and left its three caches and its committed table
    describing a list the repo no longer builds.

    WHY NOT SIMPLY ADD `edhmc/pending.py` TO SHARED, which is the one-line
    version of this. Because the ledger is one file for six decks and is edited
    constantly for reasons that touch no list at all -- a rationale reworded, a
    recheck appended, a candidate measured, this very docstring's counterpart.
    Every one of those would mark all fourteen caches stale with no number
    moved, which is the failure `MOVED` and the newline normalisation both
    exist to prevent: a fingerprint that cries wolf teaches people to resume
    across the change that mattered. Hashing the SWAPS rather than the FILE
    moves exactly the decks whose list moved, and only when it moves.

    The signature is the ordered `-out +in` pairs, and order is deliberate:
    `build_pending` applies them in list order and `up_to=n` slices that order,
    so two stages swapped round are not the same baseline.

    NOTE FOR THE READER OF A DIFF: adding this component moved all six
    fingerprints ONCE, on 2026-09-13, because a hash cannot gain an input
    without changing. Five of those six moves were the scheme and not a
    staleness; rendmaw's was both. That is recorded per cache in NOTES.
    """
    from edhmc.pending import pending_for
    return "\n".join(f"-{c.remove} +{c.add}" for c in pending_for(deck))


def fingerprint(deck: str) -> tuple[str, list[str]]:
    """Hash the deck's source and its staged swaps, NORMALISED FOR LINE ENDINGS.

    The first version hashed raw bytes, and on Windows `git checkout` rewrites
    the working tree to CRLF under core.autocrlf -- so merging a branch changed
    the fingerprint of files whose CONTENT had not changed at all
    (`git diff HEAD` was empty). It fired the moment it was first exercised,
    and it would fire on every fresh clone.

    A check that cries wolf is worse than no check, because it teaches you to
    ignore it -- and this one exists precisely to be believed when it says a
    cache is stale. Normalising newlines makes it depend on content only.

    The last component is not a file: see `staged_signature`.
    """
    files = SHARED + PER_DECK[deck]
    h = hashlib.sha256()
    for key in sorted(files):
        with open(MOVED.get(key, key), "rb") as fh:
            body = fh.read().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        h.update(key.encode())
        h.update(hashlib.sha256(body).digest())
    # Hashed under a synthetic key, exactly as a file is, so the deck's staged
    # swaps cannot collide with a real path and so the "what each fingerprint
    # covers" section can list them.
    staged = staged_signature(deck)
    h.update(f"staged:{deck}".encode())
    h.update(hashlib.sha256(staged.encode()).digest())
    return h.hexdigest()[:16], sorted(files) + [f"staged:{deck}"]


# ---------------------------------------------------------------------------
# PROVENANCE: what a cache was BUILT at, which is a historical fact and does
# not change, as opposed to the live fingerprint, which changes constantly.
#
# THIS IS THE FIX FOR THE BUG THAT MADE THIS FILE UNTRUSTWORTHY. The manifest
# used to record the fingerprint computed AT GENERATION TIME and print it beside
# each cache, which reads as "this cache was built by this code" and is not what
# it means. Regenerating the file therefore certified whatever was on disk,
# however old -- so the one command that could make the staleness check pass was
# also the command that destroyed the evidence. A built-at fingerprint written
# WHEN THE CACHE IS WRITTEN cannot do that: it is stamped once, by the run that
# produced the numbers, and nothing later can forge it.

PROVENANCE = os.path.join(CACHE_DIR, "PROVENANCE.json")


def load_provenance() -> dict:
    try:
        with open(PROVENANCE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_provenance(prov: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(PROVENANCE, "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2, sort_keys=True)
        fh.write("\n")


def stamp_built(cache_name: str, deck: str, fresh: bool = False,
                note: str = "") -> None:
    """Record what a cache was built at. Called by ablation.py on creation.

    A call for a cache that already has a record is a no-op: the build
    fingerprint of an existing cache is a fact about the past and must never
    be rewritten -- rewriting it is precisely the forgery this scheme exists
    to prevent.

    `fresh=True` is the one exception, and it is not a rewrite: ablation.py
    passes it when the run STARTED WITH NO CACHE FILE, i.e. the numbers are
    new and the old record describes a cache that was deleted. The old record
    is kept under `superseded`, so the history is longer, not different.
    Found 2026-09-17 (§0z29): the karlov rebuild ran from an empty cache and
    kept the 2026-09-16 stamp, because the no-op branch could not tell a
    resumed run from a rebuild.
    """
    prov = load_provenance()
    if cache_name in prov and not fresh:
        return
    fp, _files = fingerprint(deck)
    entry = {
        "deck": deck,
        "built_at": fp,
        "built_commit": head(),
        "built_utc": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verified": [],
    }
    if note:
        entry["note"] = note
    if cache_name in prov:
        old = prov[cache_name]
        entry["superseded"] = old.pop("superseded", []) + [old]
    prov[cache_name] = entry
    save_provenance(prov)


def record_verified(cache_name: str, evidence: str) -> str:
    """Record that a cache whose fingerprint has MOVED was checked and its
    deck's numbers had not. The evidence string is required and is the whole
    point -- see `status_of`."""
    prov = load_provenance()
    if cache_name not in prov:
        raise SystemExit(f"no provenance for {cache_name}; nothing to verify")
    deck = prov[cache_name]["deck"]
    fp, _files = fingerprint(deck)
    prov[cache_name].setdefault("verified", []).append({
        "fingerprint": fp,
        "commit": head(),
        "utc": datetime.datetime.now(datetime.timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence": evidence,
    })
    save_provenance(prov)
    return fp


def status_of(cache_name: str, prov: dict) -> tuple[str, str]:
    """(status, explanation) for one cache. THE THREE STATES ARE THE POLICY.

    CURRENT   the live fingerprint equals what the cache was built at.
    VERIFIED  they differ, and a recorded check says the deck's NUMBERS did
              not move across that difference. The cache is good.
    SUSPECT   they differ and nothing has checked. NOT condemned -- suspect.

    The old policy was "if the fingerprint differs, DELETE the cache", and it
    was unusable: `engine.py`, `opponents.py`, `experiment.py` and
    `ablation.py` are in every deck's fingerprint, so a comment change in a
    shared file condemns all six caches and demands hours of recomputation for
    numbers that provably did not move. A rule too expensive to obey is a rule
    nobody obeys, and it was in fact not obeyed -- which is how ten caches came
    to be deleted with the manifest left describing them.

    SUSPECT is resolved by EVIDENCE, not by recomputation:
    `tools/check_unchanged_decks.py` runs the BASELINES ONLY against a worktree
    at `built_commit`. Bit-identical means the cache is still valid; record it
    with `--verified` and it becomes VERIFIED. Only a deck whose baseline
    actually moved needs its table rebuilt, and only that deck.
    """
    entry = prov.get(cache_name)
    if not entry:
        return "UNRECORDED", ("no provenance: nothing knows what code produced "
                              "this. Do not resume onto it.")
    live, _files = fingerprint(entry["deck"])
    if entry["built_at"] == live:
        return "CURRENT", f"built at `{entry['built_at']}`, which is live."
    for v in reversed(entry.get("verified", [])):
        if v["fingerprint"] == live:
            return "VERIFIED", (
                f"built at `{entry['built_at']}`; fingerprint has since moved "
                f"to `{live}` and was CHECKED at `{v['commit']}` "
                f"({v['utc']}): {v['evidence']}")
    return "SUSPECT", (
        f"built at `{entry['built_at']}`, live is `{live}`. The fingerprint "
        f"moved and nothing has checked whether the NUMBERS did. Run "
        f"`tools/check_unchanged_decks.py` against a worktree at "
        f"`{entry['built_commit']}`; if bit-identical, record it with "
        f"`python -m tools.cache_manifest --verified {cache_name} \"...\"`. "
        f"Only regenerate if the baseline actually moved.")


def caches():
    # The directory can be ABSENT, not merely empty: deleting the last cache
    # removes it from the working tree, because git does not track empty
    # directories. The first version raised FileNotFoundError there, so the
    # generator crashed in exactly the state it most needs to describe -- "no
    # caches exist" is a fact about provenance, not an error.
    if not os.path.isdir(CACHE_DIR):
        return
    for name in sorted(os.listdir(CACHE_DIR)):
        if name.startswith("ablation_cache_") and name.endswith(".json"):
            body = name[len("ablation_cache_"):-len(".json")]
            deck = body.split("_")[0]
            yield name, deck, body


def head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# 2026-09-16: the first six-deck regeneration since §0z23 emptied this
# directory, and the first caches tracked since. Run from an EMPTY cache on
# every deck -- there was nothing to resume, which is exactly what §0z23 cost
# and what these files restore.
# ---------------------------------------------------------------------------
_REGEN_2026_09_16 = (
    " REGENERATED FROM AN EMPTY CACHE 2026-09-16 by `./tools/regen_tables.sh`, "
    "N=15,000, seeds 5000..19999, four workers. §0z23 had deleted every cache, "
    "so all six decks started from nothing; this is the run that restores the "
    "resume. `python -m tools.validate` is +0.00 on all 18 metrics across all "
    "six engines after it, and the game RNG is sealed after the opening hand "
    "on every engine (corr 0.9106, ~11x). "
    "WHAT MOVED, checked per deck against the previously committed table "
    "rather than argued: ZERO rows in ANY of the six moved beyond their own "
    "old CI half-width, and ZERO already-significant rows flipped sign. The "
    "largest win-rate move in the whole run is 0.0003 (rendmaw). Four label "
    "changes in total: three in rendmaw and one in shilgengar. The rendmaw "
    "three are §0z24 -- `FLIP` assigned on an unguarded sign, where "
    "Biotransference kept an IDENTICAL win rate of +0.0005 +-0.0010 and "
    "changed label anyway because a damage value that displays as 0.00 "
    "changed sign. The shilgengar one is not that and is not a defect: Priest "
    "of Fell Rites crossed its own bar by one digit in the last place "
    "(+0.0016 -> +0.0017 against +-0.0016), which is the significance test "
    "behaving as a hard threshold on a card sitting exactly on the noise "
    "floor.")

# Azusa is the control in that comparison and deserves its own sentence.
_AZUSA_2026_09_16 = (
    " AND AZUSA REPRODUCED BIT FOR BIT: all 58 cards re-measured from empty, "
    "and `results/ablation_azusa.txt` came back BYTE-IDENTICAL to the "
    "committed file -- `git diff` empty on a file whose mtime had just moved. "
    "That is the strongest statement in this run and it is what makes the "
    "other five decks' fourth-decimal drift interpretable rather than "
    "mysterious: the harness IS deterministic, so the drift is a code "
    "difference and not noise. Azusa's table is the ONLY one of the six whose "
    "committed version was produced at `b09055c` (2026-09-15); the other five "
    "date from `34d6395`/`5a377ec` and therefore predate it, and `b09055c` is "
    "the only commit since to touch any file in a source fingerprint. "
    "NOT CONCLUDED HERE -- see the close-out commit for what is and is not "
    "established about why.")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        NOTES.get(f"ablation_cache_{d}_10-20_n15000_medblank.json", "")
        + _REGEN_2026_09_16
        + (_AZUSA_2026_09_16 if d == "azusa" else "")
    for d in ("lorehold", "rendmaw", "karlov", "tivit", "shilgengar", "azusa")
})



# 2026-09-16, SECOND regeneration of the day and only TWO decks in it.
_STAGED_2026_09_16 = (
    " REGENERATED FROM AN EMPTY CACHE 2026-09-16 because a SWAP WAS STAGED "
    "into this deck, which changes `build_pending` and therefore changes the "
    "baseline every cached number was measured against. That is the one thing "
    "the fingerprint's `staged:<deck>` component exists to catch, and it "
    "caught it: both caches went SUSPECT and could NOT be cleared with "
    "--verified, because `check_unchanged_decks` compares CODE and not staged "
    "lists, so a bit-identical result there would have certified nothing. "
    "ONLY THESE TWO DECKS WERE REBUILT -- the other four were untouched by the "
    "staging and stayed VERIFIED, which is §0z23's targeted-regeneration "
    "principle doing exactly what it was written for.")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        NOTES.get(f"ablation_cache_{d}_10-20_n15000_medblank.json", "")
        + _STAGED_2026_09_16
    for d in ("karlov", "tivit")
})

# 2026-09-17: karlov alone, for the third time in two days (§0z29).
NOTES["ablation_cache_karlov_10-20_n15000_medblank.json"] += (
    " REGENERATED FROM AN EMPTY CACHE 2026-09-17 because `decks/_evasion.py` "
    "was regenerated and gave Bloodthirsty Conqueror the flying it always had. "
    "The 2026-09-16 karlov cache was measured with that card as a GROUND "
    "creature: the generated file had not been re-run when the card was added, "
    "it was in no fingerprint (it is in SHARED now), and `check_unchanged_decks` "
    "came back bit-identical because it builds from the module and the card is "
    "STAGED. The staged baseline, measured the same way, moved (+0.44 damage a "
    "game over 400 seeds). ONLY KARLOV WAS REBUILT: the regeneration changed "
    "four names and the other three are candidates in no staged list, so the "
    "other five decks were VERIFIED on that evidence plus the module-level "
    "check. Flying turned out to be worth nothing measurable to the card -- "
    "§0z29 has the row-by-row comparison with the 2026-09-16 table.")

# 2026-09-17, second regeneration of the day: M1 + M2 (§0z30), four decks.
_SHARED_2026_09_17 = (
    " REGENERATED FROM AN EMPTY CACHE 2026-09-17 for §0z30, one London "
    "mulligan and one pod-phase order for six engines. A shared-code change "
    "that was SUPPOSED to move every baseline, so the question was how much: "
    "diagnostics/run_shared_code_shift.py, N=15,000 paired on the tables' own "
    "seeds (results/shared_code_shift_0z30.txt). Rebuilt: karlov and tivit "
    "(the pod order; +0.0205 and +0.0647 win rate at T20), rendmaw and "
    "shilgengar (the MDFC keep rule; +2.0 and +6.0 stranded mana a game, win "
    "rate at the noise floor). Lorehold and azusa moved on 3 and 2 seeds of "
    "15,000 and are VERIFIED on that evidence rather than rebuilt.")

NOTES.update({
    f"ablation_cache_{d}_10-20_n15000_medblank.json":
        NOTES.get(f"ablation_cache_{d}_10-20_n15000_medblank.json", "")
        + _SHARED_2026_09_17
    for d in ("karlov", "tivit", "rendmaw", "shilgengar")
})

def main():
    # `--verified <cache|deck> "<evidence>"` records that a SUSPECT cache was
    # checked and its deck's numbers had not moved. Evidence is mandatory: an
    # unevidenced "trust me" is the thing this whole scheme replaced.
    if "--verified" in sys.argv:
        i = sys.argv.index("--verified")
        try:
            target, evidence = sys.argv[i + 1], sys.argv[i + 2]
        except IndexError:
            raise SystemExit('usage: --verified <cache-or-deck> "<evidence>"')
        if not evidence.strip():
            raise SystemExit("refusing to record a verification with no "
                             "evidence -- say what was run and what it showed")
        names = [n for n, _d, _b in caches()
                 if n == target or n.startswith(f"ablation_cache_{target}_")]
        if not names:
            raise SystemExit(f"no cache on disk matching {target!r}")
        for n in names:
            fp = record_verified(n, evidence)
            print(f"recorded: {n} verified at {fp}")
        print("Now re-run `python -m tools.cache_manifest --write`.")
        return 0

    rows = []
    for name, deck, body in caches():
        if deck not in PER_DECK:
            print(f"  WARNING: no fingerprint set for deck {deck!r} ({name})",
                  file=sys.stderr)
            continue
        fp, files = fingerprint(deck)
        with open(os.path.join(CACHE_DIR, name), encoding="utf-8") as fh:
            n_cards = len(json.load(fh))
        rows.append((name, deck, body, fp, n_cards, files))

    lines = [
        "# Committed ablation caches",
        "",
        "GENERATED by `python -m tools.cache_manifest --write`. Do not edit by",
        "hand.",
        "",
        "The caches themselves live in `results/caches/`.",
        "",
        "`ablation.py` keys its cache on deck, horizons and N — **not on the",
        "version of the code that produced it**. A full cache makes `todo`",
        "empty, so a run silently REPRINTS THE OLD NUMBERS instead of",
        "measuring anything. While these files were gitignored that hazard was",
        "bounded, because a fresh clone had no cache to go stale. Tracking them",
        "removed that safety net, which is what this file replaced it with.",
        "",
        "## The rule, and why it is no longer \"delete it\"",
        "",
        "Each cache records the fingerprint it was **built at** — stamped by",
        "the run that produced the numbers, in `ablation.py`'s `save()`, and",
        "never rewritten afterwards. Comparing that against the live",
        "fingerprint gives three states:",
        "",
        "| state | meaning | what to do |",
        "|---|---|---|",
        "| **CURRENT** | built-at equals live | resume freely |",
        "| **VERIFIED** | they differ, and a recorded check says the deck's "
        "NUMBERS did not move across that difference | resume freely; the "
        "evidence is below |",
        "| **SUSPECT** | they differ and nothing has checked | **check before "
        "resuming — do not assume either way** |",
        "| **UNRECORDED** | no provenance at all | do not resume onto it |",
        "",
        "**The old rule was \"if the fingerprint differs, DELETE the cache\",",
        "and it was unusable.** `engine.py`, `opponents.py`, `experiment.py`",
        "and `ablation.py` are in every deck's fingerprint, so a comment",
        "change in a shared file condemns all six caches and demands a "
        "six-deck",
        "regeneration — about **four hours** — for numbers that provably did",
        "not move. A rule too expensive to obey is a rule nobody obeys, and it",
        "was not obeyed: that is how ten caches came to be deleted with this",
        "file left describing them (§0z23).",
        "",
        "**SUSPECT is resolved by evidence, not by recomputation.**",
        "`tools/check_unchanged_decks.py` runs the BASELINES ONLY against a",
        "worktree at the cache's `built_commit`. It takes **seconds**, not",
        "hours. Bit-identical means the cache is still good:",
        "",
        "```bash",
        "git worktree add ../edhmc_at <built_commit>",
        "python -m tools.check_unchanged_decks --out=new.json",
        "(cd ../edhmc_at && python -m tools.check_unchanged_decks --out=old.json)",
        "python -m tools.check_unchanged_decks --diff old.json new.json",
        "python -m tools.cache_manifest --verified <deck> \"what you ran and "
        "what it showed\"",
        "python -m tools.cache_manifest --write",
        "```",
        "",
        "**Only a deck whose baseline actually moved needs its table rebuilt,",
        "and only that deck.** `./tools/regen_tables.sh` still deletes every",
        "cache by default; `--resume` does not.",
        "",
        "Generated at `{}`.".format(head()),
        "",
        # THE HEADLINE IS DERIVED, NOT ASSERTED. This opened with a flat
        # "THERE ARE NO TRACKED CACHES", which was true the day §0z23 wrote it
        # and became false the moment a cache was committed again -- a
        # GENERATED file carrying a hand-written claim about its own subject,
        # which is the very failure §0z23 was closing. It is read off `rows`
        # now, so it cannot disagree with the table underneath it.
        (f"**{len(rows)} cache{'' if len(rows) == 1 else 's'} tracked.** Each "
         "row below carries the fingerprint it was BUILT at and its state "
         "against the live one; the provenance of each is in `NOTES`."
         if rows else
         "**THERE ARE NO TRACKED CACHES. This is deliberate, and it is "
         "§0z23's chosen resolution.**"),
        "",
        "**§0z23 is why the rule above exists.** Ten caches — every",
        "`_medblank` one at N=15,000, which is to say every cache that had",
        "produced a table committed in `results/` — were deleted in `b09055c`",
        "without this generator being re-run, so this file went on describing",
        "fourteen files of which four existed. The four survivors were the old",
        "`n6000`/`n2000` caches and **every one of them disagreed with its live",
        "fingerprint**, which the rule stated above condemns. They were deleted",
        "and this file regenerated.",
        "",
        "**No committed table was invalidated by that.** The tables in",
        "`results/` are the artefact; a cache is the intermediate that lets a",
        "run resume. What was lost was the resume.",
        "",
        "**The rejected alternative is worth knowing, because it is the",
        "tempting one.** Regenerating this file WITHOUT deleting the four stale",
        "caches would have made `python -m tools.check_docs` pass — the",
        "recorded fingerprint is taken live at generation time, so regenerating",
        "sets recorded equal to live *by construction*, certifying four caches",
        "as produced by code that did not produce them and destroying the only",
        "signal that said otherwise. **Never regenerate this file to silence a",
        "staleness warning.** Regenerate it when the caches themselves change.",
        "",
        "A cache is added here in the same commit that produces it, with its",
        "note in `NOTES` — that is what makes the fingerprint above mean",
        "anything.",
        "",
    ]
    if rows:
        prov = load_provenance()
        lines += ["| cache | deck | cards | built at | built | state |",
                  "|---|---|---|---|---|---|"]
        for name, deck, body, fp, n_cards, _files in rows:
            entry = prov.get(name, {})
            st, _why = status_of(name, prov)
            lines.append(
                f"| `{name}` | {deck} | {n_cards} | "
                f"`{entry.get('built_at', '—')}` | "
                f"`{entry.get('built_commit', '—')}` | **{st}** |")
        lines += ["", "### State of each cache", ""]
        for name, deck, _b, _f, _c, _files in rows:
            st, why = status_of(name, prov)
            lines += [f"- **`{name}`** — {st}. {why}"]
            for v in prov.get(name, {}).get("verified", []):
                lines.append(f"  - verified at `{v['fingerprint']}` "
                             f"(`{v['commit']}`, {v['utc']}): {v['evidence']}")
    else:
        # An empty table renders as a bare header with no rows, which reads
        # like a rendering bug rather than like a fact. Say the fact.
        lines.append("_No caches are tracked._")
    lines += ["", "## What each fingerprint covers", ""]
    for deck in sorted(PER_DECK):
        _fp, files = fingerprint(deck)
        lines.append(f"- **{deck}** — " + ", ".join(f"`{f}`" for f in files))
        # The staged swaps are spelled out rather than left as a bare key: the
        # whole point of the component is that the LIST is an input, and a
        # reader checking whether a cache is stale needs to see which list.
        staged = staged_signature(deck)
        lines.append(f"  - `staged:{deck}` is "
                     + (", ".join(f"`{s}`" for s in staged.split("\n"))
                        if staged else "**empty** — nothing staged for this "
                                       "deck, so the baseline is the module's "
                                       "own list"))
    lines += ["", "## How each cache was produced", ""]
    if not rows:
        lines += ["No caches are tracked — see above. The notes below are kept "
                  "for the caches that HAVE existed, because they are the "
                  "provenance for numbers quoted throughout the project.", ""]
    for name, deck, _b, _f, _c, _files in rows:
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append(NOTES.get(name) or NOTES.get(deck) or "_no note recorded_")
        lines.append("")

    # Notes whose cache is no longer on disk. Deleting a cache must not delete
    # the record of what produced the numbers it produced -- several committed
    # tables are still quoted against caches that no longer exist, and a note
    # that silently stops rendering is how that provenance would be lost.
    present = {name for name, _d, _b, _f, _c, _files in rows}
    gone = sorted(k for k in NOTES
                  if k.startswith("ablation_cache_") and k not in present)
    if gone:
        lines += ["", "## Caches that no longer exist, and what produced them",
                  "",
                  "Kept as provenance. These files are NOT in the repository; "
                  "the notes are here because committed numbers were measured "
                  "on them.", ""]
        for name in gone:
            lines.append(f"### `{name}` — deleted")
            lines.append("")
            lines.append(NOTES[name])
            lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if "--write" in sys.argv:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {OUT}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
