#!/usr/bin/env python3
"""Queued item 21: the azusa backlog, converted into a decision.

Thirteen azusa cards sat in `MEASURED` with no cut named. A candidate row is
value over a blank in a FREED slot, and §0c says a common baseline cannot
rank two cards against each other -- so the two cards at the top of that
backlog, Traveling Chocobo (+0.0291 +-0.0040) and Nissa, Resurgent Animist
(+0.0285 +-0.0041), were a SET and not a ranking, 0.0006 apart. The cut is
Yavimaya Elder (+0.0023 +-0.0023, inside its own bar), MODEL-EVALUATED, the
owner's choice.

THREE RUNS, because two of them answer different questions and the third
answers the one §0c says a shared baseline cannot:

  1. -Yavimaya Elder +Traveling Chocobo        does the swap beat the list?
  2. -Yavimaya Elder +Nissa, Resurgent Animist the same question, other card
  3. Chocobo -> Nissa IN Yavimaya's slot       which of the two is better?

Run 3 is the one that ranks them: both legs are the same 99 other cards on
the same seeds, so the difference is PAIRED and the §0c objection (two swaps
against a common baseline have overlapping CIs) does not apply. It is the
same measurement that settled Caldera Pyremaw over Galvanoth.

THE BASELINE IS THE STAGED LIST (`build_pending("azusa")`), which applies
`-Perilous Forays +Ka-Zar of the Savage Land`. That is the list azusa's
committed table is measured on, so it is the list a swap's number has to be
a difference on.

    python -m diagnostics.run_azusa_head2head > results/azusa_head2head.txt

`results/azusa_head2head.txt` is the post-§0z37 run (2026-09-21);
`results/azusa_head2head_0z41.txt` is the same three runs after Horn of
Greed stopped being doubled and decking became a loss (2026-09-22).
"""
import sys
import time

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import build_pending
from edhmc.experiment import run_ab, analyse, _swap_many
from edhmc.decks.azusa_v1 import TRAVELING_CHOCOBO, NISSA_RESURGENT_ANIMIST

N = 15000
CUT = "Yavimaya Elder"
METRICS = ("won", "damage", "landfall_triggers", "lands_played",
           "cards_drawn", "final_life", "stranded_mv")


def report(label, base, cmd, out_name, in_card, sim, n):
    for turns in (10, 20):
        t0 = time.time()
        ra, rb, _cfg = run_ab(base, cmd, out_name, in_card, n=n, turns=turns,
                              sim=sim)
        print(f"\n  {label}  T{turns}  ({time.time() - t0:.0f}s)   "
              f"A-leg won {np.mean([r['won'] for r in ra]):.4f}")
        for r in analyse(ra, rb, metrics=METRICS):
            star = " *" if r.significant else "  "
            print(f"    {r.metric:<20}{r.mean_diff:>+9.4f}"
                  f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
        sys.stdout.flush()


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    sim = REGISTRY["azusa"].sim
    staged, cmd = build_pending("azusa")
    # SINCE 2026-09-22 THE CHOCOBO IS STAGED into this very slot, so the list
    # a head-to-head has to be run on is the staged list WITH THE SWAP
    # UNDONE. `_swap_many` swaps in place, so putting Yavimaya Elder back in
    # the Chocobo's slot reproduces the pre-staging list exactly -- the same
    # 99 in the same order, which is what keeps the seeds comparable with
    # every earlier run of this file.
    if any(c.name == TRAVELING_CHOCOBO.name for c in staged):
        from edhmc.decks import azusa_v1
        elder = next(c for c in azusa_v1.build()[0] if c.name == CUT)
        staged = _swap_many(staged, [TRAVELING_CHOCOBO.name], [elder])
    assert any(c.name == CUT for c in staged), f"{CUT} is not in the staged list"
    print(f"azusa head-to-head against {CUT}. N={n:,} paired, same seeds both "
          f"legs, base = build_pending('azusa') (Ka-Zar swap applied).")

    print(f"\n=== 1. the real swap -{CUT} +{TRAVELING_CHOCOBO.name}")
    report("chocobo", staged, cmd, CUT, TRAVELING_CHOCOBO, sim, n)

    print(f"\n=== 2. the real swap -{CUT} +{NISSA_RESURGENT_ANIMIST.name}")
    report("nissa", staged, cmd, CUT, NISSA_RESURGENT_ANIMIST, sim, n)

    # 3. The ranking §0c says a shared baseline cannot give. A leg plays
    # Chocobo in Yavimaya's slot, B leg plays Nissa there; everything else is
    # identical on the same seeds, so a significant difference RANKS them.
    print(f"\n=== 3. {TRAVELING_CHOCOBO.name} -> {NISSA_RESURGENT_ANIMIST.name} "
          f"in {CUT}'s slot (positive = Nissa is the better of the two)")
    with_chocobo = _swap_many(staged, [CUT], [TRAVELING_CHOCOBO])
    report("nissa-minus-chocobo", with_chocobo, cmd, TRAVELING_CHOCOBO.name,
           NISSA_RESURGENT_ANIMIST, sim, n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
