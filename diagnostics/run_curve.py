#!/usr/bin/env python3
"""The returns curve of a redundant group: what the 1st, 2nd, ... copy of one
effect is worth (§0z100).

    python -m diagnostics.run_curve 15000 results/curve_20261002.json
    python -m diagnostics.run_curve --report results/curve_20261002.json

§0z99 found two groups worth more together than their rows add up to --
azusa's four landfall creatures and karlov's five gain->drain cards -- which
says returns DIMINISH, from two points only (all in, all out). This measures
the whole curve: EVERY subset of the group is blanked (16 for azusa, 32 for
karlov), with the tables' blank, seeds 5000.., N and staged list. For each
k, the loss from removing k cards is averaged over every k-subset, per game,
so it does not depend on WHICH cards are removed:

    L(k)    = mean over |S|=k of (baseline - deck without S), per game
    V(m)    = L(n) - L(n-m)       the value of having m copies, from none
    step(m) = V(m) - V(m-1)       what the m-th copy adds

Every quantity is a per-game difference of paired columns, so each carries
its own CI. Averaging over subsets is also what makes step(m) the average
marginal value of the m-th copy over every order the copies could arrive in.

TWO CHECKS, both against numbers already committed:
  * L(1) must equal the mean of the members' cached table rows (exactly);
  * L(n) must equal §0z99's group number (exactly, same seeds and blank).
"""
import glob
import itertools
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from diagnostics.run_groups import GROUPS, blank_group
from edhmc.pending import build_pending

HORIZONS = (10, 20)
CURVES = {
    "azusa": "landfall creatures",
    "karlov": "gain -> drain",
}


def job(task):
    deck_name, subset, lo, hi = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd = build_pending(deck_name)
    if subset:
        deck = blank_group(run, deck, list(subset))
    cols = AB.columns_all(run, deck, cmd, lo, hi)
    return task, {t: cols[t]["won"] for t in HORIZONS}


def measure(n, out_path, procs=4):
    parts = AB._chunks(n, procs)
    tasks = []
    for deck, group in CURVES.items():
        members = GROUPS[deck][group]
        for k in range(len(members) + 1):
            for sub in itertools.combinations(members, k):
                tasks += [(deck, sub, lo, hi) for lo, hi in parts]
    got = {}
    with Pool(procs) as pool:
        for i, (task, cols) in enumerate(
                pool.imap_unordered(job, tasks, chunksize=1), 1):
            got[task] = cols
            if i % (4 * procs) == 0:
                print(f"  {i}/{len(tasks)}", flush=True)

    def col(d, sub, t):
        return np.concatenate([got[(d, sub, lo, hi)][t] for lo, hi in parts])

    def ci(x):
        return [float(x.mean()), float(1.96 * x.std(ddof=1) / np.sqrt(len(x)))]

    out = {"n": n, "decks": {}}
    for deck, group in CURVES.items():
        members = GROUPS[deck][group]
        nm = len(members)
        cpath = AB.Run(deck, n, HORIZONS).cache
        cache = json.load(open(cpath)) if os.path.exists(cpath) else {}
        res = {"group": group, "members": members}
        for t in HORIZONS:
            base = col(deck, (), t)
            L = [np.zeros(n)]
            for k in range(1, nm + 1):
                subs = list(itertools.combinations(members, k))
                L.append(np.mean([base - col(deck, s, t) for s in subs], axis=0))
            V = [L[nm] - L[nm - m] for m in range(nm + 1)]
            res[f"T{t}"] = {
                "V": [ci(v) if m else [0.0, 0.0] for m, v in enumerate(V)],
                "step": [ci(V[m] - V[m - 1]) for m in range(1, nm + 1)],
                "check_rows": [float(L[1].mean()),
                               (float(np.mean([cache[x][str(t)]["won"][0]
                                               for x in members]))
                                if cache else None)],
            }
        out["decks"][deck] = res
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("saved", out_path)


def report(path):
    res = json.load(open(path))
    groups = {}
    # The group number to check against is the NEWEST group run's (§0z99),
    # found on disk rather than named, so the check follows a re-run.
    found = sorted(glob.glob("results/groups_*.json"))
    gpath = found[-1] if found else ""
    if gpath:
        groups = json.load(open(gpath))["decks"]
    print(f"RETURNS CURVES, N={res['n']:,} paired, every subset of the group "
          f"blanked, seeds 5000.., staged lists. Win rate.\n"
          f"  V(m) = having m copies against none;  step = what the m-th "
          f"copy adds (averaged over every order).\n")
    for deck, r in res["decks"].items():
        print(f"{deck.upper()} -- {r['group']}: {', '.join(r['members'])}")
        for t in ("T10", "T20"):
            c = r[t]
            lone, cached = c["check_rows"]
            # Read the cache NOW, not the copy stored at measurement time: a
            # rebuild after the curve run would otherwise be checked against
            # the table it replaced (it was, once -- §0z100).
            cpath = AB.Run(deck, res["n"], HORIZONS).cache
            if os.path.exists(cpath):
                live = json.load(open(cpath))
                cached = float(np.mean([live[x][t[1:]]["won"][0]
                                        for x in r["members"]]))
            ok_rows = cached is not None and abs(lone - cached) < 1e-12
            g = groups.get(deck, {}).get(r["group"], {})
            gv = g.get("cells", {}).get(f"won{t[1:]}", {}).get("group", [None])[0]
            ok_grp = gv is not None and abs(c["V"][-1][0] - gv) < 1e-12
            print(f"  {t}: checks -- one removed = mean cached row "
                  f"{'YES' if ok_rows else 'NO'};  all removed = §0z99 group "
                  f"{'YES' if ok_grp else 'NO'}")
            for m, (s, v) in enumerate(zip(c["step"], c["V"][1:]), 1):
                bar = "#" * max(0, int(round(s[0] * 400)))
                print(f"    copy {m}: adds {s[0]:+.4f} ±{s[1]:.4f}   "
                      f"total {v[0]:+.4f} ±{v[1]:.4f}   {bar}")
        print()


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        measure(int(sys.argv[1]), sys.argv[2])
