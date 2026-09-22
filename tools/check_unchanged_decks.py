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

`--cfg=k=v,k=v` sets knobs on the side it is passed to. A change that ships
behind a knob claims the knob's OLD value reproduces the old code; running
the new tree with `--cfg=<old values>` against a worktree at the old commit
is that claim checked (2026-09-22: `decking_loss=False,
horn_doubled_legacy=True` against the commit before queued item 17).

Prints a per-metric diff. BIT-IDENTICAL is the pass condition for a deck the
change was not meant to touch; anything else means its table needs
regenerating, whatever the argument for why it should not.
"""
import json
import sys

from edhmc.registry import DECKS as REGISTRY

DECKS = tuple(REGISTRY)
METRICS = ("won", "lost", "damage", "cards_drawn", "turns_played",
           "final_life", "mana_spent", "stranded_mv")


def sim_for(deck):
    return REGISTRY[deck].sim


def build(deck):
    # The deck MODULE, deliberately: this compares CODE, and a staged swap
    # is not code (see CLAUDE.md, "more than one right check").
    return REGISTRY[deck].build()


def measure(n, turns, extra=None):
    from edhmc.experiment import DEFAULT_CFG
    extra = extra or {}
    out = {}
    for deck in DECKS:
        deck_list, cmd = build(deck)
        sim = sim_for(deck)
        totals = {m: 0.0 for m in METRICS}
        for s in range(n):
            # The same seeds both sides. Not a statistical comparison: the
            # answer wanted here is "identical" or "not", not "close".
            r = sim(deck_list, cmd, dict(DEFAULT_CFG, turns=turns,
                                         watch=frozenset(), **extra),
                    3000 + s)
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
    extra = {}
    for a in args:
        if a.startswith("--cfg="):
            from diagnostics.run_shared_code_shift import parse_cfg
            extra = parse_cfg(a.split("=", 1)[1])
    json.dump(measure(n, turns, extra), open(out, "w"), indent=1,
              sort_keys=True)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
