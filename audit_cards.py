#!/usr/bin/env python3
"""Re-verify every card in every deck module against Scryfall oracle text.

Rebuilt 2026-09-05 (the original was lost; CLAUDE.md lists it as missing).

Checks, per card, against `cards/collection`:

  name        the name resolves at all, and resolves to itself (no fuzzy hit)
  cost        colour pips and generic, allowing for {X} via `x_pips` and for
              hybrid, which a single-cost model cannot express
  mv          derived from `cost`, compared against Scryfall's `cmc`
  p/t         creatures only; `*` toughness is reported, not failed
  types       the CARD TYPES in `Card.types` against Scryfall's type line
  flying      `Card.flying` against Scryfall's `keywords`, which is what
              `tag_flying.py` reads (never match on oracle text: reach's
              reminder text contains the word "flying")
  land        `is_land` against the type line, and `tapped` against the
              oracle text's "enters tapped" clause
  produces    a land's `produces` against Scryfall's `produced_mana`

Every failure is a claim about DATA, not about behaviour. Behaviour lives in
the ORACLE_AUDIT_*.md files.

    python audit_cards.py            # all three decks, summary + failures
    python audit_cards.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

from edhmc.engine import STACK_ONLY_CREATURES
from edhmc.decks import karlov_v2, lorehold_v16, rendmaw_v12, tivit_v1
from edhmc.decks._evasion import FLYING

UA = {"User-Agent": "EDHMC/1.0", "Accept": "application/json"}
API = "https://api.scryfall.com/cards/collection"

CARD_TYPES = {"Artifact", "Battle", "Creature", "Enchantment", "Instant",
              "Kindred", "Tribal", "Land", "Planeswalker", "Sorcery"}

# Cards whose single-cost model cannot be right, with the reason. These are
# reported in their own section rather than as failures.
KNOWN_MODEL_LIMITS = {
    "Lurrus of the Dream-Den": "hybrid {1}{W/B}{W/B} flattened to {1}{W}{B}",
    "Revitalizing Repast": "hybrid {B/G} modelled as {B} + a {G} alt_cost",
    "Damn": "cast face {B}{B}; the wrath is overload {2}{W}{W}, MV 4",
    "Mizzix's Mastery": "overload {5}{R}{R}{R} is a special case in lorehold.py",
    "Overlord of the Hauntwoods": "Impending 4 modelled via alt_costs",
}

# Lands whose Scryfall `produced_mana` is WUBRG because the card reads "any
# colour in your commander's colour identity" (or names a creature type).
# Restricting them to the deck's two colours is CORRECT, not a data error.
IDENTITY_LANDS = {"Command Tower", "Cavern of Souls", "Plaza of Heroes",
                  "Opal Palace",
                  # "any color that a land an OPPONENT controls could
                  # produce" -- Scryfall lists all five; restricting it to the
                  # deck's own colours is the conservative reading.
                  "Exotic Orchard"}


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def collect():
    """(deck, card, in_deck) for every Card object we can reach."""
    out = []
    for deck, mod in (("rendmaw", rendmaw_v12),
                      ("lorehold", lorehold_v16),
                      ("karlov", karlov_v2),
                      ("tivit", tivit_v1)):
        cards, commander = mod.build()
        seen = set()
        for c in [commander] + cards:
            if c.name in seen:
                continue
            seen.add(c.name)
            out.append((deck, c, True))
        # module-level candidates / cut cards kept for the swap harnesses
        for attr in dir(mod):
            if not attr.isupper():
                continue
            v = getattr(mod, attr)
            if type(v).__name__ != "Card" or v.name in seen:
                continue
            seen.add(v.name)
            out.append((deck, v, False))
    return out


# ---------------------------------------------------------------------------
# scryfall
# ---------------------------------------------------------------------------

def fetch(names):
    data = {}
    names = list(names)
    for i in range(0, len(names), 75):
        chunk = names[i:i + 75]
        body = json.dumps(
            {"identifiers": [{"name": n} for n in chunk]}).encode()
        req = urllib.request.Request(
            API, data=body, headers={**UA, "Content-Type": "application/json"})
        res = json.load(urllib.request.urlopen(req, timeout=30))
        for card in res.get("data", []):
            data[card["name"]] = card
        for miss in res.get("not_found", []):
            # `identifiers: [{"name": ...}]` does not accept the COMBINED name
            # of a double-faced card ("Witch Enchanter // Witch-Blessed
            # Meadow"). Fall back to a fuzzy lookup rather than reporting a
            # real card as missing.
            data[miss.get("name")] = named(miss.get("name"))
        time.sleep(0.12)          # Scryfall asks for 50-100ms between calls
    return data


def named(name):
    url = ("https://api.scryfall.com/cards/named?fuzzy="
           + urllib.parse.quote(name))
    try:
        return json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30))
    except Exception:
        return None


def index(data):
    """Name -> card, keyed on the full name AND on each face name."""
    idx = {}
    for name, card in data.items():
        if card is None:
            continue
        idx[card["name"]] = card
        for part in card["name"].split(" // "):
            idx.setdefault(part, card)
        idx.setdefault(name, card)
    return idx


# ---------------------------------------------------------------------------
# cost parsing
# ---------------------------------------------------------------------------

SYM = re.compile(r"\{([^}]+)\}")


def parse_cost(s):
    """Scryfall mana cost string -> (dict, x_count, hybrid_count)."""
    cost, x, hybrid = {}, 0, 0
    for sym in SYM.findall(s or ""):
        if sym == "X":
            x += 1
        elif sym.isdigit():
            cost["gen"] = cost.get("gen", 0) + int(sym)
        elif "/" in sym:
            hybrid += 1
            # count a hybrid pip against the first colour we can, so the
            # comparison is at least the right SIZE; the reason is reported.
            for part in sym.split("/"):
                if part in "WUBRGC":
                    cost[part] = cost.get(part, 0) + 1
                    break
            else:
                cost["gen"] = cost.get("gen", 0) + 1
        elif sym in "WUBRGC":
            cost[sym] = cost.get(sym, 0) + 1
        else:
            cost["gen"] = cost.get("gen", 0) + 1
    return cost, x, hybrid


def front(card):
    """The face a cost/P-T/type comparison should use."""
    if card.get("mana_cost") is not None and card.get("mana_cost") != "":
        return card
    faces = card.get("card_faces")
    if faces:
        return faces[0]
    return card


def fmt(cost):
    order = ["gen", "W", "U", "B", "R", "G", "C"]
    bits = []
    for k in order:
        v = cost.get(k, 0)
        if not v:
            continue
        bits.append("{%d}" % v if k == "gen" else "{%s}" % k * v)
    return "".join(bits) or "{0}"


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check(deck, c, sc):
    """-> list of (severity, message). severity in {'ERR','WARN','NOTE'}."""
    out = []
    if sc is None:
        return [("ERR", "not found on Scryfall")]

    f = front(sc)
    tl = f.get("type_line", sc.get("type_line", ""))
    is_land = "Land" in tl.split("//")[0]
    limit = KNOWN_MODEL_LIMITS.get(c.name)

    # --- name -------------------------------------------------------------
    if c.name != sc["name"] and c.name not in sc["name"].split(" // "):
        out.append(("ERR", f"name resolves to {sc['name']!r}"))

    # --- type line --------------------------------------------------------
    printed = {t for t in re.split(r"[\s—–-]+", tl.split("//")[0])
               if t in CARD_TYPES}
    if c.name in STACK_ONLY_CREATURES:
        # `Card.types` is deliberately the type line ON THE STACK, because that
        # is what Rendmaw's "play a card with two or more card types" reads.
        # engine.is_battlefield_creature() takes it off the battlefield again.
        out.append(("NOTE", "stack-only creature, Creature type carried on "
                            "purpose: %s" % STACK_ONLY_CREATURES[c.name]))
        printed = printed | {"Creature"}
    if printed and c.types != printed:
        # the module writes "Kindred" where old cards printed "Tribal"
        norm = {"Tribal": "Kindred"}
        printed = {norm.get(t, t) for t in printed}
        if c.types != printed:
            out.append(("ERR", "types %s, oracle %s"
                        % ("/".join(sorted(c.types)),
                           "/".join(sorted(printed)))))

    if c.is_land != is_land:
        out.append(("ERR", f"is_land={c.is_land}, type line {tl!r}"))

    # --- cost -------------------------------------------------------------
    if not is_land:
        oc, xs, hy = parse_cost(f.get("mana_cost", ""))
        mine = dict(c.cost)
        if xs:
            # the module bakes a chosen X into `gen` and records it in x_pips
            if c.x_pips:
                mine["gen"] = mine.get("gen", 0) - c.x_pips
                if mine.get("gen") == 0:
                    mine.pop("gen")
                out.append(("NOTE",
                            f"{{X}}x{xs}: modelled at X={c.x_pips}"))
            else:
                out.append(("ERR", f"oracle has {{X}}x{xs} but x_pips=0"))
        if mine != oc:
            sev = "NOTE" if (hy and limit) else ("WARN" if limit else "ERR")
            out.append((sev, "cost %s, oracle %s"
                        % (fmt(c.cost), f.get("mana_cost") or "{0}")))
        elif limit:
            out.append(("NOTE", limit))

        cmc = sc.get("cmc")
        if cmc is not None and not xs and not c.x_pips and not limit:
            if float(c.mv) != float(cmc):
                out.append(("ERR", f"mv {c.mv}, oracle cmc {cmc:g}"))

    # --- power / toughness ------------------------------------------------
    if "Creature" in printed or "Vehicle" in tl:
        p, t = f.get("power"), f.get("toughness")
        for label, mine_v, theirs in (("power", c.power, p),
                                      ("toughness", c.toughness, t)):
            if theirs is None:
                continue
            if not str(theirs).lstrip("+-").isdigit():
                out.append(("NOTE",
                            f"{label} is {theirs!r}; modelled as {mine_v}"))
            elif int(theirs) != mine_v:
                out.append(("ERR",
                            f"{label} {mine_v}, oracle {theirs}"))
    elif c.power or c.toughness:
        if not is_land:
            out.append(("WARN", f"p/t {c.power}/{c.toughness} on a noncreature"))

    # --- flying -----------------------------------------------------------
    kw = set(sc.get("keywords", []))
    has_flying = "Flying" in kw
    if c.flying != has_flying:
        out.append(("ERR", f"flying={c.flying}, Scryfall keywords {sorted(kw)}"))
    if has_flying and c.name not in FLYING:
        out.append(("ERR", "flies but is missing from decks/_evasion.py"))

    # --- lands ------------------------------------------------------------
    if is_land:
        oracle = (f.get("oracle_text") or sc.get("oracle_text") or "")
        enters_tapped = bool(re.search(
            r"enters (?:the battlefield )?tapped", oracle, re.I))
        # shocklands, "reveal a card", check lands: the tapped clause is the
        # FALLBACK, not the rule. Case matters here -- "If you don't" starts a
        # sentence, so this must be case-insensitive.
        conditional = bool(re.search(r"unless|if you (?:don't|do)\b",
                                     oracle, re.I))
        if enters_tapped and not c.tapped and not conditional:
            out.append(("ERR", "enters tapped; module has tapped=False"))
        if c.tapped and not enters_tapped:
            out.append(("WARN", "module has tapped=True; oracle does not say so"))

        prod = set(sc.get("produced_mana") or [])
        mine = set(c.produces)
        if prod and mine - prod:
            out.append(("ERR", "produces %s, oracle produces %s"
                        % ("".join(sorted(mine)), "".join(sorted(prod)))))
        elif prod and prod - mine and prod - mine != {"C"} \
                and c.name not in IDENTITY_LANDS:
            out.append(("WARN", "produces %s, oracle also makes %s"
                        % ("".join(sorted(mine)), "".join(sorted(prod - mine)))))
    return out


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--all", action="store_true",
                    help="print NOTEs as well as ERR/WARN")
    args = ap.parse_args()

    cards = collect()
    names = sorted({c.name for _, c, _ in cards})
    print(f"fetching {len(names)} distinct names from Scryfall ...",
          file=sys.stderr)
    idx = index(fetch(names))

    report, counts = [], {"ERR": 0, "WARN": 0, "NOTE": 0}
    for deck, c, in_deck in cards:
        sc = idx.get(c.name)
        for sev, msg in check(deck, c, sc):
            counts[sev] += 1
            report.append({"deck": deck, "card": c.name, "in_deck": in_deck,
                           "severity": sev, "message": msg})

    for sev in ("ERR", "WARN", "NOTE"):
        rows = [r for r in report if r["severity"] == sev]
        if sev == "NOTE" and not args.all:
            continue
        if not rows:
            continue
        print(f"\n=== {sev} ({len(rows)}) " + "=" * 40)
        for r in rows:
            flag = "" if r["in_deck"] else " [candidate]"
            print(f"  {r['deck']:9s} {r['card']:38s}{flag} {r['message']}")

    checked = len(cards)
    print(f"\n{checked} card slots checked ({len(names)} distinct names): "
          f"{counts['ERR']} ERR, {counts['WARN']} WARN, {counts['NOTE']} NOTE")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    return 1 if counts["ERR"] else 0


if __name__ == "__main__":
    sys.exit(main())
