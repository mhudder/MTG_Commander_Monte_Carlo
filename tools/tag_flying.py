#!/usr/bin/env python3
"""Fetch FLYING and INDESTRUCTIBLE for every card in every current deck, from Scryfall.

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

    python -m tools.tag_flying            # print the classification
    python -m tools.tag_flying --write    # regenerate edhmc/decks/_evasion.py
"""
import json
import re
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
    "Spirit",   # Benevolent Offering: "three 1/1 white Spirit ... with flying"
                # (shilgengar's Spirits fly too, set on its own constructor)
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


BASIC_TYPES = ("Plains", "Island", "Swamp", "Mountain", "Forest")
_TYPE = r"(Plains|Island|Swamp|Mountain|Forest)"
_COLOURS = {"W", "U", "B", "R", "G"}


def land_oracle(card) -> str:
    """The FRONT face's text: a modal or transforming land enters as its
    front face, and the back's text is not a rule about how it enters."""
    if card.get("oracle_text") is not None:
        return card["oracle_text"]
    faces = card.get("card_faces") or [{}]
    return faces[0].get("oracle_text") or ""


def classify_land(text: str) -> dict:
    """What a land's ORACLE TEXT says about entering, tapping and life, as
    data (§0z115). Each key is one rule the engines read from
    `edhmc.lands`; a land with none of them returns {}.

      etb       how it enters: ("tapped",), ("shock",), ("fast",), ("slow",),
                ("battle",), ("bond",), ("check", types), ("reveal", types),
                ("count", type, n)
      pain      (life, colours, always): a mana ability that hurts -- the
                painlands only for a colour, the horizon lands on every tap
      fetch     (life, types, mode): "{T}, [Pay 1 life,] Sacrifice: search
                ... put it onto the battlefield[ tapped]"; types () = any
                basic; mode "untapped" / "tapped" / "untap4" (Fabled Passage)
      karoo     True: "return a land you control to its owner's hand"
      only_if   ("control", type) or ("lands", n): a mana ability that works
                only under a condition (Tainted Field, Temple of the False God)

    RAISES on enters-tapped text it cannot read. A rule guessed from a near
    miss is the partial-tag bias this generator exists to prevent (§0z29);
    an unread rule stops the generator instead."""
    out: dict = {}
    t = " ".join(text.split())
    low = t.lower()
    m = re.search(r"enters tapped unless you control an? " + _TYPE
                  + r"(?: or an? " + _TYPE + r")?\.", t)
    if m:
        out["etb"] = ("check", tuple(x for x in m.groups() if x))
    elif "unless you control two or fewer other lands" in low:
        out["etb"] = ("fast",)
    elif "unless you control two or more other lands" in low:
        out["etb"] = ("slow",)
    elif "unless you control two or more basic lands" in low:
        out["etb"] = ("battle",)
    elif "unless you have two or more opponents" in low:
        out["etb"] = ("bond",)
    elif (m := re.search(r"unless you control (\w+) or more other "
                         + _TYPE + r"s\.", t)):
        n = {"two": 2, "three": 3, "four": 4}[m.group(1)]
        out["etb"] = ("count", m.group(2), n)
    elif (m := re.search(r"you may reveal an? " + _TYPE + r" or " + _TYPE
                         + r" card from your hand\. If you don't, this land "
                         r"enters tapped", t)):
        out["etb"] = ("reveal", m.groups())
    elif "you may pay 2 life. if you don't, it enters tapped" in low:
        out["etb"] = ("shock",)
    elif re.search(r"(?:^|[.)] )this land enters tapped\.", low):
        out["etb"] = ("tapped",)
    elif "enters tapped" in low and "onto the battlefield tapped" not in low:
        raise ValueError(f"unread enters-tapped rule: {t!r}")
    m = re.search(r"\{T\}: Add ([^.]*)\. This land deals (\d) damage to you",
                  t)
    if m:
        # A painless "{T}: Add {C}." beside it makes the pain a price of the
        # COLOURS (a painland); with no such mode every tap hurts (Ancient
        # Tomb, whose only ability is the painful one).
        painless = re.search(r"(?:^|\. )\{T\}: Add \{C\}\.", t) is not None
        out["pain"] = (int(m.group(2)),
                       tuple(sorted(set(re.findall(r"\{([WUBRG])\}",
                                                   m.group(1))))),
                       not painless)
    m = re.search(r"\{T\}, Pay (\d) life: Add ([^.]*)\.", t)
    if m:
        out["pain"] = (int(m.group(1)),
                       tuple(sorted(set(re.findall(r"\{([WUBRG])\}",
                                                   m.group(2))))), True)
    m = re.search(r"\{T\}, (?:Pay (\d) life, )?Sacrifice this land: Search "
                  r"your library for (a basic land card|an? " + _TYPE
                  + r" or " + _TYPE + r" card), put it onto the battlefield"
                  r"( tapped)?", t)
    if m:
        types = () if m.group(2).startswith("a basic") else \
            (m.group(3), m.group(4))
        mode = "tapped" if m.group(5) else "untapped"
        if "if you control four or more lands, untap that land" in low:
            mode = "untap4"
        out["fetch"] = (int(m.group(1) or 0), types, mode)
    if "return a land you control to its owner's hand" in low:
        out["karoo"] = True
    # A condition on a MANA ability only -- Cryptic Caves' "Activate only if
    # you control five or more lands" is on its sacrifice ability and is not
    # a rule about its mana. The gated colours are carried: Tainted Field
    # loses {W}/{B} without a Swamp and keeps its {C}.
    m = re.search(r"\{T\}: Add ([^.]*)\. Activate only if you control an? "
                  + _TYPE + r"\.", t)
    if m:
        out["only_if"] = ("control", m.group(2),
                          tuple(sorted(set(re.findall(r"\{([WUBRGC])\}",
                                                      m.group(1))))))
    m = re.search(r"\{T\}: Add ([^.]*)\. Activate only if you control "
                  r"(\w+) or more lands\.", t)
    if m:
        out["only_if"] = ("lands", {"five": 5, "four": 4, "three": 3,
                                    "seven": 7}[m.group(2)],
                          tuple(sorted(set(re.findall(r"\{([WUBRGC])\}",
                                                      m.group(1))))))
    return out


_PIP = re.compile(r"\{([^}]+)\}")


def flashback_cost(text: str):
    """The cost on a card's own "Flashback {..}" line, as a C() cost dict, or
    None when the card has no such line (it only GRANTS flashback). Raises on
    a flashback cost this cannot read -- hybrid, X, Phyrexian, or a non-mana
    cost -- because a misread cost would be a cast at the wrong price, and an
    unread one a card that silently has no flashback (classify_land's rule).
    """
    m = re.search(r"^Flashback(?:\s|—)(.*)$", text, re.M)
    if m is None:
        return None
    rest = m.group(1).split("(")[0].strip()
    if not re.fullmatch(r"(\{[^}]+\})+", rest):
        raise ValueError(f"tag_flying: unreadable flashback cost {rest!r}")
    cost = {}
    for pip in _PIP.findall(rest):
        if pip.isdigit():
            cost["gen"] = cost.get("gen", 0) + int(pip)
        elif pip in ("W", "U", "B", "R", "G", "C"):
            cost[pip] = cost.get(pip, 0) + 1
        else:
            raise ValueError(f"tag_flying: unreadable flashback pip {{{pip}}}")
    return cost


def current_cards(decks=None):
    """(creatures, everything) -- every Card the current deck modules
    construct, deck members and module-level candidates alike.

    Factored out of main() on 2026-09-17 so `check_docs` can ask the same
    question WITHOUT Scryfall: is every card here in `_evasion.SCANNED`? If
    not, a card was added and this generator was not re-run -- which is how
    Bloodthirsty Conqueror was measured as a ground creature (§0z29).
    """
    decks = decks if decks is not None else discover_current_decks()
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
    return creatures, everything


def main():
    # DISCOVERED, not named by hand: see edhmc.decks.discover_current_decks.
    # A newly added "<name>_v1.py" with a build() is tagged the first time
    # this runs, with no edit here — the same fix `audit_cards.py` got, for
    # the same reason: this file's own history is the SCRIPTED_* class of bug.
    decks = discover_current_decks()
    creatures, everything = current_cards(decks)

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
    # MENACE, 2026-09-26 (§0z61): "can't be blocked except by two or more
    # creatures". Creatures only, for flying's reason: a card that GRANTS
    # menace (Edgar's "he gains menace") carries the keyword too, and that is
    # conditional, so it is not a tag.
    menace = {n for n, c in cards.items()
              if n in creatures and "Menace" in c.get("keywords", [])
              and "gains menace" not in (c.get("oracle_text") or "").lower()}
    # TRAMPLE, 2026-09-30 (§0z92): a blocked trampler assigns the damage its
    # blockers cannot absorb to the player. Creatures only and unconditional
    # only, for menace's reason: the keywords array also carries GRANTS
    # ("creatures you control gain trample") and conditions ("has trample as
    # long as"), and neither is a fact about the permanent.
    trample = {n for n, c in cards.items()
               if n in creatures and "Trample" in c.get("keywords", [])
               and not re.search(r"(gains?|have|has) trample",
                                 (c.get("oracle_text") or "").lower())}
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
    # PLAINS, 2026-10-01, with the trostani deck: its fetchlands say "search
    # your library for a Forest or Plains CARD" and Fortified Village reveals
    # "a Forest or Plains card" -- a dual whose type line says Plains is one
    # (Temple Garden, Canopy Vista), a Command Tower is not. FOREST's rule.
    plains = {n for n, c in cards.items()
              if n in everything and everything[n].is_land
              and "Plains" in subtypes(c)}
    # LEGENDARY, 2026-10-01, with the trostani deck: a token COPY of a
    # legendary permanent puts two of one name on the battlefield and the
    # legend rule (704.5j) takes one. Bramble Sovereign, populate and Mimic
    # Vat can all make such a copy, so the engine has to know which names are
    # legendary. The SUPERTYPE half of the type line -- the half `subtypes`
    # drops -- and every card type, since a legendary land or artifact
    # (Yavimaya Hollow, Alhammarret's Archive) obeys the same rule.
    legendary = {n for n, c in cards.items()
                 if n in everything and any(
                     "Legendary" in (line.split("—", 1)[0])
                     for line in [c.get("type_line") or ""] + [
                         f.get("type_line") or ""
                         for f in c.get("card_faces", []) or []])}
    # ELF_ELEMENTAL is NOT restricted to creatures, unlike HUMAN. Nissa,
    # Resurgent Animist reveals until it reveals "an Elf or Elemental CARD",
    # and a card carries its subtypes in every zone -- a tribal or enchantment
    # card with the subtype would count. Nothing in these lists is one today;
    # restricting the set to creatures would make that a silent assumption
    # instead of a fact about the lists.
    elf_elemental = {n for n, c in cards.items()
                     if n in everything and ({"Elf", "Elemental"} & subtypes(c))}
    # PLANT, 2026-10-03 (§0z101): Avenger of Zendikar pumps "each PLANT
    # creature you control", and Bristly Bill, Spine Sower is a Plant Druid --
    # so a card, not only Avenger's own tokens, can be one. Creatures only:
    # the clause says "Plant creature".
    plants = {n for n, c in cards.items()
              if n in creatures and "Plant" in subtypes(c)}
    # ANGEL and CLERIC, 2026-10-07 (§0z117): shilgengar's tribal payoffs read
    # them, and its hand-typed tags had Avacyn, Angel of Hope and Angel of
    # Suffering as non-Angels and Bishop of Wings as no Cleric (§0z116 item 4).
    # Creatures only: every payoff says "Angel creature" or reads a creature.
    angels = {n for n, c in cards.items()
              if n in creatures and "Angel" in subtypes(c)}
    clerics = {n for n, c in cards.items()
               if n in creatures and "Cleric" in subtypes(c)}

    # LANDS, 2026-10-06 (§0z115): each land's basic land types and the rules
    # its own text states about entering, tapping and life -- read from
    # Scryfall like every set above, never tagged by hand. `edhmc.lands`
    # reads both, for every engine that plays lands through it.
    land_types = {n: tuple(t for t in BASIC_TYPES if t in subtypes(c))
                  for n, c in cards.items()
                  if n in everything and everything[n].is_land
                  and set(BASIC_TYPES) & subtypes(c)}
    # FLASHBACK, 2026-10-09: "You may cast this card from your graveyard for
    # its flashback cost. Then exile it." (702.34a.) The keyword says the card
    # HAS it -- a GRANT (Past in Flames' "gains flashback") carries the
    # keyword too, so the cost is read from the card's own "Flashback {..}"
    # line and a card whose line is not a mana cost raises rather than
    # becoming a free cast. Lorehold is the only reader (`lorehold.
    # flashback_options`); every other engine ignores the table.
    flashback = {}
    for n, c in cards.items():
        if n in everything and "Flashback" in c.get("keywords", []):
            cost = flashback_cost(c.get("oracle_text") or "")
            if cost is not None:
                flashback[n] = cost

    land_rules = {}
    for n, c in cards.items():
        if n in everything and everything[n].is_land:
            rule = classify_land(land_oracle(c))
            if rule:
                land_rules[n] = rule

    print(f"{len(cards)}/{len(everything)} cards resolved "
          f"({len(creatures)} of them creatures)\n")
    print(f"UNCONDITIONAL FLYING ({len(flying)}):")
    for n in sorted(flying):
        print(f"    {n}")
    print(f"\nUNCONDITIONAL MENACE ({len(menace)}):")
    for n in sorted(menace):
        print(f"    {n}")
    print(f"\nUNCONDITIONAL TRAMPLE ({len(trample)}):")
    for n in sorted(trample):
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
    print(f"\nPLAINS ({len(plains)}) — a fetchland's or Fortified Village's "
          f"'Plains card':")
    for n in sorted(plains):
        print(f"    {n}")
    print(f"\nLEGENDARY ({len(legendary)}) — the legend rule on a token copy:")
    for n in sorted(legendary):
        print(f"    {n}")
    print(f"\nELF or ELEMENTAL ({len(elf_elemental)}) — what Nissa, Resurgent "
          f"Animist can reveal.\nThe hit RATE is the card, so a name missing "
          f"here is a whiff that should have been a card:")
    for n in sorted(elf_elemental):
        print(f"    {n:34} {' '.join(sorted({'Elf', 'Elemental'} & subtypes(cards[n])))}")

    print(f"\nPLANT ({len(plants)}) — Avenger of Zendikar's landfall pumps "
          f"these as well as its tokens:")
    for n in sorted(plants):
        print(f"    {n}")

    print(f"\nFLASHBACK ({len(flashback)}) -- the card's own flashback cost:")
    for n in sorted(flashback):
        print(f"    {n:42} {flashback[n]}")

    print(f"\nLAND RULES ({len(land_rules)}) -- entering, tapping and life, "
          f"from the oracle text:")
    for n in sorted(land_rules):
        print(f"    {n:42} {land_rules[n]}")

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
                     f"Unconditional flying for every creature in the {len(decks)} decks,\n"
                     "read from Scryfall's `keywords` array. Conditional fliers are\n"
                     "NOT here: see opponents.flying_of(). Regenerate with\n"
                     "`python -m tools.tag_flying --write` after any deck change.\n"
                     '"""\n\nFLYING = {\n')
            for n in sorted(flying):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\n# Unconditional menace (creatures only), from the "
                     "same keywords array.\n# Read by opponents.menace_of(): a "
                     "menace attacker costs two blockers.\nMENACE = {\n")
            for n in sorted(menace):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\n# Unconditional trample (creatures only), from the "
                     "same keywords array.\n# Read by opponents.trample_of(): a "
                     "blocked trampler assigns the excess (§0z92).\nTRAMPLE = {\n")
            for n in sorted(trample):
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
                     "#   ELF_ELEMENTAL\n"
                     "#           Nissa, Resurgent Animist reveals until it "
                     "hits one of these, so\n"
                     "#           the SIZE of this set is most of what that "
                     "card is worth. NOT\n"
                     "#           restricted to creatures: the card says 'Elf "
                     "or Elemental CARD',\n"
                     "#           and a card carries its subtypes in every "
                     "zone.\n"
                     "HUMAN = {\n")
            for n in sorted(humans):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\nFOREST = {\n")
            for n in sorted(forests):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\n# PLAINS: the land half of 'a Forest or Plains card' "
                     "(trostani's fetches,\n# Fortified Village). FOREST's rule.\n"
                     "PLAINS = {\n")
            for n in sorted(plains):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\n# LEGENDARY, every card type, from the type line's "
                     "supertype half.\n# A token copy of one of these meets the "
                     "legend rule (704.5j).\nLEGENDARY = {\n")
            for n in sorted(legendary):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\nELF_ELEMENTAL = {\n")
            for n in sorted(elf_elemental):
                fh.write(f"    {n!r},\n")
            fh.write("}\n")
            fh.write("\n# PLANT creature cards: Avenger of Zendikar's landfall "
                     "puts a counter on\n# each Plant creature you control, "
                     "and that is not only its tokens.\nPLANT = {\n")
            for n in sorted(plants):
                fh.write(f"    {n!r},\n")
            fh.write("}\n")
            fh.write("\n# ANGEL and CLERIC creature cards (§0z117): "
                     "shilgengar's tribe, from the type\n# line -- its "
                     "`angel`/`cleric` tags are derived from these.\n"
                     "ANGEL = {\n")
            for n in sorted(angels):
                fh.write(f"    {n!r},\n")
            fh.write("}\n\nCLERIC = {\n")
            for n in sorted(clerics):
                fh.write(f"    {n!r},\n")
            fh.write("}\n")
            fh.write("\n# LAND TYPES: a land's basic land types (Plains, "
                     "Island, Swamp, Mountain,\n# Forest), from the type line. "
                     "A check land, a snarl, a fetch and Witch's\n# Cottage "
                     "read these (§0z115).\nLAND_TYPES = {\n")
            for n in sorted(land_types):
                fh.write(f"    {n!r}: {land_types[n]!r},\n")
            fh.write("}\n")
            fh.write("\n# LAND RULES: what each land's own text says about "
                     "entering, tapping and\n# life, classified by "
                     "`tag_flying.classify_land` (which raises on text it\n# "
                     "cannot read). Read by `edhmc.lands` (§0z115).\n"
                     "LAND_RULES = {\n")
            for n in sorted(land_rules):
                fh.write(f"    {n!r}: {land_rules[n]!r},\n")
            fh.write("}\n")
            fh.write("\n# FLASHBACK: a card's OWN flashback cost, from its "
                     "\"Flashback {..}\" line\n# (a grant such as Past in "
                     "Flames' carries the keyword and no cost, and\n# is not "
                     "here). Read by lorehold's main phase (702.34a).\n"
                     "FLASHBACK = {\n")
            for n in sorted(flashback):
                fh.write(f"    {n!r}: {flashback[n]!r},\n")
            fh.write("}\n")
            fh.write("\n# EVERY CARD NAME THIS RUN SCANNED, deck members and "
                     "module-level candidates\n"
                     "# alike. `check_docs` compares it with the cards the deck "
                     "modules construct\n"
                     "# TODAY and fails on any difference: a card added without "
                     "re-running this\n"
                     "# generator is constructed with flying=False whatever "
                     "Scryfall says (§0z29).\n"
                     "SCANNED = {\n")
            for n in sorted(everything):
                fh.write(f"    {n!r},\n")
            fh.write("}\n")
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
