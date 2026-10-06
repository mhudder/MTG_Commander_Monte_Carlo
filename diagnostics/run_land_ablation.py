#!/usr/bin/env python3
"""The land ablation: what every NONBASIC land is worth over a basic (§0z112).

    python -m diagnostics.run_land_ablation 15000 results/land_ablation_20261006.json
    python -m diagnostics.run_land_ablation 15000 OUT.json --decks=azusa,karlov
    python -m diagnostics.run_land_ablation --report results/land_ablation_20261006.json

WHY. `tools/ablation.py` blanks NONLAND cards only, so all 441 rows across
the seven tables are spells: 19-22 lands per deck have never been measured in
the deck they are in. There is no "blank land" -- every land taps for
something -- so the replacement is the slot a land actually competes with: a
BASIC. Each nonbasic is replaced by a fresh copy of the basic of the colour it
makes that the deck's spells ask for most (coloured pips over the nonland
cards, `demand`); a land that makes none of the deck's colours gets the
deck's most common basic (`candidates.filler_land`, §0z3's convention).

THE NUMBER IS land minus basic, paired, the tables' seeds (5000..) and N, one
T20 game per seed with T10 read off it (§0z93), on the staged list. It
measures what the engine does with the land: its colours, whether it enters
tapped, and whatever ability the engine implements -- nothing else.

WHICH HALF A LAND IS IN, BY IDENTITY, NOT BY READING (§0z66). Each land is
also played against a TWIN: the same Card with its name changed and its
`script` removed -- same colours, same enters-tapped, same tags. The engine
reads a land beyond those fields only by name or by script, so:
  BY NAME             some game of the first 1,000 differs from the twin:
                      the engine dispatches on the card's name or script,
                      so the row includes an implemented ability
  BY ITS FIELDS       every game identical: the engine plays it from its
                      `L()` fields alone -- colours, enters-tapped, and any
                      `lifegain` or `tags` it carries (printed beside it).
                      Rules text those fields do not encode is BLIND, and
                      the row is a floor on that land
The oracle text (Scryfall, cached beside the results) is printed under each
BY-ITS-FIELDS row, with a HEURISTIC flag for text beyond mana; the flag is
a reading aid, the identity test is the classification.

TWO CHECKS, so the tool is checked against numbers already committed (§0z35):
  * a NONLAND row blanked the tables' way must reproduce the deck's cached
    row exactly (the harness is the tables' harness);
  * a NOOP arm -- a basic replaced by a fresh copy of itself -- must change
    zero games (the copy-and-replace is not itself a change).
"""
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG, repl_priority
from edhmc.pending import build_pending
from edhmc.registry import DECKS as REGISTRY
from tools.candidates import filler_land

HORIZONS = (10, 20)
N_ID = 1000                     # identity games per land (exact, not a CI)
BASIC_OF = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain",
            "G": "Forest"}
BASICS = set(BASIC_OF.values()) | {"Wastes"}
ORACLE = os.path.join("results", "land_oracle.json")
CHECK_CARD = "Sol Ring"


def demand(deck) -> dict:
    """Coloured pips over the deck's nonland cards: what its spells ask for."""
    out = {c: 0 for c in BASIC_OF}
    for card in deck:
        if card.is_land:
            continue
        for k, v in (card.cost or {}).items():
            if k in out:
                out[k] += v
    return out


def nonbasics(deck):
    seen, out = set(), []
    for c in deck:
        if c.is_land and c.name not in BASICS and c.name not in seen:
            seen.add(c.name)
            out.append(c.name)
    return out


def basic_for(deck, land):
    """The basic this land would be swapped for (see the module docstring)."""
    want = demand(deck)
    have = {c.name: c for c in deck if c.is_land and c.name in BASICS}
    colours = [k for k in BASIC_OF if k in (land.produces or ())
               and BASIC_OF[k] in have]
    if colours:
        best = max(colours, key=lambda k: want[k])
        return dataclasses.replace(have[BASIC_OF[best]])
    return dataclasses.replace(filler_land(deck))


def swap(deck, name, card):
    out = list(deck)
    i = next(i for i, c in enumerate(out) if c.name == name)
    out[i] = card
    return out


def arm_deck(deck_name, arm):
    """`arm` is None (baseline), ("land", name), ("twin", name), ("noop", ""),
    or ("check", card name)."""
    deck, cmd = build_pending(deck_name)
    if arm is None:
        return deck, cmd
    kind, name = arm
    if kind == "land":
        land = next(c for c in deck if c.name == name)
        return swap(deck, name, basic_for(deck, land)), cmd
    if kind == "twin":
        land = next(c for c in deck if c.name == name)
        return swap(deck, name, dataclasses.replace(
            land, name=land.name + " ~twin", script=None)), cmd
    if kind == "noop":
        basic = filler_land(deck)
        return swap(deck, basic.name, dataclasses.replace(basic)), cmd
    if kind == "check":
        card = next(c for c in deck if c.name == name)
        run = AB.Run(deck_name, 1, HORIZONS)
        return swap(deck, name, AB.blank_like(
            card, repl_priority(deck), keep_types=run.blank_keeps_types)), cmd
    raise ValueError(arm)


def digest(r) -> str:
    """Every numeric output key of one game, hashed -- "identical" means all
    of them (§0z32), not the eight the tables read."""
    items = sorted((k, round(float(v), 9)) for k, v in r.items()
                   if isinstance(v, (int, float, bool)))
    return hashlib.sha1(repr(items).encode()).hexdigest()


def job(task):
    deck_name, arm, lo, hi, mode = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd = arm_deck(deck_name, arm)
    if mode == "cols":
        cols = AB.columns_all(run, deck, cmd, lo, hi)
        return task, {t: {m: cols[t][m].tolist() for m in run.metrics}
                      for t in HORIZONS}
    cfg = dict(DEFAULT_CFG, turns=max(HORIZONS), watch=frozenset())
    return task, [digest(run.sim(list(deck), cmd, cfg, 5000 + s))
                  for s in range(lo, hi)]


def measure(n, out_path, decks=None, procs=4):
    decks = decks or list(REGISTRY)
    parts = AB._chunks(n, procs)
    tasks = []
    for d in decks:
        deck, _ = build_pending(d)
        arms = [None, ("noop", "")] + [("land", x) for x in nonbasics(deck)]
        if any(c.name == CHECK_CARD for c in deck):
            arms.append(("check", CHECK_CARD))
        tasks += [(d, a, lo, hi, "cols") for a in arms for lo, hi in parts]
        id_parts = AB._chunks(N_ID, procs)
        tasks += [(d, a, lo, hi, "hash") for a in
                  [None] + [("twin", x) for x in nonbasics(deck)]
                  for lo, hi in id_parts]
    got = {}
    t0 = time.time()
    with Pool(procs) as pool:
        for i, (task, res) in enumerate(
                pool.imap_unordered(job, tasks, chunksize=1), 1):
            got[task] = res
            if i % 40 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)}  {time.time() - t0:.0f}s", flush=True)

    out = json.load(open(out_path)) if os.path.exists(out_path) else {
        "n": n, "decks": {}}
    for d in decks:
        deck, _ = build_pending(d)
        run = AB.Run(d, 1, HORIZONS)

        def col(arm, t, m):
            return np.concatenate([got[(d, arm, lo, hi, "cols")][t][m]
                                   for lo, hi in parts])

        def hashes(arm):
            return sum((got[(d, arm, lo, hi, "hash")]
                        for lo, hi in AB._chunks(N_ID, procs)), [])

        def cell(arm):
            res = {}
            for t in HORIZONS:
                for m in run.metrics:
                    x = col(None, t, m) - col(arm, t, m)
                    res[f"{m}{t}"] = [float(x.mean()),
                                      float(1.96 * x.std(ddof=1) / np.sqrt(n))]
            return res

        base_h = hashes(None)
        rows = {}
        for name in nonbasics(deck):
            land = next(c for c in deck if c.name == name)
            twin_h = hashes(("twin", name))
            rows[name] = {
                "basic": basic_for(deck, land).name,
                "produces": sorted(land.produces or ()),
                "tapped": bool(land.tapped),
                "script": land.script,
                "tags": sorted(land.tags or ()),
                "lifegain": float(getattr(land, "lifegain", 0) or 0),
                "copies": sum(1 for c in deck if c.name == name),
                "id_changed": sum(a != b for a, b in zip(base_h, twin_h)),
                "cells": cell(("land", name)),
            }
        noop = cell(("noop", ""))
        res = {"rows": rows, "demand": demand(deck),
               "noop_changed": int(sum(
                   np.any(col(None, t, m) != col(("noop", ""), t, m))
                   for t in HORIZONS for m in run.metrics)),
               "noop_won20": noop["won20"]}
        if any(c.name == CHECK_CARD for c in deck):
            res["check"] = cell(("check", CHECK_CARD))
        out["decks"][d] = res
    out["n"] = n
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("saved", out_path)


def fetch_oracle(names):
    cache = json.load(open(ORACLE)) if os.path.exists(ORACLE) else {}
    for name in names:
        if name in cache:
            continue
        url = ("https://api.scryfall.com/cards/named?exact="
               + urllib.parse.quote(name))
        req = urllib.request.Request(url, headers={
            "User-Agent": "EDHMC/1.0", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as fh:
                j = json.load(fh)
            text = j.get("oracle_text") or " // ".join(
                f.get("oracle_text", "") for f in j.get("card_faces", []))
            cache[name] = {"type_line": j.get("type_line", ""),
                           "oracle_text": text}
        except Exception as exc:                       # noqa: BLE001
            cache[name] = {"type_line": "?", "oracle_text": f"UNFETCHED: {exc}"}
        time.sleep(0.1)
    with open(ORACLE, "w") as fh:
        json.dump(dict(sorted(cache.items())), fh, indent=1)
    return cache


# A READING AID, NOT A CLASSIFICATION: lines that are only about mana, the
# land entering tapped, its life payment or fetching a land. Anything else in
# a BY-ITS-FIELDS land's text is flagged for a human to read -- it may be a
# clause a field already encodes (a lifegain, a shock tag), or a blind one.
MANA_LINE = [r"^\{T\}: Add", r"^\{T\}, Pay \d+ life: Add",
             r"enters (the battlefield )?tapped", r"^As .* enters",
             r"deals 1 damage to you", r"Add one mana of any",
             r"^\{T\}, Sacrifice .*: Search your library for an? .*card",
             r"^When .* enters, (return a land|you gain 1 life)",
             r"^\{T\}: Add \{[WUBRGC]\} or \{[WUBRGC]\}",
             r"^\(\{T\}: Add", r"^Flash$", r"^Hideaway", r"^Landfall"]


def beyond_mana(text) -> bool:
    text = re.sub(r"\([^)]*\)", "", text or "")
    for line in filter(None, (s.strip() for s in text.split("\n"))):
        if not any(re.search(p, line) for p in MANA_LINE):
            return True
    return False


def report(path):
    res = json.load(open(path))
    names = sorted({x for d in res["decks"].values() for x in d["rows"]})
    oracle = fetch_oracle(names)
    n = res["n"]
    print(f"LAND ABLATION, N={n:,} paired, seeds 5000.., staged lists. Each "
          f"nonbasic land against the BASIC it would be swapped for (the "
          f"colour the deck's spells want most). Win rate, land minus basic; "
          f"* = CI excludes zero.\n"
          f"  BY NAME       = some of {N_ID:,} games differ from a renamed, "
          f"script-free twin: an implemented ability is in the row.\n"
          f"  BY ITS FIELDS = every game identical: colours, tap state, and "
          f"the lifegain/tags shown; any rules text those do not encode is "
          f"BLIND (the row is a floor).\n")
    for d, r in res["decks"].items():
        cache_path = AB.Run(d, n, HORIZONS).cache
        cached = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
        chk = ""
        if "check" in r and CHECK_CARD in cached:
            ok = all(abs(r["check"][f"won{t}"][0]
                         - cached[CHECK_CARD][str(t)]["won"][0]) < 1e-12
                     for t in HORIZONS)
            chk = (f"{CHECK_CARD} row reproduces the cached table: "
                   f"{'YES' if ok else 'NO'}")
        print(f"{d.upper()}  demand {r['demand']}   NOOP changed "
              f"{r['noop_changed']} metric columns (must be 0)   {chk}")
        groups = {"BY NAME": [], "BY ITS FIELDS": []}
        for name, row in r["rows"].items():
            g = "BY NAME" if row["id_changed"] else "BY ITS FIELDS"
            groups[g].append((name, row))
        for g, rows in groups.items():
            if not rows:
                continue
            print(f"  -- {g} ({len(rows)})")
            rows.sort(key=lambda x: -x[1]["cells"]["won20"][0])
            for name, row in rows:
                c = row["cells"]
                cells = "  ".join(
                    f"T{t} {c[f'won{t}'][0]:+.4f} ±{c[f'won{t}'][1]:.4f}"
                    f"{'*' if abs(c[f'won{t}'][0]) > c[f'won{t}'][1] else ' '}"
                    for t in HORIZONS)
                tag = (f"vs {row['basic']:<8} {''.join(row['produces']):<6}"
                       f"{'tapped' if row['tapped'] else '      '}")
                extra = (f"  [{row['id_changed']} of {N_ID} games differ]"
                         if row["id_changed"] else "")
                fields = ", ".join(row.get("tags", [])
                                   + ([f"gain {row['lifegain']:g}"]
                                      if row.get("lifegain") else []))
                if fields:
                    extra += f"  fields: {fields}"
                print(f"    {name:<32} {tag}  {cells}{extra}")
                if not row["id_changed"]:
                    o = oracle.get(name, {})
                    text = (o.get("oracle_text") or "").replace("\n", " / ")
                    if beyond_mana(o.get("oracle_text")):
                        print(f"        text beyond mana (heuristic -- read it): "
                              f"{text[:150]}")
        print()


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        only = next((a.split("=", 1)[1].split(",") for a in sys.argv[3:]
                     if a.startswith("--decks=")), None)
        measure(int(sys.argv[1]), sys.argv[2], decks=only)
