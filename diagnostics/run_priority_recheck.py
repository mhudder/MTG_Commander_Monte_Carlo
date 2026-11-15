#!/usr/bin/env python3
"""Queue item 48: the ADOPTED priority moves, re-measured on today's pod.

    python -m diagnostics.run_priority_recheck [--n=15000] [--decks=a,b]
    python -m diagnostics.run_priority_recheck --n=300     # smoke

Item 18's moves (§0z44, §0z86, §0z150) were swept and adopted on the formula
pod, before item 44's flip (§0z204) made attackers die and you block. This
does NOT re-run the sweep (the screen is 760 arms and ~tens of CPU-hours, and
it asks a different question: are there NEW moves). It asks only whether the
moves already made still pay: each is UNDONE against the list as it stands,
paired, N=15,000, both horizons, on a seed block none of item 18's tiers has
seen (§0z170: the winner of many arms is graded by the seeds that picked it).

The arms (B) are the current list with the old priorities put back; A is the
current list. The column printed is ADOPTED minus UNDONE, i.e. A - B, so a
positive number means the adopted move still wins.

It is `diagnostics/run_priority_sweep.py`'s machinery -- the same job, the
same shared A leg, the same NOOP gate, the same cache under
results/.priority_sweep/ keyed on each deck's fingerprint -- with only the
arms and the seed block chosen here.
"""
import json
import os
import sys

from diagnostics import run_priority_sweep as PS

# The adopted moves, as each deck module records them beside the card.
UNDO = {
    "karlov": {
        "§0z44 joint (Felidar Sovereign 9->7, Sorin 8->6)":
            {"Felidar Sovereign": 7.0, "Sorin, Solemn Visitor": 6.0},
    },
    "tivit": {
        "§0z44 joint (Tempting Contract 8.5->6.5, Mirkwood Bats 10->8, "
        "Rhystic Study 7.5->9.5)":
            {"Tempting Contract": 6.5, "Mirkwood Bats": 8.0,
             "Rhystic Study": 9.5},
        "§0z86/§0z150 Time Sieve 11->9": {"Time Sieve": 9.0},
    },
}
# Disjoint from every block item 18 used (1234.. through 36233) and from
# the tables' 5000.. .
SEED0 = 101234


def main() -> int:
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if "=" in a)
    n = int(opt.get("n", 15000))
    decks = opt["decks"].split(",") if "decks" in opt else list(UNDO)
    procs = int(opt.get("procs", os.cpu_count() or 4))
    horizons = (10, 20)
    arms_by_deck = {}
    cells = []
    for d in decks:
        deck, _ = PS.build_pending(d)
        have = {c.name: c.priority for c in PS.nonland(deck)}
        arms = []
        for label, moves in UNDO[d].items():
            missing = [k for k in moves if k not in have]
            if missing:
                raise SystemExit(f"{d}: not in the list: {missing}")
            arms.append((label, "joint:" + json.dumps(moves, sort_keys=True)))
        arms_by_deck[d] = arms
        for t in horizons:
            for a in ["base", "noop"] + [a for _l, a in arms]:
                cells.append((d, a, t, SEED0, n))
    print(f"adopted priority moves, UNDONE against the list as it stands. "
          f"N={n:,} paired, seeds {SEED0}..{SEED0 + n - 1}, horizons "
          f"{horizons}, staged lists (build_pending). Printed: ADOPTED minus "
          f"UNDONE (positive = the adopted move still wins).\n")
    sys.stdout.flush()
    results = PS.run_arms(cells, procs)
    print("THE TOOL'S OWN A/A CONTROL -- NOOP must change zero games:")
    if not PS.noop_gate(results, cells):
        print("\nNOOP CHANGED GAMES. Every row below is VOID.")
        return 1
    print()
    for d in decks:
        deck, _ = PS.build_pending(d)
        have = {c.name: c.priority for c in PS.nonland(deck)}
        base_line = ", ".join(
            f"T{t} won {results[(d, 'base', t, SEED0, n)][0].mean():.4f}"
            for t in horizons)
        print(f"== {d}   (as listed: {base_line})")
        for label, arm in arms_by_deck[d]:
            cols = []
            for t in horizons:
                # compare(base, arm) is arm - base; flip it to adopted - undone
                c = PS.compare(results[(d, arm, t, SEED0, n)],
                               results[(d, "base", t, SEED0, n)])
                cols.append(f"T{t} {PS.fmt(c)}")
            now = ", ".join(f"{k} {have[k]:g}" for k in sorted(
                json.loads(arm[len('joint:'):])))
            print(f"  {label}\n      now: {now}\n      " + "   ".join(cols))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
