#!/usr/bin/env python3
"""Re-measure `-Plains +Anointed Procession` on the post-§0z30 tivit baseline.

The swap was staged on 2026-09-16 (§0z27) on evidence measured before the
pod-phase order was unified (§0z30, 2026-09-17), and that change moved
tivit's baseline more than any other deck's: +0.0647 win rate at T20, a
fifth of its games ending differently. A swap's number is a difference on
a baseline, and this baseline is not the one the number was measured on.

Two measurements, both at the table's N so they are comparable to it:

  1. value over a blank in the Plains slot (the §0z26 candidate row);
  2. the real swap -Plains +Anointed Procession against the module list
     (tivit has no other staged change), same seeds both legs.

    python -m diagnostics.run_tivit_procession > results/tivit_procession.txt
"""
import sys
import time

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, run_ab, analyse, _swap_many, repl_priority
from edhmc.decks.tivit_v1 import ANOINTED_PROCESSION
from tools.candidates import blank_like

N = 15000
METRICS = ("won", "damage", "artifacts_made", "treasures_made", "final_life",
           "opponents_killed", "cards_drawn", "stranded_mv")


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    sim = REGISTRY["tivit"].sim
    base, cmd = build_pending("tivit", apply_pending=False)
    cand = ANOINTED_PROCESSION
    print(f"Anointed Procession, post-§0z30 baseline: N={n:,} paired, same "
          f"seeds both legs, base = tivit module list (Plains in)")

    print("\n=== value over a blank of the same cost, Plains slot "
          "(candidates.add_value replicated on the module list)")
    a = _swap_many(base, ["Plains"], [blank_like(cand, repl_priority(base), base)])
    b = _swap_many(base, ["Plains"], [cand])
    for turns in (10, 20):
        t0 = time.time()
        cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({cand.name}))
        ra = [sim(a, cmd, cfg, 80000 + j) for j in range(n)]
        rb = [sim(b, cmd, cfg, 80000 + j) for j in range(n)]
        out = {}
        for m in ("damage", "won", "artifacts_made"):
            x = (np.array([r[m] for r in rb], float)
                 - np.array([r[m] for r in ra], float))
            out[m] = (x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)))
        deploy = np.mean([r["cast_test_card"] for r in rb])
        print(f"  T{turns}: damage {out['damage'][0]:+.2f}+-{out['damage'][1]:.2f}"
              f"   win rate {out['won'][0]:+.4f}+-{out['won'][1]:.4f}"
              f"   artifacts_made {out['artifacts_made'][0]:+.2f}"
              f"+-{out['artifacts_made'][1]:.2f}"
              f"   P(deploy) {deploy:.3f}   ({time.time() - t0:.0f}s)")
        sys.stdout.flush()

    print("\n=== real swap -Plains +Anointed Procession, module list as the A leg")
    for turns in (10, 20):
        t0 = time.time()
        ra, rb, cfg = run_ab(base, cmd, "Plains", cand, n=n, turns=turns, sim=sim)
        print(f"\n  T{turns}  ({time.time() - t0:.0f}s)   baseline won "
              f"{np.mean([r['won'] for r in ra]):.4f}")
        for r in analyse(ra, rb, metrics=METRICS):
            star = " *" if r.significant else "  "
            print(f"    {r.metric:<20}{r.mean_diff:>+9.4f}"
                  f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
