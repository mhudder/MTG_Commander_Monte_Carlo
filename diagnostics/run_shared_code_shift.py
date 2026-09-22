#!/usr/bin/env python3
"""How much did a SHARED-CODE change move each deck's baseline, at the
table's own N -- measured, not argued (§0z30, and the rule in CLAUDE.md).

`tools/check_unchanged_decks.py` answers "did anything move" on 400 seeds
and is meant to come back bit-identical. When a change is SUPPOSED to move
every deck -- M1's mulligan fix and M2's pod-phase order, 2026-09-17 -- the
question is "by how much, and is it inside the noise the tables are read
at", which needs the tables' N and a paired comparison. Same idea as an
A/B run, with the two legs being the same list on two versions of the
CODE: run `--out` in a worktree at the old commit and in the live tree,
then `--diff` the two files. Every game is one seed, same seeds both sides,
so the per-deck difference is paired and its CI is the honest one.

    git worktree add ../edhmc_old <commit>
    (cd ../edhmc_old && python -m diagnostics.run_shared_code_shift --out=old.json)
    python -m diagnostics.run_shared_code_shift --out=new.json
    python -m diagnostics.run_shared_code_shift --diff old.json new.json

`--n=` (default 15000) and `--decks=a,b` narrow it. `--cfg=k=v,k=v` sets
knobs on this leg only, so a change that ships behind a knob can be
measured with BOTH legs in one tree -- `--cfg=decking_loss=False` against
the default is the knob's worth, on the same seeds, with no worktree
(values are read as Python literals: False, 3, "legacy"). The baseline is
`build_pending(deck)` -- the STAGED list, which is what every current
table is measured on -- so a staged deck is compared on the list its cache
was built from (the §0z29 trap, avoided by construction).
"""
import json
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY

N = 15000
DECKS = tuple(REGISTRY)
METRICS = ("won", "damage", "final_life", "cards_drawn", "stranded_mv",
           "turns_played")
HORIZONS = (10, 20)


def _sim(deck):
    return REGISTRY[deck].sim


def parse_cfg(text):
    import ast
    out = {}
    for kv in filter(None, text.split(",")):
        k, v = kv.split("=", 1)
        try:
            out[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            out[k] = v
    return out


def measure_one(args):
    deck, turns, n, extra = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG
    deck_list, cmd = build_pending(deck)
    sim = _sim(deck)
    rows = {m: [] for m in METRICS}
    for s in range(n):
        r = sim(deck_list, cmd, dict(DEFAULT_CFG, turns=turns,
                                     watch=frozenset(), **extra), 5000 + s)
        for m in METRICS:
            rows[m].append(float(r.get(m, 0.0)))
    return f"{deck}@T{turns}", rows


def diff(old_path, new_path):
    old = json.load(open(old_path))
    new = json.load(open(new_path))
    print(f"{'deck':<16}{'metric':<14}{'old':>10}{'new':>10}"
          f"{'new-old':>10}{'95% CI':>22}")
    for key in old:
        if key not in new:
            continue
        for m in METRICS:
            a = np.array(old[key][m]); b = np.array(new[key][m])
            n = min(len(a), len(b)); a, b = a[:n], b[:n]
            d = b - a
            hw = 1.96 * d.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
            star = " *" if abs(d.mean()) > hw and hw > 0 else ""
            print(f"{key:<16}{m:<14}{a.mean():>10.4f}{b.mean():>10.4f}"
                  f"{d.mean():>+10.4f}   [{d.mean()-hw:>+8.4f}, "
                  f"{d.mean()+hw:>+8.4f}]{star}")
        moved = int(np.sum(np.array(old[key]['won']) != np.array(new[key]['won'])))
        print(f"{'':<16}{'seeds whose result changed':<30}{moved:>6} of {n}")
        print()


def main():
    args = sys.argv[1:]
    if "--diff" in args:
        i = args.index("--diff")
        diff(args[i + 1], args[i + 2])
        return 0
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")), list(DECKS))
    out = next((a.split("=")[1] for a in args if a.startswith("--out=")),
               "results/shared_code_shift.json")
    extra = next((parse_cfg(a.split("=", 1)[1]) for a in args
                  if a.startswith("--cfg=")), {})
    jobs = [(d, t, n, extra) for d in decks for t in HORIZONS]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure_one, jobs))
    json.dump(res, open(out, "w"))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
