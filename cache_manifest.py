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
    for d, old, ratio, pred in (
        ("karlov", 6000, "0.64", "0.63"),
        ("rendmaw", 6000, "0.64", "0.63"),
        ("lorehold", 6000, "0.63", "0.63"),
        ("tivit", 2000, "0.39", "0.37"),
    )
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
