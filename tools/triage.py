#!/usr/bin/env python3
"""Triage: can the engine SEE this card, and does its counter fire? (item 23)

`docs/TRIAGE.md` is the design; this is tiers 0 and 2 of it. Tier 0 runs on
paper in seconds; tier 2 is a small-N smoke run. Neither measures VALUE --
triage predicts MEASURABILITY, and a card that passes is only a card worth
the ~152 CPU-seconds of a candidate row (tier 3).

    python -m tools.triage --proposals          # tier 0 over the PROPOSED ledger
    python -m tools.triage --deck karlov        # tier 0 over one deck's list
    python -m tools.triage --smoke rendmaw "Pitiless Plunderer" [--n=1000]
    python -m tools.triage --backtest           # the acceptance test (below)

TIER 0, TWO WAYS, because a card is either implemented or it is not:

  STRUCTURAL (an implemented Card object). The channels through which this
  engine can act on a card, DERIVED from the object and the engine source:

      body      a creature: it attacks, blocks, dies, is sacrificed
      land      a land: mana and land drops
      mana      a mana ability
      script    a `script=` the engine dispatches on
      fields    any effect field set off its default (pod_damage, lifegain,
                treasures, tokens, tags, flying ...)
      named     its name as a string literal in THIS deck's engine files
                (`engine_files`) -- how behaviour attaches when there is no
                script (§0z25: Heliod, Breach)
      types     two or more card types (rendmaw's commander counts them)

  No channel at all is BLIND: the model sees its cost, priority and threat --
  the constants ablation's blank varies on (§0j) -- and nothing else. A body
  and nothing else is BODY: the §0z36 case, Soulmender's unmodelled tap on a
  modelled 1/1.

  TEXT (a Proposal: oracle text, no object yet). Each sentence, reminder text
  stripped, is matched against the §4 limits -- targeting an opponent's
  permanent, countering, "an opponent casts", an opponent's library or
  sacrifice. A card is BLIND only if EVERY clause matches and it has no body.
  Anything unmatched is REVIEW: the screen is optimistic by construction,
  because its only fatal error is discarding a good card (LEDGER_STATES
  rule 3), and the clauses it DID match are listed so a BLIND flag can name
  them (§0z13).

TIER 2, `--smoke`: the card in a slot against a blank there, N games, and
every output counter that moved. A count has far lower variance than a win
rate, so "does it fire" is decidable at N=1000 (Sai's 0.155 Thopters, §0z26).

THE ACCEPTANCE TEST (`--backtest`, and tests/test_triage.py) IS EXACT, NOT
STATISTICAL. `docs/TRIAGE.md` proposed failing the screen when it calls BLIND
a card whose row is significant. Run over the rebuilt tables that failed 32
times -- and every one was a cheap removal spell or counterspell with a
POSITIVE row, at priority 1-2 against a blank cast at the deck's median
priority. Those rows measure the §0j constants (a dead card cast late costs
less than a blank cast on curve), not the card's text, so significance is the
wrong witness. The right one is common random numbers: a card whose text the
engine cannot see plays IDENTICALLY, seed for seed, to a blank matching its
cost, types, body, priority and threat (`matched_blank`). So the screen FAILS
if any card it calls BLIND or BODY differs from its matched blank in any
output on any seed -- the engine saw something the screen missed -- or if it
calls BLIND a card the ablation classification says is SCRIPTED or PARTLY.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
import sys

from edhmc.engine import Card

# The engine files a card's name can be dispatched from, PER DECK: the files
# in that deck's cache fingerprint (`registry.fingerprint_files`) plus the
# shared ones `cache_manifest.SHARED` names -- derived, so a new engine file
# is searched the day it is fingerprinted. Searching every engine was the
# first version, and it called Midnight Reaper "named" in rendmaw because
# shilgengar.py dispatches on it.
def engine_files(deck_name: str) -> list[pathlib.Path]:
    from edhmc.registry import DECKS as REG
    from tools.cache_manifest import SHARED
    spec = REG[deck_name]
    names = [f for f in SHARED + spec.fingerprint_files
             if f.startswith("edhmc/") and "/decks/" not in f]
    if spec.engine == "engine":
        names.append("edhmc/engine.py")
    return sorted({pathlib.Path(f) for f in names if pathlib.Path(f).exists()})

# Effect fields: a value off the default is a claim that the engine reads it.
# Identity fields (name, types, cost, power/toughness, priority, threat) are
# not -- ablation's blank varies on those itself.
EFFECT_FIELDS = ("mana_ability", "script", "miracle_cost", "treasures",
                 "pod_damage", "discards", "land_face", "lifegain", "drain",
                 "lifelink", "indestructible", "haste", "flying", "x_pips",
                 "alt_costs", "tokens", "tags")
_DEFAULTS = {f.name: (f.default if f.default is not dataclasses.MISSING
                      else f.default_factory())
             for f in dataclasses.fields(Card)
             if f.default is not dataclasses.MISSING
             or f.default_factory is not dataclasses.MISSING}

_SRC_CACHE: dict = {}


def engine_text(deck_name: str) -> str:
    if deck_name not in _SRC_CACHE:
        _SRC_CACHE[deck_name] = "\n".join(p.read_text()
                                          for p in engine_files(deck_name))
    return _SRC_CACHE[deck_name]


def named_in_engine(name: str, deck_name: str) -> bool:
    text = engine_text(deck_name)
    return any(f'"{b}"' in text or f"'{b}'" in text
               for b in {name, name.split(" // ")[0]})


def structural_channels(card: Card, deck_name: str) -> list[str]:
    """Every channel through which the engine can act on `card`."""
    ch = []
    if card.is_creature:
        ch.append("body")
    if card.is_land:
        ch.append("land")
    if card.mana_ability:
        ch.append("mana")
    if card.script:
        ch.append("script")
    moved = [f for f in EFFECT_FIELDS
             if f not in ("mana_ability", "script")
             and getattr(card, f) != _DEFAULTS.get(f)]
    if moved:
        ch.append("fields:" + ",".join(moved))
    if named_in_engine(card.name, deck_name):
        ch.append("named")
    if len(card.types) >= 2:
        ch.append("types")
    return ch


def structural_verdict(card: Card, deck_name: str) -> str:
    ch = structural_channels(card, deck_name)
    if not ch:
        return "BLIND"
    if ch == ["body"]:
        return "BODY"
    return "SEEN"


# ---------------------------------------------------------------------------
# Tier 0 on paper: the text screen
# ---------------------------------------------------------------------------

# Each pattern is a §4 limit: opponents' boards are a creature COUNT, they
# hold no spells, no library and no permanents as objects. A clause matching
# one of these is one the engine cannot see. The list is deliberately short:
# anything it misses is REVIEW, never BLIND.
BLIND_CLAUSES = (
    ("counters an opponent's spell",
     r"\bcounter target (?:\w+ )*spell"),
    ("targets a permanent an opponent controls",
     r"target (?:\w+ )*(?:creature|artifact|enchantment|planeswalker|"
     r"permanent|land)s? (?:an opponent controls|you don't control|"
     r"your opponents control)"),
    ("reads an opponent casting",
     r"\b(?:whenever|when) an opponent casts\b"),
    ("an opponent's sacrifice",
     r"\b(?:each|target) opponent sacrifices\b"),
    ("an opponent's library",
     r"\b(?:each|target) opponent (?:mills|shuffles|reveals|exiles the top)"),
    ("tapped creatures your opponents control",
     r"tapped creatures? (?:your opponents|an opponent) controls?"),
    ("gains control of an opponent's permanent",
     r"\bgain control of target\b"),
    ("copies an opponent's spell or permanent",
     r"\bcopy (?:of )?target (?:\w+ )*(?:spell|permanent|creature)"
     r"(?: an opponent controls)?"),
)


def clauses(oracle: str) -> list[str]:
    text = re.sub(r"\([^)]*\)", "", oracle)
    parts = re.split(r"(?<=[.!])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def text_screen(oracle: str, type_line: str) -> dict:
    """Clause-by-clause verdict for a card that exists only as text."""
    rows = []
    for c in clauses(oracle):
        hit = next((why for why, pat in BLIND_CLAUSES
                    if re.search(pat, c, re.IGNORECASE)), None)
        rows.append((c, hit))
    body = "Creature" in type_line
    blind = [r for r in rows if r[1]]
    if rows and len(blind) == len(rows) and not body:
        verdict = "BLIND"
    else:
        verdict = "REVIEW"
    return {"verdict": verdict, "clauses": rows, "body": body,
            "blind_clauses": [c for c, _ in blind]}


# ---------------------------------------------------------------------------
# Tier 2: the smoke run
# ---------------------------------------------------------------------------

# The engine's own instrumentation of the watched card: it reads the card's
# NAME, so it always differs from a blank and says nothing about the card.
WATCH_KEYS = {"cast_test_card", "test_card_turn", "test_card_resolved",
              "test_card_answered", "test_card_removed", "test_card_countered"}


def smoke(deck_name: str, card: Card, n: int = 1000, slot: str | None = None,
          turns: int = 20):
    """The card in `slot` against a blank there; every counter that moved.

    Returns [(key, mean with card, mean with blank, z)] sorted by |z|. The
    blank is ablation's, at `repl_priority` -- the same comparison a
    candidate row makes, at a fraction of its N.
    """
    import math
    from edhmc.experiment import DEFAULT_CFG, repl_priority
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS as REG
    from tools.ablation import blank_like
    deck, cmd = build_pending(deck_name)
    deck = list(deck)
    rp = repl_priority(deck)
    if slot is None:
        slot = _victim(deck_name)
    i = next(k for k, c in enumerate(deck) if c.name == slot)
    with_card, with_blank = list(deck), list(deck)
    with_card[i] = card
    with_blank[i] = blank_like(card, rp)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({card.name}))
    sim = REG[deck_name].sim
    # THE UNION OF KEYS, each seed defaulting to 0. A counter only the card's
    # arm ever touches -- `sai_thopters` -- is ABSENT from the blank arm's
    # dict (`Metrics` reads 0 but does not list the key), and the first
    # version intersected the key sets: it dropped exactly the counter this
    # tier exists to read.
    a, b = [], []
    for s in range(5000, 5000 + n):
        a.append(sim(with_card, cmd, dict(cfg), s))
        b.append(sim(with_blank, cmd, dict(cfg), s))

    def numeric(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    keys = {k for out in a + b for k, v in out.items() if numeric(v)}
    rows = []
    for k in sorted(keys - WATCH_KEYS):
        xs = [float(o.get(k, 0) or 0) for o in a]
        ys = [float(o.get(k, 0) or 0) for o in b]
        diff = [x - y for x, y in zip(xs, ys)]
        mu = sum(diff) / n
        var = sum((x - mu) ** 2 for x in diff) / max(1, n - 1)
        if mu == 0 and var == 0:
            continue
        z = mu / math.sqrt(var / n) if var > 0 else float("inf")
        rows.append((k, sum(xs) / n, sum(ys) / n, z))
    cast = sum(float(o.get("cast_test_card", 0)) for o in a) / n
    rows.append(("P(cast)", cast, 0.0, float("nan")))
    rows.sort(key=lambda r: (r[0] != "P(cast)", -abs(r[3]) if r[3] == r[3]
                             else 0))
    return rows


def _victim(deck_name: str) -> str:
    """The slot tools/candidates.py uses for this deck's current batch."""
    import tools.candidates as CAND
    for spec in CAND.DECKS.values():
        if spec[1] == deck_name:
            victim = spec[4]
            from edhmc.pending import build_pending
            if any(c.name == victim for c in build_pending(deck_name)[0]):
                return victim
    raise SystemExit(f"no candidates.py victim slot is in {deck_name}'s list; "
                     f"pass --slot=NAME")


# ---------------------------------------------------------------------------
# The acceptance test
# ---------------------------------------------------------------------------

def matched_blank(card: Card) -> Card:
    """A card the engine cannot tell from `card` EXCEPT by its text: same
    cost, types, body, priority and threat, a name nothing dispatches on, and
    every effect field at its default."""
    return Card(name="(matched blank)", types=card.types, cost=dict(card.cost),
                power=card.power, toughness=card.toughness,
                priority=card.priority, threat=card.threat)


def plays_identically(deck_name: str, card: Card, seeds=range(5000, 5040),
                      turns: int = 20) -> tuple[bool, str]:
    """Does `card` play exactly like its matched blank on every seed?

    Returns (identical, the first output key and seed that differ). Under
    CRN the two decks are shuffled on the same seed with the card in the same
    slot, so any difference at all is the engine acting on something the
    blank does not have.
    """
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS as REG
    deck, cmd = build_pending(deck_name)
    deck = list(deck)
    i = next(k for k, c in enumerate(deck) if c.name == card.name)
    blank = list(deck)
    blank[i] = matched_blank(card)
    sim = REG[deck_name].sim
    for s in seeds:
        a = sim(deck, cmd, dict(DEFAULT_CFG, turns=turns), s)
        b = sim(blank, cmd, dict(DEFAULT_CFG, turns=turns), s)
        for k in a:
            va, vb = a[k], b.get(k)
            if isinstance(va, (int, float)) and va != vb:
                return False, f"{k} on seed {s}: {va!r} vs {vb!r}"
    return True, ""

ROW = re.compile(r"^(.+?)\s{2,}([+-]\d+\.\d+)\+-(\d+\.\d+)\s+([+-]\d+\.\d+)"
                 r"\+-(\d+\.\d+)\s+([+-]\d+\.\d+)\+-(\d+\.\d+)\s*(\S*)\s*$")


def table_rows(deck_name: str) -> dict:
    """name -> signal, from the committed results/ablation_<deck>.txt."""
    out = {}
    path = pathlib.Path(f"results/ablation_{deck_name}.txt")
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        m = ROW.match(line)
        if m and not line.startswith("card "):
            out[m.group(1).strip()] = m.group(8) or "--"
    return out


def backtest(seeds=range(5000, 5040), decks=None, labels=True) -> dict:
    """Structural verdicts against everything the repo has measured.

    Returns {"violations": [...], "label_diffs": [...], "counts": {...},
    "constant_rows": [...]}. A VIOLATION fails the screen: a BLIND or BODY
    card that plays differently from its matched blank, or a BLIND verdict on
    a card the ablation classification calls SCRIPTED or PARTLY. A LABEL DIFF
    is information: a KNOWN_BLIND card the derivation finds a channel for --
    a label that rotted, or a channel the label ignores (§0q).
    `constant_rows` lists the BLIND cards whose table row is significant
    anyway: §0j's constants, measured.
    """
    import tools.ablation as AB
    from edhmc.pending import DECKS as CATALOG, build_pending
    violations, diffs, constant_rows = [], [], []
    counts = {"BLIND": 0, "BODY": 0, "SEEN": 0}
    for deck_name in (decks or CATALOG):
        deck, _ = build_pending(deck_name)
        rows = table_rows(deck_name)
        scripted = AB.SCRIPTED_BY_DECK.get(deck_name, set())
        partly = AB.partly_for(deck_name, deck)
        blind_label = AB.KNOWN_BLIND.get(deck_name, set())
        for c in deck:
            if c.is_land:
                continue
            v = structural_verdict(c, deck_name)
            counts[v] += 1
            if v in ("BLIND", "BODY"):
                same, why = plays_identically(deck_name, c, seeds)
                if not same:
                    violations.append((deck_name, c.name,
                                       f"{v} but plays differently: {why}"))
                elif v == "BLIND" and rows.get(c.name, "--") != "--":
                    constant_rows.append((deck_name, c.name, rows[c.name]))
            if v == "BLIND" and c.name in scripted:
                violations.append((deck_name, c.name, "BLIND but SCRIPTED"))
            if v == "BLIND" and c.name in partly:
                violations.append((deck_name, c.name, "BLIND but PARTLY"))
            if labels and c.name in blind_label and v == "SEEN":
                # Which kind of disagreement? The same exact test splits it:
                # identical to its matched blank = the channel is INERT (a tag
                # nothing reads, §0z12) and the label is right in practice;
                # different = the engine DOES act on the card and the label
                # is a claim that rotted (§0q).
                same, why = plays_identically(deck_name, c, seeds)
                kind = "inert" if same else "LIVE"
                diffs.append((deck_name, c.name, kind, ";".join(
                    x for x in structural_channels(c, deck_name) if x != "body"),
                    why))
    return {"violations": violations, "label_diffs": diffs, "counts": counts,
            "constant_rows": constant_rows}


def main() -> int:
    # `--deck karlov` and `--deck=karlov` both work: a valued flag takes the
    # next word when it has no `=`.
    VALUED = ("--deck", "--slot", "--n")
    argv, args, flags = list(sys.argv[1:]), [], {}
    while argv:
        a = argv.pop(0)
        if not a.startswith("--"):
            args.append(a)
        elif "=" in a:
            k, v = a.split("=", 1)
            flags[k] = v
        elif a in VALUED and argv:
            flags[a] = argv.pop(0)
        else:
            flags[a] = True
    if "--backtest" in flags:
        r = backtest()
        print(f"structural verdicts over every nonland in every list: "
              f"{r['counts']}")
        print(f"\nVIOLATIONS (the engine saw a card the screen called blind): "
              f"{len(r['violations'])}")
        for v in r["violations"]:
            print("   ", *v)
        print(f"\nBLIND, PROVED BLIND, AND A SIGNIFICANT ROW ANYWAY (§0j's "
              f"constants): {len(r['constant_rows'])}")
        for d in r["constant_rows"]:
            print("   ", *d)
        print(f"\nLABEL DIFFS (KNOWN_BLIND, but a channel exists): "
              f"{len(r['label_diffs'])}")
        for kind in ("LIVE", "inert"):
            group = [d for d in r["label_diffs"] if d[2] == kind]
            print(f"  {kind}: {len(group)}"
                  + ("  -- the engine acts on these, so 'does not implement "
                     "the card at all' is too strong: PARTLY at least"
                     if kind == "LIVE" else
                     "  -- a channel exists and nothing fires it"))
            for d in group:
                print(f"    {d[0]:<10} {d[1]:<36} {d[3]}"
                      + (f"   [{d[4]}]" if d[4] else ""))
        return 1 if r["violations"] else 0
    if "--proposals" in flags:
        from edhmc.pending import PROPOSED
        for p in PROPOSED:
            if p.rejected:
                continue
            r = text_screen(p.oracle, p.type_line)
            print(f"  [{r['verdict']:<6}] {p.deck:<10} {p.card}")
            for c in r["blind_clauses"]:
                print(f"            blind: {c}")
        return 0
    if "--deck" in flags:
        from edhmc.pending import build_pending
        deck, _ = build_pending(flags["--deck"])
        for c in sorted(deck, key=lambda c: c.name):
            if c.is_land:
                continue
            print(f"  [{structural_verdict(c, flags['--deck']):<5}] "
                  f"{c.name:<40} "
                  f"{', '.join(structural_channels(c, flags['--deck']))}")
        return 0
    if "--smoke" in flags and len(args) == 2:
        from edhmc.pending import DECKS as CATALOG, build_pending
        deck_name, name = args
        pool = list(build_pending(deck_name)[0]) + list(
            CATALOG[deck_name][1].values())
        card = next((c for c in pool if c.name == name), None)
        if card is None:
            raise SystemExit(f"{name} is not in {deck_name}'s list or catalog")
        n = int(flags.get("--n", 1000))
        rows = smoke(deck_name, card, n=n,
                     slot=flags.get("--slot"))
        print(f"{name} in {deck_name}, N={n}, every counter that moved "
              f"(|z| sorted):")
        for k, x, y, z in rows[:25]:
            if k == "P(cast)":
                print(f"   {'P(cast)':<28} {x:>10.3f}   (games it was cast in)")
                continue
            print(f"   {k:<28} {x:>10.3f} vs blank {y:>10.3f}   z {z:+.1f}")
        if len(rows) <= 1:
            print("   NOTHING MOVED -- the card does not fire in this deck.")
        return 0
    print(__doc__.strip().splitlines()[0])
    return 2


if __name__ == "__main__":
    sys.exit(main())
