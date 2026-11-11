#!/usr/bin/env python3
"""Queue item 41 (§0z192, finding 4): does a row's size or sign depend on
where the baseline win rate sits?

Since §0z140 the pod's kill timing is re-fitted so the mean T20 win rate over
the active decks equals the previous pod's; the decks now win 0.31-0.62,
mean ~0.47, against 0.25-0.31 at the first calibration. This re-measures a
sample of rows at the fitted pod and at a pod made strong enough to bring the
mean near 0.30, paired by seed, and counts the rows that change sign or leave
their bar. It informs an OWNER DECISION (keep the fit rule, or a fixed
target); it decides nothing.

THE ROWS, per active deck, on the staged list (`build_pending`):
  swap   each STAGED swap: the staged list minus the list with that one swap
         reverted (the cut back in the added card's slot).
  card   the deck's five largest and five smallest MODEL-EVALUATED rows at
         T20 win rate in the committed cache, re-measured here as (list) -
         (list with `ablation.blank_like` in the card's slot, at
         `repl_priority`), which is the table's own row. A cached name no
         longer in the staged list is skipped (tivit's withdrawn Anointed
         Procession).

THE TWO PODS: `threat_clock_shift` at its default (2.3) and at SHIFT_STRONG
(7.5). 7.5 is read off `run_knob_sweep threat_clock_shift 2.3 ...` at N=1,000
a deck, seeds 60000.. (2026-11-11): 6.5 moved the mean T20 win rate by
-0.138, 8 by -0.178, so ~7.5 is the -0.17 that takes ~0.47 to ~0.30. The kill
turn is floored at 4 (`opponents.roll_threat_routes`), which is why the shift
needed is that large and why T10 barely moves: most of the strong pod's
extra kills land after round 10.

Seeds 5000.. (the tables' block), N=15,000, T20 with T10 off the same game.

THE COUNTS, written before the run (§0z11):
  flip     the row's T20 win rate is significant at BOTH pods with opposite
           signs.
  leaves   significant at one pod and inside its bar at the other.
  ratio    strong / default, for rows significant at the default pod: the
           median says whether rows scale with the room a baseline leaves.

    python -m diagnostics.run_baseline_dependence > results/baseline_dependence.txt
    python -m diagnostics.run_baseline_dependence --n=300 --decks=karlov   # smoke

BLIND TO (§0z15): one knob moves the baseline. A pod made stronger by its
clock is not the same as one made stronger by its removal or its life
damage; `incidental_rate` and the clock are the two big levers (§0z192's
knobs), and only the clock is moved here.
"""
from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 1250
SHIFT_DEFAULT, SHIFT_STRONG = 2.3, 7.5
TOP, SHORT = 20, 10
K = 5


def reverted(deck_name, i):
    """The staged list with staged change `i` undone, slots kept."""
    from edhmc.experiment import _swap_many
    from edhmc.pending import DECKS as CAT, pending_for, validate
    module, catalog = CAT[deck_name]
    deck, cmd = module.build()
    ch = [c for j, c in enumerate(pending_for(deck_name)) if j != i]
    if ch:
        deck = _swap_many(deck, [c.remove for c in ch],
                          [catalog[c.add] for c in ch])
    validate(deck, cmd)
    return deck, cmd


def variant(deck_name, row):
    """(list A, list B, commander): the row is A - B."""
    from edhmc.experiment import repl_priority
    from edhmc.pending import build_pending
    import tools.ablation as AB
    staged, cmd = build_pending(deck_name)
    kind, arg = row
    if kind == "base":
        return staged, staged, cmd
    if kind == "swap":
        return staged, reverted(deck_name, arg)[0], cmd
    idx = next(i for i, c in enumerate(staged) if c.name == arg)
    b = list(staged)
    b[idx] = AB.blank_like(staged[idx], repl_priority(staged))
    return staged, b, cmd


def rows_for(deck_name):
    import tools.ablation as AB
    from edhmc.pending import build_pending, pending_for
    staged, _ = build_pending(deck_name)
    names = {c.name for c in staged if not c.is_land}
    out = [(("swap", i), f"swap -{c.remove} +{c.add}")
           for i, c in enumerate(pending_for(deck_name))]
    run = AB.Run(deck_name, 15000, (10, 20))
    with open(run.cache) as fh:
        res = json.load(fh)
    ev = sorted((v["20"]["won"][0], n) for n, v in res.items()
                if n in run.scripted and n in names and "20" in v)
    picks = ev[-K:][::-1] + ev[:K]
    seen = set()
    for w, n in picks:
        if n not in seen:
            seen.add(n)
            out.append((("card", n), f"{n} (cached {w:+.4f})"))
    return out


def job(args):
    deck_name, row, leg, shift, lo, n = args
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.registry import DECKS
    a, b, cmd = variant(deck_name, row)
    lst = a if leg == "A" else b
    cfg = dict(DEFAULT_CFG, turns=TOP, watch=frozenset(),
               snapshot_rounds=(SHORT,), threat_clock_shift=shift)
    sim = DECKS[deck_name].sim
    won = np.zeros((2, n), np.int8)
    for i in range(n):
        r = sim(lst, cmd, dict(cfg), SEED0 + lo + i)
        won[0, i] = r["won"]
        won[1, i] = r["at_rounds"][SHORT]["won"]
    return args, won


def diff(a, b):
    d = (a - b).astype(float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    from edhmc.registry import ACTIVE
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if "=" in a)
    n = int(opt.get("n", 15000))
    decks = opt["decks"].split(",") if "decks" in opt else list(ACTIVE)
    plan = {d: rows_for(d) for d in decks}
    jobs = []
    for d, rows in plan.items():
        for shift in (SHIFT_DEFAULT, SHIFT_STRONG):
            legs = [(("base", None), "A")] + [(r, "B") for r, _ in rows]
            for row, leg in legs:
                jobs += [(d, row, leg, shift, lo, min(CHUNK, n - lo))
                         for lo in range(0, n, CHUNK)]
    print(f"baseline dependence: N={n:,} paired, seeds {SEED0}.., T{TOP} with "
          f"T{SHORT} off the same game, threat_clock_shift {SHIFT_DEFAULT} "
          f"against {SHIFT_STRONG}; staged lists. A row is A - B.\n")
    print(f"  {len(jobs)} jobs, {sum(j[5] for j in jobs):,} games",
          file=sys.stderr)
    got = {}
    with Pool() as pool:
        for k, (args, won) in enumerate(pool.imap_unordered(job, jobs), 1):
            d, row, leg, shift, lo, _n = args
            got[(d, row, leg, shift, lo)] = won
            if k % 50 == 0:
                print(f"  {k}/{len(jobs)}", file=sys.stderr)

    def cat(d, row, leg, shift):
        los = sorted(lo for (dd, r, lg, s, lo) in got
                     if (dd, r, lg, s) == (d, row, leg, shift))
        return np.concatenate([got[(d, row, leg, shift, lo)] for lo in los],
                              axis=1)

    flips = leaves = total = 0
    ratios = []
    for d, rows in plan.items():
        bases = {s: cat(d, ("base", None), "A", s)
                 for s in (SHIFT_DEFAULT, SHIFT_STRONG)}
        print(f"== {d}   base won T20 {bases[SHIFT_DEFAULT][0].mean():.4f} "
              f"(shift {SHIFT_DEFAULT}) / {bases[SHIFT_STRONG][0].mean():.4f} "
              f"(shift {SHIFT_STRONG})")
        for row, label in rows:
            cells, sig = [], {}
            for s in (SHIFT_DEFAULT, SHIFT_STRONG):
                b = cat(d, row, "B", s)
                m20, h20 = diff(bases[s][0], b[0])
                m10, h10 = diff(bases[s][1], b[1])
                sig[s] = (m20, abs(m20) > h20)
                cells.append(f"T10 {m10:+.4f}+-{h10:.4f} T20 {m20:+.4f}+-"
                             f"{h20:.4f}{'*' if abs(m20) > h20 else ' '}")
            (m0, s0), (m1, s1) = sig[SHIFT_DEFAULT], sig[SHIFT_STRONG]
            tag = ""
            if s0 and s1 and np.sign(m0) != np.sign(m1):
                tag, flips = "FLIP", flips + 1
            elif s0 != s1:
                tag, leaves = "LEAVES", leaves + 1
            if s0:
                ratios.append(m1 / m0)
            total += 1
            print(f"  {label:<52} | {cells[0]} | {cells[1]} {tag}")
        print()
    print(f"{total} rows: {flips} FLIP (significant at both pods, opposite "
          f"signs), {leaves} LEAVES (significant at one pod only).")
    if ratios:
        print(f"strong/default T20 ratio over the {len(ratios)} rows "
              f"significant at the default pod: median {np.median(ratios):.2f}"
              f", quartiles {np.percentile(ratios, 25):.2f} / "
              f"{np.percentile(ratios, 75):.2f}")


if __name__ == "__main__":
    main()
