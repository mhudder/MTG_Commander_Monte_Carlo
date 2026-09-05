#!/usr/bin/env python3
"""Fit the pod model so that COMBAT, not the clock, does most of the killing.

THE PROBLEM
-----------
`incidental_damage` and `resolve_clocks` are two independent kill mechanisms.
The clock is a deus ex machina: it eliminates a player on a threat-weighted
coin flip, regardless of the board. Combat is a smooth trickle calibrated so
low that, measured 2026-09-04, it accounts for 0% of losses in all three decks
— disable the clocks entirely and it still only kills you in 0.4-2.9% of games
by turn 30.

That makes your life total inert, which makes lifegain, lifelink and any card
with a life cost unevaluable.

WHY YOU CANNOT JUST TURN THE KNOB UP
------------------------------------
Raising `incidental_rate` ADDS lethality rather than moving it. At rate 2.0
Rendmaw's loss rate goes 0.691 -> 0.965 and its win rate collapses 0.307 ->
0.035. So the fit has TWO free parameters against TWO targets:

    incidental_rate   how hard the pod hits you
    clock_shift       how much later the deus ex machina arrives

and the targets are

    1. total lethality UNCHANGED  — each deck's win rate stays where the pod
       was already calibrated, so nothing else in the project moves
    2. the loss-route split becomes realistic — most losses via combat

Usage:
    python fit_pod.py            # coarse sweep, then verify the pick
    python fit_pod.py verify 0.9 4
"""
import sys

import numpy as np

from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG
from edhmc.engine import simulate as rendmaw_sim
from edhmc.lorehold import simulate as lorehold_sim
from edhmc.karlov import simulate as karlov_sim

DECKS = (("rendmaw", rendmaw_sim), ("lorehold", lorehold_sim),
         ("karlov", karlov_sim))

# Measured on the current pod at turns=20 — this is the calibration the whole
# project already rests on, so the fit must not move it.
BASELINE_WIN = {"rendmaw": 0.307, "lorehold": 0.233, "karlov": 0.443}

# Target share of LOSSES that should come from being reduced to 0 life rather
# than from an opponent's clock. See the note in fit_pod's output: this is a
# judgement call, stated out loud, and it is the one number here that is not
# measured from anything.
TARGET_LIFE_SHARE = 0.65


def evaluate(rate, shift, n=700, turns=20, seed0=95000):
    out = {}
    for name, sim in DECKS:
        deck, cmd = build_pending(name)
        cfg = dict(DEFAULT_CFG, turns=turns, incidental_rate=rate,
                   clock_shift=shift, combat_targeting="open")
        rows = [sim(deck, cmd, cfg, seed0 + j) for j in range(n)]
        lost = [r for r in rows if r["lost"]]
        out[name] = {
            "win": float(np.mean([r["won"] for r in rows])),
            "loss": len(lost) / len(rows),
            "life_share": (sum(1 for r in lost if r["loss_route"] == 1)
                           / max(1, len(lost))),
            "turns": float(np.mean([r["turns_played"] for r in rows])),
            "final_life": float(np.mean([r["final_life"] for r in rows])),
        }
    return out


def score(res):
    """Squared error against the two targets, win rate weighted heavily."""
    win_err = sum((res[d]["win"] - BASELINE_WIN[d]) ** 2 for d in BASELINE_WIN)
    share_err = sum((res[d]["life_share"] - TARGET_LIFE_SHARE) ** 2
                    for d in BASELINE_WIN)
    return 3.0 * win_err + share_err


def sweep():
    rates = (0.6, 0.8, 1.0, 1.2, 1.5)
    shifts = (0, 2, 4, 6, 8)
    print("Fitting (incidental_rate, clock_shift) with combat_targeting='open'")
    print(f"targets: win rate {BASELINE_WIN}, "
          f"life share of losses {TARGET_LIFE_SHARE}\n")
    print(f"{'rate':>5}{'shift':>6}  "
          f"{'win r/l/k':>22}  {'life-share r/l/k':>22}  {'score':>7}")
    best = None
    for rate in rates:
        for shift in shifts:
            res = evaluate(rate, shift)
            sc = score(res)
            wins = "/".join(f"{res[d]['win']:.3f}" for d, _ in DECKS)
            shares = "/".join(f"{res[d]['life_share']:.2f}" for d, _ in DECKS)
            flag = ""
            if best is None or sc < best[0]:
                best, flag = (sc, rate, shift, res), "  <-"
            print(f"{rate:>5.2f}{shift:>6}  {wins:>22}  {shares:>22}"
                  f"  {sc:>7.4f}{flag}")
            sys.stdout.flush()
    return best


def verify(rate, shift, n=4000):
    print(f"\nVERIFY  incidental_rate={rate}  clock_shift={shift}  "
          f"combat_targeting='open'   (n={n:,} per deck)")
    new = evaluate(rate, shift, n=n)
    print(f"  {'deck':<10}{'win (was)':>18}{'loss':>8}"
          f"{'life-share':>12}{'turns':>8}{'final life':>12}")
    for name, _ in DECKS:
        r = new[name]
        print(f"  {name:<10}{r['win']:>9.3f} ({BASELINE_WIN[name]:.3f})"
              f"{r['loss']:>8.3f}{r['life_share']:>12.2f}"
              f"{r['turns']:>8.1f}{r['final_life']:>12.1f}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["verify"]:
        verify(float(sys.argv[2]), int(sys.argv[3]))
    else:
        sc, rate, shift, _ = sweep()
        print(f"\nbest: rate={rate}, shift={shift} (score {sc:.4f})")
        verify(rate, shift)
