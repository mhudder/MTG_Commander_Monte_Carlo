#!/usr/bin/env python3
"""Forbidden Orchard against the basic it would replace (§0z128).

A land candidate is cut for a land, so its candidate row is the swap itself:
`-<basic> +Forbidden Orchard`, the basic `run_land_ablation.basic_for` picks
(the colour of the two it makes that karlov's spells want most) -- §0z113's
shape, which measured karlov's other land candidates the same way.

Three arms, each paired on the same seeds against the live staged list:

  1. orchard          the swap, with the pilot's idle tap (`orchard_idle_tap`,
                      the default): an Orchard the turn left untapped is
                      tapped for its trigger alone when a payoff is out.
  2. orchard-naive    the same swap with `orchard_idle_tap=False` -- the
                      Orchard fires only when its mana is spent. The policy
                      said out loud is measured against the pilot without it.
  3. noop             the basic replaced by a fresh copy of itself. Must read
                      exactly zero on every metric.

The cost is charged as the model charges any pod creature: each Spirit is +1
to an opponent's creature count, which is a blocker AND chip damage to you
(`opponents.incidental_damage` reads the same count, §4). It is charged as one
AVERAGE pod creature, so a 1/1 is if anything over-charged.

    python -m diagnostics.run_karlov_orchard        > results/karlov_orchard.txt
    python -m diagnostics.run_karlov_orchard --n=40 # smoke test
"""
import dataclasses
import sys
import time
from multiprocessing import Pool

from diagnostics.run_land_ablation import basic_for
from edhmc.decks import karlov_v2
from edhmc.experiment import analyse, run_ab
from edhmc.pending import build_pending
from edhmc.registry import DECKS as REGISTRY

N = 15000
HORIZONS = (10, 20)
METRICS = ("won", "damage", "combat_damage", "lifegain_triggers",
           "life_gained", "orchard_spirits", "orchard_idle_taps",
           "stranded_mv")
ARMS = {
    "orchard": {},
    "orchard-naive": {"orchard_idle_tap": False},
    "noop": {},
}


def legs(label):
    staged, cmd = build_pending("karlov")
    basic = basic_for(staged, karlov_v2.FORBIDDEN_ORCHARD)
    if label == "noop":
        return staged, basic.name, dataclasses.replace(basic), cmd
    return staged, basic.name, karlov_v2.FORBIDDEN_ORCHARD, cmd


def job(args):
    label, turns, n = args
    base, out, card, cmd = legs(label)
    t0 = time.time()
    ra, rb, _cfg = run_ab(base, cmd, out, card, n=n, turns=turns,
                          cfg=ARMS[label], sim=REGISTRY["karlov"].sim)
    rows = analyse(ra, rb, metrics=METRICS)
    return (label, turns, out, time.time() - t0,
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in rows])


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    jobs = [(lab, t, n) for lab in ARMS for t in HORIZONS]
    print(f"karlov x Forbidden Orchard. N={n:,} paired, same seeds both legs, "
          f"base = build_pending('karlov').\n")
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for label, turns, out, secs, rows in pool.imap_unordered(job, jobs):
            done[(label, turns)] = rows
            print(f"  {label}  T{turns}  (-{out} +Forbidden Orchard, {secs:.0f}s)")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()

    print("=" * 78)
    print("SUMMARY: win rate, paired")
    print("=" * 78)
    print(f"{'arm':<20}{'win T10':>20}{'win T20':>20}")
    for lab in ARMS:
        cells = []
        for t in HORIZONS:
            _m, diff, lo, hi, sig = done[(lab, t)][0]
            cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}"
                         f"{' *' if sig else '  '}")
        print(f"{lab:<20}{cells[0]:>20}{cells[1]:>20}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
