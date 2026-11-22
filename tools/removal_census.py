#!/usr/bin/env python3
"""What fraction of real Commander interaction does INDESTRUCTIBLE survive?

    python -m tools.removal_census            # print the census
    python -m tools.removal_census --write    # regenerate edhmc/decks/_removal.py
                                              # and edhmc/decks/_pod_mana.py

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
    table, counters = {}, {}
    census.spell_mv = {}
    census.oracle = oracle
    for n in names:
        card = oracle.get(n) or oracle.get(n.split(" // ")[0])
        if card is None:
            print(f"  NOT FOUND on Scryfall: {n}", file=sys.stderr)
            continue
        hit = classify(oracle_of(card))
        if hit is not None:
            table[n] = hit
            # §0z224: a SPOT answer that is a SPELL (an instant or sorcery):
            # its mana value, for what the pod's removal costs
            # (`SPOT_SPELL_MV`). Creatures and permanents that remove on
            # entering or by an ability are not spells cast at a target.
            tl = card.get("type_line", "")
            if hit[0] == "spot" and ("Instant" in tl or "Sorcery" in tl):
                census.spell_mv[n] = float(card.get("cmc", 0))
        ctr = classify_counter(oracle_of(card))
        if ctr is not None:
            counters[n] = ctr
    return table, per_deck, names, counters


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


# COUNTERSPELLS (item 24, change 3; §0z134): what each one can counter, from
# the clause, so `opponents.counter_hits` decides without a hand list. First
# match wins. An ability counter ("counter target activated ability") is not
# a spell counter and is not read.
COUNTER_RULES = (
    ("instant_sorcery", r"counter target instant or sorcery spell"),
    ("noncreature", r"counter target noncreature spell"),
    ("spell", r"counter target spell"),
)


def classify_counter(text):
    """(what, clause) or None."""
    low = text.lower()
    for what, pat in COUNTER_RULES:
        m = re.search(pat, low)
        if m is not None:
            end = low.find(".", m.end())
            return what, low[m.start():(end + 1) if end >= 0 else None][:120]
    return None


def spot_spell_mv(per_deck) -> float:
    """§0z224: the MEDIAN mana value of the spot-removal SPELLS in the six
    lists, each counted once per deck that runs it (the shares' unit) --
    what the pod's spot removal costs, which `opponents.ward_choice` reads.
    Our lists stand for the pod's, as they do for the destroy shares."""
    mvs = sorted(mv for d, ns in per_deck.items() for n in ns
                 for mv in [getattr(census, "spell_mv", {}).get(n)]
                 if mv is not None)
    if not mvs:
        return 2.0
    k = len(mvs)
    return mvs[k // 2] if k % 2 else (mvs[k // 2 - 1] + mvs[k // 2]) / 2.0


def render(table, per_deck, scanned, counters=None):
    sh = shares(table, per_deck)
    mv_n = sum(1 for d, ns in per_deck.items() for n in ns
               if n in getattr(census, "spell_mv", {}))
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
        "# the median mana value of the spot-removal SPELLS (instants and "
        f"sorceries), {mv_n} counted",
        "# once per deck that runs one: what the pod's spot removal costs, "
        "read by",
        "# `opponents.ward_choice` (§0z224)",
        f"SPOT_SPELL_MV = {spot_spell_mv(per_deck):.1f}",
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
    lines += ["}", "", "# name -> (what it counters, the clause): spell, noncreature or",
              "# instant_sorcery (§0z134)", "COUNTERS = {"]
    for n, (w, clause) in sorted((counters or {}).items()):
        lines.append(f"    {n!r}: ({w!r}, {clause!r}),")
    lines += ["}", "", "# every nonland name the census read", "SCANNED = {"]
    lines += [f"    {n!r}," for n in scanned]
    lines += ["}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# THE POD'S MANA (queue item 50, §0z235): lands, ramp and what answers cost
# ---------------------------------------------------------------------------
# The pod's library is the six lists' (the owner, 2026-11-20: "model the
# library, based on the decklists"). Its land count and its ramp are read
# from each deck's COMMITTED MODULE list -- not the staged one, so staging a
# land swap in one deck does not move every deck's pod (§0z126's hazard) --
# and the costs of its answers from the lists the shares read (module or
# staged), SPOT_SPELL_MV's rule. Ramp is mana ROCKS and LAND RAMP only
# (decision 2): anything whose mana leaves with a creature -- a creature's
# {T}: Add, a creature's "play an additional land" -- is queue item 52.
#
# EVERY CARD WHOSE TEXT READS LIKE MANA IS CLASSIFIED OR THE CENSUS RAISES
# (§0z115's rule for lands, applied to ramp): `RAMP_CANDIDATE` decides what
# must be read; a candidate no rule reads is an error naming the card.
RAMP_CANDIDATE = re.compile(
    r"\badd (\{|one |two |three |x |ten |an additional|mana |an amount )|"
    r"additional lands?|"
    r"tapped for mana|land cards?[^.]*onto the battlefield|treasure tokens?")
# (reason, pattern): NOT the pod's ramp. First match wins, checked first.
NOT_RAMP_RULES = (
    # Your spell hands the TARGET'S CONTROLLER mana: under item 50 that is
    # the pod ramping off your removal. Kept as `POD_GIFTS`, for the engine.
    # And your permanent that hands EACH OPPONENT WHO TAKES IT a Treasure
    # (Tempting Contract, Master of Ceremonies, §0z245): the census read
    # only the first wording until 2026-11-22, so the second was free.
    ("gift", r"its controller (may search their library for a basic land|"
             r"creates (a|an|one|two|three|\w+) treasure)|"
             r"each opponent may create a treasure|"
             r"you and that player each create a treasure"),
    # A Treasure is one-shot mana (111.10a), not a source.
    ("treasure", r"\btreasure tokens?\b"),
    ("sacrifice outlet", r"(^|\n)sacrifice a creature: add"),
    ("net zero", r"as an additional cost to cast this spell, sacrifice a land"),
    ("symmetric", r"each player may play an additional land"),
    ("land trigger", r"whenever (you tap a land for mana|a land you control "
                     r"enters), add"),
    ("fixing", r"lands tapped for mana produce mana of the chosen color"),
    ("reveal", r"reveal the top [^.]*\.? ?[^.]*land cards?[^.]*onto the "
               r"battlefield"),
    ("repeatable outlet", r"sacrifice a creature: search your library for "
                          r"[^.]*land"),
    ("modal", r"you may play up to \w+ additional lands this turn"),
)
CREATURE_MANA = re.compile(r"(^|\n|\")\{t\}[^:\n]*: add|you may play an "
                           r"additional land")
ROCK_ABILITY = re.compile(r"(?:^|\n)((?:\{[^}]+\}, )*\{t\}(?:, [^:\n]*)?): "
                          r"add ([^.\n]*)")
LAND_FETCH = re.compile(
    r"search your library for (?:up to (one|two|three) )?[^.]*?land cards?"
    r"[^.]*?put (them|it|that card|one|those cards)[^.]*? onto the "
    r"battlefield( tapped)?")
EXTRA_DROP = re.compile(r"you may play an additional land on each of your "
                        r"turns")
WORDS = {"one": 1, "two": 2, "three": 3}


def generic(cost: str) -> int:
    """The generic mana in a cost string: "{1}, {T}" is 1, "{T}" is 0."""
    return sum(int(x) for x in re.findall(r"\{(\d+)\}", cost))


def produced(add: str, name: str) -> int:
    """How much mana one activation adds: "{C}{C}" is 2, "{R} or {W}" is 1,
    "one mana of any color" is 1. Raises on text it cannot read."""
    best = 0
    for alt in add.split(" or "):
        n = len(re.findall(r"\{[wubrgc]\}", alt))
        m = re.match(r"\s*(one|two|three) mana\b", alt)
        if m:
            n = max(n, WORDS[m.group(1)])
        best = max(best, n)
    if best <= 0:
        raise ValueError(f"mana census: cannot read how much {name!r} adds: "
                         f"{add!r}")
    return best


def mv_of_cost(cost: str) -> float:
    """Mana value of a mana-cost string ("{2}{W}{W}" is 4; X is 0)."""
    mv = 0
    for sym in re.findall(r"\{([^}]+)\}", cost):
        if sym.isdigit():
            mv += int(sym)
        elif sym.lower() != "x":
            mv += 1
    return float(mv)


def classify_ramp(name: str, type_line: str, text: str, mv: float):
    """One card's mana, for the pod's library. Returns None (not mana), or

        ("rock", mv, net mana a turn, flags, clause)   a noncreature permanent
                                                       with a repeatable {T}: Add
        ("land", total cost, lands onto the battlefield, flags, clause)
        ("drop", mv, extra land drops a turn, flags, clause)
        ("not", reason, clause)                        read, and not ramp

    `flags` is a tuple: "tapped" (enters, or puts its land, tapped),
    "untaps_each_turn" (Bender's Waterskin). Raises on a candidate it cannot
    read."""
    low = text.lower()
    if not RAMP_CANDIDATE.search(low):
        return None
    for reason, pat in NOT_RAMP_RULES:
        m = re.search(pat, low)
        if m:
            return ("not", reason, m.group(0).strip()[:120])
    creature = "Creature" in type_line
    if creature and CREATURE_MANA.search(low) and not LAND_FETCH.search(low):
        return ("not", "on a creature: queue item 52",
                CREATURE_MANA.search(low).group(0).strip()[:120])
    if ("Instant" in type_line or "Sorcery" in type_line) \
            and re.search(r"\badd\b", low) and not LAND_FETCH.search(low):
        return ("not", "ritual: one-shot mana", re.search(
            r"[^.\n]*\badd\b[^.\n]*", low).group(0).strip()[:120])
    flags = []
    if not creature and ("Artifact" in type_line or "Enchantment" in type_line):
        nets = [produced(add, name) - generic(cost)
                for cost, add in ROCK_ABILITY.findall(low)
                if "sacrifice" not in cost]
        if nets:
            if re.search(r"enters tapped", low):
                flags.append("tapped")
            if re.search(r"untap this \w+ during each other player's untap "
                         r"step", low):
                flags.append("untaps_each_turn")
            return ("rock", float(mv), max(nets), tuple(flags),
                    ROCK_ABILITY.search(low).group(0).strip()[:120])
    m = LAND_FETCH.search(low)
    if m:
        n = 1
        if m.group(2) in ("them", "those cards") and m.group(1):
            n = WORDS[m.group(1)]
        if m.group(3):
            flags.append("tapped")
        line = low[:m.start()].rsplit("\n", 1)[-1]
        cost = float(mv) + (generic(line.split(":")[0]) if ":" in line else 0)
        return ("land", cost, n, tuple(flags), m.group(0)[:120])
    if not creature and EXTRA_DROP.search(low):
        return ("drop", float(mv), 1, (), EXTRA_DROP.search(low).group(0))
    raise ValueError(f"mana census: {name!r} reads like mana and no rule "
                     f"reads it: {text[:160]!r}")


def read_gift(name: str, text: str) -> tuple:
    """(kind, amount, tapped, clause) of a card that hands the TARGET'S
    CONTROLLER mana (§0z241): "land" -- a basic onto the battlefield, tapped
    or not -- or "treasure", how many. A symmetric gift (§0z245) is one
    Treasure for EACH opponent who takes it: the amount is per taker, and
    the engine gives it once per taker. Raises on a gift it cannot read."""
    low = text.lower()
    m = re.search(r"each opponent may create a treasure token|you and that "
                  r"player each create a treasure token", low)
    if m:
        return ("treasure", 1, False, m.group(0)[:120])
    m = re.search(r"its controller may search their library for a basic "
                  r"land card, put (it|that card) onto the battlefield"
                  r"( tapped)?", low)
    if m:
        return ("land", 1, bool(m.group(2)), m.group(0)[:120])
    m = re.search(r"its controller creates (a|an|one|two|three) treasure",
                  low)
    if m:
        n = {"a": 1, "an": 1}.get(m.group(1)) or WORDS[m.group(1)]
        return ("treasure", n, False, m.group(0)[:120])
    raise ValueError(f"mana census: cannot read {name!r}'s gift: "
                     f"{text[:160]!r}")


def module_lists():
    """deck -> every card name in its COMMITTED MODULE list (the 99), lands
    included. Needs no network, so `check_docs` compares it with
    `_pod_mana.MODULE_LISTS`."""
    from edhmc.registry import DECKS
    return {d: sorted(c.name for c in DECKS[d].build()[0]) for d in DECKS}


def median(xs) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = len(xs)
    return float(xs[k // 2]) if k % 2 else (xs[k // 2 - 1] + xs[k // 2]) / 2.0


def mana_census(oracle, table, counters, per_deck):
    """Everything `_pod_mana.py` holds; see `render_mana`."""
    from edhmc.registry import DECKS
    ramp, not_ramp, gifts = {}, {}, {}
    lands, sizes, mod = {}, {}, module_lists()
    for d in DECKS:
        deck = DECKS[d].build()[0]
        lands[d] = sum(1 for c in deck if c.is_land)
        sizes[d] = len(deck)
    names = sorted({n for ns in per_deck.values() for n in ns}
                   | {n for ns in mod.values() for n in ns})
    for n in names:
        card = oracle.get(n) or oracle.get(n.split(" // ")[0])
        if card is None:
            continue
        tl = card.get("type_line", "")
        if "Land" in tl.split(" // ")[0]:
            continue
        hit = classify_ramp(n, tl, oracle_of(card), card.get("cmc", 0))
        if hit is None:
            continue
        if hit[0] == "not":
            not_ramp[n] = hit[1:]
            if hit[1] == "gift":
                gifts[n] = read_gift(n, oracle_of(card))
        else:
            ramp[n] = hit
    by_deck = {d: sorted(n for n in mod[d] if n in ramp) for d in DECKS}

    def per(kind):
        return [sum(1 for n in by_deck[d] if ramp[n][0] == kind) for d in DECKS]

    def vals(kind, i):
        return [ramp[n][i] for d in DECKS for n in by_deck[d]
                if ramp[n][0] == kind]

    def spell_costs(names_ok):
        """(median, counted, X spells left out): instants and sorceries,
        once per deck that runs one (SPOT_SPELL_MV's unit). A card whose
        answer is its OVERLOAD (Damn) is costed at the overload."""
        out, xs = [], 0
        for d, ns in per_deck.items():
            for n in ns:
                if not names_ok(n):
                    continue
                card = oracle.get(n) or oracle.get(n.split(" // ")[0])
                tl = card.get("type_line", "").split(" // ")[0]
                if "Instant" not in tl and "Sorcery" not in tl:
                    continue
                text = oracle_of(card).lower()
                ov = re.search(r"overload (\{[^}]+\})+", text)
                if ov and table.get(n, ("",))[0] == "wipe":
                    out.append(mv_of_cost(ov.group(0)))
                    continue
                cost = card.get("mana_cost") or (card.get("card_faces") or
                                                 [{}])[0].get("mana_cost", "")
                if "{X}" in cost:
                    xs += 1
                    continue
                out.append(float(card.get("cmc", 0)))
        return median(out), len(out), xs

    costs = {
        "wipe": spell_costs(lambda n: table.get(n, ("",))[0] == "wipe"),
        "ae": spell_costs(lambda n: n in table and table[n][0] == "spot"
                          and is_ae(table[n][2])),
        "counter": spell_costs(lambda n: n in counters),
    }
    return dict(ramp=ramp, not_ramp=not_ramp, gifts=gifts, lands=lands,
                sizes=sizes, by_deck=by_deck, per=per, vals=vals,
                costs=costs, module=mod)


def render_mana(mc, per_deck):
    from edhmc.registry import DECKS
    decks = list(DECKS)
    rocks, lramp, drops = mc["per"]("rock"), mc["per"]("land"), mc["per"]("drop")
    c = mc["costs"]
    lines = [
        '"""GENERATED by `python -m tools.removal_census --write` -- do not edit.',
        "",
        "THE POD'S MANA (queue item 50, §0z235): the library its opponents draw",
        "their land drops from, and what their answers cost -- read from the",
        "seven lists, which stand in for the pod's as they do for the destroy",
        "shares (`_removal.py`). Lands and ramp from each deck's COMMITTED module",
        "list; costs from the lists the shares read. Ramp is mana rocks and land",
        "ramp only (the owner, 2026-11-20); a creature's mana is queue item 52.",
        "",
        "Read by `opponents.roll_pod_mana` (§0z236, `pod_mana`), and so in every",
        'cache fingerprint (`tools/cache_manifest`\'s shared files)."""',
        "",
        f"# the list size, the median over {len(decks)} decks",
        f"POD_LIBRARY = {int(median(mc['sizes'].values()))}",
        "# lands in each committed list, and their median: the pod's land count",
        f"LANDS_BY_DECK = {dict(sorted(mc['lands'].items()))!r}",
        f"POD_LANDS = {int(round(median(mc['lands'].values())))}",
        "",
        "# ramp pieces per committed list (rocks / land ramp / extra land drops),",
        f"# per deck in {decks!r} order: {rocks!r} / {lramp!r} / {drops!r}",
        f"POD_ROCKS = {int(round(median(rocks)))}",
        f"POD_LAND_RAMP = {int(round(median(lramp)))}",
        f"POD_EXTRA_DROPS = {int(round(median(drops)))}",
        "# medians over every piece, once per deck that runs it",
        f"ROCK_MV = {median(mc['vals']('rock', 1)):.1f}",
        f"ROCK_NET = {median(mc['vals']('rock', 2)):.1f}"
        "    # mana a turn, less any activation cost",
        f"LAND_RAMP_COST = {median(mc['vals']('land', 1)):.1f}"
        "    # mana value plus any activation cost",
        f"LAND_RAMP_LANDS = {median(mc['vals']('land', 2)):.1f}"
        "    # lands put onto the battlefield",
        "",
        "# what the pod's answers cost: the median mana value of the INSTANTS AND",
        "# SORCERIES of each kind, once per deck that runs one (SPOT_SPELL_MV's",
        "# rule, `_removal.py`); X spells left out (Scryfall counts X as 0), an",
        "# overloaded wipe (Damn) costed at its overload",
        f"# wipe: {c['wipe'][1]} counted, {c['wipe'][2]} X left out; "
        f"ae: {c['ae'][1]} counted, {c['ae'][2]} X; "
        f"counter: {c['counter'][1]} counted, {c['counter'][2]} X",
        f"# a kind with fewer than {MIN_SAMPLE} counted takes what contains it, as"
        " the shares do:",
        f"# ae (median {c['ae'][0]:.1f} of {c['ae'][1]}) takes SPOT_SPELL_MV;"
        f" no kind contains a counterspell,",
        f"# so COUNTER_SPELL_MV is its own {c['counter'][1]} -- THIN, said out"
        " loud",
        f"WIPE_SPELL_MV = {c['wipe'][0]:.1f}",
        f"AE_SPELL_MV = {(c['ae'][0] if c['ae'][1] >= MIN_SAMPLE else spot_spell_mv(per_deck)):.1f}",
        f"COUNTER_SPELL_MV = {c['counter'][0]:.1f}",
        "",
        "# name -> (kind, cost, amount, flags, the clause that decided it):",
        "# rock (mv, net mana), land (cost, lands), drop (mv, drops)",
        "RAMP = {",
    ]
    for n, (k, cost, amt, fl, clause) in sorted(mc["ramp"].items()):
        lines.append(f"    {n!r}: ({k!r}, {cost!r}, {amt!r}, {fl!r}, {clause!r}),")
    lines += ["}", "", "# deck -> its ramp, from the committed list", "RAMP_BY_DECK = {"]
    for d in decks:
        lines.append(f"    {d!r}: {mc['by_deck'][d]!r},")
    lines += ["}", "",
              "# read and NOT the pod's ramp: name -> (reason, clause)",
              "NOT_RAMP = {"]
    for n, (r, clause) in sorted(mc["not_ramp"].items()):
        lines.append(f"    {n!r}: ({r!r}, {clause!r}),")
    lines += ["}", "",
              "# YOUR cards that hand the pod mana -- its controller searches for a",
              "# land, or makes Treasure, or each opponent who takes it makes one",
              "# (the amount is then per taker): name -> (kind, amount, tapped,",
              "# clause), read by `opponents.pod_gift` (§0z235, §0z241, §0z245)",
              "POD_GIFTS = {"]
    for n, g in sorted(mc["gifts"].items()):
        lines.append(f"    {n!r}: {g!r},")
    lines += ["}", "",
              "# deck -> every card in its committed module list (`check_docs`)",
              "MODULE_LISTS = {"]
    for d in decks:
        lines.append(f"    {d!r}: {mc['module'][d]!r},")
    lines += ["}", "", "# every nonland name the cost medians read (`check_docs`)",
              "SCANNED = {"]
    lines += [f"    {n!r}," for n in sorted({n for ns in per_deck.values() for n in ns})]
    lines += ["}", ""]
    return "\n".join(lines)


def main() -> int:
    table, per_deck, scanned, counters = census()
    sh = shares(table, per_deck)
    for kind in KINDS:
        d, t = sh[kind]
        print(f"{kind:<5} {d} of {t} destroy -> {d / max(1, t):.3f}")
        for n, (k, c, clause) in sorted(table.items()):
            if (k == kind if kind != "ae" else k == "spot" and is_ae(clause)):
                print(f"    {c:<8} {n:<42} {clause[:70]}")
    print("counterspells:")
    for n, (w, clause) in sorted(counters.items()):
        print(f"    {w:<16} {n:<32} {clause[:60]}")
    mc = mana_census(census.oracle, table, counters, per_deck)
    print("the pod's mana (§0z235):")
    print(f"    lands by deck {dict(sorted(mc['lands'].items()))}")
    for kind in ("rock", "land", "drop"):
        print(f"    {kind}s per deck {mc['per'](kind)}")
        for n, r in sorted(mc["ramp"].items()):
            if r[0] == kind:
                print(f"        {n:<34} cost {r[1]:<4} amount {r[2]} {r[3]}")
    print("    not ramp:")
    for n, (reason, clause) in sorted(mc["not_ramp"].items()):
        print(f"        {reason:<28} {n:<34} {clause[:50]}")
    for k, (m, cnt, xs) in mc["costs"].items():
        print(f"    {k} spell mv median {m} ({cnt} counted, {xs} X left out)")
    if "--write" in sys.argv:
        open("edhmc/decks/_removal.py", "w").write(
            render(table, per_deck, scanned, counters))
        print("wrote edhmc/decks/_removal.py")
        open("edhmc/decks/_pod_mana.py", "w").write(render_mana(mc, per_deck))
        print("wrote edhmc/decks/_pod_mana.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
