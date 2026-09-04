#!/usr/bin/env python3
"""
Cross-deck comparison and Lorehold bottleneck diagnostics.

READ THIS BEFORE READING THE NUMBERS
------------------------------------
The opponents in this model have no win condition. They remove, counter, wipe,
and block, but they never advance a clock of their own. So the figure reported
here is NOT a win rate in a four-player race — it is:

    P(you can deal 120 damage to the table by turn N)

That makes it a fair measure of how fast a deck closes against resistance, and
an unfair measure of a control deck that intends to win late or by alternate
means. Rendmaw is built to race; Lorehold is built to hold the table down with
eight board wipes. The metric is shaped like Rendmaw's plan.

Usage:  python compare_decks.py [n_games]
"""
import sys

import numpy as np

from edhmc.decks.rendmaw_v11 import build as rendmaw_build
from edhmc.decks.lorehold_v16 import build as lorehold_build, C
from edhmc.engine import simulate as rendmaw_sim
from edhmc.lorehold import simulate as lorehold_sim
from edhmc.experiment import DEFAULT_CFG

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4000

rd, rc = rendmaw_build()
ld, lc = lorehold_build()


def run(deck, cmd, sim, **override):
    cfg = dict(DEFAULT_CFG, turns=14, watch=frozenset(), **override)
    rows = [sim(deck, cmd, cfg, s) for s in range(N)]
    return (np.mean([1.0 if r["damage"] >= 120 else 0.0 for r in rows]),
            np.mean([r["damage"] for r in rows]))


print("P(120 damage) and mean damage, by horizon (mixed pod)")
print(f"{'turns':>6}{'Rendmaw':>12}{'Lorehold':>12}{'R dmg':>10}{'L dmg':>10}")
for t in (10, 12, 14, 16):
    pr, dr = run(rd, rc, rendmaw_sim, turns=t)
    pl, dl = run(ld, lc, lorehold_sim, turns=t)
    print(f"{t:>6}{pr:>12.3f}{pl:>12.3f}{dr:>10.1f}{dl:>10.1f}")

print("\nIs the gap the pod, or the decks? (14 turns)")
print(f"{'pod':<22}{'Rendmaw':>10}{'Lorehold':>11}")
for label, ov in [("no interaction", {"opponents": False, "derived_blocking": False}),
                  ("all bracket 2", {"pod_brackets": (2, 2, 2)}),
                  ("mixed 2/3/4", {"pod_brackets": (2, 3, 4)}),
                  ("all bracket 4", {"pod_brackets": (4, 4, 4)})]:
    pr, _ = run(rd, rc, rendmaw_sim, **ov)
    pl, _ = run(ld, lc, lorehold_sim, **ov)
    print(f"{label:<22}{pr:>10.3f}{pl:>11.3f}")

print("\nLorehold bottlenecks — sizing the levers (14 turns, mixed pod)")
print(f"{'scenario':<42}{'P(120)':>9}{'dmg':>8}")
base = run(ld, lc, lorehold_sim)
print(f"{'baseline v15':<42}{base[0]:>9.3f}{base[1]:>8.1f}")

# Upper bound on fixing commander access: make it free to cast.
# Not a real card — a lever measurement.
free_cmd = C("Lorehold, the Historian", "Creature", {}, 5, 5,
             priority=10, threat=9.0)
r = run(ld, free_cmd, lorehold_sim)
print(f"{'  commander costs {0} (upper bound)':<42}{r[0]:>9.3f}{r[1]:>8.1f}")

# Trade three basics for three cheap cantrips.
cantrips = [C("Cantrip A", "Instant", {"R": 1}, priority=3, script="draw2"),
            C("Cantrip B", "Instant", {"W": 1}, priority=3, script="draw2"),
            C("Cantrip C", "Sorcery", {"R": 1}, priority=3, script="draw2")]
d2, k = list(ld), 0
for i, x in enumerate(d2):
    if x.name in ("Mountain", "Plains") and k < 3:
        d2[i] = cantrips[k]
        k += 1
r = run(d2, lc, lorehold_sim)
print(f"{'  31 lands + 3 cantrips':<42}{r[0]:>9.3f}{r[1]:>8.1f}")
