#!/usr/bin/env python3
"""Harness validation: A/A control + measurement of the CRN variance reduction."""
import numpy as np
from edhmc.decks.rendmaw_v12 import build, SKULLCLAMP
from edhmc.experiment import run_ab, analyse

deck, cmd = build()

print("A/A control — identical decks under common random numbers.")
print("Any nonzero difference here means the harness is leaking randomness.")
same = [c for c in deck if c.name == "March of the World Ooze"][0]
ra, rb, _ = run_ab(deck, cmd, "March of the World Ooze", same, n=5000)
for r in analyse(ra, rb, metrics=("damage", "cards_drawn", "tokens_made")):
    print("  ", r.line("A", "A"))

print("\n\nLorehold engine — A/A control")
from edhmc.decks.lorehold_v16 import build as lh_build
from edhmc.lorehold import simulate as lh_sim
ld, lc = lh_build()
same = [x for x in ld if x.name == "Verge Rangers"][0]
la, lb, _ = run_ab(ld, lc, "Verge Rangers", same, n=3000,
                   cfg={"turns": 14}, sim=lh_sim)
for r in analyse(la, lb, metrics=("mv_cheated", "miracles_cast", "damage")):
    print("  ", r.line("A", "A"))

print("\nTivit engine — A/A control")
from edhmc.decks.tivit_v1 import build as tv_build
from edhmc.tivit import simulate as tv_sim
td, tc = tv_build()
same = [x for x in td if x.name == "Academy Manufactor"][0]
ta, tb, _ = run_ab(td, tc, "Academy Manufactor", same, n=3000,
                   cfg={"turns": 14}, sim=tv_sim)
for r in analyse(ta, tb, metrics=("artifacts_made", "votes_cast", "damage")):
    print("  ", r.line("A", "A"))

print("\nKarlov engine — A/A control")
from edhmc.decks.karlov_v2 import build as kv_build
from edhmc.karlov import simulate as kv_sim
kd, kc = kv_build()
same = [x for x in kd if x.name == "Blood Artist"][0]
ka, kb, _ = run_ab(kd, kc, "Blood Artist", same, n=3000,
                   cfg={"turns": 14}, sim=kv_sim)
for r in analyse(ka, kb, metrics=("lifegain_triggers", "life_gained", "damage")):
    print("  ", r.line("A", "A"))

print("\nShilgengar engine — A/A control")
from edhmc.decks.shilgengar_v1 import build as sg_build
from edhmc.shilgengar import simulate as sg_sim
sd, sc = sg_build()
same = [x for x in sd if x.name == "Blood Artist"][0]
sa, sb, _ = run_ab(sd, sc, "Blood Artist", same, n=3000,
                   cfg={"turns": 14}, sim=sg_sim)
for r in analyse(sa, sb, metrics=("blood_made", "creatures_sacrificed", "damage")):
    print("  ", r.line("A", "A"))

print("\nAzusa engine — A/A control")
from edhmc.decks.azusa_v1 import build as az_build
from edhmc.azusa import simulate as az_sim
ad, ac = az_build()
same = [x for x in ad if x.name == "Lotus Cobra"][0]
aa, ab_, _ = run_ab(ad, ac, "Lotus Cobra", same, n=3000,
                    cfg={"turns": 14}, sim=az_sim)
for r in analyse(aa, ab_, metrics=("landfall_triggers", "lands_played", "damage")):
    print("  ", r.line("A", "A"))

# The same real comparison as always, now run in the other direction: March
# is in the deck as of v12, so this swaps it back out for the cut Skullclamp.
print("\nCRN variance reduction on the real comparison:")
ra, rb, _ = run_ab(deck, cmd, "March of the World Ooze", SKULLCLAMP, n=8000)
a = np.array([r["damage"] for r in ra]); b = np.array([r["damage"] for r in rb])
se_p = (b - a).std(ddof=1) / np.sqrt(len(a))
se_i = np.sqrt(a.var(ddof=1) + b.var(ddof=1)) / np.sqrt(len(a))
print(f"  corr(A,B)      = {np.corrcoef(a, b)[0,1]:.4f}")
print(f"  paired SE      = {se_p:.4f}")
print(f"  independent SE = {se_i:.4f}   ({se_i/se_p:.1f}x wider)")
print(f"  CRN is worth ~{(se_i/se_p)**2:.0f}x the number of games.")
