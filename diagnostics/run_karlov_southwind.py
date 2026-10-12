#!/usr/bin/env python3
"""South Wind Avatar against Daxos, Blessed by the Sun -- the real swap (§0z128).

THE CANDIDATE ROW IS +0.0205 +-0.0028 at T20 (results/candidates_karlov4.txt),
value over a blank in Swiftfoot Boots' slot. A candidate row is not a swap
(§0e): this is the swap the owner named, `-Daxos +South Wind Avatar`, paired on
the same seeds against the live staged list.

THE CUT IS MODEL-EVALUATED. Daxos's leave-one-out row is +0.0013 +-0.0021 at
T20, significant on damage only (+0.21 +-0.10). Both of its clauses are
modelled -- toughness from devotion (§0z52) and "whenever another creature you
control enters or dies, you gain 1 life" -- so the row is evidence (§0z31).

NOTE THE OVERLAP, which is why the swap is not the candidate row minus
Daxos's: both cards pay off your creatures dying, and the Avatar's lifegain
trigger fires on Daxos's lifegain events. The swap prices all of that at once.

    python -m diagnostics.run_karlov_southwind        > results/karlov_southwind.txt
    python -m diagnostics.run_karlov_southwind --n=40 # smoke test
"""
import sys
import time
from multiprocessing import Pool

from edhmc.experiment import analyse, run_ab
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.registry import DECKS as REGISTRY

N = 15000
CUT = "Daxos, Blessed by the Sun"
ADD = "South Wind Avatar"
HORIZONS = (10, 20)
METRICS = ("won", "damage", "drain_damage", "combat_damage",
           "lifegain_triggers", "life_gained", "karlov_counters",
           "southwind_drains", "southwind_death_gains", "drain_loop_wins",
           "final_life", "stranded_mv")


def job(args):
    turns, n = args
    _mod, catalog = CATALOG["karlov"]
    staged, cmd = build_pending("karlov")
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    t0 = time.time()
    ra, rb, _cfg = run_ab(staged, cmd, CUT, catalog[ADD], n=n, turns=turns,
                          sim=REGISTRY["karlov"].sim)
    rows = analyse(ra, rb, metrics=METRICS)
    base_won = sum(r["won"] for r in ra) / len(ra)
    return (turns, time.time() - t0, base_won,
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in rows])


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    print(f"karlov: -{CUT} +{ADD}. N={n:,} paired, same seeds both legs, "
          f"base = build_pending('karlov').\n")
    sys.stdout.flush()
    done = {}
    with Pool(2) as pool:
        for turns, secs, base_won, rows in pool.imap_unordered(
                job, [(t, n) for t in HORIZONS]):
            done[turns] = rows
            print(f"  T{turns}  ({secs:.0f}s)   A-leg won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<22}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()
    print("=" * 78)
    print(f"SUMMARY: -{CUT} +{ADD}, win rate, paired")
    for t in HORIZONS:
        _m, diff, lo, hi, sig = done[t][0]
        print(f"  T{t}: {diff:+.4f} +-{(hi - lo) / 2:.4f}"
              f"{'  significant' if sig else '  inside its bar'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
