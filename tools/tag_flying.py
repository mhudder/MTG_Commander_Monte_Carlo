#!/usr/bin/env python3
"""Fetch FLYING and INDESTRUCTIBLE for every card in the four decks, from Scryfall.

(The name is historical: it collected only flying until 2026-09-06. The two
keywords are collected by one script because they are one problem -- see below.)

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

INDESTRUCTIBLE, added 2026-09-06, for exactly the reason above
--------------------------------------------------------------
`Card.indestructible` has existed since 2026-09-04, priced by `destroy_share`,
and was INERT: no card in any committed list carried it, only the Heliod
candidate, by hand. Fixing Erebos, Bleak-Hearted made it live for the first
time — and hand-setting one card is precisely the partial-tag bias this script
exists to prevent. Checked against Scryfall, the four lists hold THREE
statically indestructible cards, and two of them are ones nobody would think of:

    Erebos, Bleak-Hearted   rendmaw
    Darksteel Citadel       tivit    (a LAND, so `L()` needs the tag too)
    Darkmoss Bridge         tivit    (a LAND)

The two lands are provably inert today — `spot_removal` and `ae_removal` both
exclude `is_land`, so a land is never a removal target — but "inert today" is
what `Card.indestructible` itself was, and the point of generating the set is
that the next card added cannot be missed. `audit_cards.py` verifies it.

NOT COLLECTED, because they are not static and a tag would be a lie:

  * GRANTED until end of turn — Boros Charm, Heroic Intervention, Dawn's Truce,
    Plaza of Heroes. Heroic Intervention is already modelled as `hold_up_rate`.
  * CONDITIONAL — Voice of the Blessed has indestructible only with TEN or more
    +1/+1 counters (its flying needs four, which is why it is in CONDITIONAL
    below). Ten is reachable in the Karlov list and is NOT modelled.

SUBTYPES, added 2026-09-10, for the third time the same reason
--------------------------------------------------------------
`Card.types` holds CARD types (Creature, Land), never creature or land
SUBTYPES — a limitation `edhmc.shilgengar` and `edhmc.azusa` both document. Two
cards in the 2026-09-10 Azusa batch read a subtype and cannot be evaluated
without one:

    Return of the Wildspeaker   "draw cards equal to the greatest power among
                                NON-HUMAN creatures you control"
    Sapling Nursery             "Affinity for FORESTS"

and a third, Nissa, Who Shakes the World, doubles "whenever you tap a FOREST
for mana". Writing those two sets by hand is the failure mode CLAUDE.md names
and KNOWN_ISSUES §0q records four instances of, so they are GENERATED here from
Scryfall's type line with everything else.

READ THE TYPE LINE'S SUBTYPE HALF, NOT THE WHOLE LINE. "Forest" appears in the
name of cards that are not Forests (Forest Bear) and in oracle text constantly;
only the segment after the em dash is the subtype list. Dryad Arbor ("Land
Creature — Forest Dryad") IS a Forest and IS a nontoken creature, which is
exactly the kind of card a hand-written set forgets.

    python tag_flying.py            # print the classification
    python tag_flying.py --write    # regenerate edhmc/decks/_evasion.py
"""
import json
import sys
import urllib.parse
import urllib.request

from edhmc.decks import discover_current_decks

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


def subtypes(card):
    """The SUBTYPE half of a type line, as a set.

    "Legendary Creature — Human Monk" -> {"Human", "Monk"}. Scryfall uses an em
    dash; a double-faced card has no top-level type line, so its faces are
    walked and merged. Anything before the dash is a card type or a supertype
    and is deliberately dropped -- matching on the whole line is how "Forest"
    matches Forest Bear and how "Human" matches "Human Soldier tokens" in
    oracle text.
    """
    lines = [card.get("type_line") or ""]
    for face in card.get("card_faces", []) or []:
        lines.append(face.get("type_line") or "")
    out = set()
    for line in lines:
        if "—" in line:
            out |= set(line.split("—", 1)[1].split())
    return out


def named(name):
    url = ("https://api.scryfall.com/cards/named?fuzzy="
           + urllib.parse.quote(name))
    try:
        return json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers=HEADERS)))
    except Exception:
        return None


def main():
    # DISCOVERED, not named by hand: see edhmc.decks.discover_current_decks.
    # A newly added "<name>_v1.py" with a build() is tagged the first time
    # this runs, with no edit here — the same fix `audit_cards.py` got, for
    # the same reason: this file's own history is the SCRIPTED_* class of bug.
    decks = discover_current_decks()
    creatures = {}
    everything = {}          # indestructible is not a creature-only keyword
    for mod in decks.values():
        deck, cmd = mod.build()
        for c in list(deck) + [cmd]:
            everything[c.name] = c
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
            if type(v).__name__ != "Card":
                continue
            everything.setdefault(v.name, v)
            if v.is_creature and not v.is_land:
                creatures.setdefault(v.name, v)

    cards = scryfall_collection(sorted(everything))
    flying = {n for n, c in cards.items()
              if n in creatures and "Flying" in c.get("keywords", [])}
    # Restricted to PERMANENTS, for the same reason `flying` is restricted to
    # creatures: Scryfall's `keywords` array does not distinguish "this card
    # has indestructible" from "this card GRANTS indestructible to something
    # else". Found 2026-09-07 adding the Azusa deck: Sylvan Awakening ("lands
    # you control become ... indestructible ...") is a Sorcery -- it can never
    # be a Permanent on a battlefield for `opponents.destroy()` to check, so
    # tagging it was harmless in practice, but it was still a false claim
    # about the card and exactly the "a tag would be a lie" trap this
    # generator exists to avoid.
    indestructible = {n for n, c in cards.items()
                      if "Indestructible" in c.get("keywords", [])
                      and n in everything and everything[n].is_permanent}
    # SUBTYPES. Restricted to the card types that can carry them here: a Human
    # is a creature and a Forest is a land, and nothing else in these lists
    # reads either. Dryad Arbor satisfies both halves of "land" and "creature"
    # and lands in FOREST only, which is correct -- it is a Forest Dryad, not a
    # Human.
    humans = {n for n, c in cards.items()
              if n in creatures and "Human" in subtypes(c)}
    forests = {n for n, c in cards.items()
               if n in everything and everything[n].is_land
               and "Forest" in subtypes(c)}

    print(f"{len(cards)}/{len(everything)} cards resolved "
          f"({len(creatures)} of them creatures)\n")
    print(f"UNCONDITIONAL FLYING ({len(flying)}):")
    for n in sorted(flying):
        print(f"    {n}")
    print(f"\nCONDITIONAL — handled in opponents.flying_of(), not tagged:")
    for n, why in sorted(CONDITIONAL.items()):
        seen = "in deck" if n in creatures else "NOT IN ANY DECK"
        print(f"    {n:26} {why}   [{seen}]")
    print(f"\nUNCONDITIONAL INDESTRUCTIBLE ({len(indestructible)}), all card "
          f"types:")
    for n in sorted(indestructible):
        c = everything[n]
        print(f"    {n:26} {'LAND' if c.is_land else ''}")
    granted = {n for n, c in cards.items()
               if n not in indestructible
               and "indestructible" in (c.get("oracle_text") or "").lower()}
    if granted:
        print("\nGRANTS or CONDITIONS indestructible in its text — correctly "
              "NOT tagged\n(a tag would claim the permanent always has it):")
        for n in sorted(granted):
            print(f"    {n}")
    print(f"\nHUMAN ({len(humans)}) — Return of the Wildspeaker reads the "
          f"complement of this set:")
    for n in sorted(humans):
        print(f"    {n}")
    print(f"\nFOREST ({len(forests)}) — Sapling Nursery's affinity and Nissa, "
          f"Who Shakes the World\ncount these; a nonbasic that is not a Forest "
          f"is not one, however green it looks:")
    for n in sorted(forests):
        print(f"    {n}")

    missed = {n for n, c in cards.items()
              if n in creatures and n not in flying and n not in CONDITIONAL
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
            fh.write("}\n\n"
                     "# UNCONDITIONAL indestructible, every card type -- two of "
                     "them are LANDS,\n"
                     "# so L() has to consult this as well as C(). Granted "
                     "(Heroic Intervention,\n"
                     "# Boros Charm) and conditional (Voice of the Blessed at "
                     "ten counters)\n"
                     "# indestructibility is deliberately absent: a static tag "
                     "would be a lie.\n"
                     "INDESTRUCTIBLE = {\n")
            for n in sorted(indestructible):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\n"
                     "# SUBTYPES, read from the type line's subtype half.\n"
                     "# `Card.types` holds CARD types only, so a card that "
                     "reads a creature or\n"
                     "# land subtype has to consult these.\n"
                     "#\n"
                     "#   HUMAN   Return of the Wildspeaker counts and pumps "
                     "the COMPLEMENT of\n"
                     "#           this set. A Human missing from here would be "
                     "pumped and\n"
                     "#           counted when the card says it is not.\n"
                     "#   FOREST  Sapling Nursery's affinity, Nissa, Who Shakes "
                     "the World's mana\n"
                     "#           doubler, and Castle Garenbrig's "
                     "enters-untapped condition.\n"
                     "#           Dryad Arbor is one; no other nonbasic in any "
                     "list is.\n"
                     "HUMAN = {\n")
            for n in sorted(humans):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\nFOREST = {\n")
            for n in sorted(forests):
                fh.write(f"    {n!r},\n")
            fh.write("}\n")
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
