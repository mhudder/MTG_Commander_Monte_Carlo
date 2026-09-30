#!/usr/bin/env python3
"""What fraction of real Commander interaction does INDESTRUCTIBLE survive?

    python -m tools.removal_census            # print the census
    python -m tools.removal_census --write    # regenerate edhmc/decks/_removal.py

The pod's answers are anonymous rolls (§4), so `opponents.destroy` prices
indestructible with a share: the fraction of answers that DESTROY (or deal
damage) -- which indestructible survives -- rather than exile, bounce, shuffle,
tuck, sacrifice or shrink, which it does not. That share was one hand-written
0.60 for spot removal and wipes alike (queued item 7).

THE CENSUS IS THIS PROJECT'S OWN SIX LISTS: the interaction its owner's
playgroup actually builds with, read from Scryfall's oracle text and classified
by the explicit rules below -- not remembered. Two shares come out, one for
TARGETED removal and one for WIPES, and `opponents.destroy` reads them
(§0z87). It is a proxy for the pod's interaction and says so: the pod is three
unknown decks, and these are the six known ones at the same table.

Every card's class and the clause that decided it are written into the
generated file, so a misread rule is visible in review rather than hidden in a
number.
"""
import re
import sys

# Checked BEFORE the wipe rules: text that reads like a wipe and is not one.
EARLY_RULES = (
    # Vault 11: "destroy each creature with the most votes" -- targeted by vote.
    ("spot", "destroy", r"destroy each [^.]*with the most votes"),
    # Damn: "Destroy target creature ... Overload" -- at a Commander table it
    # is cast as the wipe. Destroy either way.
    ("wipe", "destroy", r"destroy target creature[^\n]*\n?overload"),
)
WIPE_RULES = (
    # (class, pattern) -- first match wins. "destroy" = indestructible SURVIVES.
    ("destroy", r"\bdestroy (all|each)\b"),
    ("destroy", r"deals (\d+|x) damage to each creature"),
    ("other", r"\bexile (all|each) (creatures?|nonland permanents?|artifacts?|"
              r"enchantments?|other)"),
    ("other", r"each creature gets -"),
    ("other", r"creatures [^.]*get -(\d+|x)/-(\d+|x)"),
    ("other", r"all creatures get -"),
    ("other", r"return (all|each) [^.]*to (its|their) owners?'? hands?"),
    ("other", r"sacrifices? the rest"),
    ("other", r"each (player|opponent) sacrifices (all|each)"),
)
SPOT_RULES = (
    ("destroy", r"\bdestroy (up to (one|two|three) )?(another )?target "
                r"([\w-]+,? )*(permanent|creature|artifact|enchantment|planeswalker)"),
    # "any target" is left out on purpose: Aetherflux Reservoir's 50 damage
    # is a win, not an answer (the first census counted it).
    ("destroy", r"deals (\d+|x) damage to target (creature|planeswalker)"),
    ("other", r"\bexile (up to (one|two|three) )?(another )?target "
              r"([\w-]+,? )*(permanent|creature|artifact|enchantment|planeswalker)"),
    ("other", r"target creature gets [+-](\d+|x)/-(\d+|x)"),
    ("other", r"exile each permanent with the most votes"),
    ("other", r"(target player|each opponent|target opponent) sacrifices"),
    ("other", r"target [^.]*gets -(\d+|x)/-(\d+|x)"),
    ("other", r"shuffles? (it|that permanent|target [^.]*) into"),
    ("other", r"put target [^.]*(on the (top|bottom)|into its owner's library)"),
    ("other", r"return target (nonland )?(permanent|creature)[^.]* to its "
              r"owner's hand"),
)
# "target creature you control" and friends are YOUR permanents: a blink or a
# protection spell, never an answer to the pod.
MINE = re.compile(r"target [^.]*you control")


def oracle_of(card):
    """The FRONT face's text for a modal double-faced card (its back is the
    land), every face otherwise."""
    faces = card.get("card_faces")
    if faces and "Land" in faces[-1].get("type_line", "") \
            and "Land" not in faces[0].get("type_line", ""):
        return faces[0].get("oracle_text", "")
    if faces:
        return "\n".join(f.get("oracle_text", "") for f in faces)
    return card.get("oracle_text", "")


def classify(text):
    """(kind, class, clause) or None. `kind` is "wipe" or "spot"."""
    low = text.lower()
    for kind, cls, pat in EARLY_RULES:
        m = re.search(pat, low)
        if m is not None:
            return kind, cls, m.group(0)[:120]
    for kind, rules in (("wipe", WIPE_RULES), ("spot", SPOT_RULES)):
        for cls, pat in rules:
            m = re.search(pat, low)
            if m is None:
                continue
            sentence = low[max(0, low.rfind(".", 0, m.start()) + 1):
                           low.find(".", m.end()) + 1 or len(low)].strip()
            if kind == "spot" and MINE.search(sentence):
                continue
            return kind, cls, sentence[:120]
    return None


def deck_lists():
    """deck -> every NONLAND name in its committed module list or its staged
    list. Needs no network, so `check_docs` compares it with SCANNED."""
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    per_deck = {}
    for deck in DECKS:
        staged, _ = build_pending(deck)
        module, _ = DECKS[deck].build()
        per_deck[deck] = sorted({c.name for c in list(staged) + list(module)
                                 if not c.is_land})
    return per_deck


def census():
    """(table, per_deck, scanned). A card is COUNTED once per deck that runs
    it -- in its committed module list or its staged list -- so an answer four
    decks play weighs four times: the unit is 'how often this table's decks
    hold this answer', not 'how many different answers exist'."""
    from tools.tag_flying import scryfall_collection
    per_deck = deck_lists()
    names = sorted({n for ns in per_deck.values() for n in ns})
    oracle = scryfall_collection(names)
    # A double-faced card comes back under its COMBINED name; the deck
    # modules call it by its front face. Index both.
    for full, card in list(oracle.items()):
        oracle.setdefault(full.split(" // ")[0], card)
    table = {}
    for n in names:
        card = oracle.get(n) or oracle.get(n.split(" // ")[0])
        if card is None:
            print(f"  NOT FOUND on Scryfall: {n}", file=sys.stderr)
            continue
        hit = classify(oracle_of(card))
        if hit is not None:
            table[n] = hit
    return table, per_deck, names


def is_ae(clause):
    """A targeted answer whose TARGET NOUN is an artifact or enchantment -- the
    pod's `ae_removal` event, Naturalize and Vandalblast's family. The noun is
    the first card-type word after "target", so "sacrifice this creature:
    exile target noncreature artifact" (Haywire Mite) reads as artifact: the
    first two versions of this test looked at the whole clause and dropped it."""
    m = re.search(r"target (?:[\w-]+,? |or )*?(artifact|enchantment|creature|"
                  r"permanent|planeswalker)\b", clause)
    return m is not None and m.group(1) in ("artifact", "enchantment")


KINDS = ("spot", "wipe", "ae")
# A share from fewer cards than this is not a measurement: that kind falls
# back to the SPOT share, which contains it. The artifact-and-enchantment
# subset is four cards in this census.
MIN_SAMPLE = 10


def share_value(sh, kind):
    d, t = sh[kind]
    if kind != "spot" and t < MIN_SAMPLE:
        d, t = sh["spot"]
    return d / max(1, t)


def shares(table, per_deck):
    """(destroy, total) per event kind, counted once per deck. `ae` is the
    artifact-and-enchantment-only subset of `spot`, and is also counted in
    it: the pod's spot removal can hit those too."""
    out = {}
    for kind in KINDS:
        rows = [table[n][1] for ns in per_deck.values() for n in ns
                if n in table and (table[n][0] == kind if kind != "ae" else
                                   table[n][0] == "spot" and is_ae(table[n][2]))]
        out[kind] = (sum(c == "destroy" for c in rows), len(rows))
    return out


def render(table, per_deck, scanned):
    sh = shares(table, per_deck)
    lines = [
        '"""GENERATED by `python -m tools.removal_census --write` -- do not edit.',
        "",
        "Every targeted answer and every wipe in the six current lists, classified",
        "from Scryfall oracle text: 'destroy' is destroy or damage (indestructible",
        "survives), 'other' is exile, bounce, tuck, shuffle, sacrifice or -X/-X",
        "(it does not). `opponents.destroy` prices indestructible with the two",
        'shares below (§0z87)."""',
        "",
        "# counted once per deck that runs the card: "
        + "; ".join(f"{k} {sh[k][0]} of {sh[k][1]} destroy" for k in KINDS),
        f"# a kind with fewer than {MIN_SAMPLE} cards takes the SPOT share"
        f" (ae has {sh['ae'][1]})",
        f"DESTROY_SHARE_SPOT = {share_value(sh, 'spot'):.4f}",
        f"DESTROY_SHARE_WIPE = {share_value(sh, 'wipe'):.4f}",
        f"DESTROY_SHARE_AE = {share_value(sh, 'ae'):.4f}",
        "",
        "# name -> (kind, class, the clause that decided it)",
        "INTERACTION = {",
    ]
    for n, (k, c, clause) in sorted(table.items()):
        lines.append(f"    {n!r}: ({k!r}, {c!r}, {clause!r}),")
    lines += ["}", "", "# deck -> the interaction it runs, as counted above",
              "RUN_BY = {"]
    for d, ns in sorted(per_deck.items()):
        lines.append(f"    {d!r}: {sorted(n for n in ns if n in table)!r},")
    lines += ["}", "", "# every nonland name the census read", "SCANNED = {"]
    lines += [f"    {n!r}," for n in scanned]
    lines += ["}", ""]
    return "\n".join(lines)


def main() -> int:
    table, per_deck, scanned = census()
    sh = shares(table, per_deck)
    for kind in KINDS:
        d, t = sh[kind]
        print(f"{kind:<5} {d} of {t} destroy -> {d / max(1, t):.3f}")
        for n, (k, c, clause) in sorted(table.items()):
            if (k == kind if kind != "ae" else k == "spot" and is_ae(clause)):
                print(f"    {c:<8} {n:<42} {clause[:70]}")
    if "--write" in sys.argv:
        open("edhmc/decks/_removal.py", "w").write(render(table, per_deck,
                                                          scanned))
        print("wrote edhmc/decks/_removal.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
