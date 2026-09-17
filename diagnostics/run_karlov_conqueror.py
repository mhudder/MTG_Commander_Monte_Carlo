#!/usr/bin/env python3
"""Re-measure Bloodthirsty Conqueror with the flying it always had (§0z29).

The card was added to `decks/karlov_v2.py` on 2026-09-16 and measured the
same day -- as a GROUND creature. `Card.flying` is set from the generated
`decks/_evasion.py`, which nobody regenerated when the card was added, so the
§0z26 candidate row (+0.0328), the §0z27 head-to-head (+0.0257 / +0.0247) and
every row of the regenerated karlov table were measured with a 5/5 flier
walking into blockers. The ledger's own rationale calls it "a 5/5 FLYING
DEATHTOUCH body" in the same breath. This is §0q in its purest form: a
generated name set is only as current as the last time someone generated it.

Two measurements, both at the table's N so they are comparable to it:

  1. value over a blank in the Soulmender slot (what `candidates.py karlov2`
     printed for §0z26), at T10 and T20;
  2. the real swap -Soulmender +Bloodthirsty Conqueror against the staged
     list WITHOUT that swap (Citadel in, Conqueror out), same seeds both legs,
     at T10 and T20 -- the number the staging rests on.

    python -m diagnostics.run_karlov_conqueror > results/karlov_conqueror.txt
"""
import sys
import time

import numpy as np

from edhmc.karlov import simulate as karlov_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, run_ab, analyse, _swap_many, repl_priority
from edhmc.decks.karlov_v2 import BLOODTHIRSTY_CONQUEROR, build
from tools.candidates import blank_like

N = 15000
METRICS = ("won", "damage", "lifegain_triggers", "final_life",
           "opponents_killed", "cards_drawn", "stranded_mv")


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    # The premise, asserted rather than assumed: if this fails, _evasion.py
    # has not been regenerated and every number below would repeat the bug.
    assert BLOODTHIRSTY_CONQUEROR.flying, (
        "Bloodthirsty Conqueror is not tagged flying -- run "
        "`python -m tools.tag_flying --write` first")
    print(f"Bloodthirsty Conqueror: flying={BLOODTHIRSTY_CONQUEROR.flying}, "
          f"N={n:,} paired, same seeds both legs")

    # The A leg for both measurements: the staged list with THIS swap undone
    # (Citadel in, Soulmender back, Conqueror out). `candidates.add_value`
    # refuses a card that is already staged -- correctly, §0o -- so its
    # blank comparison is replicated here on that list, same seeds it uses.
    staged, cmd = build_pending("karlov")
    soulmender = next(c for c in build()[0] if c.name == "Soulmender")
    base = _swap_many(staged, ["Bloodthirsty Conqueror"], [soulmender])

    # 1. value over a blank, Soulmender slot (the §0z26 candidate row)
    print("\n=== value over a blank of the same cost, Soulmender slot "
          "(candidates.add_value replicated on the pre-swap staged list)")
    cand = BLOODTHIRSTY_CONQUEROR
    a = _swap_many(base, ["Soulmender"], [blank_like(cand, repl_priority(base), base)])
    b = _swap_many(base, ["Soulmender"], [cand])
    for turns in (10, 20):
        t0 = time.time()
        cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({cand.name}))
        ra = [karlov_sim(a, cmd, cfg, 80000 + j) for j in range(n)]
        rb = [karlov_sim(b, cmd, cfg, 80000 + j) for j in range(n)]
        out = {}
        for m in ("damage", "won", "lifegain_triggers"):
            x = (np.array([r[m] for r in rb], float)
                 - np.array([r[m] for r in ra], float))
            out[m] = (x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)))
        deploy = np.mean([r["cast_test_card"] for r in rb])
        print(f"  T{turns}: damage {out['damage'][0]:+.2f}+-{out['damage'][1]:.2f}"
              f"   win rate {out['won'][0]:+.4f}+-{out['won'][1]:.4f}"
              f"   lifegain_triggers {out['lifegain_triggers'][0]:+.2f}"
              f"+-{out['lifegain_triggers'][1]:.2f}"
              f"   P(deploy) {deploy:.3f}   ({time.time() - t0:.0f}s)")
        sys.stdout.flush()

    # 2. the real swap
    print("\n=== real swap -Soulmender +Bloodthirsty Conqueror, staged list "
          "(Citadel in) with this swap undone as the A leg")
    for turns in (10, 20):
        t0 = time.time()
        ra, rb, cfg = run_ab(base, cmd, "Soulmender", BLOODTHIRSTY_CONQUEROR,
                             n=n, turns=turns, sim=karlov_sim)
        print(f"\n  T{turns}  ({time.time() - t0:.0f}s)")
        for r in analyse(ra, rb, metrics=METRICS):
            star = " *" if r.significant else "  "
            print(f"    {r.metric:<20}{r.mean_diff:>+9.4f}"
                  f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
