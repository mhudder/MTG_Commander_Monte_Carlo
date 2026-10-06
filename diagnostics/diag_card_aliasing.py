#!/usr/bin/env python3
"""Which decks played differently while copies of a basic shared ONE Card
object? (§0z112)

    python -m diagnostics.diag_card_aliasing 15000 > results/card_aliasing_20261006.txt

Every deck module built its basics as `[L("Forest", "G")] * n`: n references
to one object. The land ablation's NOOP arm caught it -- a basic replaced by
a field-identical copy changed games in rendmaw and trostani -- and the
cause is identity checks reading two copies as one card (Shigeki's
`c is land`, trostani's hideaway `c is not pick`). The modules now build one
object per copy and `pending.validate` refuses an aliased list.

This counts, per deck, the games (staged list, seeds 5000.., T20, every
numeric output key hashed) whose outcome differs between the list as built
today and the same list re-aliased the old way. Zero means the deck's
committed table is unaffected; anything else means its numbers moved.
"""
import sys
from multiprocessing import Pool

from diagnostics.run_land_ablation import digest
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import BASICS, build_pending
from edhmc.registry import DECKS

CHUNKS = 4


def realias(deck):
    first = {}
    out = []
    for c in deck:
        if c.name in BASICS:
            out.append(first.setdefault(c.name, c))
        else:
            out.append(c)
    return out


def job(task):
    d, lo, hi = task
    deck, cmd = build_pending(d)
    old = realias(deck)
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset())
    sim = DECKS[d].sim
    diff, won = [], 0.0
    for s in range(lo, hi):
        a = sim(list(old), cmd, cfg, 5000 + s)
        b = sim(list(deck), cmd, cfg, 5000 + s)
        if digest(a) != digest(b):
            diff.append(s)
            won += float(b["won"]) - float(a["won"])
    return d, diff, won


def main():
    n = int(sys.argv[1])
    tasks = [(d, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for d in DECKS for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        res = p.map(job, tasks, chunksize=1)
    print(f"Games that differ between aliased and distinct basics, N={n:,} per "
          f"deck, seeds 5000.., staged lists, T20, every numeric key (§0z112).\n")
    for d in DECKS:
        diff = sorted(s for dd, ds, _ in res if dd == d for s in ds)
        won = sum(w for dd, _, w in res if dd == d)
        print(f"  {d:<11} {len(diff):>5} games differ   net won {won:+.0f}   "
              f"first seeds {[5000 + s for s in diff[:5]]}")


if __name__ == "__main__":
    main()
