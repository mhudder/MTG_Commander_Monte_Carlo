#!/usr/bin/env python3
"""Is this card already known to the repo? Derived, not grepped.

WHY THIS EXISTS. `.claude/skills/add-card/SKILL.md` step 1 says to grep three
places before proposing a card, and one of the three CANNOT WORK:
`tools/candidates.py` imports card CONSTANTS and never writes a card's name, so
`grep "Enlightened Confidant" tools/candidates.py` finds nothing about a card
that file measures. That grep returned nothing on 2026-09-20 and the card was
reported as unmeasured; it had been measured on 2026-09-04 at +0.0087 +-0.0034.
§0q's rule applies to a PROCEDURE as much as to a name set: derive the answer
from what the repo already holds, and do not ask a human to spell a constant
right. §0z26 is the finding that two of fifteen proposals were already-measured
cards; this is the check that finding never got.

WHAT IT LOOKS AT, all by importing rather than by text where it can:

    deck list      every current deck module's build()
    catalog        pending.DECKS' per-deck swap-in catalog
    candidates     EVERY card object in EVERY batch of tools/candidates.py
                   (and its OLD batches), read off the objects' .name
    ledger         PROPOSED / MEASURED / CHANGES / COMMITTED / WITHDRAWN
    engine         the name as a string literal in edhmc/*.py or tools/*.py,
                   which is how behaviour attaches when there is no script=
                   (§0z25). decks/_evasion.py is excluded: it is GENERATED
                   from Scryfall, so a name there is not a claim by anyone.

    python -m tools.card_known "Verdant Kraken" "Koth of the Homestead"
    python -m tools.card_known --stdin < names.txt      # one name per line
    python -m tools.card_known --unknown-only --stdin   # filter a set dump

Exit code is 1 if any name is known anywhere, so it can gate a batch script.
"""
import pathlib
import sys

from edhmc.pending import (DECKS as CATALOG, PROPOSED, MEASURED, CHANGES,
                           COMMITTED, WITHDRAWN)

SRC = [p for p in list(pathlib.Path("edhmc").rglob("*.py"))
       + list(pathlib.Path("tools").rglob("*.py"))
       if p.name != "_evasion.py" and p.name != "card_known.py"]


def _candidate_cards():
    """Every card object named in a candidates batch, by importing the module.

    Walks the batch tuples rather than reading the file, so a card added to a
    batch is found whatever the constant is called.
    """
    import tools.candidates as CAND
    out = {}
    for label, spec in getattr(CAND, "DECKS", {}).items():
        for item in spec:
            for card in (item if isinstance(item, (list, tuple)) else ()):
                name = getattr(card, "name", None)
                if name:
                    out.setdefault(name, set()).add(label)
    for label, cards in getattr(CAND, "OLD", {}).items():
        for card in cards:
            name = getattr(card, "name", None)
            if name:
                out.setdefault(name, set()).add(f"OLD:{label}")
    return out


def index():
    """name -> {channel: [where]} for everything the repo already knows."""
    idx = {}

    def add(name, channel, where):
        idx.setdefault(name, {}).setdefault(channel, []).append(where)

    for deck, (mod, catalog) in CATALOG.items():
        cards, commander = mod.build()
        for c in cards:
            add(c.name, "deck list", deck)
        add(commander.name, "commander", deck)
        for name in catalog:
            add(name, "catalog", deck)

    for name, labels in _candidate_cards().items():
        for label in sorted(labels):
            add(name, "candidates batch", label)

    for p in PROPOSED:
        add(p.card, "ledger PROPOSED", p.deck)
    for c in MEASURED:
        add(c.card, "ledger MEASURED", c.deck)
    for lst, tag in ((CHANGES, "ledger STAGED"), (COMMITTED, "ledger COMMITTED"),
                     (WITHDRAWN, "ledger WITHDRAWN")):
        for ch in lst:
            add(ch.add, tag, f"{ch.deck} +")
            add(ch.remove, tag, f"{ch.deck} -")

    text = {p: p.read_text() for p in SRC}
    for name in list(idx) + []:
        pass
    return idx, text


def lookup(name, idx, text):
    found = dict(idx.get(name, {}))
    # The engine check is a text search by necessity: a name dispatched in an
    # `if c.name == "..."` is a string and nothing else knows about it.
    for base in {name, name.split(" // ")[0]}:
        for p, t in text.items():
            if f'"{base}"' in t or f"'{base}'" in t:
                found.setdefault("named in code", []).append(str(p))
    return found


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if "--stdin" in flags:
        args += [ln.strip() for ln in sys.stdin if ln.strip()]
    if not args:
        print(__doc__.strip().splitlines()[0])
        print("\nusage: python -m tools.card_known \"Name\" [...] | --stdin")
        return 2
    idx, text = index()
    known = 0
    for name in args:
        found = lookup(name, idx, text)
        if not found:
            if "--unknown-only" in flags:
                print(name)
            else:
                print(f"  [new ] {name}")
            continue
        known += 1
        if "--unknown-only" in flags:
            continue
        print(f"  [KNOWN] {name}")
        for channel, where in sorted(found.items()):
            print(f"      {channel:<18} {', '.join(sorted(set(where)))}")
    if "--unknown-only" not in flags:
        print(f"\n{len(args)} checked, {known} already known, "
              f"{len(args) - known} new.")
    return 1 if known else 0


if __name__ == "__main__":
    sys.exit(main())
