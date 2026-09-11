#!/usr/bin/env python3
"""Did a shared-code change move a deck it was not supposed to move?

`edhmc/opponents.py` is in EVERY deck's cache fingerprint, so any edit to it
moves all six fingerprints whether or not it moves any numbers. This project
has been wrong about that distinction once already -- `regen_tables.sh`'s
header argued Karlov was unaffected by the 2026-09-05 work, which was true of
the Grist change and false of the "another creature you control" one -- so the
rule since then has been to CHECK rather than argue, with a git worktree at the
previous commit running the same seeds through both versions.

    git worktree add ../edhmc_head HEAD
    python check_unchanged_decks.py --out new.json
    (cd ../edhmc_head && python check_unchanged_decks.py --out old.json)
    python check_unchanged_decks.py --diff old.json new.json

Prints a per-metric diff. BIT-IDENTICAL is the pass condition for a deck the
change was not meant to touch; anything else means its table needs
regenerating, whatever the argument for why it should not.
"""
import json
import sys

DECKS = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
METRICS = ("won", "lost", "damage", "cards_drawn", "turns_played",
           "final_life", "mana_spent", "stranded_mv")


def sim_for(deck):
    from edhmc import engine, lorehold, karlov, tivit
    mods = {"rendmaw": engine, "lorehold": lorehold, "karlov": karlov,
            "tivit": tivit}
    if deck == "shilgengar":
        from edhmc import shilgengar
        mods["shilgengar"] = shilgengar
    if deck == "azusa":
        from edhmc import azusa
        mods["azusa"] = azusa
    return mods[deck].simulate


def build(deck):
    from edhmc.decks import (rendmaw_v12, lorehold_v16, karlov_v2, tivit_v1,
                             shilgengar_v1, azusa_v1)
    return {"rendmaw": rendmaw_v12, "lorehold": lorehold_v16,
            "karlov": karlov_v2, "tivit": tivit_v1,
            "shilgengar": shilgengar_v1, "azusa": azusa_v1}[deck].build()


def measure(n, turns):
    from edhmc.experiment import DEFAULT_CFG
    out = {}
    for deck in DECKS:
        deck_list, cmd = build(deck)
        sim = sim_for(deck)
        totals = {m: 0.0 for m in METRICS}
        for s in range(n):
            # The same seeds both sides. Not a statistical comparison: the
            # answer wanted here is "identical" or "not", not "close".
            r = sim(deck_list, cmd, dict(DEFAULT_CFG, turns=turns,
                                         watch=frozenset()), 3000 + s)
            for m in METRICS:
                totals[m] += float(r.get(m, 0.0))
        out[deck] = {m: totals[m] / n for m in METRICS}
        print(f"  measured {deck}", file=sys.stderr)
    return out


def diff(old_path, new_path):
    old = json.load(open(old_path))
    new = json.load(open(new_path))
    bad = 0
    for deck in DECKS:
        if deck not in old or deck not in new:
            print(f"  {deck:<12} not in both files, skipped")
            continue
        moved = {m: (old[deck][m], new[deck][m]) for m in METRICS
                 if old[deck][m] != new[deck][m]}
        if not moved:
            print(f"  {deck:<12} BIT-IDENTICAL on all {len(METRICS)} metrics")
            continue
        bad += 1
        print(f"  {deck:<12} MOVED on {len(moved)} of {len(METRICS)} metrics")
        for m, (a, b) in moved.items():
            print(f"      {m:<16}{a:>14.5f} ->{b:>14.5f}   {b - a:>+12.5f}")
    print(f"\n  {bad} deck(s) moved.")
    return bad


def main():
    args = sys.argv[1:]
    if "--diff" in args:
        i = args.index("--diff")
        diff(args[i + 1], args[i + 2])
        # Always exit 0: a deck that MOVED is not necessarily a failure -- the
        # decks whose own engine changed are supposed to move. Reading which
        # ones did is the whole output, so it is not reduced to a status code.
        return 0
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 400)
    turns = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--turns=")), 20)
    out = next((a.split("=")[1] for a in args if a.startswith("--out=")),
               "baselines.json")
    json.dump(measure(n, turns), open(out, "w"), indent=1, sort_keys=True)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
