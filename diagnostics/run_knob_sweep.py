#!/usr/bin/env python3
"""One numeric knob at several values, each PAIRED against a base value, on
every active deck's staged list (§0z191).

    python -m diagnostics.run_knob_sweep KNOB BASE V1,V2,... [--n=15000]
                                         [--seed0=5000] [--decks=a,b]
                                         [--reach=counter] [--out=PATH]

e.g. `python -m diagnostics.run_knob_sweep hold_back_pad 0 2,5,10
--reach=held_back`. Every arm is `DEFAULT_CFG` plus KNOB=V, T20 with T10
read off the same game, on seeds SEED0..SEED0+N-1, so each arm minus BASE
is paired by seed. Prints, per deck and value, the T10 and T20 win-rate
difference with its 95% CI (`*` when the CI excludes 0) and the REACH
counter's mean in both legs, then the mean over the decks of each
difference with its CI (the decks are independent, so the variances add).

`fit_pod_knob` asks a different question -- where a pod knob must sit to
hold the mean win rate -- and prints levels, not paired differences;
`run_knob_ab` is one boolean knob on against off, with its identity check.

THE WINNER OF A SWEEP IS GRADED BY THE SEEDS THAT PICKED IT (§0z170): pick
on one block, then re-run the pick alone against BASE with `--seed0` on a
block nobody looked at, and quote that.
"""
import ast
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

CHUNK = 500


def _lit(v):
    try:
        return ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return v


def _job(args):
    deck, knob, value, lo, hi, reach = args
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    lst, cmd = build_pending(deck)
    sim = DECKS[deck].sim
    out = np.zeros((hi - lo, 4))
    for i, s in enumerate(range(lo, hi)):
        r = sim(lst, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                               watch=frozenset(), **{knob: value}), s)
        out[i] = (float(r["at_rounds"][10]["won"]), float(r["won"]),
                  float(r.get(reach, 0.0)) if reach else 0.0,
                  float(r.get("turns_played", 0.0)))
    return deck, value, lo, out


def main() -> int:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) for a in sys.argv[1:]
                if a.startswith("--") and "=" in a)
    if len(pos) != 3:
        print(__doc__)
        return 2
    knob, base = pos[0], _lit(pos[1])
    values = [_lit(v) for v in pos[2].split(",")]
    n = int(opts.get("--n", 15000))
    seed0 = int(opts.get("--seed0", 5000))
    reach = opts.get("--reach")
    from edhmc.registry import ACTIVE
    decks = opts["--decks"].split(",") if "--decks" in opts else list(ACTIVE)
    arms = [base] + [v for v in values if v != base]
    jobs = [(d, knob, v, lo, min(lo + CHUNK, seed0 + n), reach)
            for d in decks for v in arms
            for lo in range(seed0, seed0 + n, CHUNK)]
    res = {}
    with Pool(4) as pool:
        for d, v, lo, block in pool.imap_unordered(_job, jobs):
            res.setdefault((d, repr(v)), {})[lo] = block
    cols = {k: np.vstack([b[lo] for lo in sorted(b)]) for k, b in res.items()}

    def diff(d, v, c):
        x = cols[(d, repr(v))][:, c] - cols[(d, repr(base))][:, c]
        return x.mean(), x.var(ddof=1) / len(x)

    py = sys.version.split()[0]
    lines = [f"{knob}: each value minus {knob}={base!r}, paired, the staged "
             f"lists, N={n:,} a deck, seeds {seed0}..{seed0 + n - 1}, T20 "
             f"(T10 off the same game), python {py} / numpy {np.__version__}",
             "95% CI; * = excludes 0" + (f"; reach `{reach}` a game, "
                                         "value leg / base leg" if reach else ""),
             ""]
    for d in decks:
        lines.append(d)
        for v in arms[1:]:
            cells = []
            for c, t in ((0, "T10"), (1, "T20")):
                mu, var = diff(d, v, c)
                ci = 1.96 * var ** 0.5
                cells.append(f"{t} {mu:+.4f} +-{ci:.4f}"
                             f"{'*' if abs(mu) > ci else ' '}")
            r = ""
            if reach:
                r = (f"  {reach} {cols[(d, repr(v))][:, 2].mean():.3f}"
                     f" / {cols[(d, repr(base))][:, 2].mean():.3f}")
            turns, _ = diff(d, v, 3)
            lines.append(f"  {knob}={v!r:<8}" + "  ".join(cells) + r
                         + f"  turns {turns:+.3f}")
        lines.append("")
    lines.append(f"MEAN OVER {len(decks)} DECKS (each deck's paired "
                 "difference, averaged; variances add)")
    for v in arms[1:]:
        cells = []
        for c, t in ((0, "T10"), (1, "T20")):
            parts = [diff(d, v, c) for d in decks]
            mu = sum(p[0] for p in parts) / len(parts)
            ci = 1.96 * sum(p[1] for p in parts) ** 0.5 / len(parts)
            cells.append(f"{t} {mu:+.4f} +-{ci:.4f}"
                         f"{'*' if abs(mu) > ci else ' '}")
        lines.append(f"  {knob}={v!r:<8}" + "  ".join(cells))
    text = "\n".join(lines)
    print(text)
    out = opts.get("--out")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
