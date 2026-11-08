#!/usr/bin/env python3
"""Where must one pod knob sit so the mean T20 win rate is what it was?

    python -m diagnostics.fit_pod_knob KNOB V1,V2,... [--n=1500]
                                       [--target=k=v,...] [--cand=k=v,...]

e.g. `python -m diagnostics.fit_pod_knob incidental_rate 0.6,0.8,1.0
--target=untapped_blockers=False` (§0z186). `fit_threat_clock` is the same
measurement for `threat_clock_shift` on §0z132's pod, written first; this
one takes any knob and any two pods.

THE TARGET, the owner's rule since §0z140: when the pod changes, the mean
T20 win rate over the ACTIVE decks (`registry.ACTIVE`, staged lists) stays
what it was -- the pod is as strong as it was on average, and a deck's
edge shows as an edge rather than as everyone's win rate moving. The target
pod is `DEFAULT_CFG` plus `--target`; each candidate is `DEFAULT_CFG` plus
`--cand` plus KNOB=V. Same seeds (5000..), so each candidate's difference
from the target is paired. Prints each deck's T10 and T20 win rate and mean
turns for the target and every value, the means, and the value where the
mean T20 crosses the target, interpolated linearly between the two values
that bracket it.
"""
import ast
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())


def parse(text):
    out = {}
    for kv in filter(None, (text or "").split(",")):
        k, v = kv.split("=", 1)
        try:
            out[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            out[k] = v
    return out


def measure(args):
    deck, label, extra, n = args
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    lst, cmd = build_pending(deck)
    sim = DECKS[deck].sim
    w10, w20, turns = [], [], []
    for s in range(n):
        r = sim(lst, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                               watch=frozenset(), **extra), 5000 + s)
        w10.append(float(r["at_rounds"][10]["won"]))
        w20.append(float(r["won"]))
        turns.append(float(r.get("turns_played", 0)))
    return (deck, label), (np.array(w10), np.array(w20), np.array(turns))


def main() -> int:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) for a in sys.argv[1:]
                if a.startswith("--") and "=" in a)
    if len(pos) != 2:
        print(__doc__)
        return 2
    knob = pos[0]
    values = [ast.literal_eval(v) for v in pos[1].split(",")]
    n = int(opts.get("--n", 1500))
    target_cfg = parse(opts.get("--target"))
    cand_cfg = parse(opts.get("--cand"))
    from edhmc.registry import ACTIVE
    decks = list(ACTIVE)
    jobs = [(d, None, target_cfg, n) for d in decks]
    jobs += [(d, v, dict(cand_cfg, **{knob: v}), n)
             for d in decks for v in values]
    with Pool(4) as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    target = np.mean([res[(d, None)][1].mean() for d in decks])
    py = sys.version.split()[0]
    print(f"fit {knob} over {values}: target pod DEFAULT_CFG + {target_cfg}, "
          f"candidates + {cand_cfg}; N={n} a deck, staged lists, seeds "
          f"5000..{5000 + n - 1}, python {py}")
    print(f"target: mean T20 win rate over {len(decks)} active decks = "
          f"{target:.4f}; mean turns "
          f"{np.mean([res[(d, None)][2].mean() for d in decks]):.2f}\n")
    print(f"{'deck':11s} {'target T10':>10s} {'T20':>7s} {'turns':>6s}"
          + "".join(f" | {knob}={v!s:<6} T20 (diff ±)" for v in values))
    for d in decks:
        o10, o20, ot = res[(d, None)]
        row = f"{d:11s} {o10.mean():10.4f} {o20.mean():7.4f} {ot.mean():6.2f}"
        for v in values:
            a10, a20, at = res[(d, v)]
            dd = a20 - o20
            hw = 1.96 * dd.std(ddof=1) / np.sqrt(n)
            row += f" | {a20.mean():.4f} ({dd.mean():+.4f} ±{hw:.4f})"
        print(row)
    means = [np.mean([res[(d, v)][1].mean() for d in decks]) for v in values]
    turns = [np.mean([res[(d, v)][2].mean() for d in decks]) for v in values]
    print("\nmean T20: " + ", ".join(f"{knob}={v}: {m:.4f} ({t:.2f} turns)"
                                     for v, m, t in zip(values, means, turns)))
    cross = None
    for (v0, m0), (v1, m1) in zip(zip(values, means),
                                  zip(values[1:], means[1:])):
        if (m0 - target) * (m1 - target) <= 0 and m0 != m1:
            cross = v0 + (target - m0) * (v1 - v0) / (m1 - m0)
            break
    print(f"crossing: {knob} = {cross:.3f}" if cross is not None
          else "crossing: not bracketed by these values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
