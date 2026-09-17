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

# The notes -- how each cache was produced -- are DATA, in
# results/caches/NOTES.json beside PROVENANCE.json, keyed by cache file name.
# Until 2026-09-17 they were ~700 lines of string constants in this file (L4
# of that day's review): documentation in code, the thing the repo says not
# to do. `--note <cache|deck> "<text>"` appends to a cache's note the way
# `--verified` appends its evidence, so a regeneration records its provenance
# without editing a .py file. A deleted cache keeps its note: several
# committed numbers were measured on caches that no longer exist, and the
# manifest renders those under "Caches that no longer exist".
NOTES_PATH = os.path.join(CACHE_DIR, "NOTES.json")


def load_notes() -> dict:
    try:
        with open(NOTES_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {}


def record_note(cache_name: str, text: str) -> None:
    notes = load_notes()
    notes[cache_name] = (notes.get(cache_name, "") + " " + text.strip()).strip()
    with open(NOTES_PATH, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(notes.items())), fh, indent=1,
                  ensure_ascii=False, sort_keys=True)


NOTES = load_notes()


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

    # `--note <cache|deck> "<text>"` appends provenance prose to a cache's
    # note in results/caches/NOTES.json -- the record of HOW a run was done.
    if "--note" in sys.argv:
        i = sys.argv.index("--note")
        try:
            target, text = sys.argv[i + 1], sys.argv[i + 2]
        except IndexError:
            raise SystemExit('usage: --note <cache-or-deck> "<text>"')
        if not text.strip():
            raise SystemExit("refusing to record an empty note")
        names = [n for n, _d, _b in caches()
                 if n == target or n.startswith(f"ablation_cache_{target}_")]
        if not names:
            raise SystemExit(f"no cache on disk matching {target!r}")
        for n in names:
            record_note(n, text)
            print(f"recorded a note on {n}")
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
         "against the live one; the provenance of each is in "
         "`results/caches/NOTES.json`."
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
        "note in `results/caches/NOTES.json` (`--note`) — that is what makes",
        "the fingerprint above mean anything.",
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
