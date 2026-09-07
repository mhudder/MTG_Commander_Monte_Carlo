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

import hashlib
import json
import os
import subprocess
import sys

OUT = "ABLATION_CACHES.md"

# The modules whose behaviour a cached number depends on. opponents.py and
# experiment.py are shared, so a change to either invalidates every deck.
SHARED = ["edhmc/opponents.py", "edhmc/experiment.py", "edhmc/engine.py",
          "ablation.py"]
PER_DECK = {
    "rendmaw": ["edhmc/decks/rendmaw_v12.py"],
    "lorehold": ["edhmc/lorehold.py", "edhmc/decks/lorehold_v16.py"],
    "karlov": ["edhmc/karlov.py", "edhmc/decks/karlov_v2.py"],
    "tivit": ["edhmc/tivit.py", "edhmc/voting.py", "edhmc/decks/tivit_v1.py"],
    "shilgengar": ["edhmc/shilgengar.py", "edhmc/decks/shilgengar_v1.py"],
    "azusa": ["edhmc/azusa.py", "edhmc/decks/azusa_v1.py"],
}
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
        "what the card actually does."),
})


def fingerprint(deck: str) -> tuple[str, list[str]]:
    """Hash the deck's source, NORMALISED FOR LINE ENDINGS.

    The first version hashed raw bytes, and on Windows `git checkout` rewrites
    the working tree to CRLF under core.autocrlf -- so merging a branch changed
    the fingerprint of files whose CONTENT had not changed at all
    (`git diff HEAD` was empty). It fired the moment it was first exercised,
    and it would fire on every fresh clone.

    A check that cries wolf is worse than no check, because it teaches you to
    ignore it -- and this one exists precisely to be believed when it says a
    cache is stale. Normalising newlines makes it depend on content only.
    """
    files = SHARED + PER_DECK[deck]
    h = hashlib.sha256()
    for path in sorted(files):
        with open(path, "rb") as fh:
            body = fh.read().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        h.update(path.encode())
        h.update(hashlib.sha256(body).digest())
    return h.hexdigest()[:16], sorted(files)


def caches():
    for name in sorted(os.listdir(".")):
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


def main():
    rows = []
    for name, deck, body in caches():
        if deck not in PER_DECK:
            print(f"  WARNING: no fingerprint set for deck {deck!r} ({name})",
                  file=sys.stderr)
            continue
        fp, files = fingerprint(deck)
        with open(name, encoding="utf-8") as fh:
            n_cards = len(json.load(fh))
        rows.append((name, deck, body, fp, n_cards, files))

    lines = [
        "# Committed ablation caches",
        "",
        "GENERATED by `cache_manifest.py --write`. Do not edit by hand.",
        "",
        "`ablation.py` keys its cache on deck, horizons and N — **not on the",
        "version of the code that produced it**. A full cache makes `todo`",
        "empty, so a run silently REPRINTS THE OLD NUMBERS instead of",
        "measuring anything. While these files were gitignored that hazard was",
        "bounded, because a fresh clone had no cache to go stale. They are",
        "tracked now — 141 KB against roughly six hours of simulation — so the",
        "provenance below is the safety net instead.",
        "",
        "**Before resuming a cache, re-run `python cache_manifest.py` and",
        "compare the fingerprint. If it differs, DELETE the cache.**",
        "`./regen_tables.sh` deletes them by default; `--resume` does not.",
        "",
        f"Fingerprints recorded at `{head()}`.",
        "",
        "| cache | deck | cards | source fingerprint |",
        "|---|---|---|---|",
    ]
    for name, deck, body, fp, n_cards, _files in rows:
        lines.append(f"| `{name}` | {deck} | {n_cards} | `{fp}` |")
    lines += ["", "## What each fingerprint covers", ""]
    for deck in sorted(PER_DECK):
        _fp, files = fingerprint(deck)
        lines.append(f"- **{deck}** — " + ", ".join(f"`{f}`" for f in files))
    lines += ["", "## How each cache was produced", ""]
    for name, deck, _b, _f, _c, _files in rows:
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append(NOTES.get(name) or NOTES.get(deck) or "_no note recorded_")
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
