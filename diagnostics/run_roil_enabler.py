#!/usr/bin/env python3
"""What did Zendikar's Roil's missing LAND_ENABLERS entry cost? (§0z101)

    python -m diagnostics.run_roil_enabler 15000 > results/roil_enabler.txt

Zendikar's Roil was never in azusa.LAND_ENABLERS from its 2026-09-16
implementation until 2026-10-03, so it was cast AFTER the turn's land drops
and its +0.0133 row (§0z25) was a floor. Each seed is played twice with the
Roil in the Sylvan Library slot (candidates.py's azusa3-6 slot): once with it
in LAND_ENABLERS (today's engine) and once with it removed (the old one), so
the difference is the fix alone, paired. Seeds 5000.., T10 off the T20 game.
"""
import sys
from multiprocessing import Pool
import numpy as np
import edhmc.azusa as AZ
from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.pending import build_pending, DECKS as CAT
from edhmc.registry import DECKS

def job(a):
    lo, hi = a
    base, cmd = build_pending("azusa")
    deck = _swap_many(base, ["Sylvan Library"], [CAT["azusa"][1]["Zendikar's Roil"]])
    sim = DECKS["azusa"].sim
    full = AZ.LAND_ENABLERS
    out = []
    for s in range(5000 + lo, 5000 + hi):
        cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,))
        AZ.LAND_ENABLERS = full
        r1 = sim(list(deck), cmd, cfg, s)
        AZ.LAND_ENABLERS = full - {"Zendikar's Roil"}
        r0 = sim(list(deck), cmd, dict(cfg), s)
        AZ.LAND_ENABLERS = full
        out.append((r1["at_rounds"][10]["won"] - r0["at_rounds"][10]["won"],
                     r1["won"] - r0["won"], r1["damage"] - r0["damage"]))
    return out

n = int(sys.argv[1])
with Pool(4) as p:
    rows = sum(p.map(job, [(k*n//4, (k+1)*n//4) for k in range(4)]), [])
a = np.array(rows, dtype=float)
for i, k in enumerate(("won T10", "won T20", "damage T20")):
    m = a[:, i].mean(); h = 1.96 * a[:, i].std(ddof=1) / np.sqrt(len(a))
    print(f"  Roil before the drops minus after: {k:11} {m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ''}")
