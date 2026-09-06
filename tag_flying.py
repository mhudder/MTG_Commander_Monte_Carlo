#!/usr/bin/env python3
"""Fetch FLYING for every creature in the three decks, from Scryfall.

WHY THIS IS A SCRIPT AND NOT A HAND-EDIT
----------------------------------------
CLAUDE.md: "Do not hand-tag a keyword from memory: ablation compares each card
against a blank in the same list, so a partial tag list biases the whole table
toward whatever got tagged. It is worse than no tags at all."

That is exactly right for evasion, because the bias is not random — you
remember the fliers you think of as fliers and forget the rest.

READ THE KEYWORDS ARRAY, NOT THE ORACLE TEXT. A first pass here matched
"flying" in the text and produced false positives in both directions:

  * REACH'S REMINDER TEXT contains the word flying ("Reach (This creature can
    block creatures with flying.)"), so Longshot, Arasta, The Dawning Archaic
    and Rendmaw itself were all tagged as fliers. None of them fly.
  * TOKEN-MAKING TEXT contains it too — Rendmaw makes Birds with flying and
    Bitterblossom makes Faeries with flying, but neither card flies.
  * CONDITIONAL grants are in the text and NOT in the keywords array, so they
    must be modelled per-card rather than tagged. See CONDITIONAL below.

Scryfall's `keywords` array carries only what the card unconditionally has,
which is precisely the question this script is asking.

REACH IS DELIBERATELY NOT COLLECTED. Reach is a blocking ability, and this
engine never blocks with your creatures — the opponents' capacity to block
fliers is the abstract `flier_block_share`. Your creatures' reach is inert.

    python tag_flying.py            # print the classification
    python tag_flying.py --write    # regenerate edhmc/decks/_evasion.py
"""
import json
import sys
import urllib.parse
import urllib.request

from edhmc.decks import rendmaw_v12, lorehold_v16, karlov_v2, tivit_v1

HEADERS = {"User-Agent": "EDHMC/1.0", "Accept": "application/json",
           "Content-Type": "application/json"}
OUT = "edhmc/decks/_evasion.py"

# Creatures whose flying is CONDITIONAL. These cannot be a static tag and are
# implemented in opponents.flying_of() instead. Listed here so the two places
# can be diffed by eye, and so a new conditional flier is not silently missed.
CONDITIONAL = {
    "Serra Ascendant": "flies only at 30+ life",
    "Voice of the Blessed": "flies only with 4+ counters",
    "Dragon's Rage Channeler": "flies only with delirium (4+ card types in yard)",
}

# Token subtypes made by the Tivit list that do NOT fly, listed so the absence
# is deliberate rather than forgotten: Soldier (Lieutenants, Vault 11), Rabbit
# (Tempt with Bunnies), Citizen (Master of Ceremonies), Servo (Marionette
# Master). Its Clue, Food and Treasure tokens are not creatures at all.

# Tokens that fly, verified against the text of the card that makes them.
# Kept here rather than at the make_tokens call sites so every evasion claim
# in the project has one home.
FLYING_TOKENS = {
    "Bird",     # Rendmaw: "2/2 black Bird creature token with flying"
    "Faerie",   # Bitterblossom: "1/1 black Faerie Rogue ... with flying"
    "Pegasus",  # Storm Herd: "X 1/1 white Pegasus creature tokens with flying"
    "Angel",    # Emeria's Call: "two 4/4 white Angel Warrior ... with flying"
}


def scryfall_collection(names):
    found = {}
    for i in range(0, len(names), 75):
        body = json.dumps({"identifiers": [{"name": n} for n in names[i:i + 75]]})
        req = urllib.request.Request("https://api.scryfall.com/cards/collection",
                                     data=body.encode(), headers=HEADERS,
                                     method="POST")
        data = json.load(urllib.request.urlopen(req))
        for card in data.get("data", []):
            found[card["name"]] = card
        for miss in data.get("not_found", []):
            # A double-faced card's COMBINED name ("Witch Enchanter //
            # Witch-Blessed Meadow") is not a valid `name` identifier. Falling
            # through silently would leave it untagged, which is the exact
            # partial-tag bias this script exists to avoid.
            card = named(miss.get("name"))
            if card is None:
                print(f"  NOT FOUND: {miss}", file=sys.stderr)
            else:
                found[miss["name"]] = card
    return found


def named(name):
    url = ("https://api.scryfall.com/cards/named?fuzzy="
           + urllib.parse.quote(name))
    try:
        return json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers=HEADERS)))
    except Exception:
        return None


def main():
    decks = {"rendmaw": rendmaw_v12, "lorehold": lorehold_v16,
             "karlov": karlov_v2, "tivit": tivit_v1}
    creatures = {}
    for mod in decks.values():
        deck, cmd = mod.build()
        for c in list(deck) + [cmd]:
            if c.is_creature and not c.is_land:
                creatures[c.name] = c
        # CANDIDATES TOO. `flying=name in FLYING` is evaluated at import, so a
        # candidate that is not in this set is constructed as a GROUND
        # creature and candidates.py measures it as one. Found 2026-09-05:
        # Goldspan Dragon (4/4 flying haste) and Caldera Pyremaw (3/3 flying)
        # were both scored with no evasion. Walking only build() is the same
        # class of bug as the SCRIPTED_* sets — the deck moved and the
        # generated data did not.
        for attr in dir(mod):
            if not attr.isupper():
                continue
            v = getattr(mod, attr)
            if type(v).__name__ == "Card" and v.is_creature and not v.is_land:
                creatures.setdefault(v.name, v)

    cards = scryfall_collection(sorted(creatures))
    flying = {n for n, c in cards.items() if "Flying" in c.get("keywords", [])}

    print(f"{len(cards)}/{len(creatures)} creatures resolved\n")
    print(f"UNCONDITIONAL FLYING ({len(flying)}):")
    for n in sorted(flying):
        print(f"    {n}")
    print(f"\nCONDITIONAL — handled in opponents.flying_of(), not tagged:")
    for n, why in sorted(CONDITIONAL.items()):
        seen = "in deck" if n in creatures else "NOT IN ANY DECK"
        print(f"    {n:26} {why}   [{seen}]")
    missed = {n for n, c in cards.items()
              if n not in flying and n not in CONDITIONAL
              and "flying" in (c.get("oracle_text") or "").lower()}
    if missed:
        print(f"\nMentions 'flying' but does NOT have it (reach reminder text,")
        print(f"or it makes flying tokens) — correctly NOT tagged:")
        for n in sorted(missed):
            print(f"    {n}")

    if "--write" in sys.argv:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write('"""GENERATED by tag_flying.py — do not edit by hand.\n\n'
                     "Unconditional flying for every creature in the three decks,\n"
                     "read from Scryfall's `keywords` array. Conditional fliers are\n"
                     "NOT here: see opponents.flying_of(). Regenerate with\n"
                     "`python tag_flying.py --write` after any deck change.\n"
                     '"""\n\nFLYING = {\n')
            for n in sorted(flying):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\n# Token subtypes that fly, from the text of the card "
                     "that makes them.\nFLYING_TOKENS = {\n")
            for n in sorted(FLYING_TOKENS):
                fh.write(f"    {n!r},\n")
            fh.write("}\n")
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
