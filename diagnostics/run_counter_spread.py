#!/usr/bin/env python3
"""Focus or spread: where should a "+1/+1 counter on target creature" go?
(§0z101, the owner's question, 2026-10-03)

    python -m diagnostics.run_counter_spread 15000 > results/counter_spread.txt

`azusa.counter_target` places Bristly Bill's landfall counter and Dancing
from Dark to Dawn's cast-trigger counters. Two policies, both with Mossborn
Hydra first:

  focus   an evasive creature, else the highest power
  spread  the smallest creature, ties to fewer counters

THE OWNER'S HYPOTHESIS: one huge creature does little without evasion, and
this model chump-blocks the biggest attackers (§0v), so spreading should win.

THREE LEGS ON ONE SEED per game: A is the staged list with Wayward Swordtooth,
B_focus and B_spread both cut it for the card. So each swap is the real swap
against the owner's cut, and spread-minus-focus is PAIRED -- the two B legs
differ only in the policy, which is what makes a policy difference this size
measurable at all. T10 is read off the T20 game (§0z93). Seeds 5000.., the
same as diagnostics/run_azusa_batch6.py, so the focus arm reproduces its row.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.registry import DECKS as REGISTRY

CUT = "Wayward Swordtooth"
CARDS = ("Bristly Bill, Spine Sower", "Dancing from Dark to Dawn")
POLICIES = ("focus", "spread")
CHUNKS = 4
SEED0 = 5000
KEYS = ("damage", "bristly_counters", "bristly_activations",
        "dancing_counters")


def job(a):
    add, lo, hi = a
    base, cmd = build_pending("azusa")
    card = CATALOG["azusa"][1][add]
    deck_b = _swap_many(base, [CUT], [card])
    sim = REGISTRY["azusa"].sim
    out = []
    for i in range(lo, hi):
        seed = SEED0 + i
        row = []
        for deck, pol in ((base, "focus"), (deck_b, "focus"),
                          (deck_b, "spread")):
            cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                       counter_target=pol,
                       watch=frozenset({CUT, add}))
            r = sim(list(deck), cmd, cfg, seed)
            row.append((float(r["at_rounds"][10]["won"]), float(r["won"]))
                       + tuple(float(r[k]) for k in KEYS))
        out.append(row)
    return out


def ci(d):
    d = np.asarray(d, dtype=float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def cell(d):
    m, h = ci(d)
    return f"{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ' '}"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    tasks = [(c, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for c in CARDS for k in range(CHUNKS)]
    with Pool(4) as p:
        res = p.map(job, tasks, chunksize=1)
    rows = {}
    for (c, _lo, _hi), r in zip(tasks, res):
        rows.setdefault(c, []).extend(r)
    arr = {c: np.array(v) for c, v in rows.items()}   # [game, leg, field]

    print(f"counter_target: focus vs spread. N={n:,} games per card, three "
          f"legs per seed (A = staged list with {CUT}; B = the card in its "
          f"slot under each policy), seeds {SEED0}.., T10 read off the T20 "
          "game. * = the 95% CI excludes zero.\n")
    print(f"  {'card':<28}{'horizon':>8}{'swap, focus':>18}{'swap, spread':>18}"
          f"{'spread - focus':>18}")
    for c in CARDS:
        a = arr[c]
        for h, idx in (("T10", 0), ("T20", 1)):
            print(f"  {c:<28}{h:>8}"
                  f"{cell(a[:, 1, idx] - a[:, 0, idx]):>18}"
                  f"{cell(a[:, 2, idx] - a[:, 0, idx]):>18}"
                  f"{cell(a[:, 2, idx] - a[:, 1, idx]):>18}")
    print("\nmechanism, T20, per game (B legs): damage is bounded; "
          "counters as the counters record them")
    for c in CARDS:
        a = arr[c]
        for li, pol in ((1, "focus"), (2, "spread")):
            parts = [f"{k} {a[:, li, 2 + j].mean():.2f}"
                     for j, k in enumerate(KEYS)]
            print(f"  {c:<28}{pol:>8}  " + "  ".join(parts))
        m, h = ci(a[:, 2, 2] - a[:, 1, 2])
        print(f"  {'':<28}{'':>8}  damage spread - focus {m:+.2f} ±{h:.2f}")


if __name__ == "__main__":
    main()
