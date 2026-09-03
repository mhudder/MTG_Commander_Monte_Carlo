#!/usr/bin/env python3
"""Harness validation: A/A control + measurement of the CRN variance reduction."""
import numpy as np
from edhmc.decks.rendmaw_v11 import build, MARCH_OF_THE_WORLD_OOZE
from edhmc.experiment import run_ab, analyse

deck, cmd = build()

print("A/A control — identical decks under common random numbers.")
print("Any nonzero difference here means the harness is leaking randomness.")
same = [c for c in deck if c.name == "Skullclamp"][0]
ra, rb, _ = run_ab(deck, cmd, "Skullclamp", same, n=5000)
for r in analyse(ra, rb, metrics=("damage", "cards_drawn", "tokens_made")):
    print("  ", r.line("A", "A"))

print("\n\nLorehold engine — A/A control")
from edhmc.decks.lorehold_v15 import build as lh_build
from edhmc.lorehold import simulate as lh_sim
ld, lc = lh_build()
same = [x for x in ld if x.name == "Verge Rangers"][0]
la, lb, _ = run_ab(ld, lc, "Verge Rangers", same, n=3000,
                   cfg={"turns": 14}, sim=lh_sim)
for r in analyse(la, lb, metrics=("mv_cheated", "miracles_cast", "damage")):
    print("  ", r.line("A", "A"))

print("\nCRN variance reduction on the real comparison:")
ra, rb, _ = run_ab(deck, cmd, "Skullclamp", MARCH_OF_THE_WORLD_OOZE, n=8000)
a = np.array([r["damage"] for r in ra]); b = np.array([r["damage"] for r in rb])
se_p = (b - a).std(ddof=1) / np.sqrt(len(a))
se_i = np.sqrt(a.var(ddof=1) + b.var(ddof=1)) / np.sqrt(len(a))
print(f"  corr(A,B)      = {np.corrcoef(a, b)[0,1]:.4f}")
print(f"  paired SE      = {se_p:.4f}")
print(f"  independent SE = {se_i:.4f}   ({se_i/se_p:.1f}x wider)")
print(f"  CRN is worth ~{(se_i/se_p)**2:.0f}x the number of games.")
