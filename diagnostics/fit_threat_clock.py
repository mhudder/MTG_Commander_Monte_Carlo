#!/usr/bin/env python3
"""Retune the pod's kill timing for a pod whose kills can be delayed (§0z132).

    python -m diagnostics.fit_threat_clock                  # N=1500, shifts 0..3
    python -m diagnostics.fit_threat_clock --n=3000 --shifts=1.5,2,2.5
    python -m diagnostics.fit_threat_clock --cfg=rearm_rule=reland   (§0z137)

THE TARGET, the owner's (2026-10-13): with the POD_V4 candidate on --
`pod_bodies` and `pod_threats` -- the mean T20 win rate over the ACTIVE decks
(`registry.ACTIVE`, staged lists) equals today's pod's. The pod is then as
strong as it was on average, and a deck's answers show up as its edge over a
deck without them, not as everybody's win rate going up.

`threat_clock_shift` brings every kill that many rounds earlier, its
fraction rolled per opponent (`opponents.roll_threat_routes`). For each
shift this prints every deck's T10 and T20 win rate against the off pod on
the same seeds, the mean, and the shift where the mean crosses the target,
interpolated between the two shifts that bracket it.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.registry import ACTIVE, DECKS as REGISTRY

N = 1500
SHIFTS = (0.0, 1.0, 2.0, 3.0)
POD_V4 = dict(pod_bodies=True, pod_threats=True)


def measure(args):
    deck, shift, n, cfg = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG
    deck_list, cmd = build_pending(deck)
    sim = REGISTRY[deck].sim
    # `--cfg` knobs go on the candidate pod only: the target is today's.
    extra = ({} if shift is None
             else dict(POD_V4, threat_clock_shift=shift, **cfg))
    w10, w20, turns = [], [], []
    for s in range(n):
        r = sim(deck_list, cmd, dict(DEFAULT_CFG, turns=20,
                                     snapshot_rounds=(10,),
                                     watch=frozenset(), **extra), 5000 + s)
        w10.append(float(r["at_rounds"][10]["won"]))
        w20.append(float(r["won"]))
        turns.append(float(r.get("turns_played", 0)))
    return (deck, shift), (np.array(w10), np.array(w20), np.array(turns))


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    shifts = next((tuple(float(x) for x in a.split("=")[1].split(","))
                   for a in args if a.startswith("--shifts=")), SHIFTS)
    from diagnostics.run_shared_code_shift import parse_cfg
    cfg = next((parse_cfg(a.split("=", 1)[1]) for a in args
                if a.startswith("--cfg=")), {})
    decks = list(ACTIVE)
    jobs = [(d, s, n, cfg) for d in decks for s in (None,) + shifts]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    target = np.mean([res[(d, None)][1].mean() for d in decks])
    print(f"POD_V4 candidate {dict(POD_V4, **cfg)}, N={n} per deck, "
          f"staged lists, "
          f"seeds 5000..{5000 + n - 1}")
    print(f"target: mean T20 win rate of the off pod over {len(decks)} "
          f"active decks = {target:.4f}\n")
    means = []
    for s in shifts:
        print(f"threat_clock_shift={s}")
        m = []
        for d in decks:
            o10, o20, oturn = res[(d, None)]
            a10, a20, aturn = res[(d, s)]
            d20 = a20 - o20
            hw = 1.96 * d20.std(ddof=1) / np.sqrt(n)
            print(f"   {d:<11} T10 {a10.mean():.4f} ({a10.mean() - o10.mean():+.4f})"
                  f"   T20 {a20.mean():.4f} ({d20.mean():+.4f} ±{hw:.4f})"
                  f"   turns {aturn.mean():.2f} ({aturn.mean() - oturn.mean():+.2f})")
            m.append(a20.mean())
        means.append(np.mean(m))
        print(f"   mean T20 {means[-1]:.4f}  ({means[-1] - target:+.4f} "
              f"against the target)\n")
    fit = None
    for (s0, m0), (s1, m1) in zip(zip(shifts, means), zip(shifts[1:], means[1:])):
        if (m0 - target) * (m1 - target) <= 0 and m0 != m1:
            fit = s0 + (target - m0) * (s1 - s0) / (m1 - m0)
            break
    print("fitted threat_clock_shift: "
          + (f"{fit:.2f}" if fit is not None else "not bracketed -- widen --shifts"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
