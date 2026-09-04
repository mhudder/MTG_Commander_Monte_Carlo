#!/usr/bin/env python3
"""
Lorehold v16 (pending) — second candidate swap.
    OUT  Monologue Tax, Urabrask // The Great Work
    IN   Monastery Mentor, Arcane Bombardment

Tested against the PENDING list (Dawning Archaic already in for Triumph),
not against the stale v15 baseline.
"""
import sys
import statistics as st

from edhmc.decks.lorehold_v16 import MONASTERY_MENTOR, ARCANE_BOMBARDMENT
from edhmc.pending import build_pending
from edhmc.lorehold import simulate as lh_sim
from edhmc.experiment import run_ab, analyse, analyse_conditional, report

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
TURNS = int(sys.argv[2]) if len(sys.argv) > 2 else 14
M = ("mv_cheated", "damage", "spell_damage", "combat_damage", "total_mv_cast",
     "spells_cast", "bombardment_copies", "won", "miracles_cast", "treasures_made")

# up_to=1 reproduces the baseline this experiment was run against:
# Dawning Archaic in, but Bombardment/Mentor not yet staged.
deck, commander = build_pending("lorehold", up_to=1)

EXP = [("combined 2-for-2", ["Monologue Tax", "Urabrask // The Great Work"],
        [MONASTERY_MENTOR, ARCANE_BOMBARDMENT]),
       ("Arcane Bombardment only (for Monologue Tax)",
        ["Monologue Tax"], [ARCANE_BOMBARDMENT]),
       ("Monastery Mentor only (for Urabrask)",
        ["Urabrask // The Great Work"], [MONASTERY_MENTOR])]

for label, outs, ins in EXP:
    a, b, cfg = run_ab(deck, commander, outs, ins, n=N,
                       cfg={"turns": TURNS}, sim=lh_sim)
    print()
    report(a, b, "v16 pending", label, cfg, analyse(a, b, metrics=M))
    for name, rows in (("A (v16 pending)", a), (label, b)):
        t = [r["test_card_turn"] for r in rows if r["cast_test_card"]]
        print(f"    {name:<44} P(deploy)={st.mean([r['cast_test_card'] for r in rows]):.3f}"
              f"  turn={st.mean(t) if t else float('nan'):.2f}"
              f"  answered={st.mean([min(1, r['test_card_answered']) for r in rows]):.3f}")

a, b, cfg = run_ab(deck, commander, ["Monologue Tax", "Urabrask // The Great Work"],
                   [MONASTERY_MENTOR, ARCANE_BOMBARDMENT], n=N,
                   cfg={"turns": TURNS}, sim=lh_sim)
keep, res = analyse_conditional(a, b, metrics=("mv_cheated", "damage", "won"))
print(f"\nConditional on a swapped card deploying (n={len(keep):,}, {len(keep)/len(a):.1%})")
for r in res:
    print("  ", r.line("A", "B"))

print("\nSensitivity: game length (combined swap)")
for t in (10, 12, 14, 16):
    a, b, _ = run_ab(deck, commander, ["Monologue Tax", "Urabrask // The Great Work"],
                     [MONASTERY_MENTOR, ARCANE_BOMBARDMENT],
                     n=max(3000, N // 3), cfg={"turns": t}, base_seed=77, sim=lh_sim)
    dm, dd, dw = analyse(a, b, metrics=("mv_cheated", "damage", "won"))
    print(f"  T{t:<3} mv_cheated {dm.mean_diff:+7.2f}  damage {dd.mean_diff:+7.2f}"
          f"  win rate {dw.mean_a:.3f} -> {dw.mean_b:.3f} ({dw.mean_diff:+.4f})")
